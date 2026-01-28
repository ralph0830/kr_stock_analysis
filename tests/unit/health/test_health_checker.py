"""
헬스체커 테스트
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from src.health.health_checker import (
    HealthChecker,
    HealthStatus,
    ServiceHealth,
    SystemHealth,
    init_health_checker,
    get_health_checker,
)


class TestHealthStatus:
    """HealthStatus Enum 테스트"""

    def test_health_status_values(self):
        """HealthStatus 값 확인"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestServiceHealth:
    """ServiceHealth 테스트"""

    def test_service_health_creation(self):
        """ServiceHealth 생성 테스트"""
        health = ServiceHealth(
            name="test_service",
            status=HealthStatus.HEALTHY,
            response_time_ms=50.5,
            message="OK",
        )

        assert health.name == "test_service"
        assert health.status == HealthStatus.HEALTHY
        assert health.response_time_ms == 50.5
        assert health.message == "OK"
        assert health.details == {}

    def test_service_health_to_dict(self):
        """ServiceHealth to_dict 테스트"""
        now = datetime.now(timezone.utc)
        health = ServiceHealth(
            name="test_service",
            status=HealthStatus.HEALTHY,
            response_time_ms=100.0,
            message="Slow",
            details={"memory": "100MB"},
            last_check=now,
        )

        result = health.to_dict()

        assert result["name"] == "test_service"
        assert result["status"] == "healthy"
        assert result["response_time_ms"] == 100.0
        assert result["message"] == "Slow"
        assert result["details"]["memory"] == "100MB"
        assert "last_check" in result


class TestSystemHealth:
    """SystemHealth 테스트"""

    def test_system_health_creation(self):
        """SystemHealth 생성 테스트"""
        services = {
            "database": ServiceHealth(name="database", status=HealthStatus.HEALTHY),
            "redis": ServiceHealth(name="redis", status=HealthStatus.HEALTHY),
        }

        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            services=services,
            uptime_seconds=3600.0,
        )

        assert health.status == HealthStatus.HEALTHY
        assert len(health.services) == 2
        assert health.uptime_seconds == 3600.0

    def test_system_health_to_dict(self):
        """SystemHealth to_dict 테스트"""
        services = {
            "database": ServiceHealth(name="database", status=HealthStatus.HEALTHY),
        }

        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            services=services,
            uptime_seconds=100.0,
        )

        result = health.to_dict()

        assert result["status"] == "healthy"
        assert "database" in result["services"]
        assert result["uptime_seconds"] == 100.0
        assert "timestamp" in result


class TestHealthChecker:
    """HealthChecker 테스트"""

    @pytest.fixture
    def checker(self):
        """헬스체커 인스턴스"""
        return HealthChecker(start_time=1000.0, timeout=2.0)

    def test_checker_initialization(self, checker):
        """헬스체커 초기화 테스트"""
        assert checker.start_time == 1000.0
        assert checker.timeout == 2.0
        assert checker._checkers == {}

    def test_register_checker(self, checker):
        """체커 등록 테스트"""
        async def mock_checker():
            return ServiceHealth(name="custom", status=HealthStatus.HEALTHY)

        checker.register_checker("custom", mock_checker)
        assert "custom" in checker._checkers

    def test_determine_overall_status_healthy(self, checker):
        """전체 상태: healthy"""
        services = {
            "database": ServiceHealth(name="database", status=HealthStatus.HEALTHY),
            "redis": ServiceHealth(name="redis", status=HealthStatus.HEALTHY),
        }

        status = checker._determine_overall_status(services)
        assert status == HealthStatus.HEALTHY

    def test_determine_overall_status_degraded(self, checker):
        """전체 상태: degraded"""
        services = {
            "database": ServiceHealth(name="database", status=HealthStatus.HEALTHY),
            "redis": ServiceHealth(name="redis", status=HealthStatus.DEGRADED),
            "api_gateway": ServiceHealth(name="api_gateway", status=HealthStatus.HEALTHY),
        }

        status = checker._determine_overall_status(services)
        assert status == HealthStatus.DEGRADED

    def test_determine_overall_status_unhealthy(self, checker):
        """전체 상태: unhealthy (핵심 서비스 다운)"""
        services = {
            "database": ServiceHealth(name="database", status=HealthStatus.UNHEALTHY),
            "redis": ServiceHealth(name="redis", status=HealthStatus.HEALTHY),
        }

        status = checker._determine_overall_status(services)
        assert status == HealthStatus.UNHEALTHY

    def test_determine_overall_status_unknown(self, checker):
        """전체 상태: unknown (서비스 없음)"""
        status = checker._determine_overall_status({})
        assert status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_check_api_gateway(self, checker):
        """API Gateway 헬스체크 테스트"""
        health = await checker._check_api_gateway()

        assert health.name == "api_gateway"
        assert health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNKNOWN)
        assert health.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_service_not_found(self, checker):
        """존재하지 않는 서비스 체크"""
        health = await checker.check_service("nonexistent")

        assert health.name == "nonexistent"
        assert health.status == HealthStatus.UNKNOWN
        assert "not found" in health.message.lower()


class TestHttpServiceCheck:
    """HTTP 서비스 체크 테스트"""

    @pytest.fixture
    def checker(self):
        return HealthChecker(start_time=1000.0, timeout=2.0)

    @pytest.mark.asyncio
    async def test_check_http_service_success(self, checker):
        """HTTP 서비스 체크 성공"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            health = await checker._check_http_service(
                name="test_service",
                base_url="http://localhost:8000",
                health_path="/health",
            )

            assert health.name == "test_service"
            assert health.status == HealthStatus.HEALTHY
            assert health.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_http_service_timeout(self, checker):
        """HTTP 서비스 체크 타임아웃"""
        with patch("httpx.AsyncClient") as mock_client_class:
            import httpx

            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            health = await checker._check_http_service(
                name="test_service",
                base_url="http://localhost:8000",
                health_path="/health",
            )

            assert health.name == "test_service"
            assert health.status == HealthStatus.UNHEALTHY
            # 타임아웃 또는 연결 실패 메시지 확인
            assert "timeout" in health.message.lower() or "failed" in health.message.lower()

    @pytest.mark.asyncio
    async def test_check_http_service_error_status(self, checker):
        """HTTP 서비스 체크 에러 상태"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            health = await checker._check_http_service(
                name="test_service",
                base_url="http://localhost:8000",
                health_path="/health",
            )

            assert health.name == "test_service"
            assert health.status == HealthStatus.UNHEALTHY


class TestGlobalFunctions:
    """전역 함수 테스트"""

    def test_init_health_checker(self):
        """헬스체커 초기화 테스트"""
        import time

        start_time = time.time()
        checker = init_health_checker(start_time)

        assert checker is not None
        assert checker.start_time == start_time

        # 두 번 호출 시 동일 인스턴스 반환
        checker2 = get_health_checker()
        assert checker is checker2

    def test_get_health_checker_before_init(self):
        """초기화 전 get_health_checker 호출"""
        # 초기화 전에는 None 반환
        with patch("src.health.health_checker._health_checker", None):
            checker = get_health_checker()
            assert checker is None
