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
            websocket: WebSocket 연결 객체 (이미 accept() 호출된 상태여야 함)
            client_id: 클라이언트 ID
        """
        # FastAPI WebSocket: accept()는 라우트 핸들러에서 호출해야 함
        # 여기서는 이미 accept된 상태라고 가정
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
            print(f"[BROADCAST] Topic={topic}, subscribers={len(recipients)}")
        else:
            recipients = set(self.active_connections.keys())
            print(f"[BROADCAST] No topic, broadcasting to all {len(recipients)} connections")

        # 연결된 클라이언트에게 전송
        sent_count = 0
        for client_id in recipients:
            if client_id in self.active_connections:
                await self.send_personal_message(message, client_id)
                sent_count += 1

        if sent_count > 0:
            print(f"[BROADCAST] Sent to {sent_count} recipients")
        else:
            print(f"[BROADCAST] No recipients found to send to")

    def _is_valid_ticker(self, ticker: str) -> bool:
        """
        종목 코드 유효성 검증 (ELW 지원)

        - KOSPI/KOSDAQ: 6자리 숫자
        - ELW(상장지수증권): 6자리 (숫자+알파벳 조합)

        Args:
            ticker: 종목 코드

        Returns:
            bool: 유효한 종목 코드이면 True
        """
        if not ticker or len(ticker) != 6:
            return False

        # 전체 숫자이면 통과 (KOSPI/KOSDAQ)
        if ticker.isdigit():
            return True

        # ELW 형식: 숫자+알파벳 조합
        has_digit = any(c.isdigit() for c in ticker)
        has_alpha = any(c.isalpha() for c in ticker)

        return has_digit and has_alpha

    def subscribe(self, client_id: str, topic: str) -> None:
        """
        토픽 구독 (ELW 지원, 디버깅 로그 추가)

        Args:
            client_id: 클라이언트 ID
            topic: 구독할 토픽

        Note:
            topic이 'price:{ticker}' 형식이면 자동으로 KiwoomWebSocketBridge에 ticker 추가
        """
        print(f"[SUBSCRIBE] Client {client_id} subscribing to {topic}")

        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
            print(f"[SUBSCRIBE] Created new topic set for {topic}")

        self.subscriptions[topic].add(client_id)
        print(f"[SUBSCRIBE] Added client {client_id} to {topic}, total: {len(self.subscriptions[topic])}")
        logger.info(f"Client {client_id} subscribed to {topic}")

        # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
        if topic.startswith("price:"):
            ticker = topic.split(":", 1)[1]
            print(f"[SUBSCRIBE] Processing price ticker: {ticker}, is_valid: {self._is_valid_ticker(ticker)}")

            # ELW 포함한 종목 코드 검증
            if self._is_valid_ticker(ticker):
                print(f"[SUBSCRIBE] Ticker {ticker} is valid, checking data source")
                # KiwoomWebSocketBridge에 ticker 추가 (실시간 데이터)
                from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
                ws_bridge = get_kiwoom_ws_bridge()
                has_pipeline = ws_bridge.has_pipeline() if ws_bridge else False
                print(f"[SUBSCRIBE] ws_bridge: {ws_bridge}, running: {ws_bridge.is_running() if ws_bridge else False}, has_pipeline: {has_pipeline}")

                # Kiwoom Pipeline이 있으면 실시간 데이터 사용, 없으면 DB 폴링 사용
                if ws_bridge and ws_bridge.is_running() and has_pipeline:
                    import asyncio
                    asyncio.create_task(ws_bridge.add_ticker(ticker))
                    print(f"[WS BRIDGE] Added ticker to KiwoomWebSocketBridge: {ticker}")
                else:
                    # Kiwoom Pipeline이 없으면 price_broadcaster에 추가 (DB 폴링)
                    from src.websocket.server import price_broadcaster
                    price_broadcaster.add_ticker(ticker)
                    reason = "no pipeline" if not has_pipeline else "bridge not running"
                    print(f"[BROADCASTER] Added ticker to price_broadcaster ({reason}): {ticker}")
            else:
                print(f"[SUBSCRIBE] Ticker {ticker} is INVALID, skipping bridge registration")

    def unsubscribe(self, client_id: str, topic: str) -> None:
        """
        토픽 구독 취소

        Args:
            client_id: 클라이언트 ID
            topic: 구독 취소할 토픽
        """
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

            # 구독자가 없으면 토픽 삭제 및 브릿지에서 ticker 제거
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]

                # price:{ticker} 형식이면 브릿지에서 ticker 제거
                if topic.startswith("price:"):
                    ticker = topic.split(":", 1)[1]
                    # ELW 포함한 종목 코드 검증
                    if self._is_valid_ticker(ticker):
                        # KiwoomWebSocketBridge에서 ticker 제거
                        from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
                        ws_bridge = get_kiwoom_ws_bridge()
                        has_pipeline = ws_bridge.has_pipeline() if ws_bridge else False
                        # Kiwoom Pipeline이 있으면 실시간 데이터 사용, 없으면 DB 폴링 사용
                        if ws_bridge and ws_bridge.is_running() and has_pipeline:
                            import asyncio
                            asyncio.create_task(ws_bridge.remove_ticker(ticker))
                            print(f"[WS BRIDGE] Removed ticker from KiwoomWebSocketBridge: {ticker}")
                        else:
                            # Kiwoom Pipeline이 없으면 price_broadcaster에서 제거
                            from src.websocket.server import price_broadcaster
                            price_broadcaster.remove_ticker(ticker)
                            reason = "no pipeline" if not has_pipeline else "bridge not running"
                            print(f"[BROADCASTER] Removed ticker from price_broadcaster ({reason}): {ticker}")

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
    # 삼성전자, SK하이닉스, NAVER, 현대차, 삼성물산, 동화약품
    # + 주요 VCP 시그널 종목 (흥국화재우, 삼양홀딩스 등)
    DEFAULT_TICKERS = {
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "035420",  # NAVER
        "005380",  # 현대차
        "028260",  # 삼성물산
        "000020",  # 동화약품
        # VCP 시그널 주요 종목 (0원 표시 문제 해결)
        "000545",  # 흥국화재우
        "000070",  # 삼양홀딩스
        "001540",  # 한독
        "001250",  # 삼성에스디에스
        "002360",  # 축남제약
    }

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

        # 실시간 가격 캐시 (Daytrading Scanner에서 사용)
        self._price_cache: Dict[str, dict] = {}  # ticker -> price_data

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

    async def _fetch_prices_from_db(self, tickers: Set[str]) -> Dict[str, dict]:
        """
        데이터베이스에서 종목 가격 조회

        Kiwoom REST API가 설정되지 않은 경우 DB의 최신 가격 데이터를 사용합니다.

        Args:
            tickers: 조회할 종목코드 집합

        Returns:
            종목코드 -> 가격데이터 매핑
        """
        from src.websocket.price_provider import PriceDataProvider

        print(f"[FETCH DB] Fetching prices for tickers: {tickers}")
        provider = PriceDataProvider()
        price_dicts = provider.get_latest_prices(list(tickers))
        print(f"[FETCH DB] Got price_dicts for {len(price_dicts)} tickers")

        # PriceDataProvider의 형식을 브로드캐스터 형식으로 변환
        result = {}
        for ticker, data in price_dicts.items():
            result[ticker] = {
                "price": data.get("close", 0),
                "change": data.get("change", 0),
                "change_rate": data.get("change_rate", 0),
                "volume": data.get("volume", 0),
                "bid_price": data.get("close", 0),
                "ask_price": data.get("close", 0),
            }

        print(f"[FETCH DB] Returning {len(result)} prices from database")
        return result

    def get_cached_prices(self) -> Dict[str, dict]:
        """
        캐시된 실시간 가격 반환 (Daytrading Scanner에서 사용)

        Returns:
            ticker -> price_data 매핑
        """
        return self._price_cache.copy()

    def get_cached_price(self, ticker: str) -> Optional[dict]:
        """
        단일 종목 캐시 가격 반환

        Args:
            ticker: 종목 코드

        Returns:
            가격 데이터 또는 None
        """
        return self._price_cache.get(ticker)

    async def _broadcast_loop(self):
        """브로드캐스트 루프"""
        print(f"[BROADCASTER LOOP] Entered, _is_running={self._is_running}")
        while self._is_running:
            try:
                # 브로드캐스트할 종목 결정 (기본 종목 + 추가된 종목)
                tickers_to_broadcast = self.DEFAULT_TICKERS | self._active_tickers

                if not tickers_to_broadcast:
                    print("[BROADCASTER LOOP] No tickers to broadcast")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                print(f"[BROADCASTER LOOP] Tickers to broadcast: {tickers_to_broadcast}")

                # Kiwoom API 사용 시 실시간 데이터 조회
                if os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
                    print("[BROADCASTER LOOP] Using Kiwoom API")
                    price_updates = await self._fetch_prices_from_kiwoom(tickers_to_broadcast)
                    if not price_updates:
                        logger.warning("Failed to fetch prices from Kiwoom")
                        await asyncio.sleep(self.interval_seconds)
                        continue
                else:
                    # Kiwoom 미설정 시 DB에서 최근 가격 데이터 조회
                    print("[BROADCASTER LOOP] Using Database for prices")
                    price_updates = await self._fetch_prices_from_db(tickers_to_broadcast)
                    if not price_updates:
                        print("[BROADCASTER LOOP] No price data available in database")
                        await asyncio.sleep(self.interval_seconds)
                        continue

                # 가격 캐시 업데이트 (Daytrading Scanner에서 사용)
                self._price_cache.update(price_updates)

                # 브로드캐스트 및 API Gateway 캐시 업데이트
                for ticker, data in price_updates.items():
                    print(f"[BROADCAST] Sending price update for {ticker}: {data}")
                    message = {
                        "type": "price_update",
                        "ticker": ticker,
                        "data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "kiwoom_rest" if os.getenv("USE_KIWOOM_REST", "false").lower() == "true" else "db",
                    }

                    # API Gateway 실시간 가격 캐시 업데이트
                    try:
                        from src.websocket.routes import realtime_price_cache
                        # 메시지 데이터를 캐시 형식으로 변환
                        cache_data = {
                            "price": data.get("price"),
                            "change": data.get("change"),
                            "change_rate": data.get("change_rate"),
                            "volume": data.get("volume"),
                            "bid_price": data.get("bid_price"),
                            "ask_price": data.get("ask_price"),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        realtime_price_cache.update(ticker, cache_data)
                        logger.debug(f"[Cache] Updated API cache for {ticker}")
                    except ImportError as e:
                        logger.debug(f"[Cache] Could not update API cache: {e}")

                    await connection_manager.broadcast(
                        message,
                        topic=f"price:{ticker}",
                    )

                print(f"[BROADCASTER LOOP] Broadcasted price updates for {len(price_updates)} tickers")

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
        print("[BROADCASTER] Starting broadcast task, _is_running set to True")
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        print(f"[BROADCASTER] Broadcast task created: {self._broadcast_task}")
        print("[BROADCASTER] Price update broadcaster started")

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
                "005930": 75000,   # 삼성전자
                "000660": 150000,  # SK하이닉스
                "035420": 250000,  # NAVER
                "005380": 240000,  # 현대차
                "028260": 140000,  # 삼성물산
                "000020": 60000,   # 동화약품
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


# ============================================================================
# VCP 시그널 브로드캐스터 (실시간 시그널 업데이트)
# ============================================================================

class SignalBroadcaster:
    """
    VCP 시그널 실시간 브로드캐스터

    VCP 스캔 결과를 WebSocket 클라이언트에게 실시간으로 브로드캐스트합니다.

    Usage:
        # 시그널 업데이트 브로드캐스트
        await signal_broadcaster.broadcast_signal_update(signals)
    """

    def __init__(self):
        """초기화"""
        self._running = False

    async def broadcast_signal_update(
        self,
        signals: list,
        signal_type: str = "VCP"
    ) -> None:
        """
        시그널 업데이트 브로드캐스트

        Args:
            signals: 시그널 리스트 (Dict 또는 to_dict() 메서드를 가진 객체)
            signal_type: 시그널 타입 (VCP, JONGGA_V2 등)
        """
        # 시그널 데이터 변환 (객체 → dict)
        signal_dicts = []
        for sig in signals:
            if hasattr(sig, "to_dict"):
                signal_dicts.append(sig.to_dict())
            elif isinstance(sig, dict):
                signal_dicts.append(sig)
            else:
                logger.warning(f"Invalid signal type: {type(sig)}")

        message = {
            "type": "signal_update",
            "data": {
                "signal_type": signal_type,
                "signals": signal_dicts,
                "count": len(signal_dicts),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        # signal:vcp 토픽으로 브로드캐스트
        topic = f"signal:{signal_type.lower()}"
        await connection_manager.broadcast(message, topic=topic)
        logger.info(f"Broadcasted {len(signal_dicts)} {signal_type} signals to topic '{topic}'")

    async def start(self) -> None:
        """브로드캐스터 시작"""
        self._running = True
        logger.info("Signal broadcaster started")

    async def stop(self) -> None:
        """브로드캐스터 중지"""
        self._running = False
        logger.info("Signal broadcaster stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._running


# 전역 시그널 브로드캐스터 인스턴스
signal_broadcaster = SignalBroadcaster()


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


# ============================================================================
# Redis Pub/Sub 리스너 (Celery 태스크 → WebSocket 브로드캐스트)
# ============================================================================

class RedisSubscriber:
    """
    Redis Pub/Sub 구독자

    Celery 태스크가 Redis에 발행한 메시지를 구독하여
    WebSocket 클라이언트들에게 브로드캐스트합니다.

    Usage:
        subscriber = RedisSubscriber(connection_manager)
        await subscriber.start()
        await subscriber.stop()
    """

    # 구독할 Redis 채널 패턴
    CHANNEL_PREFIX = "ws:broadcast:"

    def __init__(self, connection_manager: ConnectionManager):
        """
        초기화

        Args:
            connection_manager: WebSocket 연결 관리자
        """
        self.connection_manager = connection_manager
        self._subscriber_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._redis_client = None

    async def _subscribe_loop(self):
        """Redis Pub/Sub 구독 루프"""
        print("[REDIS SUB] _subscribe_loop() started")  # 동기 print 로그
        logger.info("[REDIS SUB] _subscribe_loop() coroutine started")

        # Redis URL 확인
        celery_broker = os.getenv("CELERY_BROKER_URL")
        redis_url_env = os.getenv("REDIS_URL")
        print(f"[REDIS SUB] CELERY_BROKER_URL={celery_broker}, REDIS_URL={redis_url_env}")

        redis_url = celery_broker or redis_url_env or "redis://localhost:6379/0"
        print(f"[REDIS SUB] Using Redis URL: {redis_url}")
        logger.info(f"[REDIS SUB] Starting subscribe loop, URL={redis_url}")

        while self._is_running:
            try:
                # Redis 비동기 클라이언트 생성 (redis.asyncio 방식)
                print("[REDIS SUB] Importing redis.asyncio...")
                import redis.asyncio as redis
                print("[REDIS SUB] Creating Redis client...")

                self._redis_client = redis.Redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                print(f"[REDIS SUB] Redis client created: {self._redis_client}")

                logger.info(f"[REDIS SUB] Connecting to Redis at {redis_url}")

                # 연결 테스트
                print("[REDIS SUB] Pinging Redis...")
                await self._redis_client.ping()
                print("[REDIS SUB] Ping successful!")
                logger.info("[REDIS SUB] Redis connection successful")

                # Pub/Sub 구독자 생성
                print("[REDIS SUB] Creating pubsub...")
                pubsub = self._redis_client.pubsub()
                print(f"[REDIS SUB] Pubsub created: {pubsub}")

                # 채널 패턴 구독 (ws:broadcast:*)
                pattern = f"{self.CHANNEL_PREFIX}*"
                print(f"[REDIS SUB] Subscribing to pattern: {pattern}")
                await pubsub.psubscribe(pattern)
                print(f"[REDIS SUB] Subscription successful!")
                logger.info(f"[REDIS SUB] Subscribed to Redis channel pattern: {pattern}")

                # 메시지 수신 대기
                print("[REDIS SUB] Entering message listener loop...")
                async for message in pubsub.listen():
                    print(f"[REDIS SUB] Got message: {message.get('type')}, full: {message}")
                    if not self._is_running:
                        logger.info("[REDIS SUB] Stopping message listener")
                        break

                    logger.debug(f"[REDIS SUB] Received message: {message.get('type')}")

                    # 데이터 메시지만 처리 (pmessage = pattern message)
                    if message.get("type") in ["pmessage", "message"]:
                        channel = message.get("channel")
                        data = message.get("data")

                        print(f"[REDIS SUB] Processing pmessage: channel={channel}, data={data[:100] if data else None}")

                        # 토픽 추출 (ws:broadcast:market-gate -> market-gate)
                        topic = channel.replace(self.CHANNEL_PREFIX, "") if channel else ""

                        logger.info(f"[REDIS SUB] Received on {channel}: {topic}")

                        try:
                            # JSON 파싱
                            import json
                            msg_data = json.loads(data)
                            print(f"[REDIS SUB] JSON parsed: {msg_data.get('type') if msg_data else None}")

                            # WebSocket으로 브로드캐스트
                            print(f"[REDIS SUB] Broadcasting to {topic}...")
                            await self.connection_manager.broadcast(msg_data, topic=topic)
                            logger.info(f"[REDIS → WS] Broadcasted to topic: {topic}")

                        except json.JSONDecodeError as e:
                            logger.error(f"[REDIS SUB] Failed to parse JSON: {e}")
                            print(f"[REDIS SUB] JSON decode error: {e}")
                        except Exception as e:
                            logger.error(f"[REDIS → WS] Broadcast error: {e}")
                            print(f"[REDIS SUB] Broadcast error: {e}")

            except asyncio.CancelledError:
                logger.info("[REDIS SUB] Task cancelled")
                break
            except Exception as e:
                import traceback
                tb_str = traceback.format_exc()
                print(f"[REDIS SUB] Error: {e}\n{tb_str}")
                logger.error(f"[REDIS SUB] Error in subscribe loop: {e}\n{tb_str}")
                if self._is_running:
                    # 연결 끊기면 5초 후 재시도
                    logger.info("[REDIS SUB] Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

        logger.info("[REDIS SUB] Subscribe loop ended")

    async def start(self):
        """구독 시작"""
        print(f"[REDIS SUB] start() method called, _is_running={self._is_running}")  # 동기 print 로그
        logger.info(f"[REDIS SUB] start() method called, _is_running={self._is_running}")

        if self._is_running:
            print("[REDIS SUB] Already running, returning")
            return

        print("[REDIS SUB] Setting _is_running to True")
        self._is_running = True

        # 태스크 생성 및 실행
        logger.info("[REDIS SUB] Creating task...")
        self._subscriber_task = asyncio.create_task(self._subscribe_loop())
        print(f"[REDIS SUB] Task created: {self._subscriber_task}, done={self._subscriber_task.done()}")
        logger.info(f"[REDIS SUB] Task created: {self._subscriber_task}, done={self._subscriber_task.done()}")

        # 태스크가 바로 완료되면 에러 로그 확인
        if self._subscriber_task.done():
            print("[REDIS SUB] Task completed immediately - this is unexpected")
            logger.error("[REDIS SUB] Task completed immediately - checking for errors")
            try:
                result = await self._subscriber_task
                print(f"[REDIS SUB] Task result: {result}")
                logger.info(f"[REDIS SUB] Task completed immediately: {result}")
            except Exception as e:
                print(f"[REDIS SUB] Task failed with exception: {e}")
                logger.error(f"[REDIS SUB] Task failed: {e}")
                # 재시도
                self._is_running = False
                await self.start()

        print("[REDIS SUB] Start method complete")
        logger.info("[REDIS SUB] Redis Pub/Sub subscriber started")

    async def stop(self):
        """구독 중지"""
        if not self._is_running:
            return

        self._is_running = False

        # 태스크 취소
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

        # Redis 연결 종료
        if self._redis_client:
            await self._redis_client.close()

        logger.info("Redis Pub/Sub subscriber stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._is_running


# 전역 Redis 구독자 인스턴스
_redis_subscriber: Optional[RedisSubscriber] = None


def get_redis_subscriber() -> Optional[RedisSubscriber]:
    """
    Redis 구독자 인스턴스 반환

    Returns:
        RedisSubscriber 인스턴스 또는 None
    """
    return _redis_subscriber


def create_redis_subscriber(connection_manager: ConnectionManager) -> RedisSubscriber:
    """
    Redis 구독자 인스턴스 생성 및 시작

    Args:
        connection_manager: ConnectionManager 인스턴스

    Returns:
        생성된 RedisSubscriber 인스턴스
    """
    global _redis_subscriber
    _redis_subscriber = RedisSubscriber(connection_manager)

    # 백그라운드에서 시작
    asyncio.create_task(_redis_subscriber.start())

    return _redis_subscriber
