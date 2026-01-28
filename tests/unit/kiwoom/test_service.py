"""
키움 Realtime Service 테스트

TDD RED 단계: Service 통합 및 관리 테스트를 먼저 작성합니다.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.kiwoom.base import KiwoomConfig, KiwoomEventType, RealtimePrice
from src.kiwoom.service import KiwoomRealtimeService


class TestServiceInitialization:
    """Service 초기화 테스트"""

    def test_service_initialization_with_bridge(self):
        """Bridge로 Service 초기화 테스트"""
        mock_bridge = Mock()
        mock_bridge.is_connected.return_value = False

        service = KiwoomRealtimeService(mock_bridge)

        assert service._bridge is mock_bridge
        assert service.is_running() is False

    def test_service_initialization_with_config(self):
        """Config로 Service 초기화 테스트"""
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=True,
        )

        with patch('src.kiwoom.service.MockKiwoomBridge') as mock_bridge_class:
            mock_bridge = Mock()
            mock_bridge_class.return_value = mock_bridge

            service = KiwoomRealtimeService.from_config(config)

            mock_bridge_class.assert_called_once_with(config)
            assert service._bridge is mock_bridge


class TestServiceLifecycle:
    """Service 라이프사이클 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = False
        bridge.connect = AsyncMock(return_value=True)
        bridge.disconnect = AsyncMock()
        bridge.subscribe_realtime = AsyncMock(return_value=True)
        bridge.unsubscribe_realtime = AsyncMock(return_value=True)
        bridge.get_subscribe_list = Mock(return_value=[])
        return bridge

    @pytest.mark.asyncio
    async def test_service_start(self, mock_bridge):
        """Service 시작 테스트"""
        service = KiwoomRealtimeService(mock_bridge)

        await service.start()

        assert service.is_running() is True
        mock_bridge.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_stop(self, mock_bridge):
        """Service 중지 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        await service.start()

        await service.stop()

        assert service.is_running() is False
        mock_bridge.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_restart(self, mock_bridge):
        """Service 재시작 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        await service.start()
        await service.stop()

        await service.start()

        assert service.is_running() is True
        assert mock_bridge.connect.call_count == 2


class TestSubscriptionManagement:
    """구독 관리 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = True
        bridge.subscribe_realtime = AsyncMock(return_value=True)
        bridge.unsubscribe_realtime = AsyncMock(return_value=True)
        bridge.get_subscribe_list = Mock(return_value=[])
        return bridge

    @pytest.mark.asyncio
    async def test_subscribe_ticker(self, mock_bridge):
        """종목 구독 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        service._running = True  # Simulate running state

        result = await service.subscribe("005930")

        assert result is True
        mock_bridge.subscribe_realtime.assert_called_once_with("005930")

    @pytest.mark.asyncio
    async def test_subscribe_multiple_tickers(self, mock_bridge):
        """여러 종목 구독 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        service._running = True
        tickers = ["005930", "000660", "035420"]

        results = await service.subscribe_many(tickers)

        assert len(results) == 3
        assert all(r is True for r in results)
        assert mock_bridge.subscribe_realtime.call_count == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_ticker(self, mock_bridge):
        """종목 구독 해제 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        service._running = True

        result = await service.unsubscribe("005930")

        assert result is True
        mock_bridge.unsubscribe_realtime.assert_called_once_with("005930")

    @pytest.mark.asyncio
    async def test_get_subscribed_list(self, mock_bridge):
        """구독 목록 조회 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        mock_bridge.get_subscribe_list.return_value = ["005930", "000660"]

        tickers = service.get_subscribed_tickers()

        assert tickers == ["005930", "000660"]
        mock_bridge.get_subscribe_list.assert_called_once()


class TestEventHandlerManagement:
    """이벤트 핸들러 관리 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = True
        bridge.register_event = Mock()
        bridge.unregister_event = Mock()
        return bridge

    def test_register_event_handler(self, mock_bridge):
        """이벤트 핸들러 등록 테스트"""
        service = KiwoomRealtimeService(mock_bridge)

        def handler(data):
            pass

        service.register_event_handler(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        mock_bridge.register_event.assert_called_once_with(
            KiwoomEventType.RECEIVE_REAL_DATA, handler
        )

    def test_unregister_event_handler(self, mock_bridge):
        """이벤트 핸들러 해제 테스트"""
        service = KiwoomRealtimeService(mock_bridge)

        def handler(data):
            pass

        service.unregister_event_handler(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        mock_bridge.unregister_event.assert_called_once_with(
            KiwoomEventType.RECEIVE_REAL_DATA, handler
        )


class TestRedisIntegration:
    """Redis 발행 통합 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = True
        bridge.register_event = Mock()
        return bridge

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis fixture"""
        redis = AsyncMock()
        redis.publish = AsyncMock()
        return redis

    def test_enable_redis_publishing(self, mock_bridge, mock_redis):
        """Redis 발행 활성화 테스트"""
        service = KiwoomRealtimeService(mock_bridge, redis_client=mock_redis)

        service.enable_redis_publishing()

        assert service._redis_enabled is True
        # Bridge에 이벤트 핸들러 등록 확인

    @pytest.mark.asyncio
    async def test_redis_publish_on_realtime_data(self, mock_bridge, mock_redis):
        """실시간 데이터 수신 시 Redis 발행 테스트"""
        service = KiwoomRealtimeService(mock_bridge, redis_client=mock_redis)
        service.enable_redis_publishing()

        # 이벤트 핸들러 실행 시뮬레이션
        test_price = RealtimePrice(
            ticker="005930",
            price=72500,
            change=500,
            change_rate=0.69,
            volume=1000000,
            bid_price=72400,
            ask_price=72600,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # 등록된 핸들러 가져와서 실행
        call_args = mock_bridge.register_event.call_args
        if call_args:
            # call_args[0] contains positional args
            if len(call_args[0]) >= 2:
                handler = call_args[0][1]
                handler(test_price)

        # Redis 발행 확인 (create_task로 비동기 호출되므로 잠시 대기)
        await asyncio.sleep(0.01)
        mock_redis.publish.assert_called()


class TestServiceErrorHandling:
    """Service 에러 처리 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = False
        bridge.connect = AsyncMock(return_value=True)
        bridge.disconnect = AsyncMock()
        bridge.subscribe_realtime = AsyncMock(return_value=False)  # 실패
        return bridge

    @pytest.mark.asyncio
    async def test_subscribe_failure_handling(self, mock_bridge):
        """구독 실패 처리 테스트"""
        service = KiwoomRealtimeService(mock_bridge)

        result = await service.subscribe("005930")

        assert result is False  # 실패 시 False 반환

    @pytest.mark.asyncio
    async def test_service_connect_failure(self, mock_bridge):
        """Service 연결 실패 처리 테스트"""
        mock_bridge.connect = AsyncMock(return_value=False)
        service = KiwoomRealtimeService(mock_bridge)

        with pytest.raises(Exception):
            await service.start()


class TestServiceStatus:
    """Service 상태 조회 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = False
        bridge.has_valid_token = Mock(return_value=True)
        bridge.get_subscribe_list = Mock(return_value=["005930"])
        return bridge

    def test_get_service_status(self, mock_bridge):
        """Service 상태 조회 테스트"""
        service = KiwoomRealtimeService(mock_bridge)
        service._running = True

        status = service.get_status()

        assert status["running"] is True
        assert status["connected"] is False
        assert status["has_token"] is True
        assert status["subscribed_count"] == 1
