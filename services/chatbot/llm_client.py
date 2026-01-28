"""
Chatbot LLM Client
Gemini API 기반 LLM 클라이언트
"""

import logging
import os
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        LLM 클라이언트 초기화

        Args:
            api_key: Gemini API 키 (None이면 환경 변수 사용)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        self._use_mock = False

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel("gemini-pro")
                logger.info("✅ Gemini LLM initialized")
            except ImportError:
                logger.warning("⚠️ google-generativeai not installed")
                self._use_mock = True
            except Exception as e:
                logger.warning(f"⚠️ Gemini API init failed: {e}")
                self._use_mock = True
        else:
            logger.warning("⚠️ GEMINI_API_KEY not set, using mock LLM")
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
        if self._use_mock or not self._client:
            return self._mock_generate_reply(prompt, conversation_history)

        try:
            # Gemini API 호출
            response = self._client.generate_content(prompt)
            reply_text = response.text.strip()

            # 추천 질문 추출
            suggestions = self._extract_suggestions(reply_text)

            return LLMResponse(
                reply=reply_text,
                suggestions=suggestions,
                usage=None,  # TODO: 사용량 추적
            )

        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            # Fallback to mock
            return self._mock_generate_reply(prompt, conversation_history)

    def _mock_generate_reply(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        Mock LLM 답변 생성

        Args:
            prompt: 프롬프트
            conversation_history: 대화 기록

        Returns:
            Mock 응답
        """
        # 프롬프트에서 질문 추출
        question = self._extract_question_from_prompt(prompt)

        # 키워드 기반 응답 생성
        if "추천" in question:
            return LLMResponse(
                reply="현재 VCP 패턴이 감지된 종목을 추천합니다. "
                      "삼성전자(005930) A등급, SK하이닉스(000660) B등급 등이 있습니다. "
                      "각 종목의 리스크를 충분히 고려하시기 바랍니다.",
                suggestions=["VCP 시그널 종목", "종가베팅 S등급", "추천 종목 더보기"]
            )
        elif "시장" in question or "kospi" in question.lower():
            return LLMResponse(
                reply="현재 Market Gate 상태는 YELLOW (레벨 50)입니다. "
                      "KOSPI는 소폭 상승, KOSDAQ은 소폭 하락 추세입니다. "
                      "관망이 필요한 시기로 판단됩니다.",
                suggestions=["KOSPI 현황", "급등 종목", "외국인 수급"]
            )
        elif "삼성" in question or "005930" in question:
            return LLMResponse(
                reply="삼성전자(005930)은 현재 VCP A등급 시그널이 있습니다. "
                      "반도체 섹터에 속하며, 외국인 수급 흐름을 확인해보시기 바랍니다.",
                suggestions=["삼성전자 재무제표", "삼성전자 수급", "삼성전자 최신 뉴스"]
            )
        else:
            return LLMResponse(
                reply="질문해 드리겠습니다. 더 구체적인 정보가 필요하시면 말씀해주세요.",
                suggestions=["오늘의 추천종목", "Market Gate 상태", "VCP 시그널 확인"]
            )

    def _extract_question_from_prompt(self, prompt: str) -> str:
        """프롬프트에서 질문 추출"""
        # "## 사용자 질문" 섹션 찾기
        if "## 사용자 질문" in prompt:
            parts = prompt.split("## 사용자 질문")
            if len(parts) > 1:
                return parts[1].strip()
        return prompt

    def _extract_suggestions(self, reply_text: str) -> List[str]:
        """응답에서 추천 질문 추출"""
        # 간단한 키워드 기반 추천 질문
        suggestions = []

        if "VCP" in reply_text or "패턴" in reply_text:
            suggestions.append("VCP 시그널 확인")

        if "삼성전자" in reply_text or "005930" in reply_text:
            suggestions.append("삼성전자 수급")

        if "Market Gate" in reply_text or "시장" in reply_text:
            suggestions.append("KOSPI 현황")

        if "추천" in reply_text:
            suggestions.append("추천 종목 더보기")

        # 기본 추천 질문
        if not suggestions:
            suggestions = ["오늘의 추천종목", "Market Gate 상태", "VCP 시그널 확인"]

        return suggestions[:3]  # 최대 3개

    def is_available(self) -> bool:
        """LLM 사용 가능 여부"""
        return not self._use_mock and self._client is not None


# 싱글톤 인스턴스
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """LLM 클라이언트 싱글톤 반환"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
