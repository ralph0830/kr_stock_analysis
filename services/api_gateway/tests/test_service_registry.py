"""
Service Registry 테스트 (TDD RED Phase)

서비스 디스커버리 및 헬스 체크 기능 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime


class TestServiceInfo:
    """ServiceInfo 데이터 클래스 테스트"""

    def test_service_info_creation(self):
        """ServiceInfo 생성 테스트"""
        from services.api_gateway.service_registry import ServiceInfo

        service = ServiceInfo(
            name="test-service",
            url="http://localhost:8000"
        )

        assert service.name == "test-service"
        assert service.url == "http://localhost:8000"
        assert service.health_check_url == "http://localhost:8000/health"
        assert service.is_healthy is True
        assert service.timeout == 5.0
        assert service.retry_count == 0
        assert service.max_retries == 3

    def test_service_info_with_custom_health_check(self):
        """커스텀 health_check_url 테스트"""
        from services.api_gateway.service_registry import ServiceInfo

        service = ServiceInfo(
            name="test-service",
            url="http://localhost:8000",
            health_check_url="http://localhost:8000/status"
        )

        assert service.health_check_url == "http://localhost:8000/status"


class TestServiceRegistry:
    """ServiceRegistry 클래스 테스트"""

    def test_registry_init(self):
        """ServiceRegistry 초기화 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry

        registry = ServiceRegistry()

        # 환경 변수에서 로드된 기본 서비스 확인
        services = registry.list_services()
        service_names = [s["name"] for s in services]

        assert "vcp-scanner" in service_names
        assert "signal-engine" in service_names
        assert "market-analyzer" in service_names or "ai-analyzer" in service_names

    def test_register_service(self):
        """서비스 등록 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo

        registry = ServiceRegistry()
        initial_count = len(registry.list_services())

        new_service = ServiceInfo(
            name="new-service",
            url="http://localhost:9999"
        )
        registry.register(new_service)

        assert len(registry.list_services()) == initial_count + 1

    def test_get_service(self):
        """서비스 조회 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        service = registry.get_service("vcp-scanner")

        assert service is not None
        assert service["name"] == "vcp-scanner"
        assert "url" in service

    def test_get_service_not_found(self):
        """없는 서비스 조회 시 None 반환"""
        from services.api_gateway.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        service = registry.get_service("non-existent")

        assert service is None

    def test_get_unhealthy_service(self):
        """비정상 서비스 조회 시 None 반환"""
        from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo

        registry = ServiceRegistry()
        unhealthy_service = ServiceInfo(
            name="unhealthy",
            url="http://localhost:9999",
            is_healthy=False
        )
        registry.register(unhealthy_service)

        service = registry.get_service("unhealthy")
        assert service is None

    def test_list_services(self):
        """전체 서비스 목록 조회 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        services = registry.list_services()

        assert isinstance(services, list)
        assert len(services) >= 3  # 최소 3개 기본 서비스
        for service in services:
            assert "name" in service
            assert "url" in service
            assert "is_healthy" in service

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """헬스 체크 성공 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo

        registry = ServiceRegistry()
        service = ServiceInfo(
            name="test",
            url="http://localhost:8000",
            health_check_url="http://localhost:8000/health"
        )
        registry.register(service)

        # Mock httpx.AsyncClient
        with patch('services.api_gateway.service_registry.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await registry.check_health("test")

            assert result is True
            assert service.is_healthy is True
            assert service.retry_count == 0

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """헬스 체크 실패 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo

        registry = ServiceRegistry()
        service = ServiceInfo(
            name="test",
            url="http://localhost:9999",  # 존재하지 않는 포트
        )
        registry.register(service)

        # 실제 HTTP 요청이 실패하도록 함
        result = await registry.check_health("test")

        # 연결 실패 시 False 반환 (서버 없음)
        assert result is False
        assert service.is_healthy is False
        assert service.retry_count >= 1

    def test_get_unhealthy_services(self):
        """비정상 서비스 목록 조회 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo

        registry = ServiceRegistry()

        # 비정상 서비스 추가
        unhealthy1 = ServiceInfo(name="unhealthy1", url="http://localhost:9999", is_healthy=False)
        unhealthy2 = ServiceInfo(name="unhealthy2", url="http://localhost:9998", is_healthy=False)
        registry.register(unhealthy1)
        registry.register(unhealthy2)

        unhealthy_list = registry.get_unhealthy_services()

        assert "unhealthy1" in unhealthy_list
        assert "unhealthy2" in unhealthy_list

    def test_cleanup_unhealthy(self):
        """비정상 서비스 제거 테스트"""
        from services.api_gateway.service_registry import ServiceRegistry, ServiceInfo

        registry = ServiceRegistry()

        # 최대 재시도 횟수 초과한 서비스 추가
        max_retry_service = ServiceInfo(
            name="to-remove",
            url="http://localhost:9999",
            is_healthy=False,
            retry_count=3,
            max_retries=3
        )
        registry.register(max_retry_service)

        removed = registry.cleanup_unhealthy()

        assert "to-remove" in removed
        assert registry.get_service("to-remove") is None


class TestHealthCheckLoop:
    """헬스 체크 루프 테스트"""

    @pytest.mark.asyncio
    async def test_health_check_loop_single_iteration(self):
        """헬스 체크 루프 단일 반복 테스트"""
        from services.api_gateway.service_registry import health_check_loop, get_registry

        registry = get_registry()

        # 한 번만 실행하고 취소
        task = asyncio.create_task(health_check_loop(interval=1))

        # 첫 번째 체크 대기
        await asyncio.sleep(0.1)

        # 취소
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass  # 예상된 취소


class TestGetRegistry:
    """get_registry 싱글톤 테스트"""

    def test_get_registry_singleton(self):
        """get_registry 싱글톤 패턴 테스트"""
        from services.api_gateway.service_registry import get_registry, ServiceRegistry

        registry1 = get_registry()
        registry2 = get_registry()

        assert isinstance(registry1, ServiceRegistry)
        assert registry1 is registry2  # 동일 인스턴스
