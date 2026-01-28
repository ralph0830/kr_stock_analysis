"""
API 메트릭 수집 미들웨어
요청/응답 시간 및 에러율 자동 수집
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.metrics import metrics_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# 메트릭 정의
api_requests_total = metrics_registry.counter(
    "api_requests_total",
    "Total API requests"
)

api_response_time = metrics_registry.histogram(
    "api_response_time_seconds",
    "API response time in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

api_errors_total = metrics_registry.counter(
    "api_errors_total",
    "Total API errors"
)

api_active_connections = metrics_registry.gauge(
    "api_active_connections",
    "Active API connections"
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    메트릭 수집 미들웨어

    모든 API 요청에 대해:
    - 요청 수 카운트
    - 응답 시간 기록
    - 에러 수 카운트
    - 활성 연결 수 추적
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        요청 처리 및 메트릭 수집

        Args:
            request: FastAPI Request
            call_next: 다음 미들웨어/라우터 핸들러

        Returns:
            Response
        """
        # 시작 시간 기록
        start_time = time.time()

        # 경로 추출 (엔드포인트 식별)
        path = request.url.path
        method = request.method

        # 활성 연결 수 증가
        api_active_connections.set(
            api_active_connections.get() + 1
        )

        try:
            # 요청 처리
            response = await call_next(request)

            # 응답 시간 계산
            duration = time.time() - start_time

            # 메트릭 기록
            api_requests_total.inc()
            api_response_time.observe(duration)

            # 에러 응답인 경우
            if response.status_code >= 400:
                api_errors_total.inc()

            # 요청 로깅
            logger.info(
                f"{method} {path} - {response.status_code}",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration": duration,
                }
            )

            return response

        except Exception as e:
            # 응답 시간 계산
            duration = time.time() - start_time

            # 에러 메트릭 기록
            api_requests_total.inc()
            api_errors_total.inc()
            api_response_time.observe(duration)

            # 에러 로깅
            logger.error(
                f"{method} {path} - Exception: {str(e)}",
                extra={
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "duration": duration,
                }
            )

            # 예외 재발생
            raise

        finally:
            # 활성 연결 수 감소
            api_active_connections.set(
                api_active_connections.get() - 1
            )


def get_path_label(request: Request) -> str:
    """
    요청 경로에서 라벨 생성

    Args:
        request: FastAPI Request

    Returns:
        경로 라벨 (예: "/api/kr/signals")
    """
    return request.url.path


def get_client_ip(request: Request) -> str:
    """
    클라이언트 IP 추출

    Args:
        request: FastAPI Request

    Returns:
        클라이언트 IP
    """
    # X-Forwarded-For 헤더 확인
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # 직접 연결 IP
    if request.client:
        return request.client.host

    return "unknown"
