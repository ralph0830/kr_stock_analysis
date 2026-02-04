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
from datetime import date

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 독립 실행을 위한 유연한 import
import sys
import os

# 현재 파일의 디렉토리를 sys.path에 추가
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

try:
    # Docker/독립 실행: 현재 디렉토리에서 import
    from vcp_analyzer import VCPAnalyzer
except ImportError:
    # 프로젝트 루트 실행
    try:
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer
    except ImportError:
        # 다른 방법 시도
        import importlib.util
        spec = importlib.util.spec_from_file_location("vcp_analyzer", os.path.join(_current_dir, "vcp_analyzer.py"))
        vcp_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vcp_module)
        VCPAnalyzer = vcp_module.VCPAnalyzer

try:
    from ralph_stock_lib.database.session import get_db_session
    from ralph_stock_lib.database.models import Signal
except ImportError:
    # lib 패키지가 설치되지 않은 경우 (프로젝트 루트 실행)
    from src.database.session import get_db_session
    from src.database.models import Signal
from sqlalchemy import delete

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
    min_score: float = 0.0  # 최소 VCP 점수 필터


class ScanResponse(BaseModel):
    """스캔 응답 모델"""
    results: List[Dict[str, Any]]
    count: int
    scanned_at: Optional[str] = None
    saved: bool = False  # DB 저장 여부


# ============================================================================
# Database Save Function
# ============================================================================


def _get_grade_from_score(total_score: float) -> str:
    """점수에 따른 등급 반환"""
    if total_score >= 80:
        return "S"
    elif total_score >= 65:
        return "A"
    elif total_score >= 50:
        return "B"
    return "C"


def _broadcast_signal_update(results: List[Any]) -> None:
    """
    VCP 시그널 업데이트를 WebSocket으로 브로드캐스트

    Args:
        results: VCPAnalyzer 결과 리스트
    """
    try:
        import asyncio

        # 이미 실행 중인 이벤트 루프가 있는지 확인
        try:
            loop = asyncio.get_running_loop()
            # 이벤트 루프가 실행 중이면 create_task 사용
            asyncio.create_task(_do_broadcast(results))
        except RuntimeError:
            # 실행 중인 이벤트 루프가 없으면 새로 생성
            asyncio.run(_do_broadcast(results))

    except Exception as e:
        logging.warning(f"WebSocket 브로드캐스트 실패 (무시): {e}")


async def _do_broadcast(results: List[Any]) -> None:
    """
    비동기 브로드캐스트 실행

    Args:
        results: VCPAnalyzer 결과 리스트
    """
    try:
        from src.websocket.server import signal_broadcaster
        await signal_broadcaster.broadcast_signal_update(results, signal_type="VCP")
        logging.info(f"VCP 시그널 {len(results)}개 WebSocket 브로드캐스트 완료")
    except Exception as e:
        logging.warning(f"WebSocket 브로드캐스트 중 오류 (무시): {e}")


def save_vcp_signals_to_db(results: List[Any], signal_date: Optional[date] = None) -> int:
    """
    VCP 스캔 결과를 DB에 저장

    Args:
        results: VCPAnalyzer 결과 리스트
        signal_date: 시그널 날짜 (없으면 오늘)

    Returns:
        저장된 시그널 수
    """
    if not results:
        return 0

    if signal_date is None:
        signal_date = date.today()

    saved_count = 0

    # 세션 관리 표준화: get_db_session_sync 사용
    from src.database.session import get_db_session_sync

    with get_db_session_sync() as db:
        try:
            # 기존 VCP 시그널 삭제 (갱신)
            db.execute(
                delete(Signal).where(
                    Signal.signal_type == "VCP",
                    Signal.signal_date == signal_date
                )
            )

            # 새 시그널 저장
            for result in results:
                # total_score 기반 등급 계산
                grade = _get_grade_from_score(result.total_score)

                # Signal 레코드 생성
                signal = Signal(
                    ticker=result.ticker,
                    signal_type="VCP",
                    status="OPEN",
                    score=result.total_score,
                    grade=grade,
                    contraction_ratio=result.vcp_score / 100 if result.vcp_score else None,
                    signal_date=signal_date,
                    entry_price=int(result.current_price) if result.current_price else None,
                    foreign_net_5d=result.foreign_net_5d or 0,
                    inst_net_5d=result.inst_net_5d or 0,
                )
                db.add(signal)
                saved_count += 1

            db.commit()
            logging.info(f"VCP 시그널 {saved_count}개 DB 저장 완료")

            # WebSocket 브로드캐스트 (실시간 업데이트)
            _broadcast_signal_update(results)

        except Exception as e:
            db.rollback()
            logging.error(f"VCP 시그널 DB 저장 실패: {e}")
            raise

    return saved_count


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
# Helper Functions
# ============================================================================

VALID_MARKETS = ["KOSPI", "KOSDAQ", "ALL"]


def _validate_market(market: str) -> str:
    """시장 값 검증 및 대문자 변환"""
    market_upper = market.upper()
    if market_upper not in VALID_MARKETS:
        raise HTTPException(
            status_code=422,
            detail=f"유효하지 않은 market 값입니다: {market}. (KOSPI/KOSDAQ/ALL)"
        )
    return market_upper


def _signal_to_dict(signal) -> dict:
    """
    Signal 엔티티를 API 응답 딕셔너리로 변환

    Args:
        signal: Signal ORM 객체

    Returns:
        API 응답용 딕셔너리
    """
    # 종목명 조회
    stock_name = signal.stock.name if signal.stock else signal.ticker

    return {
        "ticker": signal.ticker,
        "name": stock_name,
        "total_score": signal.score or 0,
        "vcp_score": (signal.contraction_ratio * 100) if signal.contraction_ratio else 0,
        "current_price": signal.entry_price,
        "foreign_net_5d": signal.foreign_net_5d or 0,
        "inst_net_5d": signal.inst_net_5d or 0,
        "signal_date": signal.signal_date.isoformat() if signal.signal_date else None,
    }


# ============================================================================
# VCP Scanner Endpoints
# ============================================================================

@app.get("/signals")
async def get_signals(limit: int = 20, market: str = "ALL"):
    """
    활성 VCP 시그널 조회 (DB에서 조회)

    Args:
        limit: 최대 반환 개수
        market: 시장 필터 (KOSPI, KOSDAQ, ALL)

    Returns:
        VCP 패턴이 감지된 종목 리스트
    """
    try:
        # DB에서 저장된 시그널 조회
        from src.repositories.vcp_signal_repository import VCPSignalRepository
        from src.database.session import get_db_session_sync

        # 시장 값 검증
        market = _validate_market(market)

        with get_db_session_sync() as db:
            repo = VCPSignalRepository(db)

            # 시장 필터 적용
            if market == "ALL":
                signals = repo.get_active_vcp_signals(limit=limit)
            else:  # KOSPI or KOSDAQ
                signals = repo.get_vcp_signals_by_market(market=market, limit=limit)

            # Signal 엔티티를 딕셔너리로 변환
            signal_dicts = [_signal_to_dict(signal) for signal in signals]

            # 최신 시그널의 생성 시간
            timestamp = None
            if signals and signals[0].created_at:
                timestamp = signals[0].created_at.isoformat()

            return {
                "signals": signal_dicts,
                "count": len(signal_dicts),
                "timestamp": timestamp,
            }

    except HTTPException:
        raise
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
        results = await analyzer.scan_market(
            market=request.market,
            top_n=request.top_n,
            min_score=request.min_score
        )

        # DB 저장
        saved_count = 0
        try:
            saved_count = save_vcp_signals_to_db(results)
        except Exception as db_error:
            logger.warning(f"DB 저장 실패 (스캔 결과는 반환): {db_error}")

        from datetime import datetime
        return ScanResponse(
            results=[r.to_dict() for r in results],
            count=len(results),
            scanned_at=datetime.now().isoformat(),
            saved=saved_count > 0,
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
        port=5112,
        reload=True,
    )
