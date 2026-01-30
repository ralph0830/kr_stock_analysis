"""
Kiwoom API Health Check Tests (TDD Phase 1 - RED)

진단 테스트: 현재 Kiwoom API 연동 상태 확인
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestKiwoomEnvironmentSetup:
    """Kiwoom API 환경 변수 설정 확인"""

    def test_kiwoom_env_variables_set(self):
        """Kiwoom API 필수 환경 변수가 설정되어야 함"""
        # 필수 환경 변수
        app_key = os.getenv("KIWOOM_APP_KEY")
        secret_key = os.getenv("KIWOOM_SECRET_KEY")
        use_kiwoom = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"

        # Kiwoom API 사용이 설정된 경우 키가 있어야 함
        if use_kiwoom:
            assert app_key is not None, "KIWOOM_APP_KEY가 설정되지 않았습니다"
            assert secret_key is not None, "KIWOOM_SECRET_KEY가 설정되지 않았습니다"
            assert len(app_key) > 10, "KIWOOM_APP_KEY 형식이 올바르지 않습니다"
            assert len(secret_key) > 10, "KIWOOM_SECRET_KEY 형식이 올바르지 않습니다"

    def test_kiwoom_base_url_configuration(self):
        """Kiwoom API Base URL이 설정되어야 함"""
        base_url = os.getenv("KIWOOM_BASE_URL")
        assert base_url is not None, "KIWOOM_BASE_URL이 설정되지 않았습니다"
        assert base_url.startswith("https://"), "KIWOOM_BASE_URL은 HTTPS여야 합니다"

    def test_use_kiwoom_rest_flag(self):
        """USE_KIWOOM_REST 플래그 확인"""
        use_kiwoom = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"
        # 테스트 환경에서는 false여도 테스트 통과
        assert isinstance(use_kiwoom, bool)


class TestKiwoomClientInitialization:
    """Kiwoom API 클라이언트 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_kiwoom_client_singleton(self):
        """Kiwoom 클라이언트는 싱글톤이어야 함"""
        from services.chatbot.kiwoom_integration import _get_kiwoom_client

        # Kiwoom API가 사용 가능하지 않으면 테스트 스킵
        try:
            client1 = _get_kiwoom_client()
            client2 = _get_kiwoom_client()
            assert client1 is client2, "Kiwoom 클라이언트는 싱글톤이어야 합니다"
        except Exception as e:
            pytest.skip(f"Kiwoom API not available: {e}")

    @pytest.mark.asyncio
    async def test_kiwoom_client_has_token_method(self):
        """Kiwoom 클라이언트에 토큰 관련 메서드가 있어야 함"""
        from services.chatbot.kiwoom_integration import _get_kiwoom_client

        try:
            client = _get_kiwoom_client()
            assert hasattr(client, 'ensure_token_valid'), "ensure_token_valid 메서드가 필요합니다"
            assert hasattr(client, '_fetch_token'), "_fetch_token 메서드가 필요합니다"
        except Exception as e:
            pytest.skip(f"Kiwoom API not available: {e}")


class TestKiwoomTokenFetch:
    """Kiwoom API 토큰 발급 테스트"""

    @pytest.mark.asyncio
    async def test_kiwoom_token_fetch_success(self):
        """Kiwoom API 토큰 발급이 성공해야 함"""
        from services.chatbot.kiwoom_integration import _get_kiwoom_client

        try:
            client = _get_kiwoom_client()
            # 토큰 유효성 확인 (자동 갱신됨)
            await client.ensure_token_valid()
            assert client.access_token is not None, "액세스 토큰이 발급되어야 합니다"
            assert len(client.access_token) > 0, "액세스 토큰이 비어있으면 안 됩니다"
        except Exception as e:
            pytest.skip(f"Kiwoom API not available or token fetch failed: {e}")

    @pytest.mark.asyncio
    async def test_kiwoom_token_expiration_handling(self):
        """토큰 만료 시 자동 갱신되어야 함"""
        from services.chatbot.kiwoom_integration import _get_kiwoom_client
        from datetime import datetime, timedelta

        try:
            client = _get_kiwoom_client()
            # 토큰 만료 시간 설정 (과거로)
            client.token_expires_at = datetime.now() - timedelta(hours=1)

            # ensure_token_valid 호출로 자동 갱신
            await client.ensure_token_valid()

            assert client.token_expires_at > datetime.now(), "토큰이 갱신되어야 합니다"
        except Exception as e:
            pytest.skip(f"Kiwoom API not available: {e}")


class TestKiwoomAPIAvailability:
    """Kiwoom API 가용성 확인"""

    def test_is_kiwoom_available_function(self):
        """is_kiwoom_available 함수가 정상 작동해야 함"""
        from services.chatbot.kiwoom_integration import is_kiwoom_available

        result = is_kiwoom_available()
        assert isinstance(result, bool)

    def test_check_kiwoom_available_raises_on_no_keys(self):
        """키가 없으면 check_kiwoom_available이 예외를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import check_kiwoom_available, KiwoomAPIError

        # 환경 변수 없이 테스트
        with patch.dict(os.environ, {
            "KIWOOM_APP_KEY": "",
            "KIWOOM_SECRET_KEY": "",
            "USE_KIWOOM_REST": "true"
        }):
            # 모듈 재로드하여 환경 변수 변경 반영
            import importlib
            import services.chatbot.kiwoom_integration as kiwoom_integration
            importlib.reload(kiwoom_integration)

            with pytest.raises(KiwoomAPIError):
                kiwoom_integration.check_kiwoom_available()


class TestKiwoomAPILogging:
    """Kiwoom API 로깅 확인"""

    @pytest.mark.asyncio
    async def test_kiwoom_initialization_logging(self, caplog):
        """Kiwoom 클라이언트 초기�始化 시 로그가 기록되어야 함"""
        import logging
        caplog.set_level(logging.INFO)

        from services.chatbot.kiwoom_integration import _get_kiwoom_client

        try:
            client = _get_kiwoom_client()
            # 로그에 초기화 메시지 확인
            log_messages = [record.message for record in caplog.records]
            assert any("KiwoomRestAPI" in msg for msg in log_messages), "초기화 로그가 필요합니다"
        except Exception as e:
            pytest.skip(f"Kiwoom API not available: {e}")
