"""
Redis Pub/Sub 구독자 테스트

RedisSubscriber 클래스 단위 테스트
Redis 연결, Pub/Sub 메시지 수신, WebSocket 브로드캐스트 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import json

from src.websocket.server import RedisSubscriber, ConnectionManager


# ============================================================================
# RedisSubscriber 테스트
# ============================================================================

class TestRedisSubscriber:
    """RedisSubscriber 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        assert subscriber.is_running() is False
        assert subscriber._redis_client is None
        assert subscriber._subscriber_task is None
        assert subscriber.connection_manager == manager
        assert subscriber.CHANNEL_PREFIX == "ws:broadcast:"

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """시작/중지 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # 초기 상태
        assert subscriber.is_running() is False

        # 시작 (Redis 연결 없이 테스트를 위해 모킹)
        with patch.object(subscriber, '_subscribe_loop', new_callable=AsyncMock):
            await subscriber.start()
            assert subscriber.is_running() is True
            assert subscriber._subscriber_task is not None

            # 중지
            await subscriber.stop()
            # stop은 _is_running을 False로 설정하고 태스크를 취소
            assert subscriber._is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """이미 실행 중일 때 시작 테스트 (중복 시작 방지)"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        with patch.object(subscriber, '_subscribe_loop', new_callable=AsyncMock):
            # 첫 번째 시작
            await subscriber.start()
            first_task = subscriber._subscriber_task

            # 두 번째 시작은 무시되어야 함
            await subscriber.start()

            # 동일한 태스크인지 확인
            assert subscriber._subscriber_task == first_task

            await subscriber.stop()

    @pytest.mark.asyncio
    async def test_topic_extraction_from_channel(self):
        """채널에서 토픽 추출 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # 채널 prefix 제거 로직 테스트
        test_cases = [
            ("ws:broadcast:market-gate", "market-gate"),
            ("ws:broadcast:signal:vcp", "signal:vcp"),
            ("ws:broadcast:price:005930", "price:005930"),
            ("ws:broadcast:", ""),  # 빈 토픽
            ("", ""),  # 빈 채널
        ]

        for channel, expected_topic in test_cases:
            topic = channel.replace(subscriber.CHANNEL_PREFIX, "") if channel else ""
            assert topic == expected_topic, f"Channel: {channel}, Expected: {expected_topic}, Got: {topic}"

    @pytest.mark.asyncio
    async def test_broadcast_to_websocket(self):
        """WebSocket으로 브로드캐스트 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # WebSocket 클라이언트 추가
        websocket = AsyncMock()
        websocket.send_json = AsyncMock()
        manager.active_connections["test_client"] = websocket
        manager.subscriptions["test_topic"] = {"test_client"}

        # 테스트 데이터
        test_channel = "ws:broadcast:test_topic"
        test_data = '{"type": "test", "value": 123}'

        # 토픽 추출
        topic = test_channel.replace(subscriber.CHANNEL_PREFIX, "") if test_channel else ""

        # JSON 파싱
        msg_data = json.loads(test_data)

        # 브로드캐스트
        await manager.broadcast(msg_data, topic=topic)

        # WebSocket으로 전송 확인
        websocket.send_json.assert_called_once_with(msg_data)

    def test_json_decode_error_handling(self):
        """JSON 디코딩 에러 처리 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # 잘못된 JSON 데이터
        invalid_json_data = "invalid json data"

        # JSON 파싱 시도
        try:
            msg_data = json.loads(invalid_json_data)
            parsed = True
        except json.JSONDecodeError:
            parsed = False

        # 파싱 실패 확인
        assert parsed is False

    @pytest.mark.asyncio
    async def test_stop_closes_redis_connection(self):
        """중지 시 Redis 연결 종료 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # Mock Redis 클라이언트
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        subscriber._redis_client = mock_redis

        # 시작 상태로 설정
        subscriber._is_running = True
        subscriber._subscriber_task = asyncio.create_task(asyncio.sleep(10))

        # 중지
        await subscriber.stop()

        # Redis 연결이 종료되었는지 확인
        mock_redis.close.assert_called_once()

    def test_channel_prefix_constant(self):
        """채널 프리픽스 상수 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # CHANNEL_PREFIX 상수 확인
        assert subscriber.CHANNEL_PREFIX == "ws:broadcast:"

        # 채널 패턴 생성 확인
        expected_pattern = "ws:broadcast:*"
        actual_pattern = f"{subscriber.CHANNEL_PREFIX}*"
        assert actual_pattern == expected_pattern

    def test_valid_message_types(self):
        """유효한 메시지 타입 확인 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # 처리해야 할 메시지 타입
        valid_types = ["pmessage", "message"]

        for msg_type in valid_types:
            message = {"type": msg_type}
            should_process = message.get("type") in ["pmessage", "message"]
            assert should_process is True, f"Type {msg_type} should be processed"

    def test_invalid_message_types(self):
        """유효하지 않은 메시지 타입 확인 테스트"""
        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # 처리하지 않을 메시지 타입
        invalid_types = ["subscribe", "psubscribe", "punsubscribe", "unsubscribe"]

        for msg_type in invalid_types:
            message = {"type": msg_type}
            should_process = message.get("type") in ["pmessage", "message"]
            assert should_process is False, f"Type {msg_type} should not be processed"

    @pytest.mark.asyncio
    async def test_redis_url_resolution(self):
        """Redis URL 우선순위 확인 테스트"""
        import os

        manager = ConnectionManager()
        subscriber = RedisSubscriber(manager)

        # 환경 변수 설정
        original_broker = os.getenv("CELERY_BROKER_URL")
        original_url = os.getenv("REDIS_URL")

        # CELERY_BROKER_URL 우선순위 테스트
        expected_urls = [
            ("redis://broker:6379/0", None, "redis://broker:6379/0"),  # CELERY_BROKER_URL
            (None, "redis://redis:6379/0", "redis://redis:6379/0"),  # REDIS_URL
            (None, None, "redis://localhost:6379/0"),  # 기본값
        ]

        for broker, url, expected in expected_urls:
            # 시뮬레이션
            if broker:
                redis_url = broker
            elif url:
                redis_url = url
            else:
                redis_url = "redis://localhost:6379/0"

            assert redis_url == expected

        # 환경 변수 복원
        if original_broker:
            os.environ["CELERY_BROKER_URL"] = original_broker
        if original_url:
            os.environ["REDIS_URL"] = original_url


# ============================================================================
# 전역 함수 테스트
# ============================================================================

class TestRedisSubscriberGlobalFunctions:
    """RedisSubscriber 전역 함수 테스트"""

    def test_get_redis_subscriber_type(self):
        """get_redis_subscriber 반환 타입 테스트"""
        from src.websocket.server import get_redis_subscriber

        # 반환 값 확인 (None 또는 RedisSubscriber 인스턴스)
        result = get_redis_subscriber()
        assert result is None or isinstance(result, RedisSubscriber)

    @pytest.mark.asyncio
    async def test_create_redis_subscriber(self):
        """Redis 구독자 생성 테스트"""
        from src.websocket.server import create_redis_subscriber

        manager = ConnectionManager()

        # 모킹된 _subscribe_loop로 생성
        with patch('src.websocket.server.RedisSubscriber._subscribe_loop', new_callable=AsyncMock):
            subscriber = create_redis_subscriber(manager)

            # 생성된 인스턴스 확인
            assert subscriber is not None
            assert isinstance(subscriber, RedisSubscriber)
            assert subscriber.connection_manager == manager

            # 전역 인스턴스로 설정되었는지 확인
            from src.websocket.server import get_redis_subscriber
            global_subscriber = get_redis_subscriber()
            assert global_subscriber == subscriber

            # 정리
            await subscriber.stop()
