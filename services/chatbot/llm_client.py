"""
Chatbot LLM Client
Gemini API 기반 LLM 클라이언트
"""

import logging
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LLMInitializationError(Exception):
    """LLM 초기화 실패 예외"""
    pass


@dataclass
class LLMResponse:
    """LLM 응답 모델"""
    reply: str
    suggestions: List[str]
    usage: Optional[Dict] = None


class LLMClient:
    """
    LLM 클라이언트

    Gemini API를 사용하여 답변을 생성합니다.
    API 키가 없으면 Mock 모드로 동작합니다.
    """

    # Mock 응답 템플릿
    MOCK_RESPONSES = {
        "추천": "VCP A등급 종목을 추천드립니다. 현재 삼성전자(005930)가 VCP 패턴을 형성하고 있어 매수 기회로 보입니다. SmartMoney 흐름도 긍정적입니다.",
        "시장": "현재 Market Gate 상태는 YELLOW입니다. KOSPI는 횡보 중이며, KOSDAQ은 약세를 보이고 있습니다. 외국인과 기관의 수급 변화를 주의 깊게 살펴보세요.",
        "삼성전자": "삼성전자(005930)는 현재 VCP A등급입니다. 종가베팅 점수는 85점으로 매수 추천입니다. 외국인 순매수가 지속되고 있어 추가 상승 여력이 있습니다.",
        "default": "죄송합니다. 해당 종목에 대한 분석 정보를 준비 중입니다. VCP A등급 종목이나 Market Gate 상태를 확인해보세요.",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        LLM 클라이언트 초기화

        Args:
            api_key: Gemini API 키 (None이면 환경 변수 사용)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._use_mock = False
        self._client = None

        # API 키가 없거나 테스트용 키면 Mock 모드
        if not self.api_key or self.api_key == "test-key":
            self._use_mock = True
            self._client = None
            logger.info("🤖 LLM Mock mode enabled")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel("gemini-3-flash-preview")
            logger.info("✅ Gemini LLM initialized")
        except ImportError as e:
            logger.warning(f"google-generativeai not installed: {e}, falling back to mock mode")
            self._use_mock = True
        except Exception as e:
            logger.warning(f"Gemini API initialization failed: {e}, falling back to mock mode")
            self._use_mock = True

    def generate_reply(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        LLM 답변 생성

        Args:
            prompt: 프롬프트
            conversation_history: 대화 기록

        Returns:
            LLM 응답
        """
        # Mock 모드
        if self._use_mock:
            return self._generate_mock_reply(prompt)

        try:
            # Gemini API 호출
            response = self._client.generate_content(prompt)
            reply_text = response.text.strip()

            # 추천 질문 추출
            suggestions = self._extract_suggestions(reply_text)

            return LLMResponse(
                reply=reply_text,
                suggestions=suggestions,
                usage=None,
            )

        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}, falling back to mock")
            # API 호출 실패 시 Mock으로 fallback
            return self._generate_mock_reply(prompt)

    def _generate_mock_reply(self, prompt: str) -> LLMResponse:
        """
        Mock 응답 생성

        Args:
            prompt: 프롬프트

        Returns:
            Mock LLM 응답
        """
        # 질문에서 키워드 추출
        question = self._extract_question_from_prompt(prompt)

        # 적절한 Mock 응답 선택
        reply = self._get_mock_response(question)

        # 추천 질문 생성
        suggestions = self._extract_suggestions(reply)

        return LLMResponse(
            reply=reply,
            suggestions=suggestions,
            usage=None,
        )

    def _get_mock_response(self, question: str) -> str:
        """질문에 맞는 Mock 응답 반환"""
        if "추천" in question:
            return self.MOCK_RESPONSES["추천"]
        elif "시장" in question or "상황" in question or "상태" in question:
            return self.MOCK_RESPONSES["시장"]
        elif "삼성전자" in question or "005930" in question:
            return self.MOCK_RESPONSES["삼성전자"]
        else:
            return self.MOCK_RESPONSES["default"]

    def _extract_question_from_prompt(self, prompt: str) -> str:
        """
        프롬프트에서 사용자 질문 추출

        Args:
            prompt: 전체 프롬프트

        Returns:
            추출된 질문 텍스트
        """
        # "## 사용자 질문" 섹션 추출
        if "## 사용자 질문" in prompt:
            parts = prompt.split("## 사용자 질문")
            if len(parts) > 1:
                question = parts[1].strip()
                # 다른 섹션이 있으면 잘라내기
                for marker in ["## 시스템 프롬프트", "## 종목 데이터", "## 사용자 질문"]:
                    if marker in question and marker != "## 사용자 질문":
                        question = question.split(marker)[0].strip()
                return question

        # 섹션이 없으면 전체 반환
        return prompt.strip()

    def _extract_suggestions(self, reply_text: str) -> List[str]:
        """응답에서 추천 질문 추출"""
        suggestions = []

        if "VCP" in reply_text or "패턴" in reply_text:
            suggestions.append("VCP 시그널 확인")

        if "삼성전자" in reply_text or "005930" in reply_text:
            suggestions.append("삼성전자 수급")

        if "Market Gate" in reply_text or "시장" in reply_text:
            suggestions.append("KOSPI 현황")

        if "추천" in reply_text:
            suggestions.append("추천 종목 더보기")

        if not suggestions:
            suggestions = ["오늘의 추천종목", "Market Gate 상태", "VCP 시그널 확인"]

        return suggestions[:3]

    def is_available(self) -> bool:
        """LLM 사용 가능 여부"""
        # Mock 모드가 아니고 클라이언트가 초기화된 경우
        return not self._use_mock and self._client is not None


# 싱글톤 인스턴스
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> Optional[LLMClient]:
    """LLM 클라이언트 싱글톤 반환"""
    global _llm_client
    if _llm_client is None:
        try:
            _llm_client = LLMClient()
        except Exception:
            # 초기화 실패 시 Mock 모드로 생성
            _llm_client = LLMClient(api_key=None)
    return _llm_client
