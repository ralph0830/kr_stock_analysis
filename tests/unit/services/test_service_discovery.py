"""
Test Suite: Service Discovery (GREEN Phase)
작성 목적: Service Discovery 기능 구현 후 테스트
예상 결과: PASS - ServiceRegistry 구현 완료
"""

import pytest
from typing import Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo, get_registry


class TestServiceRegistry:
    """Service Registry 테스트"""

    @pytest.fixture
    def registry(self):
        """Service Registry Fixture"""
        return ServiceRegistry()

    def test_register_service(self, registry):
        """서비스 등록 테스트"""
        # Arrange
        service_info = ServiceInfo(
            name="test-service",
            url="http://test-service:8000",
            health_check_url="http://test-service:8000/health",
        )

        # Act
        registry.register(service_info)

        # Assert
        services = registry.list_services()
        service_names = [s["name"] for s in services]
        assert "test-service" in service_names

    def test_get_service(self, registry):
        """서비스 조회 테스트"""
        # Arrange
        service_info = ServiceInfo(
            name="test-service",
            url="http://test-service:8000",
        )
        registry.register(service_info)

        # Act
        service = registry.get_service("test-service")

        # Assert
        assert service is not None
        assert service["name"] == "test-service"
        assert service["url"] == "http://test-service:8000"

    def test_get_nonexistent_service(self, registry):
        """존재하지 않는 서비스 조회 테스트"""
        # Act
        service = registry.get_service("nonexistent-service")

        # Assert
        assert service is None

    def test_list_all_services(self, registry):
        """전체 서비스 목록 조회 테스트"""
        # Arrange
        registry.register(ServiceInfo(name="service-1", url="http://s1:8000"))
        registry.register(ServiceInfo(name="service-2", url="http://s2:8000"))

        # Act
        services = registry.list_services()

        # Assert
        assert len(services) >= 2
        assert all("name" in s and "url" in s for s in services)

    @pytest.mark.asyncio
    async def test_health_check_success(self, registry):
        """헬스 체크 성공 테스트"""
        # Arrange
        service_info = ServiceInfo(
            name="test-service",
            url="http://test-service:8000",
        )
        registry.register(service_info)

        # Mock httpx async client
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Act
            healthy = await registry.check_health("test-service")

            # Assert
            assert healthy is True
            assert service_info.is_healthy is True
            assert service_info.retry_count == 0

    @pytest.mark.asyncio
    async def test_health_check_failure(self, registry):
        """헬스 체크 실패 테스트"""
        # Arrange
        service_info = ServiceInfo(
            name="test-service",
            url="http://test-service:8000",
        )
        registry.register(service_info)

        # Mock httpx async client to raise exception
        with patch("httpx.AsyncClient.get") as mock_get:
            import httpx
            mock_get.side_effect = httpx.RequestError("Connection failed")

            # Act
            healthy = await registry.check_health("test-service")

            # Assert
            assert healthy is False
            assert service_info.is_healthy is False
            assert service_info.retry_count == 1

    def test_cleanup_unhealthy_service(self, registry):
        """비정상 서비스 제거 테스트"""
        # Arrange
        healthy_service = ServiceInfo(name="healthy-service", url="http://healthy:8000")
        healthy_service.is_healthy = True

        unhealthy_service = ServiceInfo(name="unhealthy-service", url="http://unhealthy:8000")
        unhealthy_service.is_healthy = False
        unhealthy_service.retry_count = 5

        registry.register(healthy_service)
        registry.register(unhealthy_service)

        # Act
        removed = registry.cleanup_unhealthy()

        # Assert
        assert "unhealthy-service" in removed
        assert registry.get_service("healthy-service") is not None
        assert registry.get_service("unhealthy-service") is None

    def test_get_unhealthy_services(self, registry):
        """비정상 서비스 목록 조회 테스트"""
        # Arrange
        healthy_service = ServiceInfo(name="healthy-service", url="http://healthy:8000")
        healthy_service.is_healthy = True

        unhealthy_service = ServiceInfo(name="unhealthy-service", url="http://unhealthy:8000")
        unhealthy_service.is_healthy = False

        registry.register(healthy_service)
        registry.register(unhealthy_service)

        # Act
        unhealthy_list = registry.get_unhealthy_services()

        # Assert
        assert "unhealthy-service" in unhealthy_list
        assert "healthy-service" not in unhealthy_list

    def test_singleton_registry(self):
        """싱글톤 레지스트리 테스트"""
        # Act
        registry1 = get_registry()
        registry2 = get_registry()

        # Assert
        assert registry1 is registry2


class TestLoadBalancing:
    """로드 밸런싱 테스트 (추후 구현)"""

    @pytest.mark.skip(reason="Load balancing not implemented yet")
    def test_round_robin_selection(self):
        """Round-robin 로드 밸런싱 테스트"""
        pass

    @pytest.mark.skip(reason="Weighted selection not implemented yet")
    def test_weighted_selection(self):
        """가중치 기반 선택 테스트"""
        pass

    @pytest.mark.skip(reason="Sticky sessions not implemented yet")
    def test_sticky_sessions(self):
        """Sticky 세션 테스트"""
        pass


class TestServiceConfiguration:
    """서비스 설정 테스트"""

    def test_env_config_loading(self):
        """환경 변수 기반 설정 로드 테스트"""
        # Arrange & Act
        registry = ServiceRegistry()

        # Assert - 기본 서비스들이 환경 변수에서 로드되어야 함
        services = registry.list_services()
        service_names = [s["name"] for s in services]

        # 기본 서비스들 확인
        assert "vcp-scanner" in service_names
        assert "market-analyzer" in service_names
        assert "signal-engine" in service_names

    def test_service_url_resolution(self):
        """서비스 URL 해결 테스트"""
        # Arrange
        registry = ServiceRegistry()

        # Act
        vcp_service = registry.get_service("vcp-scanner")

        # Assert
        assert vcp_service is not None
        assert "url" in vcp_service
        assert vcp_service["url"].startswith("http://")

    def test_timeout_configuration(self):
        """타임아웃 설정 테스트"""
        # Arrange & Act
        service = ServiceInfo(
            name="test-service",
            url="http://test:8000",
            timeout=10.0
        )

        # Assert
        assert service.timeout == 10.0

    def test_retry_configuration(self):
        """재시도 설정 테스트"""
        # Arrange & Act
        service = ServiceInfo(
            name="test-service",
            url="http://test:8000",
            max_retries=5
        )

        # Assert
        assert service.max_retries == 5
        assert service.retry_count == 0
