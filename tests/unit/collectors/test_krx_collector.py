"""
KRXCollector 단위 테스트
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from src.collectors.krx_collector import KRXCollector


class TestKRXCollectorInitialization:
    """KRXCollector 초기화 테스트"""

    def test_init_with_pykrx(self):
        """pykrx가 있을 때 초기화 테스트"""
        # 실제 pykrx import 여부는 환경에 따라 다름
        collector = KRXCollector()
        assert collector is not None

    def test_init_without_pykrx(self):
        """pykrx가 없을 때 Mock 모드 테스트"""
        with patch('src.collectors.krx_collector.KRXCollector._check_pykrx', return_value=False):
            collector = KRXCollector()
            assert collector._pykrx_available is False
            assert collector.stock is None

    def test_check_pykrx_available(self):
        """pykrx 사용 가능 여부 확인 테스트"""
        collector = KRXCollector()
        # 결과는 불리언이어야 함
        assert isinstance(collector._pykrx_available, bool)


class TestKRXCollectorFetchStockList:
    """종목 마스터 조회 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    def test_fetch_stock_list_mock_mode(self, collector):
        """Mock 모드로 종목 목록 조회"""
        stocks = collector.fetch_stock_list("KOSPI")

        assert isinstance(stocks, list)
        assert len(stocks) > 0

        # 데이터 구조 확인
        for stock in stocks:
            assert "ticker" in stock
            assert "name" in stock
            assert "market" in stock
            assert stock["market"] == "KOSPI"

    def test_fetch_stock_list_kosdaq(self, collector):
        """KOSDAQ 종목 목록 조회"""
        stocks = collector.fetch_stock_list("KOSDAQ")

        assert isinstance(stocks, list)
        assert len(stocks) > 0

        for stock in stocks:
            assert stock["market"] == "KOSDAQ"

    def test_fetch_stock_list_konex(self, collector):
        """KONEX 종목 목록 조회"""
        stocks = collector.fetch_stock_list("KONEX")

        assert isinstance(stocks, list)

    @patch('src.collectors.krx_collector.KRXCollector._check_pykrx', return_value=True)
    def test_fetch_stock_list_with_pykrx(self, mock_check, collector):
        """pykrx가 있을 때 종목 목록 조회"""
        # Mock stock module
        mock_stock = MagicMock()
        mock_stock.get_market_ticker_list.return_value = ["005930", "000660"]
        mock_stock.get_market_ticker_name.side_effect = lambda x: "삼성전자" if x == "005930" else "SK하이닉스"

        collector.stock = mock_stock
        stocks = collector.fetch_stock_list("KOSPI")

        assert len(stocks) == 2
        assert stocks[0]["ticker"] == "005930"
        assert stocks[0]["name"] == "삼성전자"
        assert stocks[1]["ticker"] == "000660"
        assert stocks[1]["name"] == "SK하이닉스"


class TestKRXCollectorFetchDailyPrices:
    """일별 시세 조회 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    def test_fetch_daily_prices_default_range(self, collector):
        """기본 날짜 범위로 시세 조회"""
        df = collector.fetch_daily_prices("005930")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # 필수 컬럼 확인
        required_cols = ["date", "open", "high", "low", "close", "volume", "ticker"]
        for col in required_cols:
            assert col in df.columns

    def test_fetch_daily_prices_custom_range(self, collector):
        """사용자 지정 날짜 범위로 시세 조회"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        df = collector.fetch_daily_prices("005930", start_date=start, end_date=end)

        assert isinstance(df, pd.DataFrame)
        # 날짜 범위 내의 데이터 확인
        if len(df) > 0:
            assert df["date"].min() >= start
            assert df["date"].max() <= end

    def test_fetch_daily_prices_ticker_normalization(self, collector):
        """종목코드 정규화 테스트 (6자리)"""
        # 4자리 종목코드
        df1 = collector.fetch_daily_prices("5930")
        assert "ticker" in df1.columns
        assert df1["ticker"].iloc[0] == "005930"  # zero-padding 확인

        # 6자리 종목코드
        df2 = collector.fetch_daily_prices("005930")
        assert df2["ticker"].iloc[0] == "005930"

    def test_fetch_daily_prices_returns_dataframe(self, collector):
        """DataFrame 형식 반환 확인"""
        df = collector.fetch_daily_prices("005930")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # 데이터 타입 확인
        assert df["open"].dtype in [float, int]
        assert df["high"].dtype in [float, int]
        assert df["low"].dtype in [float, int]
        assert df["close"].dtype in [float, int]
        assert df["volume"].dtype in [int]


class TestKRXCollectorFetchSupplyDemand:
    """수급 데이터 조회 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    def test_fetch_supply_demand_default_range(self, collector):
        """기본 날짜 범위로 수급 데이터 조회"""
        df = collector.fetch_supply_demand("005930")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # 필수 컬럼 확인
        required_cols = ["date", "ticker"]
        for col in required_cols:
            assert col in df.columns

    def test_fetch_supply_demand_custom_range(self, collector):
        """사용자 지정 날짜 범위로 수급 데이터 조회"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        df = collector.fetch_supply_demand("005930", start_date=start, end_date=end)

        assert isinstance(df, pd.DataFrame)
        if len(df) > 0:
            assert df["date"].min() >= start
            assert df["date"].max() <= end


class TestKRXCollectorDateValidation:
    """날짜 검증 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    def test_validate_date_range_default(self, collector):
        """기본 날짜 범위 검증"""
        start, end = collector._validate_date_range(None, None)

        assert end == date.today()
        assert isinstance(start, date)
        assert isinstance(end, date)

    def test_validate_date_range_custom(self, collector):
        """사용자 지정 날짜 검증"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        validated_start, validated_end = collector._validate_date_range(start, end)

        assert validated_start == start
        assert validated_end == end

    def test_validate_date_range_partial(self, collector):
        """부분 날짜 지정 검증"""
        start = date(2024, 1, 1)
        end = None

        validated_start, validated_end = collector._validate_date_range(start, end)

        assert validated_start == start
        assert validated_end == date.today()

    def test_validate_date_range_custom_days(self, collector):
        """사용자 지정 일수 검증"""
        start, end = collector._validate_date_range(None, None, default_days=30)

        # 대략 30일 전이어야 함
        expected_start = date.today() - timedelta(days=30)
        assert start == expected_start
        assert end == date.today()


class TestKRXCollectorMockData:
    """Mock 데이터 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    def test_mock_stock_list_structure(self, collector):
        """Mock 종목 목록 구조 확인"""
        stocks = collector._get_mock_stock_list("KOSPI")

        assert len(stocks) >= 2  # 최소 2개 종목

        # 삼성전자 확인
        samsung = next(s for s in stocks if s["ticker"] == "005930")
        assert samsung["name"] == "삼성전자"
        assert samsung["market"] == "KOSPI"
        assert samsung["sector"] == "반도체"

    def test_mock_daily_prices_structure(self, collector):
        """Mock 일봉 데이터 구조 확인"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 10)

        df = collector._get_mock_daily_prices("005930", start, end)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # 컬럼 확인
        required_cols = ["date", "ticker", "open", "high", "low", "close", "volume"]
        for col in required_cols:
            assert col in df.columns

        # 데이터 논리성 확인
        for _, row in df.iterrows():
            assert row["high"] >= row["low"]  # 고가 >= 저가
            assert row["high"] >= row["open"]  # 고가 >= 시가
            assert row["high"] >= row["close"]  # 고가 >= 종가
            assert row["volume"] > 0

    def test_mock_supply_demand_structure(self, collector):
        """Mock 수급 데이터 구조 확인"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 10)

        df = collector._get_mock_supply_demand("005930", start, end)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # 컬럼 확인
        assert "date" in df.columns
        assert "ticker" in df.columns
        assert "foreign_net_buy" in df.columns
        assert "inst_net_buy" in df.columns


class TestKRXCollectorErrorHandling:
    """에러 핸들링 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    @patch('src.collectors.krx_collector.KRXCollector._check_pykrx', return_value=True)
    def test_fetch_stock_list_fallback_to_mock(self, mock_check, collector):
        """pykrx 호출 실패 시 Mock으로 fallback"""
        # Mock stock module that raises exception
        mock_stock = MagicMock()
        mock_stock.get_market_ticker_list.side_effect = Exception("Network error")

        collector.stock = mock_stock
        stocks = collector.fetch_stock_list("KOSPI")

        # Mock 데이터가 반환되어야 함
        assert isinstance(stocks, list)
        assert len(stocks) > 0
        assert stocks[0]["ticker"] == "005930"

    @patch('src.collectors.krx_collector.KRXCollector._check_pykrx', return_value=True)
    def test_fetch_daily_prices_fallback_to_mock(self, mock_check, collector):
        """일봉 조회 실패 시 Mock으로 fallback"""
        mock_stock = MagicMock()
        mock_stock.get_market_ohlcv_by_date.side_effect = Exception("API error")

        collector.stock = mock_stock
        df = collector.fetch_daily_prices("005930")

        # Mock 데이터가 반환되어야 함
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    @patch('src.collectors.krx_collector.KRXCollector._check_pykrx', return_value=True)
    def test_fetch_supply_demand_fallback_to_mock(self, mock_check, collector):
        """수급 데이터 조회 실패 시 Mock으로 fallback"""
        mock_stock = MagicMock()
        mock_stock.get_market_trading_value_by_date.side_effect = Exception("API error")

        collector.stock = mock_stock
        df = collector.fetch_supply_demand("005930")

        # Mock 데이터가 반환되어야 함
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


class TestKRXCollectorDataQuality:
    """데이터 품질 테스트"""

    @pytest.fixture
    def collector(self):
        return KRXCollector()

    def test_stock_list_data_quality(self, collector):
        """종목 목록 데이터 품질 확인"""
        stocks = collector.fetch_stock_list("KOSPI")

        for stock in stocks:
            # 티커는 6자리 문자열
            assert len(stock["ticker"]) == 6
            assert stock["ticker"].isdigit()

            # 이름은 비어있지 않음
            assert stock["name"]
            assert len(stock["name"]) > 0

            # 시장은 유효한 값
            assert stock["market"] in ["KOSPI", "KOSDAQ", "KONEX"]

    def test_daily_prices_data_quality(self, collector):
        """일봉 데이터 품질 확인"""
        df = collector.fetch_daily_prices("005930")

        for _, row in df.iterrows():
            # 가격은 양수
            assert row["open"] > 0
            assert row["high"] > 0
            assert row["low"] > 0
            assert row["close"] > 0

            # 거래량은 양수
            assert row["volume"] >= 0

            # 날짜는 유효한 date 객체
            assert isinstance(row["date"], date)

    def test_supply_demand_data_quality(self, collector):
        """수급 데이터 품질 확인"""
        df = collector.fetch_supply_demand("005930")

        for _, row in df.iterrows():
            # 날짜는 유효한 date 객체
            assert isinstance(row["date"], date)

            # 티커는 6자리
            assert len(row["ticker"]) == 6
