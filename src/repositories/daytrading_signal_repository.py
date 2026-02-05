"""
DaytradingSignal Repository
단타 매수 신호 Repository
"""

from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from src.repositories.base import BaseRepository
from src.database.models.daytrading_signal import DaytradingSignal


class DaytradingSignalRepository(BaseRepository[DaytradingSignal]):
    """단타 매수 신호 Repository"""

    def __init__(self, session: Session):
        """
        Args:
            session: DB 세션
        """
        super().__init__(DaytradingSignal, session)

    def create(self, signal: DaytradingSignal) -> DaytradingSignal:
        """
        신호 생성

        Args:
            signal: DaytradingSignal 인스턴스

        Returns:
            생성된 신호
        """
        self.session.add(signal)
        self.session.commit()
        self.session.refresh(signal)
        return signal

    def get_by_ticker(self, ticker: str) -> Optional[DaytradingSignal]:
        """
        종목 코드로 최신 신호 조회

        Args:
            ticker: 종목 코드

        Returns:
            DaytradingSignal 또는 None
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(ticker=ticker)
            .order_by(DaytradingSignal.signal_date.desc())
            .first()
        )

    def get_active_signals(self, limit: int = 50) -> List[DaytradingSignal]:
        """
        활성(OPEN) 신호 조회

        Args:
            limit: 최대 반환 개수

        Returns:
            활성 신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(status="OPEN")
            .order_by(DaytradingSignal.score.desc())
            .limit(limit)
            .all()
        )

    def get_by_min_score(self, min_score: int, limit: int = 100) -> List[DaytradingSignal]:
        """
        최소 점수 이상 신호 조회

        Args:
            min_score: 최소 점수
            limit: 최대 반환 개수

        Returns:
            신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter(DaytradingSignal.score >= min_score)
            .filter_by(status="OPEN")
            .order_by(DaytradingSignal.score.desc())
            .limit(limit)
            .all()
        )

    def get_by_market(self, market: str, limit: int = 100) -> List[DaytradingSignal]:
        """
        시장별 신호 조회

        Args:
            market: KOSPI 또는 KOSDAQ
            limit: 최대 반환 개수

        Returns:
            신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(market=market, status="OPEN")
            .order_by(DaytradingSignal.score.desc())
            .limit(limit)
            .all()
        )

    def get_by_date(self, signal_date: date, limit: int = 100) -> List[DaytradingSignal]:
        """
        날짜별 신호 조회

        Args:
            signal_date: 신호 날짜
            limit: 최대 반환 개수

        Returns:
            신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(signal_date=signal_date)
            .order_by(DaytradingSignal.score.desc())
            .limit(limit)
            .all()
        )

    def get_open_signals_by_ticker(self, ticker: str) -> List[DaytradingSignal]:
        """
        종목의 OPEN 상태 신호 조회

        Args:
            ticker: 종목 코드

        Returns:
            OPEN 상태 신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(ticker=ticker, status="OPEN")
            .order_by(DaytradingSignal.signal_date.desc())
            .all()
        )

    def get_top_scorers(self, limit: int = 10) -> List[DaytradingSignal]:
        """
        상위 점수 신호 조회

        Args:
            limit: 최대 반환 개수

        Returns:
            상위 점수 신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(status="OPEN")
            .order_by(DaytradingSignal.score.desc())
            .limit(limit)
            .all()
        )

    def get_by_grade(self, grade: str, limit: int = 50) -> List[DaytradingSignal]:
        """
        등급별 신호 조회

        Args:
            grade: S, A, B, C
            limit: 최대 반환 개수

        Returns:
            등급별 신호 리스트
        """
        return (
            self.session.query(DaytradingSignal)
            .filter_by(grade=grade, status="OPEN")
            .order_by(DaytradingSignal.score.desc())
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        signal_id: int,
        status: str,
        exit_time: Optional[date] = None,
        exit_reason: Optional[str] = None
    ) -> bool:
        """
        신호 상태 업데이트

        Args:
            signal_id: 신호 ID
            status: 새 상태 (OPEN, CLOSED)
            exit_time: 청산 시간
            exit_reason: 청산 사유

        Returns:
            업데이트 성공 여부
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return False

        signal.status = status
        if exit_time:
            signal.exit_time = exit_time
        if exit_reason:
            signal.exit_reason = exit_reason

        self.session.commit()
        return True

    def delete_by_date(self, signal_date: date) -> int:
        """
        날짜별 신호 삭제

        Args:
            signal_date: 삭제할 신호 날짜

        Returns:
            삭제된 레코드 수
        """
        count = (
            self.session.query(DaytradingSignal)
            .filter_by(signal_date=signal_date)
            .delete()
        )
        self.session.commit()
        return count
