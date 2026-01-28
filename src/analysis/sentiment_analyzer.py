"""
Sentiment Analyzer
뉴스 감성 분석기 - Gemini API 기반
"""

import os
import logging
from typing import Dict, Any, List
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
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel("gemini-pro")
                logger.info("✅ Gemini API initialized")
            except ImportError:
                logger.warning("⚠️  google-generativeai not installed")
            except Exception as e:
                logger.error(f"❌ Gemini API init failed: {e}")
        else:
            logger.warning("⚠️  GEMINI_API_KEY not set, using mock analysis")

    def analyze(self, title: str, content: str) -> SentimentResult:
        """
        뉴스 감성 분석

        Args:
            title: 뉴스 제목
            content: 뉴스 내용

        Returns:
            감성 분석 결과
        """
        if self._client is None:
            return self._mock_analyze(title, content)

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
            return self._mock_analyze(title, content)

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

    def _mock_analyze(self, title: str, content: str) -> SentimentResult:
        """
        목업 감성 분석 (테스트용)

        간단한 키워드 기반 분석
        """
        # 긍정 키워드
        positive_words = [
            "상승",
            "성장",
            "호조",
            "개선",
            "증가",
            "최대",
            "기록",
            "강세",
            "폭등",
            "달성",
            "突破",
            "초격차",
            "혁신",
        ]

        # 부정 키워드
        negative_words = [
            "하락",
            "부진",
            "약세",
            "감소",
            "위기",
            "우려",
            "폭락",
            "부실",
            "적자",
            "감사",
            "리스크",
            "충격",
            "악화",
        ]

        text = (title + " " + content).lower()
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        # 감성 결정
        if positive_count > negative_count:
            sentiment = Sentiment.POSITIVE
            confidence = min(0.9, 0.5 + positive_count * 0.1)
            score = confidence
        elif negative_count > positive_count:
            sentiment = Sentiment.NEGATIVE
            confidence = min(0.9, 0.5 + negative_count * 0.1)
            score = -confidence
        else:
            sentiment = Sentiment.NEUTRAL
            confidence = 0.5
            score = 0.0

        # 키워드 추출
        keywords = []
        all_words = positive_words + negative_words
        for word in all_words:
            if word in text:
                keywords.append(word)
                if len(keywords) >= 5:
                    break

        return SentimentResult(
            sentiment=sentiment,
            confidence=confidence,
            keywords=keywords,
            summary=f"[목업] {title[:50]}...",
            score=score,
        )
