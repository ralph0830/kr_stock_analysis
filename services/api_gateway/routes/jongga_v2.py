"""
종가베팅 V2 API Routes
종가베팅 V2 시그널 생성 및 조회 API 엔드포인트
"""

import logging
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.repositories.signal_repository import SignalRepository
from src.database.models import Signal

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/kr/jongga-v2",
    tags=["jongga-v2"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class JonggaV2RunRequest(BaseModel):
    """종가베팅 V2 엔진 실행 요청"""
    market: str = Field(
        default="KOSPI",
        description="시장 (KOSPI/KOSDAQ/ALL)"
    )
    top_n: int = Field(
        default=30,
        ge=1,
        le=100,
        description="상위 N개 종목"
    )
    min_score: int = Field(
        default=6,
        ge=0,
        le=12,
        description="최소 점수 (0-12)"
    )
    background: bool = Field(
        default=False,
        description="백그라운드 실행 여부"
    )
    capital: int = Field(
        default=10_000_000,
        description="투자 자본 (원)"
    )


class JonggaV2RunResponse(BaseModel):
    """종가베팅 V2 엔진 실행 응답"""
    status: str = Field(description="상태 (queued/started/running/completed/error)")
    task_id: str = Field(description="Celery 태스크 ID")
    message: Optional[str] = Field(default=None, description="추가 메시지")


class JonggaV2DatesResponse(BaseModel):
    """종가베팅 V2 가능한 날짜 목록 응답"""
    dates: List[str] = Field(description="날짜 목록 (YYYY-MM-DD)")
    count: int = Field(description="날짜 수")


class JonggaSignalItem(BaseModel):
    """종가베팅 V2 시그널 아이템"""
    ticker: str = Field(description="종목 코드")
    name: str = Field(description="종목명")
    signal_type: str = Field(default="JONGGA_V2")
    score: dict = Field(description="점수 상세")
    grade: str = Field(description="등급 (S/A/B/C)")
    entry_price: Optional[int] = Field(default=None, description="진입가")
    target_price: Optional[int] = Field(default=None, description="목표가")
    stop_loss: Optional[int] = Field(default=None, description="손절가")
    position_size: Optional[int] = Field(default=None, description="포지션 사이즈")
    reasons: List[str] = Field(default_factory=list, description="매매 사유")
    signal_date: str = Field(description="시그널 날짜")


class JonggaV2HistoryResponse(BaseModel):
    """종가베팅 V2 히스토리 응답"""
    date: str = Field(description="시그널 날짜")
    signals: List[JonggaSignalItem] = Field(description="시그널 목록")
    count: int = Field(description="시그널 수")


# ============================================================================
# Constants
# ============================================================================

VALID_MARKETS = ["KOSPI", "KOSDAQ", "ALL"]
DEFAULT_MIN_SCORE = 6
SIGNAL_TYPE = "JONGGA_V2"


# ============================================================================
# Helper Functions
# ============================================================================


def _validate_market(market: str) -> str:
    """시장 값 검증"""
    market_upper = market.upper()
    if market_upper not in VALID_MARKETS:
        raise HTTPException(
            status_code=422,
            detail=f"유효하지 않은 market 값입니다: {market}. (KOSPI/KOSDAQ/ALL)"
        )
    return market_upper


def _parse_date_string(date_str: str) -> date:
    """
    ISO 형식 날짜 문자열을 date 객체로 변환

    Args:
        date_str: YYYY-MM-DD 형식의 날짜 문자열

    Returns:
        datetime.date 객체

    Raises:
        HTTPException: 날짜 형식이 잘못된 경우
    """
    try:
        return datetime.fromisoformat(date_str).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 날짜 형식입니다: {date_str}. (YYYY-MM-DD)"
        )


def _signal_to_item(signal: Signal) -> "JonggaSignalItem":
    """
    Signal 엔티티를 JonggaSignalItem 응답 모델로 변환

    Args:
        signal: Signal ORM 객체

    Returns:
        JonggaSignalItem 응답 모델
    """
    # 점수 상세 변환
    score_detail = {
        "total": signal.score or 0,
        "news": signal.news_score or 0,
        "volume": signal.volume_score or 0,
        "chart": signal.chart_score or 0,
        "candle": signal.candle_score or 0,
        "period": signal.period_score or 0,
        "flow": signal.supply_score or 0,
    }

    # 종목명 조회
    name = signal.stock.name if signal.stock else signal.ticker

    return JonggaSignalItem(
        ticker=signal.ticker,
        name=name,
        score=score_detail,
        grade=signal.grade or "C",
        entry_price=signal.entry_price,
        target_price=signal.target_price,
        stop_loss=signal.stop_price,
        position_size=None,  # TODO: 계산 로직 추가
        reasons=[],  # TODO: 사유 생성 로직 추가
        signal_date=signal.signal_date.isoformat()
    )


# ============================================================================
# Routes
# ============================================================================


@router.post(
    "/run",
    response_model=JonggaV2RunResponse,
    summary="종가베팅 V2 엔진 실행",
    description="전체 종목을 대상으로 종가베팅 V2 시그널 생성을 실행합니다.",
    responses={
        200: {"description": "엔진 실행 시작"},
        422: {"description": "잘못된 파라미터"},
        503: {"description": "Celery 사용 불가"},
    },
)
async def run_jongga_v2_engine(
    request: JonggaV2RunRequest,
    background_tasks: BackgroundTasks,
) -> JonggaV2RunResponse:
    """
    종가베팅 V2 엔진 실행

    ## 설명
    전체 종목을 스캔하여 종가베팅 V2 점수를 계산하고 시그널을 생성합니다.
    Celery 백그라운드 태스크로 비동기 실행됩니다.

    ## Parameters
    - **market**: 시장 (KOSPI/KOSDAQ/ALL)
    - **top_n**: 상위 N개 종목 (기본 30, 최대 100)
    - **min_score**: 최소 점수 (0-12, 기본 6)
    - **background**: 백그라운드 실행 여부
    - **capital**: 투자 자본 (기본 1000만원)

    ## Returns
    - **status**: 상태 (queued/started/completed/error)
    - **task_id**: Celery 태스크 ID

    ## Example
    ```bash
    curl -X POST "http://localhost:5111/api/kr/jongga-v2/run" \\
      -H "Content-Type: application/json" \\
      -d '{"market": "KOSPI", "top_n": 30, "min_score": 6}'
    ```
    """
    try:
        # 시장 값 검증
        market = _validate_market(request.market)

        # Celery 태스크 호출
        try:
            from tasks.signal_tasks import generate_jongga_signals
        except ImportError:
            from ralph_stock_lib.tasks.signal_tasks import generate_jongga_signals

        task = generate_jongga_signals.delay(
            capital=request.capital,
            top_n=request.top_n,
            market=market,
            min_score=request.min_score,
        )

        logger.info(f"종가베팅 V2 엔진 실행: task_id={task.id}, market={market}, top_n={request.top_n}")

        return JonggaV2RunResponse(
            status="queued",
            task_id=task.id,
            message=f"종가베팅 V2 시그널 생성이 시작되었습니다. task_id: {task.id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종가베팅 V2 엔진 실행 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"종가베팅 V2 엔진 실행 실패: {str(e)}"
        )


@router.get(
    "/dates",
    response_model=JonggaV2DatesResponse,
    summary="종가베팅 V2 가능한 날짜 목록",
    description="종가베팅 V2 시그널이 존재하는 날짜 목록을 반환합니다.",
    responses={
        200: {"description": "날짜 목록 반환 성공"},
        500: {"description": "서버 에러"},
    },
)
async def get_jongga_v2_dates(
    limit: int = Query(default=30, ge=1, le=365, description="최대 반환 날짜 수"),
    db: Session = Depends(get_db_session),
) -> JonggaV2DatesResponse:
    """
    종가베팅 V2 가능한 날짜 목록 조회

    ## 설명
    종가베팅 V2 시그널이 존재하는 날짜 목록을 반환합니다.

    ## Parameters
    - **limit**: 최대 반환 날짜 수 (기본 30일, 최대 365일)

    ## Returns
    - **dates**: 날짜 목록 (YYYY-MM-DD)
    - **count**: 날짜 수

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/jongga-v2/dates?limit=30"
    ```
    """
    try:
        repo = SignalRepository(db)

        # 종가베팅 V2 시그널이 있는 날짜 목록 조회
        from sqlalchemy import func, desc

        query = (
            db.query(func.date(Signal.signal_date))
            .where(Signal.signal_type == SIGNAL_TYPE)
            .group_by(Signal.signal_date)
            .order_by(desc(Signal.signal_date))
            .limit(limit)
        )

        date_results = query.all()
        dates = [row[0].isoformat() for row in date_results]

        return JonggaV2DatesResponse(
            dates=dates,
            count=len(dates)
        )

    except Exception as e:
        logger.error(f"종가베팅 V2 날짜 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"날짜 목록 조회 실패: {str(e)}"
        )


@router.get(
    "/history/{date_str}",
    response_model=JonggaV2HistoryResponse,
    summary="종가베팅 V2 특정 날짜 시그널 조회",
    description="특정 날짜의 종가베팅 V2 시그널 목록을 반환합니다.",
    responses={
        200: {"description": "시그널 목록 반환 성공"},
        400: {"description": "잘못된 날짜 형식"},
        404: {"description": "시그널 없음"},
        500: {"description": "서버 에러"},
    },
)
async def get_jongga_v2_history(
    date_str: str,
    db: Session = Depends(get_db_session),
) -> JonggaV2HistoryResponse:
    """
    종가베팅 V2 특정 날짜 시그널 조회

    ## 설명
    특정 날짜의 종가베팅 V2 시그널 목록을 반환합니다.

    ## Parameters
    - **date_str**: 날짜 문자열 (YYYY-MM-DD)

    ## Returns
    - **date**: 시그널 날짜
    - **signals**: 시그널 목록
    - **count**: 시그널 수

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/jongga-v2/history/2026-02-01"
    ```
    """
    try:
        # 날짜 파싱
        target_date = _parse_date_string(date_str)

        # 해당 날짜의 종가베팅 V2 시그널 조회
        signals = db.query(Signal).filter(
            Signal.signal_type == SIGNAL_TYPE,
            Signal.signal_date == target_date,
            Signal.score >= DEFAULT_MIN_SCORE  # B급 이상만
        ).order_by(Signal.score.desc()).all()

        # 응답 변환
        signal_items = [_signal_to_item(signal) for signal in signals]

        return JonggaV2HistoryResponse(
            date=date_str,
            signals=signal_items,
            count=len(signal_items)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종가베팅 V2 히스토리 조회 실패 ({date_str}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"히스토리 조회 실패: {str(e)}"
        )


@router.get(
    "/status/{task_id}",
    summary="종가베팅 V2 엔진 상태 조회",
    description="Celery 태스크 실행 상태를 조회합니다.",
    responses={
        200: {"description": "상태 조회 성공"},
        404: {"description": "태스크 없음"},
    },
)
async def get_jongga_v2_status(
    task_id: str,
):
    """
    종가베팅 V2 엔진 상태 조회

    ## 설명
    Celery 태스크의 실행 상태를 조회합니다.

    ## Parameters
    - **task_id**: Celery 태스크 ID

    ## Returns
    - **state**: 태스크 상태 (PENDING/STARTED/SUCCESS/FAILURE)
    - **result**: 태스크 결과 (완료 시)

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/jongga-v2/status/celery-task-id"
    ```
    """
    try:
        from tasks.celery_app import celery_app

        # 태스크 결과 조회
        result = celery_app.AsyncResult(task_id)

        if not result.id:
            raise HTTPException(
                status_code=404,
                detail=f"태스크를 찾을 수 없습니다: {task_id}"
            )

        return {
            "task_id": task_id,
            "state": result.state,
            "result": result.result if result.ready() else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태스크 상태 조회 실패 ({task_id}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"상태 조회 실패: {str(e)}"
        )
