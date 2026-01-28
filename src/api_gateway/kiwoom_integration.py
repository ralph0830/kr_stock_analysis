"""
API Gateway Kiwoom 연동 구현

Kiwoom REST API를 API Gateway에 통합합니다.
"""

import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.kiwoom.base import KiwoomConfig
from src.kiwoom.pipeline import KiwoomPipelineManager


logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================

class SubscribeRequest(BaseModel):
    """종목 구독 요청"""
    ticker: str = Field(..., min_length=6, max_length=6, description="종목코드 (6자리)")


class SubscribeResponse(BaseModel):
    """종목 구독 응답"""
    success: bool
    message: str
    ticker: Optional[str] = None


class UnsubscribeRequest(BaseModel):
    """종목 구독 해제 요청"""
    ticker: str = Field(..., min_length=6, max_length=6, description="종목코드 (6자리)")


class HealthResponse(BaseModel):
    """Health Check 응답"""
    status: str
    connected: bool
    has_token: bool
    subscribed_count: int


class SubscriptionsResponse(BaseModel):
    """구독 목록 응답"""
    tickers: list[str]
    count: int


class PriceResponse(BaseModel):
    """실시간 가격 응답"""
    ticker: str
    price: float
    change: float
    change_rate: float
    volume: int
    bid_price: float
    ask_price: float
    timestamp: str


# ==================== Kiwoom Integration Manager ====================

class KiwoomIntegration:
    """
    Kiwoom 연동 관리자

    API Gateway의 lifespan 이벤트에서 사용됩니다.
    """

    def __init__(self, config: Optional[KiwoomConfig] = None):
        """
        초기화

        Args:
            config: Kiwoom 설정 (None인 경우 환경변수에서 로드)
        """
        if config is None:
            config = self._load_config_from_env()

        self._config = config
        self._pipeline: Optional[KiwoomPipelineManager] = None

    def _load_config_from_env(self) -> Optional[KiwoomConfig]:
        """환경변수에서 설정 로드 (실전 트레이딩만 지원)"""
        import os

        # Kiwoom REST 모드 확인
        use_rest = os.getenv("USE_KIWOOM_REST", "true").lower() == "true"

        if not use_rest:
            return None

        # 실전 API 키 로드
        app_key = os.getenv("KIWOOM_APP_KEY", "")
        secret_key = os.getenv("KIWOOM_SECRET_KEY", "")
        base_url = os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com")
        ws_url = os.getenv("KIWOOM_WS_URL", "wss://api.kiwoom.com:10000/api/dostk/websocket")

        if not app_key or not secret_key:
            logger.warning("Kiwoom API keys not configured")
            return None

        logger.info(f"Using Kiwoom Real Trading API at {base_url}")

        return KiwoomConfig(
            app_key=app_key,
            secret_key=secret_key,
            base_url=base_url,
            ws_url=ws_url,
            use_mock=False,  # 항상 실전 모드
        )

    async def startup(self) -> None:
        """시작 시 Pipeline 생성 및 시작"""
        if self._config is None:
            logger.info("Kiwoom REST API disabled")
            return

        self._pipeline = KiwoomPipelineManager(self._config, auto_start=True)
        logger.info("Kiwoom Pipeline started")

    async def shutdown(self) -> None:
        """종료 시 Pipeline 중지"""
        if self._pipeline is not None:
            await self._pipeline.stop()
            logger.info("Kiwoom Pipeline stopped")

    @property
    def pipeline(self) -> Optional[KiwoomPipelineManager]:
        """Pipeline 인스턴스"""
        return self._pipeline


# 전역 인스턴스
_kiwoom_integration: Optional[KiwoomIntegration] = None


def get_kiwoom_integration() -> Optional[KiwoomIntegration]:
    """Kiwoom 연동 인스턴스 가져오기"""
    return _kiwoom_integration


def create_kiwoom_integration() -> KiwoomIntegration:
    """Kiwoom 연동 인스턴스 생성"""
    global _kiwoom_integration
    _kiwoom_integration = KiwoomIntegration()
    return _kiwoom_integration


# ==================== Route Setup ====================

def setup_kiwoom_routes(
    app: FastAPI,
    pipeline: Optional[KiwoomPipelineManager] = None,
    ws_bridge: Optional[Any] = None,
) -> None:
    """
    Kiwoom 관련 라우트 설정

    Args:
        app: FastAPI 앱 인스턴스
        pipeline: Kiwoom Pipeline (테스트용)
        ws_bridge: Kiwoom WebSocket Bridge (실시간 데이터 브로드캐스트용)
    """
    if pipeline is None:
        # 전역 인스턴스 사용
        integration = get_kiwoom_integration()
        pipeline = integration.pipeline if integration else None

    if pipeline is None:
        logger.warning("Kiwoom Pipeline not available, routes will return errors")
        return

    # WebSocket Bridge가 없으면 전역 인스턴스 사용
    if ws_bridge is None:
        from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
        ws_bridge = get_kiwoom_ws_bridge()

    @app.get("/api/kr/kiwoom/health", response_model=HealthResponse, tags=["kiwoom"])
    async def get_kiwoom_health():
        """Kiwoom Health Check"""
        health = pipeline.health_check()
        return HealthResponse(**health)

    @app.get("/api/kr/kiwoom/subscriptions", response_model=SubscriptionsResponse, tags=["kiwoom"])
    async def get_kiwoom_subscriptions():
        """구독 중인 종목 목록"""
        tickers = pipeline.get_subscribed_tickers()
        return SubscriptionsResponse(tickers=tickers, count=len(tickers))

    @app.post("/api/kr/kiwoom/subscribe", response_model=SubscribeResponse, tags=["kiwoom"])
    async def subscribe_ticker(request: SubscribeRequest):
        """종목 구독"""
        if not pipeline.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        # Pipeline 구독
        pipeline_success = await pipeline.subscribe(request.ticker)

        # WebSocket Bridge에도 종목 추가 (실시간 브로드캐스트용)
        bridge_success = True
        if ws_bridge and ws_bridge.is_running():
            bridge_success = await ws_bridge.add_ticker(request.ticker)
            logger.info(f"Added ticker {request.ticker} to WebSocket Bridge")

        if pipeline_success and bridge_success:
            return SubscribeResponse(
                success=True,
                message=f"Subscribed to {request.ticker}",
                ticker=request.ticker,
            )
        else:
            return SubscribeResponse(
                success=False,
                message=f"Failed to subscribe to {request.ticker}",
                ticker=request.ticker,
            )

    @app.post("/api/kr/kiwoom/unsubscribe", response_model=SubscribeResponse, tags=["kiwoom"])
    async def unsubscribe_ticker(request: UnsubscribeRequest):
        """종목 구독 해제"""
        if not pipeline.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        # Pipeline 구독 해제
        pipeline_success = await pipeline.unsubscribe(request.ticker)

        # WebSocket Bridge에서도 종목 제거
        if ws_bridge and ws_bridge.is_running():
            await ws_bridge.remove_ticker(request.ticker)
            logger.info(f"Removed ticker {request.ticker} from WebSocket Bridge")

        if pipeline_success:
            return SubscribeResponse(
                success=True,
                message=f"Unsubscribed from {request.ticker}",
                ticker=request.ticker,
            )
        else:
            return SubscribeResponse(
                success=False,
                message=f"Failed to unsubscribe from {request.ticker}",
                ticker=request.ticker,
            )

    @app.get("/api/kr/kiwoom/prices", tags=["kiwoom"])
    async def get_realtime_prices():
        """구독 중인 종목의 실시간 가격 목록"""
        if not pipeline.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        tickers = pipeline.get_subscribed_tickers()
        return {"tickers": tickers, "count": len(tickers)}

    @app.get("/api/kr/kiwoom/prices/{ticker}", response_model=PriceResponse, tags=["kiwoom"])
    async def get_realtime_price(ticker: str):
        """특정 종목의 실시간 가격"""
        if not pipeline.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        # Bridge에서 현재가 조회
        price = await pipeline._bridge.get_current_price(ticker)

        if price is None:
            raise HTTPException(status_code=404, detail=f"Price not found for {ticker}")

        return PriceResponse(
            ticker=price.ticker,
            price=price.price,
            change=price.change,
            change_rate=price.change_rate,
            volume=price.volume,
            bid_price=price.bid_price,
            ask_price=price.ask_price,
            timestamp=price.timestamp,
        )


# ==================== Helper Functions ====================

def get_kiwoom_config() -> Optional[KiwoomConfig]:
    """환경변수에서 Kiwoom 설정 가져오기"""
    integration = KiwoomIntegration()
    return integration._config
