"""
WebSocket Mock 서버

WebSocket 연결, 메시지 송수신, 브로드캐스트 기능을 Mock 처리합니다.
"""

from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
import asyncio
import json


class MockWebSocket:
    """
    Mock WebSocket 연결

    실제 WebSocket 연결 없이 테스트할 수 있습니다.
    """

    def __init__(self, client_id: str = "test_client"):
        """
        Mock WebSocket 초기화

        Args:
            client_id: 클라이언트 ID
        """
        self.client_id = client_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.received_messages: List[Dict[str, Any]] = []
        self.closed = False
        self.subscribed_topics: Set[str] = set()

    async def send_json(self, data: Dict[str, Any]):
        """
        JSON 메시지 전송

        Args:
            data: 전송할 데이터
        """
        if self.closed:
            raise RuntimeError("WebSocket is closed")

        self.sent_messages.append(data)

    async def receive_json(self):
        """
        JSON 메시지 수신

        Returns:
            수신한 데이터
        """
        if self.closed:
            raise RuntimeError("WebSocket is closed")

        if not self.received_messages:
            # 메시지가 없으면 대기
            await asyncio.sleep(0.1)
            return {}

        return self.received_messages.pop(0)

    async def close(self):
        """연결 종료"""
        self.closed = True
        self.subscribed_topics.clear()

    def add_received_message(self, message: Dict[str, Any]):
        """
        수신 메시지 추가 (테스트용)

        Args:
            message: 수신할 메시지
        """
        self.received_messages.append(message)

    def get_last_sent_message(self) -> Optional[Dict[str, Any]]:
        """마지막 전송 메시지 반환"""
        if not self.sent_messages:
            return None
        return self.sent_messages[-1]

    def clear_sent_messages(self):
        """전송 메시지 초기화"""
        self.sent_messages.clear()


class MockConnectionManager:
    """
    Mock Connection Manager

    WebSocket 연결 관리, 토픽 구독, 브로드캐스트 기능을 제공합니다.
    """

    def __init__(self):
        """Connection Manager 초기화"""
        self.active_connections: Dict[str, MockWebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # client_id -> topics
        self.topic_subscribers: Dict[str, Set[str]] = {}  # topic -> client_ids

    async def connect(self, websocket: MockWebSocket, client_id: str):
        """
        클라이언트 연결

        Args:
            websocket: WebSocket 연결 객체
            client_id: 클라이언트 ID
        """
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()

    async def disconnect(self, client_id: str):
        """
        클라이언트 연결 해제

        Args:
            client_id: 클라이언트 ID
        """
        # 모든 토픽에서 구독 취소
        if client_id in self.subscriptions:
            for topic in self.subscriptions[client_id]:
                if topic in self.topic_subscribers:
                    self.topic_subscribers[topic].discard(client_id)

        # 연결 제거
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]

    async def subscribe(self, client_id: str, topic: str):
        """
        토픽 구독

        Args:
            client_id: 클라이언트 ID
            topic: 구독할 토픽 (예: price:005930)
        """
        if client_id not in self.subscriptions:
            self.subscriptions[client_id] = set()

        self.subscriptions[client_id].add(topic)

        if topic not in self.topic_subscribers:
            self.topic_subscribers[topic] = set()
        self.topic_subscribers[topic].add(client_id)

    async def unsubscribe(self, client_id: str, topic: str):
        """
        토픽 구독 취소

        Args:
            client_id: 클라이언트 ID
            topic: 구독 취소할 토픽
        """
        if client_id in self.subscriptions:
            self.subscriptions[client_id].discard(topic)

        if topic in self.topic_subscribers:
            self.topic_subscribers[topic].discard(client_id)

    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """
        토픽 구독자에게 메시지 브로드캐스트

        Args:
            topic: 브로드캐스트할 토픽
            message: 브로드캐스트할 메시지
        """
        if topic not in self.topic_subscribers:
            return

        for client_id in self.topic_subscribers[topic]:
            ws = self.active_connections.get(client_id)
            if ws and not ws.closed:
                await ws.send_json(message)

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """
        특정 클라이언트에게 메시지 전송

        Args:
            message: 전송할 메시지
            client_id: 수신 클라이언트 ID
        """
        ws = self.active_connections.get(client_id)
        if ws and not ws.closed:
            await ws.send_json(message)

    def get_connection_count(self) -> int:
        """활성 연결 수 반환"""
        return len(self.active_connections)

    def get_subscriber_count(self, topic: str) -> int:
        """토픽 구독자 수 반환"""
        if topic not in self.topic_subscribers:
            return 0
        return len(self.topic_subscribers[topic])

    def is_subscribed(self, client_id: str, topic: str) -> bool:
        """토픽 구독 여부 확인"""
        if client_id not in self.subscriptions:
            return False
        return topic in self.subscriptions[client_id]


class MockHeartbeatManager:
    """
    Mock Heartbeat Manager

    WebSocket 하트비트 관리 기능을 제공합니다.
    """

    def __init__(self, timeout: int = 30):
        """
        Heartbeat Manager 초기화

        Args:
            timeout: 타임아웃 시간 (초)
        """
        self.timeout = timeout
        self.last_pong: Dict[str, datetime] = {}
        self.connection_manager: Optional[MockConnectionManager] = None

    def set_connection_manager(self, manager: MockConnectionManager):
        """
        연결 관리자 설정

        Args:
            manager: Connection Manager 인스턴스
        """
        self.connection_manager = manager

    async def ping_all(self):
        """모든 연결에 ping 전송"""
        if not self.connection_manager:
            return

        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }

        for client_id, ws in self.connection_manager.active_connections.items():
            if not ws.closed:
                await ws.send_json(ping_message)

    def record_pong(self, client_id: str):
        """
        Pong 수신 시간 기록

        Args:
            client_id: 클라이언트 ID
        """
        self.last_pong[client_id] = datetime.now()

    def is_client_alive(self, client_id: str) -> bool:
        """
        클라이언트 생존 여부 확인

        Args:
            client_id: 클라이언트 ID

        Returns:
            생존 여부
        """
        if client_id not in self.last_pong:
            return False

        last_time = self.last_pong[client_id]
        current_time = datetime.now()

        # 타임아웃 확인
        time_diff = (current_time - last_time).total_seconds()
        return time_diff < self.timeout

    def remove_client(self, client_id: str):
        """
        클라이언트 제거

        Args:
            client_id: 제거할 클라이언트 ID
        """
        if client_id in self.last_pong:
            del self.last_pong[client_id]

    async def check_timeouts(self):
        """타임아웃된 클라이언트 확인 및 처리"""
        if not self.connection_manager:
            return

        timeout_clients = []

        for client_id in self.connection_manager.active_connections.keys():
            if not self.is_client_alive(client_id):
                timeout_clients.append(client_id)

        for client_id in timeout_clients:
            await self.connection_manager.disconnect(client_id)
            self.remove_client(client_id)


class MockPriceUpdateBroadcaster:
    """
    Mock 가격 업데이트 브로드캐스터

    실시간 가격 업데이트 브로드캐스트 기능을 Mock 처리합니다.
    """

    def __init__(self):
        """가격 브로드캐스터 초기화"""
        self.connection_manager = MockConnectionManager()
        self.heartbeat_manager = MockHeartbeatManager()
        self.heartbeat_manager.set_connection_manager(self.connection_manager)
        self.is_running = False

    async def start(self):
        """브로드캐스터 시작"""
        self.is_running = True

    async def stop(self):
        """브로드캐스터 중지"""
        self.is_running = False

    async def broadcast_price_update(self, ticker: str, price: int, change: int):
        """
        가격 업데이트 브로드캐스트

        Args:
            ticker: 종목 코드
            price: 현재가
            change: 변동액
        """
        message = {
            "type": "price_update",
            "ticker": ticker,
            "price": price,
            "change": change,
            "timestamp": datetime.now().isoformat()
        }

        topic = f"price:{ticker}"
        await self.connection_manager.broadcast(topic, message)

    async def add_client(self, client_id: str):
        """
        클라이언트 추가

        Args:
            client_id: 클라이언트 ID
        """
        ws = MockWebSocket(client_id)
        await self.connection_manager.connect(ws, client_id)
        return ws


# ============================================================================
# Pytest Fixtures
# ============================================================================

import pytest


@pytest.fixture
def mock_websocket():
    """
    Mock WebSocket Fixture

    Example:
        def test_websocket_send(mock_websocket):
            await mock_websocket.send_json({"test": "data"})
            assert len(mock_websocket.sent_messages) == 1
    """
    return MockWebSocket()


@pytest.fixture
async def mock_connection_manager():
    """
    Mock Connection Manager Fixture

    Example:
        async def test_broadcast(mock_connection_manager):
            ws1 = MockWebSocket("client1")
            ws2 = MockWebSocket("client2")

            await mock_connection_manager.connect(ws1, "client1")
            await mock_connection_manager.subscribe("client1", "price:005930")

            await mock_connection_manager.broadcast("price:005930", {"price": 80500})

            assert len(ws1.sent_messages) == 1
            assert len(ws2.sent_messages) == 0
    """
    return MockConnectionManager()


@pytest.fixture
def mock_heartbeat_manager():
    """
    Mock Heartbeat Manager Fixture

    Example:
        def test_heartbeat(mock_heartbeat_manager):
            mock_heartbeat_manager.record_pong("client1")
            assert mock_heartbeat_manager.is_client_alive("client1") is True
    """
    return MockHeartbeatManager()


@pytest.fixture
async def mock_price_broadcaster():
    """
    Mock 가격 브로드캐스터 Fixture

    Example:
        async def test_price_broadcast(mock_price_broadcaster):
            await mock_price_broadcaster.start()
            await mock_price_broadcaster.broadcast_price_update("005930", 80500, 500)

            ws = await mock_price_broadcaster.add_client("client1")
            await mock_price_broadcaster.connection_manager.subscribe("client1", "price:005930")

            assert len(ws.sent_messages) > 0
    """
    broadcaster = MockPriceUpdateBroadcaster()
    await broadcaster.start()
    yield broadcaster
    await broadcaster.stop()
