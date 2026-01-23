"""
Test Suite: Event Bus (GREEN Phase)
Redis Pub/Sub 기반 이벤트 버스 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from services.event_bus.event_bus import (
    EventBus,
    Event,
    SignalEvent,
    MarketUpdateEvent,
    create_signal_event,
    create_market_update_event,
    CHANNEL_SIGNAL_CREATED,
    CHANNEL_MARKET_GATE,
)


class TestEventBus:
    """이벤트 버스 테스트"""

    @pytest.mark.asyncio
    async def test_event_bus_init(self):
        """이벤트 버스 초기화 테스트"""
        bus = EventBus()
        assert bus is not None
        assert bus._handlers == {}

    @pytest.mark.asyncio
    async def test_event_serialization(self):
        """이벤트 직렬화 테스트"""
        event = Event(
            event_type="test.event",
            data={"key": "value"},
            timestamp="2024-01-01T00:00:00",
            source="test",
        )

        json_str = event.to_json()
        restored = Event.from_json(json_str)

        assert restored.event_type == event.event_type
        assert restored.data == event.data

    @pytest.mark.asyncio
    async def test_subscribe_channel(self):
        """채널 구독 테스트"""
        bus = EventBus()

        async def dummy_handler(event):
            pass

        await bus.subscribe("test-channel", dummy_handler)

        assert "test-channel" in bus._handlers
        assert len(bus._handlers["test-channel"]) == 1


class TestSignalEvents:
    """시그널 이벤트 테스트"""

    def test_create_signal_event(self):
        """시그널 이벤트 생성 테스트"""
        event = create_signal_event(
            ticker="005930",
            signal_type="vcp",
            score=75,
            grade="A",
        )

        assert isinstance(event, SignalEvent)
        assert event.ticker == "005930"
        assert event.signal_type == "vcp"
        assert event.score == 75
        assert event.grade == "A"

    def test_signal_event_serialization(self):
        """시그널 이벤트 직렬화 테스트"""
        event = create_signal_event("005930", "vcp", 75, "A")

        json_str = event.to_json()
        restored = SignalEvent.from_json(json_str)

        assert restored.ticker == event.ticker
        assert restored.score == event.score


class TestMarketEvents:
    """마켓 이벤트 테스트"""

    def test_create_market_update_event(self):
        """마켓 업데이트 이벤트 생성 테스트"""
        event = create_market_update_event(
            gate_status="GREEN",
            score=85,
        )

        assert isinstance(event, MarketUpdateEvent)
        assert event.gate_status == "GREEN"
        assert event.score == 85


class TestEventHandlers:
    """이벤트 핸들러 테스트"""

    @pytest.mark.asyncio
    async def test_handler_execution(self):
        """핸들러 실행 테스트"""
        bus = EventBus()

        # Mock 핸들러
        handler_mock = Mock()
        async def mock_handler(event):
            handler_mock(event.data)

        # 이벤트 생성
        event = Event(
            event_type="test.event",
            data={"test": "data"},
            timestamp="2024-01-01",
            source="test",
        )

        # 핸들러 등록 및 실행
        await bus.subscribe("test-channel", mock_handler)
        handlers = bus._handlers.get("test-channel", [])

        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

        # 핸들러 실행 확인
        handler_mock.assert_called_once_with({"test": "data"})


class TestChannelConstants:
    """채널 상수 테스트"""

    def test_channel_constants(self):
        """채널 상수 확인 테스트"""
        assert CHANNEL_SIGNAL_CREATED == "signals:created"
        assert CHANNEL_MARKET_GATE == "market:gate"
