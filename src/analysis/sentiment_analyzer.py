"""
Sentiment Analyzer
뉴스 감성 분석기 - Gemini API 기반
"""

import os
import logging
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Sentiment(Enum):
    """감성 라벨"""
    POSITIVE = "positive"  # 긍정
    NEGATIVE = "negative"  # 부정
    NEUTRAL = "neutral"    # 중립


@dataclass
class SentimentResult:
    """감성 분석 결과"""
    sentiment: Sentiment
    confidence: float  # 0~1 사이 신뢰도
    keywords: List[str]  # 핵심 키워드
    summary: str  # 뉴스 요약
    score: float  # 감성 점수 (-1.0 ~ 1.0)


class SentimentAnalyzer:
    """
    뉴스 감성 분석기

    Gemini API를 사용하여 뉴스 감성 분석
    """

    # 감성 분석 프롬프트 템플릿
    SENTIMENT_PROMPT = """
다음 뉴스 기사를 분석하여 주식 시장 관점에서 감성을 분석해주세요.

**뉴스 제목:** {title}
**뉴스 내용:** {content}

**분석 요청:**
1. 감성 분류 (긍정/부정/중립)
2. 신뢰도 (0~1 사이 값)
3. 핵심 키워드 (3~5개)
4. 1문장 요약

**출력 형식 (JSON):**
{{
    "sentiment": "positive|negative|neutral",
    "confidence": 0.8,
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "summary": "뉴스 요약 1문장"
}}
"""

    def __init__(self, api_key: str | None = None):
        """
        감성 분석기 초기화

        Args:
            api_key: Gemini API 키 (None이면 환경 변수 사용)

        Raises:
            RuntimeError: Gemini API 키가 없는 경우
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다. 감성 분석을 사용하려면 API 키가 필요합니다.")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel("gemini-pro")
            logger.info("✅ Gemini API initialized")
        except ImportError:
            raise RuntimeError("google-generativeai 라이브러리가 설치되지 않았습니다. pip install google-generativeai로 설치하세요.")
        except Exception as e:
            raise RuntimeError(f"Gemini API 초기화 실패: {e}")

    def analyze(self, title: str, content: str) -> SentimentResult:
        """
        뉴스 감성 분석

        Args:
            title: 뉴스 제목
            content: 뉴스 내용

        Returns:
            감성 분석 결과

        Raises:
            RuntimeError: 분석 실패 시
        """
        try:
            prompt = self.SENTIMENT_PROMPT.format(title=title, content=content)

            response = self._client.generate_content(prompt)
            result_text = response.text

            # JSON 파싱
            import json

            # 마크다운 코드 블록 제거
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            # 감성 라벨 변환
            sentiment_map = {
                "positive": Sentiment.POSITIVE,
                "negative": Sentiment.NEGATIVE,
                "neutral": Sentiment.NEUTRAL,
            }
            sentiment = sentiment_map.get(result["sentiment"], Sentiment.NEUTRAL)

            # 감성 점수 계산 (-1.0 ~ 1.0)
            if sentiment == Sentiment.POSITIVE:
                score = result["confidence"]
            elif sentiment == Sentiment.NEGATIVE:
                score = -result["confidence"]
            else:
                score = 0.0

            return SentimentResult(
                sentiment=sentiment,
                confidence=result.get("confidence", 0.5),
                keywords=result.get("keywords", []),
                summary=result.get("summary", ""),
                score=score,
            )

        except Exception as e:
            logger.error(f"❌ 감성 분석 실패: {e}")
            raise RuntimeError(f"감성 분석 실패: {e}")

    def analyze_batch(self, articles: List[Dict[str, str]]) -> List[SentimentResult]:
        """
        여러 뉴스 일괄 분석

        Args:
            articles: 뉴스 리스트 [{title, content}, ...]

        Returns:
            감성 분석 결과 리스트
        """
        results = []
        for article in articles:
            result = self.analyze(article["title"], article.get("content", ""))
            results.append(result)
        return results
