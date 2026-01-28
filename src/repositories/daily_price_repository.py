"""
DailyPrice Repository
일봉 데이터 접근 계층
"""

from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from src.repositories.base import BaseRepository
from src.database.models import DailyPrice


class DailyPriceRepository(BaseRepository[DailyPrice]):
    """
    DailyPrice Repository
    일봉 데이터 CRUD 작업 처리
    """

    def __init__(self, session: Session):
        super().__init__(DailyPrice, session)

    def get_by_ticker_and_date_range(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyPrice]:
        """
        종목별 날짜 범위 조회

        Args:
            ticker: 종목 코드 (6자리)
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            DailyPrice 리스트 (날짜 오름차순)
        """
        query = (
            select(DailyPrice)
            .where(
                and_(
                    DailyPrice.ticker == ticker,
                    DailyPrice.date >= start_date,
                    DailyPrice.date <= end_date,
                )
            )
            .order_by(DailyPrice.date.asc())
        )

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_latest_by_ticker(self, ticker: str, limit: int = 1) -> List[DailyPrice]:
        """
        종목 최신 데이터 조회

        Args:
            ticker: 종목 코드
            limit: 최대 반환 수

        Returns:
            최신 DailyPrice 리스트 (날짜 내림차순)
        """
        query = (
            select(DailyPrice)
            .where(DailyPrice.ticker == ticker)
            .order_by(desc(DailyPrice.date))
            .limit(limit)
        )

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_ohlcv_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        OHLCV 데이터 조회 (딕셔너리 리스트 변환)

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            OHLCV 데이터 딕셔너리 리스트 (날짜 오름차순)
        """
        prices = self.get_by_ticker_and_date_range(ticker, start_date, end_date)

        return [
            {
                "date": p.date,
                "open": p.open_price,
                "high": p.high_price,
                "low": p.low_price,
                "close": p.close_price,
                "volume": p.volume,
            }
            for p in prices
        ]

    def get_latest_volume(self, ticker: str) -> Optional[int]:
        """
        종목 최신 거래량 조회

        Args:
            ticker: 종목 코드

        Returns:
            최신 거래량 또는 None (데이터 없음)
        """
        prices = self.get_latest_by_ticker(ticker, limit=1)
        if prices:
            return prices[0].volume
        return None
