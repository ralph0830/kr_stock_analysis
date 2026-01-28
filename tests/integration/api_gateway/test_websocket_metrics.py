"""
API Gateway 통합 테스트
WebSocket 및 메트릭 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient

from services.api_gateway.main import app


class TestAPIGatewayWebSocket:
    """API Gateway WebSocket 통합 테스트"""

    def test_websocket_route_included(self):
        """WebSocket 라우터 포함 테스트"""
        routes = [route.path for route in app.routes]
        assert "/ws" in routes
        assert "/ws/stats" in routes


class TestAPIGatewayMetrics:
    """API Gateway 메트릭 엔드포인트 테스트"""

    def test_prometheus_metrics_endpoint(self):
        """Prometheus 메트릭 엔드포인트 테스트"""
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        # Prometheus 형식 확인
        content = response.text
        assert "# HELP" in content or content == ""  # 비어있을 수 있음

    def test_json_metrics_endpoint(self):
        """JSON 메트릭 엔드포인트 테스트"""
        client = TestClient(app)

        response = client.get("/api/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # JSON 구조 확인
        metrics = response.json()
        assert isinstance(metrics, dict)

    def test_reset_metrics_endpoint(self):
        """메트릭 리셋 엔드포인트 테스트"""
        client = TestClient(app)

        response = client.post("/api/metrics/reset")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestAPIGatewayHealth:
    """API Gateway 헬스 체크 테스트"""

    def test_health_check(self):
        """헬스 체크 엔드포인트 테스트"""
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"

    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestAPIGatewayRoutes:
    """API Gateway 라우트 테스트"""

    def test_signals_route_exists(self):
        """시그널 라우트 존재 테스트"""
        routes = [route.path for route in app.routes]
        assert "/api/kr/signals" in routes

    def test_market_gate_route_exists(self):
        """Market Gate 라우트 존재 테스트"""
        routes = [route.path for route in app.routes]
        assert "/api/kr/market-gate" in routes

    def test_jongga_v2_route_exists(self):
        """종가베팅 V2 라우트 존재 테스트"""
        routes = [route.path for route in app.routes]
        assert "/api/kr/jongga-v2/latest" in routes
