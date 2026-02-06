"""
WebSocket 재시도 로직 테스트 (TDD - Red Phase)

이 테스트 파일은 KiwoomWebSocket의 재시도 로직을 검증합니다.
TDD 방식으로 작성되었으며, 먼저 실패하는 테스트를 작성합니다.

테스트 커버리지:
1. 지수 백오프 (Exponential Backoff)
2. 최대 재시도 횟수 제한
3. 로그 레벨 조정
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# 테스트 대상 모듈 임포트
from src.kiwoom.websocket import KiwoomWebSocket
from src.kiwoom.base import KiwoomConfig


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """테스트용 KiwoomConfig fixture"""
    return KiwoomConfig(
        app_key="test_app_key",
        secret_key="test_secret_key",
        base_url="https://test.kiwoom.com",
        ws_url="wss://test.kiwoom.com:10000/api/dostk/websocket",
    )


@pytest.fixture
def websocket_client(mock_config):
    """테스트용 KiwoomWebSocket fixture"""
    client = KiwoomWebSocket(mock_config, debug_mode=False)
    # 재시도 설정을 테스트에 맞게 조정
    client._max_reconnect_attempts = 5  # 테스트용으로 줄임
    client._reconnect_delay = 0.1  # 테스트용으로 짧게 설정
    return client


# =============================================================================
# Test 1: 지수 백오프 (Exponential Backoff)
# =============================================================================

class TestExponentialBackoff:
    """지수 백오프 동작 검증"""

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_retry(self, websocket_client):
        """
        GIVEN: WebSocket 연결이 실패하는 상황 (access_token 있음)
        WHEN: 재연결을 시도하면
        THEN: 대기 시간이 지수적으로 증가해야 함 (1s, 2s, 4s, 8s...)
        """
        # Arrange: sleep 함수를 mock하여 대기 시간을 측정
        sleep_times = []

        async def mock_sleep(seconds):
            sleep_times.append(seconds)

        # 테스트를 위해 access_token 설정
        websocket_client._access_token = "test_token"

        # Act: 재연결 시도 (connect는 항상 실패)
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with patch.object(websocket_client, 'connect', return_value=False):
                await websocket_client._reconnect(max_attempts=4)

        # Assert: 대기 시간이 지수적으로 증가하는지 확인
        # 기대값: 0.1, 0.2, 0.4 (base_delay * 2^attempt)
        assert len(sleep_times) == 3, "3번의 재시도 대기가 있어야 함"
        assert sleep_times[0] == 0.1, f"첫 번째 대기 시간은 0.1s여야 함, 실제: {sleep_times[0]}"
        assert sleep_times[1] == 0.2, f"두 번째 대기 시간은 0.2s여야 함, 실제: {sleep_times[1]}"
        assert sleep_times[2] == 0.4, f"세 번째 대기 시간은 0.4s여야 함, 실제: {sleep_times[2]}"

    @pytest.mark.asyncio
    async def test_exponential_backoff_with_max_cap(self, websocket_client):
        """
        GIVEN: 지수 백오프 대기 시간이 최대값을 초과해야 할 때
        WHEN: 재연결을 시도하면
        THEN: 대기 시간이 최대값(60초)으로 제한되어야 함
        """
        # Arrange: 많은 재시도 시도
        sleep_times = []

        async def mock_sleep(seconds):
            sleep_times.append(seconds)

        # 테스트를 위해 access_token 설정
        websocket_client._access_token = "test_token"

        # Act: 10번의 재시도 시도
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with patch.object(websocket_client, 'connect', return_value=False):
                # base_delay가 10초라고 가정하면 10, 20, 40, 60, 60...으로 제한되어야 함
                websocket_client._reconnect_delay = 10
                await websocket_client._reconnect(max_attempts=8)

        # Assert: 최대값(60초) 제한 확인
        max_sleep = max(sleep_times) if sleep_times else 0
        assert max_sleep <= 60, f"최대 대기 시간은 60초 이하여야 함, 실제: {max_sleep}"

    @pytest.mark.asyncio
    async def test_no_sleep_on_final_attempt(self, websocket_client):
        """
        GIVEN: 마지막 재시도 시도가 실패할 때
        WHEN: 모든 시도가 소진되면
        THEN: 추가 대기 없이 즉시 False를 반환해야 함
        """
        # Arrange
        sleep_count = [0]
        websocket_client._access_token = "test_token"

        async def mock_sleep(seconds):
            sleep_count[0] += 1

        # Act
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with patch.object(websocket_client, 'connect', return_value=False):
                result = await websocket_client._reconnect(max_attempts=3)

        # Assert: 3번 시도 → 2번만 sleep (마지막 시도 후에는 sleep 없음)
        assert result is False, "재연결 실패 시 False 반환해야 함"
        assert sleep_count[0] == 2, f"마지막 시도 후에는 sleep이 없어야 함, 실제 sleep 횟수: {sleep_count[0]}"


# =============================================================================
# Test 2: 최대 재시도 횟수 제한
# =============================================================================

class TestMaxRetryAttempts:
    """최대 재시도 횟수 제한 검증"""

    @pytest.mark.asyncio
    async def test_respects_max_retry_attempts(self, websocket_client):
        """
        GIVEN: max_attempts = 3으로 설정된 상황
        WHEN: 연결이 계속 실패하면
        THEN: 정확히 3번만 시도하고 중단해야 함
        """
        # Arrange: connect 호출 횟수 추적
        connect_count = [0]
        websocket_client._access_token = "test_token"

        async def mock_connect(*args, **kwargs):
            connect_count[0] += 1
            return False  # 항상 실패

        # Act
        with patch.object(websocket_client, 'connect', side_effect=mock_connect):
            result = await websocket_client._reconnect(max_attempts=3)

        # Assert
        assert result is False, "재연결 실패 시 False 반환해야 함"
        assert connect_count[0] == 3, f"정확히 3번 시도해야 함, 실제: {connect_count[0]}"

    @pytest.mark.asyncio
    async def test_stops_on_first_success(self, websocket_client):
        """
        GIVEN: 최대 재시도 횟수가 5번인 상황
        WHEN: 2번째 시도에서 성공하면
        THEN: 추가 시도 없이 즉시 True를 반환해야 함
        """
        # Arrange
        connect_count = [0]
        websocket_client._access_token = "test_token"

        async def mock_connect(*args, **kwargs):
            connect_count[0] += 1
            return connect_count[0] == 2  # 2번째 시도에서 성공

        # Act
        with patch.object(websocket_client, 'connect', side_effect=mock_connect):
            result = await websocket_client._reconnect(max_attempts=5)

        # Assert
        assert result is True, "재연결 성공 시 True 반환해야 함"
        assert connect_count[0] == 2, f"성공 시 즉시 중단해야 함, 실제 시도 횟수: {connect_count[0]}"

    @pytest.mark.asyncio
    async def test_default_max_attempts(self, websocket_client):
        """
        GIVEN: max_attempts를 별도로 지정하지 않은 상황
        WHEN: 재연결을 시도하면
        THEN: 기본값(DEFAULT_MAX_RECONNECT_ATTEMPTS = 10)을 사용해야 함
        """
        # Arrange: fixture 설정을 기본값으로 복원
        connect_count = [0]
        websocket_client._access_token = "test_token"
        websocket_client._max_reconnect_attempts = websocket_client.DEFAULT_MAX_RECONNECT_ATTEMPTS  # 기본값 10

        async def mock_connect(*args, **kwargs):
            connect_count[0] += 1
            return False

        # Act: max_attempts 없이 호출 (sleep mock으로 시간 단축)
        with patch('asyncio.sleep'):  # sleep 생략
            with patch.object(websocket_client, 'connect', side_effect=mock_connect):
                await websocket_client._reconnect()

        # Assert: 기본값 10회 사용 (수정됨)
        assert connect_count[0] == 10, f"기본 최대 횟수는 10회여야 함, 실제: {connect_count[0]}"


# =============================================================================
# Test 3: 로그 레벨 조정
# =============================================================================

class TestLogLevelAdjustment:
    """로그 레벨 조정 검증"""

    @pytest.mark.asyncio
    async def test_warning_level_on_retry_failure(self, websocket_client, caplog):
        """
        GIVEN: 연결 실패 상황
        WHEN: 재시도를 시도하면
        THEN: WARNING 레벨로 로깅되어야 함 (매 시도마다 INFO 아님)
        """
        # Arrange: caplog를 사용하여 로그 캡처
        import logging
        caplog.set_level(logging.WARNING)

        # Act
        with patch.object(websocket_client, 'connect', return_value=False):
            await websocket_client._reconnect(max_attempts=2)

        # Assert: WARNING 레벨 로그가 있는지 확인
        warning_logs = [record for record in caplog.records if record.levelno >= logging.WARNING]
        assert len(warning_logs) > 0, "재시도 실패 시 WARNING 레벨 로그가 있어야 함"

    @pytest.mark.asyncio
    async def test_info_level_on_final_success(self, websocket_client, caplog):
        """
        GIVEN: 재시도 중인 상황
        WHEN: 연결에 성공하면
        THEN: INFO 레벨로 성공 로그를 출력해야 함
        """
        # Arrange
        import logging
        caplog.set_level(logging.INFO)
        websocket_client._access_token = "test_token"

        attempt_count = [0]

        async def mock_connect(*args, **kwargs):
            attempt_count[0] += 1
            return attempt_count[0] >= 2  # 2번째 시도에서 성공

        # Act
        with patch.object(websocket_client, 'connect', side_effect=mock_connect):
            await websocket_client._reconnect(max_attempts=5)

        # Assert: 성공 로그 확인
        info_logs = [record for record in caplog.records if record.levelno == logging.INFO]
        success_logs = [log for log in info_logs if "successful" in log.message.lower() or "reconnected" in log.message.lower()]
        assert len(success_logs) > 0, "재연결 성공 시 INFO 레벨 로그가 있어야 함"

    @pytest.mark.asyncio
    async def test_no_excessive_logging_on_retries(self, websocket_client, caplog):
        """
        GIVEN: 다수의 재시도가 발생하는 상황
        WHEN: 10번의 재시도가 실패하면
        THEN: 과도한 로그(10개 이상의 INFO 로그)가 생성되지 않아야 함
        """
        # Arrange
        import logging
        caplog.set_level(logging.INFO)

        # Act
        with patch('asyncio.sleep'):  # sleep 생략 (테스트 속도)
            with patch.object(websocket_client, 'connect', return_value=False):
                await websocket_client._reconnect(max_attempts=10)

        # Assert: INFO 레벨 로그가 과도하지 않아야 함
        info_logs = [record for record in caplog.records if record.levelno == logging.INFO]
        # 각 재시도마다 INFO 로그를 남기면 10개가 넘어가지만, 요약 로그면 적어야 함
        assert len(info_logs) <= 5, f"과도한 INFO 로그 생성: {len(info_logs)}개 (요약 로그 권장)"


# =============================================================================
# Test 4: 재시도 후 구독 복원
# =============================================================================

class TestSubscriptionRestoration:
    """재연결 후 구독 복원 검증"""

    @pytest.mark.asyncio
    async def test_tickers_restored_after_reconnect(self, websocket_client):
        """
        GIVEN: 재연결 전에 종목을 구독한 상황
        WHEN: 재연결에 성공하면
        THEN: 이전 구독이 모두 복원되어야 함 (_receive_loop에서 처리)

        NOTE: 이 테스트는 _receive_loop의 구독 복원 로직을 검증합니다.
        """
        # Arrange: 기존 구독 설정 및 access_token
        websocket_client._subscribed_tickers = {"005930", "000660", "035420"}
        websocket_client._subscribed_indices = {"001", "201"}
        websocket_client._access_token = "test_token"

        # _receive_loop는 connect 성공 후 구독을 복원하므로
        # 실제 구독 복원 테스트는 통합 테스트에서 수행하는 것이 적합합니다.
        # 여기서는 _reconnect가 성공 후 True를 반환하는지만 검증합니다.

        # Act: 재연결 성공
        with patch.object(websocket_client, 'connect', return_value=True):
            result = await websocket_client._reconnect(max_attempts=3)

        # Assert: 재연결 성공 확인
        assert result is True, "재연결 성공해야 함"


# =============================================================================
# Test 5: 종료 요청 처리
# =============================================================================

class TestStopRequest:
    """종료 요청 시 graceful shutdown 검증"""

    @pytest.mark.asyncio
    async def test_stop_request_halts_reconnection(self, websocket_client):
        """
        GIVEN: 재연결 루프가 실행 중인 상황
        WHEN: 종료 요청이 있으면
        THEN: 즉시 재연결을 중단해야 함
        """
        # Arrange
        websocket_client._stop_requested = True

        connect_count = [0]

        async def mock_connect(*args, **kwargs):
            connect_count[0] += 1
            return False

        # Act
        with patch.object(websocket_client, 'connect', side_effect=mock_connect):
            result = await websocket_client._reconnect(max_attempts=10)

        # Assert: 종료 요청이 있으면 시도하지 않음
        assert connect_count[0] == 0, "종료 요청 시 재연결을 시도하지 않아야 함"
        assert result is False, "종료 요청 시 False 반환해야 함"
