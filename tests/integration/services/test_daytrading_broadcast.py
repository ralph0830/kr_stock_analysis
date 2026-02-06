"""
Daytrading 브로드캐스트 테스트 (TDD - Red Phase)

이 테스트 파일은 daytrading 시그널과 가격 브로드캐스트를 검증합니다.
TDD 방식으로 작성되었으며, 먼저 실패하는 테스트를 작성합니다.

테스트 커버리지:
1. `signal:daytrading` 토픽으로 메시지 전송
2. `price:{ticker}` 토픽으로 메시지 전송
3. 스캔 완료 시 자동 브로드캐스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# 테스트 대상 모듈 임포트
from services.daytrading_scanner.broadcaster import (
    DaytradingBroadcaster,
    broadcast_daytrading_signals,
    broadcast_price_update,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager"""
    manager = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_signal_data():
    """Mock 시그널 데이터"""
    return [
        {
            "ticker": "005930",
            "name": "삼성전자",
            "grade": "S",
            "total_score": 90,
            "signal_type": "strong_buy",
            "entry_price": 75000,
            "target_price": 80000,
            "stop_loss": 73000,
            "current_price": 75500,
            "checks": [
                {"name": "거래량 폭증", "status": "passed", "points": 15},
                {"name": "모멘텀 돌파", "status": "passed", "points": 15},
                {"name": "박스권 탈출", "status": "passed", "points": 15},
                {"name": "5일선 위", "status": "passed", "points": 15},
                {"name": "기관 매수", "status": "passed", "points": 15},
                {"name": "낙폭 과대", "status": "passed", "points": 15},
                {"name": "섹터 모멘텀", "status": "passed", "points": 15},
            ]
        },
        {
            "ticker": "000270",
            "name": "기아",
            "grade": "A",
            "total_score": 75,
            "signal_type": "buy",
            "entry_price": 120000,
            "target_price": 130000,
            "stop_loss": 115000,
            "current_price": 122000,
            "checks": [
                {"name": "거래량 폭증", "status": "passed", "points": 15},
                {"name": "모멘텀 돌파", "status": "passed", "points": 15},
                {"name": "박스권 탈출", "status": "passed", "points": 15},
                {"name": "5일선 위", "status": "passed", "points": 15},
                {"name": "기관 매수", "status": "passed", "points": 15},
            ]
        }
    ]


# =============================================================================
# Test 1: 시그널 브로드캐스트
# =============================================================================

class TestSignalBroadcast:
    """시그널 브로드캐스트 검증"""

    @pytest.mark.asyncio
    async def test_broadcast_signals_to_correct_topic(self, mock_connection_manager, mock_signal_data):
        """
        GIVEN: 시그널 데이터
        WHEN: broadcast_daytrading_signals()를 호출하면
        THEN: `signal:daytrading` 토픽으로 메시지가 전송되어야 함
        """
        # Act
        await broadcast_daytrading_signals(mock_signal_data, mock_connection_manager)

        # Assert: broadcast가 올바른 토픽으로 호출되었는지
        mock_connection_manager.broadcast.assert_called_once()
        call_args = mock_connection_manager.broadcast.call_args

        # broadcast(message, topic=topic) 형식 확인
        # call_args는 positional args를 tuple로 가짐
        args = call_args[0]  # positional args
        kwargs = call_args[1] if len(call_args) > 1 else {}  # kwargs

        # topic 확인
        topic = kwargs.get("topic")
        assert topic == "signal:daytrading", f"올바른 토픽이어야 함, 실제: {topic}"

    @pytest.mark.asyncio
    async def test_broadcast_message_format(self, mock_connection_manager, mock_signal_data):
        """
        GIVEN: 시그널 데이터
        WHEN: 브로드캐스트하면
        THEN: 올바른 메시지 형식이어야 함
        """
        # Act
        await broadcast_daytrading_signals(mock_signal_data, mock_connection_manager)

        # Assert: 메시지 형식 확인
        call_args = mock_connection_manager.broadcast.call_args
        message = call_args[0][0]

        assert message["type"] == "signal_update"
        assert "data" in message
        assert "signals" in message["data"]
        assert "timestamp" in message["data"]
        assert message["data"]["count"] == 2

    @pytest.mark.asyncio
    async def test_signal_data_fields(self, mock_connection_manager, mock_signal_data):
        """
        GIVEN: 시그널 데이터
        WHEN: 브로드캐스트하면
        THEN: 모든 필드가 올바르게 변환되어야 함
        """
        # Act
        await broadcast_daytrading_signals(mock_signal_data, mock_connection_manager)

        # Assert: 시그널 데이터 필드 확인
        call_args = mock_connection_manager.broadcast.call_args
        message = call_args[0][0]
        signals = message["data"]["signals"]

        # 첫 번째 시그널 확인
        assert signals[0]["ticker"] == "005930"
        assert signals[0]["name"] == "삼성전자"
        assert signals[0]["grade"] == "S"
        assert signals[0]["total_score"] == 90
        assert signals[0]["signal_type"] == "strong_buy"
        assert signals[0]["entry_price"] == 75000
        assert signals[0]["target_price"] == 80000
        assert signals[0]["stop_loss"] == 73000
        assert signals[0]["current_price"] == 75500
        assert len(signals[0]["checks"]) == 7


# =============================================================================
# Test 2: 가격 브로드캐스트
# =============================================================================

class TestPriceBroadcast:
    """가격 브로드캐스트 검증"""

    @pytest.mark.asyncio
    async def test_broadcast_price_to_correct_topic(self, mock_connection_manager):
        """
        GIVEN: 종목 코드와 가격 데이터
        WHEN: broadcast_price_update()를 호출하면
        THEN: `price:{ticker}` 토픽으로 메시지가 전송되어야 함
        """
        # Arrange
        ticker = "005930"
        price_data = {
            "price": 75500,
            "change": 500,
            "change_rate": 0.66,
            "volume": 15000000
        }

        # Act
        await broadcast_price_update(ticker, price_data, mock_connection_manager)

        # Assert: broadcast가 올바른 토픽으로 호출되었는지
        mock_connection_manager.broadcast.assert_called_once()
        call_args = mock_connection_manager.broadcast.call_args

        # topic 확인
        kwargs = call_args[1] if len(call_args) > 1 else {}
        topic = kwargs.get("topic")
        assert topic == "price:005930", f"올바른 토픽이어야 함, 실제: {topic}"

    @pytest.mark.asyncio
    async def test_price_message_format(self, mock_connection_manager):
        """
        GIVEN: 가격 데이터
        WHEN: 브로드캐스트하면
        THEN: 올바른 메시지 형식이어야 함
        """
        # Arrange
        ticker = "005930"
        price_data = {
            "price": 75500,
            "change": 500,
            "change_rate": 0.66,
            "volume": 15000000
        }

        # Act
        await broadcast_price_update(ticker, price_data, mock_connection_manager)

        # Assert: 메시지 형식 확인
        call_args = mock_connection_manager.broadcast.call_args
        message = call_args[0][0]

        assert message["type"] == "price_update"
        assert message["ticker"] == "005930"
        assert "data" in message
        assert message["data"]["price"] == 75500
        assert message["data"]["change"] == 500
        assert message["data"]["change_rate"] == 0.66
        assert message["data"]["volume"] == 15000000
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_multiple_tickers(self, mock_connection_manager):
        """
        GIVEN: 여러 종목의 가격 데이터
        WHEN: 순차적으로 브로드캐스트하면
        THEN: 각 종목의 토픽으로 전송되어야 함
        """
        # Arrange
        tickers = ["005930", "000270", "066570"]

        # Act: 각 종목 브로드캐스트
        for ticker in tickers:
            price_data = {"price": 75000, "change": 500, "change_rate": 0.5}
            await broadcast_price_update(ticker, price_data, mock_connection_manager)

        # Assert: 3회 호출되었는지
        assert mock_connection_manager.broadcast.call_count == 3

        # 각 호출의 토픽 확인
        for i, ticker in enumerate(tickers):
            call_args = mock_connection_manager.broadcast.call_args_list[i]
            kwargs = call_args[1] if len(call_args) > 1 else {}
            topic = kwargs.get("topic")
            assert topic == f"price:{ticker}"


# =============================================================================
# Test 3: DaytradingBroadcaster 클래스
# =============================================================================

class TestDaytradingBroadcaster:
    """DaytradingBroadcaster 클래스 검증"""

    @pytest.mark.asyncio
    async def test_broadcast_signals(self, mock_connection_manager, mock_signal_data):
        """
        GIVEN: DaytradingBroadcaster 인스턴스
        WHEN: broadcast_signals()를 호출하면
        THEN: ConnectionManager를 통해 브로드캐스트되어야 함
        """
        # Arrange
        broadcaster = DaytradingBroadcaster(mock_connection_manager)

        # Act
        await broadcaster.broadcast_signals(mock_signal_data)

        # Assert
        mock_connection_manager.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_price(self, mock_connection_manager):
        """
        GIVEN: DaytradingBroadcaster 인스턴스
        WHEN: broadcast_price()를 호출하면
        THEN: ConnectionManager를 통해 브로드캐스트되어야 함
        """
        # Arrange
        broadcaster = DaytradingBroadcaster(mock_connection_manager)
        ticker = "005930"
        price_data = {"price": 75500, "change": 500, "change_rate": 0.66}

        # Act
        await broadcaster.broadcast_price(ticker, price_data)

        # Assert
        mock_connection_manager.broadcast.assert_called_once()
