"""
System Routes Unit Tests
TDD GREEN Phase - Tests should pass with implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException


class TestSystemRoutesUnit:
    """System Routes 단위 테스트"""

    def test_get_data_status(self):
        """데이터 파일 상태 조회"""
        from services.api_gateway.routes.system import get_data_status
        from services.api_gateway.schemas import DataStatusResponse

        mock_session = Mock()

        # Mock repositories
        with patch("services.api_gateway.routes.system.StockRepository") as mock_repo_cls:
            with patch("services.api_gateway.routes.system.SignalRepository") as mock_signal_repo_cls:
                mock_repo = Mock()
                mock_repo.count.return_value = 100
                mock_repo_cls.return_value = mock_repo

                mock_signal_repo = Mock()
                mock_signal_repo.count.return_value = 10
                mock_signal_repo_cls.return_value = mock_signal_repo

                # Mock session.execute to return proper mock objects
                with patch("services.api_gateway.routes.system.func.count") as mock_count:
                    with patch("services.api_gateway.routes.system.func.max") as mock_max:
                        mock_count_obj = Mock()
                        mock_count_obj.scalar.return_value = 1000
                        mock_count.return_value = mock_count_obj

                        mock_max_obj = Mock()
                        mock_max_obj.scalar.return_value = datetime(2024, 1, 27).date()
                        mock_max.return_value = mock_max_obj

                        # Mock session.execute for distinct count
                        mock_session.execute.return_value = mock_count_obj

                        result = get_data_status(mock_session)
                        assert isinstance(result, DataStatusResponse)
                        assert result.total_stocks == 100

    def test_get_system_health(self):
        """전체 시스템 헬스 체크"""
        from services.api_gateway.routes.system import get_system_health

        mock_session = Mock()

        with patch("services.api_gateway.routes.system.check_database_health", return_value="up"):
            with patch("services.api_gateway.routes.system.check_redis_health", return_value="up"):
                with patch("services.api_gateway.routes.system.check_celery_health", return_value=None):
                    result = get_system_health(mock_session)
                    assert result.status in ["healthy", "degraded", "unhealthy"]
                    assert "database" in result.services
                    assert "redis" in result.services

    def test_check_database_health_up(self):
        """데이터베이스 헬스 체크 - 정상"""
        from services.api_gateway.routes.system import check_database_health

        mock_session = Mock()
        mock_session.execute.return_value = Mock()

        result = check_database_health(mock_session)
        assert result == "up"

    def test_check_database_health_down(self):
        """데이터베이스 헬스 체크 - 비정상"""
        from services.api_gateway.routes.system import check_database_health

        mock_session = Mock()
        mock_session.execute.side_effect = Exception("DB Error")

        result = check_database_health(mock_session)
        assert result == "down"

    def test_check_redis_health_up(self):
        """Redis 헬스 체크 - 정상"""
        from services.api_gateway.routes.system import check_redis_health

        with patch("redis.Redis.from_url") as mock_from_url:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_from_url.return_value = mock_client

            result = check_redis_health()
            assert result == "up"

    def test_check_redis_health_down(self):
        """Redis 헬스 체크 - 비정상"""
        from services.api_gateway.routes.system import check_redis_health

        with patch("redis.Redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Redis Error")

            result = check_redis_health()
            assert result == "down"

    def test_get_uptime_seconds(self):
        """애플리케이션 실행 시간 확인"""
        from services.api_gateway.routes.system import get_uptime_seconds

        uptime = get_uptime_seconds()
        assert uptime >= 0
        assert isinstance(uptime, float)

    def test_data_status_response_model(self):
        """DataStatusResponse 모델"""
        from services.api_gateway.schemas import DataStatusResponse, DataStatusItem

        response = DataStatusResponse(
            total_stocks=100,
            updated_stocks=50,
            last_update="2024-01-27T10:00:00",
            data_files={"prices": "OK", "signals": "OK"},
            details=[
                DataStatusItem(
                    name="prices",
                    status="OK",
                    last_update="2024-01-27T10:00:00",
                    record_count=1000,
                )
            ],
        )
        assert response.total_stocks == 100
        assert response.data_files["prices"] == "OK"

    def test_system_health_response_model(self):
        """SystemHealthResponse 모델"""
        from services.api_gateway.schemas import SystemHealthResponse

        response = SystemHealthResponse(
            status="healthy",
            services={"api_gateway": "up", "vcp_scanner": "up"},
            timestamp="2024-01-27T10:00:00",
            uptime_seconds=3600.0,
            database_status="up",
            redis_status="up",
        )
        assert response.status == "healthy"
        assert response.services["api_gateway"] == "up"

    def test_data_status_item(self):
        """DataStatusItem 모델 - 개별 데이터 상태"""
        from services.api_gateway.schemas import DataStatusItem

        item = DataStatusItem(
            name="prices",
            status="OK",
            last_update="2024-01-27T10:00:00",
            record_count=1000,
        )
        assert item.name == "prices"
        assert item.status == "OK"

    def test_service_status_item(self):
        """ServiceStatusItem 모델 - 개별 서비스 상태"""
        from services.api_gateway.schemas import ServiceStatusItem

        item = ServiceStatusItem(
            name="api_gateway",
            status="up",
            response_time_ms=50,
        )
        assert item.name == "api_gateway"
        assert item.status == "up"
