"""
System API Integration Tests
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


class TestSystemAPIIntegration:
    """System API 통합 테스트"""

    async def test_data_status_api(self, client: AsyncClient):
        """데이터 상태 조회 API"""
        response = await client.get("/api/system/data-status")

        # GREEN Phase: 200 with proper response
        assert response.status_code == 200
        data = response.json()
        assert "total_stocks" in data
        assert "updated_stocks" in data
        assert "data_files" in data

    async def test_system_health_api(self, client: AsyncClient):
        """시스템 헬스 체크 API"""
        response = await client.get("/api/system/health")

        # GREEN Phase: 200 with proper response
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    async def test_update_data_stream_api(self, client: AsyncClient):
        """데이터 업데이트 SSE 스트림 API"""
        response = await client.post("/api/system/update-data-stream")

        # GREEN Phase: 200 with streaming response
        assert response.status_code == 200

    async def test_data_status_response_structure(self, client: AsyncClient):
        """데이터 상태 응답 구조 검증"""
        response = await client.get("/api/system/data-status")

        assert response.status_code == 200
        data = response.json()
        assert "total_stocks" in data
        assert isinstance(data["total_stocks"], int)
        assert "updated_stocks" in data
        assert isinstance(data["updated_stocks"], int)
        assert "data_files" in data
        assert isinstance(data["data_files"], dict)

    async def test_system_health_response_structure(self, client: AsyncClient):
        """시스템 헬스 응답 구조 검증"""
        response = await client.get("/api/system/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "services" in data
        assert isinstance(data["services"], dict)
        assert "timestamp" in data
        assert "database_status" in data
        assert "redis_status" in data

    async def test_all_system_endpoints_implemented(self, client: AsyncClient):
        """모든 시스템 엔드포인트 구현 확인"""
        endpoints = [
            "/api/system/data-status",
            "/api/system/health",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            # GREEN Phase: Should not be 404
            assert response.status_code != 404, f"{endpoint} returned 404"

    async def test_data_status_includes_prices(self, client: AsyncClient):
        """데이터 상태에 주가 정보 포함 확인"""
        response = await client.get("/api/system/data-status")

        assert response.status_code == 200
        data = response.json()
        assert "data_files" in data
        # 주가 데이터 상태 확인
        assert "prices" in data["data_files"]

    async def test_system_health_includes_database(self, client: AsyncClient):
        """시스템 헬스에 데이터베이스 상태 포함 확인"""
        response = await client.get("/api/system/health")

        assert response.status_code == 200
        data = response.json()
        assert "database_status" in data
        assert data["database_status"] in ["up", "down"]

    async def test_system_health_includes_redis(self, client: AsyncClient):
        """시스템 헬스에 Redis 상태 포함 확인"""
        response = await client.get("/api/system/health")

        assert response.status_code == 200
        data = response.json()
        assert "redis_status" in data
        assert data["redis_status"] in ["up", "down"]

    async def test_data_status_details(self, client: AsyncClient):
        """데이터 상태 상세 정보 확인"""
        response = await client.get("/api/system/data-status")

        assert response.status_code == 200
        data = response.json()
        assert "details" in data
        assert isinstance(data["details"], list)
