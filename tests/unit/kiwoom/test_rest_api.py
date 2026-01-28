"""
키움 REST API 클라이언트 테스트

TDD GREEN 단계: REST API 호출 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from httpx import HTTPStatusError, RequestError

from src.kiwoom.base import KiwoomConfig, RealtimePrice
from src.kiwoom.rest_api import KiwoomRestAPI, KiwoomAPIError


def create_mock_response(status_code: int = 200, json_data=None):
    """Mock 응답 생성 헬퍼"""
    mock_response = AsyncMock()
    mock_response.status_code = status_code

    async def mock_json():
        return json_data if json_data else {}

    mock_response.json = mock_json
    mock_response.raise_for_status = AsyncMock()
    return mock_response


class TestKiwoomRestAPIInitialization:
    """REST API 초기화 테스트"""

    def test_rest_api_initialization_with_config(self):
        """설정 객체로 초기화 테스트"""
        config = KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

        api = KiwoomRestAPI(config)

        assert api._config.app_key == "test_app_key"
        assert api._config.secret_key == "test_secret"
        assert api._access_token is None


class TestOAuth2TokenManagement:
    """OAuth2 토큰 관리 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    @pytest.mark.asyncio
    async def test_issue_token_success(self, config):
        """토큰 발급 성공 테스트"""
        api = KiwoomRestAPI(config)

        mock_response = create_mock_response(200, {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token"
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.issue_token()

            assert result is True
            assert api._access_token == "test_access_token"
            assert api._token_expires_at is not None

    @pytest.mark.asyncio
    async def test_token_refresh(self, config):
        """토큰 갱신 테스트"""
        api = KiwoomRestAPI(config)
        api._refresh_token = "test_refresh_token"

        mock_response = create_mock_response(200, {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.refresh_token()

            assert result is True
            assert api._access_token == "new_access_token"

    def test_is_token_valid(self, config):
        """토큰 유효성 확인 테스트"""
        api = KiwoomRestAPI(config)

        # 토큰 없음
        assert api.is_token_valid() is False

        # 토큰 있지만 만료됨
        api._access_token = "test_token"
        api._token_expires_at = datetime.now(timezone.utc).timestamp() - 1000
        assert api.is_token_valid() is False

        # 유효한 토큰
        api._token_expires_at = datetime.now(timezone.utc).timestamp() + 1000
        assert api.is_token_valid() is True


class TestStockPriceQuery:
    """현재가 조회 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    @pytest.mark.asyncio
    async def test_get_current_price_success(self, config):
        """현재가 조회 성공 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        mock_response = create_mock_response(200, {
            "jsonrpc": "2.0",
            "result": {
                "t0414": [
                    "005930",
                    "Samsung Elec",
                    "72500",
                    "500",
                    "0.69",
                    "72400",
                    "72600",
                    "1234567",
                ]
            }
        })

        # Mock 클라이언트 직접 설정
        mock_client = AsyncMock()

        async def mock_request(*args, **kwargs):
            return mock_response

        mock_client.request = mock_request
        api._set_client(mock_client)

        price = await api.get_current_price("005930")

        assert price is not None
        assert price.ticker == "005930"
        assert price.price == 72500


class TestOrderPlacement:
    """주문 관련 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    @pytest.mark.asyncio
    async def test_buy_market_order(self, config):
        """시장가 매수 주문 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        mock_response = create_mock_response(200, {
            "jsonrpc": "2.0",
            "result": {
                "t1102": [
                    "0",
                    "0000",
                    "005930",
                    "001",
                    "72500",
                    "10",
                    "00",
                ]
            }
        })

        mock_client = AsyncMock()

        async def mock_request(*args, **kwargs):
            return mock_response

        mock_client.request = mock_request
        api._set_client(mock_client)

        result = await api.order_buy_market("005930", 10)

        assert result is not None
        assert result.get("order_no") == "0000"


class TestAccountQuery:
    """계좌 조회 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    @pytest.mark.asyncio
    async def test_get_account_balance(self, config):
        """계좌 잔고 조회 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        mock_response = create_mock_response(200, {
            "jsonrpc": "2.0",
            "result": {
                "t0424": [
                    "005930",
                    "Samsung",
                    "10",
                    "72500",
                    "72600",
                    "1000",
                    "1.38",
                ]
            }
        })

        mock_client = AsyncMock()

        async def mock_request(*args, **kwargs):
            return mock_response

        mock_client.request = mock_request
        api._set_client(mock_client)

        balance = await api.get_account_balance()

        assert balance is not None
        assert len(balance) > 0

    @pytest.mark.asyncio
    async def test_get_account_deposit(self, config):
        """예수금 조회 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        mock_response = create_mock_response(200, {
            "jsonrpc": "2.0",
            "result": {
                "t0425": [
                    "100000000",
                    "50000000",
                    "20000000",
                    "1000000",
                ]
            }
        })

        mock_client = AsyncMock()

        async def mock_request(*args, **kwargs):
            return mock_response

        mock_client.request = mock_request
        api._set_client(mock_client)

        deposit = await api.get_account_deposit()

        assert deposit is not None
        assert deposit.get("total_deposit") == "100000000"


class TestAPIErrorHandling:
    """API 에러 처리 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    @pytest.mark.asyncio
    async def test_network_error_retry(self, config):
        """네트워크 오류 시 재시도 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        call_count = 0

        mock_client = AsyncMock()

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RequestError("Network error")
            return create_mock_response(200, {"jsonrpc": "2.0", "result": {"t0414": []}})

        mock_client.request = mock_request
        api._set_client(mock_client)

        result = await api.get_current_price("005930")
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_token_expired_auto_refresh(self, config):
        """토큰 만료 시 자동 갱신 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "old_token"
        api._refresh_token = "refresh_token"

        mock_client = AsyncMock()
        call_count = 0

        async def mock_request(method, url, *args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 첫 번째 호출: 401 에러
                mock_resp = AsyncMock()
                mock_resp.status_code = 401

                async def mock_raise():
                    raise HTTPStatusError(
                        "Token expired", request=Mock(), response=mock_resp
                    )

                mock_resp.raise_for_status = mock_raise
                return mock_resp
            else:
                # 두 번째 호출: 성공
                return create_mock_response(200, {
                    "jsonrpc": "2.0",
                    "result": {"t0414": ["005930", "", "72500", "0", "0", "72400", "72600", "0"]}
                })

        async def mock_post(*args, **kwargs):
            # 토큰 갱신
            return create_mock_response(200, {
                "access_token": "refreshed_token",
                "expires_in": 3600,
            })

        mock_client.request = mock_request
        mock_client.post = mock_post
        api._set_client(mock_client)

        result = await api.get_current_price("005930")

        assert api._access_token == "refreshed_token"
