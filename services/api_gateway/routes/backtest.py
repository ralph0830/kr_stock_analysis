"""
백테스트 결과 API 라우터
백테스트 결과 조회, 요약, 히스토리 엔드포인트 제공
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from src.database.session import get_db_session
from src.repositories.backtest_repository import BacktestRepository
from services.api_gateway.schemas import (
    BacktestSummaryResponse,
    BacktestResultItem,
    BacktestListResponse,
)

router = APIRouter(prefix="/api/kr/backtest", tags=["backtest"])


@router.get(
    "/summary",
    response_model=BacktestSummaryResponse,
    summary="백테스트 요약 조회",
    description="전체 또는 특정 설정의 백테스트 결과 요약 통계를 반환합니다.",
)
async def get_backtest_summary(
    config_name: Optional[str] = Query(default=None, description="설정명 필터"),
    session: Session = Depends(get_db_session),
):
    """
    백테스트 결과 요약 조회

    ## 설명
    전체 또는 특정 설정의 백테스트 결과 요약 통계를 반환합니다.

    ## Parameters
    - **config_name**: 설정명 필터 (예: vcp_conservative, jongga_v2)

    ## 반환 데이터
    - **total_backtests**: 총 백테스트 수
    - **avg_return_pct**: 평균 수익률 (%)
    - **avg_win_rate**: 평균 승률 (%)
    - **best_return_pct**: 최고 수익률 (%)
    - **worst_return_pct**: 최저 수익률 (%)
    - **avg_sharpe_ratio**: 평균 샤프 비율
    - **avg_max_drawdown_pct**: 평균 최대 낙폭 (%)
    """
    try:
        repo = BacktestRepository(session)
        summary = repo.get_summary(config_name=config_name)
        return BacktestSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch backtest summary: {str(e)}"
        )


@router.get(
    "/latest",
    response_model=BacktestListResponse,
    summary="최신 백테스트 목록 조회",
    description="최신 백테스트 결과 목록을 반환합니다 (생성일 내림차순).",
)
async def get_latest_backtests(
    config_name: Optional[str] = Query(default=None, description="설정명 필터"),
    limit: int = Query(default=20, ge=1, le=100, description="최대 반환 수"),
    session: Session = Depends(get_db_session),
):
    """
    최신 백테스트 결과 조회

    ## 설명
    최신 백테스트 결과 목록을 반환합니다 (생성일 내림차순).

    ## Parameters
    - **config_name**: 설정명 필터 (선택)
    - **limit**: 최대 반환 수 (1-100, 기본 20)

    ## 반환 데이터
    - **results**: 백테스트 결과 리스트
    - **total**: 전체 결과 수
    """
    try:
        repo = BacktestRepository(session)
        results = repo.get_latest(config_name=config_name, limit=limit)

        return BacktestListResponse(
            results=[BacktestResultItem.model_validate(r) for r in results],
            total=len(results),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latest backtests: {str(e)}"
        )


@router.get(
    "/history",
    response_model=BacktestListResponse,
    summary="백테스트 히스토리 조회",
    description="날짜 범위 및 설정명으로 필터링한 백테스트 히스토리를 반환합니다.",
)
async def get_backtest_history(
    start_date: Optional[date] = Query(default=None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="종료 날짜 (YYYY-MM-DD)"),
    config_name: Optional[str] = Query(default=None, description="설정명 필터"),
    limit: int = Query(default=50, ge=1, le=100, description="최대 반환 수"),
    session: Session = Depends(get_db_session),
):
    """
    백테스트 히스토리 조회

    ## 설명
    날짜 범위 및 설정명으로 필터링한 백테스트 히스토리를 반환합니다.

    ## Parameters
    - **start_date**: 시작 날짜 (선택)
    - **end_date**: 종료 날짜 (선택)
    - **config_name**: 설정명 필터 (선택)
    - **limit**: 최대 반환 수 (1-100, 기본 50)

    ## 반환 데이터
    - **results**: 백테스트 결과 리스트 (백테스트 날짜 내림차순)
    - **total**: 전체 결과 수
    """
    try:
        repo = BacktestRepository(session)
        results = repo.get_history(
            start_date=start_date,
            end_date=end_date,
            config_name=config_name,
            limit=limit,
        )

        return BacktestListResponse(
            results=[BacktestResultItem.model_validate(r) for r in results],
            total=len(results),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch backtest history: {str(e)}"
        )


@router.get(
    "/best",
    response_model=BacktestResultItem,
    summary="최고 수익률 백테스트 조회",
    description="전체 또는 특정 설정 중 최고 수익률을 기록한 백테스트 결과를 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "백테스트 결과를 찾을 수 없음"},
    },
)
async def get_best_backtest(
    config_name: Optional[str] = Query(default=None, description="설정명 필터"),
    session: Session = Depends(get_db_session),
):
    """
    최고 수익률 백테스트 조회

    ## 설명
    전체 또는 특정 설정 중 최고 수익률을 기록한 백테스트 결과를 반환합니다.

    ## Parameters
    - **config_name**: 설정명 필터 (선택)

    ## 반환 데이터
    최고 수익률 백테스트 결과
    """
    try:
        repo = BacktestRepository(session)
        best = repo.get_best_result(config_name=config_name)

        if not best:
            raise HTTPException(
                status_code=404,
                detail="No backtest results found"
            )

        return BacktestResultItem.model_validate(best)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch best backtest: {str(e)}"
        )
