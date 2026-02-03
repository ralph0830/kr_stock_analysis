"""
Kiwoom WebSocket Bridge
Kiwoom Pipeline의 실시간 데이터를 WebSocket 클라이언트에게 전달합니다.
"""

import logging
from typing import Optional, Set, Dict, Any

from src.kiwoom.base import KiwoomEventType, RealtimePrice, IndexRealtimePrice
from src.websocket.server import connection_manager


logger = logging.getLogger(__name__)


# 업종코드 매핑
INDEX_CODES = {
    "001": "KOSPI",
    "201": "KOSDAQ",
}


class KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket Bridge

    Kiwoom Pipeline에서 발생하는 실시간 데이터 이벤트를 수신하여
    WebSocket 연결된 클라이언트에게 브로드캐스트합니다.
    """

    def __init__(self):
        self._running = False
        self._pipeline: Optional[Any] = None
        self._event_handlers: Dict[KiwoomEventType, list] = {}

        # 구독 중인 종목 (WebSocket 클라이언트들이 구독한 종목)
        self._active_tickers: Set[str] = set()
        # 구독 중인 지수 (KOSPI, KOSDAQ)
        self._active_indices: Set[str] = set()

    async def start(self, pipeline: Any) -> None:
        """
        브릿지 시작

        Args:
            pipeline: KiwoomPipelineManager 인스턴스
        """
        if self._running:
            logger.warning("KiwoomWebSocketBridge already running")
            return

        self._pipeline = pipeline
        self._running = True

        # Pipeline 이벤트 핸들러 등록
        self._register_event_handlers()

        logger.info("KiwoomWebSocketBridge started")

    async def stop(self) -> None:
        """브릿지 중지"""
        if not self._running:
            return

        self._running = False

        # 이벤트 핸들러 해제
        if self._pipeline:
            self._pipeline.unregister_event_handler(
                KiwoomEventType.RECEIVE_REAL_DATA,
                self._on_realtime_data
            )
            self._pipeline.unregister_event_handler(
                KiwoomEventType.RECEIVE_INDEX_DATA,
                self._on_index_data
            )

        self._pipeline = None
        self._active_tickers.clear()
        self._active_indices.clear()

        logger.info("KiwoomWebSocketBridge stopped")

    def _register_event_handlers(self) -> None:
        """Pipeline 이벤트 핸들러 등록"""
        if self._pipeline:
            self._pipeline.register_event_handler(
                KiwoomEventType.RECEIVE_REAL_DATA,
                self._on_realtime_data
            )
            self._pipeline.register_event_handler(
                KiwoomEventType.RECEIVE_INDEX_DATA,
                self._on_index_data
            )
            logger.info("Registered KiwoomWebSocketBridge event handlers for RECEIVE_REAL_DATA, RECEIVE_INDEX_DATA")
        else:
            logger.warning("Cannot register event handler: pipeline is None")

    async def _on_realtime_data(self, price: RealtimePrice) -> None:
        """
        실시간 데이터 수신 시 처리

        Args:
            price: 실시간 가격 데이터
        """
        if not self._running:
            print(f"[WS BRIDGE] Not running, ignoring price data for {price.ticker}")
            return

        ticker = price.ticker

        # 구독 중인 종목인지 확인
        if ticker not in self._active_tickers:
            print(f"[WS BRIDGE] Ticker {ticker} not in active_tickers: {self._active_tickers}")
            return

        # WebSocket으로 브로드캐스트
        try:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat()
            print(f"[WS BRIDGE] Broadcasting price update for {ticker}: {price.price}")
            await connection_manager.broadcast(
                {
                    "type": "price_update",
                    "ticker": ticker,
                    "data": {
                        "price": price.price,
                        "change": price.change,
                        "change_rate": price.change_rate,
                        "volume": price.volume,
                        "bid_price": price.bid_price,
                        "ask_price": price.ask_price,
                    },
                    "timestamp": timestamp,
                },
                topic=f"price:{ticker}",
            )
            print(f"[WS BRIDGE] ✅ Broadcasted price update for {ticker}: {price.price}")
        except Exception as e:
            print(f"[WS BRIDGE] ❌ Failed to broadcast price update: {e}")

    async def _on_index_data(self, index_data: IndexRealtimePrice) -> None:
        """
        지수 데이터 수신 시 처리

        Args:
            index_data: 실시간 지수 데이터
        """
        if not self._running:
            print(f"[WS BRIDGE] Not running, ignoring index data for {index_data.code}")
            return

        code = index_data.code

        # 구독 중인 지수인지 확인
        if code not in self._active_indices:
            print(f"[WS BRIDGE] Index {code} not in active_indices: {self._active_indices}")
            return

        # WebSocket으로 브로드캐스트
        try:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat()
            print(f"[WS BRIDGE] Broadcasting index update for {index_data.name}: {index_data.index}")
            await connection_manager.broadcast(
                {
                    "type": "index_update",
                    "code": code,
                    "name": index_data.name,
                    "data": {
                        "index": index_data.index,
                        "change": index_data.change,
                        "change_rate": index_data.change_rate,
                        "volume": index_data.volume,
                    },
                    "timestamp": timestamp,
                },
                topic=f"market:{index_data.name.lower()}",
            )
            print(f"[WS BRIDGE] ✅ Broadcasted index update for {index_data.name}: {index_data.index}")
        except Exception as e:
            print(f"[WS BRIDGE] ❌ Failed to broadcast index update: {e}")

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

    async def add_ticker(self, ticker: str) -> bool:
        """
        종목 구독 추가

        Args:
            ticker: 종목코드

        Returns:
            성공 여부
        """
        # 종목 코드 검증 (ELW 지원)
        if not self._is_valid_ticker(ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            return False

        if ticker in self._active_tickers:
            return True

        # Kiwoom WebSocket 실시간 시세 등록 (pipeline.subscribe() 사용)
        if self._pipeline:
            try:
                success = await self._pipeline.subscribe(ticker)
                if success:
                    logger.info(f"Subscribed to Kiwoom real-time data: {ticker}")
                else:
                    logger.warning(f"Failed to subscribe to Kiwoom real-time data for {ticker}")
                    # 실패해도 _active_tickers에 추가 (데이터가 오면 브로드캐스트)
            except Exception as e:
                logger.error(f"Error subscribing to {ticker}: {e}")
                # 에러가 발생해도 _active_tickers에 추가

        self._active_tickers.add(ticker)
        logger.info(f"Added ticker to KiwoomWebSocketBridge: {ticker}")
        return True

    async def remove_ticker(self, ticker: str) -> bool:
        """
        종목 구독 제거

        Args:
            ticker: 종목코드

        Returns:
            성공 여부
        """
        # Kiwoom WebSocket 실시간 시세 해제 (pipeline.unsubscribe() 사용)
        if self._pipeline:
            try:
                await self._pipeline.unsubscribe(ticker)
            except Exception as e:
                logger.error(f"Error unsubscribing from {ticker}: {e}")

        self._active_tickers.discard(ticker)
        logger.info(f"Removed ticker from KiwoomWebSocketBridge: {ticker}")
        return True

    async def add_index(self, code: str) -> bool:
        """
        지수 구독 추가

        Args:
            code: 업종코드 (001: KOSPI, 201: KOSDAQ)

        Returns:
            성공 여부
        """
        # Kiwoom WebSocket 지수 실시간 시세 등록
        if self._pipeline:
            try:
                success = await self._pipeline.subscribe_index(code)
                if success:
                    name = INDEX_CODES.get(code, code)
                    logger.info(f"Subscribed to Kiwoom index data: {name} ({code})")
                else:
                    logger.warning(f"Failed to subscribe to Kiwoom index data for {code}")
            except Exception as e:
                logger.error(f"Error subscribing to index {code}: {e}")

        self._active_indices.add(code)
        name = INDEX_CODES.get(code, code)
        logger.info(f"Added index to KiwoomWebSocketBridge: {name} ({code})")
        return True

    async def remove_index(self, code: str) -> bool:
        """
        지수 구독 제거

        Args:
            code: 업종코드

        Returns:
            성공 여부
        """
        # Kiwoom WebSocket 지수 실시간 시세 해제
        if self._pipeline:
            try:
                await self._pipeline.unsubscribe_index(code)
            except Exception as e:
                logger.error(f"Error unsubscribing from index {code}: {e}")

        self._active_indices.discard(code)
        name = INDEX_CODES.get(code, code)
        logger.info(f"Removed index from KiwoomWebSocketBridge: {name} ({code})")
        return True

    def get_active_tickers(self) -> Set[str]:
        """활성 종목 목록 반환"""
        return self._active_tickers.copy()

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._running

    def has_pipeline(self) -> bool:
        """Pipeline 연결 여부 확인 (Kiwoom API 사용 가능 여부)"""
        return self._pipeline is not None


# 전역 인스턴스
_kiwoom_ws_bridge: Optional[KiwoomWebSocketBridge] = None


def get_kiwoom_ws_bridge() -> Optional[KiwoomWebSocketBridge]:
    """Kiwoom WebSocket Bridge 전역 인스턴스 가져오기"""
    return _kiwoom_ws_bridge


async def init_kiwoom_ws_bridge(pipeline: Any, default_tickers: list = None, subscribe_indices: bool = True) -> KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket Bridge 초기화 및 시작

    Args:
        pipeline: KiwoomPipelineManager 인스턴스
        default_tickers: 기본 구독 종목 리스트
        subscribe_indices: KOSPI/KOSDAQ 지수 구독 여부

    Returns:
        KiwoomWebSocketBridge 인스턴스
    """
    global _kiwoom_ws_bridge

    if _kiwoom_ws_bridge is None:
        _kiwoom_ws_bridge = KiwoomWebSocketBridge()

    await _kiwoom_ws_bridge.start(pipeline)

    # 기본 종목 추가 (선택 사항)
    if default_tickers:
        for ticker in default_tickers:
            await _kiwoom_ws_bridge.add_ticker(ticker)
        logger.info(f"Added default tickers to KiwoomWebSocketBridge: {default_tickers}")

    # KOSPI/KOSDAQ 지수 구독
    if subscribe_indices:
        await _kiwoom_ws_bridge.add_index("001")  # KOSPI
        await _kiwoom_ws_bridge.add_index("201")  # KOSDAQ
        logger.info("Added KOSPI/KOSDAQ indices to KiwoomWebSocketBridge")

    return _kiwoom_ws_bridge


async def shutdown_kiwoom_ws_bridge() -> None:
    """Kiwoom WebSocket Bridge 종료"""
    global _kiwoom_ws_bridge

    if _kiwoom_ws_bridge:
        await _kiwoom_ws_bridge.stop()
        _kiwoom_ws_bridge = None
