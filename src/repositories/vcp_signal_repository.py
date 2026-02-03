"""
VCP Signal Repository
VCP 패턴 시그널 데이터 접근 계층

활성 VCP 시그널(상위 10개) 조회를 위한 전용 Repository
"""

from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from src.repositories.base import BaseRepository
from src.database.models import Signal, Stock


class VCPSignalRepository(BaseRepository[Signal]):
    """
    VCP Signal Repository

    VCP 패턴 시그널 조회를 위한 전용 Repository
    - 활성 VCP 시그널 조회 (status='OPEN', signal_type='VCP')
    - 상위 N개 시그널 필터링
    - 시장별 필터링 (KOSPI/KOSDAQ)
    """

    def __init__(self, session: Session):
        """
        Args:
            session: DB 세션
        """
        super().__init__(Signal, session)

    def get_active_vcp_signals(
        self,
        limit: int = 10,
        market: Optional[str] = None
    ) -> List[Signal]:
        """
        활성 VCP 시그널 조회 (상위 N개)

        Args:
            limit: 최대 반환 수 (기본 10개)
            market: 시장 필터 (KOSPI/KOSDAQ/None=전체)

        Returns:
            활성 VCP Signal 리스트 (점수 내림차순)
        """
        # Stock과 조인을 위한 쿼리
        query = select(Signal).join(
            Stock, Signal.ticker == Stock.ticker
        ).where(
            and_(
                Signal.signal_type == "VCP",
                Signal.status == "OPEN"
            )
        )

        # 시장 필터
        if market:
            query = query.where(Stock.market == market)

        # 점수 내림차순 정렬
        query = query.order_by(desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_top_vcp_signals(
        self,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[Signal]:
        """
        상위 VCP 시그널 조회

        Args:
            limit: 최대 반환 수 (기본 10개)
            min_score: 최소 점수 (기본 0.0)

        Returns:
            상위 VCP Signal 리스트
        """
        query = select(Signal).where(
            and_(
                Signal.signal_type == "VCP",
                Signal.status == "OPEN",
                Signal.score >= min_score
            )
        ).order_by(desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_vcp_signals_by_market(
        self,
        market: str,
        limit: int = 10
    ) -> List[Signal]:
        """
        시장별 VCP 시그널 조회

        Args:
            market: 시장 (KOSPI/KOSDAQ)
            limit: 최대 반환 수

        Returns:
            해당 시장의 VCP Signal 리스트
        """
        query = select(Signal).join(
            Stock, Signal.ticker == Stock.ticker
        ).where(
            and_(
                Signal.signal_type == "VCP",
                Signal.status == "OPEN",
                Stock.market == market
            )
        ).order_by(desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_vcp_signals_with_min_score(
        self,
        min_score: float,
        limit: int = 10
    ) -> List[Signal]:
        """
        최소 점수 이상 VCP 시그널 조회

        Args:
            min_score: 최소 점수
            limit: 최대 반환 수

        Returns:
            최소 점수 이상 VCP Signal 리스트
        """
        query = select(Signal).where(
            and_(
                Signal.signal_type == "VCP",
                Signal.status == "OPEN",
                Signal.score >= min_score
            )
        ).order_by(desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_vcp_signal_by_ticker(self, ticker: str) -> Optional[Signal]:
        """
        종목별 활성 VCP 시그널 조회

        Args:
            ticker: 종목 코드

        Returns:
            활성 VCP Signal 또는 None
        """
        query = select(Signal).where(
            and_(
                Signal.ticker == ticker,
                Signal.signal_type == "VCP",
                Signal.status == "OPEN"
            )
        ).order_by(desc(Signal.signal_date)).limit(1)

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def count_active_vcp_signals(self, market: Optional[str] = None) -> int:
        """
        활성 VCP 시그널 수 카운트

        Args:
            market: 시장 필터 (KOSPI/KOSDAQ/None=전체)

        Returns:
            활성 VCP 시그널 수
        """
        query = select(Signal).join(
            Stock, Signal.ticker == Stock.ticker
        ).where(
            and_(
                Signal.signal_type == "VCP",
                Signal.status == "OPEN"
            )
        )

        if market:
            query = query.where(Stock.market == market)

        result = self.session.execute(query)
        return len(list(result.scalars().all()))
