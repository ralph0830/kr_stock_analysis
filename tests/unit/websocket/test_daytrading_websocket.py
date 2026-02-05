"""
Unit Tests for Daytrading WebSocket Integration
TDD: Red-Green-Refactor Cycle

Phase 5: WebSocket Tests
- Signal broadcasting
- Scan result streaming
- Connection management
"""

import pytest
import asyncio
from datetime import date

from src.websocket.server import ConnectionManager


# =============================================================================
# Test Connection Management
# =============================================================================

class TestConnectionManager:
    """ConnectionManager 테스트"""

    @pytest.fixture
    def manager(self):
        """ConnectionManager fixture"""
        return ConnectionManager()

    def test_initial_state_empty(self, manager):
        """초기 상태: 연결 없음"""
        assert len(manager.active_connections) == 0
        assert len(manager.subscriptions) == 0

    def test_get_connection_count_empty(self, manager):
        """get_connection_count() → 0"""
        assert manager.get_connection_count() == 0


# =============================================================================
# Mock WebSocket for Testing
# =============================================================================

class MockWebSocket:
    """테스트용 Mock WebSocket"""
    def __init__(self):
        self.messages = []
        self.closed = False

    async def send_json(self, message: dict):
        """JSON 메시지 전송"""
        if self.closed:
            raise ConnectionError("WebSocket is closed")
        self.messages.append(message)

    async def close(self, code: int = 1000, reason: str = ""):
        """WebSocket 연결 종료"""
        self.closed = True


@pytest.fixture
def mock_ws():
    """Mock WebSocket fixture"""
    return MockWebSocket()


# =============================================================================
# Test Daytrading Broadcast Events
# =============================================================================

class TestDaytradingBroadcast:
    """Daytrading 브로드캐스트 테스트"""

    @pytest.fixture
    def manager(self):
        """ConnectionManager fixture"""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_broadcast_daytrading_signal(self, manager):
        """단타 신호 브로드캐스트"""
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()

        # 연결 시뮬레이션
        manager.active_connections["client1"] = mock_ws1
        manager.active_connections["client2"] = mock_ws2

        # 구독 (broadcast가 구독자에게만 전송하므로)
        manager.subscribe("client1", "daytrading_signals")
        manager.subscribe("client2", "daytrading_signals")

        # 신호 브로드캐스트
        signal = {
            "type": "daytrading_signal",
            "data": {
                "ticker": "005930",
                "name": "삼성전자",
                "total_score": 90,
                "grade": "S",
                "status": "OPEN"
            }
        }

        await manager.broadcast(signal, topic="daytrading_signals")

        # 두 클라이언트 모두 수신
        assert len(mock_ws1.messages) == 1
        assert len(mock_ws2.messages) == 1
        assert mock_ws1.messages[0]["type"] == "daytrading_signal"

    @pytest.mark.asyncio
    async def test_broadcast_to_subscribers_only(self, manager):
        """구독자에게만 브로드캐스트"""
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()

        manager.active_connections["client1"] = mock_ws1
        manager.active_connections["client2"] = mock_ws2

        # client1만 구독
        manager.subscribe("client1", "daytrading_signals")

        signal = {
            "type": "scan_update",
            "data": {"count": 5}
        }

        await manager.broadcast(signal, topic="daytrading_signals")

        # client1만 수신
        assert len(mock_ws1.messages) == 1
        assert len(mock_ws2.messages) == 0

    @pytest.mark.asyncio
    async def test_broadcast_scan_complete(self, manager):
        """스캔 완료 브로드캐스트"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws
        manager.subscribe("client1", "daytrading_scan")

        scan_result = {
            "type": "scan_complete",
            "data": {
                "market": "KOSPI",
                "count": 10,
                "candidates": [
                    {"ticker": "005930", "name": "삼성전자", "score": 90},
                    {"ticker": "000270", "name": "기아", "score": 75}
                ]
            }
        }

        await manager.broadcast(scan_result, topic="daytrading_scan")

        assert len(mock_ws.messages) == 1
        assert mock_ws.messages[0]["type"] == "scan_complete"
        assert mock_ws.messages[0]["data"]["count"] == 10

    @pytest.mark.asyncio
    async def test_broadcast_score_update(self, manager):
        """점수 업데이트 브로드캐스트"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws
        manager.subscribe("client1", "daytrading_signals")

        update = {
            "type": "score_update",
            "data": {
                "ticker": "005930",
                "previous_score": 75,
                "new_score": 90,
                "grade": "S"
            }
        }

        await manager.broadcast(update, topic="daytrading_signals")

        assert len(mock_ws.messages) == 1
        assert mock_ws.messages[0]["data"]["new_score"] == 90


# =============================================================================
# Test Subscription Management
# =============================================================================

class TestSubscriptionManagement:
    """구독 관리 테스트"""

    @pytest.fixture
    def manager(self):
        """ConnectionManager fixture"""
        return ConnectionManager()

    def test_subscribe_to_topic(self, manager):
        """토픽 구독"""
        manager.subscribe("client1", "daytrading_signals")

        assert "client1" in manager.subscriptions.get("daytrading_signals", set())

    def test_unsubscribe_from_topic(self, manager):
        """토픽 구독 해지"""
        manager.subscribe("client1", "daytrading_signals")
        manager.unsubscribe("client1", "daytrading_signals")

        assert "client1" not in manager.subscriptions.get("daytrading_signals", set())

    def test_unsubscribe_removes_empty_topic(self, manager):
        """구독자가 없으면 토픽 제거"""
        manager.subscribe("client1", "temp_topic")
        manager.unsubscribe("client1", "temp_topic")

        # 빈 토픽은 자동 제거됨
        assert "temp_topic" not in manager.subscriptions


# =============================================================================
# Test Disconnection Handling
# =============================================================================

class TestDisconnectionHandling:
    """연결 종료 처리 테스트"""

    @pytest.fixture
    def manager(self):
        """ConnectionManager fixture"""
        return ConnectionManager()

    def test_disconnect_removes_from_active_connections(self, manager):
        """연결 종료 시 active_connections에서 제거"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws
        manager.subscribe("client1", "daytrading_signals")

        manager.disconnect("client1")

        assert "client1" not in manager.active_connections
        assert "client1" not in manager.subscriptions.get("daytrading_signals", set())

    def test_disconnect_with_code_and_reason(self, manager):
        """종료 코드와 사유로 연결 종료"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws

        manager.disconnect("client1", code=1000, reason="Normal closure")

        assert "client1" not in manager.active_connections


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """에러 처리 테스트"""

    @pytest.fixture
    def manager(self):
        """ConnectionManager fixture"""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_send_to_disconnected_client_returns_false(self, manager):
        """연결되지 않은 클라이언트 전송 → False"""
        result = await manager.send_personal_message(
            {"data": "test"},
            "nonexistent_client"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_closed_websocket_removes_connection(self, manager):
        """닫힌 WebSocket에 전송 시 연결 제거"""
        mock_ws = MockWebSocket()
        await mock_ws.close()  # 닫힌 상태로 만듦
        manager.active_connections["client1"] = mock_ws

        result = await manager.send_personal_message({"data": "test"}, "client1")

        assert result is False
        assert "client1" not in manager.active_connections


# =============================================================================
# Test Daytrading Event Types
# =============================================================================

class TestDaytradingEventTypes:
    """단타 이벤트 타입 테스트"""

    @pytest.fixture
    def manager(self):
        """ConnectionManager fixture"""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_signal_created_event(self, manager):
        """신호 생성 이벤트"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws
        manager.subscribe("client1", "daytrading_signals")

        event = {
            "type": "signal_created",
            "data": {
                "id": 123,
                "ticker": "005930",
                "grade": "S",
                "total_score": 90
            },
            "timestamp": "2026-02-04T10:00:00+09:00"
        }

        await manager.broadcast(event, topic="daytrading_signals")

        assert mock_ws.messages[0]["type"] == "signal_created"

    @pytest.mark.asyncio
    async def test_signal_status_changed_event(self, manager):
        """신호 상태 변경 이벤트"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws
        manager.subscribe("client1", "daytrading_signals")

        event = {
            "type": "signal_status_changed",
            "data": {
                "id": 123,
                "ticker": "005930",
                "old_status": "OPEN",
                "new_status": "CLOSED",
                "exit_reason": "Target reached"
            },
            "timestamp": "2026-02-04T14:30:00+09:00"
        }

        await manager.broadcast(event, topic="daytrading_signals")

        assert mock_ws.messages[0]["data"]["new_status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_scan_progress_event(self, manager):
        """스캔 진행률 이벤트"""
        mock_ws = MockWebSocket()
        manager.active_connections["client1"] = mock_ws
        manager.subscribe("client1", "daytrading_scan")

        event = {
            "type": "scan_progress",
            "data": {
                "market": "KOSPI",
                "progress": 50,
                "processed": 500,
                "total": 1000
            },
            "timestamp": "2026-02-04T10:30:00+09:00"
        }

        await manager.broadcast(event, topic="daytrading_scan")

        assert mock_ws.messages[0]["data"]["progress"] == 50
