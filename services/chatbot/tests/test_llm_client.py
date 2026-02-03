"""
LLM Client 테스트 (TDD RED Phase)

Gemini API 클라이언트 테스트
"""

import pytest
from unittest.mock import Mock, patch


class TestLLMClient:
    """LLMClient 클래스 테스트"""

    def test_llm_client_init_with_api_key(self):
        """API 키로 LLMClient 초기화 테스트"""
        from services.chatbot.llm_client import LLMClient

        with patch('services.chatbot.llm_client.os.getenv', return_value="test-api-key"):
            client = LLMClient(api_key="test-api-key")
            assert client.api_key == "test-api-key"

    def test_llm_client_init_without_api_key(self):
        """API 키 없으면 Mock 모드 활성화"""
        from services.chatbot.llm_client import LLMClient

        with patch('services.chatbot.llm_client.os.getenv', return_value=None):
            client = LLMClient()
            assert client._use_mock is True
            assert client._client is None

    def test_llm_client_init_with_test_key(self):
        """테스트 키면 Mock 모드 활성화"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key="test-key")
        assert client._use_mock is True

    def test_generate_reply_mock_mode(self):
        """Mock 모드에서 답변 생성 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)
        response = client.generate_reply("추천해줘")

        assert response.reply is not None
        assert len(response.reply) > 0
        assert isinstance(response.suggestions, list)

    def test_generate_mock_reply_for_recommendation(self):
        """추천 질문에 대한 Mock 응답 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)
        response = client.generate_reply("오늘 추천 종목은?")

        assert "추천" in response.reply or "VCP" in response.reply

    def test_generate_mock_reply_for_market(self):
        """시장 질문에 대한 Mock 응답 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)
        response = client.generate_reply("시장 상황 어떄?")

        assert "Market Gate" in response.reply or "시장" in response.reply

    def test_extract_suggestions(self):
        """추천 질문 추출 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)

        suggestions = client._extract_suggestions("삼성전자는 VCP A등급입니다. Market Gate 상태도 확인해보세요.")

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_extract_question_from_prompt(self):
        """프롬프트에서 질문 추출 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient(api_key=None)

        prompt = """
        ## 시스템 프롬프트
        주식 분석 도우미입니다.

        ## 사용자 질문
        삼성전자 추천해줘
        """

        question = client._extract_question_from_prompt(prompt)

        assert "삼성전자" in question or question.strip() == "삼성전자 추천해줘"

    def test_is_available(self):
        """LLM 사용 가능 여부 테스트"""
        from services.chatbot.llm_client import LLMClient

        # Mock 모드
        client_mock = LLMClient(api_key=None)
        assert client_mock.is_available() is False


class TestLLMResponse:
    """LLMResponse dataclass 테스트"""

    def test_llm_response_creation(self):
        """LLMResponse 생성 테스트"""
        from services.chatbot.llm_client import LLMResponse

        response = LLMResponse(
            reply="테스트 응답",
            suggestions=["추천", "시장"],
            usage={"tokens": 100}
        )

        assert response.reply == "테스트 응답"
        assert len(response.suggestions) == 2
        assert response.usage["tokens"] == 100


class TestGetLLMClient:
    """get_llm_client 싱글톤 테스트"""

    def test_get_llm_client_singleton(self):
        """get_llm_client 싱글톤 테스트"""
        from services.chatbot.llm_client import get_llm_client, _llm_client

        # 첫 번째 호출
        client1 = get_llm_client()
        # 두 번째 호출
        client2 = get_llm_client()

        assert client1 is client2

    def test_get_llm_client_fallback_to_mock(self):
        """초기화 실패 시 Mock 모드로 fallback"""
        from services.chatbot.llm_client import get_llm_client

        # 이미 초기화되어 있으면 그대로 사용
        client = get_llm_client()
        assert client is not None
        assert hasattr(client, 'generate_reply')
