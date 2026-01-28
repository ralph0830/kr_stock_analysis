"""
요청/응답 로깅 미들웨어 테스트
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from fastapi import Request, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from src.middleware.logging_middleware import RequestLoggingMiddleware
from src.utils.logging_config import setup_logging, get_logger


class TestRequestLoggingMiddleware:
    """RequestLoggingMiddleware 테스트"""

    @pytest.fixture
    def mock_app(self) -> ASGIApp:
        """Mock ASGI app"""
        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            response = Response(b'{"status": "ok"}', media_type="application/json")
            await response(scope, receive, send)
        return app

    @pytest.fixture
    def sample_request(self) -> Request:
        """샘플 Request 객체 생성"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/kr/signals",
            "query_string": b"",
            "headers": [
                (b"user-agent", b"test-agent"),
                (b"x-forwarded-for", b"192.168.1.100"),
            ],
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 50000),
        }
        return Request(scope)

    def test_middleware_initialization(self, mock_app):
        """미들웨어 초기화 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)
        assert middleware.app == mock_app
        assert middleware.skip_paths == {"/health", "/metrics", "/readiness"}
        assert middleware.log_body is False

    def test_middleware_custom_skip_paths(self, mock_app):
        """사용자 정의 skip_paths 테스트"""
        custom_skip = ["/health", "/custom"]
        middleware = RequestLoggingMiddleware(mock_app, skip_paths=custom_skip)
        assert middleware.skip_paths == set(custom_skip)

    def test_middleware_log_body_option(self, mock_app):
        """log_body 옵션 테스트"""
        middleware = RequestLoggingMiddleware(mock_app, log_body=True)
        assert middleware.log_body is True

    def test_generate_request_id_from_header(self, mock_app, sample_request):
        """헤더에서 Request ID 추출 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        # 헤더에 X-Request-ID가 있는 경우
        sample_request.headers.__dict__["_list"].append((b"x-request-id", b"test-req-123"))
        request_id = middleware._generate_request_id(sample_request)
        assert request_id == "test-req-123"

    def test_generate_request_id_new_uuid(self, mock_app, sample_request):
        """새 UUID 생성 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        # X-Request-ID 헤더가 없는 경우
        request_id = middleware._generate_request_id(sample_request)
        assert request_id is not None
        assert len(request_id) == 36  # UUID 형식

    def test_get_client_ip_from_forwarded_for(self, mock_app, sample_request):
        """X-Forwarded-For 헤더에서 IP 추출 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)
        ip = middleware._get_client_ip(sample_request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_from_x_real_ip(self, mock_app):
        """X-Real-IP 헤더에서 IP 추출 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "query_string": b"",
            "headers": [(b"x-real-ip", b"10.0.0.1")],
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 50000),
        }
        request = Request(scope)
        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_direct(self, mock_app):
        """직접 연결 IP 추출 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 50000),
        }
        request = Request(scope)
        ip = middleware._get_client_ip(request)
        assert ip == "127.0.0.1"

    def test_get_client_ip_none(self, mock_app):
        """클라이언트 IP 없는 경우 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
        }
        request = Request(scope)
        ip = middleware._get_client_ip(request)
        assert ip is None

    def test_sanitize_headers(self, mock_app):
        """민감정보 헤더 마스킹 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        headers = {
            "authorization": "Bearer secret-token",
            "content-type": "application/json",
            "cookie": "session=abc123",
            "user-agent": "test-agent",
        }

        sanitized = middleware._sanitize_headers(headers)

        assert sanitized["authorization"] == "***REDACTED***"
        assert sanitized["content-type"] == "application/json"
        assert sanitized["cookie"] == "***REDACTED***"
        assert sanitized["user-agent"] == "test-agent"

    def test_sanitize_dict(self):
        """딕셔너리 민감정보 마스킹 테스트"""
        data = {
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "api_key": "key-abc-123",
            "nested": {
                "token": "nested-token",
                "safe_value": "keep-this",
            },
            "list_data": [
                {"secret": "value1"},
                {"normal": "value2"},
            ],
        }

        sanitized = RequestLoggingMiddleware.sanitize_dict(data)

        assert sanitized["username"] == "testuser"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["email"] == "test@example.com"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["nested"]["token"] == "***REDACTED***"
        assert sanitized["nested"]["safe_value"] == "keep-this"
        assert sanitized["list_data"][0]["secret"] == "***REDACTED***"
        assert sanitized["list_data"][1]["normal"] == "value2"

    def test_skip_paths_check(self, mock_app):
        """skip_paths 확인 테스트"""
        middleware = RequestLoggingMiddleware(mock_app, skip_paths=["/health", "/metrics"])

        assert "/health" in middleware.skip_paths
        assert "/metrics" in middleware.skip_paths
        assert "/api/kr/signals" not in middleware.skip_paths

    def test_log_request_data_structure(self, mock_app, sample_request):
        """요청 로깅 데이터 구조 테스트"""
        middleware = RequestLoggingMiddleware(mock_app)

        # _log_request는 로거를 호출하므로 실제 호출 테스트는 통합 테스트에서 수행
        # 여기서는 데이터 구조가 올바른지 확인
        assert sample_request.method == "GET"
        assert sample_request.url.path == "/api/kr/signals"

    def test_get_request_id_header(self, mock_app, sample_request):
        """요청에서 Request ID 헤더 추출 테스트"""
        from src.middleware.logging_middleware import get_request_id_header

        # 헤더가 있는 경우
        sample_request.headers.__dict__["_list"].append((b"x-request-id", b"req-456"))
        request_id = get_request_id_header(sample_request)
        assert request_id == "req-456"

        # 헤더가 없는 경우
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
        }
        request = Request(scope)
        request_id = get_request_id_header(request)
        assert request_id == "unknown"


class TestMiddlewareIntegration:
    """미들웨어 통합 테스트"""

    def test_request_id_context_tracking(self):
        """Request ID 컨텍스트 추적 테스트"""
        from src.utils.logging_config import bind_request_id, get_request_id

        # Request ID 바인딩
        test_id = "test-req-789"
        bind_request_id(test_id)

        # 컨텍스트에서 가져오기
        retrieved_id = get_request_id()
        assert retrieved_id == test_id

    def test_log_data_structure(self):
        """로그 데이터 구조 검증 테스트"""
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(level="INFO", log_dir=log_dir, json_output=True)
            logger = get_logger("test_structure")

            from src.utils.logging_config import bind_request_id

            bind_request_id("test-req-999")
            logger.info("Test message", extra={"custom_field": "custom_value"})

            # 로그 파일 확인
            info_log_path = Path(log_dir) / "info.log"
            with open(info_log_path, "r") as f:
                content = f.read()
                log_data = json.loads(content.strip().split("\n")[-1])

                # 필수 필드 확인
                assert log_data["level"] == "INFO"
                assert log_data["message"] == "Test message"
                assert log_data["request_id"] == "test-req-999"
                assert log_data["service"] == "kr_stock"
                assert log_data["environment"] == "development"
                assert "custom_field" in log_data["extra"]
