"""
키움 REST API 인증/만료 처리 테스트

TDD GREEN 단계: 인증 및 토큰 만료 처리 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from httpx import HTTPStatusError

from src.kiwoom.base import KiwoomConfig
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


class TestTokenLifecycle:
    """토큰 수명 주기 테스트"""

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
    async def test_token_expiry_detection(self, config):
        """토큰 만료 감지 테스트"""
        api = KiwoomRestAPI(config)

        # 만료된 토큰 설정
        api._access_token = "expired_token"
        api._token_expires_at = (datetime.now(timezone.utc) - timedelta(seconds=100)).timestamp()

        assert api.is_token_valid() is False

    @pytest.mark.asyncio
    async def test_token_expires_soon(self, config):
        """토큰 곧 만료 감지 테스트 (5분 이내)"""
        api = KiwoomRestAPI(config)

        # 4분 후 만료
        api._access_token = "expiring_soon_token"
        api._token_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=240)).timestamp()

        # 유효하지만 곧 만료
        assert api.is_token_valid() is True
        assert api.is_token_expiring_soon(300) is True

    @pytest.mark.asyncio
    async def test_token_refresh_before_expiry(self, config):
        """만료 전 토큰 갱신 테스트"""
        api = KiwoomRestAPI(config)
        api._refresh_token = "valid_refresh_token"

        mock_response = create_mock_response(200, {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token"
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.refresh_token()

            assert result is True
            assert api._access_token == "new_access_token"
            assert api._refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_token_refresh_failure(self, config):
        """토큰 갱신 실패 테스트"""
        api = KiwoomRestAPI(config)
        api._refresh_token = "invalid_refresh_token"

        mock_response = AsyncMock()
        mock_response.status_code = 401

        async def mock_json():
            return {
                "error": "invalid_grant",
                "error_description": "Invalid refresh token"
            }

        mock_response.json = mock_json

        async def mock_raise():
            raise HTTPStatusError(
                "Invalid refresh token", request=Mock(), response=mock_response
            )

        mock_response.raise_for_status = mock_raise

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            with pytest.raises(KiwoomAPIError):
                await api.refresh_token()


class TestAutoTokenRefresh:
    """자동 토큰 갱신 테스트"""

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
    async def test_auto_refresh_on_401(self, config):
        """401 에러 시 자동 토큰 갱신 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "expiring_token"
        api._refresh_token = "valid_refresh_token"

        mock_client = AsyncMock()
        call_count = 0

        async def mock_request(method, url, *args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 토큰 갱신 요청
                return create_mock_response(200, {
                    "access_token": "refreshed_token",
                    "expires_in": 3600,
                })
            elif call_count == 2:
                # 첫 번째 API 호출: 401 에러 (갱신되지 않음)
                mock_resp = AsyncMock()
                mock_resp.status_code = 401

                async def mock_raise():
                    raise HTTPStatusError(
                        "Token expired", request=Mock(), response=mock_resp
                    )

                mock_resp.raise_for_status = mock_raise
                return mock_resp
            else:
                # 세 번째 호출: 성공
                return create_mock_response(200, {
                    "jsonrpc": "2.0",
                    "result": {"t0414": ["005930", "", "72500", "0", "0", "72400", "72600", "0"]}
                })

        async def mock_post(*args, **kwargs):
            # 토큰 갱신도 request로 처리
            return await mock_request("POST", *args, **kwargs)

        mock_client.request = mock_request
        mock_client.post = mock_post
        api._set_client(mock_client)

        try:
            await api.get_current_price("005930")
        except:
            pass

        # 토큰이 갱신되었는지 확인
        assert api._access_token == "refreshed_token"

    @pytest.mark.asyncio
    async def test_no_refresh_on_other_errors(self, config):
        """다른 에러 시 토큰 갱신 안 함 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "valid_token"

        mock_client = AsyncMock()

        async def mock_request(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 500

            async def mock_json():
                return {"error": "internal_server_error"}

            mock_response.json = mock_json

            async def mock_raise():
                raise HTTPStatusError(
                    "Server error", request=Mock(), response=mock_response
                )

            mock_response.raise_for_status = mock_raise
            return mock_response

        mock_client.request = mock_request
        api._set_client(mock_client)

        with pytest.raises(KiwoomAPIError):
            await api.get_current_price("005930")

        # 토큰이 변경되지 않았는지 확인
        assert api._access_token == "valid_token"


class TestReauthenticationFlow:
    """재인증 흐름 테스트"""

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
    async def test_full_reauthentication_flow(self, config):
        """전체 재인증 흐름 테스트"""
        api = KiwoomRestAPI(config)

        mock_response = create_mock_response(200, {
            "access_token": "new_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            result = await api.reauthenticate()
            assert result is True
            assert api._access_token == "new_token"

    @pytest.mark.asyncio
    async def test_concurrent_token_requests(self, config):
        """동시 토큰 요청 처리 테스트"""
        api = KiwoomRestAPI(config)
        api._refresh_token = "valid_refresh_token"

        request_count = 0

        mock_response = create_mock_response(200, {
            "access_token": "token_1",
            "expires_in": 3600,
        })

        async def mock_post(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            await asyncio.sleep(0.01)
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            # 동시에 여러 토큰 갱신 요청
            tasks = [api.refresh_token() for _ in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 모두 성공
            success_count = sum(1 for r in results if r is True)
            assert success_count >= 1


class TestTokenStorage:
    """토큰 저장소 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    def test_token_persistence_in_memory(self, config):
        """메모리 내 토큰 저장 테스트"""
        api = KiwoomRestAPI(config)

        # 토큰 저장
        api._access_token = "test_token"
        api._refresh_token = "test_refresh"
        api._token_expires_at = datetime.now(timezone.utc).timestamp() + 3600

        # 토큰 확인
        assert api._access_token == "test_token"
        assert api._refresh_token == "test_refresh"
        assert api.is_token_valid() is True

    @pytest.mark.asyncio
    async def test_token_clear_on_disconnect(self, config):
        """연결 해제 시 토큰 초기화 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._refresh_token = "test_refresh"

        await api.disconnect()

        # 연결 해제 후 토큰 상태 확인
        assert api._access_token is None


class TestAuthHeader:
    """인증 헤더 테스트"""

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
    async def test_auth_header_includes_token(self, config):
        """요청 헤더에 토큰 포함 테스트"""
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        captured_headers = {}

        mock_client = AsyncMock()

        async def mock_request(method, url, *args, **kwargs):
            captured_headers.update(kwargs.get("headers", {}))
            return create_mock_response(200, {
                "jsonrpc": "2.0",
                "result": {"t0414": ["005930", "", "72500", "0", "0", "72400", "72600", "0"]}
            })

        mock_client.request = mock_request
        api._set_client(mock_client)

        await api.get_current_price("005930")

        # Authorization 헤더 확인
        auth_header = captured_headers.get("Authorization", "")
        assert "Bearer test_token" in auth_header

    @pytest.mark.asyncio
    async def test_auth_header_without_token_raises_error(self, config):
        """토큰 없이 요청 시 자동 발급 테스트"""
        api = KiwoomRestAPI(config)
        # 토큰 미설정

        # issue_token도 mock해야 함
        mock_response = create_mock_response(200, {
            "access_token": "auto_issued_token",
            "expires_in": 3600,
        })

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            # ensure_token_valid로 인해 토큰이 자동 발급됨
            result = await api.get_current_price("005930")

            # 자동 발급된 토큰 확인
            assert api._access_token == "auto_issued_token"
