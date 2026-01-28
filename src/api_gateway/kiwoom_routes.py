"""
API Gateway Kiwoom 라우트 설정

Kiwoom REST API 관련 엔드포인트를 정의합니다.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.kiwoom.pipeline import KiwoomPipelineManager
from src.api_gateway.kiwoom_integration import get_kiwoom_integration


# ==================== Request/Response Models ====================

class SubscribeRequest(BaseModel):
    """종목 구독 요청"""
    ticker: str = Field(..., min_length=6, max_length=6, description="종목코드 (6자리)")


class SubscribeResponse(BaseModel):
    """종목 구독 응답"""
    success: bool
    message: str
    ticker: str | None = None


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


class ChartResponse(BaseModel):
    """차트 데이터 응답"""
    ticker: str
    period_days: int
    data: list[dict]
    total_points: int


class InvestorChartRequest(BaseModel):
    """투자자별 차트 요청"""
    ticker: str = Field(..., min_length=6, max_length=6, description="종목코드 (6자리)")
    date: str = Field(..., description="조회일자 (YYYYMMDD)")
    amt_qty_tp: str = Field(default="1", description="금액/수량 구분 (1:금액, 2:수량)")
    trde_tp: str = Field(default="0", description="거래구분 (0:순매수, 1:매수, 2:매도)")
    unit_tp: str = Field(default="1000", description="단위구분 (1000:천주, 1:단주)")


# ==================== Helper Functions ====================

def _get_pipeline() -> Optional[KiwoomPipelineManager]:
    """전역 Kiwoom Integration에서 Pipeline 가져오기"""
    integration = get_kiwoom_integration()
    if integration and integration.pipeline:
        return integration.pipeline
    return None


def _get_ws_bridge():
    """전역 Kiwoom WebSocket Bridge 가져오기"""
    from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
    return get_kiwoom_ws_bridge()


# ==================== Route Setup ====================

def setup_kiwoom_routes(
    app: FastAPI,
    pipeline: Optional[KiwoomPipelineManager] = None,
) -> None:
    """
    Kiwoom 관련 라우트 설정

    Args:
        app: FastAPI 앱 인스턴스
        pipeline: Kiwoom Pipeline Manager (可选, 없으면 전역 인스턴스 사용)
    """
    import logging
    logger = logging.getLogger(__name__)

    @app.get("/api/kr/kiwoom/health-debug", tags=["kiwoom"])
    async def get_kiwoom_health_debug():
        """Kiwoom Health Check with Debug Info"""
        pipe = pipeline or _get_pipeline()
        ws_bridge = _get_ws_bridge()

        debug_info = {
            "pipeline": "available" if pipe else "None",
            "pipeline_running": pipe.is_running() if pipe else False,
            "ws_bridge": "available" if ws_bridge else "None",
            "ws_bridge_running": ws_bridge.is_running() if ws_bridge else False,
            "ws_bridge_active_tickers": list(ws_bridge.get_active_tickers()) if ws_bridge else [],
        }

        return debug_info

    @app.get("/api/kr/kiwoom/subscriptions", response_model=SubscriptionsResponse, tags=["kiwoom"])
    async def get_kiwoom_subscriptions():
        """구독 중인 종목 목록"""
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")
        tickers = pipe.get_subscribed_tickers()
        return SubscriptionsResponse(tickers=tickers, count=len(tickers))

    @app.post("/api/kr/kiwoom/subscribe", response_model=SubscribeResponse, tags=["kiwoom"])
    async def subscribe_ticker(request: SubscribeRequest):
        """종목 구독"""
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")
        if not pipe.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        # Pipeline 구독
        pipeline_success = await pipe.subscribe(request.ticker)

        # WebSocket Bridge에도 종목 추가 (실시간 브로드캐스트용)
        ws_bridge = _get_ws_bridge()
        logger.info(f"WebSocket Bridge: {ws_bridge}, is_running: {ws_bridge.is_running() if ws_bridge else None}")
        if ws_bridge and ws_bridge.is_running():
            await ws_bridge.add_ticker(request.ticker)
            logger.info(f"Added ticker {request.ticker} to WebSocket Bridge")
        else:
            logger.warning(f"WebSocket Bridge not available for ticker {request.ticker}")

        if pipeline_success:
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
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")
        if not pipe.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        # Pipeline 구독 해제
        pipeline_success = await pipe.unsubscribe(request.ticker)

        # WebSocket Bridge에서도 종목 제거
        ws_bridge = _get_ws_bridge()
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
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")
        if not pipe.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        tickers = pipe.get_subscribed_tickers()
        return {"tickers": tickers, "count": len(tickers)}

    @app.get("/api/kr/kiwoom/prices/{ticker}", response_model=PriceResponse, tags=["kiwoom"])
    async def get_realtime_price(ticker: str):
        """특정 종목의 실시간 가격"""
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")
        if not pipe.is_running():
            raise HTTPException(status_code=503, detail="Kiwoom Pipeline not running")

        # Bridge에서 현재가 조회
        price = await pipe._bridge.get_current_price(ticker)

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

    @app.get("/api/kr/kiwoom/chart/{ticker}", response_model=ChartResponse, tags=["kiwoom"])
    async def get_kiwoom_chart(ticker: str, days: int = Query(default=30, ge=1, le=365, description="조회 일수")):
        """
        Kiwoom API에서 종목 차트 데이터 조회

        Kiwoom REST API의 투자자별 차트 데이터를 조회하여 반환합니다.
        """
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")

        # Pipeline의 Service에서 REST API 클라이언트 가져오기
        if not hasattr(pipe, "_service") or pipe._service is None:
            raise HTTPException(status_code=503, detail="Kiwoom Service not available")

        service = pipe._service
        rest_api = service.rest_api
        if rest_api is None:
            raise HTTPException(status_code=503, detail="Kiwoom REST API not available")

        # 일별 가격 데이터 조회
        price_data = await rest_api.get_daily_prices(ticker, days)

        if price_data is None:
            raise HTTPException(status_code=404, detail=f"Chart data not found for {ticker}")

        return ChartResponse(
            ticker=ticker,
            period_days=days,
            data=price_data,
            total_points=len(price_data),
        )

    @app.post("/api/kr/kiwoom/chart/investor", tags=["kiwoom"])
    async def get_investor_chart(request: InvestorChartRequest):
        """
        특정일자 투자자별 차트 데이터 조회

        Kiwoom REST API ka10060 TR을 사용하여 특정일자의 투자자별 수급 데이터를 조회합니다.
        """
        pipe = pipeline or _get_pipeline()
        if pipe is None:
            raise HTTPException(status_code=503, detail="Kiwoom integration not available")

        # Pipeline의 Service에서 REST API 클라이언트 가져오기
        if not hasattr(pipe, "_service") or pipe._service is None:
            raise HTTPException(status_code=503, detail="Kiwoom Service not available")

        service = pipe._service
        rest_api = service.rest_api
        if rest_api is None:
            raise HTTPException(status_code=503, detail="Kiwoom REST API not available")

        # 투자자별 차트 데이터 조회
        chart_result = await rest_api.get_investor_chart(
            ticker=request.ticker,
            date=request.date,
            amt_qty_tp=request.amt_qty_tp,
            trde_tp=request.trde_tp,
            unit_tp=request.unit_tp,
        )

        if chart_result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Investor chart data not found for {request.ticker} on {request.date}"
            )

        return chart_result
