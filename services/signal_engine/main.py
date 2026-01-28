"""
Signal Engine Service - FastAPI Main
종가베팅 V2 시그널 생성 엔진
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import logging

from services.signal_engine.scorer import SignalScorer, JonggaSignal

logger = logging.getLogger(__name__)

# 전역 점수 계산기 인스턴스
_scorer: Optional[SignalScorer] = None


def get_scorer() -> SignalScorer:
    """Signal Scorer 싱글톤 반환"""
    global _scorer
    if _scorer is None:
        _scorer = SignalScorer()
    return _scorer


# Lifespan 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("🚀 Signal Engine Service Starting...")
    scorer = get_scorer()
    logger.info("✅ Signal Engine ready")

    yield

    # Shutdown
    logger.info("🛑 Signal Engine Service Shutting down...")


app = FastAPI(
    title="Signal Engine Service",
    description="종가베팅 V2 시그널 생성 엔진",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================================
# Request/Response Models
# ============================================================================


class GenerateRequest(BaseModel):
    """시그널 생성 요청"""
    market: str = "KOSPI"
    top_n: int = 30
    capital: int = 10_000_000  # 1000만원


class AnalyzeRequest(BaseModel):
    """단일 종목 분석 요청"""
    ticker: str
    name: str
    price: int


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": "signal-engine",
        "version": "2.0.0",
    }


# ============================================================================
# Signal Engine Endpoints
# ============================================================================

@app.get("/signals/latest")
async def get_latest_signals():
    """
    최신 생성 시그널 조회

    Returns:
        최근 생성된 종가베팅 시그널 리스트
    """
    try:
        scorer = get_scorer()

        # TODO: Database에서 저장된 시그널 조회
        # 현재는 mock 데이터 생성
        mock_signals = []
        for ticker, name in [("005930", "삼성전자"), ("000660", "SK하이닉스")]:
            signal = scorer.calculate(ticker, name, 80000)
            if signal and signal.score.total >= 6:
                mock_signals.append(signal.to_dict())

        return {
            "signals": mock_signals,
            "count": len(mock_signals),
            "date": None,  # TODO: DB에서 조회 시 생성 날짜 사용
        }

    except Exception as e:
        logger.error(f"시그널 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate_signals(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    시그널 생성 실행

    Args:
        request: 생성 요청 (market, top_n, capital)
        background_tasks: 백그라운드 태스크

    Returns:
        생성된 시그널 리스트
    """
    try:
        scorer = get_scorer()

        # TODO: 실제 종목 스캔 로직
        # 현재는 mock 데이터
        mock_stocks = [
            ("005930", "삼성전자", 80000),
            ("000660", "SK하이닉스", 180000),
            ("035420", "NAVER", 250000),
        ][:request.top_n]

        signals = []
        for ticker, name, price in mock_stocks:
            signal = scorer.calculate(ticker, name, price)
            if signal and signal.score.total >= 6:  # B급 이상만
                signals.append(signal.to_dict())

        # TODO: 백그라운드 태스크로 DB 저장
        # background_tasks.add_task(save_signals_to_db, signals)

        # 등급순 정렬
        grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        signals.sort(key=lambda s: grade_order[s["grade"]])

        return {
            "signals": signals,
            "count": len(signals),
            "capital": request.capital,
        }

    except Exception as e:
        logger.error(f"시그널 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_stock(request: AnalyzeRequest):
    """
    단일 종목 시그널 분석

    Args:
        request: 종목 분석 요청

    Returns:
        종가베팅 시그널
    """
    try:
        scorer = get_scorer()

        signal = scorer.calculate(request.ticker, request.name, request.price)

        if not signal:
            raise HTTPException(
                status_code=404,
                detail=f"종목 분석 실패: {request.ticker}"
            )

        return signal.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 분석 실패 ({request.ticker}): {e}")
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
        "services.signal_engine.main:app",
        host="0.0.0.0",
        port=5113,
        reload=True,
    )
