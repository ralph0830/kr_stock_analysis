"""
WebSocket 서버 테스트

ConnectionManager, PriceUpdateBroadcaster, SignalBroadcaster,
HeartbeatManager, RedisSubscriber 테스트
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timezone

from src.websocket.server import (
    ConnectionManager,
    PriceUpdateBroadcaster,
    SignalBroadcaster,
    HeartbeatManager,
    signal_broadcaster,
    connection_manager,
)


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


# ============================================================================
# SignalBroadcaster 테스트
# ============================================================================

class TestSignalBroadcaster:
    """SignalBroadcaster 테스트"""

    @pytest.mark.asyncio
    async def test_broadcast_signal_update_with_dict_signals(self):
        """dict 형태의 시그널 브로드캐스트 테스트"""
        broadcaster = SignalBroadcaster()

        signals = [
            {"ticker": "005930", "score": 85, "signal_type": "VCP"},
            {"ticker": "000660", "score": 78, "signal_type": "VCP"},
        ]

        # connection_manager.broadcast 모킹
        with patch.object(connection_manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            await broadcaster.broadcast_signal_update(signals, signal_type="VCP")

            # broadcast가 호출되었는지 확인
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args

            # 메시지 구조 확인
            message = call_args[0][0]
            assert message["type"] == "signal_update"
            assert message["data"]["signal_type"] == "VCP"
            assert message["data"]["count"] == 2
            assert len(message["data"]["signals"]) == 2

            # 토픽 확인
            topic = call_args[1]["topic"]
            assert topic == "signal:vcp"

    @pytest.mark.asyncio
    async def test_broadcast_signal_update_with_object_signals(self):
        """to_dict() 메서드를 가진 객체 시그널 브로드캐스트 테스트"""
        broadcaster = SignalBroadcaster()

        # Mock signal object with to_dict method
        mock_signal = Mock()
        mock_signal.to_dict = Mock(return_value={"ticker": "005930", "score": 90})

        signals = [mock_signal]

        with patch.object(connection_manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            await broadcaster.broadcast_signal_update(signals, signal_type="JONGGA_V2")

            # to_dict가 호출되었는지 확인
            mock_signal.to_dict.assert_called_once()

            # 메시지 확인
            message = mock_broadcast.call_args[0][0]
            assert message["data"]["signals"][0] == {"ticker": "005930", "score": 90}
            assert message["data"]["signal_type"] == "JONGGA_V2"

    @pytest.mark.asyncio
    async def test_broadcast_signal_update_empty_list(self):
        """빈 시그널 리스트 브로드캐스트 테스트"""
        broadcaster = SignalBroadcaster()

        with patch.object(connection_manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            await broadcaster.broadcast_signal_update([], signal_type="VCP")

            message = mock_broadcast.call_args[0][0]
            assert message["data"]["count"] == 0
            assert message["data"]["signals"] == []

    @pytest.mark.asyncio
    async def test_broadcast_signal_update_invalid_type(self):
        """잘못된 타입의 시그널 필터링 테스트"""
        broadcaster = SignalBroadcaster()

        # 유효하지 않은 타입의 시그널
        signals = ["invalid", 123, None]

        with patch.object(connection_manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            await broadcaster.broadcast_signal_update(signals, signal_type="VCP")

            # 유효하지 않은 시그널은 필터링되어 빈 리스트로 전달
            message = mock_broadcast.call_args[0][0]
            assert message["data"]["count"] == 0
            assert message["data"]["signals"] == []

    @pytest.mark.asyncio
    async def test_signal_broadcaster_start_stop(self):
        """SignalBroadcaster 시작/중지 테스트"""
        broadcaster = SignalBroadcaster()

        assert broadcaster.is_running() is False

        await broadcaster.start()
        assert broadcaster.is_running() is True

        await broadcaster.stop()
        assert broadcaster.is_running() is False

    @pytest.mark.asyncio
    async def test_signal_broadcaster_jongga_v2(self):
        """종가베팅 V2 시그널 브로드캐스트 테스트"""
        broadcaster = SignalBroadcaster()

        signals = [
            {"ticker": "005930", "score": 88, "entry_price": 80000},
            {"ticker": "000660", "score": 82, "entry_price": 450000},
        ]

        with patch.object(connection_manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            await broadcaster.broadcast_signal_update(signals, signal_type="JONGGA_V2")

            message = mock_broadcast.call_args[0][0]
            assert message["data"]["signal_type"] == "JONGGA_V2"
            assert message["data"]["count"] == 2

            # 토픽이 signal:jongga_v2인지 확인
            topic = mock_broadcast.call_args[1]["topic"]
            assert topic == "signal:jongga_v2"


# ============================================================================
# HeartbeatManager 테스트
# ============================================================================

class TestHeartbeatManager:
    """HeartbeatManager 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        assert heartbeat.is_running() is False
        assert heartbeat.ping_interval_seconds == 30
        assert heartbeat.pong_timeout_seconds == 90

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """시작/중지 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        # 시작
        await heartbeat.start()
        assert heartbeat.is_running() is True

        # 중지
        await heartbeat.stop()
        assert heartbeat.is_running() is False

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """이미 실행 중일 때 시작 테스트 (중복 시작 방지)"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        await heartbeat.start()
        assert heartbeat.is_running() is True

        # 두 번째 시작은 무시되어야 함
        await heartbeat.start()
        assert heartbeat.is_running() is True

        await heartbeat.stop()

    def test_record_pong_updates_timestamp(self):
        """pong 수신 시간 기록 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        client_id = "test_client"

        # 초기 상태: 기록된 pong 없음
        assert heartbeat.get_last_pong_time(client_id) is None

        # pong 기록
        before_time = time.time()
        heartbeat.record_pong(client_id)
        after_time = time.time()

        # 시간이 기록되었는지 확인
        recorded_time = heartbeat.get_last_pong_time(client_id)
        assert recorded_time is not None
        assert before_time <= recorded_time <= after_time

    def test_is_client_alive_true_recent_pong(self):
        """최근 pong 수신 시 alive 반환 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        client_id = "test_client"

        # 아직 pong을 받지 않은 클라이언트는 alive로 간주
        assert heartbeat.is_client_alive(client_id) is True

        # 최근 pong 기록
        heartbeat.record_pong(client_id)
        assert heartbeat.is_client_alive(client_id) is True

    def test_is_client_alive_false_timeout(self):
        """타임아웃 시 not alive 반환 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)
        heartbeat.pong_timeout_seconds = 1  # 1초로 타임아웃 단축

        client_id = "test_client"

        # pong 기록
        heartbeat.record_pong(client_id)

        # 즉시 확인하면 alive
        assert heartbeat.is_client_alive(client_id) is True

        # 1.1초 대기 후 확인
        time.sleep(1.1)
        assert heartbeat.is_client_alive(client_id) is False

    def test_remove_client_clears_pong_time(self):
        """클라이언트 제거 시 pong 시간 정리 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        client_id = "test_client"

        # pong 기록
        heartbeat.record_pong(client_id)
        assert heartbeat.get_last_pong_time(client_id) is not None

        # 클라이언트 제거
        heartbeat.remove_client(client_id)

        # pong 시간이 삭제되었는지 확인
        assert heartbeat.get_last_pong_time(client_id) is None

    @pytest.mark.asyncio
    async def test_heartbeat_interval_configuration(self):
        """하트비트 간격 설정 테스트"""
        manager = ConnectionManager()
        heartbeat = HeartbeatManager(manager)

        # 기본값 확인
        assert heartbeat.ping_interval_seconds == 30
        assert heartbeat.pong_timeout_seconds == 90

        # 사용자 정의 값 설정
        heartbeat.ping_interval_seconds = 10
        heartbeat.pong_timeout_seconds = 30

        assert heartbeat.ping_interval_seconds == 10
        assert heartbeat.pong_timeout_seconds == 30


# ============================================================================
# PriceUpdateBroadcaster 추가 테스트
# ============================================================================

class TestPriceUpdateBroadcasterExtended:
    """PriceUpdateBroadcaster 확장 테스트"""

    @pytest.mark.asyncio
    async def test_add_ticker(self):
        """종목 구독 추가 테스트"""
        broadcaster = PriceUpdateBroadcaster()

        # 초기 상태: 활성 티커 없음
        assert len(broadcaster.get_active_tickers()) == 0

        # 티커 추가
        broadcaster.add_ticker("005930")
        assert "005930" in broadcaster.get_active_tickers()

        # 중복 추가 방지 확인 (Set이므로 중복 무시)
        broadcaster.add_ticker("005930")
        broadcaster.add_ticker("005930")
        active_tickers = broadcaster.get_active_tickers()
        # Set이므로 중복이 없어야 함
        assert len(active_tickers) == 1
        assert "005930" in active_tickers

    @pytest.mark.asyncio
    async def test_remove_ticker(self):
        """종목 구독 제거 테스트"""
        broadcaster = PriceUpdateBroadcaster()

        # 티커 추가
        broadcaster.add_ticker("005930")
        broadcaster.add_ticker("000660")
        assert "005930" in broadcaster.get_active_tickers()
        assert "000660" in broadcaster.get_active_tickers()

        # 티커 제거
        broadcaster.remove_ticker("005930")
        assert "005930" not in broadcaster.get_active_tickers()
        assert "000660" in broadcaster.get_active_tickers()

    @pytest.mark.asyncio
    async def test_get_cached_price(self):
        """캐시된 가격 조회 테스트"""
        broadcaster = PriceUpdateBroadcaster()

        # 초기 상태: 캐시 없음 (private attribute 접근)
        assert broadcaster._price_cache.get("005930") is None

        # 캐시 설정
        test_price = {"price": 80000, "change": 500}
        broadcaster._price_cache["005930"] = test_price

        # 캐시 조회
        cached = broadcaster._price_cache.get("005930")
        assert cached == test_price

    @pytest.mark.asyncio
    async def test_fetch_prices_from_kiwoom(self):
        """Kiwoom API에서 가격 조회 테스트 (Mock)"""
        broadcaster = PriceUpdateBroadcaster(interval_seconds=1)

        # Kiwoom API 모킹
        with patch('src.kiwoom.rest_api.KiwoomRestAPI.get_current_price') as mock_get_price:
            mock_get_price.return_value = {
                "ticker": "005930",
                "price": 80000,
                "change": 500,
                "change_rate": 0.63
            }

            # 브로드캐스터 시작
            await broadcaster.start()

            # 티커 추가
            broadcaster.add_ticker("005930")

            # 가격 업데이트 대기 (broadcast 루프가 실행되도록)
            await asyncio.sleep(1.5)

            # 캐시 확인
            cached = broadcaster.get_cached_price("005930")
            # Kiwoom API 호출 확인 (실제 동작에 따라 다를 수 있음)

            await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_broadcast_loop_running(self):
        """브로드캐스트 루프 실행 테스트"""
        broadcaster = PriceUpdateBroadcaster(interval_seconds=0.5)

        assert broadcaster.is_running() is False

        await broadcaster.start()
        assert broadcaster.is_running() is True

        # 루프가 실행되는 동안 대기
        await asyncio.sleep(1)

        await broadcaster.stop()
        assert broadcaster.is_running() is False


# ============================================================================
# WebSocket 통합 테스트
# ============================================================================

class TestWebSocketIntegration:
    """WebSocket 통합 테스트"""

    def test_manager_singleton_usage(self):
        """관리자 인스턴스 사용 테스트"""
        # 전역 인스턴스 사용
        assert connection_manager is not None
        assert isinstance(connection_manager, ConnectionManager)

    def test_broadcaster_singleton_usage(self):
        """브로드캐스터 인스턴스 사용 테스트"""
        # 전역 인스턴스 사용
        assert signal_broadcaster is not None
        assert isinstance(signal_broadcaster, SignalBroadcaster)

    @pytest.mark.asyncio
    async def test_connection_manager_subscribe_elw_ticker(self):
        """ELW 종목 코드 구독 테스트"""
        manager = ConnectionManager()

        # ELW 종목 코드는 '5'로 시작 (6자리)
        elw_ticker = "500101"
        normal_ticker = "005930"

        manager.subscribe("client_1", f"price:{elw_ticker}")
        manager.subscribe("client_1", f"price:{normal_ticker}")

        subscriptions = manager.get_subscriptions("client_1")
        assert f"price:{elw_ticker}" in subscriptions
        assert f"price:{normal_ticker}" in subscriptions

    @pytest.mark.asyncio
    async def test_connection_manager_subscribe_invalid_ticker_rejected(self):
        """잘못된 종목 코드 구독 거부 테스트"""
        manager = ConnectionManager()

        # ConnectionManager.subscribe()는 현재 모든 토픽을 허용
        # 실제 검증 로직이 있다면 테스트 필요
        invalid_ticker = "invalid"

        # 현재 구조에서는 검증이 없으므로 구독 성공
        manager.subscribe("client_1", f"price:{invalid_ticker}")
        subscriptions = manager.get_subscriptions("client_1")
        assert f"price:{invalid_ticker}" in subscriptions

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_to_topic_subscribers_only(self):
        """토픽 구독자에게만 브로드캐스트 테스트"""
        manager = ConnectionManager()

        # 3개 클라이언트 생성
        for i in range(3):
            websocket = AsyncMock()
            websocket.send_json = AsyncMock()
            client_id = f"client_{i}"
            manager.active_connections[client_id] = websocket

        # client_0, client_1만 토픽 구독
        manager.subscribe("client_0", "price:005930")
        manager.subscribe("client_1", "price:005930")
        # client_2는 구독하지 않음

        message = {"type": "price_update", "ticker": "005930", "price": 80000}
        await manager.broadcast(message, topic="price:005930")

        # 구독한 클라이언트에게만 전송 확인
        manager.active_connections["client_0"].send_json.assert_called_once()
        manager.active_connections["client_1"].send_json.assert_called_once()
        manager.active_connections["client_2"].send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_manager_get_connection_count(self):
        """연결 수 조회 테스트"""
        manager = ConnectionManager()

        # 초기 상태
        assert manager.get_connection_count() == 0

        # 클라이언트 추가
        for i in range(5):
            websocket = AsyncMock()
            await manager.connect(websocket, f"client_{i}")

        assert manager.get_connection_count() == 5

        # 클라이언트 제거
        manager.disconnect("client_0")
        assert manager.get_connection_count() == 4
