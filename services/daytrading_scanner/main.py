"""
Daytrading Scanner Service - FastAPI Main
단타 매매 기회 포착 스캐닝 서비스

TDD Approach: Red-Green-Refactor Cycle
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from datetime import datetime

from services.daytrading_scanner.models.daytrading import ScanRequest, AnalyzeRequest

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Lifespan Context Manager
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("🚀 Daytrading Scanner Service Starting...")
    yield
    # Shutdown
    logger.info("🛑 Daytrading Scanner Service Shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Daytrading Scanner Service",
    description="단타 매매 기회 실시간 스캔닝 서비스 (모멘텀, 거래량 폭증)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Pydantic Validation Error 처리"""
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": 422,
            "detail": exc.errors(),
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP Exception 처리"""
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
    """일반 Exception 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "detail": str(exc),
        }
    )


# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="서비스 상태 확인"
)
async def health_check():
    """
    Health check endpoint

    Returns:
        HealthCheckResponse: 서비스 상태 정보
    """
    from services.daytrading_scanner.models.daytrading import HealthCheckResponse

    return HealthCheckResponse(
        status="healthy",
        service="daytrading-scanner",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    ).model_dump()


# =============================================================================
# API Endpoints (Phase 3에서 구현)
# =============================================================================

@app.post("/api/daytrading/scan")
async def scan_market(request: ScanRequest):
    """
    장중 단타 후보 종목 스캔

    실시간으로 단타 매매 기회가 있는 종목을 스캔합니다.
    """
    from services.daytrading_scanner.models.daytrading import ScanResponse, ScanResponseData, CandidateDataWithScore
    from services.daytrading_scanner.scanner import DaytradingScanner
    from services.daytrading_scanner.broadcaster import broadcast_daytrading_signals
    from src.database.session import get_db_session_sync

    # 실제 스캔 실행
    scanner = DaytradingScanner()

    with get_db_session_sync() as db:
        score_results = await scanner.scan_market(
            {"market": request.market, "limit": request.limit},
            db
        )

    # 점수 결과를 API 응답으로 변환
    candidates = []
    for result in score_results:
        # 현재가 조회 (없으면 0)
        current_price = 0
        change_rate = 0.0
        volume = 0
        avg_volume = 0
        volume_ratio = 0.0

        # 체크리스트에서 상위 4개 reasons 추출
        reasons = [
            check.name for check in result.checks
            if check.status == "passed"
        ][:4]

        candidates.append(CandidateDataWithScore(
            ticker=result.ticker,
            name=result.name,
            price=current_price,
            change_rate=change_rate,
            volume=volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            score=result.total_score,
            grade=result.grade
        ))

    # 브로드캐스트: 신호 업데이트 전송
    signals_data = [
        {
            "ticker": r.ticker,
            "name": r.name,
            "grade": r.grade,
            "total_score": r.total_score,
            "signal_type": "strong_buy" if r.total_score >= 80 else "buy" if r.total_score >= 60 else "watch",
            "entry_price": r.entry_price,
            "target_price": r.target_price,
            "stop_loss": r.stop_loss,
            "current_price": current_price,
            "checks": [
                {"name": c.name, "status": c.status, "points": c.points}
                for c in r.checks
            ]
        }
        for r in score_results
    ]

    # ConnectionManager 가져오기
    try:
        from src.websocket.server import connection_manager
        await broadcast_daytrading_signals(signals_data, connection_manager)
    except Exception as e:
        logger.warning(f"Failed to broadcast daytrading signals: {e}")

    data = ScanResponseData(
        candidates=candidates,
        scan_time=datetime.now().isoformat(),
        count=len(candidates)
    )

    return ScanResponse(
        success=True,
        data=data
    )


@app.get("/api/daytrading/signals")
async def get_signals(
    min_score: int = 0,
    market: str = None,
    limit: int = 50
):
    """
    활성 단타 매수 신호 조회

    Query Parameters:
    - min_score: 최소 점수 (0-105)
    - market: 시장 필터 (KOSPI/KOSDAQ)
    - limit: 최대 반환 개수 (1-100)
    """
    from services.daytrading_scanner.models.daytrading import (
        SignalsResponse, SignalsResponseData, DaytradingSignal, DaytradingCheck
    )
    from src.database.session import get_db_session_sync
    from src.repositories.daytrading_signal_repository import DaytradingSignalRepository
    from src.repositories.daily_price_repository import DailyPriceRepository

    try:
        # DB에서 시그널 조회
        with get_db_session_sync() as db:
            signal_repo = DaytradingSignalRepository(db)
            price_repo = DailyPriceRepository(db)

            # 필터에 따라 조회
            if min_score > 0 and market:
                # 점수와 시장 필터 모두 적용
                db_signals = (
                    db.query(signal_repo.model)
                    .filter_by(status="OPEN", market=market)
                    .filter(signal_repo.model.score >= min_score)
                    .order_by(signal_repo.model.score.desc())
                    .limit(limit)
                    .all()
                )
            elif min_score > 0:
                # 점수 필터만
                db_signals = signal_repo.get_by_min_score(min_score, limit)
            elif market:
                # 시장 필터만
                db_signals = signal_repo.get_by_market(market, limit)
            else:
                # 기본: 활성 시그널 조회
                db_signals = signal_repo.get_active_signals(limit)

            # DB 모델을 API 모델로 변환
            signals = []
            for db_signal in db_signals:
                # JSON checks를 DaytradingCheck 리스트로 변환
                checks_list = []
                if db_signal.checks:
                    for check_data in db_signal.checks:
                        checks_list.append(DaytradingCheck(
                            name=check_data.get("name", ""),
                            status=check_data.get("status", "failed"),
                            points=check_data.get("points", 0)
                        ))

                # 점수 기반 signal_type 결정
                if db_signal.score >= 80:
                    signal_type = "STRONG_BUY"
                elif db_signal.score >= 60:
                    signal_type = "BUY"
                else:
                    signal_type = "WATCH"

                # reasons 생성 (passed 체크리스트 이름)
                reasons = [
                    check.name for check in checks_list
                    if check.status == "passed"
                ][:4]  # 최대 4개

                # DB에서 최신 가격 조회 (실시간 가격 연동)
                latest_prices = price_repo.get_latest_by_ticker(db_signal.ticker, limit=1)
                current_price = latest_prices[0].close_price if latest_prices else None

                signals.append(DaytradingSignal(
                    ticker=db_signal.ticker,
                    name=db_signal.name,
                    market=db_signal.market,
                    score=db_signal.score,
                    grade=db_signal.grade,
                    checks=checks_list,
                    signal_type=signal_type,
                    current_price=current_price,  # 실시간 가격
                    entry_price=db_signal.entry_price,
                    target_price=db_signal.target_price,
                    stop_loss=db_signal.stop_loss,
                    reasons=reasons
                ))

            # 데이터가 없으면 빈 리스트 반환
            if not signals:
                logger.info(f"No daytrading signals found (min_score={min_score}, market={market})")
                signals = []

            data = SignalsResponseData(
                signals=signals,
                count=len(signals),
                generated_at=datetime.now().isoformat()
            )

            return SignalsResponse(
                success=True,
                data=data
            )

    except Exception as e:
        logger.error(f"Error fetching daytrading signals: {e}", exc_info=True)
        # 에러 발생 시 빈 결과 반환 (서비스 중단 방지)
        data = SignalsResponseData(
            signals=[],
            count=0,
            generated_at=datetime.now().isoformat()
        )
        return SignalsResponse(
            success=True,
            data=data
        )


@app.post("/api/daytrading/analyze")
async def analyze_stocks(request: AnalyzeRequest):
    """
    종목별 단타 점수 분석

    Request Body:
    - tickers: 분석할 종목 코드 리스트

    Returns 각 종목의 7개 체크리스트 점수와 등급
    """
    from services.daytrading_scanner.models.daytrading import (
        AnalyzeResponse, AnalyzeResponseData, AnalyzeResult, AnalyzeCheck
    )
    from src.database.session import get_db_session_sync
    from src.repositories.daytrading_signal_repository import DaytradingSignalRepository
    from src.repositories.stock_repository import StockRepository

    if not request.tickers:
        raise HTTPException(
            status_code=400,
            detail="tickers cannot be empty"
        )

    try:
        # DB에서 종목별 시그널 조회
        with get_db_session_sync() as db:
            signal_repo = DaytradingSignalRepository(db)
            stock_repo = StockRepository(db)

            results = []
            for ticker in request.tickers:
                # 종목 정보 조회
                stock = stock_repo.get_by_ticker(ticker)

                # 최신 시그널 조회
                db_signal = signal_repo.get_by_ticker(ticker)

                if db_signal:
                    # DB에 저장된 시그널이 있으면 사용
                    checks_list = []
                    if db_signal.checks:
                        for check_data in db_signal.checks:
                            checks_list.append(AnalyzeCheck(
                                name=check_data.get("name", ""),
                                status=check_data.get("status", "failed"),
                                points=check_data.get("points", 0)
                            ))

                    results.append(AnalyzeResult(
                        ticker=ticker,
                        name=db_signal.name,
                        score=db_signal.score,
                        grade=db_signal.grade,
                        checks=checks_list,
                        entry_price=db_signal.entry_price,
                        target_price=db_signal.target_price,
                        stop_loss=db_signal.stop_loss
                    ))
                else:
                    # DB에 시그널이 없으면 기본값 반환
                    name = stock.name if stock else f"종목_{ticker}"
                    results.append(AnalyzeResult(
                        ticker=ticker,
                        name=name,
                        score=0,
                        grade="C",
                        checks=[
                            AnalyzeCheck(name="거래량 폭증", status="failed", points=0),
                            AnalyzeCheck(name="모멘텀 돌파", status="failed", points=0),
                            AnalyzeCheck(name="박스권 탈출", status="failed", points=0),
                            AnalyzeCheck(name="5일선 위", status="failed", points=0),
                            AnalyzeCheck(name="기관 매수", status="failed", points=0),
                            AnalyzeCheck(name="낙폭 과대", status="failed", points=0),
                            AnalyzeCheck(name="섹터 모멘텀", status="failed", points=0),
                        ],
                        entry_price=None,
                        target_price=None,
                        stop_loss=None
                    ))

            data = AnalyzeResponseData(
                results=results,
                count=len(results),
                analyzed_at=datetime.now().isoformat()
            )

            return AnalyzeResponse(
                success=True,
                data=data
            )

    except Exception as e:
        logger.error(f"Error analyzing stocks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.daytrading_scanner.main:app",
        host="0.0.0.0",
        port=5115,
        reload=True
    )
