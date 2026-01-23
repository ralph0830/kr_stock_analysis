"""
Pytest Configuration
테스트 설정 및 Fixture 정의
"""

import pytest
import sys
from pathlib import Path
from typing import Generator
import os
import asyncio

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

# 환경 변수 로드
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kr_stock_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Pytest-asyncio 설정
pytest_plugins = ("pytest_asyncio",)


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
    # TODO: 실제 DB 연결 시 활성화
    # init_db()
    yield


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
