"""
Chatbot LLM Client Unit Tests
LLM 연동 기능을 테스트합니다.
"""

from unittest.mock import patch


# ============================================================================
# LLM Client Tests
# ============================================================================

class TestLLMClient:
    """LLMClient 클래스 테스트"""

    def test_import_llm_client(self):
        """LLMClient import 테스트"""
        from services.chatbot.llm_client import LLMClient
        assert LLMClient is not None

    @patch('services.chatbot.llm_client.os.getenv')
    def test_init_without_api_key(self, mock_getenv):
        """API 키 없는 초기화 테스트"""
        mock_getenv.return_value = None

        from services.chatbot.llm_client import LLMClient

        client = LLMClient()
        assert client._use_mock is True

    @patch('services.chatbot.llm_client.os.getenv')
    def test_init_with_api_key_import_error(self, mock_getenv):
        """API 키 있지만 import 실패"""
        mock_getenv.return_value = "test-key"

        with patch.dict('sys.modules', {'google.generativeai': None}):
            from services.chatbot.llm_client import LLMClient

            client = LLMClient()
            assert client._use_mock is True

    def test_mock_generate_reply_recommendation(self):
        """Mock 답변 생성 테스트 (추천)"""
        from services.chatbot.llm_client import LLMClient

        # Mock 모드 강제
        client = LLMClient()
        client._use_mock = True

        prompt = "## 사용자 질문\n추천종목 알려줘"
        response = client.generate_reply(prompt)

        assert response.reply is not None
        assert len(response.reply) > 0
        assert len(response.suggestions) > 0

    def test_mock_generate_reply_market(self):
        """Mock 답변 생성 테스트 (시장)"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()
        client._use_mock = True

        prompt = "## 사용자 질문\n시장 상황 어때?"
        response = client.generate_reply(prompt)

        assert "Market Gate" in response.reply or "YELLOW" in response.reply

    def test_mock_generate_reply_stock(self):
        """Mock 답변 생성 테스트 (종목)"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()
        client._use_mock = True

        prompt = "## 사용자 질문\n삼성전자 추천해줘"
        response = client.generate_reply(prompt)

        assert "삼성전자" in response.reply or "005930" in response.reply

    def test_extract_question_from_prompt(self):
        """프롬프트에서 질문 추출 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()

        prompt = "System prompt... \n## 사용자 질문\n추천종목 알려줘"
        question = client._extract_question_from_prompt(prompt)

        assert "추천종목 알려줘" in question

    def test_extract_question_no_section(self):
        """섹션이 없는 경우 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()

        prompt = "추천종목 알려줘"
        question = client._extract_question_from_prompt(prompt)

        assert question == "추천종목 알려줘"

    def test_extract_suggestions_from_reply(self):
        """응답에서 추천 질문 추출 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()

        reply = "삼성전자는 VCP A등급입니다. Market Gate 상태도 확인하세요."
        suggestions = client._extract_suggestions(reply)

        assert len(suggestions) > 0
        assert len(suggestions) <= 3

    def test_extract_suggestions_empty(self):
        """빈 응답 추천 질문 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()

        reply = "안녕하세요"
        suggestions = client._extract_suggestions(reply)

        assert len(suggestions) == 3  # 기본 추천 질문

    def test_is_available_with_mock(self):
        """Mock 모드 사용 가능 여부 테스트"""
        from services.chatbot.llm_client import LLMClient

        client = LLMClient()
        client._use_mock = True

        assert client.is_available() is False

    def test_get_llm_client_singleton(self):
        """싱글톤 패턴 테스트"""
        from services.chatbot.llm_client import get_llm_client, LLMClient

        # 첫 호출은 인스턴스 생성
        client1 = get_llm_client()
        assert isinstance(client1, LLMClient)

        # 두 번째 호출도 같은 인스턴스
        client2 = get_llm_client()
        assert client2 is client1
