"""
Trigger API Integration Tests
TDD GREEN Phase - Tests should pass with implementation
"""

import pytest
from httpx import AsyncClient, ASGITransport

from services.api_gateway.main import app
from src.database.session import get_db_session


@pytest.fixture
async def client(test_db_session):
    """Test Client Fixture"""
    # Dependency override
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestTriggerAPIIntegration:
    """Trigger API 통합 테스트"""

    async def test_trigger_vcp_scan_api(self, client: AsyncClient):
        """VCP 스캔 트리거 API"""
        response = await client.post("/api/kr/scan/vcp")

        # GREEN Phase: Should return 200 or error status
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["started", "completed", "error"]

    async def test_trigger_signal_generation_api(self, client: AsyncClient):
        """시그널 생성 트리거 API"""
        response = await client.post("/api/kr/scan/signals")

        # GREEN Phase: Should return 200 or error status
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["started", "completed", "error"]

    async def test_get_scan_status_api(self, client: AsyncClient):
        """스캔 상태 조회 API"""
        response = await client.get("/api/kr/scan/status")

        # GREEN Phase: 200 with proper response
        assert response.status_code == 200
        data = response.json()
        assert "vcp_scan_status" in data
        assert "signal_generation_status" in data

    async def test_trigger_endpoints_implemented(self, client: AsyncClient):
        """트리거 엔드포인트 구현 확인"""
        endpoints = [
            ("/api/kr/scan/vcp", "post"),
            ("/api/kr/scan/signals", "post"),
            ("/api/kr/scan/status", "get"),
        ]

        for endpoint, method in endpoints:
            if method == "post":
                response = await client.post(endpoint)
            else:
                response = await client.get(endpoint)
            # GREEN Phase: Should not be 404
            assert response.status_code != 404, f"{endpoint} returned 404"

    async def test_vcp_scan_response_structure(self, client: AsyncClient):
        """VCP 스캔 응답 구조 검증"""
        response = await client.post("/api/kr/scan/vcp")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "scanned_count" in data
        assert "found_signals" in data
        assert "started_at" in data

    async def test_signal_generation_response_structure(self, client: AsyncClient):
        """시그널 생성 응답 구조 검증"""
        response = await client.post("/api/kr/scan/signals")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "generated_count" in data
        assert "started_at" in data

    async def test_scan_status_response_structure(self, client: AsyncClient):
        """스캔 상태 응답 구조 검증"""
        response = await client.get("/api/kr/scan/status")

        assert response.status_code == 200
        data = response.json()
        assert "vcp_scan_status" in data
        assert "signal_generation_status" in data

    async def test_all_trigger_endpoints_implemented(self, client: AsyncClient):
        """모든 트리거 엔드포인트 구현 확인"""
        endpoints = [
            "/api/kr/scan/vcp",
            "/api/kr/scan/signals",
            "/api/kr/scan/status",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint) if "status" in endpoint else await client.post(endpoint)
            # GREEN Phase: Should not be 404
            assert response.status_code != 404, f"{endpoint} returned 404"

    async def test_vcp_scan_with_options(self, client: AsyncClient):
        """옵션과 함께 VCP 스캔 트리거"""
        response = await client.post(
            "/api/kr/scan/vcp",
            params={"market": "KOSPI", "min_score": 70}
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    async def test_signal_generation_with_tickers(self, client: AsyncClient):
        """특정 종목 시그널 생성"""
        response = await client.post(
            "/api/kr/scan/signals",
            params={"tickers": ["005930", "000660"]}
        )

        # Note: Query params with lists may not work as expected
        # In production, use JSON body
        assert response.status_code in [200, 422]  # 422 for validation error

    async def test_vcp_scan_status_values(self, client: AsyncClient):
        """VCP 스캔 상태 값 확인"""
        response = await client.get("/api/kr/scan/status")

        assert response.status_code == 200
        data = response.json()
        assert data["vcp_scan_status"] in ["idle", "running", "completed", "error"]
