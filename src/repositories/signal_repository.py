"""
Signal Repository
VCP/종가베팅 시그널 데이터 접근 계층
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from src.repositories.base import BaseRepository
from src.database.models import Signal


class SignalRepository(BaseRepository[Signal]):
    """
    Signal Repository
    시그널 데이터 CRUD 작업 처리
    """

    def __init__(self, session: Session):
        super().__init__(Signal, session)

    def get_active(self, limit: int = 100) -> List[Signal]:
        """
        활성 시그널 조회 (status='OPEN')

        Args:
            limit: 최대 반환 수

        Returns:
            활성 Signal 리스트
        """
        query = select(Signal).where(
            Signal.status == "OPEN"
        ).order_by(desc(Signal.signal_date), desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_by_ticker(self, ticker: str, limit: int = 50) -> List[Signal]:
        """
        종목별 시그널 조회

        Args:
            ticker: 종목 코드
            limit: 최대 반환 수

        Returns:
            Signal 리스트
        """
        query = select(Signal).where(
            Signal.ticker == ticker
        ).order_by(desc(Signal.signal_date)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        signal_type: Optional[str] = None
    ) -> List[Signal]:
        """
        날짜 범위 시그널 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            signal_type: 시그널 타입 필터 (VCP/JONGGA_V2)

        Returns:
            Signal 리스트
        """
        query = select(Signal).where(
            and_(
                Signal.signal_date >= start_date,
                Signal.signal_date <= end_date
            )
        )

        if signal_type:
            query = query.where(Signal.signal_type == signal_type)

        query = query.order_by(desc(Signal.signal_date))
        result = self.session.execute(query)
        return list(result.scalars().all())

    def update_status(
        self,
        signal_id: int,
        new_status: str,
        exit_price: Optional[float] = None,
        exit_reason: Optional[str] = None
    ) -> Optional[Signal]:
        """
        시그널 상태 업데이트 (OPEN → CLOSED)

        Args:
            signal_id: 시그널 ID
            new_status: 새 상태 (CLOSED)
            exit_price: 청산 가격
            exit_reason: 청산 사유

        Returns:
            업데이트된 Signal 인스턴스
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return None

        signal.status = new_status
        signal.exit_time = datetime.now(timezone.utc)

        if exit_price is not None:
            signal.exit_price = exit_price

        if exit_reason is not None:
            signal.exit_reason = exit_reason

        self.session.commit()
        self.session.refresh(signal)
        return signal

    def get_latest_signals(
        self,
        signal_type: str,
        limit: int = 20
    ) -> List[Signal]:
        """
        최신 시그널 조회

        Args:
            signal_type: 시그널 타입 (VCP/JONGGA_V2)
            limit: 최대 반환 수

        Returns:
            최신 Signal 리스트
        """
        query = select(Signal).where(
            Signal.signal_type == signal_type
        ).order_by(
            desc(Signal.signal_date)
        ).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_double_buy_signals(self, limit: int = 30) -> List[Signal]:
        """
        쌍끌이 매수 시그널 조회
        (외인+기관 동시 순매수)

        Returns:
            쌍끌이 Signal 리스트
        """
        # 외국인, 기관 모두 5일 연속 순매수
        query = select(Signal).where(
            and_(
                Signal.status == "OPEN",
                Signal.foreign_net_5d > 0,
                Signal.inst_net_5d > 0
            )
        ).order_by(desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_high_score_signals(self, min_score: float = 70.0, limit: int = 20) -> List[Signal]:
        """
        고득점 시그널 조회

        Args:
            min_score: 최소 점수
            limit: 최대 반환 수

        Returns:
            고득점 Signal 리스트
        """
        query = select(Signal).where(
            and_(
                Signal.status == "OPEN",
                Signal.score >= min_score
            )
        ).order_by(desc(Signal.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_summary_by_date(self, signal_date: date) -> Dict[str, Any]:
        """
        특정 날짜의 시그널 요약 통계

        Args:
            signal_date: 대상 날짜

        Returns:
            통계 정보 딕셔너리
        """
        signals = self.get_by_date_range(signal_date, signal_date)

        total = len(signals)
        by_status = {"OPEN": 0, "CLOSED": 0}
        by_type = {"VCP": 0, "JONGGA_V2": 0}
        total_score = sum(s.score or 0 for s in signals)

        for s in signals:
            by_status[s.status] = by_status.get(s.status, 0) + 1
            by_type[s.signal_type] = by_type.get(s.signal_type, 0) + 1

        avg_score = total_score / total if total > 0 else 0

        return {
            "date": signal_date,
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "avg_score": avg_score,
        }
