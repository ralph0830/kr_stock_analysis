"""
BaseCollector 추상 클래스 단위 테스트
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock
import pandas as pd

from src.collectors.base import BaseCollector


class TestBaseCollectorAbstract:
    """BaseCollector 추상 메서드 테스트"""

    def test_abstract_methods(self):
        """추상 메서드 확인"""
        abstract_methods = BaseCollector.__abstractmethods__

        # 필수 추상 메서드 확인
        assert "fetch_stock_list" in abstract_methods
        assert "fetch_daily_prices" in abstract_methods
        assert "fetch_supply_demand" in abstract_methods

    def test_cannot_instantiate(self):
        """추상 클래스는 직접 인스턴스화 불가"""
        with pytest.raises(TypeError):
            BaseCollector()


class TestBaseCollectorConcrete:
    """BaseCollector 구현 테스트"""

    @pytest.fixture
    def concrete_collector(self):
        """BaseCollector를 상속받은 구현체 fixture"""

        class ConcreteCollector(BaseCollector):
            """테스트용 구현체"""

            def fetch_stock_list(self, market: str = "KOSPI"):
                return [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "market": market,
                        "sector": "반도체",
                        "marcap": 500000000000,
                    }
                ]

            def fetch_daily_prices(
                self,
                ticker: str,
                start_date: date = None,
                end_date: date = None,
            ):
                start, end = self.validate_date_range(start_date, end_date)
                dates = pd.date_range(start, end, freq="D")

                return pd.DataFrame({
                    "date": dates.date,
                    "ticker": ticker,
                    "open": [70000] * len(dates),
                    "high": [71000] * len(dates),
                    "low": [69000] * len(dates),
                    "close": [70500] * len(dates),
                    "volume": [1000000] * len(dates),
                })

            def fetch_supply_demand(
                self,
                ticker: str,
                start_date: date = None,
                end_date: date = None,
            ):
                start, end = self.validate_date_range(start_date, end_date)
                dates = pd.date_range(start, end, freq="D")

                return pd.DataFrame({
                    "date": dates.date,
                    "ticker": ticker,
                    "foreign_net_buy": [100000] * len(dates),
                    "inst_net_buy": [50000] * len(dates),
                })

        return ConcreteCollector()

    def test_concrete_can_instantiate(self, concrete_collector):
        """구현체는 인스턴스화 가능"""
        assert concrete_collector is not None
        assert isinstance(concrete_collector, BaseCollector)

    def test_concrete_fetch_stock_list(self, concrete_collector):
        """구현체의 fetch_stock_list 테스트"""
        stocks = concrete_collector.fetch_stock_list("KOSPI")

        assert isinstance(stocks, list)
        assert len(stocks) > 0
        assert stocks[0]["ticker"] == "005930"

    def test_concrete_fetch_daily_prices(self, concrete_collector):
        """구현체의 fetch_daily_prices 테스트"""
        df = concrete_collector.fetch_daily_prices("005930")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "ticker" in df.columns

    def test_concrete_fetch_supply_demand(self, concrete_collector):
        """구현체의 fetch_supply_demand 테스트"""
        df = concrete_collector.fetch_supply_demand("005930")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "ticker" in df.columns


class TestNormalizeTicker:
    """종목코드 정규화 테스트"""

    @pytest.fixture
    def concrete_collector(self):
        class ConcreteCollector(BaseCollector):
            def fetch_stock_list(self, market: str = "KOSPI"):
                return []
            def fetch_daily_prices(self, ticker: str, start_date: date = None, end_date: date = None):
                return pd.DataFrame()
            def fetch_supply_demand(self, ticker: str, start_date: date = None, end_date: date = None):
                return pd.DataFrame()

        return ConcreteCollector()

    def test_normalize_ticker_six_digits(self, concrete_collector):
        """6자리 티커 (이미 정규화됨)"""
        result = concrete_collector.normalize_ticker("005930")
        assert result == "005930"

    def test_normalize_ticker_four_digits(self, concrete_collector):
        """4자리 티커 (zero-padding 필요)"""
        result = concrete_collector.normalize_ticker("5930")
        assert result == "005930"

    def test_normalize_ticker_five_digits(self, concrete_collector):
        """5자리 티커"""
        result = concrete_collector.normalize_ticker("05930")
        assert result == "005930"

    def test_normalize_ticker_with_spaces(self, concrete_collector):
        """공백 포함 티커"""
        result = concrete_collector.normalize_ticker(" 5930 ")
        assert result == "005930"

    def test_normalize_ticker_various_formats(self, concrete_collector):
        """다양한 형식의 티커 정규화"""
        test_cases = [
            ("5930", "005930"),
            ("005930", "005930"),
            (" 000660 ", "000660"),
            ("930", "000930"),
            ("660", "000660"),
        ]

        for input_ticker, expected in test_cases:
            result = concrete_collector.normalize_ticker(input_ticker)
            assert result == expected, f"Input: {input_ticker}, Expected: {expected}, Got: {result}"


class TestValidateDateRange:
    """날짜 범위 검증 테스트"""

    @pytest.fixture
    def concrete_collector(self):
        class ConcreteCollector(BaseCollector):
            def fetch_stock_list(self, market: str = "KOSPI"):
                return []
            def fetch_daily_prices(self, ticker: str, start_date: date = None, end_date: date = None):
                return pd.DataFrame()
            def fetch_supply_demand(self, ticker: str, start_date: date = None, end_date: date = None):
                return pd.DataFrame()

        return ConcreteCollector()

    def test_validate_both_none(self, concrete_collector):
        """start_date와 end_date가 모두 None인 경우"""
        start, end = concrete_collector.validate_date_range(None, None)

        assert end == date.today()
        assert start == end - pd.Timedelta(days=365)  # 기본 1년

    def test_validate_end_date_only(self, concrete_collector):
        """end_date만 지정한 경우"""
        custom_end = date(2024, 6, 30)
        start, end = concrete_collector.validate_date_range(None, custom_end)

        assert end == custom_end
        assert start == end - pd.Timedelta(days=365)

    def test_validate_start_date_only(self, concrete_collector):
        """start_date만 지정한 경우"""
        custom_start = date(2024, 1, 1)
        start, end = concrete_collector.validate_date_range(custom_start, None)

        assert start == custom_start
        assert end == date.today()

    def test_validate_both_dates(self, concrete_collector):
        """두 날짜 모두 지정한 경우"""
        custom_start = date(2024, 1, 1)
        custom_end = date(2024, 6, 30)

        start, end = concrete_collector.validate_date_range(custom_start, custom_end)

        assert start == custom_start
        assert end == custom_end

    def test_validate_custom_default_days(self, concrete_collector):
        """사용자 정의 기본 일수"""
        start, end = concrete_collector.validate_date_range(None, None, default_days=30)

        assert end == date.today()
        expected_start = date.today() - pd.Timedelta(days=30)
        assert start == expected_start

    def test_validate_date_order(self, concrete_collector):
        """날짜 순서 검증"""
        start = date(2024, 6, 1)
        end = date(2024, 6, 30)

        validated_start, validated_end = concrete_collector.validate_date_range(start, end)

        # 시작일이 종료일보다 빨라야 함
        assert validated_start <= validated_end

    def test_validate_same_date(self, concrete_collector):
        """같은 날짜 지정"""
        same_date = date(2024, 6, 15)

        start, end = concrete_collector.validate_date_range(same_date, same_date)

        assert start == same_date
        assert end == same_date


class TestBaseCollectorIntegration:
    """BaseCollector 통합 테스트"""

    @pytest.fixture
    def concrete_collector(self):
        class ConcreteCollector(BaseCollector):
            def fetch_stock_list(self, market: str = "KOSPI"):
                return [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "market": market,
                        "sector": "반도체",
                        "marcap": 500000000000,
                    }
                ]

            def fetch_daily_prices(
                self,
                ticker: str,
                start_date: date = None,
                end_date: date = None,
            ):
                start, end = self.validate_date_range(start_date, end_date, default_days=10)
                dates = pd.date_range(start, end, freq="D")

                data = []
                for dt in dates:
                    data.append({
                        "date": dt.date(),
                        "ticker": ticker,
                        "open": 70000 + (dt.day % 10) * 100,
                        "high": 71000 + (dt.day % 10) * 100,
                        "low": 69000 + (dt.day % 10) * 100,
                        "close": 70500 + (dt.day % 10) * 100,
                        "volume": 1000000,
                    })

                return pd.DataFrame(data)

            def fetch_supply_demand(
                self,
                ticker: str,
                start_date: date = None,
                end_date: date = None,
            ):
                start, end = self.validate_date_range(start_date, end_date, default_days=10)
                dates = pd.date_range(start, end, freq="D")

                return pd.DataFrame({
                    "date": dates.date,
                    "ticker": ticker,
                    "foreign_net_buy": [100000 * (1 if i % 2 == 0 else -1) for i in range(len(dates))],
                    "inst_net_buy": [50000 * (1 if i % 3 == 0 else -1) for i in range(len(dates))],
                })

        return ConcreteCollector()

    def test_full_workflow(self, concrete_collector):
        """전체 워크플로우 테스트"""
        # 1. 종목 목록 조회
        stocks = concrete_collector.fetch_stock_list("KOSPI")
        assert len(stocks) > 0
        ticker = stocks[0]["ticker"]

        # 2. 일봉 데이터 조회 (티커 정규화 포함)
        df_prices = concrete_collector.fetch_daily_prices(ticker)
        assert len(df_prices) > 0
        assert df_prices["ticker"].iloc[0] == ticker

        # 3. 수급 데이터 조회
        df_supply = concrete_collector.fetch_supply_demand(ticker)
        assert len(df_supply) > 0
        assert df_supply["ticker"].iloc[0] == ticker

    def test_date_range_workflow(self, concrete_collector):
        """날짜 범위 워크플로우 테스트"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 15)

        # 일봉 데이터 조회
        df_prices = concrete_collector.fetch_daily_prices("005930", start, end)
        assert df_prices["date"].min() >= start
        assert df_prices["date"].max() <= end

        # 수급 데이터 조회
        df_supply = concrete_collector.fetch_supply_demand("005930", start, end)
        assert df_supply["date"].min() >= start
        assert df_supply["date"].max() <= end

    def test_normalize_ticker_in_workflow(self, concrete_collector):
        """워크플로우에서 티커 정규화 테스트"""
        # 다양한 형식의 티커 입력
        tickers = ["5930", "005930", " 5930", "000660"]

        for ticker in tickers:
            df = concrete_collector.fetch_daily_prices(ticker)
            # ticker 컬럼이 존재하는지 확인
            assert "ticker" in df.columns
            # ticker 값이 문자열인지 확인
            assert isinstance(df["ticker"].iloc[0], str)
