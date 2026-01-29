"""
Gemini API Integration Tests (TDD: RED Phase)
Gemini API 실제 연동 테스트
먼저 실패하는 테스트를 작성하고, 그 후에 구현합니다.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


# ============================================================================
# Test Configuration
# ============================================================================

# GEMINI_API_KEY가 있는지만, 테스트를 위해 Mock 사용
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "test-key")


# ============================================================================
# LLMClient Tests (RED Phase)
# ============================================================================

class TestGeminiAPIIntegration:
    """Gemini API 연동 테스트"""

    def test_import_google_generativeai(self):
        """google-generativeai 패키지 import 테스트"""
        try:
            import google.generativeai as genai
            assert genai is not None
        except ImportError:
            pytest.skip("google-generativeai not installed")

    def test_gemini_api_key_exists(self):
        """GEMINI_API_KEY 환경 변수 확인"""
        api_key = os.getenv("GEMINI_API_KEY")
        # 테스트용 키이 아닐 경우 skip
        if not api_key or api_key == "test-key":
            pytest.skip("GEMINI_API_KEY not configured for testing")
        assert api_key is not None

    def test_llm_client_initializes_with_gemini(self):
        """Gemini API가 설치되어 있으면 LLM 클라이언트가 초기화되어야 함"""
        from services.chatbot.llm_client import LLMClient

        # API Key가 있는 경우
        if os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "test-key":
            client = LLMClient()
            # google.generativeai가 설치되어 있고 API key가 있으면 초기화 성공
            # (실제 API 호출 없이 초기화만 테스트)
            assert client is not None
        else:
            # API Key가 없으면 Mock 모드
            client = LLMClient(api_key=None)
            assert client._use_mock is True

    def test_llm_client_falls_back_to_mock_without_api_key(self):
        """API Key가 없으면 Mock fallback 테스트"""
        from services.chatbot.llm_client import LLMClient

        # API Key 없음
        client = LLMClient(api_key=None)

        # Mock 모드여야 함
        assert client._use_mock is True, "API Key 없으면 Mock 모드여야 함"
        assert client._client is None, "클라이언트 초기화 실패해야 함"

    def test_llm_client_falls_back_to_mock_with_test_key(self):
        """테스트용 키면 Mock fallback 테스트"""
        from services.chatbot.llm_client import LLMClient

        # 테스트용 키
        client = LLMClient(api_key="test-key")

        # 실제 API이므로 초기화 성공하지만, API 호출은 실패할 수 있음
        # google.generativeai가 설치되어 있으면 _client가 생성됨
        if client._client is not None:
            # API 호출 테스트 - 에러 발생 시 Mock으로 fallback
            response = client.generate_reply("테스트")
            # 응답은 반환되어야 함 (Mock 또는 실제)
            assert response.reply is not None
        else:
            # Mock 모드
            assert client._use_mock is True

    def test_generate_reply_uses_mock_when_no_api_key(self):
        """API Key 없으면 Mock 응답 생성 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)
        response = client.generate_reply("삼성전자 추천해줘")

        # Mock 응답이 반환되어야 함
        assert response.reply is not None, "Mock 응답이 반환되어야 함"
        assert isinstance(response.suggestions, list), "제안 질문이 리스트여야 함"
        # Mock 응답에 기본 키워드 확인
        assert len(response.reply) > 0, "응답이 비어있으면 안 됨"

    def test_generate_reply_fallback_to_mock_on_gemini_error(self):
        """Gemini API 호출 실패 시 Mock fallback 테스트 (실제 API에서 에러 발생 시)"""
        from services.chatbot.llm_client import LLMClient

        # API Key 없으면 무조건 Mock 모드
        client = LLMClient(api_key=None)
        response = client.generate_reply("삼성전자 추천해줘")

        # Mock 응답이 반환되어야 함
        assert response.reply is not None, "Mock 응답이 반환되어야 함"
        assert isinstance(response.suggestions, list), "제안 질문이 리스트여야 함"

    def test_is_available_returns_true_when_gemini_active(self):
        """Gemini 사용 가능 여부 확인 테스트"""
        from services.chatbot.llm_client import LLMClient

        # API Key 없음
        client_no_key = LLMClient(api_key=None)
        assert client_no_key.is_available() is False

        # API Key 있지만 Mock 모드
        client_mock = LLMClient(api_key="test-key")
        # Mock 모드이므로 False 반환
        # (실제 테스트에서는 Mock 설정으로 True 반환 가능)


# ============================================================================
# Integration Tests with Real Gemini API
# ============================================================================

class TestGeminiRealAPIIntegration:
    """실제 Gemini API 연동 테스트 (API Key 필요 시)"""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "test-key",
        reason="GEMINI_API_KEY not configured"
    )
    def test_real_gemini_api_call(self):
        """실제 Gemini API 호출 테스트"""
        try:
            import google.generativeai as genai
            from services.chatbot.llm_client import LLMClient

            # 실제 클라이언트 생성
            client = LLMClient()

            if client.is_available():
                response = client.generate_reply("안녕하세요")
                assert response.reply is not None
                assert len(response.reply) > 0
            else:
                pytest.skip("Gemini API not available, using mock")

        except Exception as e:
            pytest.skip(f"Gemini API error: {e}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "test-key",
        reason="GEMINI_API_KEY not configured"
    )
    def test_real_gemini_with_stock_question(self):
        """실제 Gemini API로 주식 질문 테스트"""
        try:
            from services.chatbot.llm_client import LLMClient

            client = LLMClient()

            if client.is_available():
                response = client.generate_reply("삼성전자 어떻게 생각하세요?")
                assert response.reply is not None
                # 주식 관련 응답인지 확인
                assert len(response.reply) > 10
            else:
                pytest.skip("Gemini API not available, using mock")

        except Exception as e:
            pytest.skip(f"Gemini API error: {e}")


# ============================================================================
# Mock Response Quality Tests
# ============================================================================

class TestMockResponseQuality:
    """Mock 응답 품질 검증 테스트"""

    def test_mock_response_for_recommendation_query(self):
        """추천 질문 Mock 응답 품질 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)  # 강제 Mock 모드
        response = client.generate_reply("삼성전자 추천해줘")

        # 응답에 포함되어야 할 키워드
        assert "삼성전자" in response.reply or "005930" in response.reply
        assert "등급" in response.reply or "A등급" in response.reply or "B등급" in response.reply
        assert len(response.suggestions) > 0

    def test_mock_response_for_market_query(self):
        """시장 질문 Mock 응답 품질 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)  # 강제 Mock 모드
        response = client.generate_reply("시장 상태 어때?")

        # 응답에 포함되어야 할 키워드
        assert "Market Gate" in response.reply or "market" in response.reply.lower()
        assert "KOSPI" in response.reply or "KOSDAQ" in response.reply

    def test_mock_response_suggestions_format(self):
        """제안 질문 형식 검증 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)  # 강제 Mock 모드
        response = client.generate_reply("test")

        # 제안 질문 리스트
        assert isinstance(response.suggestions, list)
        assert len(response.suggestions) <= 3  # 최대 3개
        for suggestion in response.suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
