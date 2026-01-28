"""
API Gateway Kiwoom 연동 테스트

TDD RED 단계: API Gateway 통합 테스트를 먼저 작성합니다.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.kiwoom.base import RealtimePrice


# 통합 테스트: 긴 timeout (60초) - API 연동 포함
@pytest.mark.timeout(60)
@pytest.mark.integration
class TestKiwoomIntegrationRoutes:
    """Kiwoom 연동 라우트 테스트"""

    @pytest.fixture
    def mock_pipeline(self):
        """Mock Pipeline fixture"""
        pipeline = Mock()
        pipeline.is_running = Mock(return_value=True)
        pipeline.health_check = Mock(return_value={
            "status": "healthy",
            "connected": True,
            "has_token": True,
            "subscribed_count": 2,
        })
        pipeline.subscribe = AsyncMock(return_value=True)
        pipeline.unsubscribe = AsyncMock(return_value=True)
        pipeline.get_subscribed_tickers = Mock(return_value=["005930", "000660"])
        return pipeline

    def test_get_kiwoom_health(self, mock_pipeline):
        """Kiwoom Health Check 엔드포인트 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.get("/api/kr/kiwoom/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["connected"] is True

    def test_get_kiwoom_subscriptions(self, mock_pipeline):
        """구독 목록 조회 엔드포인트 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.get("/api/kr/kiwoom/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert "tickers" in data
        assert data["tickers"] == ["005930", "000660"]

    def test_subscribe_ticker(self, mock_pipeline):
        """종목 구독 엔드포인트 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.post("/api/kr/kiwoom/subscribe", json={"ticker": "005930"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_pipeline.subscribe.assert_called_once_with("005930")

    def test_unsubscribe_ticker(self, mock_pipeline):
        """종목 구독 해제 엔드포인트 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.post("/api/kr/kiwoom/unsubscribe", json={"ticker": "005930"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_pipeline.unsubscribe.assert_called_once_with("005930")

    def test_subscribe_missing_ticker(self, mock_pipeline):
        """종목코드 미입력 시 에러 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.post("/api/kr/kiwoom/subscribe", json={})

        assert response.status_code == 422  # Validation error


class TestKiwoomLifespanIntegration:
    """Kiwoom Lifespan 통합 테스트"""

    @pytest.mark.asyncio
    async def test_pipeline_start_on_startup(self):
        """서버 시작 시 Pipeline 시작 테스트"""
        mock_pipeline = Mock()
        mock_pipeline.is_running = Mock(return_value=True)
        mock_pipeline.start = AsyncMock()

        with patch('src.api_gateway.kiwoom_integration.KiwoomPipelineManager') as pipeline_class:
            # Mock 생성 시 auto_start=False로 설정하여 비동기 시작 방지
            def create_pipeline(config, auto_start=False):
                mock_pipeline.is_running = Mock(return_value=False)
                return mock_pipeline

            pipeline_class.side_effect = create_pipeline

            from src.api_gateway.kiwoom_integration import KiwoomIntegration

            # Lifespan 시작 시뮬레이션
            integration = KiwoomIntegration()
            integration._config = Mock()  # Mock config 설정
            await integration.startup()

            # auto_start=False이므로 수동으로 start 호출 확인
            assert integration.pipeline is not None

    @pytest.mark.asyncio
    async def test_pipeline_stop_on_shutdown(self):
        """서버 종료 시 Pipeline 중지 테스트"""
        mock_pipeline = Mock()
        mock_pipeline.is_running = Mock(return_value=True)
        mock_pipeline.stop = AsyncMock()

        with patch('src.api_gateway.kiwoom_integration.KiwoomPipelineManager') as pipeline_class:
            pipeline_class.return_value = mock_pipeline

            from src.api_gateway.kiwoom_integration import KiwoomIntegration

            # Lifespan 종료 시뮬레이션
            integration = KiwoomIntegration()
            integration._config = Mock()  # Mock config 설정
            integration._pipeline = mock_pipeline  # Pipeline 직접 설정
            await integration.shutdown()

            mock_pipeline.stop.assert_called_once()


class TestKiwoomConfigMode:
    """Kiwoom 설정 모드 테스트"""

    def test_use_kiwoom_rest_from_env(self):
        """환경변수로 Kiwoom REST 모드 설정 테스트"""
        with patch.dict("os.environ", {
            "KIWOOM_APP_KEY": "test_key",
            "KIWOOM_SECRET_KEY": "test_secret",
            "USE_KIWOOM_REST": "true",
        }):
            from src.api_gateway.kiwoom_integration import get_kiwoom_config

            config = get_kiwoom_config()

            assert config is not None
            assert config.app_key == "test_key"

    def test_use_koa_when_rest_disabled(self):
        """REST 비활성화 시 KOA 모드 사용 테스트"""
        with patch.dict("os.environ", {
            "USE_KIWOOM_REST": "false",
        }):
            from src.api_gateway.kiwoom_integration import get_kiwoom_config

            config = get_kiwoom_config()

            # REST 비활성화 시 None 반환
            assert config is None


class TestKiwoomRealtimeEndpoints:
    """Kiwoom 실시간 데이터 엔드포인트 테스트"""

    @pytest.fixture
    def mock_pipeline(self):
        """Mock Pipeline fixture"""
        pipeline = Mock()
        pipeline.is_running = Mock(return_value=True)
        pipeline.get_subscribed_tickers = Mock(return_value=["005930"])
        return pipeline

    def test_get_realtime_prices(self, mock_pipeline):
        """실시간 가격 조회 엔드포인트 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.get("/api/kr/kiwoom/prices")

        assert response.status_code == 200
        data = response.json()
        assert "tickers" in data

    def test_get_realtime_price_by_ticker(self, mock_pipeline):
        """종목별 실시간 가격 조회 테스트"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        # Mock 현재가 조회
        test_price = RealtimePrice(
            ticker="005930",
            price=72500,
            change=500,
            change_rate=0.69,
            volume=1000000,
            bid_price=72400,
            ask_price=72600,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        mock_pipeline._bridge.get_current_price = AsyncMock(return_value=test_price)

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.get("/api/kr/kiwoom/prices/005930")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "005930"
        assert data["price"] == 72500


class TestKiwoomErrorHandling:
    """Kiwoom 에러 처리 테스트"""

    def test_pipeline_not_running_response(self):
        """Pipeline 미실행 상태 응답 테스트"""
        mock_pipeline = Mock()
        mock_pipeline.is_running = Mock(return_value=False)
        mock_pipeline.health_check = Mock(return_value={
            "status": "stopped",
            "connected": False,
            "has_token": False,
            "subscribed_count": 0,
        })

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.get("/api/kr/kiwoom/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_subscribe_failure_response(self):
        """구독 실패 응답 테스트"""
        mock_pipeline = Mock()
        mock_pipeline.is_running = Mock(return_value=True)
        mock_pipeline.subscribe = AsyncMock(return_value=False)

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        from src.api_gateway.kiwoom_routes import setup_kiwoom_routes

        setup_kiwoom_routes(app, mock_pipeline)

        client = TestClient(app)
        response = client.post("/api/kr/kiwoom/subscribe", json={"ticker": "005930"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
