"""
Circuit Breaker 테스트
"""

import pytest
import time
from httpx import HTTPError, RequestError

from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    with_circuit_breaker,
    circuit_breaker_registry,
)
from src.utils.httpx_circuit_breaker import (
    CircuitBreakerTransport,
    CircuitBreakerAsyncTransport,
    create_circuit_breaker_client,
)


class TestCircuitBreaker:
    """CircuitBreaker 클래스 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    def test_closed_to_open_on_failures(self):
        """실패 임계값 도달 시 OPEN 전환 테스트"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)

        # 3회 실패
        breaker.record_failure("Error 1")
        breaker.record_failure("Error 2")
        breaker.record_failure("Error 3")

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3
        assert breaker.last_failure_message == "Error 3"

    def test_open_to_half_open_after_timeout(self):
        """복구 시간 경과 후 HALF_OPEN 전환 테스트"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        # OPEN 상태로 전환
        breaker.record_failure("Error 1")
        breaker.record_failure("Error 2")
        assert breaker.state == CircuitBreakerState.OPEN

        # 복구 대기
        time.sleep(1.1)

        # HALF_OPEN으로 전환 확인
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        """HALF_OPEN 상태에서 성공 시 CLOSED 전환 테스트"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0, half_open_max_calls=2)

        # OPEN → HALF_OPEN
        breaker.record_failure("Error 1")
        breaker.record_failure("Error 2")
        time.sleep(1.1)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # 2회 성공 (half_open_max_calls)
        breaker.record_success()
        breaker.record_success()

        # CLOSED로 전환
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_reset(self):
        """리셋 기능 테스트"""
        breaker = CircuitBreaker(failure_threshold=3)

        # 실패 상태로 만들기
        breaker.record_failure("Error")
        breaker.record_failure("Error")
        breaker.record_failure("Error")
        assert breaker.state == CircuitBreakerState.OPEN

        # 리셋
        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.last_failure_message is None

    def test_call_decorator_success(self):
        """성공 호출 데코레이터 테스트"""
        breaker = CircuitBreaker(failure_threshold=3)

        @breaker.call
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"
        assert breaker.success_count >= 1

    def test_call_decorator_failure(self):
        """실패 호출 데코레이터 테스트"""
        breaker = CircuitBreaker(failure_threshold=2)

        @breaker.call
        def failing_function():
            raise ValueError("Test error")

        # 1회 실패
        with pytest.raises(ValueError):
            failing_function()
        assert breaker.failure_count == 1
        assert breaker.state == CircuitBreakerState.CLOSED

        # 2회 실패 → OPEN
        with pytest.raises(ValueError):
            failing_function()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_call_decorator_open_circuit(self):
        """OPEN 상태에서 CircuitBreakerError 발생 테스트"""
        breaker = CircuitBreaker(failure_threshold=2)

        @breaker.call
        def failing_function():
            raise ValueError("Test error")

        # OPEN 상태로 만들기
        with pytest.raises(ValueError):
            failing_function()
        with pytest.raises(ValueError):
            failing_function()
        assert breaker.state == CircuitBreakerState.OPEN

        # 이제 CircuitBreakerError 발생
        with pytest.raises(CircuitBreakerError):
            failing_function()


class TestCircuitBreakerRegistry:
    """CircuitBreakerRegistry 테스트"""

    def test_singleton(self):
        """싱글톤 패턴 테스트"""
        registry1 = CircuitBreakerRegistry()
        registry2 = CircuitBreakerRegistry()
        assert registry1 is registry2

    def test_get_or_create(self):
        """서킷 브레이커 조회/생성 테스트"""
        registry = CircuitBreakerRegistry()

        breaker1 = registry.get_or_create("test_api", failure_threshold=5)
        breaker2 = registry.get_or_create("test_api", failure_threshold=10)

        # 같은 인스턴스 반환
        assert breaker1 is breaker2

    def test_get_all_states(self):
        """모든 상태 조회 테스트"""
        registry = CircuitBreakerRegistry()

        breaker1 = registry.get_or_create("api1", failure_threshold=2)
        breaker1.record_failure("Error")
        breaker1.record_failure("Error")

        states = registry.get_all_states()
        assert "api1" in states
        assert states["api1"] == CircuitBreakerState.OPEN.value

    def test_reset_all(self):
        """모두 리셋 테스트"""
        registry = CircuitBreakerRegistry()

        # 고유 이름 사용 (다른 테스트와 겹치지 않도록)
        breaker1 = registry.get_or_create("reset_test_api1", failure_threshold=1)
        breaker2 = registry.get_or_create("reset_test_api2", failure_threshold=1)

        breaker1.record_failure("Error")
        breaker2.record_failure("Error")

        assert breaker1.state == CircuitBreakerState.OPEN
        assert breaker2.state == CircuitBreakerState.OPEN

        registry.reset_all()

        assert breaker1.state == CircuitBreakerState.CLOSED
        assert breaker2.state == CircuitBreakerState.CLOSED


class TestWithCircuitBreakerDecorator:
    """with_circuit_breaker 데코레이터 테스트"""

    def test_decorator_success(self):
        """데코레이터 성공 테스트"""
        @with_circuit_breaker("test_decorator", failure_threshold=3)
        def api_call():
            return "result"

        result = api_call()
        assert result == "result"

    def test_decorator_failure(self):
        """데코레이터 실패 테스트"""
        @with_circuit_breaker("test_decorator_fail", failure_threshold=2)
        def api_call():
            raise ConnectionError("Connection failed")

        # 1회 실패
        with pytest.raises(ConnectionError):
            api_call()

        # 2회 실패 → OPEN
        with pytest.raises(ConnectionError):
            api_call()

        # CircuitBreakerError 발생
        with pytest.raises(CircuitBreakerError):
            api_call()

    def test_decorator_multiple_functions(self):
        """여러 함수에 데코레이터 적용 테스트"""
        @with_circuit_breaker("shared_api", failure_threshold=2)
        def function_a():
            raise ValueError("Error A")

        @with_circuit_breaker("shared_api", failure_threshold=2)
        def function_b():
            raise ValueError("Error B")

        # 같은 서킷 브레이커 공유
        with pytest.raises(ValueError):
            function_a()
        with pytest.raises(ValueError):
            function_b()

        # 두 함수 모두 OPEN 상태
        with pytest.raises(CircuitBreakerError):
            function_a()
        with pytest.raises(CircuitBreakerError):
            function_b()


class TestCircuitBreakerTransport:
    """CircuitBreakerTransport 테스트"""

    def test_transport_creation(self):
        """트랜스포트 생성 테스트"""
        transport = CircuitBreakerTransport("test_transport")
        assert transport is not None
        assert transport._circuit_breaker is not None

    def test_transport_failure_threshold(self):
        """실패 임계값 설정 테스트"""
        transport = CircuitBreakerTransport(
            "test_threshold",
            failure_threshold=3,
            recovery_timeout=10.0,
        )
        assert transport._circuit_breaker.failure_threshold == 3

    def test_async_transport_creation(self):
        """비동기 트랜스포트 생성 테스트"""
        transport = CircuitBreakerAsyncTransport("test_async")
        assert transport is not None
        assert transport._circuit_breaker is not None


class TestCreateCircuitBreakerClient:
    """create_circuit_breaker_client 테스트"""

    def test_create_sync_client(self):
        """동기 클라이언트 생성 테스트"""
        client = create_circuit_breaker_client("test_sync")
        assert client is not None
        assert hasattr(client, "get")
        assert hasattr(client, "post")
        client.close()

    def test_create_async_client(self):
        """비동기 클라이언트 생성 테스트"""
        client = create_circuit_breaker_client("test_async", async_client=True)
        assert client is not None
        assert hasattr(client, "aget")
        assert hasattr(client, "apost")


class TestIntegrationScenarios:
    """통합 시나리오 테스트"""

    def test_service_recovery(self):
        """서비스 복구 시나리오 테스트"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        @breaker.call
        def unreliable_service(should_fail: bool = False):
            if should_fail:
                raise ConnectionError("Service unavailable")
            return "success"

        # 서비스 장애 → OPEN
        for _ in range(3):
            with pytest.raises(ConnectionError):
                unreliable_service(should_fail=True)

        assert breaker.state == CircuitBreakerState.OPEN

        # 복구 대기
        time.sleep(1.1)

        # HALF_OPEN 상태에서 시도
        result = unreliable_service(should_fail=False)
        assert result == "success"

        # 추가 성공으로 CLOSED 전환
        breaker.record_success()
        breaker.record_success()
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_intermittent_failures(self):
        """간헐적 실패 시나리오 테스트"""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=10.0)

        @breaker.call
        def intermittent_service(fail: bool = False):
            if fail:
                raise ValueError("Temporary error")
            return "success"

        # 성공/실패 혼합
        for i in range(10):
            should_fail = i % 3 == 0  # 3번 중 1번 실패
            try:
                intermittent_service(should_fail)
            except (ValueError, CircuitBreakerError):
                pass

        # 간헐적 실패로 OPEN이 되지 않아야 함 (실패 횟수 < 임계값)
        assert breaker.failure_count < 5
        assert breaker.state == CircuitBreakerState.CLOSED
