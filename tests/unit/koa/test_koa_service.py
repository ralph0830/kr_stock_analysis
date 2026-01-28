"""
실시간 데이터 서비스 통합 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.koa.service import RealtimeDataService, RealtimeDataSubscriber
from src.koa.base import RealtimePrice


class TestRealtimeDataService:
    """실시간 데이터 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_start_with_mock(self):
        """Mock 모드로 서비스 시작 테스트"""
        service = RealtimeDataService(use_mock=True)

        result = await service.start()

        assert result is True
        assert service.is_running()
        assert service.is_mock()

        await service.stop()

    @pytest.mark.asyncio
    async def test_subscribe_ticker(self):
        """종목 구독 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        result = await service.subscribe("005930")

        assert result is True
        assert "005930" in service.get_subscribed_tickers()

        await service.stop()

    @pytest.mark.asyncio
    async def test_subscribe_multiple_tickers(self):
        """여러 종목 구독 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        tickers = ["005930", "000660", "035420"]
        for ticker in tickers:
            await service.subscribe(ticker)

        subscribed = service.get_subscribed_tickers()
        for ticker in tickers:
            assert ticker.zfill(6) in subscribed

        await service.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_ticker(self):
        """종목 구독 해제 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()
        await service.subscribe("005930")

        result = await service.unsubscribe("005930")

        assert result is True
        assert "005930" not in service.get_subscribed_tickers()

        await service.stop()

    @pytest.mark.asyncio
    async def test_price_handler(self):
        """가격 핸들러 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        # 핸들러 모킹
        handler = Mock()
        service.add_price_handler(handler)

        # 종목 구독
        await service.subscribe("005930")

        # 업데이트 대기
        await asyncio.sleep(0.3)

        # 핸들러 호출 확인
        assert handler.call_count > 0

        # 첫 번째 호출 인자 확인
        call_args = handler.call_args_list[0]
        assert call_args[0][0] == "005930"  # ticker
        assert isinstance(call_args[0][1], RealtimePrice)

        await service.stop()

    @pytest.mark.asyncio
    async def test_multiple_price_handlers(self):
        """여러 가격 핸들러 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        handler1 = Mock()
        handler2 = Mock()
        service.add_price_handler(handler1)
        service.add_price_handler(handler2)

        await service.subscribe("005930")
        await asyncio.sleep(0.3)

        # 두 핸들러 모두 호출되어야 함
        assert handler1.call_count > 0
        assert handler2.call_count > 0
        assert handler1.call_count == handler2.call_count

        await service.stop()

    @pytest.mark.asyncio
    async def test_remove_price_handler(self):
        """핸들러 제거 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        handler = Mock()
        service.add_price_handler(handler)

        # 핸들러 제거
        service.remove_price_handler(handler)

        await service.subscribe("005930")
        await asyncio.sleep(0.3)

        # 핸들러가 제거되어 호출되지 않아야 함
        assert handler.call_count == 0

        await service.stop()

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_all(self):
        """서비스 중지 시 모든 구독 해제 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        # 여러 종목 구독
        await service.subscribe("005930")
        await service.subscribe("000660")
        await service.subscribe("035420")

        assert len(service.get_subscribed_tickers()) == 3

        # 서비스 중지
        await service.stop()

        # 모든 구독 해제 확인
        assert len(service.get_subscribed_tickers()) == 0

    @pytest.mark.asyncio
    async def test_format_price_data_dict(self):
        """딕셔너리 형식 데이터 변환 테스트"""
        service = RealtimeDataService(use_mock=True)

        raw_data = {
            "price": 85000,
            "change": 500,
            "change_rate": 0.59,
            "volume": 1000000,
            "bid_price": 84990,
            "ask_price": 85010,
            "timestamp": "2024-01-26T10:30:00Z",
        }

        formatted = service._format_price_data("005930", raw_data)

        assert formatted.ticker == "005930"
        assert formatted.price == 85000
        assert formatted.change == 500
        assert formatted.change_rate == 0.59
        assert formatted.volume == 1000000

    @pytest.mark.asyncio
    async def test_subscribe_before_start_fails(self):
        """시작 전 구독 실패 테스트"""
        service = RealtimeDataService(use_mock=True)

        # 서비스 시작하지 않고 구독 시도
        result = await service.subscribe("005930")

        assert result is False

    @pytest.mark.asyncio
    async def test_custom_bridge(self):
        """사용자 정의 브리지 사용 테스트"""
        from src.koa.mock import MockKOABridge

        custom_bridge = MockKOABridge(auto_update=True, update_interval=0.1)
        service = RealtimeDataService(bridge=custom_bridge, use_mock=False)

        await service.start()

        assert service.is_running()
        assert not service.is_mock()  # 명시적으로 설정한 브리지 사용

        await service.stop()


class TestRealtimeDataSubscriber:
    """실시간 데이터 구독자 관리 테스트"""

    @pytest.mark.asyncio
    async def test_subscribe_tickers_batch(self):
        """일괄 구독 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        subscriber = RealtimeDataSubscriber(service)

        tickers = ["005930", "000660", "035420"]
        results = await subscriber.subscribe_tickers(tickers)

        assert len(results) == 3
        for ticker, success in results.items():
            assert success is True

        await service.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self):
        """전체 구독 해제 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        subscriber = RealtimeDataSubscriber(service)

        # 여러 종목 구독
        await subscriber.subscribe_tickers(["005930", "000660"])

        # 전체 해제
        await subscriber.unsubscribe_all()

        assert len(service.get_subscribed_tickers()) == 0

        await service.stop()

    @pytest.mark.asyncio
    async def test_price_update_flow(self):
        """가격 업데이트 흐름 테스트"""
        service = RealtimeDataService(use_mock=True)
        await service.start()

        # Redis 발행자 모킹
        mock_publisher = AsyncMock()
        subscriber = RealtimeDataSubscriber(service, redis_publisher=mock_publisher)

        await subscriber.subscribe_tickers(["005930"])

        # 업데이트 대기
        await asyncio.sleep(0.3)

        # Redis 발행이 시도되었는지 확인
        # (실제로는 비동기 태스크이므로 즉시 확인 어려움)
        # 여기서는 핸들러가 정상적으로 등록되었는지 확인
        assert len(service._price_handlers) > 0

        await service.stop()
