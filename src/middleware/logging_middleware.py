"""
요청/응답 로깅 미들웨어
모든 HTTP 요청과 응답을 구조화된 JSON 형식으로 로깅합니다.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.utils.logging_config import bind_request_id, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    요청/응답 로깅 미들웨어

    기능:
    - 요청 ID 생성 및 추적
    - 요청/응답 시간 측정
    - 상태 코드별 로그 레벨 분리
    - 민감정보 마스킹 (비밀번호, 토큰 등)
    """

    # 민감정보 마스킹 대상 헤더 및 필드
    SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}
    SENSITIVE_FIELDS = {"password", "passwd", "secret", "token", "api_key"}

    def __init__(
        self,
        app: ASGIApp,
        skip_paths: list[str] | None = None,
        log_body: bool = False,
    ) -> None:
        """
        Args:
            app: ASGI 애플리케이션
            skip_paths: 로깅을 건너뛸 경로 목록 (health 등)
            log_body: 요청/응답 바디 로깅 여부
        """
        super().__init__(app)
        self.skip_paths = set(skip_paths or ["/health", "/metrics", "/readiness"])
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 전후로 로깅"""
        # WebSocket 요청은 미들웨어 처리 건너뛰기
        # BaseHTTPMiddleware는 WebSocket 연결을 제대로 처리하지 못함
        if self._is_websocket_request(request):
            return await call_next(request)

        # 요청 ID 생성 및 바인딩
        request_id = self._generate_request_id(request)
        bind_request_id(request_id)

        # 건너뛸 경로 체크
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # 요청 시작 시간
        start_time = time.time()

        # 요청 정보 로깅
        self._log_request(request, request_id)

        try:
            # 요청 처리
            response = await call_next(request)

            # 처리 시간 계산
            process_time = time.time() - start_time

            # 응답 로깅
            self._log_response(request, response, request_id, process_time)

            # Request ID를 응답 헤더에 추가
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # 예외 로깅
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client": self._get_client_ip(request),
                    "process_time": process_time,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _generate_request_id(self, request: Request) -> str:
        """요청 ID 생성 (헤더에 있으면 사용, 없으면 UUID 생성)"""
        existing_id = request.headers.get("X-Request-ID")
        if existing_id:
            return existing_id
        return str(uuid.uuid4())

    def _log_request(self, request: Request, request_id: str) -> None:
        """요청 정보 로깅"""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else None,
            "client": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "headers": self._sanitize_headers(dict(request.headers)),
        }

        # 바디 로깅 (활성화된 경우)
        if self.log_body and request.method in {"POST", "PUT", "PATCH"}:
            # 바디는 스트림이므로 로깅하면 소모됨 - 주의 필요
            pass  # 구현 필요 시 추가

        logger.info("Incoming request", extra=log_data)

    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        process_time: float,
    ) -> None:
        """응답 정보 로깅"""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "response_size": response.headers.get("content-length"),
        }

        # 상태 코드에 따른 로그 레벨 분리
        if response.status_code >= 500:
            logger.error("Request completed with server error", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Request completed with client error", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)

    def _get_client_ip(self, request: Request) -> str | None:
        """클라이언트 IP 주소 추출 (프록시 환경 고려)"""
        # 프록시 헤더 체크
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 직접 연결의 경우
        if request.client:
            return request.client.host

        return None

    def _sanitize_headers(self, headers: dict) -> dict:
        """민감정보가 포함된 헤더 마스킹"""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized

    def _is_websocket_request(self, request: Request) -> bool:
        """WebSocket 요청인지 확인"""
        # 경로로 확인
        if request.url.path.startswith("/ws"):
            return True
        # 헤더로 확인
        upgrade_header = request.headers.get("upgrade", "").lower()
        return upgrade_header == "websocket"

    @staticmethod
    def sanitize_dict(data: dict) -> dict:
        """딕셔너리 내 민감정보 마스킹"""
        sanitized = {}
        for key, value in data.items():
            if key.lower() in RequestLoggingMiddleware.SENSITIVE_FIELDS:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = RequestLoggingMiddleware.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    RequestLoggingMiddleware.sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


def get_request_id_header(request: Request) -> str:
    """요청에서 Request ID 헤더 값을 가져오는 헬퍼 함수"""
    return request.headers.get("X-Request-ID", "unknown")
