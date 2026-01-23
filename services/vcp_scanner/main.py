"""
VCP Scanner Service - FastAPI Main
VCP (Volatility Contraction Pattern) 스캐닝 서비스
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import logging

from services.vcp_scanner.vcp_analyzer import VCPAnalyzer, VCPResult

logger = logging.getLogger(__name__)

# 전역 분석기 인스턴스
_analyzer: Optional[VCPAnalyzer] = None


def get_analyzer() -> VCPAnalyzer:
    """VCP Analyzer 싱글톤 반환"""
    global _analyzer
    if _analyzer is None:
        _analyzer = VCPAnalyzer()
    return _analyzer


# Lifespan 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("🚀 VCP Scanner Service Starting...")
    analyzer = get_analyzer()
    logger.info("✅ VCP Scanner ready")

    yield

    # Shutdown
    logger.info("🛑 VCP Scanner Service Shutting down...")


app = FastAPI(
    title="VCP Scanner Service",
    description="VCP Pattern Detection & SmartMoney Analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================================
# Request/Response Models
# ============================================================================


class ScanRequest(BaseModel):
    """스캔 요청 모델"""
    market: str = "KOSPI"
    top_n: int = 30


class ScanResponse(BaseModel):
    """스캔 응답 모델"""
    results: List[Dict[str, Any]]
    count: int
    scanned_at: Optional[str] = None


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": "vcp-scanner",
        "version": "1.0.0",
    }


# ============================================================================
# VCP Scanner Endpoints
# ============================================================================

@app.get("/signals")
async def get_signals(limit: int = 20):
    """
    활성 VCP 시그널 조회

    Returns:
        VCP 패턴이 감지된 종목 리스트
    """
    try:
        analyzer = get_analyzer()

        # TODO: Database에서 저장된 시그널 조회
        # 현재는 실시간 분석 결과 반환
        results = await analyzer.scan_market("KOSPI", top_n=limit)

        return {
            "signals": [r.to_dict() for r in results],
            "count": len(results),
            "timestamp": None,  # TODO: DB에서 조회 시 저장 시간 사용
        }

    except Exception as e:
        logger.error(f"시그널 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan", response_model=ScanResponse)
async def scan_vcp_patterns(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    VCP 패턴 스캔 실행

    Args:
        request: 스캔 요청 (market, top_n)
        background_tasks: 백그라운드 태스크

    Returns:
        스캔 결과
    """
    try:
        analyzer = get_analyzer()

        # 시장 스캔 실행
        results = await analyzer.scan_market(market=request.market, top_n=request.top_n)

        # TODO: 백그라운드 태스크로 DB 저장
        # background_tasks.add_task(save_signals_to_db, results)

        return ScanResponse(
            results=[r.to_dict() for r in results],
            count=len(results),
            scanned_at=None,  # TODO: 실제 스캔 시간 사용
        )

    except Exception as e:
        logger.error(f"VCP 스캔 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    """
    단일 종목 VCP 분석

    Args:
        ticker: 종목코드

    Returns:
        VCP 분석 결과
    """
    try:
        analyzer = get_analyzer()

        # TODO: 종목명 조회 (DB 또는 외부 API)
        name = f"Stock_{ticker}"

        result = await analyzer.analyze(ticker, name)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"종목을 찾을 수 없거나 분석 불가: {ticker}"
            )

        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 분석 실패 ({ticker}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "detail": exc.detail,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "detail": str(exc),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.vcp_scanner.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
