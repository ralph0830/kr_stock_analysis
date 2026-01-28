"""
API 클라이언트 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from src.clients.api_client import (
    APIClient,
    SyncAPIClient,
    Signal,
    MarketGateStatus,
    StockPrice,
)


@pytest.fixture
def api_client():
    return APIClient(base_url="http://localhost:8000")


class TestSignalDataclass:
    """Signal 데이터클래스 테스트"""

    def test_signal_from_dict(self):
        """딕셔너리에서 Signal 객체 생성"""
        data = {
            "ticker": "005930",
            "name": "삼성전자",
            "signal_type": "VCP",
            "score": 85.5,
            "grade": "A",
            "entry_price": 80000,
            "target_price": 88000,
            "created_at": "2024-01-15T10:30:00",
        }

        signal = Signal.from_dict(data)

        assert signal.ticker == "005930"
        assert signal.name == "삼성전자"
        assert signal.signal_type == "VCP"
        assert signal.score == 85.5
        assert signal.grade == "A"
        assert signal.entry_price == 80000
        assert signal.target_price == 88000


class TestMarketGateStatusDataclass:
    """MarketGateStatus 데이터클래스 테스트"""

    def test_market_gate_status_from_dict(self):
        """딕셔너리에서 MarketGateStatus 객체 생성"""
        data = {
            "status": "GREEN",
            "level": 1,
            "kospi_status": "GREEN",
            "kosdaq_status": "GREEN",
            "updated_at": "2024-01-15T10:30:00",
        }

        status = MarketGateStatus.from_dict(data)

        assert status.status == "GREEN"
        assert status.level == 1


class TestStockPriceDataclass:
    """StockPrice 데이터클래스 테스트"""

    def test_stock_price_from_dict(self):
        """딕셔너리에서 StockPrice 객체 생성"""
        data = {
            "ticker": "005930",
            "name": "삼성전자",
            "price": 80500,
            "change": 500,
            "change_percent": 0.62,
            "volume": 1000000,
        }

        price = StockPrice.from_dict(data)

        assert price.ticker == "005930"
        assert price.price == 80500


class TestAPIClient:
    """APIClient 클래스 테스트"""

    def test_init(self, api_client):
        """클라이언트 초기화 테스트"""
        assert api_client.base_url == "http://localhost:8000"
        assert api_client.timeout == 30.0

    def test_init_with_api_key(self):
        """API 키 설정 테스트"""
        client = APIClient(
            base_url="http://localhost:8000",
            api_key="test-key-123",
        )

        assert client.headers["X-API-Key"] == "test-key-123"

    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """헬스 체크 요청 테스트"""
        expected_response = {
            "status": "healthy",
            "service": "api-gateway",
            "version": "2.0.0",
        }

        mock_response = Mock()
        mock_response.json = AsyncMock(return_value=expected_response)

        mock_httpx_client = AsyncMock()
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        # Mock async context manager
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_httpx_client)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            result = await api_client.health_check()

            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_signals(self, api_client):
        """시그널 조회 테스트"""
        expected_data = [{
            "ticker": "005930",
            "name": "삼성전자",
            "signal_type": "VCP",
            "score": 85.5,
            "grade": "A",
        }]

        mock_response = Mock()
        mock_response.json = AsyncMock(return_value=expected_data)

        mock_httpx_client = AsyncMock()
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_httpx_client)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            signals = await api_client.get_signals(limit=10)

            assert len(signals) == 1
            assert signals[0].ticker == "005930"

    @pytest.mark.asyncio
    async def test_get_market_gate(self, api_client):
        """Market Gate 상태 조회 테스트"""
        expected_data = {
            "status": "GREEN",
            "level": 1,
            "kospi_status": "GREEN",
            "kosdaq_status": "GREEN",
        }

        mock_response = Mock()
        mock_response.json = AsyncMock(return_value=expected_data)

        mock_httpx_client = AsyncMock()
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_httpx_client)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            status = await api_client.get_market_gate()

            assert status.status == "GREEN"

    @pytest.mark.asyncio
    async def test_get_realtime_prices(self, api_client):
        """실시간 가격 조회 테스트"""
        expected_data = {
            "prices": {
                "005930": {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "price": 80500,
                    "change": 500,
                    "change_percent": 0.62,
                    "volume": 1000000,
                }
            }
        }

        mock_response = Mock()
        mock_response.json = AsyncMock(return_value=expected_data)

        mock_httpx_client = AsyncMock()
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_httpx_client)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            prices = await api_client.get_realtime_prices(["005930"])

            assert "005930" in prices
            assert prices["005930"].price == 80500


class TestSyncAPIClient:
    """SyncAPIClient 클래스 테스트"""

    def test_init(self):
        """동기 클라이언트 초기화 테스트"""
        client = SyncAPIClient(base_url="http://localhost:8000")
        assert client._async_client is not None

    @patch("src.clients.api_client.asyncio.run")
    def test_health_check_sync(self, mock_run):
        """동기 헬스 체크 테스트"""
        mock_run.return_value = {
            "status": "healthy",
            "service": "api-gateway",
        }

        client = SyncAPIClient(base_url="http://localhost:8000")
        result = client.health_check()

        assert result["status"] == "healthy"
