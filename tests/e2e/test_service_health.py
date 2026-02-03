"""
E2E Service Health Check Tests
TDD Red Phase: Write failing tests first

This test module validates that all Docker Compose services are running and accessible.
"""
import pytest
import requests
from sqlalchemy import create_engine, text
import redis
import time


class TestServiceHealth:
    """서비스 헬스 체크 테스트 - TDD Red Phase"""

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

    def test_api_gateway_health(self, base_url):
        """
        GIVEN: API Gateway 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200과 health 정보 반환
        """
        response = requests.get(f"{base_url}:5111/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "healthy", f"Expected 'healthy', got {data['status']}"

    def test_vcp_scanner_health(self, base_url):
        """
        GIVEN: VCP Scanner 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5112/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_signal_engine_health(self, base_url):
        """
        GIVEN: Signal Engine 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5113/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_chatbot_health(self, base_url):
        """
        GIVEN: Chatbot 서비스가 실행 중
        WHEN: /health endpoint에 GET 요청
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5114/health", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

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

    def test_flower_accessible(self, base_url):
        """
        GIVEN: Flower (Celery monitoring) 서비스가 실행 중
        WHEN: Flower 대시보드 접속
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5555", timeout=5)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "Flower" in response.text or "Celery" in response.text, \
            "Response should contain 'Flower' or 'Celery'"

    def test_frontend_running(self, base_url):
        """
        GIVEN: Frontend 서비스가 실행 중
        WHEN: 홈 페이지 접속
        THEN: status code 200 반환
        """
        response = requests.get(f"{base_url}:5110", timeout=10)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
