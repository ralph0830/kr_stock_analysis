"""
WebSocket 서버 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.websocket.server import ConnectionManager, PriceUpdateBroadcaster


class TestConnectionManager:
    """ConnectionManager 테스트"""

    @pytest.mark.asyncio
    async def test_connect(self):
        """연결 테스트"""
        manager = ConnectionManager()
        websocket = AsyncMock()

        client_id = "test_client"
        # ConnectionManager.connect()는 이미 accept()가 호출된 websocket을 받는다
        # accept()는 routes.py의 websocket_endpoint에서 호출됨
        await manager.connect(websocket, client_id)

        assert client_id in manager.active_connections
        assert manager.active_connections[client_id] == websocket

    def test_disconnect(self):
        """연결 종료 테스트"""
        manager = ConnectionManager()
        websocket = MagicMock()

        manager.active_connections["test_client"] = websocket
        manager.subscriptions["test_topic"] = {"test_client"}

        manager.disconnect("test_client")

        assert "test_client" not in manager.active_connections
        assert "test_topic" not in manager.subscriptions

    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """개별 메시지 전송 테스트"""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.send_json = AsyncMock()

        manager.active_connections["test_client"] = websocket

        message = {"data": "test"}
        result = await manager.send_personal_message(message, "test_client")

        assert result is True
        websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_failure(self):
        """개별 메시지 전송 실패 테스트"""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.send_json = AsyncMock(side_effect=Exception("Connection error"))

        manager.active_connections["test_client"] = websocket

        message = {"data": "test"}
        result = await manager.send_personal_message(message, "test_client")

        # 실패 후 연결 종료
        assert result is False
        assert "test_client" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """브로드캐스트 테스트"""
        manager = ConnectionManager()

        # 3개 클라이언트 생성
        clients = {}
        for i in range(3):
            websocket = AsyncMock()
            websocket.send_json = AsyncMock()
            client_id = f"client_{i}"
            clients[client_id] = websocket
            manager.active_connections[client_id] = websocket

        # 브로드캐스트
        message = {"data": "broadcast_test"}
        await manager.broadcast(message)

        # 모든 클라이언트에게 전송 확인
        for websocket in clients.values():
            websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_topic(self):
        """토픽 기반 브로드캐스트 테스트"""
        manager = ConnectionManager()

        # 클라이언트 생성 및 구독
        for i in range(3):
            websocket = AsyncMock()
            websocket.send_json = AsyncMock()
            client_id = f"client_{i}"
            manager.active_connections[client_id] = websocket

            # 첫 2개 클라이언트만 토픽 구독
            if i < 2:
                manager.subscribe(client_id, "test_topic")

        # 토픽 브로드캐스트
        message = {"data": "topic_broadcast"}
        await manager.broadcast(message, topic="test_topic")

        # 구독한 클라이언트에게만 전송 확인
        for i in range(2):
            client_id = f"client_{i}"
            websocket = manager.active_connections[client_id]
            websocket.send_json.assert_called_once_with(message)

        # 구독하지 않은 클라이언트는 전송 안 됨
        client_id = "client_2"
        websocket = manager.active_connections[client_id]
        websocket.send_json.assert_not_called()

    def test_subscribe(self):
        """구독 테스트"""
        manager = ConnectionManager()
        manager.subscribe("client_1", "topic1")
        manager.subscribe("client_2", "topic1")
        manager.subscribe("client_1", "topic2")

        assert "client_1" in manager.subscriptions["topic1"]
        assert "client_2" in manager.subscriptions["topic1"]
        assert "client_1" in manager.subscriptions["topic2"]

    def test_unsubscribe(self):
        """구독 취소 테스트"""
        manager = ConnectionManager()
        manager.subscribe("client_1", "topic1")
        manager.subscribe("client_2", "topic1")

        manager.unsubscribe("client_1", "topic1")

        assert "client_1" not in manager.subscriptions["topic1"]
        assert "client_2" in manager.subscriptions["topic1"]

    def test_get_subscriptions(self):
        """구독 목록 조회 테스트"""
        manager = ConnectionManager()
        manager.subscribe("client_1", "topic1")
        manager.subscribe("client_1", "topic2")
        manager.subscribe("client_2", "topic1")

        subscriptions = manager.get_subscriptions("client_1")
        assert subscriptions == {"topic1", "topic2"}

    def test_get_connection_count(self):
        """연결 수 조회 테스트"""
        manager = ConnectionManager()
        assert manager.get_connection_count() == 0

        for i in range(5):
            manager.active_connections[f"client_{i}"] = MagicMock()

        assert manager.get_connection_count() == 5

    def test_get_subscriber_count(self):
        """구독자 수 조회 테스트"""
        manager = ConnectionManager()
        assert manager.get_subscriber_count("topic1") == 0

        for i in range(3):
            manager.subscribe(f"client_{i}", "topic1")

        assert manager.get_subscriber_count("topic1") == 3


class TestPriceUpdateBroadcaster:
    """PriceUpdateBroadcaster 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        broadcaster = PriceUpdateBroadcaster(interval_seconds=5)
        assert broadcaster.is_running() is False

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """시작/중지 테스트"""
        broadcaster = PriceUpdateBroadcaster(interval_seconds=1)

        # 시작
        await broadcaster.start()
        assert broadcaster.is_running() is True

        # 중지
        await broadcaster.stop()
        assert broadcaster.is_running() is False

    @pytest.mark.asyncio
    async def test_generate_mock_price_updates(self):
        """Mock 가격 업데이트 생성 테스트"""
        broadcaster = PriceUpdateBroadcaster()
        updates = broadcaster._generate_mock_price_updates()

        assert isinstance(updates, dict)
        assert "005930" in updates
        assert "000660" in updates

        # 데이터 구조 확인
        samsung = updates["005930"]
        assert "price" in samsung
        assert "change" in samsung
        assert "change_rate" in samsung
        assert "volume" in samsung


class TestWebSocketIntegration:
    """WebSocket 통합 테스트"""

    def test_manager_singleton_usage(self):
        """관리자 인스턴스 사용 테스트"""
        from src.websocket.server import connection_manager

        # 전역 인스턴스 사용
        assert connection_manager is not None
        assert isinstance(connection_manager, ConnectionManager)

    def test_broadcaster_singleton_usage(self):
        """브로드캐스터 인스턴스 사용 테스트"""
        from src.websocket.server import price_broadcaster

        # 전역 인스턴스 사용
        assert price_broadcaster is not None
        assert isinstance(price_broadcaster, PriceUpdateBroadcaster)
