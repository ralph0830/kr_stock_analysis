"""
E2E Service Health Check Tests

이 테스트 모듈은 Docker Compose 서비스가 실행 중인지 확인합니다.
CI 환경에서는 Mock 서버를 사용합니다.
"""

import pytest
import requests
from sqlalchemy import create_engine, text
import redis
import time
from typing import Generator

# Mock import
from tests.mocks.mock_server import MockServiceServer
from unittest.mock import MagicMock, patch


class TestServiceHealth:
    """서비스 헬스 체크 테스트"""

    @pytest.fixture(scope="session")
    def base_url(self):
        """기본 URL 설정"""
        return "http://localhost"

    @pytest.fixture(scope="session")
    def db_url(self):
        """데이터베이스 URL"""
        return "postgresql://postgres:postgres@localhost:5433/ralph_stock"

    @pytest.fixture(scope="session")
    def redis_url(self):
        """Redis URL"""
        return "redis://localhost:6380/0"

    # ========================================================================
    # Mock 기반 테스트 (CI 환경용)
    # ========================================================================

    def test_api_gateway_health_mock(self, mock_service_server):
        """
        GIVEN: Mock API Gateway 서비스
        WHEN: /health endpoint에 GET 요청 (Mock)
        THEN: status code 200과 health 정보 반환
        """
        response = mock_service_server.get_service_health("api_gateway")

        assert response["status"] == "healthy", \
            f"Expected 'healthy', got {response['status']}"
        assert "port" in response, "Response should contain 'port' field"
        assert response["port"] == 5111, f"Expected port 5111, got {response['port']}"

    def test_vcp_scanner_health_mock(self, mock_service_server):
        """
        GIVEN: Mock VCP Scanner 서비스
        WHEN: /health endpoint에 GET 요청 (Mock)
        THEN: status code 200 반환
        """
        response = mock_service_server.get_service_health("vcp_scanner")

        assert response["status"] == "healthy", \
            f"Expected 'healthy', got {response['status']}"

    def test_signal_engine_health_mock(self, mock_service_server):
        """
        GIVEN: Mock Signal Engine 서비스
        WHEN: /health endpoint에 GET 요청 (Mock)
        THEN: status code 200 반환
        """
        response = mock_service_server.get_service_health("signal_engine")

        assert response["status"] == "healthy", \
            f"Expected 'healthy', got {response['status']}"

    def test_chatbot_health_mock(self, mock_service_server):
        """
        GIVEN: Mock Chatbot 서비스
        WHEN: /health endpoint에 GET 요청 (Mock)
        THEN: status code 200 반환
        """
        response = mock_service_server.get_service_health("chatbot")

        assert response["status"] == "healthy", \
            f"Expected 'healthy', got {response['status']}"

    # ========================================================================
    # 실제 서비스 테스트 (로컬 개발 환경용)
    # ========================================================================

    @pytest.mark.skip(reason="서비스 실행 필요 - 로컬 개발 환경에서만 실행")
    def test_api_gateway_health(self, base_url):
        """
        GIVEN: API Gateway 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200과 health 정보 반환

        참고: 이 테스트는 실제 서비스가 실행 중이어야 합니다.
        """
        response = requests.get(f"{base_url}:5111/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "healthy", f"Expected 'healthy', got {data['status']}"

    @pytest.mark.skip(reason="서비스 실행 필요 - 로컬 개발 환경에서만 실행")
    def test_vcp_scanner_health(self, base_url):
        """
        GIVEN: VCP Scanner 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5112/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    @pytest.mark.skip(reason="서비스 실행 필요 - 로컬 개발 환경에서만 실행")
    def test_signal_engine_health(self, base_url):
        """
        GIVEN: Signal Engine 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5113/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    @pytest.mark.skip(reason="서비스 실행 필요 - 로컬 개발 환경에서만 실행")
    def test_chatbot_health(self, base_url):
        """
        GIVEN: Chatbot 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5114/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # ========================================================================
    # 데이터베이스/인프라 테스트 (실제 연결)
    # ========================================================================

    def test_postgres_connection(self, db_url):
        """
        GIVEN: PostgreSQL 서비스가 실행 중
        WHEN: 데이터베이스 연결 시도
        THEN: 연결 성공 및 버전 확인
        """
        engine = create_engine(db_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()

        assert "PostgreSQL" in version, f"Expected PostgreSQL version, got {version}"

    def test_redis_connection(self, redis_url):
        """
        GIVEN: Redis 서비스가 실행 중
        WHEN: Redis 연결 및 ping 시도
        THEN: 연결 성공 및 PONG 응답
        """
        r = redis.from_url(redis_url, decode_responses=True)

        result = r.ping()
        assert result is True, "Redis ping should return True"

    # ========================================================================
    # 선택적 서비스 테스트 (서비스 실행 시에만 테스트)
    # ========================================================================

    @pytest.mark.skip(reason="Flower 서비스 실행 필요 - 선택적 테스트")
    def test_flower_accessible(self, base_url):
        """
        GIVEN: Flower (Celery monitoring) 서비스가 실행 중
        WHEN: Flower 대시보드 접속
        THEN: status code 200 반환

        참고: Flower는 선택적 서비스이므로 실행되지 않을 수 있습니다.
        """
        try:
            response = requests.get(f"{base_url}:5555", timeout=5)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert "Flower" in response.text or "Celery" in response.text, \
                "Response should contain 'Flower' or 'Celery'"
        except requests.exceptions.ConnectionError:
            pytest.skip("Flower 서비스가 실행되지 않음")

    @pytest.mark.skip(reason="Frontend 서비스 실행 필요 - 선택적 테스트")
    def test_frontend_running(self, base_url):
        """
        GIVEN: Frontend 서비스가 실행 중
        WHEN: 홈 페이지 접속
        THEN: status code 200 반환

        참고: Frontend는 선택적 서비스이므로 실행되지 않을 수 있습니다.
        """
        try:
            response = requests.get(f"{base_url}:5110", timeout=10)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.skip("Frontend 서비스가 실행되지 않음")

    # ========================================================================
    # 서비스 상태 관리 테스트
    # ========================================================================

    def test_service_status_management(self, mock_service_server):
        """
        GIVEN: Mock 서비스 서버
        WHEN: 서비스 상태 변경
        THEN: 상태가 올바르게 변경됨
        """
        # 초기 상태 확인
        response = mock_service_server.get_service_health("api_gateway")
        assert response["status"] == "healthy"

        # unhealthy로 변경
        mock_service_server.set_service_unhealthy("api_gateway")
        response = mock_service_server.get_service_health("api_gateway")
        assert response["status"] == "unhealthy"

        # 다시 healthy로 변경
        mock_service_server.set_service_healthy("api_gateway")
        response = mock_service_server.get_service_health("api_gateway")
        assert response["status"] == "healthy"

    def test_all_services_status(self, mock_service_server):
        """
        GIVEN: Mock 서비스 서버
        WHEN: 전체 서비스 상태 조회
        THEN: 모든 서비스 상태 반환
        """
        status = mock_service_server.get_all_services_status()

        assert "timestamp" in status
        assert "services" in status
        assert "api_gateway" in status["services"]
        assert "vcp_scanner" in status["services"]
        assert "signal_engine" in status["services"]
        assert "chatbot" in status["services"]
