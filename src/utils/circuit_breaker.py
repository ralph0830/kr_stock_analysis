"""
Circuit Breaker Pattern Implementation
서킷 브레이커 패턴으로 외부 서비스 장애 격리
"""

import time
import functools
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Any, Dict
from collections import deque


class CircuitBreakerState(Enum):
    """서킷 브레이커 상태"""
    CLOSED = "closed"       # 정상 상태 (요청 통과)
    OPEN = "open"           # 차단 상태 (요청 거부)
    HALF_OPEN = "half_open" # 반개방 상태 (일부 요청 통과)


class CircuitBreakerError(Exception):
    """서킷 브레이커 차단 예외"""
    pass


class CircuitBreaker:
    """
    서킷 브레이커 구현

    Args:
        failure_threshold: 실패 임계값 (실패 횟수)
        recovery_timeout: 복구 대기 시간 (초)
        expected_exception: 예외로 간주할 예외 타입 (튜플)
        half_open_max_calls: 반개방 상태에서 허용할 최대 요청 수
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: tuple = (Exception,),
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        # 상태 추적
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_failure_message: Optional[str] = None

        # 슬라이딩 윈도우 (최근 호출 결과 추적)
        self._window_size = max(failure_threshold + half_open_max_calls, 10)
        self._call_history: deque = deque(maxlen=self._window_size)

    @property
    def state(self) -> CircuitBreakerState:
        """현재 상태 반환"""
        self._update_state()
        return self._state

    @property
    def failure_count(self) -> int:
        """현재 실패 횟수"""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """현재 성공 횟수"""
        return self._success_count

    @property
    def last_failure_message(self) -> Optional[str]:
        """마지막 실패 메시지"""
        return self._last_failure_message

    def _update_state(self) -> None:
        """상태 업데이트 (시간 경과에 따른 자동 전환)"""
        now = datetime.now()

        if self._state == CircuitBreakerState.OPEN:
            # 복구 시간 경과 시 HALF_OPEN으로 전환
            if self._last_failure_time:
                elapsed = (now - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._success_count = 0  # 반개방 상태에서 성공 횟수 초기화

        elif self._state == CircuitBreakerState.HALF_OPEN:
            # 반개방 상태에서 성공 횟수가 임계값 도달 시 CLOSED로 전환
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                self._call_history.clear()

    def _is_expired(self, timestamp: datetime) -> bool:
        """타임스탬프가 윈도우에서 만료되었는지 확인"""
        now = datetime.now()
        elapsed = (now - timestamp).total_seconds()
        return elapsed > self.recovery_timeout

    def record_success(self) -> None:
        """성공 기록"""
        self._call_history.append(True)
        self._success_count += 1

        # CLOSED 상태에서 성공 시 실패 카운트 리셋
        if self._state == CircuitBreakerState.CLOSED:
            recent_failures = sum(1 for call in self._call_history if not call)
            if recent_failures < self.failure_threshold:
                self._failure_count = recent_failures

    def record_failure(self, error_message: str = "") -> None:
        """실패 기록"""
        self._call_history.append(False)
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        self._last_failure_message = error_message

        # 실패 임계값 도달 시 OPEN으로 전환
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN

    def call(self, func: Callable) -> Callable:
        """
        함수를 서킷 브레이커로 감싸는 데코레이터

        Usage:
            @circuit_breaker.call
            def external_api_call():
                ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 현재 상태 확인
            current_state = self.state

            if current_state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. Last error: {self._last_failure_message}"
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except self.expected_exception as e:
                self.record_failure(str(e))
                raise

        return wrapper

    def reset(self) -> None:
        """서킷 브레이커 리셋"""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_failure_message = None
        self._call_history.clear()


class CircuitBreakerRegistry:
    """서킷 브레이커 레지스트리 (전역 관리용)"""

    _instance = None
    _breakers: Dict[str, CircuitBreaker] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: tuple = (Exception,),
        half_open_max_calls: int = 3,
    ) -> CircuitBreaker:
        """
        이름으로 서킷 브레이커 조회 또는 생성

        Args:
            name: 서킷 브레이커 이름
            failure_threshold: 실패 임계값
            recovery_timeout: 복구 대기 시간
            expected_exception: 예외로 간주할 예외 타입
            half_open_max_calls: 반개방 상태 최대 요청 수

        Returns:
            CircuitBreaker 인스턴스
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                half_open_max_calls=half_open_max_calls,
            )
        return self._breakers[name]

    def get_all_states(self) -> Dict[str, str]:
        """모든 서킷 브레이커 상태 반환"""
        return {
            name: breaker.state.value
            for name, breaker in self._breakers.items()
        }

    def reset_all(self) -> None:
        """모든 서킷 브레이커 리셋"""
        for breaker in self._breakers.values():
            breaker.reset()


# 전역 레지스트리 인스턴스
circuit_breaker_registry = CircuitBreakerRegistry()


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: tuple = (Exception,),
):
    """
    서킷 브레이커 데코레이터

    Usage:
        @with_circuit_breaker("external_api", failure_threshold=3)
        def call_external_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = circuit_breaker_registry.get_or_create(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )
        return breaker.call(func)
    return decorator
