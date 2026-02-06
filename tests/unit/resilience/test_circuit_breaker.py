"""
서킷 브레이커 테스트 (TDD - Red Phase)

이 테스트 파일은 CircuitBreaker의 동작을 검증합니다.
TDD 방식으로 작성되었으며, 먼저 실패하는 테스트를 작성합니다.

테스트 커버리지:
1. 연속 실패 시 서킷 오픈
2. 서킷 오픈 시 요청 즉시 실패 반환
3. 일정 시간 후 half-open 상태 전환
4. half-open 상태에서 성공 시 closed 상태로 복귀
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

# 테스트 대상 모듈 임포트 (구현 전이라 임시로 생성)
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def circuit_breaker():
    """테스트용 CircuitBreaker fixture"""
    return CircuitBreaker(
        failure_threshold=5,    # 연속 5회 실패 시 오픈
        timeout=30,              # 30초 후 half-open
        half_open_max_calls=1   # half-open 시 1회 시도
    )


@pytest.fixture
def async_function_that_fails():
    """항상 실패하는 비동기 함수 fixture"""
    async def failing_func():
        raise Exception("Simulated failure")
    return failing_func


@pytest.fixture
def async_function_that_succeeds():
    """항상 성공하는 비동기 함수 fixture"""
    async def success_func():
        return "success"
    return success_func


# =============================================================================
# Test 1: 연속 실패 시 서킷 오픈
# =============================================================================

class TestCircuitBreakerOpen:
    """서킷 오픈 동작 검증"""

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self, circuit_breaker, async_function_that_fails):
        """
        GIVEN: 서킷이 CLOSED 상태
        WHEN: 연속 5회 실패가 발생하면
        THEN: 서킷이 OPEN 상태로 전환되어야 함
        """
        # Arrange: 서킷이 CLOSED 상태인지 확인
        assert circuit_breaker.state == CircuitState.CLOSED, "초기 상태는 CLOSED여야 함"

        # Act: 5회 실패 시도
        for _ in range(5):
            try:
                await circuit_breaker.call(async_function_that_fails)
            except Exception:
                pass  # 실패 예상

        # Assert: 서킷이 OPEN 상태인지 확인
        assert circuit_breaker.state == CircuitState.OPEN, "5회 실패 후 서킷이 OPEN 상태여야 함"

    @pytest.mark.asyncio
    async def test_opens_after_custom_threshold(self):
        """
        GIVEN: failure_threshold = 3으로 설정된 상황
        WHEN: 연속 3회 실패가 발생하면
        THEN: 서킷이 OPEN 상태로 전환되어야 함
        """
        # Arrange: threshold = 3
        cb = CircuitBreaker(failure_threshold=3, timeout=30)

        async def failing_func():
            raise Exception("Failure")

        # Act: 3회 실패 시도
        for _ in range(3):
            try:
                await cb.call(failing_func)
            except Exception:
                pass

        # Assert
        assert cb.state == CircuitState.OPEN, "3회 실패 후 서킷이 OPEN 상태여야 함"

    @pytest.mark.asyncio
    async def test_remains_closed_below_threshold(self, circuit_breaker, async_function_that_fails):
        """
        GIVEN: failure_threshold = 5인 상황
        WHEN: 4회 실패가 발생하면
        THEN: 서킷이 CLOSED 상태를 유지해야 함
        """
        # Act: 4회 실패 시도 (threshold 미만)
        for _ in range(4):
            try:
                await circuit_breaker.call(async_function_that_fails)
            except Exception:
                pass

        # Assert: 여전히 CLOSED 상태
        assert circuit_breaker.state == CircuitState.CLOSED, "threshold 미만 실패 시 CLOSED 상태 유지"


# =============================================================================
# Test 2: 서킷 오픈 시 요청 즉시 실패
# =============================================================================

class TestCircuitBreakerRequestBlocking:
    """서킷 오픈 시 요청 차단 검증"""

    @pytest.mark.asyncio
    async def test_raises_exception_when_open(self, circuit_breaker, async_function_that_succeeds):
        """
        GIVEN: 서킷이 OPEN 상태
        WHEN: 요청을 시도하면
        THEN: CircuitBreakerOpenError가 즉시 발생해야 함 (함수 미호출)
        """
        # Arrange: 서킷을 OPEN 상태로 변경
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = datetime.now(timezone.utc)

        # Act & Assert: 예외 발생 확인
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(async_function_that_succeeds)

    @pytest.mark.asyncio
    async def test_does_not_call_function_when_open(self, circuit_breaker):
        """
        GIVEN: 서킷이 OPEN 상태
        WHEN: 요청을 시도하면
        THEN: 실제 함수가 호출되지 않아야 함
        """
        # Arrange: 서킷을 OPEN 상태로 변경
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = datetime.now(timezone.utc)

        # Act: 함수 호출 횟수 확인
        call_count = [0]

        async def tracked_func():
            call_count[0] += 1
            return "result"

        # 함수가 호출되지 않고 예외 발생
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(tracked_func)

        # Assert: 함수가 호출되지 않음
        assert call_count[0] == 0, "OPEN 상태에서는 함수가 호출되지 않아야 함"


# =============================================================================
# Test 3: Half-open 상태 전환
# =============================================================================

class TestHalfOpenTransition:
    """Half-open 상태 전환 검증"""

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self, circuit_breaker):
        """
        GIVEN: 서킷이 OPEN 상태이고 timeout 경과
        WHEN: 새 요청이 들어오면
        THEN: HALF_OPEN 상태로 전환되어야 함 (성공 시 CLOSED로 바로 전환될 수 있음)
        """
        # Arrange: 서킷을 OPEN 상태로 변경 (30초 전의 실패 시간 기록)
        circuit_breaker._state = CircuitState.OPEN
        past_time = datetime.now(timezone.utc) - timedelta(seconds=31)
        circuit_breaker._last_failure_time = past_time

        # Act: 요청 시도 (성공 함수)
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)

        # Assert: HALF_OPEN을 거쳐 CLOSED로 전환되거나 바로 CLOSED로 전환
        # 성공하면 CLOSED로 바로 전환되므로 CLOSED 상태여도 통과
        assert circuit_breaker.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED), \
            "timeout 경과 후 HALF_OPEN 또는 CLOSED 상태로 전환"
        assert result == "success", "요청이 실행되어야 함"

    @pytest.mark.asyncio
    async def test_remains_open_within_timeout(self, circuit_breaker):
        """
        GIVEN: 서킷이 OPEN 상태이고 timeout 미경과
        WHEN: 요청이 들어오면
        THEN: OPEN 상태를 유지하며 요청을 차단해야 함
        """
        # Arrange: 서킷을 OPEN 상태로 변경 (최근 실패 시간)
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = datetime.now(timezone.utc)

        # Act & Assert: 여전히 OPEN 상태 (요청 차단)
        with pytest.raises(CircuitBreakerOpenError):
            async def dummy_func():
                return "result"
            await circuit_breaker.call(dummy_func)


# =============================================================================
# Test 4: 성공 시 CLOSED 상태 복귀
# =============================================================================

class TestClosedRecovery:
    """성공 시 CLOSED 상태 복귀 검증"""

    @pytest.mark.asyncio
    async def test_transitions_to_closed_on_half_open_success(self, circuit_breaker):
        """
        GIVEN: 서킷이 HALF_OPEN 상태
        WHEN: 요청이 성공하면
        THEN: CLOSED 상태로 복귀하고 실패 카운트가 리셋되어야 함
        """
        # Arrange: HALF_OPEN 상태 설정
        circuit_breaker._state = CircuitState.HALF_OPEN

        # Act: 성공 함수 호출
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)

        # Assert: CLOSED 상태로 복귀
        assert circuit_breaker.state == CircuitState.CLOSED, "HALF_OPEN 성공 후 CLOSED 상태 복귀"
        assert circuit_breaker._failure_count == 0, "실패 카운트가 리셋되어야 함"
        assert result == "success"

    @pytest.mark.asyncio
    async def test_opens_again_on_half_open_failure(self, circuit_breaker):
        """
        GIVEN: 서킷이 HALF_OPEN 상태
        WHEN: 요청이 실패하면
        THEN: 다시 OPEN 상태로 전환되어야 함
        """
        # Arrange: HALF_OPEN 상태 설정
        circuit_breaker._state = CircuitState.HALF_OPEN

        # Act: 실패 함수 호출
        async def failing_func():
            raise Exception("Failure")

        try:
            await circuit_breaker.call(failing_func)
        except Exception:
            pass  # 실패 예상

        # Assert: 다시 OPEN 상태로 전환
        assert circuit_breaker.state == CircuitState.OPEN, "HALF_OPEN 실패 후 다시 OPEN 상태"


# =============================================================================
# Test 5: 성공 시 실패 카운트 리셋
# =============================================================================

class TestFailureCountReset:
    """성공 시 실패 카운트 리셋 검증"""

    @pytest.mark.asyncio
    async def test_resets_failure_count_on_success(self, circuit_breaker):
        """
        GIVEN: 3회 실패 후 성공하는 상황
        WHEN: 요청이 성공하면
        THEN: 실패 카운트가 0으로 리셋되어야 함
        """
        # Arrange: 3회 실패 상태
        async def failing_func():
            raise Exception("Failure")

        for _ in range(3):
            try:
                await circuit_breaker.call(failing_func)
            except Exception:
                pass

        assert circuit_breaker._failure_count == 3, "3회 실패 카운트 확인"

        # Act: 성공 함수 호출
        async def success_func():
            return "success"

        await circuit_breaker.call(success_func)

        # Assert: 실패 카운트 리셋
        assert circuit_breaker._failure_count == 0, "성공 후 실패 카운트 리셋"


# =============================================================================
# Test 6: 상태 조회 메서드
# =============================================================================

class TestStateQueries:
    """상태 조회 메서드 검증"""

    def test_state_property(self, circuit_breaker):
        """
        GIVEN: CircuitBreaker 인스턴스
        WHEN: state 속성을 조회하면
        THEN: 현재 상태를 반환해야 함
        """
        # Arrange & Act & Assert
        assert circuit_breaker.state == CircuitState.CLOSED, "초기 상태는 CLOSED여야 함"

        # OPEN 상태로 변경 후 확인
        circuit_breaker._state = CircuitState.OPEN
        assert circuit_breaker.state == CircuitState.OPEN, "OPEN 상태 확인"

    def test_is_closed(self, circuit_breaker):
        """is_closed() 메서드 검증"""
        assert circuit_breaker.is_closed() is True, "CLOSED 상태에서는 True여야 함"

        circuit_breaker._state = CircuitState.OPEN
        assert circuit_breaker.is_closed() is False, "OPEN 상태에서는 False여야 함"

    def test_is_open(self, circuit_breaker):
        """is_open() 메서드 검증"""
        assert circuit_breaker.is_open() is False, "CLOSED 상태에서는 False여야 함"

        circuit_breaker._state = CircuitState.OPEN
        assert circuit_breaker.is_open() is True, "OPEN 상태에서는 True여야 함"
