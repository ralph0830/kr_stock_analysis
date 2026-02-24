"""
Market Status Repository
시장 상태(Market Gate) 데이터 관리를 위한 Repository
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from src.database.models import MarketStatus
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MarketRepository:
    """Market Status Repository"""

    def __init__(self, session: Session):
        self.session = session

    def get_latest(self) -> Optional[MarketStatus]:
        """
        가장 최신 Market Status 조회

        Returns:
            최신 MarketStatus 또는 None
        """
        return self.session.execute(
            select(MarketStatus)
            .order_by(desc(MarketStatus.date))
            .limit(1)
        ).scalar_one_or_none()

    def get_by_date(self, date: date) -> Optional[MarketStatus]:
        """
        날짜별 Market Status 조회

        Args:
            date: 조회할 날짜

        Returns:
            MarketStatus 또는 None
        """
        return self.session.execute(
            select(MarketStatus)
            .where(MarketStatus.date == date)
        ).scalar_one_or_none()

    def create_or_update(
        self,
        date: date,
        kospi: Optional[float] = None,
        kospi_change_pct: float = 0.0,
        kosdaq: Optional[float] = None,
        kosdaq_change_pct: float = 0.0,
        gate: str = "YELLOW",
        gate_score: int = 50,
        gate_reasons: Optional[str] = None,
        sector_scores: Optional[List[Dict[str, Any]]] = None,
    ) -> MarketStatus:
        """
        Market Status 생성 또는 업데이트

        Args:
            date: 데이터 기준일
            kospi: KOSPI 종가
            kospi_change_pct: KOSPI 변동률 (%)
            kosdaq: KOSDAQ 종가
            kosdaq_change_pct: KOSDAQ 변동률 (%)
            gate: Market Gate 상태 (GREEN, YELLOW, RED)
            gate_score: Gate 점수 (0-100)
            gate_reasons: Gate 상태 사유
            sector_scores: 섹터별 점수 데이터

        Returns:
            생성/업데이트된 MarketStatus
        """
        # 기존 데이터 확인
        existing = self.get_by_date(date)

        if existing:
            # 업데이트
            if kospi is not None:
                existing.kospi = kospi
            existing.kospi_change_pct = kospi_change_pct
            if kosdaq is not None:
                existing.kosdaq = kosdaq
            existing.kosdaq_change_pct = kosdaq_change_pct
            existing.gate = gate
            existing.gate_score = gate_score
            existing.gate_reasons = gate_reasons
            existing.sector_scores = sector_scores
            existing.created_at = datetime.now(timezone.utc)

            self.session.commit()
            self.session.refresh(existing)
            logger.info(f"MarketStatus updated for date={date}")
            return existing
        else:
            # 생성
            market_status = MarketStatus(
                date=date,
                kospi=kospi,
                kospi_change_pct=kospi_change_pct,
                kosdaq=kosdaq,
                kosdaq_change_pct=kosdaq_change_pct,
                gate=gate,
                gate_score=gate_score,
                gate_reasons=gate_reasons,
                sector_scores=sector_scores,
            )
            self.session.add(market_status)
            self.session.commit()
            self.session.refresh(market_status)
            logger.info(f"MarketStatus created for date={date}")
            return market_status

    def calculate_gate_status(
        self,
        kospi_change_pct: float,
        kosdaq_change_pct: float,
        sector_scores: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, int]:
        """
        Market Gate 상태 계산

        Args:
            kospi_change_pct: KOSPI 변동률
            kosdaq_change_pct: KOSDAQ 변동률
            sector_scores: 섹터별 점수

        Returns:
            (gate 상태, gate 점수) 튜플
        """
        # 기본 점수 계산 (KOSPI 40%, KOSDAQ 40%, 섹터 20%)
        score = 50  # 기본 점수

        # KOSPI/KOSDAQ 기여 (각 ±20점)
        if kospi_change_pct > 1.0:
            score += 20
        elif kospi_change_pct > 0:
            score += 10
        elif kospi_change_pct < -1.0:
            score -= 20
        elif kospi_change_pct < 0:
            score -= 10

        if kosdaq_change_pct > 1.0:
            score += 20
        elif kosdaq_change_pct > 0:
            score += 10
        elif kosdaq_change_pct < -1.0:
            score -= 20
        elif kosdaq_change_pct < 0:
            score -= 10

        # 섹터 기여 (±20점)
        if sector_scores:
            bullish_count = sum(1 for s in sector_scores if s.get("change_pct", 0) > 1.0)
            bearish_count = sum(1 for s in sector_scores if s.get("change_pct", 0) < -1.0)
            sector_bonus = (bullish_count - bearish_count) * 5
            score += max(-20, min(20, sector_bonus))

        # 점수를 0-100 범위로 제한
        score = max(0, min(100, score))

        # Gate 상태 결정
        if score >= 70:
            gate = "GREEN"
        elif score >= 40:
            gate = "YELLOW"
        else:
            gate = "RED"

        return gate, score
