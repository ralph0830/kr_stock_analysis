"""
KRX Data Collector
KRX(한국거래소) 데이터 수집 - pykrx 래퍼
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class KRXCollector:
    """
    KRX 데이터 수집기

    pykrx 라이브러리를 래핑하여 한국 주식 데이터 수집
    """

    def __init__(self):
        """KRXCollector 초기화"""
        self._pykrx_available = self._check_pykrx()
        if self._pykrx_available:
            from pykrx import stock
            self.stock = stock
        else:
            self.stock = None
            logger.warning("pykrx not available, using mock data")

    def _check_pykrx(self) -> bool:
        """pykrx 사용 가능 여부 확인"""
        try:
            import pykrx
            return True
        except ImportError:
            return False

    def fetch_stock_list(self, market: str = "KOSPI") -> List[Dict[str, Any]]:
        """
        종목 마스터 조회

        Args:
            market: 시장 구분 (KOSPI, KOSDAQ, KONEX)

        Returns:
            종목 정보 리스트 [{ticker, name, market, sector, marcap}]
        """
        if not self._pykrx_available:
            return self._get_mock_stock_list(market)

        try:
            tickers = self.stock.get_market_ticker_list(market=market)
            stocks = []

            for ticker in tickers:
                name = self.stock.get_market_ticker_name(ticker)

                # 기본 정보
                stock_info = {
                    "ticker": ticker.zfill(6),
                    "name": name,
                    "market": market,
                    "sector": "",
                    "marcap": 0,
                }

                stocks.append(stock_info)

            logger.info(f"✅ {market} 종목 {len(stocks)}개 조회 완료")
            return stocks

        except Exception as e:
            logger.error(f"❌ KRX 종목 목록 조회 실패: {e}")
            return self._get_mock_stock_list(market)

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
        ticker = ticker.zfill(6)
        start_date, end_date = self._validate_date_range(start_date, end_date)

        if not self._pykrx_available:
            return self._get_mock_daily_prices(ticker, start_date, end_date)

        try:
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            df = self.stock.get_market_ohlcv_by_date(start_str, end_str, ticker)

            # 컬럼명 정규화
            df = df.reset_index()
            df.columns = ["date", "open", "high", "low", "close", "volume"]
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["ticker"] = ticker

            logger.info(f"✅ {ticker} 일봉 데이터 {len(df)}개 조회 완료")
            return df

        except Exception as e:
            logger.error(f"❌ {ticker} 일봉 데이터 조회 실패: {e}")
            return self._get_mock_daily_prices(ticker, start_date, end_date)

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
        ticker = ticker.zfill(6)
        start_date, end_date = self._validate_date_range(start_date, end_date)

        if not self._pykrx_available:
            return self._get_mock_supply_demand(ticker, start_date, end_date)

        try:
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            # 외국인/기관 순매수 거래량
            df = self.stock.get_market_trading_value_by_date(start_str, end_str, ticker)

            # 필요한 컬럼만 추출
            df = df.reset_index()
            df = df.rename(columns={"날짜": "date"})
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["ticker"] = ticker

            logger.info(f"✅ {ticker} 수급 데이터 {len(df)}개 조회 완료")
            return df

        except Exception as e:
            logger.error(f"❌ {ticker} 수급 데이터 조회 실패: {e}")
            return self._get_mock_supply_demand(ticker, start_date, end_date)

    def _validate_date_range(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        default_days: int = 365,
    ) -> tuple[date, date]:
        """날짜 범위 검증"""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=default_days)
        return start_date, end_date

    def _get_mock_stock_list(self, market: str) -> List[Dict[str, Any]]:
        """목업 종목 목록 (테스트용)"""
        return [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "market": market,
                "sector": "반도체",
                "marcap": 500000000000,
            },
            {
                "ticker": "000660",
                "name": "SK하이닉스",
                "market": market,
                "sector": "반도체",
                "marcap": 100000000000,
            },
        ]

    def _get_mock_daily_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """목업 일봉 데이터 (테스트용)"""
        dates = pd.date_range(start_date, end_date, freq="D")
        data = []

        base_price = 70000
        for dt in dates:
            price = base_price + (dt.dayofyear % 1000) * 10
            data.append(
                {
                    "date": dt.date(),
                    "ticker": ticker,
                    "open": price * 0.99,
                    "high": price * 1.01,
                    "low": price * 0.98,
                    "close": price,
                    "volume": 1000000,
                }
            )

        return pd.DataFrame(data)

    def _get_mock_supply_demand(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """목업 수급 데이터 (테스트용)"""
        dates = pd.date_range(start_date, end_date, freq="D")
        data = []

        for dt in dates:
            data.append(
                {
                    "date": dt.date(),
                    "ticker": ticker,
                    "foreign_net_buy": 100000 * (1 if dt.day % 2 == 0 else -1),
                    "inst_net_buy": 50000 * (1 if dt.day % 3 == 0 else -1),
                }
            )

        return pd.DataFrame(data)
