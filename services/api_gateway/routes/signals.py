"""
Signals Routes
VCP 및 종가베팅 시그널 조회 API
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.repositories.vcp_signal_repository import VCPSignalRepository
from src.repositories.signal_repository import SignalRepository
from src.repositories.stock_repository import StockRepository
from services.api_gateway.schemas import (
    VCPSignalItem,
    VCPSignalsResponse,
    SignalsListResponse,
)


router = APIRouter(prefix="/api/kr/signals", tags=["signals"])


def _convert_signal_to_item(signal, stock=None) -> VCPSignalItem:
    """
    Signal ORM 객체를 VCPSignalItem으로 변환

    Args:
        signal: Signal ORM 객체
        stock: Stock ORM 객체 (선택)

    Returns:
        VCPSignalItem
    """
    # Stock 정보 가져오기
    if stock:
        name = stock.name
        market = stock.market
    elif signal.stock:
        name = signal.stock.name
        market = signal.stock.market
    else:
        name = signal.ticker  # Fallback
        market = "KOSPI"  # Fallback

    return VCPSignalItem(
        ticker=signal.ticker,
        name=name,
        market=market,
        signal_type=signal.signal_type,
        score=float(signal.score) if signal.score is not None else 0.0,
        grade=signal.grade or "C",
        signal_date=signal.signal_date.isoformat() if signal.signal_date else datetime.now().date().isoformat(),
        entry_price=signal.entry_price,
        target_price=signal.target_price,
        current_price=None,  # 실시간 가격은 별도 API
        contraction_ratio=signal.contraction_ratio,
        foreign_5d=signal.foreign_net_5d or 0,
        inst_5d=signal.inst_net_5d or 0,
        created_at=signal.created_at.isoformat() if signal.created_at else datetime.now().isoformat(),
    )


@router.get(
    "/vcp",
    response_model=VCPSignalsResponse,
    summary="활성 VCP 시그널 상위 10개 조회",
    description="점수순 정렬된 활성 VCP 시그널 상위 10개를 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
        500: {"description": "서버 에러"},
    },
)
def get_active_vcp_signals(
    limit: int = Query(default=10, ge=1, le=50, description="반환할 최대 시그널 수"),
    market: Optional[str] = Query(default=None, description="시장 필터 (KOSPI/KOSDAQ)"),
    session: Session = Depends(get_db_session),
) -> VCPSignalsResponse:
    """
    활성 VCP 시그널 상위 10개 조회

    ## 설명
    VCP 패턴이 감지된 활성 시그널을 상위 10개 반환합니다.

    ## Parameters
    - **limit**: 반환할 최대 시그널 수 (기본 10개, 최대 50개)
    - **market**: 시장 필터 (KOSPI/KOSDAQ/None=전체)

    ## 반환 데이터
    - **ticker**: 종목 코드
    - **name**: 종목명
    - **market**: 시장 (KOSPI/KOSDAQ)
    - **score**: VCP 점수 (0-100)
    - **grade**: 등급 (S/A/B/C)
    - **contraction_ratio**: 수축률 (0-1)
    - **foreign_5d**: 외국인 5일 순매수 (주)
    - **inst_5d**: 기관 5일 순매수 (주)

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/signals/vcp?limit=10"
    curl "http://localhost:5111/api/kr/signals/vcp?market=KOSPI"
    ```
    """
    try:
        vcp_repo = VCPSignalRepository(session)

        # 활성 VCP 시그널 조회
        signals = vcp_repo.get_active_vcp_signals(limit=limit, market=market)

        # 응답 변환
        signal_items = [_convert_signal_to_item(s) for s in signals]

        # 생성 일시 (최신 시그널 기준)
        generated_at = None
        if signals:
            latest_created = max((s.created_at for s in signals if s.created_at), default=None)
            if latest_created:
                generated_at = latest_created.isoformat()

        return VCPSignalsResponse(
            signals=signal_items,
            count=len(signal_items),
            generated_at=generated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch VCP signals: {str(e)}",
        )


@router.get(
    "",
    summary="전체 활성 시그널 조회",
    description="VCP 및 종가베팅 V2 활성 시그널을 반환합니다. (리스트 직접 반환 - 호환성 유지)",
    responses={
        200: {"description": "조회 성공"},
        500: {"description": "서버 에러"},
    },
)
def get_all_active_signals(
    limit: int = Query(default=10, ge=1, le=50, description="반환할 최대 시그널 수"),
    signal_type: Optional[str] = Query(default=None, description="시그널 타입 필터 (VCP/JONGGA_V2)"),
    format: str = Query(default="list", description="응답 형식 (list=리스트 직접, object=객체 감싸서)"),
    session: Session = Depends(get_db_session),
):
    """
    전체 활성 시그널 조회

    ## 설명
    VCP 및 종가베팅 V2 활성 시그널을 반환합니다.

    ## Parameters
    - **limit**: 반환할 최대 시그널 수 (기본 10개, 최대 50개)
    - **signal_type**: 시그널 타입 필터 (VCP/JONGGA_V2/None=전체)
    - **format**: 응답 형식 (list=리스트 직접 반환, object=객체 감싸서)

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/signals?limit=20"
    curl "http://localhost:5111/api/kr/signals?signal_type=VCP"
    curl "http://localhost:5111/api/kr/signals?format=object"
    ```
    """
    try:
        signal_repo = SignalRepository(session)

        # 활성 시그널 조회
        if signal_type:
            signals = signal_repo.get_by_date_range(
                start_date=datetime.now().date(),
                end_date=datetime.now().date(),
                signal_type=signal_type,
            )
            # OPEN 상태만 필터
            signals = [s for s in signals if s.status == "OPEN"]
        else:
            signals = signal_repo.get_active(limit=limit)

        # 점수순 정렬 및 제한
        signals = sorted(signals, key=lambda x: x.score or 0, reverse=True)[:limit]

        # 응답 변환
        signal_items = [_convert_signal_to_item(s) for s in signals]

        # 카운트 계산
        vcp_count = sum(1 for s in signal_items if s.signal_type == "VCP")
        jongga_count = sum(1 for s in signal_items if s.signal_type == "JONGGA_V2")

        # 생성 일시
        generated_at = None
        if signals:
            latest_created = max((s.created_at for s in signals if s.created_at), default=None)
            if latest_created:
                generated_at = latest_created.isoformat()

        # format 파라미터에 따라 응답 형식 결정 (기본: 리스트 직접 반환 - 호환성)
        if format == "object":
            return SignalsListResponse(
                signals=signal_items,
                count=len(signal_items),
                vcp_count=vcp_count,
                jongga_count=jongga_count,
                generated_at=generated_at,
            )

        # 기본 동작: 리스트 직접 반환 (Python APIClient 호환성)
        return signal_items

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch signals: {str(e)}",
        )


@router.get(
    "/top",
    response_model=VCPSignalsResponse,
    summary="상위 VCP 시그널 조회",
    description="최소 점수 이상의 상위 VCP 시그널을 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
        500: {"description": "서버 에러"},
    },
)
def get_top_vcp_signals(
    min_score: float = Query(default=70.0, ge=0, le=100, description="최소 VCP 점수"),
    limit: int = Query(default=10, ge=1, le=50, description="반환할 최대 시그널 수"),
    session: Session = Depends(get_db_session),
) -> VCPSignalsResponse:
    """
    상위 VCP 시그널 조회

    ## 설명
    최소 점수 이상의 VCP 시그널을 반환합니다.

    ## Parameters
    - **min_score**: 최소 VCP 점수 (기본 70.0)
    - **limit**: 반환할 최대 시그널 수

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/signals/top?min_score=80"
    ```
    """
    try:
        vcp_repo = VCPSignalRepository(session)

        # 상위 VCP 시그널 조회
        signals = vcp_repo.get_vcp_signals_with_min_score(
            min_score=min_score,
            limit=limit,
        )

        # 응답 변환
        signal_items = [_convert_signal_to_item(s) for s in signals]

        return VCPSignalsResponse(
            signals=signal_items,
            count=len(signal_items),
            generated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch top VCP signals: {str(e)}",
        )
