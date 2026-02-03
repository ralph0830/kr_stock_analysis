"""
API Gateway API 테스트 (TDD RED Phase)

FastAPI 엔드포인트 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import contextlib


# Mock 모듈 사전 설정 (main import 전)
from unittest.mock import MagicMock

sys.modules['src.websocket'] = MagicMock()
sys.modules['src.websocket.routes'] = MagicMock()
sys.modules['src.websocket.server'] = MagicMock()
sys.modules['src.websocket.price_provider'] = MagicMock()
sys.modules['src.utils'] = MagicMock()
sys.modules['src.utils.metrics'] = MagicMock()
sys.modules['src.utils.logging_config'] = MagicMock()
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


@pytest.fixture
def mock_app():
    """FastAPI 앱 Mock Fixture"""
    from services.api_gateway.main import app

    # Mock lifespan을 빈 컨텍스트 매니저로 대체
    @contextlib.asynccontextmanager
    async def mock_lifespan(app):
        yield

    app.router.lifespan_context = mock_lifespan
    return app


class TestHealthEndpoint:
    """헬스체크 엔드포인트 테스트"""

    def test_health_endpoint(self, mock_app):
        """GET /health 헬스체크 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(mock_app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"
        assert "version" in data

    def test_root_endpoint(self, mock_app):
        """GET / 루트 엔드포인트 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(mock_app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Ralph Stock API Gateway"
        assert "docs" in data


class TestMetricsEndpoint:
    """메트릭 엔드포인트 테스트"""

    def test_prometheus_metrics(self, mock_app):
        """GET /metrics Prometheus 텍스트 형식 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(mock_app)
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_json_metrics(self, mock_app):
        """GET /api/metrics JSON 형식 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(mock_app)
        response = client.get("/api/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total" in data
        assert isinstance(data["metrics"], list)

    def test_reset_metrics(self, mock_app):
        """POST /api/metrics/reset 메트릭 리셋 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(mock_app)
        response = client.post("/api/metrics/reset")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestMarketGateEndpoint:
    """Market Gate 엔드포인트 테스트"""

    def test_market_gate_empty_db(self, mock_app):
        """DB 비어있을 때 Market Gate 테스트"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        # Mock DB 세션
        mock_session = MagicMock()
        mock_session.query.return_value.order_by.return_value.first.return_value = None

        with patch('services.api_gateway.main.get_db_session') as mock_get_db:
            mock_get_db.return_value = iter([mock_session])

            response = client.get("/api/kr/market-gate")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["GREEN", "YELLOW", "RED"]
            assert "sectors" in data


class TestBacktestKPIEndpoint:
    """백테스트 KPI 엔드포인트 테스트"""

    def test_backtest_kpi_empty_db(self, mock_app):
        """DB 비어있을 때 백테스트 KPI 테스트"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch, Mock

        client = TestClient(mock_app)

        mock_session = MagicMock()
        mock_repo = Mock()
        mock_repo.get_summary.return_value = {
            "total_backtests": 0,
            "avg_win_rate": None,
            "avg_return_pct": None,
        }

        with patch('services.api_gateway.main.get_db_session') as mock_get_db:
            with patch('services.api_gateway.main.BacktestRepository', return_value=mock_repo):
                mock_get_db.return_value = iter([mock_session])

                response = client.get("/api/kr/backtest-kpi")

                assert response.status_code == 200
                data = response.json()
                assert "vcp" in data
                assert "closing_bet" in data


class TestStockEndpoints:
    """종목 관련 엔드포인트 테스트"""

    def test_stock_detail_not_found(self, mock_app):
        """종목 없을 때 404 반환 테스트"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = None

        with patch('services.api_gateway.main.StockRepository', return_value=mock_repo):
            response = client.get("/api/kr/stocks/000000")

            assert response.status_code == 404

    def test_stock_chart_not_found(self, mock_app):
        """종목 차트 404 테스트"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = None

        with patch('services.api_gateway.main.StockRepository', return_value=mock_repo):
            response = client.get("/api/kr/stocks/000000/chart")

            assert response.status_code == 404


class TestRealtimePricesEndpoint:
    """실시간 가격 엔드포인트 테스트"""

    def test_realtime_prices_empty(self, mock_app):
        """실시간 가격 조회 (빈 요청) 테스트"""
        from fastapi.testclient import TestClient

        client = TestClient(mock_app)
        response = client.post("/api/kr/realtime-prices", json={"tickers": []})

        assert response.status_code == 200
        data = response.json()
        assert "prices" in data


class TestJonggaV2Endpoints:
    """종가베팅 V2 엔드포인트 테스트"""

    def test_jongga_v2_latest_service_unavailable(self, mock_app):
        """Signal Engine unavailable 시 503 반환"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        mock_registry = Mock()
        mock_registry.get_service.return_value = None

        with patch('services.api_gateway.main.get_registry', return_value=mock_registry):
            response = client.get("/api/kr/jongga-v2/latest")

            assert response.status_code == 503

    def test_jongga_v2_analyze_service_unavailable(self, mock_app):
        """종가베팅 V2 분석 - 서비스 unavailable 시 503"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        mock_registry = Mock()
        mock_registry.get_service.return_value = None

        with patch('services.api_gateway.main.get_registry', return_value=mock_registry):
            response = client.post("/api/kr/jongga-v2/analyze", json={"ticker": "005930"})

            assert response.status_code == 503


class TestSignalsEndpoint:
    """시그널 엔드포인트 테스트"""

    def test_signals_service_unavailable(self, mock_app):
        """VCP Scanner unavailable 시 503 반환"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        mock_registry = Mock()
        mock_registry.get_service.return_value = None

        with patch('services.api_gateway.main.get_registry', return_value=mock_registry):
            response = client.get("/api/kr/signals")

            assert response.status_code == 503


class TestErrorHandling:
    """에러 핸들링 테스트"""

    def test_http_exception_handling(self, mock_app):
        """HTTP 예외 처리 테스트"""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        client = TestClient(mock_app)

        with patch('services.api_gateway.main.StockRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_ticker.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/kr/stocks/999999")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
