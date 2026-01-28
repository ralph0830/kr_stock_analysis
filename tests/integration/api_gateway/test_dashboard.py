"""
대시보드 API 통합 테스트
"""

import pytest
from fastapi.testclient import TestClient

from services.api_gateway.main import app


class TestDashboardOverview:
    """대시보드 개요 엔드포인트 테스트"""

    def test_system_overview(self):
        """시스템 상태 개요 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert "services" in data
        assert isinstance(data["services"], dict)


class TestDashboardMetrics:
    """대시보드 메트릭 엔드포인트 테스트"""

    def test_get_metrics_all(self):
        """전체 메트릭 조회 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert "total" in data
        assert "filtered" in data
        assert isinstance(data["metrics"], list)

    def test_get_metrics_by_type_counter(self):
        """Counter 타입 메트릭 필터링 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/metrics?metric_type=counter")
        assert response.status_code == 200

        data = response.json()
        assert all(m.get("type") == "counter" for m in data["metrics"])

    def test_get_metrics_with_limit(self):
        """메트릭 조회 제한 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/metrics?limit=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["metrics"]) <= 2


class TestDashboardConnections:
    """대시보드 연결 상태 엔드포인트 테스트"""

    def test_get_connection_info(self):
        """연결 정보 조회 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/connections")
        assert response.status_code == 200

        data = response.json()
        assert "active_connections" in data
        assert "subscriptions" in data
        assert "broadcaster_running" in data
        assert isinstance(data["subscriptions"], dict)


class TestDashboardSignals:
    """대시보드 시그널 엔드포인트 테스트"""

    def test_get_signal_summary(self):
        """시그너 요약 조회 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/signals")
        assert response.status_code == 200

        data = response.json()
        assert "total_signals" in data
        assert "active_signals" in data
        assert "latest_signals" in data
        assert isinstance(data["latest_signals"], list)

    def test_get_signal_summary_with_limit(self):
        """시그널 요약 조회 제한 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/signals?limit=3")
        assert response.status_code == 200

        data = response.json()
        assert len(data["latest_signals"]) <= 3


class TestDashboardHealth:
    """대시보드 헬스 체크 테스트"""

    def test_dashboard_health(self):
        """대시보드 헬스 체크 테스트"""
        client = TestClient(app)

        response = client.get("/api/dashboard/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "checks" in data
        assert "timestamp" in data

        # 필수 체크 항목 확인
        assert "metrics" in data["checks"]
        assert "websocket" in data["checks"]
        assert "service_registry" in data["checks"]
