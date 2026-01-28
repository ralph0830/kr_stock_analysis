"""
Test Suite: API Gateway (GREEN Phase)
작성 목적: FastAPI 기반 API Gateway 구현 후 테스트
예상 결과: PASS - API Gateway 구현 완료
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch

from services.api_gateway.main import app
from services.api_gateway.service_registry import ServiceRegistry, get_registry


class TestAPIGatewayRouting:
    """API Gateway 라우팅 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 엔드포인트 테스트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_kr_signals_route(self, mock_get):
        """/api/kr/signals 라우팅 테스트"""
        # Mock VCP Scanner response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"signals": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/kr/signals?limit=20")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_market_gate_route(self, mock_get):
        """/api/kr/market-gate 라우팅 테스트"""
        # Mock Market Analyzer response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"gate": "GREEN", "score": 85}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/kr/market-gate")

        assert response.status_code == 200
        data = response.json()
        assert "gate" in data

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_jongga_v2_route(self, mock_get):
        """/api/kr/jongga-v2/latest 라우팅 테스트"""
        # Mock Signal Engine response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"signals": [], "date": "2026-01-23"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/kr/jongga-v2/latest")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "date" in data


class TestServiceDiscovery:
    """Service Discovery 테스트"""

    def test_service_registration(self):
        """서비스 등록 테스트"""
        # Arrange & Act
        registry = ServiceRegistry()
        services = registry.list_services()

        # Assert
        assert len(services) > 0
        service_names = [s["name"] for s in services]
        assert "vcp-scanner" in service_names

    def test_service_discovery(self):
        """서비스 조회 테스트"""
        # Arrange
        registry = get_registry()

        # Act
        vcp_service = registry.get_service("vcp-scanner")

        # Assert
        assert vcp_service is not None
        assert vcp_service["name"] == "vcp-scanner"

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """헬스 체크 엔드포인트 테스트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthentication:
    """인증 미들웨어 테스트 (추후 구현)"""

    @pytest.mark.skip(reason="API Key authentication not implemented yet")
    def test_api_key_auth(self):
        """API Key 인증 테스트"""
        pass

    @pytest.mark.skip(reason="Rate limiting not implemented yet")
    def test_rate_limiting(self):
        """Rate Limiting 테스트"""
        pass


class TestCircuitBreaker:
    """Circuit Breaker 패턴 테스트 (추후 구현)"""

    @pytest.mark.skip(reason="Circuit Breaker not implemented yet")
    def test_circuit_opens_on_failure(self):
        """연속 실패 시 Circuit Breaker 열림"""
        pass

    @pytest.mark.skip(reason="Circuit Breaker not implemented yet")
    def test_circuit_closes_on_recovery(self):
        """서비스 회복 시 Circuit Breaker 닫힘"""
        pass


class TestRequestResponse:
    """요청/응답 변환 테스트"""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_proxy_to_vcp_scanner(self, mock_get):
        """VCP Scanner 서비스로 프록시"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"signals": [{"ticker": "005930"}]}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/kr/signals")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """에러 처리 테스트"""
        # Arrange - 존재하지 않는 서비스 호출 시뮬레이션
        with patch("services.api_gateway.main.get_registry") as mock:
            registry = Mock()
            registry.get_service.return_value = None  # 서비스 없음
            mock.return_value = registry

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/kr/signals")

        # Assert
        assert response.status_code == 503
        assert "not available" in response.json()["detail"]
