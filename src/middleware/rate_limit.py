"""
Rate Limiting Middleware

Sliding Window 방식 요청 속도 제한
"""
import time
import logging
from typing import Callable, Optional, Dict
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding Window Rate Limiter

    IP별/Key별 요청 속도 제한

    ## 사용법
    ```python
    limiter = RateLimiter(requests=100, window=60)  # 60초에 100회

    # 요청 제한 확인
    if not limiter.is_allowed(client_id):
        raise HTTPException(status_code=429, detail="Too many requests")
    ```
    """

    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
    ):
        """
        Args:
            requests: 윈도우 내 허용 요청 수
            window: 윈도우 크기 (초)
        """
        self._requests = requests
        self._window = window
        # {client_id: deque([timestamp1, timestamp2, ...])}
        self._requests_history: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, client_id: str) -> bool:
        """
        요청 허용 여부 확인

        Args:
            client_id: 클라이언트 식별자 (IP 또는 API Key)

        Returns:
            허용 여부
        """
        now = time.time()
        history = self._requests_history[client_id]

        # 윈도우 내 요청만 유지
        while history and history[0] <= now - self._window:
            history.popleft()

        # 요청 수 확인
        if len(history) >= self._requests:
            return False

        # 현재 요청 기록
        history.append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """
        남은 요청 수 반환

        Args:
            client_id: 클라이언트 식별자

        Returns:
            남은 요청 수
        """
        now = time.time()
        history = self._requests_history[client_id]

        # 윈도우 내 요청만 유지
        while history and history[0] <= now - self._window:
            history.popleft()

        return max(0, self._requests - len(history))

    def reset(self, client_id: str) -> None:
        """클라이언트 기록 초기화"""
        if client_id in self._requests_history:
            del self._requests_history[client_id]

    def cleanup(self, older_than: float = 3600) -> int:
        """
        오래된 기록 정리

        Args:
            older_than: 이 시간보다 오래된 기록 삭제 (초)

        Returns:
            삭제된 클라이언트 수
        """
        now = time.time()
        removed = 0

        for client_id in list(self._requests_history.keys()):
            history = self._requests_history[client_id]

            if not history:
                del self._requests_history[client_id]
                removed += 1
                continue

            # 가장 오래된 기록 확인
            if history[0] < now - older_than:
                del self._requests_history[client_id]
                removed += 1

        return removed

    def to_dict(self) -> dict:
        """통계 dict 반환"""
        active_clients = len(self._requests_history)
        total_requests = sum(len(h) for h in self._requests_history.values())

        return {
            "requests_per_window": self._requests,
            "window_seconds": self._window,
            "active_clients": active_clients,
            "total_tracked_requests": total_requests,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting 미들웨어

    IP별/Key별 요청 속도 제한을 적용합니다.

    ## 사용법
    ```python
    # 기본 설정 (100회/60초)
    app.add_middleware(RateLimitMiddleware)

    # 엔드포인트별 설정
    app.add_middleware(
        RateLimitMiddleware,
        endpoint_limits={"/api/kr/signals": (10, 60)},
    )
    ```
    """

    # 엔드포인트별 제한 설정
    DEFAULT_LIMITS = {
        # 스캔/분석 엔드포인트는 더 엄격하게
        "/api/kr/scan": (10, 60),
        "/api/kr/signals": (50, 60),
        "/api/kr/ai-analyze": (5, 60),
        # 채팅은 더 관대적으로
        "/api/kr/chatbot/chat": (30, 60),
        # Daytrading API (단타 스캔/분석)
        "/api/daytrading/signals": (60, 60),  # 시그널 조회: 60회/분
        "/api/daytrading/scan": (10, 60),      # 시장 스캔: 10회/분
        "/api/daytrading/analyze": (30, 60),   # 종목 분석: 30회/분
    }

    def __init__(
        self,
        app,
        requests: int = 100,
        window: int = 60,
        excluded_paths: Optional[set[str]] = None,
        endpoint_limits: Optional[dict[str, tuple[int, int]]] = None,
    ):
        super().__init__(app)
        self._default_limiter = RateLimiter(requests, window)
        self._excluded_paths = excluded_paths or {"/", "/health", "/docs"}
        self._endpoint_limits = endpoint_limits or self.DEFAULT_LIMITS
        # {endpoint: RateLimiter}
        self._limiters: Dict[str, RateLimiter] = {}

    def _get_rate_limiter(self, path: str) -> RateLimiter:
        """경로별 Rate Limiter 반환"""
        # 정확히 일치하는 경로 확인
        if path in self._endpoint_limits:
            if path not in self._limiters:
                requests, window = self._endpoint_limits[path]
                self._limiters[path] = RateLimiter(requests, window)
            return self._limiters[path]

        # 접두사로 확인
        for endpoint, limit in self._endpoint_limits.items():
            if path.startswith(endpoint):
                if endpoint not in self._limiters:
                    requests, window = limit
                    self._limiters[endpoint] = RateLimiter(requests, window)
                return self._limiters[endpoint]

        # 기본 limiter 사용
        return self._default_limiter

    def _get_client_id(self, request: Request) -> str:
        """클라이언트 식별자 반환"""
        # API Key가 있으면 API Key 사용
        api_key = getattr(request.state, "api_key", None)
        if api_key:
            return f"key:{api_key.key}"

        # IP 주소 사용
        # X-Forwarded-For 헤더가 있으면 사용 (프록시 환경)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        # client 호스트 사용
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _is_public_path(self, path: str) -> bool:
        """공개 경로 확인"""
        if path in self._excluded_paths:
            return True

        for public_path in self._excluded_paths:
            if path.startswith(public_path):
                return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # 공개 경로는 통과
        if self._is_public_path(path):
            return await call_next(request)

        # Rate Limiter 확인
        limiter = self._get_rate_limiter(path)
        client_id = self._get_client_id(request)

        if not limiter.is_allowed(client_id):
            remaining = limiter.get_remaining(client_id)
            reset_time = int(time.time() + self._default_limiter._window)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many requests",
                    "remaining": remaining,
                    "reset_at": reset_time,
                },
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(self._default_limiter._window),
                },
            )

        # 요청 처리
        response = await call_next(request)

        # Rate Limit 정보 헤더 추가
        remaining = limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(limiter._requests)

        return response


# 전역 Rate Limiter 인스턴스
_global_rate_limiter = RateLimiter(requests=100, window=60)


def get_rate_limiter() -> RateLimiter:
    """전역 Rate Limiter 반환"""
    return _global_rate_limiter
