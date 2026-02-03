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
            logger.info("✅ KRXCollector initialized with pykrx")
        else:
            self.stock = None
            logger.warning("⚠️ pykrx not available, KRXCollector in Mock mode")

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
        # Mock 모드
        if not self._pykrx_available or self.stock is None:
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
            logger.error(f"❌ KRX 종목 목록 조회 실패: {e}, falling back to mock")
            return self._get_mock_stock_list(market)

    def _get_mock_stock_list(self, market: str) -> List[Dict[str, Any]]:
        """Mock 종목 목록 생성"""
        mock_stocks = {
            "KOSPI": [
                {"ticker": "005930", "name": "삼성전자", "market": "KOSPI", "sector": "반도체", "marcap": 500000000},
                {"ticker": "000660", "name": "SK하이닉스", "market": "KOSPI", "sector": "반도체", "marcap": 100000000},
                {"ticker": "035420", "name": "NAVER", "market": "KOSPI", "sector": "서비스", "marcap": 50000000},
            ],
            "KOSDAQ": [
                {"ticker": "051910", "name": "LG화학", "market": "KOSDAQ", "sector": "화학", "marcap": 30000000},
                {"ticker": "068270", "name": "셀트리온", "market": "KOSDAQ", "sector": "바이오", "marcap": 20000000},
            ],
            "KONEX": [
                {"ticker": "235590", "name": "알체라", "market": "KONEX", "sector": "바이오", "marcap": 1000000},
            ],
        }
        result = mock_stocks.get(market, mock_stocks["KOSPI"])
        logger.info(f"📋 {market} Mock 종목 {len(result)}개 반환")
        return result

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

        # Mock 모드
        if not self._pykrx_available or self.stock is None:
            return self._get_mock_daily_prices(ticker, start_date, end_date)

        try:
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            df = self.stock.get_market_ohlcv_by_date(start_str, end_str, ticker)

            # 컬럼명 정규화 (pykrx는 '날짜' 인덱스 + ['시가', '고가', '저가', '종가', '거래량', '등락률'] 컬럼 반환)
            df = df.reset_index()
            # 필요한 컬럼만 선택하고 이름 변경 (등락률 제외)
            df = df.rename(columns={
                "날짜": "date",
                "시가": "open",
                "고가": "high",
                "저가": "low",
                "종가": "close",
                "거래량": "volume",
            })
            df = df[["date", "open", "high", "low", "close", "volume"]]  # 등락률 컬럼 제외
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["ticker"] = ticker

            logger.info(f"✅ {ticker} 일봉 데이터 {len(df)}개 조회 완료")
            return df

        except Exception as e:
            logger.error(f"❌ {ticker} 일봉 데이터 조회 실패: {e}, falling back to mock")
            return self._get_mock_daily_prices(ticker, start_date, end_date)

    def _get_mock_daily_prices(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Mock 일봉 데이터 생성"""
        import random

        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        # 주말 제거
        dates = [d for d in dates if d.weekday() < 5]

        data = []
        base_price = 50000 if ticker == "005930" else 100000

        for dt in dates:
            # 종가 기준으로 생성 (OHLC 관계 보장)
            close = base_price + random.randint(-5000, 5000)
            open_price = close + random.randint(-1000, 1000)

            # high는 open/close 중 최대값 + random
            max_oc = max(open_price, close)
            high = max_oc + random.randint(0, 500)

            # low는 open/close 중 최소값 - random
            min_oc = min(open_price, close)
            low = min_oc - random.randint(0, 500)

            volume = random.randint(100000, 10000000)

            data.append({
                "date": dt.date(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "ticker": ticker,
            })

        df = pd.DataFrame(data)
        logger.info(f"📊 {ticker} Mock 일봉 데이터 {len(df)}개 반환")
        return df

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

        # Mock 모드
        if not self._pykrx_available or self.stock is None:
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
            logger.error(f"❌ {ticker} 수급 데이터 조회 실패: {e}, falling back to mock")
            return self._get_mock_supply_demand(ticker, start_date, end_date)

    def _get_mock_supply_demand(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Mock 수급 데이터 생성"""
        import random

        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        # 주말 제거
        dates = [d for d in dates if d.weekday() < 5]

        data = []
        for dt in dates:
            data.append({
                "date": dt.date(),
                "ticker": ticker,
                "foreign_net_buy": random.randint(-1000000000, 1000000000),
                "inst_net_buy": random.randint(-500000000, 500000000),
            })

        df = pd.DataFrame(data)
        logger.info(f"💰 {ticker} Mock 수급 데이터 {len(df)}개 반환")
        return df

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
