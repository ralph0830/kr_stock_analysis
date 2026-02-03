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

    def upsert_ohlc(
        self,
        ticker: str,
        trade_date: date,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
        foreign_net_buy: int = 0,
        inst_net_buy: int = 0,
    ) -> DailyPrice:
        """
        OHLC 데이터 삽입 또는 업데이트 (Upsert)

        기존 레코드가 있으면 OHLC를 갱신하고, 없으면 새로 생성합니다.
        실시간 데이터 수집 시 호출 횟수를 줄이기 위해 마지막 저장 시간을 추적합니다.

        Args:
            ticker: 종목 코드 (6자리)
            trade_date: 거래 날짜
            open_price: 시가
            high_price: 고가
            low_price: 저가
            close_price: 종가
            volume: 거래량
            foreign_net_buy: 외국인 순매수 (선택)
            inst_net_buy: 기관 순매수 (선택)

        Returns:
            저장된 DailyPrice 객체
        """
        # 기존 레코드 조회
        existing = self.session.execute(
            select(DailyPrice).where(
                and_(
                    DailyPrice.ticker == ticker,
                    DailyPrice.date == trade_date,
                )
            )
        ).scalar_one_or_none()

        if existing:
            # 기존 레코드 업데이트 (실시간 갱신)
            existing.open_price = min(existing.open_price or float('inf'), open_price)
            existing.high_price = max(existing.high_price or 0, high_price)
            existing.low_price = min(existing.low_price or float('inf'), low_price)
            existing.close_price = close_price
            existing.volume = volume
            if foreign_net_buy != 0:
                existing.foreign_net_buy = foreign_net_buy
            if inst_net_buy != 0:
                existing.inst_net_buy = inst_net_buy
            self.session.flush()
            return existing
        else:
            # 새 레코드 생성
            new_price = DailyPrice(
                ticker=ticker,
                date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                foreign_net_buy=foreign_net_buy,
                inst_net_buy=inst_net_buy,
            )
            self.session.add(new_price)
            self.session.flush()
            return new_price

    def update_realtime_bar(
        self,
        ticker: str,
        trade_date: date,
        price: float,
        volume: int,
        is_first_trade: bool = False,
    ) -> DailyPrice:
        """
        실시간 체결 데이터로 OHLC 바 업데이트

        새로운 체결가가 들어올 때마다 호출하여 OHLC를 갱신합니다.

        Args:
            ticker: 종목 코드
            trade_date: 거래 날짜
            price: 체결가
            volume: 누적 거래량
            is_first_trade: 장 시작 첫 거래 여부 (시가 설정용)

        Returns:
            업데이트된 DailyPrice 객체
        """
        existing = self.session.execute(
            select(DailyPrice).where(
                and_(
                    DailyPrice.ticker == ticker,
                    DailyPrice.date == trade_date,
                )
            )
        ).scalar_one_or_none()

        if existing:
            # 기존 바 업데이트
            if is_first_trade and existing.open_price is None:
                existing.open_price = price
            existing.high_price = max(existing.high_price or 0, price)
            existing.low_price = min(existing.low_price or float('inf'), price) if existing.low_price is not None else price
            existing.close_price = price
            existing.volume = volume
            self.session.flush()
            return existing
        else:
            # 새 바 생성 (장 시작 첫 거래)
            new_price = DailyPrice(
                ticker=ticker,
                date=trade_date,
                open_price=price,
                high_price=price,
                low_price=price,
                close_price=price,
                volume=volume,
            )
            self.session.add(new_price)
            self.session.flush()
            return new_price
