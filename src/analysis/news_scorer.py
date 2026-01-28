"""
News Scorer
뉴스 점수화 - 종가베팅 V2 뉴스 점수 계산
"""

import logging
from typing import List, Dict, Any
from datetime import date
from dataclasses import dataclass

from src.analysis.sentiment_analyzer import SentimentAnalyzer, SentimentResult, Sentiment

logger = logging.getLogger(__name__)


@dataclass
class NewsScoreResult:
    """일일 뉴스 점수 결과"""
    date: date
    total_score: float  # 총점 (0~3점)
    positive_count: int  # 긍정 뉴스 수
    negative_count: int  # 부정 뉴스 수
    neutral_count: int  # 중립 뉴스 수
    details: List[Dict[str, Any]]  # 개별 뉴스 분석 결과


class NewsScorer:
    """
    뉴스 점수화기

    종가베팅 V2 뉴스 점수 계산 (0~3점)
    """

    def __init__(self, api_key: str | None = None):
        """
        뉴스 점수화기 초기화

        Args:
            api_key: Gemini API 키 (None이면 환경 변수 사용)
        """
        self.analyzer = SentimentAnalyzer(api_key)

    def calculate_daily_score(
        self,
        ticker: str,
        articles: List[Dict[str, str]],
        target_date: date,
    ) -> NewsScoreResult:
        """
        일일 뉴스 점수 계산

        **점수 산정 기준:**
        - 3점: 매우 긍정적 (긍정 뉴스 3개 이상 or 평균 점수 0.6+)
        - 2점: 긍정적 (긍정 뉴스 2개 or 평균 점수 0.3+)
        - 1점: 약간 긍정 (긍정 뉴스 1개)
        - 0점: 중립 (긍정/부정 균형)
        - 음수: 부정적 (종가베팅에서는 제외)

        Args:
            ticker: 종목코드
            articles: 뉴스 리스트 [{title, content, source}, ...]
            target_date: 대상 날짜

        Returns:
            일일 뉴스 점수 결과
        """
        if not articles:
            return NewsScoreResult(
                date=target_date,
                total_score=0.0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                details=[],
            )

        # 감성 분석
        results = []
        for article in articles:
            try:
                result = self.analyzer.analyze(
                    title=article["title"],
                    content=article.get("content", ""),
                )
                results.append(result)
            except Exception as e:
                logger.error(f"❌ 뉴스 감성 분석 실패: {e}, title={article['title']}")
                # 실패 시 중립 결과로 처리 (폴백)
                from src.analysis.sentiment_analyzer import SentimentResult
                results.append(SentimentResult(
                    sentiment=Sentiment.NEUTRAL,
                    confidence=0.0,
                    keywords=[],
                    summary=f"[분석 실패] {article['title'][:30]}...",
                    score=0.0,
                ))

        # 통계 집계
        positive_count = sum(1 for r in results if r.sentiment == Sentiment.POSITIVE)
        negative_count = sum(1 for r in results if r.sentiment == Sentiment.NEGATIVE)
        neutral_count = sum(1 for r in results if r.sentiment == Sentiment.NEUTRAL)

        # 평균 감성 점수 계산
        avg_score = sum(r.score for r in results) / len(results)

        # 뉴스 점수 계산 (0~3점)
        if positive_count >= 3 or avg_score >= 0.6:
            total_score = 3.0
        elif positive_count == 2 or avg_score >= 0.3:
            total_score = 2.0
        elif positive_count == 1:
            total_score = 1.0
        elif negative_count > positive_count:
            # 부정적일 경우 음수 점수
            total_score = max(-3.0, -float(negative_count))
        else:
            total_score = 0.0

        # 상세 결과 생성
        details = []
        for i, (article, result) in enumerate(zip(articles, results)):
            details.append(
                {
                    "title": article["title"],
                    "source": article.get("source", "Unknown"),
                    "sentiment": result.sentiment.value,
                    "confidence": result.confidence,
                    "score": result.score,
                    "keywords": result.keywords,
                }
            )

        logger.info(
            f"📊 {ticker} {target_date} 뉴스 점수: {total_score:.1f} "
            f"(긍정: {positive_count}, 부정: {negative_count}, 중립: {neutral_count})"
        )

        return NewsScoreResult(
            date=target_date,
            total_score=max(0.0, total_score),  # 종가베팅에서는 음수 제거
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            details=details,
        )

    def calculate_weekly_score(
        self,
        ticker: str,
        weekly_articles: Dict[date, List[Dict[str, str]]],
    ) -> float:
        """
        주간 뉴스 점수 집계

        Args:
            ticker: 종목코드
            weekly_articles: 일자별 뉴스 딕셔너리 {date: [articles]}

        Returns:
            주간 평균 뉴스 점수 (0~3점)
        """
        if not weekly_articles:
            return 0.0

        daily_scores = []
        for target_date, articles in weekly_articles.items():
            result = self.calculate_daily_score(ticker, articles, target_date)
            daily_scores.append(result.total_score)

        weekly_avg = sum(daily_scores) / len(daily_scores) if daily_scores else 0.0

        logger.info(
            f"📊 {ticker} 주간 뉴스 점수: {weekly_avg:.1f} "
            f"(일수: {len(weekly_articles)}, 일일 점수: {[f'{s:.1f}' for s in daily_scores]})"
        )

        return weekly_avg

    def extract_keywords(self, articles: List[Dict[str, str]]) -> List[str]:
        """
        뉴스 키워드 추출

        Args:
            articles: 뉴스 리스트

        Returns:
            상위 키워드 리스트 (빈도순)
        """
        keyword_freq = {}

        for article in articles:
            result = self.analyzer.analyze(
                title=article["title"],
                content=article.get("content", ""),
            )

            for keyword in result.keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1

        # 빈도순 정렬
        sorted_keywords = sorted(
            keyword_freq.items(), key=lambda x: x[1], reverse=True
        )

        return [keyword for keyword, _ in sorted_keywords[:10]]
