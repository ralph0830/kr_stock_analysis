"""
뉴스 감성 분석 파이프라인 통합 테스트

테스트 흐름:
1. NewsCollector로 뉴스 수집
2. SentimentAnalyzer로 감성 분석
3. NewsScorer로 점수화
4. 결과 검증
"""

import pytest
import os
from datetime import datetime, date
from unittest.mock import patch, Mock

from src.collectors.news_collector import NewsCollector, NewsArticle
from src.analysis.sentiment_analyzer import SentimentAnalyzer, Sentiment, SentimentResult
from src.analysis.news_scorer import NewsScorer, NewsScoreResult


class TestSentimentPipeline:
    """뉴스 감성 분석 파이프라인 통합 테스트"""

    @pytest.fixture
    def collector(self):
        """NewsCollector fixture"""
        return NewsCollector()

    @pytest.fixture
    def analyzer(self):
        """SentimentAnalyzer fixture (목업 모드)"""
        return SentimentAnalyzer(api_key=None)

    @pytest.fixture
    def scorer(self):
        """NewsScorer fixture"""
        return NewsScorer(api_key=None)

    @pytest.fixture
    def sample_articles(self):
        """샘플 뉴스 기사"""
        return [
            {
                "title": "삼성전자, 4분기 실적 시장 기대치 상회",
                "content": "삼성전자가 4분기 매출 80조원, 영업이익 10조원을 달성하며 시장 기대치를 상회했습니다.",
                "source": "테스트언론사",
            },
            {
                "title": "SK하이닉스, HBM 생산 확대 발표",
                "content": "SK하이닉스가 AI 수요 증가에 따라 HBM 생산을 2배로 확대한다고 발표했습니다.",
                "source": "테스트경제",
            },
            {
                "title": "LG에너지솔루션, 배터리 출하량 감소",
                "content": "LG에너지솔루션의 분기 배터리 출하량이 전분기 대비 10% 감소했습니다.",
                "source": "테스트뉴스",
            },
        ]

    def test_sentiment_analyzer_with_api_key(self):
        """API 키가 있을 때 SentimentAnalyzer 초기화 테스트"""
        # API 키가 설정된 경우 (테스트용 Mock)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            analyzer = SentimentAnalyzer()

            # 패키지가 설치되어 있고 API 키가 있으면 초기화 성공
            # 단위 테스트에서는 Mock을 사용하므로 _client 확인
            if analyzer._client is not None:
                assert analyzer.api_key == "test_key"
            else:
                # 패키지 미설치 시 목업 모드
                assert analyzer.api_key == "test_key"

    def test_sentiment_analyzer_mock_mode(self, analyzer):
        """목업 모드 감성 분석 테스트"""
        result = analyzer.analyze(
            title="삼성전자 실적 호조",
            content="삼성전자가 시장 기대치를 상회하는 실적을 발표했습니다."
        )

        # 결과 검증
        assert isinstance(result, SentimentResult)
        assert result.sentiment in [Sentiment.POSITIVE, Sentiment.NEGATIVE, Sentiment.NEUTRAL]
        assert 0 <= result.confidence <= 1
        assert -1 <= result.score <= 1
        assert isinstance(result.keywords, list)
        assert isinstance(result.summary, str)

    def test_sentiment_analyze_batch(self, analyzer, sample_articles):
        """배치 감성 분석 테스트"""
        results = analyzer.analyze_batch(sample_articles)

        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)

    def test_news_scorer_calculate_daily_score(self, scorer, sample_articles):
        """일일 뉴스 점수 계산 테스트"""
        target_date = date(2024, 1, 15)

        result = scorer.calculate_daily_score(
            ticker="005930",
            articles=sample_articles,
            target_date=target_date,
        )

        # 결과 검증
        assert isinstance(result, NewsScoreResult)
        assert result.date == target_date
        assert 0 <= result.total_score <= 3  # 종가베팅은 음수 제거
        assert result.positive_count >= 0
        assert result.negative_count >= 0
        assert result.neutral_count >= 0
        assert isinstance(result.details, list)

        # 통계 검증
        total_count = result.positive_count + result.negative_count + result.neutral_count
        assert total_count == len(sample_articles)

    def test_news_scorer_empty_articles(self, scorer):
        """빈 기사 리스트 처리 테스트"""
        result = scorer.calculate_daily_score(
            ticker="005930",
            articles=[],
            target_date=date(2024, 1, 15),
        )

        assert result.total_score == 0
        assert result.positive_count == 0
        assert result.negative_count == 0
        assert result.neutral_count == 0
        assert result.details == []

    def test_news_scorer_calculate_weekly_score(self, scorer):
        """주간 뉴스 점수 계산 테스트"""
        weekly_articles = {
            date(2024, 1, 15): [
                {
                    "title": "긍정 뉴스",
                    "content": "삼성전자 실적 호조 성장",
                    "source": "A",
                }
            ],
            date(2024, 1, 16): [
                {
                    "title": "중립 뉴스",
                    "content": "시장 상황 보고",
                    "source": "B",
                }
            ],
        }

        weekly_score = scorer.calculate_weekly_score(
            ticker="005930",
            weekly_articles=weekly_articles,
        )

        # 주간 평균 점수 검증
        assert 0 <= weekly_score <= 3

    def test_news_scorer_extract_keywords(self, scorer, sample_articles):
        """키워드 추출 테스트"""
        keywords = scorer.extract_keywords(sample_articles)

        assert isinstance(keywords, list)
        assert len(keywords) <= 10  # 최대 10개
        assert all(isinstance(k, str) for k in keywords)

    def test_full_pipeline_integration(self, collector, analyzer, scorer):
        """전체 파이프라인 통합 테스트 (Mock 사용)"""

        # 1. 뉴스 수집 (Mock)
        mock_articles = [
            NewsArticle(
                title="삼성전자 실적 호조",
                content="삼성전자가 시장 기대치를 상회하는 실적을 발표했습니다.",
                source="테스트언론사",
                url="https://example.com/1",
                published_at=datetime.now(),
                ticker="005930",
            ),
            NewsArticle(
                title="SK하이닉스 HBM 확대",
                content="SK하이닉스가 HBM 생산을 2배로 확대합니다.",
                source="테스트경제",
                url="https://example.com/2",
                published_at=datetime.now(),
                ticker="005930",
            ),
        ]

        # 2. 감성 분석
        sentiment_results = []
        for article in mock_articles:
            result = analyzer.analyze(article.title, article.content)
            sentiment_results.append(result)

        assert len(sentiment_results) == 2
        assert all(isinstance(r, SentimentResult) for r in sentiment_results)

        # 3. 뉴스 점수화
        articles_dict = [collector.to_dict(a) for a in mock_articles]
        score_result = scorer.calculate_daily_score(
            ticker="005930",
            articles=articles_dict,
            target_date=date.today(),
        )

        # 4. 결과 검증
        assert score_result.total_score >= 0
        assert score_result.total_score <= 3
        assert len(score_result.details) == 2

        # 세부 정보 검증
        for detail in score_result.details:
            assert "title" in detail
            assert "sentiment" in detail
            assert "score" in detail
