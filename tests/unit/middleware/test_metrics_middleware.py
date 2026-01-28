"""
메트릭 수집 미들웨어 테스트
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import Request, Response
from starlette.datastructures import Headers

from src.middleware.metrics_middleware import (
    MetricsMiddleware,
    api_requests_total,
    api_response_time,
    api_errors_total,
    api_active_connections,
)
from src.utils.metrics import metrics_registry


@pytest.fixture(autouse=True)
def reset_metrics():
    """각 테스트 전에 메트릭 리셋"""
    metrics_registry.reset_all()
    yield


class TestMetricsMiddleware:
    """MetricsMiddleware 테스트"""

    @pytest.mark.asyncio
    async def test_successful_request_metrics(self):
        """성공 요청 메트릭 테스트"""
        middleware = MetricsMiddleware(app=None)

        # Mock Request
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = Headers({})

        # Mock call_next
        response = MagicMock(spec=Response)
        response.status_code = 200

        async def call_next(req):
            return response

        # 실행
        result = await middleware.dispatch(request, call_next)

        # 메트릭 검증
        assert api_requests_total.get() >= 1
        assert api_errors_total.get() == 0  # 에러 없음
        assert api_active_connections.get() == 0  # finally로 감소됨

    @pytest.mark.asyncio
    async def test_error_request_metrics(self):
        """에러 요청 메트릭 테스트"""
        middleware = MetricsMiddleware(app=None)

        # Mock Request
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.method = "POST"
        request.headers = Headers({})

        # Mock call_next - 예외 발생
        async def call_next(req):
            raise ValueError("Test error")

        # 실행 - 예외가 발생해야 함
        with pytest.raises(ValueError):
            await middleware.dispatch(request, call_next)

        # 메트릭 검증
        assert api_requests_total.get() >= 1
        assert api_errors_total.get() >= 1  # 에러 카운트 증가
        assert api_active_connections.get() == 0

    @pytest.mark.asyncio
    async def test_response_time_metric(self):
        """응답 시간 메트릭 테스트"""
        middleware = MetricsMiddleware(app=None)

        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = Headers({})

        response = MagicMock(spec=Response)
        response.status_code = 200

        async def call_next(req):
            return response

        # 실행
        await middleware.dispatch(request, call_next)

        # 응답 시간 메트릭 확인
        data = api_response_time.get()
        assert data["count"] >= 1  # 최소 1회 관측

    @pytest.mark.asyncio
    async def test_active_connections_tracking(self):
        """활성 연결 수 추적 테스트"""
        middleware = MetricsMiddleware(app=None)

        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = Headers({})

        response = MagicMock(spec=Response)
        response.status_code = 200

        async def call_next(req):
            # 미들웨어 내에서 연결 수 증가됨
            assert api_active_connections.get() >= 1
            return response

        # 실행 전
        initial = api_active_connections.get()
        await middleware.dispatch(request, call_next)

        # 실행 후 - 원래대로 복귀
        assert api_active_connections.get() == initial


class TestMetricsIntegration:
    """메트릭 통합 테스트"""

    def test_metrics_registry_integration(self):
        """메트릭 레지스트리 통합 테스트"""
        # 메트릭이 레지스트리에 등록되었는지 확인
        metrics = metrics_registry.get_all_metrics()

        assert "api_requests_total" in metrics
        assert "api_response_time_seconds" in metrics  # Histogram 이름에 _seconds 추가됨
        assert "api_errors_total" in metrics
        assert "api_active_connections" in metrics

        # 메트릭 타입 확인
        assert metrics["api_requests_total"]["type"] == "counter"
        assert metrics["api_response_time_seconds"]["type"] == "histogram"
        assert metrics["api_errors_total"]["type"] == "counter"
        assert metrics["api_active_connections"]["type"] == "gauge"

    def test_metrics_prometheus_format(self):
        """Prometheus 형식 내보내기 테스트"""
        export = metrics_registry.export()

        # 메트릭 포함 확인
        assert "# TYPE api_requests_total counter" in export
        assert "# TYPE api_response_time_seconds histogram" in export  # 수정
        assert "# TYPE api_errors_total counter" in export
        assert "# TYPE api_active_connections gauge" in export


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""

    def test_get_path_label(self):
        """경로 라벨 추출 테스트"""
        from src.middleware.metrics_middleware import get_path_label

        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/kr/signals"
        request.method = "GET"

        label = get_path_label(request)
        assert label == "/api/kr/signals"

    def test_get_client_ip(self):
        """클라이언트 IP 추출 테스트"""
        from src.middleware.metrics_middleware import get_client_ip

        # X-Forwarded-For 헤더 있는 경우
        request = MagicMock(spec=Request)
        request.headers = Headers({"x-forwarded-for": "192.168.1.1, 10.0.0.1"})
        request.client = None

        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

        # 직접 연결 IP
        request2 = MagicMock(spec=Request)
        request2.headers = Headers({})
        request2.client = MagicMock()
        request2.client.host = "127.0.0.1"

        ip2 = get_client_ip(request2)
        assert ip2 == "127.0.0.1"

        # 알 수 없는 경우
        request3 = MagicMock(spec=Request)
        request3.headers = Headers({})
        request3.client = None

        ip3 = get_client_ip(request3)
        assert ip3 == "unknown"
