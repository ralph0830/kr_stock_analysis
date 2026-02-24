"""
Signal Engine Service - FastAPI Main
종가베팅 V2 시그널 생성 엔진
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import date, datetime
import logging

from services.signal_engine.scorer import SignalScorer

logger = logging.getLogger(__name__)

# 전역 점수 계산기 인스턴스
_scorer: Optional[SignalScorer] = None


def get_scorer() -> SignalScorer:
    """Signal Scorer 싱글톤 반환"""
    global _scorer
    if _scorer is None:
        _scorer = SignalScorer()
    return _scorer


# ============================================================================
# DB 저장 함수
# ============================================================================

def save_jongga_signals_to_db(signals: List, signal_date: Optional[date] = None) -> int:
    """
    종가베팅 V2 시그널을 DB에 저장

    Args:
        signals: JonggaSignal 객체 리스트
        signal_date: 시그널 날짜 (기본: 오늘)

    Returns:
        저장된 시그널 수

    Raises:
        Exception: DB 저장 실패 시 (예외 재전파)
    """
    from src.database.session import get_db_session_sync
    from src.database.models import Signal
    from sqlalchemy import delete

    if signal_date is None:
        signal_date = date.today()

    saved_count = 0

    # Context Manager로 세션 관리 (리소스 누수 방지)
    with get_db_session_sync() as db:
        try:
            # 기존 JONGGA_V2 시그널 삭제 (갱신)
            db.execute(
                delete(Signal).where(
                    Signal.signal_type == "JONGGA_V2",
                    Signal.signal_date == signal_date
                )
            )

            # 새 시그널 저장
            for signal in signals:
                # ScoreDetail에서 개별 점수 추출
                score_obj = signal.score
                news_score = getattr(score_obj, 'news', 0)
                volume_score = getattr(score_obj, 'volume', 0)
                chart_score = getattr(score_obj, 'chart', 0)
                candle_score = getattr(score_obj, 'candle', 0)
                period_score = getattr(score_obj, 'period', 0)
                supply_score = getattr(score_obj, 'flow', 0)

                # Signal 레코드 생성
                db_signal = Signal(
                    ticker=signal.ticker,
                    signal_type="JONGGA_V2",
                    status="OPEN",
                    score=score_obj.total,
                    grade=signal.grade.value,
                    news_score=news_score,
                    volume_score=volume_score,
                    chart_score=chart_score,
                    candle_score=candle_score,
                    period_score=period_score,
                    supply_score=supply_score,
                    signal_date=signal_date,
                    entry_price=signal.entry_price,
                    target_price=signal.target_price,
                    stop_price=signal.stop_loss,
                )
                db.add(db_signal)
                saved_count += 1

            db.commit()
            logger.info(f"종가베팅 V2 시그널 {saved_count}개 DB 저장 완료")

        except Exception as e:
            db.rollback()
            logger.error(f"종가베팅 V2 시그널 DB 저장 실패: {e}", exc_info=True)
            raise  # 예외 재전파로 호출자가 실패를 인지하도록 함

    return saved_count


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
async def get_latest_signals(limit: int = 20):
    """
    최신 생성 시그널 조회 (DB에서 조회)

    Args:
        limit: 최대 반환 수

    Returns:
        최근 생성된 종가베팅 시그널 리스트
    """
    try:
        # DB에서 저장된 시그널 조회
        from src.database.session import get_db_session_sync
        from src.database.models import Signal
        from sqlalchemy import select, desc

        with get_db_session_sync() as db:
            # JONGGA_V2 시그널 조회 (최신 날짜순, 점수 높은 순)
            query = select(Signal).where(
                Signal.signal_type == "JONGGA_V2",
                Signal.status == "OPEN"
            ).order_by(
                desc(Signal.signal_date),
                desc(Signal.score)
            ).limit(limit)

            result = db.execute(query)
            signals = result.scalars().all()

            # Signal 엔티티를 딕셔너리로 변환
            signal_dicts = []
            for signal in signals:
                # 종목명 조회
                stock_name = signal.stock.name if signal.stock else signal.ticker

                # 점수 상세
                score_detail = {
                    "total": signal.score or 0,
                    "news": signal.news_score or 0,
                    "volume": signal.volume_score or 0,
                    "chart": signal.chart_score or 0,
                    "candle": signal.candle_score or 0,
                    "period": signal.period_score or 0,
                    "flow": signal.supply_score or 0,
                }

                signal_dict = {
                    "ticker": signal.ticker,
                    "name": stock_name,
                    "score": score_detail,
                    "grade": signal.grade or "C",
                    "entry_price": signal.entry_price,
                    "target_price": signal.target_price,
                    "stop_loss": signal.stop_price,
                    "signal_date": signal.signal_date.isoformat() if signal.signal_date else None,
                }
                signal_dicts.append(signal_dict)

            # 최신 시그널 날짜
            latest_date = None
            if signals:
                latest_date = signals[0].signal_date.isoformat()

            return {
                "signals": signal_dicts,
                "count": len(signal_dicts),
                "date": latest_date,
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
        from src.database.session import get_db_session_sync
        from src.database.models import Stock
        from sqlalchemy import select

        scorer = get_scorer()

        # 실제 종목 스캔 로직
        with get_db_session_sync() as db:
            # 시장 필터 적용
            query = select(Stock)
            if request.market != "ALL":
                query = query.where(Stock.market == request.market)

            # 일반주식만 필터 (ETF, SPAC, 관리종목 제외)
            query = query.where(
                Stock.is_etf == False,
                Stock.is_spac == False,
                Stock.is_admin == False,
            )

            # 거래대금 기준 정렬 (우량주 우선)
            query = query.order_by(Stock.market_cap.desc()).limit(request.top_n)

            result = db.execute(query)
            stocks = result.scalars().all()

        # 시그널 계산
        jongja_signals = []
        for stock in stocks:
            # 현재가는 최근 가격 데이터에서 가져올 수 있음
            # 여기서는 시가총액 기준으로 가격 추정
            estimated_price = int(stock.market_cap / 100000000) if stock.market_cap else 80000

            signal = scorer.calculate(stock.ticker, stock.name, estimated_price)
            if signal and signal.score.total >= 6:  # B급 이상만
                jongja_signals.append(signal)

        # DB 저장 (백그라운드 태스크)
        if jongja_signals:
            saved_count = save_jongga_signals_to_db(jongja_signals)
            logger.info(f"종가베팅 V2 시그널 {saved_count}개 DB 저장 완료")

        # 등급순 정렬
        grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        signal_dicts = [s.to_dict() for s in jongja_signals]
        signal_dicts.sort(key=lambda s: grade_order[s["grade"]])

        return {
            "signals": signal_dicts,
            "count": len(signal_dicts),
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
