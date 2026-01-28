"""
Kiwoom WebSocket Bridge
Kiwoom Pipeline의 실시간 데이터를 WebSocket 클라이언트에게 전달합니다.
"""

import logging
from typing import Optional, Set, Dict, Any

from src.kiwoom.base import KiwoomEventType, RealtimePrice
from src.websocket.server import connection_manager


logger = logging.getLogger(__name__)


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

        self._pipeline = None
        self._active_tickers.clear()

        logger.info("KiwoomWebSocketBridge stopped")

    def _register_event_handlers(self) -> None:
        """Pipeline 이벤트 핸들러 등록"""
        if self._pipeline:
            self._pipeline.register_event_handler(
                KiwoomEventType.RECEIVE_REAL_DATA,
                self._on_realtime_data
            )
            logger.info("Registered KiwoomWebSocketBridge event handler for RECEIVE_REAL_DATA")
        else:
            logger.warning("Cannot register event handler: pipeline is None")

    async def _on_realtime_data(self, price: RealtimePrice) -> None:
        """
        실시간 데이터 수신 시 처리

        Args:
            price: 실시간 가격 데이터
        """
        if not self._running:
            logger.warning(f"KiwoomWebSocketBridge not running, ignoring price data for {price.ticker}")
            return

        ticker = price.ticker

        # 구독 중인 종목인지 확인
        if ticker not in self._active_tickers:
            logger.debug(f"Ticker {ticker} not in active_tickers: {self._active_tickers}")
            return

        # WebSocket으로 브로드캐스트
        try:
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
                    },
                topic=f"price:{ticker}",
            )
            logger.info(f"Broadcasted price update for {ticker}: {price.price}")
        except Exception as e:
            logger.error(f"Failed to broadcast price update: {e}")

    async def add_ticker(self, ticker: str) -> bool:
        """
        종목 구독 추가

        Args:
            ticker: 종목코드

        Returns:
            성공 여부
        """
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
        self._active_tickers.discard(ticker)
        logger.info(f"Removed ticker from KiwoomWebSocketBridge: {ticker}")
        return True

    def get_active_tickers(self) -> Set[str]:
        """활성 종목 목록 반환"""
        return self._active_tickers.copy()

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._running


# 전역 인스턴스
_kiwoom_ws_bridge: Optional[KiwoomWebSocketBridge] = None


def get_kiwoom_ws_bridge() -> Optional[KiwoomWebSocketBridge]:
    """Kiwoom WebSocket Bridge 전역 인스턴스 가져오기"""
    return _kiwoom_ws_bridge


async def init_kiwoom_ws_bridge(pipeline: Any) -> KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket Bridge 초기화 및 시작

    Args:
        pipeline: KiwoomPipelineManager 인스턴스

    Returns:
        KiwoomWebSocketBridge 인스턴스
    """
    global _kiwoom_ws_bridge

    if _kiwoom_ws_bridge is None:
        _kiwoom_ws_bridge = KiwoomWebSocketBridge()

    await _kiwoom_ws_bridge.start(pipeline)
    return _kiwoom_ws_bridge


async def shutdown_kiwoom_ws_bridge() -> None:
    """Kiwoom WebSocket Bridge 종료"""
    global _kiwoom_ws_bridge

    if _kiwoom_ws_bridge:
        await _kiwoom_ws_bridge.stop()
        _kiwoom_ws_bridge = None
