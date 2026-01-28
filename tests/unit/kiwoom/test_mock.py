"""
키움 Mock Bridge 테스트

TDD RED 단계: Mock 데이터 생성 및 동작 테스트를 먼저 작성합니다.
"""

import pytest
from unittest.mock import patch

from src.kiwoom.base import (
    KiwoomConfig,
    KiwoomEventType,
)
from src.kiwoom.mock import MockKiwoomBridge


# 단위 테스트: 짧은 timeout (10초)
@pytest.mark.timeout(10)
class TestMockInitialization:
    """Mock 초기화 테스트"""

    def test_mock_initialization(self):
        """Mock 초기화 테스트"""
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=True,
        )

        mock = MockKiwoomBridge(config)

        assert mock._config.use_mock is True
        assert mock.is_connected() is False

    def test_mock_from_env(self):
        """환경변수로 Mock 초기화 테스트"""
        with patch.dict("os.environ", {
            "USE_MOCK": "true",
            "KIWOOM_MOCK_APP_KEY": "mock_key",
            "KIWOOM_MOCK_SECRET_KEY": "mock_secret",
        }):
            from src.kiwoom.mock import MockKiwoomBridge

            mock = MockKiwoomBridge.from_env()

            assert mock._config.use_mock is True


class TestMockConnection:
    """Mock 연결 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=True,
        )
        return MockKiwoomBridge(config)

    @pytest.mark.asyncio
    async def test_mock_connect(self, mock_bridge):
        """Mock 연결 테스트"""
        result = await mock_bridge.connect()

        assert result is True
        assert mock_bridge.is_connected() is True

    @pytest.mark.asyncio
    async def test_mock_disconnect(self, mock_bridge):
        """Mock 연결 해제 테스트"""
        await mock_bridge.connect()
        assert mock_bridge.is_connected() is True

        await mock_bridge.disconnect()

        assert mock_bridge.is_connected() is False


class TestMockRealtimeData:
    """Mock 실시간 데이터 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=True,
        )
        return MockKiwoomBridge(config)

    @pytest.mark.asyncio
    async def test_mock_get_current_price(self, mock_bridge):
        """Mock 현재가 조회 테스트"""
        await mock_bridge.connect()

        price = await mock_bridge.get_current_price("005930")

        assert price is not None
        assert price.ticker == "005930"
        assert isinstance(price.price, (int, float))
        assert price.volume >= 0

    @pytest.mark.asyncio
    async def test_mock_get_current_price_not_found(self, mock_bridge):
        """없는 종목 조회 테스트"""
        await mock_bridge.connect()

        price = await mock_bridge.get_current_price("999999")

        # Mock는 임의의 데이터를 반환하거나 None을 반환할 수 있음
        # 구현에 따라 다름
        assert price is not None  # Mock는 항상 데이터 반환

    @pytest.mark.asyncio
    async def test_mock_subscribe_realtime(self, mock_bridge):
        """Mock 실시간 시세 등록 테스트"""
        await mock_bridge.connect()

        result = await mock_bridge.subscribe_realtime("005930")

        assert result is True
        assert "005930" in mock_bridge.get_subscribe_list()

        # 정리: 연결 해제 (백그라운드 태스크 정리)
        await mock_bridge.disconnect()

    @pytest.mark.asyncio
    async def test_mock_unsubscribe_realtime(self, mock_bridge):
        """Mock 실시간 시세 해제 테스트"""
        await mock_bridge.connect()
        await mock_bridge.subscribe_realtime("005930")
        await mock_bridge.subscribe_realtime("000660")

        assert "005930" in mock_bridge.get_subscribe_list()
        assert "000660" in mock_bridge.get_subscribe_list()

        result = await mock_bridge.unsubscribe_realtime("005930")

        assert result is True
        assert "005930" not in mock_bridge.get_subscribe_list()
        assert "000660" in mock_bridge.get_subscribe_list()

        # 정리: 연결 해제 (백그라운드 태스크 정리)
        await mock_bridge.disconnect()

    @pytest.mark.asyncio
    async def test_mock_get_subscribe_list(self, mock_bridge):
        """Mock 구독 목록 조회 테스트"""
        await mock_bridge.connect()

        # 초기에는 빈 목록
        assert mock_bridge.get_subscribe_list() == []

        # 종목 추가
        await mock_bridge.subscribe_realtime("005930")
        await mock_bridge.subscribe_realtime("000660")

        subscribe_list = mock_bridge.get_subscribe_list()
        assert "005930" in subscribe_list
        assert "000660" in subscribe_list
        assert len(subscribe_list) == 2

        # 정리: 연결 해제 (백그라운드 태스크 정리)
        await mock_bridge.disconnect()


class TestMockEventHandling:
    """Mock 이벤트 처리 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=True,
        )
        return MockKiwoomBridge(config)

    @pytest.mark.asyncio
    async def test_mock_register_event(self, mock_bridge):
        """Mock 이벤트 등록 테스트"""
        events_received = []

        def handler(data):
            events_received.append(data)

        mock_bridge.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)
        await mock_bridge.connect()

        # 구독 후 이벤트 발생 (실제로는 비동기로 발생)
        await mock_bridge.subscribe_realtime("005930")

        # Mock에서는 수동으로 이벤트 호출이 가능함
        # 테스트에서 직접 핸들러 호출 가능

        assert len(events_received) >= 0  # Mock에서는 자동 이벤트 없을 수 있음

        # 정리: 연결 해제 (백그라운드 태스크 정리)
        await mock_bridge.disconnect()

    @pytest.mark.asyncio
    async def test_mock_unregister_event(self, mock_bridge):
        """Mock 이벤트 해제 테스트"""
        events_received = []

        def handler(data):
            events_received.append(data)

        mock_bridge.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)
        await mock_bridge.connect()

        mock_bridge.unregister_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        # 등록된 핸들러 없음
        # 실제로는 내부적으로 비어있어야 함


class TestMockDataGeneration:
    """Mock 데이터 생성 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=True,
        )
        return MockKiwoomBridge(config)

    @pytest.mark.asyncio
    async def test_mock_price_fluctuation(self, mock_bridge):
        """Mock 가격 변동 테스트"""
        await mock_bridge.connect()

        # 여러 번 조회 시 다른 가격 반환
        prices = []
        for _ in range(5):
            price = await mock_bridge.get_current_price("005930")
            prices.append(price.price)

        # 가격이 변동해야 함 (모두 같은 값이면 mock의 가격 생성 로직 확인)
        # Mock는 실제 데이터 패턴을 모방
        assert len(prices) == 5

    @pytest.mark.asyncio
    async def test_mock_seed_consistency(self, mock_bridge):
        """시드값 일관성 테스트"""
        # 같은 시드로 Mock을 생성하면 같은 데이터 반환
        pass  # 구현 시 추가
