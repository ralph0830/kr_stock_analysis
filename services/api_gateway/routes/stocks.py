"""
Stocks Routes
종목 상세, 차트, 수급, 시그널 조회 API
"""

from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.repositories.stock_repository import StockRepository
from src.repositories.signal_repository import SignalRepository
from services.api_gateway.schemas import (
    StockFlowResponse,
    FlowDataPoint,
    SignalHistoryResponse,
    SignalHistoryItem,
)


router = APIRouter(prefix="/api/kr/stocks", tags=["stocks"])


def calculate_smartmoney_score(flows: list) -> float:
    """
    SmartMoney 점수 계산 (0-100)

    Args:
        flows: InstitutionalFlow 리스트

    Returns:
        SmartMoney 점수
    """
    if not flows:
        return 50.0

    # 외국인 5일 순매수 비중 (40%)
    foreign_net_5d = sum(f.foreign_net_5d for f in flows) / len(flows)
    foreign_score = min(100, max(0, 50 + foreign_net_5d / 100000))

    # 기관 5일 순매수 비중 (30%)
    inst_net_5d = sum(f.inst_net_5d for f in flows) / len(flows)
    inst_score = min(100, max(0, 50 + inst_net_5d / 100000))

    # 외국인 연속 순매수 일수 (15%)
    consecutive_days = max(f.foreign_consecutive_days for f in flows)
    consecutive_score = min(100, consecutive_days * 10)

    # 이중 매수 (외국인+기관 동시 순매수) (15%)
    double_buy_count = sum(1 for f in flows if f.is_double_buy)
    double_buy_score = min(100, double_buy_count * 20)

    smartmoney_score = (
        foreign_score * 0.4
        + inst_score * 0.3
        + consecutive_score * 0.15
        + double_buy_score * 0.15
    )

    return round(smartmoney_score, 2)


# 종목 상세(/api/kr/stocks/{ticker}) 및 차트(/api/kr/stocks/{ticker}/chart) 엔드포인트는 main.py에서 통합 처리
# stocks.py에서는 flow, signals 엔드포인트만 담당



@router.get(
    "/{ticker}/flow",
    response_model=StockFlowResponse,
    summary="종목 수급 데이터 조회",
    description="외국인/기관 순매수 데이터를 조회합니다. SmartMoney 점수(0-100)를 계산하여 제공합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "종목을 찾을 수 없음"},
    },
)
def get_stock_flow(
    ticker: str,
    days: int = Query(default=20, ge=1, le=60, description="조회 일수"),
    session: Session = Depends(get_db_session),
) -> StockFlowResponse:
    """
    종목 수급 데이터 조회

    Args:
        ticker: 종목 코드
        days: 조회 일수 (기본 20일, 최대 60일)
        session: DB 세션

    Returns:
        수급 데이터 (SmartMoney 점수 포함)

    ## SmartMoney 점수 산출
    - 외국인 5일 순매수 비중: 40%
    - 기관 5일 순매수 비중: 30%
    - 외국인 연속 순매수 일수: 15%
    - 이중 매수(외국인+기관 동시 순매수): 15%

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/stocks/005930/flow?days=20"
    ```
    """
    stock_repo = StockRepository(session)
    flows = stock_repo.get_institutional_flow(ticker, days)

    # SmartMoney 점수 계산
    smartmoney_score = calculate_smartmoney_score(flows) if flows else 50.0

    flow_points = [
        FlowDataPoint(
            date=f.date,
            foreign_net=f.foreign_net_buy,
            inst_net=f.inst_net_buy,
            foreign_net_amount=f.foreign_net_buy * 10000,  # 주 → 원 환산
            inst_net_amount=f.inst_net_buy * 10000,
            supply_demand_score=f.supply_demand_score,
        )
        for f in flows
    ]

    return StockFlowResponse(
        ticker=ticker,
        period_days=days,
        data=flow_points,
        smartmoney_score=smartmoney_score,
        total_points=len(flow_points),
    )


@router.get(
    "/{ticker}/signals",
    response_model=SignalHistoryResponse,
    summary="종목 시그널 히스토리 조회",
    description="특정 종목의 과거 시그널 내역을 조회합니다. OPEN/CLOSED 상태별 요약과 수익률 통계를 제공합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "종목을 찾을 수 없음"},
    },
)
def get_stock_signals(
    ticker: str,
    session: Session = Depends(get_db_session),
) -> SignalHistoryResponse:
    """
    종목 시그널 히스토리 조회

    Args:
        ticker: 종목 코드
        session: DB 세션

    Returns:
        시그널 히스토리 (OPEN/COUNT 요약)

    ## Example
    ```bash
    curl "http://localhost:5111/api/kr/stocks/005930/signals"
    ```
    """
    repo = SignalRepository(session)
    signals = repo.get_by_ticker(ticker)

    # 통계 계산
    total_signals = len(signals)
    open_signals = sum(1 for s in signals if s.status == "OPEN")
    closed_signals = sum(1 for s in signals if s.status == "CLOSED")

    # 수익률 계산 (exit_price는 모델에 없으므로 계산 불가)
    avg_return_pct = None
    win_rate = None

    signal_items = [
        SignalHistoryItem(
            id=s.id,
            ticker=s.ticker,
            signal_type=s.signal_type,
            signal_date=s.signal_date,
            status=s.status,
            score=s.score,
            grade=s.grade,
            entry_price=s.entry_price,
            exit_price=None,  # Signal 모델에 없음
            entry_time=s.entry_time,
            exit_time=s.exit_time,
            return_pct=None,
            exit_reason=s.exit_reason,
        )
        for s in signals
    ]

    return SignalHistoryResponse(
        ticker=ticker,
        total_signals=total_signals,
        open_signals=open_signals,
        closed_signals=closed_signals,
        avg_return_pct=avg_return_pct,
        win_rate=win_rate,
        signals=signal_items,
    )
