"""
Pytest Configuration
테스트 설정 및 Fixture 정의
"""

import pytest
import sys
from pathlib import Path
import os
import asyncio

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

# 환경 변수 로드
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ralph_stock")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")

# Pytest-asyncio 설정
pytest_plugins = ("pytest_asyncio",)


# ============================================================================
# Timeout 설정 (pytest-timeout)
# ============================================================================

# 전체 테스트 세션 기본 timeout (초)
# 개별 테스트는 @pytest.mark.timeout 데코레이터로 오버라이드 가능
@pytest.fixture(autouse=True, scope="session")
def set_default_timeout():
    """
    전역 기본 timeout 설정 (pytest-timeout 플러그인 필요)

    사용법:
    1. 전역 설정: pytest.ini 또는 명령행 --timeout=30
    2. 개별 테스트: @pytest.mark.timeout(10)
    3. 클래스/모듈: @pytest.mark.timeout(30)
    """
    # 이 fixture는 문서화 목적으로 사용됨
    # 실제 timeout은 pytest.ini의 timeout 설정 또는 명령행 옵션 사용
    yield


# ============================================================================
# Timeout 마커 정의
# ============================================================================

def pytest_configure(config):
    """Pytest 설정 훅 - timeout 마커 등록"""
    config.addinivalue_line(
        "markers",
        "timeout(seconds): 테스트 timeout 설정 (예: @pytest.mark.timeout(10))"
    )
    config.addinivalue_line(
        "markers",
        "slow: 느린 테스트 마커 (통합 테스트 등)"
    )
    config.addinivalue_line(
        "markers",
        "integration: 통합 테스트 마커 (DB/외부 API 필요)"
    )
    config.addinivalue_line(
        "markers",
        "unit: 단위 테스트 마커 (외부 의존성 없음)"
    )


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def database_setup():
    """
    전체 테스트 세션에 한 번만 실행되는 설정
    - 테스트 DB 초기화
    - 필요한 경우 마이그레이션 실행
    """
    from src.database.session import init_db
    try:
        # 데이터베이스 초기화
        init_db()
        print("✅ Database initialized for testing")
    except Exception as e:
        print(f"⚠️  Database initialization: {e}")
    yield
    # Clean up after all tests
    # Optional: Clean test data
    print("🧹 Test session completed")


@pytest.fixture
def mock_session():
    """
    Mock DB Session (실제 DB 없이 테스트용)
    unittest.mock.Mock 객체 반환
    """
    from unittest.mock import MagicMock

    mock = MagicMock()
    # TODO: 필요에 따라 mock 동작 설정
    return mock


@pytest.fixture
def test_db_session():
    """
    통합 테스트용 DB Session (동기)
    실제 테스트 데이터베이스에 연결
    """
    from src.database.session import SessionLocal
    from sqlalchemy.orm import close_all_sessions

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        close_all_sessions()
