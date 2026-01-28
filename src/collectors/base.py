"""
Base Collector Interface
데이터 수집기 추상 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date
import pandas as pd


class BaseCollector(ABC):
    """
    데이터 수집기 추상 베이스 클래스

    모든 데이터 수집기는 이 클래스를 상속받아야 합니다.
    """

    @abstractmethod
    def fetch_stock_list(self, market: str = "KOSPI") -> List[Dict[str, Any]]:
        """
        종목 마스터 조회

        Args:
            market: 시장 구분 (KOSPI, KOSDAQ, KONEX)

        Returns:
            종목 정보 리스트 [{ticker, name, market, sector, marcap}]
        """
        pass

    @abstractmethod
    def fetch_daily_prices(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        일별 시세 조회

        Args:
            ticker: 종목코드
            start_date: 시작일 (None이면 최근 1년)
            end_date: 종료일 (None이면 오늘)

        Returns:
            일별 시세 DataFrame
            컬럼: [date, open, high, low, close, volume]
        """
        pass

    @abstractmethod
    def fetch_supply_demand(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        외국인/기관 수급 데이터 조회

        Args:
            ticker: 종목코드
            start_date: 시작일
            end_date: 종료일

        Returns:
            수급 데이터 DataFrame
            컬럼: [date, foreign_net_buy, inst_net_buy, ...]
        """
        pass

    def normalize_ticker(self, ticker: str) -> str:
        """
        종목코드 정규화 (6자리 zero-padding)

        Args:
            ticker: 종목코드

        Returns:
            6자리 종목코드
        """
        return ticker.strip().zfill(6)

    def validate_date_range(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        default_days: int = 365,
    ) -> tuple[date, date]:
        """
        날짜 범위 검증 및 기본값 설정

        Args:
            start_date: 시작일
            end_date: 종료일
            default_days: 기본 일수

        Returns:
            (start_date, end_date) 튜플
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - pd.Timedelta(days=default_days)
        return start_date, end_date
