"""
WebSocket 서버
실시간 가격 업데이트 및 이벤트 브로드캐스트
"""

import asyncio
import os
import time
from typing import Dict, Set, Optional
from fastapi import WebSocket
from datetime import datetime, timezone

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Kiwoom REST API (lazy import - USE_KIWOOM_REST가 false면 임포트하지 않음)
_kiwoom_api = None


def get_kiwoom_api():
    """Kiwoom REST API 클라이언트 가져오기 (lazy init)"""
    global _kiwoom_api
    if _kiwoom_api is None and os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
        try:
            from src.kiwoom.rest_api import KiwoomRestAPI
            _kiwoom_api = KiwoomRestAPI.from_env()
            logger.info("Kiwoom REST API initialized for price broadcasting")
        except Exception as e:
            logger.warning(f"Failed to initialize Kiwoom REST API: {e}")
    return _kiwoom_api


class ConnectionManager:
    """
    WebSocket 연결 관리자

    Usage:
        manager = ConnectionManager()

        # 클라이언트 연결
        await manager.connect(websocket, "client_1")

        # 메시지 전송
        await manager.send_personal_message({"data": "value"}, "client_1")
        await manager.broadcast({"data": "value"})

        # 연결 종료
        manager.disconnect("client_1")
    """

    def __init__(self):
        # client_id -> WebSocket 매핑
        self.active_connections: Dict[str, WebSocket] = {}

        # topic -> Set[client_id] 매핑 (구독 관리)
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        클라이언트 연결

        Args:
            websocket: WebSocket 연결 객체
            client_id: 클라이언트 ID
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str, code: int = None, reason: str = None) -> None:
        """
        클라이언트 연결 종료

        Args:
            client_id: 클라이언트 ID
            code: 종료 코드 (선택 사항, Phase 1: GREEN)
            reason: 종료 사유 (선택 사항, Phase 1: GREEN)
        """
        # 모든 구독에서 클라이언트 제거
        for topic in list(self.subscriptions.keys()):
            self.unsubscribe(client_id, topic)

        # 연결 제거
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            # 상세한 종료 정보 로깅 (Phase 1: GREEN)
            code_str = f", code={code}" if code is not None else ""
            reason_str = f", reason='{reason}'" if reason else ""
            logger.info(f"WebSocket disconnected: {client_id}{code_str}{reason_str}")

    async def send_personal_message(self, message: dict, client_id: str) -> bool:
        """
        특정 클라이언트에게 메시지 전송

        Args:
            message: 전송할 메시지 (dict)
            client_id: 수신 클라이언트 ID

        Returns:
            전송 성공 여부
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
            self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict, topic: Optional[str] = None) -> None:
        """
        메시지 브로드캐스트

        Args:
            message: 전송할 메시지 (dict)
            topic: 토픽 (지정 시 해당 토픽 구독자에게만 전송)
        """
        # 수신자 결정
        if topic:
            recipients = self.subscriptions.get(topic, set())
        else:
            recipients = set(self.active_connections.keys())

        # 연결된 클라이언트에게 전송
        for client_id in recipients:
            if client_id in self.active_connections:
                await self.send_personal_message(message, client_id)

    def subscribe(self, client_id: str, topic: str) -> None:
        """
        토픽 구독

        Args:
            client_id: 클라이언트 ID
            topic: 구독할 토픽

        Note:
            topic이 'price:{ticker}' 형식이면 자동으로 price_broadcaster에 ticker 추가
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()

        self.subscriptions[topic].add(client_id)
        logger.info(f"Client {client_id} subscribed to {topic}")

        # price:{ticker} 형식이면 price_broadcaster에 ticker 추가
        if topic.startswith("price:"):
            ticker = topic.split(":", 1)[1]
            # ticker는 6자리 숫자여야 함
            if ticker.isdigit() and len(ticker) == 6:
                # 전역 price_broadcaster 인스턴스 가져오기
                from src.websocket.server import price_broadcaster
                price_broadcaster.add_ticker(ticker)

    def unsubscribe(self, client_id: str, topic: str) -> None:
        """
        토픽 구독 취소

        Args:
            client_id: 클라이언트 ID
            topic: 구독 취소할 토픽
        """
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

            # 구독자가 없으면 토픽 삭제 및 price_broadcaster에서 ticker 제거
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]

                # price:{ticker} 형식이면 price_broadcaster에서 ticker 제거
                if topic.startswith("price:"):
                    ticker = topic.split(":", 1)[1]
                    if ticker.isdigit() and len(ticker) == 6:
                        from src.websocket.server import price_broadcaster
                        price_broadcaster.remove_ticker(ticker)

            logger.info(f"Client {client_id} unsubscribed from {topic}")

    def get_subscriptions(self, client_id: str) -> Set[str]:
        """
        클라이언트의 구독 목록 조회

        Args:
            client_id: 클라이언트 ID

        Returns:
            구독 중인 토픽 집합
        """
        topics = set()
        for topic, subscribers in self.subscriptions.items():
            if client_id in subscribers:
                topics.add(topic)
        return topics

    def get_connection_count(self) -> int:
        """현재 연결 수 반환"""
        return len(self.active_connections)

    def get_subscriber_count(self, topic: str) -> int:
        """토픽별 구독자 수 반환"""
        return len(self.subscriptions.get(topic, set()))


# 전역 연결 관리자 인스턴스
connection_manager = ConnectionManager()


class PriceUpdateBroadcaster:
    """
    가격 업데이트 브로드캐스터

    Kiwoom REST API에서 실시간 가격 데이터를 가져와 브로드캐스트합니다.

    Usage:
        broadcaster = PriceUpdateBroadcaster()

        # 종목 구독 추가
        broadcaster.add_ticker("005930")

        # 브로드캐스팅 시작
        await broadcaster.start()

        # 브로드캐스팅 중지
        await broadcaster.stop()
    """

    # 기본 종목 (마켓 개장 시 항상 포함)
    # 삼성전자, SK하이닉스, NAVER, 현대차, LG화학, 셀트리온
    DEFAULT_TICKERS = {"005930", "000660", "035420", "005380", "051910", "068270"}

    def __init__(self, interval_seconds: int = 5):
        """
        Args:
            interval_seconds: 브로드캐스트 주기 (초)
        """
        self.interval_seconds = interval_seconds
        self._broadcast_task: Optional[asyncio.Task] = None
        self._is_running = False

        # 구독 중인 종목 목록
        self._active_tickers: Set[str] = set()

        # Kiwoom API 토큰 초기화 플래그
        self._token_initialized = False

    def add_ticker(self, ticker: str) -> None:
        """
        종목 구독 추가

        Args:
            ticker: 종목코드 (6자리)
        """
        self._active_tickers.add(ticker)
        logger.info(f"Added ticker to price broadcaster: {ticker}")

    def remove_ticker(self, ticker: str) -> None:
        """
        종목 구독 제거

        Args:
            ticker: 종목코드
        """
        self._active_tickers.discard(ticker)
        logger.info(f"Removed ticker from price broadcaster: {ticker}")

    def get_active_tickers(self) -> Set[str]:
        """활성 종목 목록 반환"""
        return self._active_tickers.copy()

    async def _ensure_token(self) -> bool:
        """Kiwoom API 토큰 초기화 확인"""
        if self._token_initialized:
            return True

        api = get_kiwoom_api()
        if api is None:
            return False

        try:
            success = await api.issue_token()
            if success:
                self._token_initialized = True
                logger.info("Kiwoom API token issued for price broadcasting")
                return True
            else:
                logger.warning("Failed to issue Kiwoom API token")
                return False
        except Exception as e:
            logger.error(f"Error issuing Kiwoom API token: {e}")
            return False

    async def _fetch_prices_from_kiwoom(self, tickers: Set[str]) -> Dict[str, dict]:
        """
        Kiwoom REST API에서 종목 가격 조회

        참고: get_current_price() API ID ka10001 문제로 인해
        get_daily_prices(days=1)를 대신 사용하여 최신 종가를 가져옵니다.

        Args:
            tickers: 조회할 종목코드 집합

        Returns:
            종목코드 -> 가격데이터 매핑
        """
        api = get_kiwoom_api()
        if api is None:
            return {}

        # 토큰 확인
        if not await self._ensure_token():
            return {}

        prices = {}
        for ticker in tickers:
            try:
                # ka10001 API ID 문제로 get_daily_prices(days=1) 대신 사용
                # 가장 최근 일자 데이터의 종가를 현재가로 사용
                daily_prices = await api.get_daily_prices(ticker, days=1)

                if daily_prices and len(daily_prices) > 0:
                    latest = daily_prices[0]  # 가장 최근 데이터 (dict 형식)
                    price = latest.get("price", 0)
                    change = latest.get("change", 0)
                    # 등락률 = (현재가 - 기준가) / 기준가 * 100 = change / (price - change) * 100
                    base_price = price - change
                    change_rate = (change / base_price * 100) if base_price > 0 else 0.0

                    prices[ticker] = {
                        "price": price,
                        "change": change,
                        "change_rate": change_rate,
                        "volume": latest.get("volume", 0),
                        "bid_price": price,  # 종가를 사용 (호가/비도가 없음)
                        "ask_price": price,
                    }
                    logger.info(f"Fetched daily price for {ticker}: {latest.get('price')}")
                else:
                    logger.warning(f"No daily price data for {ticker}")
            except Exception as e:
                logger.error(f"Error fetching daily price for {ticker}: {e}")

        return prices

    async def _broadcast_loop(self):
        """브로드캐스트 루프"""
        while self._is_running:
            try:
                # 브로드캐스트할 종목 결정 (기본 종목 + 추가된 종목)
                tickers_to_broadcast = self.DEFAULT_TICKERS | self._active_tickers

                if not tickers_to_broadcast:
                    logger.debug("No tickers to broadcast")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                # Kiwoom API 사용 여부에 따라 데이터 소스 결정
                if os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
                    price_updates = await self._fetch_prices_from_kiwoom(tickers_to_broadcast)
                    if not price_updates:
                        logger.warning("Failed to fetch prices from Kiwoom, no data to broadcast")
                        await asyncio.sleep(self.interval_seconds)
                        continue
                else:
                    logger.warning("Kiwoom REST API not enabled. Set USE_KIWOOM_REST=true to enable real-time prices.")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                # 브로드캐스트
                for ticker, data in price_updates.items():
                    await connection_manager.broadcast(
                        {
                            "type": "price_update",
                            "ticker": ticker,
                            "data": data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        topic=f"price:{ticker}",
                    )

                logger.info(f"Broadcasted price updates for {len(price_updates)} tickers")

            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")

            # 대기
            await asyncio.sleep(self.interval_seconds)

    async def start(self):
        """브로드캐스팅 시작"""
        if self._is_running:
            logger.warning("Broadcaster is already running")
            return

        self._is_running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("Price update broadcaster started")

    async def stop(self):
        """브로드캐스팅 중지"""
        if not self._is_running:
            return

        self._is_running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        logger.info("Price update broadcaster stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._is_running

    def _generate_mock_price_updates(self) -> Dict[str, dict]:
        """
        Mock 가격 업데이트 생성 (테스트용)

        Returns:
            종목코드 -> 가격데이터 매핑
        """
        import random

        mock_data = {}

        for ticker in self.DEFAULT_TICKERS:
            # 기반 가격 (종목별 다른 범위)
            base_prices = {
                "005930": 75000,  # 삼성전자
                "000660": 150000,  # SK하이닉스
                "035420": 250000,  # NAVER
                "005380": 240000,  # 현대차
                "051910": 80000,   # LG화학
                "068270": 700000,  # 셀트리온
            }
            base = base_prices.get(ticker, 50000)

            # 랜덤 변동
            change = random.randint(-2000, 2000)
            price = base + change
            change_rate = (change / base * 100) if base > 0 else 0

            mock_data[ticker] = {
                "price": price,
                "change": change,
                "change_rate": round(change_rate, 2),
                "volume": random.randint(100000, 10000000),
            }

        return mock_data


# 전역 브로드캐스터 인스턴스
price_broadcaster = PriceUpdateBroadcaster(interval_seconds=5)


# Phase 3: 하트비트/핑퐁 메커니즘 (Keep-Alive)
class HeartbeatManager:
    """
    WebSocket 하트비트 관리자

    연결된 클라이언트에게 주기적으로 ping을 전송하고
    응답하지 않는 클라이언트를 연결 해지합니다.

    Usage:
        heartbeat = HeartbeatManager(connection_manager)
        await heartbeat.start()
        await heartbeat.stop()
    """

    def __init__(self, connection_manager: 'ConnectionManager'):
        """
        초기화

        Args:
            connection_manager: ConnectionManager 인스턴스
        """
        self.connection_manager = connection_manager
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._is_running = False

        # 하트비트 설정
        self.ping_interval_seconds = 30  # 30초마다 ping
        self.pong_timeout_seconds = 90  # 90초간 pong 없으면 연결 종료

        # 클라이언트별 마지막 pong 수신 시간 추적
        self._last_pong_time: Dict[str, float] = {}

    async def _heartbeat_loop(self):
        """하트비트 루프"""
        while self._is_running:
            try:
                # 연결된 클라이언트 목록 가져오기
                active_clients = list(self.connection_manager.active_connections.keys())

                if not active_clients:
                    # 활성 연결이 없으면 대기
                    await asyncio.sleep(self.ping_interval_seconds)
                    continue

                logger.debug(f"Sending ping to {len(active_clients)} clients")

                # 모든 클라이언트에게 ping 전송
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                for client_id in active_clients:
                    await self.connection_manager.send_personal_message(
                        ping_message,
                        client_id
                    )

                # 타임아웃 대기
                await asyncio.sleep(self.ping_interval_seconds)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(self.ping_interval_seconds)

    async def start(self):
        """하트비트 시작"""
        if self._is_running:
            logger.warning("Heartbeat is already running")
            return

        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket heartbeat started (30s interval)")

    async def stop(self):
        """하트비트 중지"""
        if not self._is_running:
            return

        self._is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        logger.info("WebSocket heartbeat stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._is_running

    def record_pong(self, client_id: str) -> None:
        """
        Pong 수신 시간 기록

        Args:
            client_id: 클라이언트 ID
        """
        self._last_pong_time[client_id] = time.time()
        logger.debug(f"Pong received from {client_id}")

    def is_client_alive(self, client_id: str) -> bool:
        """
        클라이언트 활성 상태 확인

        Args:
            client_id: 클라이언트 ID

        Returns:
            True if client is alive (pong 수신한지 90초 이내), False otherwise
        """
        if client_id not in self._last_pong_time:
            # 아직 pong을 받지 않은 클라이언트는 새로 연결된 것으로 간주
            return True

        elapsed = time.time() - self._last_pong_time[client_id]
        return elapsed < self.pong_timeout_seconds

    def get_last_pong_time(self, client_id: str) -> Optional[float]:
        """
        마지막 pong 수신 시간 반환

        Args:
            client_id: 클라이언트 ID

        Returns:
            마지막 pong 수신 시간 (Unix timestamp), 없으면 None
        """
        return self._last_pong_time.get(client_id)

    def remove_client(self, client_id: str) -> None:
        """
        클라이언트 제거 시 정리

        Args:
            client_id: 클라이언트 ID
        """
        self._last_pong_time.pop(client_id, None)


# 전역 하트비트 관리자 인스턴스 (lazy init)
_heartbeat_manager: Optional[HeartbeatManager] = None


def get_heartbeat_manager() -> Optional[HeartbeatManager]:
    """
    하트비트 관리자 인스턴스 반환 (lazy init)

    Returns:
        HeartbeatManager 인스턴 또는 None (WebSocket이 사용되지 않으면)
    """
    return _heartbeat_manager


def create_heartbeat_manager(connection_manager: 'ConnectionManager') -> HeartbeatManager:
    """
    하트비트 관리자 인스턴스 생성 및 시작

    Args:
        connection_manager: ConnectionManager 인스턴스

    Returns:
        생성된 HeartbeatManager 인스턴스
    """
    global _heartbeat_manager
    _heartbeat_manager = HeartbeatManager(connection_manager)

    # 백그라운드에서 시작 (비동기)
    asyncio.create_task(_heartbeat_manager.start())

    return _heartbeat_manager
