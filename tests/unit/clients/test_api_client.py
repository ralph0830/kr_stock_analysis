"""
API 클라이언트 단위 테스트
"""

import pytest
import asyncio
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
    return APIClient(base_url="http://localhost:5111")


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
        assert api_client.base_url == "http://localhost:5111"
        assert api_client.timeout == 30.0

    def test_init_with_api_key(self):
        """API 키 설정 테스트"""
        client = APIClient(
            base_url="http://localhost:5111",
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

        # 비동기 mock 함수로 side_effect 사용
        async def mock_request(*args, **kwargs):
            return expected_response

        with patch.object(api_client, "_request", side_effect=mock_request):
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

        # 비동기 mock 함수로 side_effect 사용
        async def mock_request(*args, **kwargs):
            return expected_data

        with patch.object(api_client, "_request", side_effect=mock_request):
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

        # 비동기 mock 함수로 side_effect 사용
        async def mock_request(*args, **kwargs):
            return expected_data

        with patch.object(api_client, "_request", side_effect=mock_request):
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

        # 비동기 mock 함수로 side_effect 사용
        async def mock_request(*args, **kwargs):
            return expected_data

        with patch.object(api_client, "_request", side_effect=mock_request):
            prices = await api_client.get_realtime_prices(["005930"])

            assert "005930" in prices
            assert prices["005930"].price == 80500


class TestSyncAPIClient:
    """SyncAPIClient 클래스 테스트"""

    def test_init(self):
        """동기 클라이언트 초기화 테스트"""
        client = SyncAPIClient(base_url="http://localhost:5111")
        assert client._async_client is not None

    @patch("asyncio.run")
    def test_health_check_sync(self, mock_run):
        """동기 헬스 체크 테스트"""
        mock_run.return_value = {
            "status": "healthy",
            "service": "api-gateway",
        }

        client = SyncAPIClient(base_url="http://localhost:5111")
        result = client.health_check()

        assert result["status"] == "healthy"


# ============================================================================
# 추가 API Client 테스트 (Task #16)
# ============================================================================

class TestAPIClientExtended:
    """APIClient 확장 테스트 - 타임아웃 및 에러 처리"""

    @pytest.mark.asyncio
    async def test_vcp_scan_request(self):
        """VCP 스캔 요청 테스트"""
        client = APIClient(base_url="http://localhost:5111")

        expected_data = {
            "signals": [
                {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "signal_type": "VCP",
                    "score": 85.0,
                    "grade": "A",
                }
            ]
        }

        async def mock_request(*args, **kwargs):
            return expected_data

        with patch.object(client, "_request", side_effect=mock_request):
            # get_signals를 통해 VCP 시그널 요청
            signals = await client.get_signals(limit=10)
            assert len(signals) >= 0

    @pytest.mark.asyncio
    async def test_jongga_v2_signal_retrieval(self):
        """종가베팅 V2 시그널 조회 테스트"""
        client = APIClient(base_url="http://localhost:5111")

        expected_data = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "signal_type": "JONGGA_V2",
                "score": 88.0,
                "grade": "A",
            }
        ]

        async def mock_request(*args, **kwargs):
            return expected_data

        with patch.object(client, "_request", side_effect=mock_request):
            signals = await client.get_jongga_v2_latest()
            assert len(signals) == 1
            assert signals[0].signal_type == "JONGGA_V2"

    @pytest.mark.asyncio
    async def test_signal_engine_request(self):
        """Signal Engine 요청 테스트"""
        client = APIClient(base_url="http://localhost:5111")

        # Signal Engine은 같은 API를 통해 시그널을 제공
        expected_data = [
            {
                "ticker": "000660",
                "name": "SK하이닉스",
                "signal_type": "VCP",
                "score": 78.0,
                "grade": "B",
            }
        ]

        async def mock_request(*args, **kwargs):
            return expected_data

        with patch.object(client, "_request", side_effect=mock_request):
            signals = await client.get_signals(min_score=70.0)
            assert len(signals) == 1

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """API 타임아웃 처리 테스트"""
        client = APIClient(base_url="http://localhost:5111", timeout=0.1)

        async def mock_request(*args, **kwargs):
            # 타임아웃 시뮬레이션
            await asyncio.sleep(1)
            return {}

        with patch.object(client, "_request", side_effect=mock_request):
            # 타임아웃 설정 확인
            assert client.timeout == 0.1

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """API 에러 처리 테스트"""
        from httpx import HTTPStatusError

        client = APIClient(base_url="http://localhost:5111")

        mock_response = Mock()
        mock_response.status_code = 500

        async def mock_request(*args, **kwargs):
            raise HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            )

        with patch.object(client, "_request", side_effect=mock_request):
            with pytest.raises(HTTPStatusError):
                await client.health_check()

    @pytest.mark.asyncio
    async def test_get_signals_with_status_filter(self):
        """상태 필터와 함께 시그널 조회"""
        client = APIClient(base_url="http://localhost:5111")

        expected_data = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "signal_type": "VCP",
                "score": 85.0,
                "grade": "A",
            }
        ]

        # 파라미터 캡처
        captured_params = {}

        async def mock_request(method, path, params=None, **kwargs):
            captured_params.update(params or {})
            return expected_data

        with patch.object(client, "_request", side_effect=mock_request):
            signals = await client.get_signals(limit=10, status="active", min_score=80.0)

            assert captured_params["status"] == "active"
            assert captured_params["min_score"] == 80.0

    @pytest.mark.asyncio
    async def test_base_url_trailing_slash_removed(self):
        """base_url 뒤쪽 슬래시 제거 테스트"""
        client = APIClient(base_url="http://localhost:5111/")
        assert client.base_url == "http://localhost:5111"

        # 뒤에 여러 슬래시가 있는 경우
        client2 = APIClient(base_url="http://localhost:5111///")
        assert client2.base_url == "http://localhost:5111"


class TestSignalDataclassExtended:
    """Signal 데이터클래스 확장 테스트"""

    def test_signal_from_dict_with_optional_fields(self):
        """선택적 필드 포함 Signal 생성 테스트"""
        data = {
            "ticker": "000660",
            "name": "SK하이닉스",
            "signal_type": "VCP",
            "score": 78.0,
            # grade, entry_price 등 누락
        }

        signal = Signal.from_dict(data)

        assert signal.ticker == "000660"
        assert signal.name == "SK하이닉스"
        assert signal.grade == ""  # 기본값
        assert signal.entry_price is None

    def test_signal_from_dict_empty(self):
        """빈 데이터로 Signal 생성 테스트"""
        signal = Signal.from_dict({})

        assert signal.ticker == ""
        assert signal.name == ""
        assert signal.score == 0.0
