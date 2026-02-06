"""
실시간 데이터 수집기 통합 테스트

TDD: Red-Green-Refactor Cycle
- Kiwoom REST API를 사용한 일봉/실시간 데이터 수집 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_kiwoom_api():
    """KiwoomRestAPI Mock"""
    api = Mock()
    api.get_stock_daily_chart = AsyncMock()
    api.get_current_price = AsyncMock()
    return api


@pytest.fixture
def mock_db_session():
    """DB 세션 Mock"""
    session = Mock()
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def sample_daily_chart_data():
    """샘플 일봉 차트 데이터"""
    return [
        {
            "date": "20260130",
            "open": 75000,
            "high": 76000,
            "low": 74500,
            "close": 75500,
            "volume": 15000000,
            "change": 500,
        },
        {
            "date": "20260129",
            "open": 74000,
            "high": 75000,
            "low": 73800,
            "close": 74800,
            "volume": 12000000,
            "change": -200,
        },
        {
            "date": "20260128",
            "open": 74500,
            "high": 75200,
            "low": 74000,
            "close": 75000,
            "volume": 18000000,
            "change": 300,
        },
    ]


@pytest.fixture
def sample_current_price_data():
    """샘플 현재가 데이터"""
    return {
        "price": 75800,
        "change": 300,
        "change_rate": 0.40,
        "volume": 5000000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# RealtimeDataCollector 테스트
# =============================================================================

class TestRealtimeDataCollector:
    """실시간 데이터 수집기 테스트"""

    @pytest.mark.asyncio
    async def test_collect_daily_prices_for_ticker(
        self,
        mock_kiwoom_api,
        mock_db_session,
        sample_daily_chart_data
    ):
        """단일 종목 일봉 데이터 수집 테스트"""
        from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector

        # Mock 설정
        mock_kiwoom_api.get_stock_daily_chart.return_value = sample_daily_chart_data

        # 컬렉터 생성
        collector = RealtimeDataCollector(kiwoom_api=mock_kiwoom_api)

        # 일봉 데이터 수집
        count = await collector.collect_daily_prices(
            ticker="005930",
            db=mock_db_session,
            days=30
        )

        # 검증
        assert count == 3
        mock_kiwoom_api.get_stock_daily_chart.assert_called_once_with(
            ticker="005930", days=30, base_date=None, adjusted_price=True
        )
        assert mock_db_session.execute.call_count == 3
        assert mock_db_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_collect_daily_prices_handles_empty_data(
        self,
        mock_kiwoom_api,
        mock_db_session
    ):
        """빈 일봉 데이터 처리 테스트"""
        from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector

        # Mock 설정 (빈 데이터 반환)
        mock_kiwoom_api.get_stock_daily_chart.return_value = []

        collector = RealtimeDataCollector(kiwoom_api=mock_kiwoom_api)

        # 일봉 데이터 수집
        count = await collector.collect_daily_prices(
            ticker="005930",
            db=mock_db_session,
            days=30
        )

        # 검증: 빈 데이터이므로 0 반환
        assert count == 0
        mock_db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_daily_prices_for_multiple_tickers(
        self,
        mock_kiwoom_api,
        mock_db_session,
        sample_daily_chart_data
    ):
        """다중 종목 일봉 데이터 수집 테스트"""
        from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector

        # Mock 설정
        mock_kiwoom_api.get_stock_daily_chart.return_value = sample_daily_chart_data

        collector = RealtimeDataCollector(kiwoom_api=mock_kiwoom_api)

        # 다중 종목 수집
        tickers = ["005930", "000270", "035420"]
        results = await collector.collect_daily_prices_for_tickers(
            tickers=tickers,
            db=mock_db_session,
            days=30
        )

        # 검증
        assert len(results) == 3
        assert results["005930"] == 3
        assert results["000270"] == 3
        assert results["035420"] == 3
        assert mock_kiwoom_api.get_stock_daily_chart.call_count == 3

    @pytest.mark.asyncio
    async def test_collect_current_price(
        self,
        mock_kiwoom_api,
        sample_current_price_data
    ):
        """현재가 수집 테스트"""
        from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector
        from src.kiwoom.base import RealtimePrice

        # Mock 설정
        mock_price = RealtimePrice(
            ticker="005930",
            price=sample_current_price_data["price"],
            change=sample_current_price_data["change"],
            change_rate=sample_current_price_data["change_rate"],
            volume=sample_current_price_data["volume"],
            bid_price=75700,
            ask_price=75900,
            timestamp=sample_current_price_data["timestamp"]
        )
        mock_kiwoom_api.get_current_price.return_value = mock_price

        collector = RealtimeDataCollector(kiwoom_api=mock_kiwoom_api)

        # 현재가 수집
        price_data = await collector.collect_current_price("005930")

        # 검증
        assert price_data is not None
        assert price_data["ticker"] == "005930"
        assert price_data["price"] == 75800
        assert price_data["change"] == 300
        assert price_data["change_rate"] == 0.40
        mock_kiwoom_api.get_current_price.assert_called_once_with("005930")

    @pytest.mark.asyncio
    async def test_collect_current_price_handles_failure(
        self,
        mock_kiwoom_api
    ):
        """현재가 수집 실패 처리 테스트"""
        from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector

        # Mock 설정 (None 반환)
        mock_kiwoom_api.get_current_price.return_value = None

        collector = RealtimeDataCollector(kiwoom_api=mock_kiwoom_api)

        # 현재가 수집
        price_data = await collector.collect_current_price("005930")

        # 검증: 실패 시 None 반환
        assert price_data is None

    @pytest.mark.asyncio
    async def test_collect_current_prices_for_tickers(
        self,
        mock_kiwoom_api,
        sample_current_price_data
    ):
        """다중 종목 현재가 수집 테스트"""
        from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector
        from src.kiwoom.base import RealtimePrice

        # Mock 설정
        def create_mock_price(ticker, price):
            return RealtimePrice(
                ticker=ticker,
                price=price,
                change=100,
                change_rate=0.1,
                volume=1000000,
                bid_price=price - 50,
                ask_price=price + 50,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        mock_kiwoom_api.get_current_price.side_effect = [
            create_mock_price("005930", 75800),
            create_mock_price("000270", 120000),
            create_mock_price("035420", 150000),
        ]

        collector = RealtimeDataCollector(kiwoom_api=mock_kiwoom_api)

        # 다중 종목 현재가 수집
        tickers = ["005930", "000270", "035420"]
        prices = await collector.collect_current_prices_for_tickers(tickers)

        # 검증
        assert len(prices) == 3
        assert prices["005930"]["price"] == 75800
        assert prices["000270"]["price"] == 120000
        assert prices["035420"]["price"] == 150000
        assert mock_kiwoom_api.get_current_price.call_count == 3


# =============================================================================
# Celery Task 테스트
# =============================================================================

class TestRealtimeDataCollectionTasks:
    """실시간 데이터 수집 Celery 태스크 테스트"""

    def test_collect_all_stocks_daily_prices_task(self):
        """전 종목 일봉 데이터 수집 태스크 테스트"""
        from tasks.realtime_data_tasks import collect_all_stocks_daily_prices

        # 태스크 실행 (결과만 확인, 실제 DB 연결 없이)
        with patch('src.database.session.get_db_session_sync') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value.__enter__ = Mock(return_value=mock_session)
            mock_get_db.return_value.__exit__ = Mock(return_value=False)

            # 종목 조회 Mock (ScalarReturn 사용)
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [
                Mock(ticker="005930", name="삼성전자"),
                Mock(ticker="000270", name="기아"),
            ]
            mock_execute_result = MagicMock()
            mock_execute_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_execute_result

            result = collect_all_stocks_daily_prices.delay(market="KOSPI", days=30)

            # 태스크가 성공적으로 생성되었는지 확인
            assert result.id is not None

    def test_broadcast_realtime_prices_task(self):
        """실시간 가격 브로드캐스트 태스크 테스트"""
        from tasks.realtime_data_tasks import broadcast_realtime_prices

        # 태스크 실행
        tickers = ["005930", "000270", "035420"]
        result = broadcast_realtime_prices.delay(tickers=tickers)

        # 태스크가 성공적으로 생성되었는지 확인
        assert result.id is not None
