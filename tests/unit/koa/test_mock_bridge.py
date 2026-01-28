"""
Mock KOA Bridge 유닛 테스트
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.koa.mock import MockKOABridge, AsyncMockKOABridge
from src.koa.base import KOAEventType, RealtimePrice


class TestMockKOABridge:
    """Mock KOA Bridge 테스트"""

    def test_initial_state(self):
        """초기 상태 확인"""
        bridge = MockKOABridge()

        assert not bridge.is_connected()
        assert not bridge.is_logged_in()
        assert len(bridge.get_subscribe_list()) == 0

    def test_connect(self):
        """연결 테스트"""
        bridge = MockKOABridge()
        result = bridge.connect()

        assert result is True
        assert bridge.is_connected()

    def test_login_success(self):
        """로그인 성공 테스트"""
        bridge = MockKOABridge()
        bridge.connect()

        result = bridge.login("test_id", "test_password")

        assert result is True
        assert bridge.is_logged_in()

    def test_login_failure_invalid_password(self):
        """로그인 실패 테스트 (짧은 비밀번호)"""
        bridge = MockKOABridge()
        bridge.connect()

        result = bridge.login("test_id", "123")  # 3자리

        assert result is False
        assert not bridge.is_logged_in()

    def test_login_without_connect(self):
        """연결 없이 로그인 시도"""
        bridge = MockKOABridge()

        result = bridge.login("test_id", "test_password")

        assert result is False

    def test_subscribe_realtime(self):
        """실시간 시레 등록 테스트"""
        bridge = MockKOABridge(auto_update=False)
        bridge.connect()
        bridge.login("test_id", "test_password")

        result = bridge.subscribe_realtime("005930")

        assert result is True
        assert "005930" in bridge.get_subscribe_list()

    def test_subscribe_multiple(self):
        """여러 종목 실시간 시레 등록 테스트"""
        bridge = MockKOABridge(auto_update=False)
        bridge.connect()
        bridge.login("test_id", "test_password")

        tickers = ["005930", "000660", "035420"]
        for ticker in tickers:
            bridge.subscribe_realtime(ticker)

        subscribe_list = bridge.get_subscribe_list()
        for ticker in tickers:
            assert ticker.zfill(6) in subscribe_list

    def test_unsubscribe_realtime(self):
        """실시간 시레 해제 테스트"""
        bridge = MockKOABridge(auto_update=False)
        bridge.connect()
        bridge.login("test_id", "test_password")
        bridge.subscribe_realtime("005930")

        result = bridge.unsubscribe_realtime("005930")

        assert result is True
        assert "005930" not in bridge.get_subscribe_list()

    def test_event_handler_registration(self):
        """이벤트 핸들러 등록 테스트"""
        bridge = MockKOABridge()
        callback = Mock()

        bridge.register_event(KOAEventType.EVENT_CONNECT, callback)

        # 연결 시 콜백 호출
        bridge.connect()

        callback.assert_called_once_with(True)

    def test_realtime_price_event(self):
        """실시간 가격 이벤트 테스트"""
        bridge = MockKOABridge(auto_update=True, update_interval=0.1)
        callback = Mock()

        bridge.register_event(KOAEventType.RECEIVE_REAL_DATA, callback)
        bridge.connect()
        bridge.login("test_id", "test_password")
        bridge.subscribe_realtime("005930")

        # 업데이트 대기
        time.sleep(0.3)

        # 최소 한 번은 호출되어야 함
        assert callback.call_count > 0

        # 콜백 인자 확인
        call_args = callback.call_args_list[0]
        assert call_args[0][0] == "005930"  # ticker
        assert isinstance(call_args[0][1], RealtimePrice)

        bridge.disconnect()

    def test_market_state(self):
        """장 운영 상태 조회 테스트"""
        bridge = MockKOABridge()

        state = bridge.request_market_state()

        assert state is not None
        assert "market_status" in state
        assert "is_trading" in state

    def test_set_price(self):
        """가격 설정 테스트"""
        bridge = MockKOABridge()
        bridge.set_price("005930", 100000)

        # 실시간 시레 등록 후 설정된 가격으로 시작
        bridge.connect()
        bridge.login("test_id", "test_password")
        bridge.subscribe_realtime("005930")

        # 업데이트 대기
        time.sleep(0.2)

        bridge.disconnect()

    def test_disconnect(self):
        """연결 해제 테스트"""
        bridge = MockKOABridge(auto_update=True)
        bridge.connect()
        bridge.login("test_id", "test_password")
        bridge.subscribe_realtime("005930")

        assert bridge.is_connected()

        bridge.disconnect()

        assert not bridge.is_connected()
        assert not bridge._running

    def test_generate_price_update(self):
        """가격 업데이트 생성 테스트"""
        bridge = MockKOABridge(auto_update=False)
        bridge.connect()

        price_data = bridge._generate_price_update("005930")

        assert isinstance(price_data, RealtimePrice)
        assert price_data.ticker == "005930"
        assert price_data.price > 0
        assert price_data.bid_price < price_data.price
        assert price_data.ask_price > price_data.price

    def test_multiple_ticker_updates(self):
        """여러 종목 동시 업데이트 테스트"""
        bridge = MockKOABridge(auto_update=True, update_interval=0.1)
        received = {}

        def on_price(ticker, data):
            received[ticker] = data

        bridge.register_event(KOAEventType.RECEIVE_REAL_DATA, on_price)
        bridge.connect()
        bridge.login("test_id", "test_password")

        tickers = ["005930", "000660", "035420"]
        for ticker in tickers:
            bridge.subscribe_realtime(ticker)

        # 업데이트 대기
        time.sleep(0.5)

        # 모든 종목 데이터 수신 확인
        for ticker in tickers:
            assert ticker in received

        bridge.disconnect()


class TestAsyncMockKOABridge:
    """비동기 Mock KOA Bridge 테스트"""

    @pytest.mark.asyncio
    async def test_connect(self):
        """비동기 연결 테스트"""
        bridge = AsyncMockKOABridge()

        result = await bridge.connect()

        assert result is True

    @pytest.mark.asyncio
    async def test_login(self):
        """비동기 로그인 테스트"""
        bridge = AsyncMockKOABridge()
        await bridge.connect()

        result = await bridge.login("test_id", "test_password")

        assert result is True

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self):
        """비동기 실시간 시레 및 수신 테스트"""
        import asyncio

        bridge = AsyncMockKOABridge(update_interval=0.1)
        received = []

        def on_price(ticker, data):
            received.append((ticker, data))

        bridge.register_event(KOAEventType.RECEIVE_REAL_DATA, on_price)
        await bridge.connect()
        await bridge.login("test_id", "test_password")
        await bridge.subscribe_realtime("005930")

        # 업데이트 대기
        await asyncio.sleep(0.5)

        assert len(received) > 0
        assert received[0][0] == "005930"

        await bridge.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """비동기 연결 해제 테스트"""
        bridge = AsyncMockKOABridge()
        await bridge.connect()

        await bridge.disconnect()

        assert not bridge._running
