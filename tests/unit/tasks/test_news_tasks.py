"""
News Tasks Unit Tests (Phase 5: GREEN)
TDD - 뉴스 수집 태스크 단위 테스트
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock, call
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from tasks.news_tasks import (
    collect_news,
    analyze_sentiment,
    calculate_news_scores,
    collect_all_stocks_news,
    news_pipeline_task,
    collect_and_save_task,
    scheduled_daily_collection,
    _get_recommendation_from_sentiment,
)


@pytest.fixture
def mock_db_session():
    """Mock DB session fixture"""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def mock_session_generator(mock_db_session):
    """Mock get_db_session generator fixture"""
    def gen():
        yield mock_db_session
    return gen


class TestCollectNewsTask:
    """뉴스 수집 태스크 테스트 (기존 기능)"""
    # 기존 collect_news 태스크는 Phase 1에서 이미 검증됨
    # Phase 5 핵심인 collect_and_save_task 테스트로 대체


class TestCollectAndSaveTask:
    """뉴스 수집 및 저장 태스크 테스트 (Phase 5: GREEN)"""

    @patch("tasks.news_tasks.AIAnalysisRepository")
    @patch("tasks.news_tasks.get_db_session")
    @patch("tasks.news_tasks.SentimentAnalyzer")
    @patch("tasks.news_tasks.NewsCollector")
    def test_collect_and_save_saves_news_urls_to_db(
        self, mock_collector_class, mock_analyzer_class, mock_session_func, mock_repo_class
    ):
        """
        GREEN TEST 3: collect_and_save_task가 DB에 news_urls 저장

        수집된 뉴스 URL이 DB에 저장되어야 함
        """
        # Mock 데이터: NewsArticle 객체 형태로 모킹 (.title, .url, .content 속성)
        mock_article1 = Mock()
        mock_article1.title = "삼성전자 실적"
        mock_article1.url = "https://n.news.naver.com/article/123"
        mock_article1.content = "실적 호조"

        mock_article2 = Mock()
        mock_article2.title = "삼성전자 주가"
        mock_article2.url = "https://n.news.naver.com/article/456"
        mock_article2.content = "주가 상승"

        mock_articles = [mock_article1, mock_article2]

        # Mock collector
        mock_collector = Mock()
        mock_collector.fetch_stock_news.return_value = mock_articles
        mock_collector_class.return_value = mock_collector

        # Mock analyzer
        mock_sentiment = Mock()
        mock_sentiment.value = "positive"
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = Mock(
            sentiment=mock_sentiment,
            score=0.8,
            keywords=["삼성전자", "실적"],
            confidence=0.9,
        )
        mock_analyzer_class.return_value = mock_analyzer

        # Mock session (generator)
        mock_session = Mock(spec=Session)
        mock_session_gen = iter([mock_session])
        mock_session_func.return_value = mock_session_gen

        # Mock repository
        mock_analysis = Mock()
        mock_analysis.id = 123
        mock_repo = Mock()
        mock_repo.save_analysis.return_value = mock_analysis
        mock_repo_class.return_value = mock_repo

        # 태스크 실행 (bind=True이므로 self 인자로 None 전달)
        result = collect_and_save_task(None, "005930")

        # 검증
        assert result["success"] is True
        assert result["news_urls_count"] == 2
        assert result["analysis_id"] == 123

        # save_analysis가 news_urls와 함께 호출되었는지 확인
        mock_repo.save_analysis.assert_called_once()
        call_kwargs = mock_repo.save_analysis.call_args.kwargs
        assert "news_urls" in call_kwargs
        news_urls = call_kwargs["news_urls"]
        assert len(news_urls) == 2
        assert news_urls[0]["url"] == "https://n.news.naver.com/article/123"

    @patch("tasks.news_tasks.AIAnalysisRepository")
    @patch("tasks.news_tasks.get_db_session")
    @patch("tasks.news_tasks.SentimentAnalyzer")
    @patch("tasks.news_tasks.NewsCollector")
    def test_collect_and_save_handles_no_articles(
        self, mock_collector_class, mock_analyzer_class, mock_session_func, mock_repo_class
    ):
        """
        GREEN TEST 4: 뉴스가 없을 때 처리

        수집된 뉴스가 없을 때도 에러 없이 처리되어야 함
        """
        # Mock empty result
        mock_collector = Mock()
        mock_collector.fetch_stock_news.return_value = []
        mock_collector_class.return_value = mock_collector

        # 태스크 실행 (bind=True이므로 self 인자로 None 전달)
        result = collect_and_save_task(None, "000660")

        # 검증
        assert result["success"] is False
        assert result["reason"] == "no_articles"
        assert result["saved_count"] == 0


class TestScheduledCollection:
    """스케줄된 뉴스 수집 테스트"""

    def test_schedule_configuration_exists(self):
        """
        GREEN TEST 5: Celery Beat 스케줄 설정 확인

        celeryconfig.py에 뉴스 수집 스케줄이 정의되어야 함
        """
        from tasks.celery_app import celery_app

        # beat_schedule 확인
        beat_schedule = celery_app.conf.beat_schedule

        # 뉴스 관련 스케줄이 있는지 확인
        news_schedules = [
            key for key in beat_schedule.keys()
            if "news" in key.lower()
        ]

        assert len(news_schedules) > 0, "뉴스 수집 스케줄이 있어야 함"

    def test_schedule_timing_configuration(self):
        """
        GREEN TEST 6: 스케줄 타이밍 확인

        매일 오전 9시, 오후 3시로 설정되어야 함 (테스트용은 짧게)
        """
        from tasks.celery_app import celery_app

        beat_schedule = celery_app.conf.beat_schedule

        # 뉴스 수집 스케줄 확인 (실제 beat_schedule에 있는 키들)
        assert "news-collection-kospi" in beat_schedule
        assert "news-collection-kosdaq" in beat_schedule

        # 태스크 이름 확인
        assert beat_schedule["news-collection-kospi"]["task"] == "tasks.news_tasks.scheduled_daily_collection"
        assert beat_schedule["news-collection-kosdaq"]["task"] == "tasks.news_tasks.scheduled_daily_collection"

    @patch("tasks.news_tasks.collect_multiple_and_save")
    def test_scheduled_daily_collection_calls_multiple(
        self, mock_collect_multiple
    ):
        """
        GREEN TEST 7: scheduled_daily_collection이 여러 종목 처리

        스케줄된 태스크가 여러 종목을 순차적으로 처리해야 함
        """
        # Mock 반환값
        mock_collect_multiple.return_value = {
            "total_tickers": 8,
            "success_count": 8,
            "total_urls": 24,
            "results": [],
            "success": True,
        }

        # 태스크 실행 (bind=True이므로 self 인자로 None 전달)
        result = scheduled_daily_collection(None, "KOSPI")

        # 검증
        mock_collect_multiple.assert_called_once()
        call_args = mock_collect_multiple.call_args.args

        # KOSPI 종목 리스트가 전달되었는지 확인
        tickers_arg = call_args[1]  # self 다음 두 번째 인자
        assert len(tickers_arg) == 8
        assert "005930" in tickers_arg


class TestRecommendationHelper:
    """추천사항 헬퍼 함수 테스트"""

    def test_recommendation_from_positive_sentiment(self):
        """긍정 감성 → BUY 추천"""
        result = _get_recommendation_from_sentiment("positive")
        assert result == "BUY"

    def test_recommendation_from_negative_sentiment(self):
        """부정 감성 → SELL 추천"""
        result = _get_recommendation_from_sentiment("negative")
        assert result == "SELL"

    def test_recommendation_from_neutral_sentiment(self):
        """중립 감성 → HOLD 추천"""
        result = _get_recommendation_from_sentiment("neutral")
        assert result == "HOLD"
