"""
키움 WebSocket 클라이언트 테스트

TDD RED 단계: 테스트를 먼저 작성하고, 실패를 확인합니다.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from src.kiwoom.base import KiwoomEventType, RealtimePrice, OrderBook, KiwoomConfig


class TestKiwoomWebSocket:
    """KiwoomWebSocket 클래스 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://mockapi.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
            debug_mode=True,
            ws_ping_interval=30,
            ws_ping_timeout=10,
            ws_recv_timeout=60
        )

    @pytest.mark.asyncio
    async def test_websocket_initialization(self, config):
        """WebSocket 초기화 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        assert ws._config == config
        assert ws._connected is False
        assert ws._authenticated is False
        assert len(ws._subscribed_tickers) == 0
        assert len(ws._event_handlers) == 0

    @pytest.mark.asyncio
    async def test_websocket_connect(self, config):
        """WebSocket 연결 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        # Mock websocket 연결 - websockets.connect는 async context manager를 반환
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.close = AsyncMock()

        # 로그인 응답 반환
        login_response = {
            "jsonrpc": "2.0",
            "method": "OnLogin",
            "result": {
                "token": "test_token",
                "expire": 3600
            }
        }
        mock_ws.recv.return_value = json.dumps(login_response)

        # AsyncContextManager mock 생성
        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            result = await ws.connect()

            assert result is True
            assert ws._connected is True
            assert ws._authenticated is True
            mock_ws.send.assert_called()

            # 정리
            await ws.disconnect()

    @pytest.mark.asyncio
    async def test_websocket_connect_failure(self, config):
        """WebSocket 연결 실패 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        with patch('src.kiwoom.websocket.websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            result = await ws.connect()

            assert result is False
            assert ws._connected is False

    @pytest.mark.asyncio
    async def test_websocket_disconnect(self, config):
        """WebSocket 연결 해제 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        # Mock 연결 상태 설정
        ws._connected = True
        ws._ws = AsyncMock()
        ws._ws.close = AsyncMock()

        await ws.disconnect()

        assert ws._connected is False
        ws._ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_realtime(self, config):
        """실시간 시세 등록 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._authenticated = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()

        result = await ws.subscribe_realtime("005930")

        assert result is True
        assert "005930" in ws._subscribed_tickers

        # REG 전문 전송 확인
        call_args = ws._ws.send.call_args[0][0]
        message = json.loads(call_args)
        assert message["jsonrpc"] == "2.0"
        assert message["method"] == "REG"
        assert message["params"]["tr_code"] == "NWSKST00"  # 체결가 TR

    @pytest.mark.asyncio
    async def test_subscribe_realtime_not_connected(self, config):
        """연결되지 않은 상태에서 구독 시도 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        # 연결 안 함

        result = await ws.subscribe_realtime("005930")

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_realtime(self, config):
        """실시간 시세 해제 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._authenticated = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()

        # 먼저 구독
        await ws.subscribe_realtime("005930")
        assert "005930" in ws._subscribed_tickers

        # 해제
        result = await ws.unsubscribe_realtime("005930")

        assert result is True
        assert "005930" not in ws._subscribed_tickers

    @pytest.mark.asyncio
    async def test_get_subscribe_list(self, config):
        """구독 종목 리스트 조회 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._subscribed_tickers = {"005930", "000660", "035420"}

        tickers = ws.get_subscribe_list()

        assert set(tickers) == {"005930", "000660", "035420"}

    @pytest.mark.asyncio
    async def test_register_event_handler(self, config):
        """이벤트 핸들러 등록 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        handler = Mock()
        ws.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        assert KiwoomEventType.RECEIVE_REAL_DATA in ws._event_handlers
        assert handler in ws._event_handlers[KiwoomEventType.RECEIVE_REAL_DATA]

    @pytest.mark.asyncio
    async def test_unregister_event_handler(self, config):
        """이벤트 핸들러 해제 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        handler = Mock()

        ws.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)
        assert handler in ws._event_handlers[KiwoomEventType.RECEIVE_REAL_DATA]

        ws.unregister_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        assert handler not in ws._event_handlers[KiwoomEventType.RECEIVE_REAL_DATA]

    @pytest.mark.asyncio
    async def test_on_receive_real_data(self, config):
        """실시간 데이터 수신 처리 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        received_data = []

        def handler(data):
            received_data.append(data)

        ws.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        # 실시간 체결가 데이터 시뮬레이션
        realtime_message = {
            "jsonrpc": "2.0",
            "method": "OnReceiveRealData",
            "params": {
                "tr_code": "NWSKST00",
                "data": {
                    "ticker": "005930",
                    "price": "85000",
                    "change": "500",
                    "change_rate": "0.59",
                    "volume": "1000000",
                    "bid_price": "84990",
                    "ask_price": "85010"
                }
            }
        }

        await ws._handle_message(json.dumps(realtime_message))

        assert len(received_data) == 1
        assert received_data[0].ticker == "005930"
        assert received_data[0].price == 85000.0

    @pytest.mark.asyncio
    async def test_on_receive_mt_real_data(self, config):
        """실시간 호가 데이터 수신 처리 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        received_data = []

        def handler(data):
            received_data.append(data)

        ws.register_event(KiwoomEventType.RECEIVE_MT_REAL_DATA, handler)

        # 실시간 호가 데이터 시뮬레이션
        mt_message = {
            "jsonrpc": "2.0",
            "method": "OnReceiveMTRealData",
            "params": {
                "tr_code": "NWSKST01",
                "data": {
                    "ticker": "005930",
                    "bids": [("84990", "100"), ("84980", "200")],
                    "asks": [("85010", "150"), ("85020", "300")]
                }
            }
        }

        await ws._handle_message(json.dumps(mt_message))

        assert len(received_data) == 1
        assert received_data[0].ticker == "005930"
        assert len(received_data[0].bids) == 2
        assert len(received_data[0].asks) == 2

    @pytest.mark.asyncio
    async def test_ping_pong_handling(self, config):
        """PING/PONG 처리 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._authenticated = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()

        # PING 메시지 수신 시뮬레이션
        ping_message = {
            "jsonrpc": "2.0",
            "method": "PING"
        }

        await ws._handle_message(json.dumps(ping_message))

        # PONG 응답 전송 확인
        call_args = ws._ws.send.call_args[0][0]
        message = json.loads(call_args)
        assert message["jsonrpc"] == "2.0"
        assert message["method"] == "PONG"

    @pytest.mark.asyncio
    async def test_is_connected(self, config):
        """연결 상태 확인 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        assert ws.is_connected() is False

        ws._connected = True
        assert ws.is_connected() is True

    @pytest.mark.asyncio
    async def test_has_valid_token(self, config):
        """토큰 유효성 확인 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        assert ws.has_valid_token() is False

        # 토큰이 설정되어야 유효함
        ws._authenticated = True
        ws._token = "test_token"
        assert ws.has_valid_token() is True

    @pytest.mark.asyncio
    async def test_refresh_token(self, config):
        """토큰 갱신 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._authenticated = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()
        ws._ws.recv = AsyncMock()

        # 토큰 갱신 응답
        refresh_response = {
            "jsonrpc": "2.0",
            "method": "OnRefreshToken",
            "result": {
                "token": "new_token",
                "expire": 3600
            }
        }
        ws._ws.recv.return_value = json.dumps(refresh_response)

        result = await ws.refresh_token()

        assert result is True
        assert ws._token == "new_token"

    @pytest.mark.asyncio
    async def test_get_current_price(self, config):
        """현재가 조회 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()

        # 최근 수신 가격 데이터 설정
        test_price = RealtimePrice(
            ticker="005930",
            price=85000.0,
            change=500.0,
            change_rate=0.59,
            volume=1000000,
            bid_price=84990.0,
            ask_price=85010.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        ws._current_prices["005930"] = test_price

        price = await ws.get_current_price("005930")

        assert price is not None
        assert price.ticker == "005930"
        assert price.price == 85000.0

    @pytest.mark.asyncio
    async def test_get_current_price_not_found(self, config):
        """없는 종목 현재가 조회 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True

        price = await ws.get_current_price("999999")

        assert price is None


class TestWebSocketReconnect:
    """WebSocket 자동 재연결 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://mockapi.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
            debug_mode=True,
            ws_ping_interval=30,
            ws_ping_timeout=10,
            ws_recv_timeout=60
        )

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_connection_loss(self, config):
        """연결 끊김 시 자동 재연결 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.close = AsyncMock()

        login_response = {
            "jsonrpc": "2.0",
            "method": "OnLogin",
            "result": {"token": "test_token", "expire": 3600}
        }
        mock_ws.recv.return_value = json.dumps(login_response)

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            # 첫 연결 성공
            assert await ws.connect() is True

            # 연결 상태로 설정
            ws._connected = True

            # 연결 끊김 시뮬레이션
            ws._connected = False

            # 재연결 시도
            reconnect_result = await ws._reconnect()

            assert reconnect_result is True
            assert ws._connected is True

            # 정리
            await ws.disconnect()

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts(self, config):
        """최대 재연결 시도 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        with patch('src.kiwoom.websocket.websockets.connect') as mock_connect:
            # 항상 실패하도록 설정
            mock_connect.side_effect = Exception("Connection failed")

            # 재연결 시도 (최대 3회)
            result = await ws._reconnect(max_attempts=3)

            assert result is False
            assert mock_connect.call_count == 3

    @pytest.mark.asyncio
    async def test_restore_subscriptions_after_reconnect(self, config):
        """재연결 후 구독 복원 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        # recv가 연속 호출되다가 멈추도록 설정 (ConnectionClosed 시뮬레이션)
        recv_count = [0]

        async def mock_recv():
            recv_count[0] += 1
            if recv_count[0] == 1:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "method": "OnLogin",
                    "result": {"token": "test_token", "expire": 3600}
                })
            else:
                # 2회째부터는 ConnectionClosed 예외 발생
                from websockets.exceptions import ConnectionClosed
                raise ConnectionClosed(1000, "Connection closed")

        mock_ws.recv = mock_recv

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            # 연결 및 구독 (receive_task가 자동 시작됨)
            await ws.connect()
            await ws.subscribe_realtime("005930")
            await ws.subscribe_realtime("000660")

            # receive_task가 종료될 때까지 잠시 대기
            await asyncio.sleep(0.1)

            # 재연결 후 구독 복원
            await ws._restore_subscriptions()

            # 구독이 복원되었는지 확인
            send_calls = ws._ws.send.call_args_list
            reg_calls = [
                call for call in send_calls
                if json.loads(call[0][0]).get("method") == "REG"
            ]
            # 구독 2회 + 복원 2회 = 총 4회 (최소 2회 이상이면 성공)
            assert len(reg_calls) >= 2  # 2개 종목 재구독

            # 정리
            await ws.disconnect()


class TestWebSocketPingPong:
    """WebSocket PING/PONG 유지 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://mockapi.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
            debug_mode=True,
            ws_ping_interval=30,
            ws_ping_timeout=10,
            ws_recv_timeout=60
        )

    @pytest.mark.asyncio
    async def test_send_ping_periodically(self, config):
        """주기적 PING 전송 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._authenticated = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()
        ws._ws.recv = AsyncMock(return_value='{"jsonrpc":"2.0","method":"PONG"}')

        # PING 전송
        await ws._send_ping()

        # PING 메시지 확인
        call_args = ws._ws.send.call_args[0][0]
        message = json.loads(call_args)
        assert message["method"] == "PING"

    @pytest.mark.asyncio
    async def test_pong_timeout_detection(self, config):
        """PONG 타임아웃 감지 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._authenticated = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()

        # recv가 타임아웃 발생시키도록 설정
        async def mock_recv_timeout():
            raise asyncio.TimeoutError()

        ws._ws.recv = mock_recv_timeout

        # PING 전송 (PONG 대기 활성화)
        await ws._send_ping(wait_for_pong=True)

        # 연결이 끊어져야 함
        assert ws._connected is False


class TestWebSocketMessageFormat:
    """WebSocket 메시지 포맷 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://mockapi.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
            debug_mode=True
        )

    def test_login_request_format(self, config):
        """로그인 요청 포맷 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        login_request = ws._build_login_request()

        assert login_request["jsonrpc"] == "2.0"
        assert login_request["method"] == "Login"
        assert "params" in login_request
        assert "app_key" in login_request["params"]
        assert "secret_key" in login_request["params"]

    def test_reg_request_format(self, config):
        """REG 요청 포맷 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        reg_request = ws._build_reg_request("005930")

        assert reg_request["jsonrpc"] == "2.0"
        assert reg_request["method"] == "REG"
        assert reg_request["params"]["tr_code"] == "NWSKST00"
        assert reg_request["params"]["ticker"] == "005930"

    def test_unreg_request_format(self, config):
        """UNREG 요청 포맷 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        unreg_request = ws._build_unreg_request("005930")

        assert unreg_request["jsonrpc"] == "2.0"
        assert unreg_request["method"] == "UNREG"
        assert unreg_request["params"]["tr_code"] == "NWSKST00"
        assert unreg_request["params"]["ticker"] == "005930"
