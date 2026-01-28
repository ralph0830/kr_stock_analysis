"""
WebSocket 연동 통합 테스트

KOA → Redis → WebSocket → 프론트엔드 흐름을 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.koa.pipeline import RealtimePipelineManager
from src.koa.base import RealtimePrice
from src.websocket.server import ConnectionManager


class MockWebSocket:
    """Mock WebSocket 연결"""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.messages = []
        self._accepted = False

    async def accept(self):
        """연결 수락"""
        self._accepted = True

    async def send_json(self, message: dict):
        """JSON 메시지 전송"""
        self.messages.append(message)

    def get_messages(self) -> list:
        """수신한 메시지 리스트"""
        return self.messages

    def clear_messages(self):
        """메시지 초기화"""
        self.messages.clear()


class TestConnectionManager:
    """ConnectionManager 테스트"""

    def test_initial_state(self):
        """초기 상태 확인"""
        manager = ConnectionManager()

        assert manager.get_connection_count() == 0
        assert len(manager.active_connections) == 0
        assert len(manager.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        """연결 및 해제 테스트"""
        manager = ConnectionManager()
        websocket = MockWebSocket("client_1")

        await manager.connect(websocket, "client_1")

        assert manager.get_connection_count() == 1
        assert "client_1" in manager.active_connections
        assert websocket._accepted is True

        manager.disconnect("client_1")

        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """개인 메시지 전송 테스트"""
        manager = ConnectionManager()
        websocket = MockWebSocket("client_1")

        await manager.connect(websocket, "client_1")

        message = {"type": "test", "data": "hello"}
        success = await manager.send_personal_message(message, "client_1")

        assert success is True
        assert len(websocket.get_messages()) == 1
        assert websocket.get_messages()[0] == message

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(self):
        """존재하지 않는 클라이언트에게 전송 테스트"""
        manager = ConnectionManager()

        success = await manager.send_personal_message(
            {"data": "test"},
            "nonexistent"
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self):
        """구독 및 해제 테스트"""
        manager = ConnectionManager()

        manager.subscribe("client_1", "price:005930")
        manager.subscribe("client_1", "price:000660")
        manager.subscribe("client_2", "price:005930")

        assert manager.get_subscriber_count("price:005930") == 2
        assert manager.get_subscriber_count("price:000660") == 1

        subscriptions = manager.get_subscriptions("client_1")
        assert "price:005930" in subscriptions
        assert "price:000660" in subscriptions

        manager.unsubscribe("client_1", "price:005930")

        assert manager.get_subscriber_count("price:005930") == 1
        assert manager.get_subscriber_count("price:000660") == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self):
        """전체 브로드캐스트 테스트"""
        manager = ConnectionManager()
        ws1 = MockWebSocket("client_1")
        ws2 = MockWebSocket("client_2")

        await manager.connect(ws1, "client_1")
        await manager.connect(ws2, "client_2")

        message = {"type": "broadcast", "data": "all"}
        await manager.broadcast(message)

        assert len(ws1.get_messages()) == 1
        assert len(ws2.get_messages()) == 1
        assert ws1.get_messages()[0] == message
        assert ws2.get_messages()[0] == message

    @pytest.mark.asyncio
    async def test_broadcast_to_topic(self):
        """토픽 브로드캐스트 테스트"""
        manager = ConnectionManager()
        ws1 = MockWebSocket("client_1")
        ws2 = MockWebSocket("client_2")

        await manager.connect(ws1, "client_1")
        await manager.connect(ws2, "client_2")

        # client_1만 price:005930 토픽 구독
        manager.subscribe("client_1", "price:005930")

        message = {"type": "price_update", "ticker": "005930"}
        await manager.broadcast(message, topic="price:005930")

        # client_1에게만 전송되어야 함
        assert len(ws1.get_messages()) == 1
        assert len(ws2.get_messages()) == 0
        assert ws1.get_messages()[0] == message

    @pytest.mark.asyncio
    async def test_disconnect_removes_subscriptions(self):
        """연결 해제 시 구독 제거 테스트"""
        manager = ConnectionManager()
        ws1 = MockWebSocket("client_1")

        await manager.connect(ws1, "client_1")
        manager.subscribe("client_1", "price:005930")
        manager.subscribe("client_1", "price:000660")

        assert manager.get_subscriber_count("price:005930") == 1
        assert manager.get_subscriber_count("price:000660") == 1

        manager.disconnect("client_1")

        assert manager.get_subscriber_count("price:005930") == 0
        assert manager.get_subscriber_count("price:000660") == 0


class TestKOAWebSocketIntegration:
    """KOA WebSocket 통합 테스트"""

    @pytest.mark.asyncio
    async def test_koa_service_price_handler(self):
        """KOA 서비스 가격 핸들러 테스트"""
        from src.koa.service import RealtimeDataService

        # KOA 서비스 생성 및 시작
        service = RealtimeDataService(use_mock=True, update_interval=0.1)
        await service.start()

        # 가격 업데이트 수신 확인
        received_updates = []

        def price_handler(ticker: str, price_data):
            """동기 가격 핸들러"""
            received_updates.append((ticker, price_data))

        service.add_price_handler(price_handler)

        # 종목 구독
        await service.subscribe("005930")

        # 잠시 대기 (가격 업데이트 발생 대기)
        await asyncio.sleep(0.3)

        # 핸들러가 호출되었는지 확인
        assert len(received_updates) > 0, "No price updates received"

        # 데이터 형식 확인
        ticker, price_data = received_updates[0]
        assert ticker == "005930"
        assert price_data.price > 0

        await service.stop()

    @pytest.mark.asyncio
    async def test_multiple_clients_receive_same_update(self):
        """여러 클라이언트가 동일한 업데이트를 받는지 테스트"""
        manager = ConnectionManager()
        clients = []

        # 여러 클라이언트 연결
        for i in range(3):
            ws = MockWebSocket(f"client_{i}")
            await manager.connect(ws, f"client_{i}")
            manager.subscribe(f"client_{i}", "price:005930")
            clients.append(ws)

        # 수동 브로드캐스트 테스트
        test_message = {
            "type": "price_update",
            "ticker": "005930",
            "data": {
                "price": 82500,
                "change": 500,
                "change_rate": 0.61,
                "volume": 15000000,
            },
            "timestamp": "2024-01-26T10:30:00Z"
        }

        await manager.broadcast(test_message, topic="price:005930")

        # 모든 클라이언트가 메시지를 받았는지 확인
        for ws in clients:
            messages = ws.get_messages()
            assert len(messages) == 1
            assert messages[0]["ticker"] == "005930"

    @pytest.mark.asyncio
    async def test_topic_filtering(self):
        """토픽 필터링 테스트"""
        manager = ConnectionManager()

        # 두 클라이언트 연결
        ws1 = MockWebSocket("client_1")
        ws2 = MockWebSocket("client_2")

        await manager.connect(ws1, "client_1")
        await manager.connect(ws2, "client_2")

        # 다른 토픽 구독
        manager.subscribe("client_1", "price:005930")
        manager.subscribe("client_2", "price:000660")

        # 005930 메시지만 전송
        message_005930 = {
            "type": "price_update",
            "ticker": "005930",
            "data": {"price": 82500}
        }

        await manager.broadcast(message_005930, topic="price:005930")

        # client_1만 받아야 함
        assert len(ws1.get_messages()) == 1
        assert len(ws2.get_messages()) == 0

        # 000660 메시지 전송
        message_000660 = {
            "type": "price_update",
            "ticker": "000660",
            "data": {"price": 92000}
        }

        await manager.broadcast(message_000660, topic="price:000660")

        # client_2만 받아야 함
        assert len(ws1.get_messages()) == 1  # 여전히 1개
        assert len(ws2.get_messages()) == 1  # 1개 받음


class TestWebSocketMessageFormat:
    """WebSocket 메시지 포맷 테스트"""

    @pytest.mark.asyncio
    async def test_price_update_message_format(self):
        """가격 업데이트 메시지 포맷 테스트"""
        manager = ConnectionManager()
        ws = MockWebSocket("test_client")

        await manager.connect(ws, "test_client")

        # 클라이언트를 토픽에 구독시킴
        manager.subscribe("test_client", "price:005930")

        # 가격 업데이트 메시지 전송
        message = {
            "type": "price_update",
            "ticker": "005930",
            "data": {
                "price": 82500,
                "change": 500,
                "change_rate": 0.61,
                "volume": 15000000,
            },
            "timestamp": "2024-01-26T10:30:00Z"
        }

        await manager.broadcast(message, topic="price:005930")

        messages = ws.get_messages()
        assert len(messages) == 1

        msg = messages[0]
        assert msg["type"] == "price_update"
        assert msg["ticker"] == "005930"
        assert "data" in msg
        assert "timestamp" in msg
        assert msg["data"]["price"] == 82500
