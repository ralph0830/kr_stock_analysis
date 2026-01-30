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
    API 키가 없으면 즉시 에러를 발생시킵니다.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        LLM 클라이언트 초기화

        Args:
            api_key: Gemini API 키 (None이면 환경 변수 사용)

        Raises:
            LLMInitializationError: API 키가 없거나 초기화 실패 시
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise LLMInitializationError(
                "GEMINI_API_KEY가 설정되지 않았습니다. "
                "챗봇 서비스를 사용하려면 Gemini API 키가 필요합니다."
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel("gemini-3-flash-preview")
            logger.info("✅ Gemini LLM initialized")
        except ImportError as e:
            raise LLMInitializationError(
                f"google-generativeai 패키지가 설치되지 않았습니다: {e}"
            )
        except Exception as e:
            raise LLMInitializationError(
                f"Gemini API 초기화 실패: {e}"
            )

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

        Raises:
            LLMInitializationError: API 호출 실패 시
        """
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
            logger.error(f"❌ LLM generation failed: {e}")
            raise LLMInitializationError(
                f"LLM 답변 생성 실패: {e}"
            )

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
        return self._client is not None


# 싱글톤 인스턴스
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """LLM 클라이언트 싱글톤 반환"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
