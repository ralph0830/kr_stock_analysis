"""
API Gateway Circuit Breaker 통합 테스트
"""

import pytest
import time
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from services.api_gateway.main import app
from src.utils.circuit_breaker import (
    circuit_breaker_registry,
    CircuitBreakerState,
    CircuitBreakerError,
)


class TestCircuitBreakerIntegration:
    """Circuit Breaker 통합 테스트"""

    def test_circuit_breaker_registry_exists(self):
        """Circuit Breaker 레지스트리 존재 확인"""
        assert circuit_breaker_registry is not None

    def test_get_or_create_circuit_breaker(self):
        """Circuit Breaker 조회 또는 생성 테스트"""
        # 없는 이름으로 생성
        cb1 = circuit_breaker_registry.get_or_create(
            name="test-service",
            failure_threshold=3,
        )
        assert cb1 is not None

        # 같은 이름으로 조회 (동일 인스턴스)
        cb2 = circuit_breaker_registry.get_or_create("test-service")
        assert cb1 is cb2

    def test_circuit_breaker_initial_state(self):
        """Circuit Breaker 초기 상태 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-initial-state",
            failure_threshold=2,
        )

        # 초기 상태: CLOSED
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_circuit_breaker_state_transitions(self):
        """Circuit Breaker 상태 전이 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-transitions",
            failure_threshold=2,
            recovery_timeout=1.0,
        )

        # 초기 상태: CLOSED
        assert cb.state == CircuitBreakerState.CLOSED

        # 실패 기록
        cb.record_failure("Error 1")
        assert cb.state == CircuitBreakerState.CLOSED  # 아직 CLOSED

        cb.record_failure("Error 2")
        # 실패 임계값 도달 → OPEN
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_open_blocks_calls(self):
        """OPEN 상태에서 호출 차단 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-blocking",
            failure_threshold=2,
        )

        # OPEN 상태로 전이
        cb.record_failure("Error 1")
        cb.record_failure("Error 2")
        assert cb.state == CircuitBreakerState.OPEN

        # OPEN 상태에서 요청 → 예외
        @cb.call
        def test_function():
            return "success"

        with pytest.raises(CircuitBreakerError):
            test_function()

    def test_circuit_breaker_auto_recovery(self):
        """Circuit Breaker 자동 복구 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-recovery",
            failure_threshold=2,
            recovery_timeout=0.5,  # 0.5초 후 복구
            half_open_max_calls=1,  # 1회 성공으로 복구
        )

        # OPEN 상태로 전이
        cb.record_failure("Error 1")
        cb.record_failure("Error 2")
        assert cb.state == CircuitBreakerState.OPEN

        # 복구 시간 대기
        time.sleep(0.6)

        # HALF_OPEN 상태로 전이 (상태 확인 시 자동 업데이트)
        current_state = cb.state
        assert current_state in [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED]

        # 성공하면 CLOSED로 복귀
        @cb.call
        def success_function():
            return "success"

        result = success_function()
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_with_decorator(self):
        """@with_circuit_breaker 데코레이터 테스트"""
        from src.utils.circuit_breaker import with_circuit_breaker

        # Circuit Breaker 생성
        cb = circuit_breaker_registry.get_or_create(
            name="decorator-test",
            failure_threshold=2,
            recovery_timeout=1.0,
        )

        @with_circuit_breaker("decorator-test")
        def test_function():
            return "function result"

        # 정상 호출
        result = test_function()
        assert result == "function result"

        # 실패 유도
        @with_circuit_breaker("decorator-test")
        def failing_function():
            raise Exception("Service error")

        # 두 번 실패
        for _ in range(2):
            with pytest.raises(Exception):
                failing_function()

        # Circuit Breaker가 열려야 함
        assert cb.state == CircuitBreakerState.OPEN


class TestServiceResilience:
    """서비스 복원력 테스트"""

    def test_service_down_scenario(self):
        """서비스 다운 시나리오 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="down-service",
            failure_threshold=3,
        )

        # 서비스 다운 가정 (연속 실패)
        for i in range(3):
            cb.record_failure(f"Connection error {i+1}")

        # Circuit Breaker가 열려야 함
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3

        # 이후 요청은 즉시 실패 (서비스 호출 안 함)
        @cb.call
        def should_not_be_called():
            return "should not be called"

        with pytest.raises(CircuitBreakerError):
            should_not_be_called()

    def test_service_recovery_scenario(self):
        """서비스 복구 시나리오 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="recovery-service",
            failure_threshold=2,
            recovery_timeout=0.5,
            half_open_max_calls=1,  # 1회 성공으로 복구
        )

        # 서비스 다운
        cb.record_failure("Service down")
        cb.record_failure("Service down")

        assert cb.state == CircuitBreakerState.OPEN

        # 복구 대기
        time.sleep(0.6)

        # 서비스 복구 가정
        @cb.call
        def healthy_service():
            return "service is back"

        # HALF_OPEN에서 성공하면 CLOSED로 복귀
        result = healthy_service()
        assert result == "service is back"
        assert cb.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerMetrics:
    """Circuit Breaker 메트릭 테스트"""

    def test_failure_count_tracking(self):
        """실패 횟수 추적 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-metrics",
            failure_threshold=5,
        )

        # 초기 실패 횟수
        assert cb.failure_count == 0

        # 실패 기록
        cb.record_failure("Error 1")
        cb.record_failure("Error 2")
        cb.record_failure("Error 3")

        assert cb.failure_count == 3

    def test_success_count_tracking(self):
        """성공 횟수 추적 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-success-metrics",
            failure_threshold=5,
        )

        # 초기 성공 횟수
        assert cb.success_count == 0

        # 성공 기록
        cb.record_success()
        cb.record_success()
        cb.record_success()

        assert cb.success_count == 3

    def test_state_reset_after_recovery(self):
        """복구 후 상태 리셋 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-reset",
            failure_threshold=2,
            recovery_timeout=0.3,
            half_open_max_calls=1,  # 1회 성공으로 복구
        )

        # OPEN 상태로 전이
        cb.record_failure("Error 1")
        cb.record_failure("Error 2")
        assert cb.failure_count == 2
        assert cb.state == CircuitBreakerState.OPEN

        # 복구 대기
        time.sleep(0.4)

        # 성공 호출로 복구
        @cb.call
        def success_func():
            return "success"

        success_func()

        # 상태 확인을 통해 _update_state() 트리거
        # (한 번 더 state에 접근해야 HALF_OPEN → CLOSED 전환 발생)
        final_state = cb.state

        # 실패 횟수 리셋 확인
        assert cb.failure_count == 0
        assert final_state == CircuitBreakerState.CLOSED

    def test_last_failure_message(self):
        """마지막 실패 메시지 추적 테스트"""
        cb = circuit_breaker_registry.get_or_create(
            name="test-error-message",
        )

        cb.record_failure("First error")
        assert cb.last_failure_message == "First error"

        cb.record_failure("Second error")
        assert cb.last_failure_message == "Second error"


class TestCircuitBreakerRegistry:
    """Circuit Breaker 레지스트리 테스트"""

    def test_multiple_circuit_breakers(self):
        """여러 Circuit Breaker 관리 테스트"""
        # 서로 다른 이름으로 생성
        cb1 = circuit_breaker_registry.get_or_create("service-1")
        cb2 = circuit_breaker_registry.get_or_create("service-2")
        cb3 = circuit_breaker_registry.get_or_create("service-3")

        # 서로 다른 인스턴스
        assert cb1 is not cb2
        assert cb2 is not cb3
        assert cb1 is not cb3

    def test_list_breakers(self):
        """Circuit Breaker 목록 조회 테스트"""
        # 초기화
        circuit_breaker_registry.get_or_create("list-test-1")
        circuit_breaker_registry.get_or_create("list-test-2")

        # 목록 조회
        breakers = circuit_breaker_registry.get_all_states()

        # 이름으로 확인
        assert "list-test-1" in breakers
        assert "list-test-2" in breakers

        # 상태 확인
        assert breakers["list-test-1"] == "closed"
        assert breakers["list-test-2"] == "closed"
