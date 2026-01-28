"""
Stock Repository
종목 관련 데이터 접근 계층
"""

from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_
from src.repositories.base import BaseRepository
from src.database.models import Stock, InstitutionalFlow


class StockRepository(BaseRepository[Stock]):
    """
    Stock Repository
    종목 데이터 CRUD 작업 처리
    """

    def __init__(self, session: Session):
        super().__init__(Stock, session)

    def get_by_ticker(self, ticker: str) -> Optional[Stock]:
        """
        종목 코드로 조회

        Args:
            ticker: 종목 코드 (6자리)

        Returns:
            Stock 인스턴스 또는 None
        """
        query = select(Stock).where(Stock.ticker == ticker)
        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def list_all(
        self,
        market: Optional[str] = None,
        sector: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Stock]:
        """
        전체 종목 목록 조회 (with filters)

        Args:
            market: 시장 필터 (KOSPI/KOSDAQ)
            sector: 섹터 필터
            limit: 최대 반환 수

        Returns:
            Stock 리스트
        """
        query = select(Stock)

        if market:
            query = query.where(Stock.market == market)
        if sector:
            query = query.where(Stock.sector == sector)

        query = query.limit(limit)
        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_by_market(self, market: str) -> List[Stock]:
        """시장별 종목 목록"""
        return self.list_all(market=market)

    def get_by_sector(self, sector: str) -> List[Stock]:
        """섹터별 종목 목록"""
        return self.list_all(sector=sector)

    def search(self, keyword: str, limit: int = 50) -> List[Stock]:
        """
        종목 검색 (이름 또는 티커)

        Args:
            keyword: 검색어
            limit: 최대 반환 수

        Returns:
            검색된 Stock 리스트
        """
        query = select(Stock).where(
            or_(
                Stock.name.ilike(f"%{keyword}%"),
                Stock.ticker.ilike(f"%{keyword}%")
            )
        ).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def create_if_not_exists(self, **kwargs) -> Stock:
        """
        종목 생성 (이미 존재하면 조회만)

        Args:
            **kwargs: 종목 정보

        Returns:
            생성되거나 기존 Stock 인스턴스
        """
        ticker = kwargs.get("ticker")
        existing = self.get_by_ticker(ticker)
        if existing:
            return existing

        return self.create(**kwargs)

    def get_etf_list(self) -> List[Stock]:
        """ETF 종목 목록"""
        return self.get_all(is_etf=True)

    def get_admin_list(self) -> List[Stock]:
        """관리종목 목록"""
        return self.get_all(is_admin=True)

    def update_market_cap(self, ticker: str, market_cap: int) -> Optional[Stock]:
        """시가총액 업데이트"""
        stock = self.get_by_ticker(ticker)
        if stock:
            stock.market_cap = market_cap
            self.session.commit()
            self.session.refresh(stock)
        return stock

    def get_institutional_flow(
        self, ticker: str, days: int = 20
    ) -> List[InstitutionalFlow]:
        """
        종목 수급 데이터 조회 (기간별)

        Args:
            ticker: 종목 코드 (6자리)
            days: 조회 기간 (일수, 기본 20일, 최대 60일)

        Returns:
            InstitutionalFlow 리스트 (날짜 오름차순)
        """
        # 최대 60일 제한
        days = min(days, 60)

        # 조회 기간 계산
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 쿼리 생성
        query = select(InstitutionalFlow).where(
            and_(
                InstitutionalFlow.ticker == ticker,
                InstitutionalFlow.date >= start_date,
                InstitutionalFlow.date <= end_date,
            )
        ).order_by(InstitutionalFlow.date.asc())

        # 실행
        result = self.session.execute(query)
        return list(result.scalars().all())
