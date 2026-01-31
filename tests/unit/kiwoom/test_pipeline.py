"""
키움 Pipeline Manager 테스트

TDD RED 단계: Pipeline 관리자 테스트를 먼저 작성합니다.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.kiwoom.base import KiwoomConfig
from src.kiwoom.pipeline import KiwoomPipelineManager


# Pipeline 테스트: 비동기 작업 포함, 중간 timeout (15초)
@pytest.mark.timeout(15)
class TestPipelineInitialization:
    """Pipeline 초기화 테스트"""

    def test_pipeline_initialization_with_config(self):
        """Config로 Pipeline 초기화 테스트"""
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,  # Mock 모드는 더 이상 지원하지 않음
        )

        # KiwoomWebSocket와 KiwoomRestAPI를 모의
        mock_bridge = Mock()
        mock_bridge.is_connected.return_value = False
        mock_rest_api = Mock()

        with patch('src.kiwoom.service.KiwoomWebSocket', return_value=mock_bridge), \
             patch('src.kiwoom.service.KiwoomRestAPI', return_value=mock_rest_api):

            pipeline = KiwoomPipelineManager(config)

            assert pipeline._config is config
            assert pipeline.is_running() is False

    def test_pipeline_initialization_with_bridge(self):
        """Bridge로 Pipeline 초기화 테스트"""
        mock_bridge = Mock()
        mock_bridge.is_connected.return_value = False

        pipeline = KiwoomPipelineManager(bridge=mock_bridge)

        assert pipeline._bridge is mock_bridge
        assert pipeline.is_running() is False


class TestPipelineLifecycle:
    """Pipeline 라이프사이클 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = False
        bridge.connect = AsyncMock(return_value=True)
        bridge.disconnect = AsyncMock()
        bridge.has_valid_token = Mock(return_value=True)
        bridge.subscribe_realtime = AsyncMock(return_value=True)
        bridge.unsubscribe_realtime = AsyncMock(return_value=True)
        bridge.get_subscribe_list = Mock(return_value=[])
        return bridge

    @pytest.mark.asyncio
    async def test_pipeline_start(self, mock_bridge):
        """Pipeline 시작 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)

        await pipeline.start()

        assert pipeline.is_running() is True
        mock_bridge.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_stop(self, mock_bridge):
        """Pipeline 중지 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        await pipeline.start()

        await pipeline.stop()

        assert pipeline.is_running() is False
        mock_bridge.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_restart(self, mock_bridge):
        """Pipeline 재시작 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        await pipeline.start()
        await pipeline.stop()

        await pipeline.start()

        assert pipeline.is_running() is True
        assert mock_bridge.connect.call_count == 2


class TestPipelineSubscription:
    """Pipeline 구독 관리 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = True
        bridge.subscribe_realtime = AsyncMock(return_value=True)
        bridge.unsubscribe_realtime = AsyncMock(return_value=True)
        bridge.get_subscribe_list = Mock(return_value=[])
        return bridge

    @pytest.mark.asyncio
    async def test_subscribe_ticker(self, mock_bridge):
        """종목 구독 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        pipeline._running = True
        pipeline._service._running = True  # Service 상태도 동기화

        result = await pipeline.subscribe("005930")

        assert result is True
        mock_bridge.subscribe_realtime.assert_called_once_with("005930")

    @pytest.mark.asyncio
    async def test_subscribe_multiple_tickers(self, mock_bridge):
        """여러 종목 구독 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        pipeline._running = True
        pipeline._service._running = True  # Service 상태도 동기화
        tickers = ["005930", "000660", "035420"]

        results = await pipeline.subscribe_many(tickers)

        assert len(results) == 3
        assert all(r is True for r in results)
        assert mock_bridge.subscribe_realtime.call_count == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_ticker(self, mock_bridge):
        """종목 구독 해제 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        pipeline._running = True

        result = await pipeline.unsubscribe("005930")

        assert result is True
        mock_bridge.unsubscribe_realtime.assert_called_once_with("005930")

    @pytest.mark.asyncio
    async def test_get_subscribed_list(self, mock_bridge):
        """구독 목록 조회 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        mock_bridge.get_subscribe_list.return_value = ["005930", "000660"]

        tickers = pipeline.get_subscribed_tickers()

        assert tickers == ["005930", "000660"]


class TestPipelineHealthCheck:
    """Pipeline Health Check 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = True
        bridge.has_valid_token.return_value = True
        bridge.get_subscribe_list = Mock(return_value=["005930"])
        return bridge

    def test_health_check_when_running(self, mock_bridge):
        """실행 중 Health Check 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        pipeline._running = True

        health = pipeline.health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["has_token"] is True
        assert health["subscribed_count"] == 1

    def test_health_check_when_stopped(self, mock_bridge):
        """중지 상태 Health Check 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        pipeline._running = False

        health = pipeline.health_check()

        assert health["status"] == "stopped"

    def test_health_check_without_connection(self, mock_bridge):
        """연결 없는 Health Check 테스트"""
        mock_bridge.is_connected.return_value = False
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)
        pipeline._running = True

        health = pipeline.health_check()

        assert health["status"] == "unhealthy"
        assert health["connected"] is False


class TestPipelineAutoStart:
    """Pipeline 자동 시작 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = False
        bridge.connect = AsyncMock(return_value=True)
        bridge.disconnect = AsyncMock()
        return bridge

    @pytest.mark.asyncio
    async def test_auto_start_on_creation(self, mock_bridge):
        """생성 시 자동 시작 테스트"""
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,  # Mock 모드는 더 이상 지원하지 않음
        )

        mock_rest_api = Mock()

        with patch('src.kiwoom.service.KiwoomWebSocket', return_value=mock_bridge), \
             patch('src.kiwoom.service.KiwoomRestAPI', return_value=mock_rest_api):

            pipeline = KiwoomPipelineManager(config, auto_start=True)

            # 자동 시작은 비동기 태스크로 실행되므로 조금 대기
            await asyncio.sleep(0.01)
            assert pipeline.is_running() is True

    @pytest.mark.asyncio
    async def test_no_auto_start_by_default(self, mock_bridge):
        """기본적으로 자동 시작 안 함 테스트"""
        config = KiwoomConfig(
            app_key="test_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,  # Mock 모드는 더 이상 지원하지 않음
        )

        mock_rest_api = Mock()

        with patch('src.kiwoom.service.KiwoomWebSocket', return_value=mock_bridge), \
             patch('src.kiwoom.service.KiwoomRestAPI', return_value=mock_rest_api):

            pipeline = KiwoomPipelineManager(config, auto_start=False)

            # 자동 시작 비활성화 상태 확인
            await asyncio.sleep(0.01)
            assert pipeline.is_running() is False


class TestPipelineIntegration:
    """Pipeline 통합 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = True
        bridge.has_valid_token.return_value = True
        bridge.connect = AsyncMock(return_value=True)
        bridge.disconnect = AsyncMock()
        bridge.subscribe_realtime = AsyncMock(return_value=True)
        bridge.get_subscribe_list = Mock(return_value=[])
        bridge.register_event = Mock()
        return bridge

    @pytest.mark.asyncio
    async def test_full_pipeline_workflow(self, mock_bridge):
        """전체 Pipeline 워크플로우 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)

        # 1. 시작
        await pipeline.start()
        assert pipeline.is_running() is True

        # 2. 구독
        await pipeline.subscribe("005930")
        await pipeline.subscribe("000660")

        # 3. Health Check
        health = pipeline.health_check()
        assert health["status"] == "healthy"

        # 4. 중지
        await pipeline.stop()
        assert pipeline.is_running() is False


class TestPipelineErrorHandling:
    """Pipeline 에러 처리 테스트"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock Bridge fixture"""
        bridge = Mock()
        bridge.is_connected.return_value = False
        bridge.connect = AsyncMock(return_value=False)  # 연결 실패
        bridge.disconnect = AsyncMock()
        return bridge

    @pytest.mark.asyncio
    async def test_start_failure_handling(self, mock_bridge):
        """시작 실패 처리 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)

        with pytest.raises(RuntimeError):
            await pipeline.start()

        assert pipeline.is_running() is False

    @pytest.mark.asyncio
    async def test_subscribe_when_not_running(self, mock_bridge):
        """미실행 상태에서 구독 테스트"""
        pipeline = KiwoomPipelineManager(bridge=mock_bridge)

        result = await pipeline.subscribe("005930")

        assert result is False
