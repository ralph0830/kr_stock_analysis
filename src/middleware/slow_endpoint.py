"""
Slow Endpoint Tracker

느린 엔드포인트 추적 및 기록
"""
import time
import logging
from typing import Callable, Dict, List
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 느린 엔드포인트 기준 (초)
SLOW_ENDPOINT_THRESHOLD = 1.0


class SlowEndpointTracker:
    """느린 엔드포인트 추적"""

    def __init__(self, threshold: float = SLOW_ENDPOINT_THRESHOLD):
        self._threshold = threshold
        self._slow_calls: Dict[str, List[Dict]] = defaultdict(list)
        self._max_entries = 100  # 경로당 최대 저장 수

    @property
    def threshold(self) -> float:
        return self._threshold

    def record(self, path: str, method: str, duration: float, status_code: int) -> None:
        """느린 호출 기록"""
        if duration < self._threshold:
            return

        call_info = {
            "method": method,
            "duration": round(duration, 3),
            "status_code": status_code,
            "timestamp": time.time(),
        }

        # 최대 항목 수 제한
        path_key = f"{method} {path}"
        if len(self._slow_calls[path_key]) >= self._max_entries:
            self._slow_calls[path_key].pop(0)

        self._slow_calls[path_key].append(call_info)

        # 로그 기록
        logger.warning(
            f"Slow endpoint: {method} {path} - {duration:.3f}s (status: {status_code})"
        )

    def get_slow_endpoints(self, limit: int = 10) -> List[Dict]:
        """
        느린 엔드포인트 목록 반환

        Args:
            limit: 반환할 최대 항목 수

        Returns:
            느린 엔드포인트 목록
        """
        results = []

        for path_key, calls in self._slow_calls.items():
            if not calls:
                continue

            # 평균 응답 시간 계산
            avg_duration = sum(c["duration"] for c in calls) / len(calls)
            max_duration = max(c["duration"] for c in calls)
            count = len(calls)

            results.append({
                "path": path_key,
                "count": count,
                "avg_duration": round(avg_duration, 3),
                "max_duration": round(max_duration, 3),
                "last_call": calls[-1]["timestamp"],
            })

        # 평균 응답 시간 기준 정렬
        results.sort(key=lambda x: x["avg_duration"], reverse=True)

        return results[:limit]

    def clear(self) -> None:
        """기록 초기화"""
        self._slow_calls.clear()

    def to_dict(self, limit: int = 10) -> Dict:
        """통계 dict 반환"""
        return {
            "threshold": self._threshold,
            "slow_endpoints": self.get_slow_endpoints(limit),
        }


# 전역 인스턴스
_slow_endpoint_tracker = SlowEndpointTracker()


def get_slow_endpoint_tracker() -> SlowEndpointTracker:
    """전역 SlowEndpointTracker 인스턴스 반환"""
    return _slow_endpoint_tracker


class SlowEndpointMiddleware(BaseHTTPMiddleware):
    """
    느린 엔드포인트 추적 미들웨어

    지정된 임계값보다 느린 요청을 기록합니다.

    ## 사용법
    ```python
    app.add_middleware(SlowEndpointMiddleware, threshold=1.0)
    ```
    """

    def __init__(self, app, threshold: float = SLOW_ENDPOINT_THRESHOLD):
        super().__init__(app)
        self._threshold = threshold
        _slow_endpoint_tracker._threshold = threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 요청 처리
        response = await call_next(request)

        # 응답 시간 계산
        duration = time.time() - start_time

        # 느린 요청 기록
        path = request.url.path
        method = request.method
        status_code = response.status_code

        _slow_endpoint_tracker.record(path, method, duration, status_code)

        return response
