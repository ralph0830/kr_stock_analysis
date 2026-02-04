"""
가격 데이터 제공자 테스트
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.websocket.price_provider import (
    PriceDataProvider,
    RealTimePriceService,
    init_realtime_service,
)


class TestPriceDataProvider:
    """PriceDataProvider 테스트"""

    @patch('src.websocket.price_provider.SessionLocal')
    def test_get_latest_price_no_data(self, mock_session_local):
        """데이터 없을 때 테스트"""
        # Mock session 설정
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session
        mock_session.execute().scalar_one_or_none.return_value = None

        provider = PriceDataProvider()

        # 존재하지 않는 종목
        price = provider.get_latest_price("999999")
        assert price is None

    @patch('src.websocket.price_provider.SessionLocal')
    def test_get_latest_prices_empty_list(self, mock_session_local):
        """빈 리스트로 조회 테스트"""
        provider = PriceDataProvider()

        prices = provider.get_latest_prices([])
        assert prices == {}

    @patch('src.websocket.price_provider.SessionLocal')
    def test_get_recent_prices_no_data(self, mock_session_local):
        """데이터 없을 때 최근 가격 조회 테스트"""
        # Mock session 설정
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session
        mock_session.execute().scalars().all.return_value = []

        provider = PriceDataProvider()

        prices = provider.get_recent_prices("999999", days=5)
        assert prices == []

    def test_format_price_data(self):
        """가격 데이터 포맷팅 테스트"""
        from src.database.models import DailyPrice

        provider = PriceDataProvider()

        # Mock DailyPrice 객체 (SQLAlchemy 모델)
        # DailyPrice 모델의 속성명: open_price, high_price, low_price, close_price
        mock_price = MagicMock(spec=DailyPrice)
        mock_price.ticker = "005930"
        mock_price.date = date(2024, 1, 15)
        mock_price.open_price = 80000
        mock_price.high_price = 81000
        mock_price.low_price = 79500
        mock_price.close_price = 80500
        mock_price.volume = 10000000

        formatted = provider._format_price_data(mock_price)

        assert formatted["ticker"] == "005930"
        assert formatted["open"] == 80000.0
        assert formatted["close"] == 80500.0
        assert formatted["change"] == 500.0
        assert formatted["change_rate"] == 0.62  # (500 / 80000) * 100


class TestRealTimePriceService:
    """RealTimePriceService 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        service = RealTimePriceService(
            tickers=["005930"],
            use_real_data=False,
        )
        assert service.is_running() is False

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """시작/중지 테스트"""
        service = RealTimePriceService(
            tickers=["005930"],
            use_real_data=False,
            interval_seconds=0.1,
        )

        await service.start()
        assert service.is_running() is True

        await service.stop()
        assert service.is_running() is False

    @pytest.mark.asyncio
    async def test_generate_mock_prices(self):
        """Mock 가격 생성 테스트"""
        service = RealTimePriceService(
            tickers=["005930", "000660"],
            use_real_data=False,
        )

        mock_prices = service._generate_mock_prices()

        assert "005930" in mock_prices
        assert "000660" in mock_prices

        # 데이터 구조 확인
        samsung = mock_prices["005930"]
        assert "ticker" in samsung
        assert "open" in samsung
        assert "close" in samsung
        assert "volume" in samsung
        assert "change" in samsung

    @pytest.mark.asyncio
    async def test_duplicate_start(self):
        """중복 시작 테스트"""
        service = RealTimePriceService(
            tickers=["005930"],
            use_real_data=False,
        )

        await service.start()
        assert service.is_running() is True

        # 중복 시작 (무시되어야 함)
        await service.start()
        assert service.is_running() is True

        await service.stop()


    @pytest.mark.asyncio
    async def test_generate_mock_price_for_ticker(self):
        """단일 종목 Mock 가격 생성 테스트"""
        service = RealTimePriceService(
            tickers=["005930"],
            use_real_data=False,
        )

        mock_price = service._generate_mock_price_for_ticker("005930")

        assert mock_price["ticker"] == "005930"
        assert "open" in mock_price
        assert "close" in mock_price
        assert "volume" in mock_price
        assert "change" in mock_price
        assert "change_rate" in mock_price

    @pytest.mark.asyncio
    async def test_broadcast_with_fallback_to_mock(self):
        """DB 데이터 없을 때 Mock 데이터로 fallback 테스트"""
        service = RealTimePriceService(
            tickers=["005930"],
            use_real_data=True,  # 실제 데이터 사용 모드
            interval_seconds=0.1,
        )

        # DB에 데이터가 없어도 Mock으로 fallback되므로 정상 동작해야 함
        await service.start()
        assert service.is_running() is True

        # 잠시 대기 후 브로드캐스트 확인
        import asyncio
        await asyncio.sleep(0.2)

        await service.stop()
        assert service.is_running() is False


class TestGlobalService:
    """전역 서비스 테스트"""

    @pytest.fixture(autouse=True)
    def reset_global_service(self):
        """전역 서비스 리셋"""
        from src.websocket.price_provider import _realtime_price_service
        # 전역 서비스 저장
        original_service = _realtime_price_service
        # 리셋
        import src.websocket.price_provider as price_provider_module
        price_provider_module._realtime_price_service = None
        yield
        # 테스트 후 원복
        price_provider_module._realtime_price_service = original_service

    def test_init_realtime_service(self):
        """전역 서비스 초기화 테스트"""
        from src.websocket.price_provider import _realtime_price_service

        # 초기화 전
        assert _realtime_price_service is None

        # 초기화
        service = init_realtime_service(
            tickers=["005930"],
            use_real_data=False,
        )

        assert service is not None
        assert isinstance(service, RealTimePriceService)

    def test_get_realtime_service(self):
        """전역 서비스 조회 테스트"""
        from src.websocket.price_provider import get_realtime_service, _realtime_price_service

        # 초기화 안 된 상태
        service = get_realtime_service()
        if _realtime_price_service is None:
            assert service is None
        else:
            assert service is not None
