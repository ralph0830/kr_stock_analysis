"""
서킷 브레이커 (Circuit Breaker) 패턴 구현

분산 시스템에서 외부 서비스 장애 시 전체 시스템의 연쇄적 실패를 방지하기 위해
일정 횟수 이상 실패하면 일시적으로 요청을 차단하는 패턴입니다.

상태 전환:
    CLOSED → OPEN: 연속 실패가 threshold 도달 시
    OPEN → HALF_OPEN: timeout 경과 후
    HALF_OPEN → CLOSED: 요청 성공 시
    HALF_OPEN → OPEN: 요청 실패 시
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Callable, Optional, Any, TypeVar

T = TypeVar('T')


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """서킷 브레이커 상태"""
    CLOSED = "closed"       # 정상 상태, 요청 전달
    OPEN = "open"           # 차단 상태, 요청 거부
    HALF_OPEN = "half_open" # 복구 시도, 일부 요청 허용


class CircuitBreakerOpenError(Exception):
    """서킷 브레이커가 OPEN 상태일 때 발생하는 예외"""
    def __init__(self, message: str = "Circuit breaker is OPEN") -> None:
        self.message = message
        super().__init__(self.message)


class CircuitBreaker:
    """
    서킷 브레이커

    외부 서비스 호출을 래핑하여 장애 상황에서의 과부하를 방지합니다.

    Args:
        failure_threshold: 연속 실패 임계값 (기본값: 5)
        timeout: OPEN 상태 유지 시간 (초, 기본값: 30)
        half_open_max_calls: HALF_OPEN 상태에서 시도할 최대 요청 수 (기본값: 1)

    Usage:
        cb = CircuitBreaker(failure_threshold=5, timeout=30)

        # 함수 호출 래핑
        try:
            result = await cb.call(external_service_function, arg1, arg2)
        except CircuitBreakerOpenError:
            # 서킷이 OPEN 상태, 요청 차단됨
            handle_circuit_open()
        except Exception:
            # 서비스 호출 실패
            handle_service_error()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 30,
        half_open_max_calls: int = 1,
    ):
        """
        서킷 브레이커 초기화

        Args:
            failure_threshold: 연속 실패 임계값
            timeout: OPEN 상태 유지 시간 (초)
            half_open_max_calls: HALF_OPEN 시 시도할 최대 요청 수
        """
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._half_open_max_calls = half_open_max_calls

        # 상태 관리
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0

        # 모니터링
        self._total_calls = 0
        self._total_successes = 0
        self._total_failures = 0

    @property
    def state(self) -> CircuitState:
        """현재 상태 반환"""
        return self._state

    @property
    def failure_count(self) -> int:
        """현재 실패 카운트 반환"""
        return self._failure_count

    def is_closed(self) -> bool:
        """CLOSED 상태 여부 확인"""
        return self._state == CircuitState.CLOSED

    def is_open(self) -> bool:
        """OPEN 상태 여부 확인"""
        return self._state == CircuitState.OPEN

    def is_half_open(self) -> bool:
        """HALF_OPEN 상태 여부 확인"""
        return self._state == CircuitState.HALF_OPEN

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        서킷 브레이커를 통해 함수 호출

        Args:
            func: 호출할 비동기 함수
            *args: 함수 위치 인자
            **kwargs: 함수 키워드 인자

        Returns:
            함수 반환 값

        Raises:
            CircuitBreakerOpenError: 서킷이 OPEN 상태일 때
            Exception: 함수 호출 실패 시
        """
        self._total_calls += 1

        # OPEN 상태 확인
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info("Circuit breaker: OPEN → HALF_OPEN transition")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            else:
                logger.warning(f"Circuit breaker is OPEN, blocking call (failures: {self._failure_count})")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN after {self._failure_count} failures. "
                    f"Last failure: {self._last_failure_time}"
                )

        # HALF_OPEN 상태에서 호출 횟수 제한
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._half_open_max_calls:
                logger.warning("Circuit breaker: HALF_OPEN max calls exceeded, transitioning to OPEN")
                self._transition_to_open()
                raise CircuitBreakerOpenError("Circuit breaker HALF_OPEN max calls exceeded")

        try:
            # 함수 호출
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """
        OPEN 상태에서 HALF_OPEN으로 전환할지 확인

        Returns:
            전환해야 하면 True
        """
        if self._last_failure_time is None:
            return True

        elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
        return elapsed >= self._timeout

    def _on_success(self) -> None:
        """성공 처리"""
        self._total_successes += 1

        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker: HALF_OPEN → CLOSED transition (success)")
            self._transition_to_closed()
        elif self._state == CircuitState.CLOSED:
            # CLOSED 상태에서 성공하면 실패 카운트 리셋
            self._failure_count = 0

    def _on_failure(self) -> None:
        """실패 처리"""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)

        if self._failure_count >= self._failure_threshold:
            logger.warning(
                f"Circuit breaker: Failure threshold ({self._failure_threshold}) reached, "
                f"transitioning to OPEN"
            )
            self._transition_to_open()
        elif self._state == CircuitState.HALF_OPEN:
            # HALF_OPEN 상태에서 실패하면 바로 OPEN으로 전환
            logger.warning("Circuit breaker: HALF_OPEN → OPEN transition (failure)")
            self._transition_to_open()

    def _transition_to_closed(self) -> None:
        """CLOSED 상태로 전환"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info("Circuit breaker: Transitioned to CLOSED")

    def _transition_to_open(self) -> None:
        """OPEN 상태로 전환"""
        self._state = CircuitState.OPEN
        self._last_failure_time = datetime.now(timezone.utc)
        self._half_open_calls = 0
        logger.warning(f"Circuit breaker: Transitioned to OPEN (failures: {self._failure_count})")

    def get_stats(self) -> dict:
        """
        서킷 브레이커 통계 정보 반환

        Returns:
            통계 정보 딕셔너리
        """
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "total_calls": self._total_calls,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
        }

    def reset(self) -> None:
        """서킷 브레이커 상태 리셋 (테스트 또는 수동 복구용)"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info("Circuit breaker: Manually reset to CLOSED")
