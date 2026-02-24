"""
Pytest Configuration
테스트 설정 및 Fixture 정의
"""

import pytest
import sys
from pathlib import Path
import os
import asyncio
from typing import AsyncGenerator

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
    config.addinivalue_line(
        "markers",
        "e2e: End-to-End 테스트 마커 (실제 서버 필요)"
    )
    config.addinivalue_line(
        "markers",
        "fast: 빠른 테스트 마커 (5초 이내)"
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


# ============================================================================
# Mock Server Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def mock_service_server():
    """
    Mock 서비스 서버 Fixture

    모든 마이크로서비스의 Health Check를 Mock 처리합니다.

    Example:
        def test_api_health(mock_service_server):
            response = mock_service_server.get_service_health("api_gateway")
            assert response["status"] == "healthy"
    """
    from tests.mocks.mock_server import MockServiceServer
    server = MockServiceServer()
    return server


@pytest.fixture
def mock_service_responses():
    """
    Mock 서비스 응답 Fixture

    다양한 API 응답을 Mock 처리합니다.

    Example:
        def test_with_mock_responses(mock_service_responses):
            health_response = mock_service_responses["health_check"]
            assert health_response["status"] == "healthy"
    """
    from tests.mocks.mock_server import create_mock_response
    return {
        # Health Check 응답
        "health_check": {
            "status": "healthy",
            "timestamp": "2026-02-06T00:00:00Z",
            "services": {
                "vcp_scanner": "healthy",
                "signal_engine": "healthy",
                "chatbot": "healthy",
                "daytrading_scanner": "healthy"
            }
        },

        # VCP Scanner 응답
        "vcp_signals": {
            "signals": [],
            "total": 0,
            "timestamp": "2026-02-06T00:00:00Z"
        },

        # Signal Engine 응답
        "jongga_signals": {
            "signals": [],
            "total": 0,
            "timestamp": "2026-02-06T00:00:00Z"
        },

        # Daytrading Scanner 응답
        "daytrading_signals": {
            "signals": [],
            "total": 0,
            "timestamp": "2026-02-06T00:00:00Z"
        },

        # Market Gate 응답
        "market_status": {
            "status": "open",
            "market_time": "09:00:00",
            "next_close_time": "15:30:00"
        },

        # AI 분석 응답
        "ai_analysis": {
            "ticker": "005930",
            "sentiment_score": 0.75,
            "recommendation": "buy",
            "confidence": 0.85,
            "created_at": "2026-02-06T00:00:00Z"
        },

        # 백테스트 응답
        "backtest_result": {
            "config_name": "test_config",
            "total_trades": 100,
            "win_rate": 0.65,
            "total_return": 0.15,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.8
        },

        # 종목 정보 응답
        "stock_info": {
            "ticker": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "sector": "전자",
            "close_price": 80500,
            "change": 500,
            "change_rate": 0.62
        },

        # 차트 데이터 응답
        "chart_data": {
            "ticker": "005930",
            "data": [
                {
                    "date": "2026-02-06",
                    "open": 80000,
                    "high": 81000,
                    "low": 79500,
                    "close": 80500,
                    "volume": 1000000
                }
            ]
        }
    }


@pytest.fixture
def mock_kiwoom_api():
    """
    Mock Kiwoom REST API Fixture

    Example:
        async def test_get_chart(mock_kiwoom_api):
            chart = await mock_kiwoom_api.get_stock_daily_chart("005930", 10)
            assert len(chart) == 10
    """
    from tests.mocks.mock_kiwoom_api import MockKiwoomRestAPI
    api = MockKiwoomRestAPI()
    return api


@pytest.fixture
def mock_websocket():
    """
    Mock WebSocket Fixture

    Example:
        def test_websocket_send(mock_websocket):
            await mock_websocket.send_json({"test": "data"})
            assert len(mock_websocket.sent_messages) == 1
    """
    from tests.mocks.mock_websocket import MockWebSocket
    return MockWebSocket()


@pytest.fixture
async def mock_connection_manager():
    """
    Mock Connection Manager Fixture

    Example:
        async def test_broadcast(mock_connection_manager):
            from tests.mocks.mock_websocket import MockWebSocket

            ws1 = MockWebSocket("client1")
            await mock_connection_manager.connect(ws1, "client1")
            await mock_connection_manager.subscribe("client1", "price:005930")

            await mock_connection_manager.broadcast("price:005930", {"price": 80500})

            assert len(ws1.sent_messages) == 1
    """
    from tests.mocks.mock_websocket import MockConnectionManager
    return MockConnectionManager()


@pytest.fixture
def mock_heartbeat_manager():
    """
    Mock Heartbeat Manager Fixture

    Example:
        def test_heartbeat(mock_heartbeat_manager):
            mock_heartbeat_manager.record_pong("client1")
            assert mock_heartbeat_manager.is_client_alive("client1") is True
    """
    from tests.mocks.mock_websocket import MockHeartbeatManager
    return MockHeartbeatManager()


# ============================================================================
# WebSocket 테스트를 위한 추가 Fixture
# ============================================================================

@pytest.fixture
def ws_test_data():
    """
    WebSocket 테스트용 Mock 데이터
    """
    return {
        "mock_stocks": {
            "005930": {"name": "삼성전자", "base_price": 80000},
            "000660": {"name": "SK하이닉스", "base_price": 150000},
            "035420": {"name": "NAVER", "base_price": 250000},
            "005380": {"name": "현대차", "base_price": 240000},
            "028260": {"name": "삼성물산", "base_price": 140000},
        },
        "mock_price_update": {
            "type": "price_update",
            "ticker": "005930",
            "data": {
                "price": 80500,
                "change": 500,
                "change_rate": 0.62,
                "volume": 1000000,
                "bid_price": 80490,
                "ask_price": 80510,
            },
            "timestamp": "2026-02-06T00:00:00Z",
        }
    }


@pytest.fixture
async def real_connection_manager() -> AsyncGenerator:
    """
    실제 ConnectionManager Fixture (테스트용 인스턴스)
    """
    from src.websocket.server import ConnectionManager

    manager = ConnectionManager()
    yield manager

    # Clean up: 모든 연결 제거
    manager.active_connections.clear()
    manager.subscriptions.clear()


@pytest.fixture
async def real_heartbeat_manager(real_connection_manager) -> AsyncGenerator:
    """
    실제 HeartbeatManager Fixture (테스트용 인스턴스)
    """
    from src.websocket.server import HeartbeatManager

    heartbeat = HeartbeatManager(real_connection_manager)

    yield heartbeat

    # Clean up
    if heartbeat.is_running():
        await heartbeat.stop()


@pytest.fixture
def kiwoom_test_config():
    """
    Kiwoom 테스트용 설정 Fixture
    """
    from src.kiwoom.test_config import KiwoomTestConfig
    return KiwoomTestConfig()
