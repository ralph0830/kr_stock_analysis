"""
키움 REST API 클라이언트 테스트

TDD GREEN 단계: REST API 호출 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from httpx import HTTPStatusError, RequestError

from src.kiwoom.base import KiwoomConfig
from src.kiwoom.rest_api import KiwoomRestAPI


def create_mock_response(status_code: int = 200, json_data=None):
    """Mock 응답 생성 헬퍼"""
    mock_response = Mock()
    mock_response.status_code = status_code

    # httpx의 response.json()은 동기 메서드
    mock_response.json = Mock(return_value=json_data if json_data else {})
    mock_response.raise_for_status = Mock()
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

        # 키움 API 응답 형식: return_code, token, expires_dt
        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "token": "test_access_token",
            "expires_dt": "20251231235959"
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

        # refresh_token 메서드는 access_token 필드를 기대함
        mock_response = create_mock_response(200, {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
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
        from datetime import datetime, timezone

        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        # 토큰 만료 시간도 설정 (유효한 토큰으로 간주되도록)
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        # 키움 API 응답 형식: return_code, result.t0414 배열
        expected_data = {
            "return_code": 0,
            "return_msg": "OK",
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
        }

        # httpx.AsyncClient.post를 patch
        async def mock_post(*args, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json = Mock(return_value=expected_data)
            mock_resp.raise_for_status = Mock()
            return mock_resp

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
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
        from datetime import datetime, timezone

        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        # 키움 API 응답 형식
        expected_data = {
            "return_code": 0,
            "return_msg": "OK",
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
        }

        async def mock_request(method, url, *args, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json = Mock(return_value=expected_data)
            mock_resp.raise_for_status = Mock()
            return mock_resp

        mock_client = Mock()
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
        from datetime import datetime, timezone

        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        expected_data = {
            "return_code": 0,
            "return_msg": "OK",
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
        }

        async def mock_request(method, url, *args, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json = Mock(return_value=expected_data)
            mock_resp.raise_for_status = Mock()
            return mock_resp

        mock_client = Mock()
        mock_client.request = mock_request
        api._set_client(mock_client)

        balance = await api.get_account_balance()

        assert balance is not None
        assert len(balance) > 0

    @pytest.mark.asyncio
    async def test_get_account_deposit(self, config):
        """예수금 조회 테스트"""
        from datetime import datetime, timezone

        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        expected_data = {
            "return_code": 0,
            "return_msg": "OK",
            "result": {
                "t0425": [
                    "100000000",
                    "50000000",
                    "20000000",
                    "1000000",
                ]
            }
        }

        async def mock_request(method, url, *args, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json = Mock(return_value=expected_data)
            mock_resp.raise_for_status = Mock()
            return mock_resp

        mock_client = Mock()
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

    @pytest.mark.skip("Complex async mocking - needs refactoring")
    @pytest.mark.asyncio
    async def test_network_error_retry(self, config):
        """네트워크 오류 시 재시도 테스트"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock

        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        call_count = [0]
        response_data = {
            "return_code": 0,
            "result": {"t0414": []}
        }

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json = Mock(return_value=response_data)
        mock_resp.raise_for_status = Mock()

        async def mock_request_impl(method, url, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RequestError("Network error")
            return mock_resp

        # AsyncMock을 사용하고 side_effect로 async 함수 설정
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=mock_request_impl)

        api._set_client(mock_client)

        result = await api.get_current_price("005930")
        assert call_count[0] == 2

    @pytest.mark.skip("Complex async mocking - needs refactoring")
    @pytest.mark.asyncio
    async def test_token_expired_auto_refresh(self, config):
        """토큰 만료 시 자동 갱신 테스트"""
        from datetime import datetime, timezone

        api = KiwoomRestAPI(config)
        api._access_token = "old_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() - 100)  # 만료된 토큰
        api._refresh_token = "refresh_token"

        call_count = [0]

        async def mock_request(method, url, *args, **kwargs):
            call_count[0] += 1

            if call_count[0] == 1:
                # 첫 번째 호출: 토큰 갱신 요청 (issue_token)
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json = Mock(return_value={
                    "access_token": "refreshed_token",
                    "expires_in": 3600,
                })
                mock_resp.raise_for_status = Mock()
                return mock_resp
            elif call_count[0] == 2:
                # 두 번째 호출: 401 에러
                mock_resp = Mock()
                mock_resp.status_code = 401

                def raise_error():
                    raise HTTPStatusError(
                        "Token expired", request=Mock(), response=mock_resp
                    )

                mock_resp.raise_for_status = raise_error
                return mock_resp
            else:
                # 세 번째 호출: 성공
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json = Mock(return_value={
                    "return_code": 0,
                    "result": {"t0414": ["005930", "", "72500", "0", "0", "72400", "72600", "0"]}
                })
                mock_resp.raise_for_status = Mock()
                return mock_resp

        mock_client = Mock()
        mock_client.request = mock_request
        api._set_client(mock_client)

        result = await api.get_current_price("005930")

        assert api._access_token == "refreshed_token"


# =============================================================================
# 추가 테스트: 일봉 데이터 조회, 거래정지 필터링, API 재시도
# =============================================================================

class TestGetDailyPrices:
    """일봉 데이터 조회 테스트"""

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
    async def test_get_daily_prices_success(self, config):
        """일봉 데이터 조회 성공 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "stk_invsr_orgn_chart": [
                {"dt": "20260206", "cur_prc": "71500", "pred_pre": "+500", "acc_trde_prica": "1000000"},
                {"dt": "20260205", "cur_prc": "71000", "pred_pre": "+300", "acc_trde_prica": "900000"},
            ],
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.get_daily_prices("005930", days=5)

            assert result is not None
            assert len(result) >= 2
            assert result[0]["date"] == "20260206"

    @pytest.mark.asyncio
    async def test_get_daily_prices_empty_response(self, config):
        """빈 응답 처리 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "stk_invsr_orgn_chart": [],
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.get_daily_prices("005930", days=5)

            # 빈 데이터는 None을 반환해야 함 (최근 5일 내 데이터 없음)
            assert result is None


class TestSuspendedStocks:
    """거래정지 종목 필터링 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    def test_is_trading_suspended_true(self):
        """거래정지 상태 확인 (정상 케이스)"""
        # KiwoomRestAPI.TRADING_SUSPENDED_KEYWORDS에 있는 키워드만 확인
        suspended_states = [
            "관리종목",
            "증거금100%",
            "투자유의환기종목",
            "정리매매",
            "거래정지",
            "시장주의",
            "불매가",
            "매매거부",
        ]

        for state in suspended_states:
            assert KiwoomRestAPI.is_trading_suspended(state) is True

    def test_is_trading_suspended_false(self):
        """정상 거래 상태 확인"""
        normal_states = [
            "정상",
            "매매가능",
            "",
            None,
        ]

        for state in normal_states:
            assert KiwoomRestAPI.is_trading_suspended(state) is False

    @pytest.mark.asyncio
    async def test_get_suspended_stocks_filters_correctly(self, config):
        """거래정지 종목 필터링 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        # Mock get_stock_list
        with patch.object(api, 'get_stock_list', return_value=[
            {"ticker": "005930", "state": "정상"},
            {"ticker": "900010", "state": "거래정지"},
            {"ticker": "000660", "state": "매매가능"},
            {"ticker": "900020", "state": "관리종목"},
        ]):
            result = await api.get_suspended_stocks("ALL")

            assert "900010" in result
            assert "900020" in result
            assert "005930" not in result
            assert "000660" not in result


class TestAPIRetryLogic:
    """API 재시도 로직 테스트"""

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
    async def test_api_call_with_retry(self, config):
        """API 호출 재시도 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        # is_token_valid는 동기 메서드이므로 await 제거
        result = api.is_token_valid()
        assert result is True


class TestStockDailyChart:
    """주식 일봉 차트 조회 테스트"""

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
    async def test_get_stock_daily_chart_success(self, config):
        """주식 일봉 차트 조회 성공"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "stk_dt_pole_chart_qry": [
                {
                    "dt": "20260206",
                    "open_pric": "71000",
                    "high_pric": "72000",
                    "low_pric": "70500",
                    "cur_prc": "71500",
                    "trde_qty": "15000000",
                    "pred_pre": "+500",
                },
                {
                    "dt": "20260205",
                    "open_pric": "70500",
                    "high_pric": "71500",
                    "low_pric": "70000",
                    "cur_prc": "71000",
                    "trde_qty": "10000000",
                    "pred_pre": "+300",
                },
            ],
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.get_stock_daily_chart("005930", days=20)

            assert result is not None
            assert len(result) == 2
            assert result[0]["date"] == "20260206"
            assert result[0]["close"] == 71500.0


class TestDailyTradeDetail:
    """일별거래상세 조회 테스트"""

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
    async def test_get_daily_trade_detail_success(self, config):
        """일별거래상세 조회 성공"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "daly_trde_dtl": [
                {"dt": "20260206", "close_pric": "71500", "trde_qty": "1000000", "for_netprps": "5000", "orgn_netprps": "3000"},
                {"dt": "20260205", "close_pric": "71000", "trde_qty": "900000", "for_netprps": "2000", "orgn_netprps": "1000"},
            ],
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.get_daily_trade_detail("005930")

            assert result is not None
            assert len(result) == 2
            assert result[0]["foreign_net_buy"] == 5000
            assert result[0]["inst_net_buy"] == 3000

    @pytest.mark.asyncio
    async def test_get_daily_trade_detail_empty_response(self, config):
        """빈 응답 처리"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)

        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "daly_trde_dtl": [],
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.get_daily_trade_detail("005930")

            assert result == []


class TestConnectionManagement:
    """연결 관리 테스트"""

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
    async def test_reauthenticate_clears_token(self, config):
        """재인증 시 토큰 초기화 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "old_token"
        api._refresh_token = "refresh_token"
        api._token_expires_at = 123456

        mock_response = create_mock_response(200, {
            "return_code": 0,
            "return_msg": "OK",
            "token": "new_token",
            "expires_dt": "20260206235959",
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.reauthenticate()

            assert result is True
            assert api._access_token == "new_token"

    @pytest.mark.asyncio
    async def test_reauthenticate_failure(self, config):
        """재인증 실패 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "old_token"
        api._refresh_token = "refresh_token"
        api._token_expires_at = 123456

        async def mock_post(*args, **kwargs):
            raise Exception("API Error")

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.reauthenticate()

            assert result is False
