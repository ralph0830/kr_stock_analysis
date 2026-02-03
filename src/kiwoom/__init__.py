"""
키움증권 API 모듈

REST API와 WebSocket을 통한 실시간 데이터 수집 기능을 제공합니다.
"""

from src.kiwoom.base import (
    KiwoomConfig,
    KiwoomEventType,
    RealtimePrice,
    OrderBook,
    IKiwoomBridge,
)
from src.kiwoom.rest_api import (
    KiwoomRestAPI,
    KiwoomAPIError,
    TokenExpiredError,
    OrderResult,
)
from src.kiwoom.websocket import KiwoomWebSocket
from src.kiwoom.ohlc_collector import (
    OHLCCollector,
    OHLCCollectorConfig,
    OHLCBar,
    collect_ohlc_for_tickers,
    collect_ohlc_main,
)

__all__ = [
    # Base
    "KiwoomConfig",
    "KiwoomEventType",
    "RealtimePrice",
    "OrderBook",
    "IKiwoomBridge",
    # REST API
    "KiwoomRestAPI",
    "KiwoomAPIError",
    "TokenExpiredError",
    "OrderResult",
    # WebSocket
    "KiwoomWebSocket",
    # OHLC Collector
    "OHLCCollector",
    "OHLCCollectorConfig",
    "OHLCBar",
    "collect_ohlc_for_tickers",
    "collect_ohlc_main",
]
