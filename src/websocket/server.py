"""
WebSocket 서버
실시간 가격 업데이트 및 이벤트 브로드캐스트
"""

import asyncio
import os
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

    def disconnect(self, client_id: str) -> None:
        """
        클라이언트 연결 종료

        Args:
            client_id: 클라이언트 ID
        """
        # 모든 구독에서 클라이언트 제거
        for topic in list(self.subscriptions.keys()):
            self.unsubscribe(client_id, topic)

        # 연결 제거
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")

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


# 전역 브로드캐스터 인스턴스
price_broadcaster = PriceUpdateBroadcaster(interval_seconds=5)
