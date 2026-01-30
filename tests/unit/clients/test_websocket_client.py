"""
WebSocket 클라이언트 단위 테스트
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from src.clients.websocket_client import (
    PriceUpdate,
    WebSocketClient,
    WebSocketClientPool,
    subscribe_to_tickers,
)


class TestPriceUpdate:
    """PriceUpdate 데이터클래스 테스트"""

    def test_price_update_from_dict(self):
        """딕셔너리에서 PriceUpdate 객체 생성"""
        data = {
            "ticker": "005930",
            "price": 80500,
            "change": 500,
            "change_percent": 0.62,
            "volume": 1000000,
            "timestamp": "2024-01-15T10:30:00",
        }

        update = PriceUpdate.from_dict(data)

        assert update.ticker == "005930"
        assert update.price == 80500
        assert update.change == 500
        assert update.change_percent == 0.62
        assert update.volume == 1000000

    def test_price_update_repr(self):
        """PriceUpdate 문자열 표현 테스트"""
        update = PriceUpdate(
            ticker="005930",
            price=80500,
            change=500,
            change_percent=0.62,
            volume=1000000,
            timestamp="2024-01-15T10:30:00",
        )

        repr_str = repr(update)
        assert "005930" in repr_str
        assert "80500" in repr_str


class TestWebSocketClient:
    """WebSocketClient 클래스 테스트"""

    @pytest.fixture
    def ws_client(self):
        return WebSocketClient("ws://localhost:5111/ws/price")

    def test_init(self, ws_client):
        """클라이언트 초기화 테스트"""
        assert ws_client.uri == "ws://localhost:5111/ws/price"
        assert ws_client.reconnect_interval == 5.0
        assert ws_client.ping_interval == 20.0
        assert ws_client._websocket is None
        assert len(ws_client._subscriptions) == 0
        assert len(ws_client._callbacks) == 0

    def test_custom_init(self):
        """사용자 정의 초기화 테스트"""
        client = WebSocketClient(
            uri="ws://localhost:5111/ws/price",
            reconnect_interval=10.0,
            ping_interval=30.0,
        )

        assert client.reconnect_interval == 10.0
        assert client.ping_interval == 30.0

    @pytest.mark.asyncio
    async def test_connect(self, ws_client):
        """WebSocket 연결 테스트"""
        # AsyncMock으로 websockets.connect 모킹
        mock_ws = AsyncMock()
        mock_ws.closed = False

        # websockets.connect를 모킹하여 AsyncContextManager를 반환하도록 설정
        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            await ws_client.connect()
            assert ws_client._websocket == mock_ws

    @pytest.mark.asyncio
    async def test_subscribe(self, ws_client):
        """종목 구독 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        ws_client._websocket = mock_ws

        await ws_client.subscribe("005930")

        # 구독 메시지 전송 확인
        sent_message = json.loads(mock_ws.send.call_args[0][0])
        assert sent_message["action"] == "subscribe"
        assert sent_message["topic"] == "price:005930"
        assert "005930" in ws_client._subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_without_connection(self, ws_client):
        """연결 없이 구독 시도 테스트"""
        with pytest.raises(ConnectionError):
            await ws_client.subscribe("005930")

    @pytest.mark.asyncio
    async def test_unsubscribe(self, ws_client):
        """구독 취소 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        ws_client._websocket = mock_ws
        ws_client._subscriptions.add("005930")

        await ws_client.unsubscribe("005930")

        # 구독 취소 메시지 전송 확인
        sent_message = json.loads(mock_ws.send.call_args[0][0])
        assert sent_message["action"] == "unsubscribe"
        assert "005930" not in ws_client._subscriptions

    @pytest.mark.asyncio
    async def test_resubscribe_all(self, ws_client):
        """모든 구독 재등록 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        ws_client._websocket = mock_ws
        ws_client._subscriptions.update(["005930", "000660"])

        await ws_client._resubscribe_all()

        assert mock_ws.send.call_count == 2

    @pytest.mark.asyncio
    async def test_disconnect(self, ws_client):
        """연결 종료 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        ws_client._websocket = mock_ws
        ws_client._listening = True

        await ws_client.disconnect()

        assert ws_client._listening is False
        mock_ws.close.assert_called_once()

    def test_on_price_update(self, ws_client):
        """콜백 등록 테스트"""
        def callback(update):
            pass

        ws_client.on_price_update(callback)

        assert callback in ws_client._callbacks
        assert len(ws_client._callbacks) == 1

    @pytest.mark.asyncio
    async def test_listen_once_with_message(self, ws_client):
        """단일 메시지 수신 테스트"""
        message = json.dumps({
            "ticker": "005930",
            "price": 80500,
            "change": 500,
            "change_percent": 0.62,
            "volume": 1000000,
            "timestamp": "2024-01-15T10:30:00",
        })

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=message)
        mock_ws.closed = False
        ws_client._websocket = mock_ws

        update = await ws_client.listen_once()

        assert update is not None
        assert update.ticker == "005930"
        assert update.price == 80500

    @pytest.mark.asyncio
    async def test_listen_once_timeout(self, ws_client):
        """수신 타임아웃 테스트"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_ws.closed = False
        ws_client._websocket = mock_ws

        update = await ws_client.listen_once(timeout=1.0)

        assert update is None

    @pytest.mark.asyncio
    async def test_listen_once_without_connection(self, ws_client):
        """연결 없이 수신 시도 테스트"""
        with pytest.raises(ConnectionError):
            await ws_client.listen_once()

    def test_is_connected(self, ws_client):
        """연결 상태 확인 테스트"""
        assert ws_client.is_connected is False

        mock_ws = Mock()
        mock_ws.closed = False
        ws_client._websocket = mock_ws

        assert ws_client.is_connected is True

    def test_subscriptions_property(self, ws_client):
        """구독 목록 속성 테스트"""
        ws_client._subscriptions.add("005930")
        ws_client._subscriptions.add("000660")

        subs = ws_client.subscriptions

        assert "005930" in subs
        assert "000660" in subs
        assert len(subs) == 2

        # 원본을 수정하지 않는지 확인
        subs.add("035720")
        assert "035720" not in ws_client._subscriptions


class TestWebSocketClientPool:
    """WebSocketClientPool 클래스 테스트"""

    @pytest.fixture
    def pool(self):
        return WebSocketClientPool()

    def test_init(self, pool):
        """풀 초기화 테스트"""
        assert len(pool._clients) == 0

    @pytest.mark.asyncio
    async def test_create_client(self, pool):
        """클라이언트 생성 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            client = await pool.create_client(
                name="test-client",
                uri="ws://localhost:5111/ws/price",
            )

            assert client is not None
            assert "test-client" in pool._clients

    @pytest.mark.asyncio
    async def test_get_client(self, pool):
        """클라이언트 조회 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            await pool.create_client(
                name="test-client",
                uri="ws://localhost:5111/ws/price",
            )

            client = pool.get_client("test-client")

            assert client is not None
            assert pool.get_client("non-existent") is None

    @pytest.mark.asyncio
    async def test_close_all(self, pool):
        """모든 클라이언트 종료 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            await pool.create_client("client1", "ws://localhost:5111/ws/price")
            await pool.create_client("client2", "ws://localhost:5111/ws/price")

            await pool.close_all()

            assert len(pool._clients) == 0

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Async context manager 테스트"""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            async with WebSocketClientPool() as pool:
                await pool.create_client("test", "ws://localhost:5111/ws/price")
                assert len(pool._clients) == 1

            # 컨텍스트 종료 후 모든 클라이언트가 종료되어야 함
            assert len(pool._clients) == 0


class TestSubscribeToTickers:
    """subscribe_to_tickers 유틸리티 함수 테스트"""

    @pytest.mark.asyncio
    async def test_subscribe_to_tickers(self):
        """여러 종목 구독 테스트"""
        callback = Mock()

        mock_ws = AsyncMock()
        mock_ws.closed = False

        # websockets.connect를 모킹
        async def mock_connect_func(*args, **kwargs):
            return mock_ws

        mock_connect = AsyncMock(side_effect=mock_connect_func)
        mock_connect_instance = Mock()
        mock_connect_instance.__aenter__.return_value = mock_ws

        with patch("websockets.connect", return_value=mock_connect_instance):
            client = await subscribe_to_tickers(
                uri="ws://localhost:5111/ws/price",
                tickers=["005930", "000660"],
                callback=callback,
            )

            assert client is not None
            assert len(client._subscriptions) == 2
            assert callback in client._callbacks

    @pytest.mark.asyncio
    async def test_subscribe_to_tickers_with_custom_reconnect(self):
        """사용자 정의 재연결 간격 테스트"""
        callback = Mock()

        mock_ws = AsyncMock()
        mock_ws.closed = False

        async def mock_connect_func(*args, **kwargs):
            return mock_ws

        mock_connect_instance = Mock()
        mock_connect_instance.__aenter__.return_value = mock_ws

        with patch("websockets.connect", return_value=mock_connect_instance):
            client = await subscribe_to_tickers(
                uri="ws://localhost:5111/ws/price",
                tickers=["005930"],
                callback=callback,
                reconnect_interval=10.0,
            )

            assert client.reconnect_interval == 10.0
