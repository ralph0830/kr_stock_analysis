"""
API Gateway 테스트 설정
pytest fixtures 및 공통 설정
"""

import sys
from pathlib import Path

# 프로젝트 루트와 현재 서비스 경로를 sys.path에 추가
_current_dir = Path(__file__).parent.resolve()
_project_root = _current_dir.parent.parent.parent
_service_root = _current_dir.parent.parent

for path in [_project_root, _service_root, _current_dir]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# Mock 모듈이 main.py import 전에 설정되도록 먼저 로드
from unittest.mock import Mock, MagicMock, patch

# Mock 모듈 미리 설정
sys.modules['src.websocket'] = MagicMock()
sys.modules['src.websocket.routes'] = MagicMock()
sys.modules['src.websocket.server'] = MagicMock()
sys.modules['src.utils'] = MagicMock()
sys.modules['src.utils.metrics'] = MagicMock()
sys.modules['src.middleware'] = MagicMock()
sys.modules['src.middleware.metrics_middleware'] = MagicMock()
sys.modules['src.middleware.logging_middleware'] = MagicMock()
sys.modules['src.middleware.request_id'] = MagicMock()
sys.modules['src.middleware.slow_endpoint'] = MagicMock()
sys.modules['src.api_gateway'] = MagicMock()
sys.modules['src.api_gateway.kiwoom_integration'] = MagicMock()
sys.modules['src.websocket.kiwoom_bridge'] = MagicMock()
sys.modules['src.kiwoom'] = MagicMock()
sys.modules['src.kiwoom.base'] = MagicMock()
sys.modules['src.repositories.backtest_repository'] = MagicMock()
sys.modules['src.repositories.signal_repository'] = MagicMock()

# Mock 함수 설정
mock_integration = Mock()
mock_integration.startup = Mock(return_value=None)
mock_integration.shutdown = Mock(return_value=None)
mock_integration.pipeline = None
sys.modules['src.api_gateway.kiwoom_integration'].create_kiwoom_integration = Mock(return_value=mock_integration)
sys.modules['src.api_gateway.kiwoom_integration'].setup_kiwoom_routes = Mock()

# metrics_registry mock
mock_metrics_registry = Mock()
mock_metrics_registry.export.return_value = "# Mock metrics\n"
mock_metrics_registry.get_all_metrics.return_value = {}
mock_metrics_registry.reset_all = Mock()
sys.modules['src.utils.metrics'].metrics_registry = mock_metrics_registry

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_registry():
    """ServiceRegistry Mock"""
    registry = Mock()
    registry.list_services.return_value = [
        {
            "name": "vcp-scanner",
            "url": "http://localhost:5112",
            "health_check_url": "http://localhost:5112/health",
            "is_healthy": True,
        }
    ]
    registry.get_service.return_value = {
        "name": "vcp-scanner",
        "url": "http://localhost:5112",
        "health_check_url": "http://localhost:5112/health",
        "timeout": 10.0,
    }
    return registry


@pytest.fixture
def mock_db_session():
    """Database Session Mock"""
    session = MagicMock()
    session.query.return_value.order_by.return_value.first.return_value = None
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value.scalars.return_value.all.return_value = []
    return session


@pytest.fixture
def client(mock_registry, mock_db_session):
    """Test Client Fixture"""
    # Import main AFTER mocks are set up
    import importlib

    # main 모듈을 미리 import하여 mocks가 적용되도록 함
    main_module = sys.modules.get('services.api_gateway.main')
    if main_module:
        importlib.reload(main_module)

    # 패치 경로를 src로 변경 (모듈 레벨에서 패치)
    with patch('src.database.session.get_db_session') as mock_get_db:
        with patch('services.api_gateway.service_registry.get_registry') as mock_get_reg:
            mock_get_db.return_value = iter([mock_db_session])
            mock_get_reg.return_value = mock_registry

            # 지연 import 방지를 위해 app 직접 import
            from services.api_gateway.main import app
            yield TestClient(app)
