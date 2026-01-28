"""
Performance Routes
누적 수익률 및 성과 지표 API
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from src.database.session import get_db_session
from src.repositories.performance_repository import PerformanceRepository

router = APIRouter(prefix="/api/kr/performance", tags=["performance"])


# ============================================================================
# Response Models
# ============================================================================

class CumulativeReturnPoint(BaseModel):
    """누적 수익률 데이터 포인트"""
    date: str = Field(..., description="날짜")
    daily_return_pct: float = Field(..., description="일일 수익률 (%)")
    cumulative_return_pct: float = Field(..., description="누적 수익률 (%)")


class CumulativeReturnResponse(BaseModel):
    """누적 수익률 응답"""
    data: list[CumulativeReturnPoint] = Field(..., description="누적 수익률 데이터")
    total_points: int = Field(..., description="데이터 포인트 수")
    final_return_pct: float = Field(..., description="최종 누적 수익률 (%)")


class SignalPerformanceResponse(BaseModel):
    """시그널 성과 응답"""
    total_signals: int = Field(..., description="전체 시그널 수")
    closed_signals: int = Field(..., description="종료된 시그널 수")
    win_rate: float = Field(..., description="승률 (%)")
    avg_return: float = Field(..., description="평균 수익률 (%)")
    best_return: Optional[float] = Field(None, description="최고 수익률 (%)")
    worst_return: Optional[float] = Field(None, description="최저 수익률 (%)")


class PeriodPerformanceResponse(BaseModel):
    """기간별 성과 응답"""
    period: str = Field(..., description="기간")
    total_signals: int = Field(..., description="전체 시그널 수")
    win_rate: float = Field(..., description="승률 (%)")
    avg_return: float = Field(..., description="평균 수익률 (%)")
    cumulative_return: float = Field(..., description="누적 수익률 (%)")
    mdd: float = Field(..., description="최대 낙폭 (MDD, %)")
    best_return: Optional[float] = Field(None, description="최고 수익률 (%)")
    worst_return: Optional[float] = Field(None, description="최저 수익률 (%)")
    sharpe_ratio: float = Field(..., description="샤프 비율")


class TopPerformerItem(BaseModel):
    """최고 성과 종목 아이템"""
    ticker: str = Field(..., description="종목 코드")
    signal_type: str = Field(..., description="시그널 타입")
    entry_price: float = Field(..., description="진입가")
    exit_price: float = Field(..., description="청산가")
    return_pct: float = Field(..., description="수익률 (%)")
    signal_date: str = Field(..., description="시그널 일자")


class TopPerformersResponse(BaseModel):
    """최고 성과 종목 목록 응답"""
    performers: list[TopPerformerItem] = Field(..., description="최고 성과 종목 리스트")
    total_count: int = Field(..., description="전체 종목 수")


# ============================================================================
# Routes
# ============================================================================

@router.get(
    "/cumulative",
    response_model=CumulativeReturnResponse,
    summary="누적 수익률 조회",
    description="시그널 기반 누적 수익률을 날짜별로 조회합니다."
)
async def get_cumulative_returns(
    signal_type: Optional[str] = Query(None, description="시그널 타입 (VCP, JONGGA_V2)"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_db_session)
):
    """
    누적 수익률 조회

    ## Parameters
    - **signal_type**: 시그널 타입 필터 (VCP, JONGGA_V2)
    - **start_date**: 시작 날짜 (YYYY-MM-DD)
    - **end_date**: 종료 날짜 (YYYY-MM-DD)

    ## Returns
    - 날짜별 누적 수익률 데이터

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/performance/cumulative?signal_type=VCP"
    ```
    """
    try:
        repo = PerformanceRepository(db)

        # 날짜 변환
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date).date()
        if end_date:
            end_dt = datetime.fromisoformat(end_date).date()

        data = repo.calculate_cumulative_return(
            signal_type=signal_type,
            start_date=start_dt,
            end_date=end_dt,
        )

        final_return = data[-1]["cumulative_return_pct"] if data else 0.0

        return CumulativeReturnResponse(
            data=[CumulativeReturnPoint(**item) for item in data],
            total_points=len(data),
            final_return_pct=round(final_return, 2),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"날짜 형식 오류: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"누적 수익률 계산 실패: {e}")


@router.get(
    "/by-signal",
    response_model=SignalPerformanceResponse,
    summary="시그널별 성과 조회",
    description="특정 종목 또는 전체 시그널의 성과 지표를 조회합니다."
)
async def get_signal_performance(
    ticker: Optional[str] = Query(None, description="종목 코드"),
    signal_type: Optional[str] = Query(None, description="시그널 타입 (VCP, JONGGA_V2)"),
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    db: Session = Depends(get_db_session)
):
    """
    시그널별 성과 조회

    ## Parameters
    - **ticker**: 종목 코드 (선택)
    - **signal_type**: 시그널 타입 (VCP, JONGGA_V2)
    - **days**: 조회 기간 (일, 기본 30일)

    ## Returns
    - 승률, 평균 수익률, 최고/최저 수익률

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/performance/by-signal?days=30"
    ```
    """
    try:
        repo = PerformanceRepository(db)
        performance = repo.calculate_signal_performance(
            ticker=ticker,
            signal_type=signal_type,
            days=days,
        )

        return SignalPerformanceResponse(**performance)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성과 계산 실패: {e}")


@router.get(
    "/by-period",
    response_model=PeriodPerformanceResponse,
    summary="기간별 성과 조회",
    description="특정 기간 동안의 성과 지표를 조회합니다."
)
async def get_period_performance(
    period: str = Query("1mo", description="기간 (1w, 2w, 1mo, 3mo, 6mo, 1y)"),
    signal_type: Optional[str] = Query(None, description="시그널 타입 (VCP, JONGGA_V2)"),
    db: Session = Depends(get_db_session)
):
    """
    기간별 성과 조회

    ## Parameters
    - **period**: 기간 (1w, 2w, 1mo, 3mo, 6mo, 1y)
    - **signal_type**: 시그널 타입 (VCP, JONGGA_V2)

    ## Returns
    - 누적 수익률, MDD, 샤프 비율 등

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/performance/by-period?period=3mo"
    ```
    """
    try:
        repo = PerformanceRepository(db)
        performance = repo.get_performance_by_period(
            period=period,
            signal_type=signal_type,
        )

        return PeriodPerformanceResponse(**performance)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기간별 성과 조회 실패: {e}")


@router.get(
    "/top-performers",
    response_model=TopPerformersResponse,
    summary="최고 성과 종목 조회",
    description="수익률 기준 최고 성과 종목 목록을 조회합니다."
)
async def get_top_performers(
    signal_type: Optional[str] = Query(None, description="시그널 타입 (VCP, JONGGA_V2)"),
    limit: int = Query(10, ge=1, le=50, description="최대 반환 수"),
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    db: Session = Depends(get_db_session)
):
    """
    최고 성과 종목 조회

    ## Parameters
    - **signal_type**: 시그널 타입 (VCP, JONGGA_V2)
    - **limit**: 최대 반환 수 (기본 10)
    - **days**: 조회 기간 (일, 기본 30일)

    ## Returns
    - 수익률 순 종목 리스트

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/performance/top-performers?limit=20"
    ```
    """
    try:
        repo = PerformanceRepository(db)
        performers = repo.get_top_performers(
            signal_type=signal_type,
            limit=limit,
            days=days,
        )

        return TopPerformersResponse(
            performers=[TopPerformerItem(**p) for p in performers],
            total_count=len(performers),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최고 성과 종목 조회 실패: {e}")


@router.get(
    "/sharpe-ratio",
    summary="샤프 비율 조회",
    description="시그널 전략의 샤프 비율을 계산합니다."
)
async def get_sharpe_ratio(
    signal_type: Optional[str] = Query(None, description="시그널 타입 (VCP, JONGGA_V2)"),
    days: int = Query(30, ge=7, le=365, description="조회 기간 (일)"),
    risk_free_rate: float = Query(2.0, description="무위험 이자율 (연율 %)"),
    db: Session = Depends(get_db_session)
):
    """
    샤프 비율 조회

    ## Parameters
    - **signal_type**: 시그널 타입 (VCP, JONGGA_V2)
    - **days**: 조회 기간 (일, 기본 30일)
    - **risk_free_rate**: 무위험 이자율 (연율 %, 기본 2.0%)

    ## Returns
    - 연율화 샤프 비율

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/performance/sharpe-ratio?days=90"
    ```
    """
    try:
        repo = PerformanceRepository(db)
        sharpe = repo.calculate_sharpe_ratio(
            signal_type=signal_type,
            days=days,
            risk_free_rate=risk_free_rate,
        )

        return {
            "sharpe_ratio": round(sharpe, 4),
            "period_days": days,
            "risk_free_rate": risk_free_rate,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"샤프 비율 계산 실패: {e}")
