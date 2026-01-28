"""
Rate Limiter (속도 제한)
슬라이딩 윈도우 알고리즘 기반 요청 속도 제한
"""

import time
from typing import Dict, Optional
from collections import deque
from datetime import datetime, timedelta


class RateLimiter:
    """
    Rate Limiter (슬라이딩 윈도우)

    Args:
        max_requests: 최대 요청 수
        window_seconds: 시간 윈도우 (초)
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # 요청 기록 (타임스탬프 큐)
        self._requests: deque = deque()

        # 현재 카운트
        self._count = 0

    def _clean_old_requests(self) -> None:
        """윈도우에서 벗어난 오래된 요청 제거"""
        now = time.time()
        cutoff = now - self.window_seconds

        # 오래된 요청 제거
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
            self._count -= 1

    def is_allowed(self) -> bool:
        """
        요청 허용 여부 확인

        Returns:
            True면 요청 허용, False면 제한
        """
        self._clean_old_requests()

        if self._count < self.max_requests:
            # 요청 기록
            self._requests.append(time.time())
            self._count += 1
            return True

        return False

    def get_reset_time(self) -> float:
        """
        제한 해제 시간 반환

        Returns:
            제한이 해제되는 시간 (Unix timestamp)
        """
        if not self._requests:
            return time.time()

        # 가장 오래된 요청 + 윈도우 시간
        return self._requests[0] + self.window_seconds

    def get_remaining_requests(self) -> int:
        """
        남은 요청 수 반환

        Returns:
            남은 요청 수
        """
        self._clean_old_requests()
        return max(0, self.max_requests - self._count)

    def reset(self) -> None:
        """Rate Limiter 리셋"""
        self._requests.clear()
        self._count = 0


class RateLimiterRegistry:
    """
    Rate Limiter 레지스트리

    여러 클라이언트(IP 또는 API Key)별로 Rate Limiter 관리

    Usage:
        registry = RateLimiterRegistry()

        # IP별 Rate Limiting (default: 100 requests/hour)
        if registry.is_allowed("192.168.1.1"):
            # 요청 처리
            pass

        # API Key별 Rate Limiting (custom limit)
        if registry.is_allowed("api_key_123", max_requests=1000):
            # 요청 처리
            pass
    """

    def __init__(self, default_max_requests: int = 100, default_window_seconds: int = 3600):
        self.default_max_requests = default_max_requests
        self.default_window_seconds = default_window_seconds

        # client_id -> RateLimiter 매핑
        self._limiters: Dict[str, RateLimiter] = {}

    def _get_limiter(
        self,
        client_id: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> RateLimiter:
        """Rate Limiter 가져오기 또는 생성"""
        if client_id not in self._limiters:
            max_req = max_requests or self.default_max_requests
            window_sec = window_seconds or self.default_window_seconds
            self._limiters[client_id] = RateLimiter(max_req, window_sec)

        return self._limiters[client_id]

    def is_allowed(
        self,
        client_id: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> bool:
        """
        요청 허용 여부 확인

        Args:
            client_id: 클라이언트 식별자 (IP, API Key 등)
            max_requests: 최대 요청 수 (None이면 기본값 사용)
            window_seconds: 시간 윈도우 (None이면 기본값 사용)

        Returns:
            True면 요청 허용, False면 제한
        """
        limiter = self._get_limiter(client_id, max_requests, window_seconds)
        return limiter.is_allowed()

    def get_remaining_requests(self, client_id: str) -> int:
        """
        남은 요청 수 반환

        Args:
            client_id: 클라이언트 식별자

        Returns:
            남은 요청 수
        """
        limiter = self._limiters.get(client_id)
        if limiter:
            return limiter.get_remaining_requests()
        return self.default_max_requests

    def get_reset_time(self, client_id: str) -> Optional[float]:
        """
        제한 해제 시간 반환

        Args:
            client_id: 클라이언트 식별자

        Returns:
            제한 해제 시간 (Unix timestamp)
        """
        limiter = self._limiters.get(client_id)
        if limiter:
            return limiter.get_reset_time()
        return None

    def reset(self, client_id: str) -> bool:
        """
        특정 클라이언트의 Rate Limiter 리셋

        Args:
            client_id: 클라이언트 식별자

        Returns:
            성공 여부
        """
        if client_id in self._limiters:
            self._limiters[client_id].reset()
            return True
        return False

    def reset_all(self) -> None:
        """모든 Rate Limiter 리셋"""
        self._limiters.clear()


# 전역 Rate Limiter 레지스트리
rate_limiter_registry = RateLimiterRegistry()


class RateLimitExceeded(Exception):
    """Rate Limit 초과 예외"""

    def __init__(self, retry_after: float = 0):
        """
        Args:
            retry_after: 재시도 가능 시간 (초)
        """
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.1f} seconds.")
