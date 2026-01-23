"""
KR Stock - API Gateway
FastAPI 기반 API Gateway 구현
"""

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import httpx

from services.api_gateway.service_registry import ServiceRegistry, get_registry


# Lifespan 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    print("🚀 API Gateway Starting...")
    print("📡 Registering services...")
    registry = get_registry()
    print(f"✅ Registered {len(registry.list_services())} services")

    yield

    # Shutdown
    print("🛑 API Gateway Shutting down...")


app = FastAPI(
    title="KR Stock API Gateway",
    description="Open Architecture based Korean Stock Analysis System",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """API Gateway 헬스 체크"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "2.0.0",
    }


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "KR Stock API Gateway",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
    }


# ============================================================================
# KR Market Routes (Proxy to VCP Scanner)
# ============================================================================

@app.get("/api/kr/signals")
async def get_kr_signals(limit: int = 20):
    """
    활성 VCP 시그널 조회

    VCP Scanner 서비스로 프록시하여 시그널 목록 반환
    """
    registry = get_registry()

    # VCP Scanner 서비스 조회
    vcp_scanner = registry.get_service("vcp-scanner")
    if not vcp_scanner:
        raise HTTPException(
            status_code=503,
            detail="VCP Scanner service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{vcp_scanner['url']}/signals",
                params={"limit": limit},
                timeout=10.0,
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"VCP Scanner error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"VCP Scanner unavailable: {str(e)}",
            )


@app.get("/api/kr/market-gate")
async def get_kr_market_gate():
    """
    Market Gate 상태 조회

    Market Analyzer 서비스로 프록시하여 상태 반환
    """
    registry = get_registry()

    # Market Analyzer 서비스 조회
    market_analyzer = registry.get_service("market-analyzer")
    if not market_analyzer:
        raise HTTPException(
            status_code=503,
            detail="Market Analyzer service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{market_analyzer['url']}/market-gate",
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Market Analyzer error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Market Analyzer unavailable: {str(e)}",
            )


@app.get("/api/kr/jongga-v2/latest")
async def get_jongga_v2_latest():
    """
    최신 종가베팅 V2 시그널 조회

    Signal Engine 서비스로 프록시
    """
    registry = get_registry()

    # Signal Engine 서비스 조회
    signal_engine = registry.get_service("signal-engine")
    if not signal_engine:
        raise HTTPException(
            status_code=503,
            detail="Signal Engine service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{signal_engine['url']}/signals/latest",
                timeout=15.0,  # AI 분석이 포함되어 시간 더 소요
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Signal Engine error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Signal Engine unavailable: {str(e)}",
            )


# ============================================================================
# Fallback Routes (Flask legacy) - 이전 단계 호환성용
# ============================================================================


class RealtimePricesRequest(BaseModel):
    """실시간 가격 요청 모델"""
    tickers: list[str] = []


@app.post("/api/kr/realtime-prices")
async def get_kr_realtime_prices(request: RealtimePricesRequest):
    """
    실시간 가격 일괄 조회 (이전 Flask 라우팅 호환)
    """
    tickers = request.tickers

    # TODO: Price Service 또는 Data Collector로 프록시
    return {"prices": {}}


@app.get("/api/kr/stock-chart/{ticker}")
async def get_kr_stock_chart(ticker: str, period: str = "6mo"):
    """
    종목 차트 데이터 조회
    """
    # TODO: Data Service 또는 VCP Scanner로 프록시
    return {"ticker": ticker, "data": []}


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "detail": str(exc),
            "path": str(request.url.path),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.api_gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
