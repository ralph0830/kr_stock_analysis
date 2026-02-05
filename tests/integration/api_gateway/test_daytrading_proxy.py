"""
Daytrading Scanner Proxy Tests
API Gateway → Daytrading Scanner 프록시 테스트
"""

import pytest
import httpx
from fastapi import testclient

# =============================================================================
# Test Daytrading Proxy Routes
# =============================================================================

class TestDaytradingProxy:
    """Daytrading 프록시 라우팅 테스트"""

    @pytest.fixture
    def app(self):
        """FastAPI 앱 fixture"""
        from services.api_gateway.main import app
        return app

    @pytest.fixture
    def client(self, app):
        """Test client fixture"""
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_daytrading_signals_proxy_200ok(self, client, monkeypatch):
        """GET /api/daytrading/signals → 200 OK"""
        # Mock httpx.AsyncClient
        async def mock_get(*args, **kwargs):
            class MockResponse:
                status_code = 200
                def raise_for_status(self):
                    pass
                def json(self):
                    return {
                        "success": True,
                        "data": {
                            "signals": [
                                {
                                    "ticker": "005930",
                                    "name": "삼성전자",
                                    "total_score": 90,
                                    "grade": "S",
                                    "market": "KOSPI"
                                }
                            ],
                            "count": 1
                        }
                    }
            return MockResponse()

        # httpx 모킹
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        response = client.get("/api/daytrading/signals?min_score=60&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "signals" in data

    def test_daytrading_scan_proxy_200ok(self, client, monkeypatch):
        """POST /api/daytrading/scan → 200 OK"""
        # Mock httpx.AsyncClient
        async def mock_post(*args, **kwargs):
            class MockResponse:
                status_code = 200
                def raise_for_status(self):
                    pass
                def json(self):
                    return {
                        "success": True,
                        "data": {
                            "candidates": [
                                {
                                    "ticker": "005930",
                                    "name": "삼성전자",
                                    "total_score": 90,
                                    "grade": "S"
                                }
                            ],
                            "count": 1
                        }
                    }
            return MockResponse()

        # httpx 모킹
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        response = client.post(
            "/api/daytrading/scan",
            json={"market": "KOSPI", "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "candidates" in data

    def test_daytrading_analyze_proxy_200ok(self, client, monkeypatch):
        """POST /api/daytrading/analyze → 200 OK"""
        # Mock httpx.AsyncClient
        async def mock_post(*args, **kwargs):
            class MockResponse:
                status_code = 200
                def raise_for_status(self):
                    pass
                def json(self):
                    return {
                        "success": True,
                        "data": {
                            "results": [
                                {
                                    "ticker": "005930",
                                    "name": "삼성전자",
                                    "total_score": 90,
                                    "grade": "S"
                                }
                            ],
                            "count": 1
                        }
                    }
            return MockResponse()

        # httpx 모킹
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        response = client.post(
            "/api/daytrading/analyze",
            json={"tickers": ["005930"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "results" in data

    def test_vcp_paths_still_work(self, client):
        """기존 VCP 경로 정상 동작 확인"""
        # VCP 시그널 엔드포인트는 service 없이 503을 반환할 수 있음
        # 중요한 것은 경로가 등록되어 있다는 것
        response = client.get("/api/kr/signals?limit=10")
        # service unavailable이면 503, 정상이면 200
        assert response.status_code in [200, 503]


# =============================================================================
# Test Service Discovery
# =============================================================================

class TestDaytradingServiceDiscovery:
    """Daytrading 서비스 발견 테스트"""

    @pytest.fixture
    def registry(self):
        """Service Registry fixture"""
        from services.api_gateway.service_registry import get_registry
        return get_registry()

    def test_daytrading_scanner_in_registry(self, registry):
        """Service Registry에 daytrading-scanner 등록됨"""
        service = registry.get_service("daytrading-scanner")
        assert service is not None
        assert service["name"] == "daytrading-scanner"
        assert "url" in service
        assert "health_check_url" in service

    def test_daytrading_scanner_url_format(self, registry):
        """Daytrading Scanner URL 형식 확인"""
        service = registry.get_service("daytrading-scanner")
        # URL이 http://localhost:5115 또는 http://daytrading-scanner:5115 형식
        assert "5115" in service["url"] or "daytrading" in service["url"]


# =============================================================================
# Test Proxy Error Handling
# =============================================================================

class TestDaytradingProxyErrors:
    """Daytrading 프록시 에러 처리 테스트"""

    @pytest.fixture
    def app(self):
        """FastAPI 앱 fixture"""
        from services.api_gateway.main import app
        return app

    @pytest.fixture
    def client(self, app):
        """Test client fixture"""
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_service_unavailable_returns_503(self, client, monkeypatch):
        """서비스 unavailable → 503"""
        # httpx 연결 실패 모킹 (서비스 다운 시나리오)
        class MockRequestError(httpx.RequestError):
            pass

        class FailingAsyncClient:
            """연결 실패를 시뮬레이션하는 Mock AsyncClient"""
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, *args, **kwargs):
                raise MockRequestError("Service unavailable")

            async def post(self, *args, **kwargs):
                raise MockRequestError("Service unavailable")

        # daytrading 라우터의 httpx.AsyncClient를 모킹
        import services.api_gateway.routes.daytrading as daytrading_module
        monkeypatch.setattr(
            daytrading_module.httpx,
            "AsyncClient",
            FailingAsyncClient
        )

        response = client.get("/api/daytrading/signals")

        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data.get("detail", "").lower()
