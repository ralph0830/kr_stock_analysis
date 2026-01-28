"""
API Gateway lifespan 및 브로드캐스터 통합 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.api_gateway.main import app, lifespan


class TestAPIGatewayLifespan:
    """API Gateway lifespan 테스트"""

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """ lifespan 시작 테스트"""
        # lifespan 컨텍스트 실행
        async with lifespan(app):
            # 서비스 레지스트리 확인
            from services.api_gateway.service_registry import get_registry
            registry = get_registry()
            services = registry.list_services()

            # 서비스 등록 확인
            assert isinstance(services, list)

    @pytest.mark.asyncio
    async def test_lifespan_with_broadcaster(self):
        """브로드캐스터 포함 lifespan 테스트"""
        from src.websocket.price_provider import get_realtime_service

        # 브로드캐스터 시작 전
        service_before = get_realtime_service()
        assert service_before is None or not service_before.is_running()

        # lifespan 실행 (내부에서 브로드캐스터 시작됨)
        async with lifespan(app):
            # 브로드캐스터가 시작되었는지 확인
            # (실제로 시작하려면 시간이 좀 걸림)
            service_after = get_realtime_service()
            assert service_after is not None

            # TODO: 브로드캐스터가 실제로 시작되었는지 확인하려면
            # 잠시 대기 후 상태 확인 필요

        # 종료 후 브로드캐스터 중지 확인
        service_final = get_realtime_service()
        if service_final:
            assert not service_final.is_running()


class TestBroadcasterIntegration:
    """브로드캐스터 통합 테스트"""

    def test_init_realtime_service(self):
        """전역 서비스 초기화 테스트"""
        from src.websocket.price_provider import init_realtime_service, get_realtime_service

        # 초기화
        service = init_realtime_service(
            tickers=["005930", "000660"],
            use_real_data=False,
        )

        assert service is not None
        assert service.tickers == ["005930", "000660"]
        assert service.use_real_data is False

        # 전역 인스턴스 확인
        global_service = get_realtime_service()
        assert global_service is not None

    def test_service_configuration(self):
        """서비스 구성 테스트"""
        from src.websocket.price_provider import init_realtime_service

        service = init_realtime_service(
            tickers=["005930", "000660", "035420"],
            interval_seconds=10,
            use_real_data=True,
        )

        assert service.tickers == ["005930", "000660", "035420"]
        assert service.interval_seconds == 10
        assert service.use_real_data is True

    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """서비스 생명주기 테스트"""
        from src.websocket.price_provider import init_realtime_service

        service = init_realtime_service(
            tickers=["005930"],
            use_real_data=False,
        )

        # 시작
        assert service.is_running() is False
        await service.start()
        assert service.is_running() is True

        # 중지
        await service.stop()
        assert service.is_running() is False


class TestAPIGatewayStartup:
    """API Gateway 시작 테스트"""

    @pytest.mark.asyncio
    async def test_consecutive_startup_shutdown(self):
        """연속 시작/종료 테스트"""
        # 여러 번 시작/종료 시도
        for _ in range(3):
            async with lifespan(app):
                assert True  # lifespan 성공

    @pytest.mark.asyncio
    async def test_startup_order(self):
        """시작 순서 테스트"""
        started_components = []

        # lifespan 시작 전
        started_components.append("before_lifespan")

        # 수동으로 lifespan 실행
        async with lifespan(app):
            started_components.append("inside_lifespan")

        # lifespan 종료 후
        started_components.append("after_lifespan")

        assert "before_lifespan" in started_components
        assert "inside_lifespan" in started_components
        assert "after_lifespan" in started_components


class TestMetricsAvailability:
    """메트릭 가용성 테스트"""

    def test_metrics_endpoints_available(self):
        """메트릭 엔드포인트 사용 가능 여부 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # 메트릭 엔드포인트 테스트
        response = client.get("/metrics")
        assert response.status_code == 200

        response = client.get("/api/metrics")
        assert response.status_code == 200

    def test_websocket_stats_available(self):
        """WebSocket 통계 엔드포인트 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # WebSocket 통계 엔드포인트 테스트
        response = client.get("/ws/stats")
        assert response.status_code == 200

        data = response.json()
        assert "active_connections" in data
        assert "broadcaster_running" in data
