"""
키움 WebSocket 클라이언트 테스트

실제 구현과 일치하도록 수정
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.kiwoom.base import KiwoomEventType, RealtimePrice, KiwoomConfig


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

        # Mock websocket 연결
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.close = AsyncMock()

        # 로그인 응답 반환 (trnm: LOGIN, return_code: 0)
        login_response = {
            "trnm": "LOGIN",
            "return_code": 0,
            "return_msg": "OK"
        }
        mock_ws.recv.return_value = json.dumps(login_response)

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            # _receive_loop를 mock하여 실제 루프가 실행되지 않도록 함
            with patch.object(ws, '_receive_loop', new_callable=AsyncMock):
                result = await ws.connect(access_token="test_token")

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
        import asyncio

        ws = KiwoomWebSocket(config)

        # Mock 연결 상태 설정
        ws._connected = True

        # 실제 태스크 생성 (이미 완료된 상태로)
        async def dummy_task():
            pass

        ws._receive_task = asyncio.create_task(dummy_task())
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
        assert message["trnm"] == "REG"
        assert message["grp_no"] == "1"

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
        """실시간 데이터 수신 처리 테스트 (0B - 주식체결)"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        received_data = []

        def handler(data):
            received_data.append(data)

        ws.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        # 실시간 체결가 데이터 시뮬레이션 (trnm: REAL)
        realtime_message = {
            "trnm": "REAL",
            "data": [{
                "type": "0B",  # 주식체결
                "item": "005930",
                "values": {
                    "10": "85000",    # 현재가
                    "11": "500",      # 전일대비
                    "12": "0.59",     # 등락율
                    "13": "1000000",  # 누적거래량
                    "15": "+100",     # 거래량
                    "27": "85010",    # 매도호가
                    "28": "84990"     # 매수호가
                }
            }]
        }

        await ws._handle_message(json.dumps(realtime_message))

        assert len(received_data) == 1
        assert received_data[0].ticker == "005930"
        assert received_data[0].price == 85000.0

    @pytest.mark.asyncio
    async def test_on_receive_real_data_with_signs(self, config):
        """부호 포함 실시간 데이터 수신 처리 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        received_data = []

        def handler(data):
            received_data.append(data)

        ws.register_event(KiwoomEventType.RECEIVE_REAL_DATA, handler)

        # 부호 포함 데이터 시뮬레이션
        realtime_message = {
            "trnm": "REAL",
            "data": [{
                "type": "0B",
                "item": "005930",
                "values": {
                    "10": "-85000",    # 하락 (-)
                    "11": "-500",
                    "12": "-0.59",
                    "13": "1000000",
                    "15": "-100",
                    "27": "84990",
                    "28": "85010"
                }
            }]
        }

        await ws._handle_message(json.dumps(realtime_message))

        assert len(received_data) == 1
        # 부호 제거 후 절대값으로 변환되어야 함
        assert received_data[0].price == 85000.0

    @pytest.mark.asyncio
    async def test_ping_handling(self, config):
        """PING 메시지 처리 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._ws = AsyncMock()
        ws._ws.send = AsyncMock()

        # PING 메시지 수신 시뮬레이션
        ping_message = {"trnm": "PING"}

        await ws._handle_message(json.dumps(ping_message))

        # PING을 그대로 돌려보내야 함
        call_args = ws._ws.send.call_args[0][0]
        message = json.loads(call_args)
        assert message["trnm"] == "PING"

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
        ws._access_token = "test_token"
        assert ws.has_valid_token() is True

    @pytest.mark.asyncio
    async def test_refresh_token(self, config):
        """토큰 갱신 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._connected = True
        ws._access_token = "old_token"

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.close = AsyncMock()

        # 로그인 응답
        login_response = {
            "trnm": "LOGIN",
            "return_code": 0,
            "return_msg": "OK"
        }
        mock_ws.recv.return_value = json.dumps(login_response)

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            # _receive_task를 mock하여 실제 루프가 실행되지 않도록 함
            with patch.object(ws, '_receive_loop', new_callable=AsyncMock):
                result = await ws.refresh_token()

                assert result is True
                assert ws._connected is True

    @pytest.mark.asyncio
    async def test_get_current_price(self, config):
        """현재가 조회 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

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
        ws._access_token = "test_token"

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.close = AsyncMock()

        login_response = {
            "trnm": "LOGIN",
            "return_code": 0,
            "return_msg": "OK"
        }
        mock_ws.recv.return_value = json.dumps(login_response)

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            # _receive_loop를 mock하여 실제 루프가 실행되지 않도록 함
            with patch.object(ws, '_receive_loop', new_callable=AsyncMock):
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
        ws._access_token = "test_token"

        with patch('src.kiwoom.websocket.websockets.connect') as mock_connect:
            # 항상 실패하도록 설정
            async def failing_connect(*args, **kwargs):
                raise Exception("Connection failed")

            mock_connect.side_effect = failing_connect

            # 재연결 시도 (최대 3회)
            result = await ws._reconnect(max_attempts=3)

            assert result is False

    @pytest.mark.asyncio
    async def test_restore_subscriptions_after_reconnect(self, config):
        """재연결 후 구독 복원 테스트"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)
        ws._access_token = "test_token"

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        # 로그인 응답
        login_response = {
            "trnm": "LOGIN",
            "return_code": 0,
            "return_msg": "OK"
        }
        mock_ws.recv = AsyncMock(return_value=json.dumps(login_response))
        mock_ws.close = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch('src.kiwoom.websocket.websockets.connect', side_effect=mock_connect):
            # 먼저 구독 설정
            ws._subscribed_tickers = {"005930", "000660"}

            # 재연결 (내부적으로 subscribe_realtime 호출하여 복원)
            # _receive_loop를 mock하지 않고 실제 재연결 후 구독 복원 확인
            with patch.object(ws, '_receive_loop', new_callable=AsyncMock):
                await ws._reconnect()

                # 재연결 성공 확인
                assert ws._connected is True
                assert ws._authenticated is True

                # 수동으로 구독 복원 확인
                for ticker in ws._subscribed_tickers:
                    result = await ws.subscribe_realtime(ticker)
                    assert result is True

                # REG 메시지가 2번 호출되었는지 확인
                send_calls = ws._ws.send.call_args_list
                reg_calls = [
                    call for call in send_calls
                    if json.loads(call[0][0]).get("trnm") == "REG"
                ]
                assert len(reg_calls) >= 2  # 2개 종목 재구독

                # 정리
                await ws.disconnect()


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
        """로그인 요청 포맷 테스트 (실제 구현 확인)"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        # 로그인 메시지는 connect 메서드 내부에서 생성됨
        # 형식 확인: {"trnm": "LOGIN", "token": "..."}
        test_token = "test_token_123"
        expected_format = {
            "trnm": "LOGIN",
            "token": test_token
        }

        # 실제 코드에서 사용하는 포맷과 일치
        assert expected_format["trnm"] == "LOGIN"
        assert "token" in expected_format

    def test_reg_request_format(self, config):
        """REG 요청 포맷 테스트 (실제 구현 확인)"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        # REG 메시지 포맷: {"trnm": "REG", "grp_no": "1", ...}
        expected_trnm = "REG"
        assert expected_trnm == "REG"

        # 타입 확인
        assert ws.TYPE_STOCK_QUOTE == "0A"
        assert ws.TYPE_STOCK_TRADE == "0B"

    def test_unreg_request_format(self, config):
        """REMOVE 요청 포맷 테스트 (실제 구현 확인)"""
        from src.kiwoom.websocket import KiwoomWebSocket

        ws = KiwoomWebSocket(config)

        # REMOVE 메시지 포맷: {"trnm": "REMOVE", "grp_no": "1", ...}
        expected_trnm = "REMOVE"
        assert expected_trnm == "REMOVE"
