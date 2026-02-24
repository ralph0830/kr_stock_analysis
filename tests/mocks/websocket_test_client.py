"""
WebSocket 테스트 클라이언트

실제 WebSocket 프로토콜을 사용한 테스트를 위한 헬퍼 클래스입니다.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import websockets.client as ws_client
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class WebSocketTestClient:
    """
    WebSocket 테스트 클라이언트

    웹소켓 서버에 연결하여 메시지 송수신 테스트를 수행합니다.

    Usage:
        client = WebSocketTestClient("ws://localhost:5111/ws")
        await client.connect()

        # 메시지 전송
        await client.send_json({"type": "subscribe", "topic": "price:005930"})

        # 메시지 수신
        msg = await client.receive_json(timeout=1.0)

        await client.disconnect()
    """

    def __init__(
        self,
        uri: str,
        origin: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        초기화

        Args:
            uri: WebSocket URI (예: "ws://localhost:5111/ws")
            origin: Origin 헤더
            headers: 추가 헤더
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package is required for WebSocketTestClient")

        self.uri = uri
        self.origin = origin
        self.headers = headers or {}
        self._ws: Optional[Any] = None
        self._is_connected = False

        # 수신 메시지 기록
        self.received_messages: List[Dict[str, Any]] = []
        self.sent_messages: List[Dict[str, Any]] = []

    async def connect(self, timeout: float = 5.0) -> bool:
        """
        서버에 연결

        Args:
            timeout: 연결 타임아웃 (초)

        Returns:
            연결 성공 여부
        """
        if not WEBSOCKETS_AVAILABLE:
            return False

        try:
            extra_headers = {}
            if self.origin:
                extra_headers["Origin"] = self.origin
            extra_headers.update(self.headers)

            self._ws = await asyncio.wait_for(
                ws_client.connect(self.uri, extra_headers=extra_headers),
                timeout=timeout
            )
            self._is_connected = True

            # 연결 메시지 수신
            try:
                msg = await asyncio.wait_for(self.receive_json(timeout=1.0), timeout=1.0)
                if msg.get("type") == "connected":
                    self.client_id = msg.get("client_id")
            except asyncio.TimeoutError:
                pass

            return True

        except Exception as e:
            print(f"WebSocketTestClient connect error: {e}")
            return False

    async def disconnect(self):
        """연결 해제"""
        if self._ws:
            await self._ws.close()
            self._is_connected = False

    async def send_json(self, data: Dict[str, Any]):
        """
        JSON 메시지 전송

        Args:
            data: 전송할 데이터
        """
        if not self._is_connected or not self._ws:
            raise RuntimeError("Not connected")

        await self._ws.send(json.dumps(data))
        self.sent_messages.append(data)

    async def receive_json(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        JSON 메시지 수신

        Args:
            timeout: 수신 타임아웃 (초)

        Returns:
            수신한 데이터 또는 None (타임아웃)
        """
        if not self._is_connected or not self._ws:
            raise RuntimeError("Not connected")

        try:
            message = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
            data = json.loads(message)
            self.received_messages.append(data)
            return data
        except asyncio.TimeoutError:
            return None
        except ConnectionClosedOK:
            self._is_connected = False
            return None
        except ConnectionClosedError:
            self._is_connected = False
            return None

    async def send_and_wait(
        self,
        send_data: Dict[str, Any],
        expected_type: Optional[str] = None,
        timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        메시지 전송 후 응답 대기

        Args:
            send_data: 전송할 데이터
            expected_type: 기대하는 응답 메시지 타입
            timeout: 응답 대기 타임아웃 (초)

        Returns:
            응답 데이터 또는 None
        """
        await self.send_json(send_data)
        return await self.wait_for_message_type(expected_type, timeout)

    async def wait_for_message_type(
        self,
        message_type: Optional[str],
        timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        특정 타입의 메시지 대기

        Args:
            message_type: 기다릴 메시지 타입 (None이면 아무 메시지나)
            timeout: 대기 타임아웃 (초)

        Returns:
            메시지 데이터 또는 None
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = timeout - elapsed

            if remaining <= 0:
                return None

            msg = await self.receive_json(timeout=remaining)
            if msg is None:
                return None

            if message_type is None or msg.get("type") == message_type:
                return msg

    def clear_history(self):
        """송수신 메시지 기록 초기화"""
        self.received_messages.clear()
        self.sent_messages.clear()

    @property
    def is_connected(self) -> bool:
        """연결 상태"""
        return self._is_connected

    def get_last_message(self, message_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        마지막 메시지 조회

        Args:
            message_type: 필터링할 메시지 타입

        Returns:
            마지막 메시지 또는 None
        """
        if not self.received_messages:
            return None

        if message_type:
            for msg in reversed(self.received_messages):
                if msg.get("type") == message_type:
                    return msg
            return None

        return self.received_messages[-1]

    def count_messages(self, message_type: Optional[str] = None) -> int:
        """
        수신 메시지 수 카운트

        Args:
            message_type: 카운트할 메시지 타입

        Returns:
            메시지 수
        """
        if message_type:
            return sum(1 for msg in self.received_messages if msg.get("type") == message_type)
        return len(self.received_messages)


class WebSocketTestHelper:
    """
    WebSocket 테스트 헬퍼

    여러 클라이언트를 관리하고 테스트 시나리오를 실행합니다.
    """

    def __init__(self, base_uri: str = "ws://localhost:5111/ws"):
        """
        초기화

        Args:
            base_uri: 기본 WebSocket URI
        """
        self.base_uri = base_uri
        self.clients: List[WebSocketTestClient] = []

    async def create_client(
        self,
        origin: str = "http://localhost:5110",
        connect: bool = True
    ) -> WebSocketTestClient:
        """
        새 클라이언트 생성 및 연결

        Args:
            origin: Origin 헤더
            connect: 즉시 연결 여부

        Returns:
            생성된 클라이언트
        """
        client = WebSocketTestClient(self.base_uri, origin=origin)

        if connect:
            success = await client.connect()
            if not success:
                raise RuntimeError(f"Failed to connect client to {self.base_uri}")

        self.clients.append(client)
        return client

    async def disconnect_all(self):
        """모든 클라이언트 연결 해제"""
        for client in self.clients:
            await client.disconnect()
        self.clients.clear()

    async def broadcast_test(
        self,
        topic: str,
        num_subscribers: int = 3,
        num_non_subscribers: int = 2
    ) -> Dict[str, Any]:
        """
        브로드캐스트 테스트 시나리오

        Args:
            topic: 구독할 토픽
            num_subscribers: 구독자 수
            num_non_subscribers: 비구독자 수

        Returns:
            테스트 결과
        """
        subscribers = []
        non_subscribers = []

        # 구독자 생성
        for i in range(num_subscribers):
            client = await self.create_client()
            await client.send_and_wait({
                "type": "subscribe",
                "topic": topic
            }, expected_type="subscribed")
            subscribers.append(client)

        # 비구독자 생성
        for i in range(num_non_subscribers):
            client = await self.create_client()
            non_subscribers.append(client)

        # 결과 반환 (나중에 브로드캐스트 후 수신 확인)
        return {
            "subscribers": subscribers,
            "non_subscribers": non_subscribers,
        }

    def cleanup(self):
        """리소스 정리"""
        self.clients.clear()


# ============================================================================
# 테스트 유틸리티 함수
# ============================================================================

def create_mock_price_update(ticker: str, price: int, change: int) -> Dict[str, Any]:
    """
    Mock 가격 업데이트 메시지 생성

    Args:
        ticker: 종목 코드
        price: 현재가
        change: 변동액

    Returns:
        가격 업데이트 메시지
    """
    base_price = price - change
    change_rate = (change / base_price * 100) if base_price > 0 else 0.0

    return {
        "type": "price_update",
        "ticker": ticker,
        "data": {
            "price": price,
            "change": change,
            "change_rate": round(change_rate, 2),
            "volume": 1000000,
            "bid_price": price - 10,
            "ask_price": price + 10,
        },
        "timestamp": datetime.now().isoformat(),
    }


def assert_connected_message(message: Dict[str, Any]):
    """연결 메시지 검증"""
    assert message.get("type") == "connected"
    assert "client_id" in message
    assert message.get("message") == "WebSocket connection established"


def assert_subscribed_message(message: Dict[str, Any], topic: str):
    """구독 메시지 검증"""
    assert message.get("type") == "subscribed"
    assert message.get("topic") == topic
    assert "Subscribed to" in message.get("message", "")


def assert_price_update_message(message: Dict[str, Any], ticker: str):
    """가격 업데이트 메시지 검증"""
    assert message.get("type") == "price_update"
    assert message.get("ticker") == ticker
    assert "data" in message
    assert "timestamp" in message

    data = message["data"]
    required_fields = ["price", "change", "change_rate", "volume"]
    for field in required_fields:
        assert field in data


# ============================================================================
# Pytest Fixture
# ============================================================================

import pytest


@pytest.fixture
async def websocket_helper():
    """
    WebSocket 테스트 헬퍼 Fixture
    """
    helper = WebSocketTestHelper()
    yield helper
    await helper.disconnect_all()
    helper.cleanup()


@pytest.fixture
async def websocket_client():
    """
    WebSocket 테스트 클라이언트 Fixture
    """
    client = WebSocketTestClient("ws://localhost:5111/ws")
    await client.connect()
    yield client
    await client.disconnect()
