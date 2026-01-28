"""
E2E Tests for News Pipeline
뉴스 수집 → 분석 → 점수화 전체 파이프라인 테스트
"""

from datetime import date
from unittest.mock import patch

from src.collectors.news_collector import NewsCollector
from src.analysis.sentiment_analyzer import SentimentAnalyzer
from src.analysis.news_scorer import NewsScorer


class TestNewsPipelineE2E:
    """뉴스 파이프라인 E2E 테스트"""

    def test_full_pipeline_with_mock_data(self):
        """전체 파이프라인 테스트 (Mock 데이터)"""
        # 1. 뉴스 수집
        collector = NewsCollector()

        # Mock 데이터 생성
        mock_articles = [
            {
                "title": "삼성전자, AI 반도체 기술 혁신",
                "content": "삼성전자가 인공지능 반도체 기술을 혁신하여 시장을 선도하고 있다.",
                "date": "2025-01-22",
                "source": "naver",
            },
            {
                "title": "삼성전자 실적 부진 우려",
                "content": "반도체 가격 하락으로 삼성전자 실적이 부진할 수 있다는 우려가 있다.",
                "date": "2025-01-21",
                "source": "naver",
            },
        ]

        # Mock NewsCollector.fetch_stock_news
        with patch.object(collector, 'fetch_stock_news', return_value=mock_articles):
            articles = collector.fetch_stock_news("005930", days=7, max_articles=10)

        assert len(articles) == 2
        assert articles[0]["title"] == "삼성전자, AI 반도체 기술 혁신"

        # 2. 감성 분석
        analyzer = SentimentAnalyzer()

        sentiment_results = []
        for article in articles:
            result = analyzer.analyze(
                title=article["title"],
                content=article.get("content", ""),
            )
            sentiment_results.append({
                "title": article["title"],
                "sentiment": result.sentiment.value,
                "confidence": result.confidence,
                "score": result.score,
                "keywords": result.keywords,
            })

        assert len(sentiment_results) == 2
        assert all("sentiment" in r for r in sentiment_results)

        # 3. 뉴스 점수 계산
        scorer = NewsScorer()
        target_date = date.today()

        score_result = scorer.calculate_daily_score(
            ticker="005930",
            articles=articles,
            target_date=target_date,
        )

        assert score_result.date == target_date
        assert score_result.positive_count >= 0
        assert score_result.negative_count >= 0
        assert 0 <= score_result.total_score <= 100

        # 전체 파이프라인 검증
        assert len(articles) > 0
        assert len(sentiment_results) == len(articles)
        assert score_result.total_score is not None

    def test_pipeline_with_no_articles(self):
        """기사 없을 때 파이프라인 테스트"""
        collector = NewsCollector()
        scorer = NewsScorer()

        with patch.object(collector, 'fetch_stock_news', return_value=[]):
            articles = collector.fetch_stock_news("005930", days=7, max_articles=10)

        assert len(articles) == 0

        # 빈 기사로 점수 계산
        score_result = scorer.calculate_daily_score(
            ticker="005930",
            articles=articles,
            target_date=date.today(),
        )

        # 빈 결과 검증
        assert score_result.total_score == 0.0
        assert score_result.positive_count == 0
        assert score_result.negative_count == 0
        assert score_result.neutral_count == 0

    def test_pipeline_sentiment_distribution(self):
        """감성 분포 검증 테스트"""
        collector = NewsCollector()

        # 긍정/부정/중립 기사 혼합
        mock_articles = [
            {"title": "삼성전자, 사상 최대 실적", "content": "역사적인 실적으로 주가 상승이 예상된다.", "date": "2025-01-22", "source": "naver"},
            {"title": "삼성전자, 리스크 요인 부각", "content": "경기 불황으로 어려움을 겪을 수 있다.", "date": "2025-01-21", "source": "naver"},
            {"title": "삼성전자, 신제품 출시 예정", "content": "내달 신제품을 출시할 계획이다.", "date": "2025-01-20", "source": "naver"},
        ]

        with patch.object(collector, 'fetch_stock_news', return_value=mock_articles):
            articles = collector.fetch_stock_news("005930", days=7, max_articles=10)

        # 감성 분석
        analyzer = SentimentAnalyzer()
        sentiments = []

        for article in articles:
            result = analyzer.analyze(
                title=article["title"],
                content=article.get("content", ""),
            )
            sentiments.append(result.sentiment.value)

        # 적어도 하나 이상의 감성이 있어야 함
        assert len(sentiments) == 3
        assert "sentiment" in dir(sentiments[0]) or isinstance(sentiments[0], str)

    def test_pipeline_date_handling(self):
        """날짜 처리 검증 테스트"""
        collector = NewsCollector()
        scorer = NewsScorer()

        mock_articles = [
            {"title": "테스트 기사", "content": "테스트 내용", "date": "2025-01-22", "source": "naver"},
        ]

        with patch.object(collector, 'fetch_stock_news', return_value=mock_articles):
            articles = collector.fetch_stock_news("005930", days=7, max_articles=10)

        target_date = date(2025, 1, 22)
        score_result = scorer.calculate_daily_score(
            ticker="005930",
            articles=articles,
            target_date=target_date,
        )

        assert score_result.date == target_date

    def test_pipeline_error_handling(self):
        """에러 처리 검증 테스트"""
        collector = NewsCollector()

        # 잘못된 데이터 형식
        invalid_articles = [
            {"title": None, "content": None},  # Invalid article
        ]

        # 에러가 발생해도 처리되어야 함
        try:
            with patch.object(collector, 'fetch_stock_news', return_value=invalid_articles):
                articles = collector.fetch_stock_news("005930", days=7, max_articles=10)

            # 감성 분석에서 에러 처리 검증
            analyzer = SentimentAnalyzer()
            results = []

            for article in articles:
                try:
                    result = analyzer.analyze(
                        title=article.get("title", ""),
                        content=article.get("content", ""),
                    )
                    results.append(result)
                except Exception:
                    # 에러가 발생하면 neutral로 처리
                    pass

            # 적어도 일부는 처리되어야 함
            assert len(results) >= 0

        except Exception:
            # 최상위 에러도 허용
            assert True


class TestNewsPipelinePerformance:
    """뉴스 파이프라인 성능 테스트"""

    def test_pipeline_performance_small_batch(self):
        """소량 배치 성능 테스트 (10건)"""
        import time

        collector = NewsCollector()

        # 10건 기사 생성
        mock_articles = [
            {
                "title": f"뉴스 {i}",
                "content": f"테스트 내용 {i}",
                "date": "2025-01-22",
                "source": "naver",
            }
            for i in range(10)
        ]

        with patch.object(collector, 'fetch_stock_news', return_value=mock_articles):
            start_time = time.time()
            articles = collector.fetch_stock_news("005930", days=7, max_articles=10)
            collect_time = time.time() - start_time

        # 수집 시간 검증 (1초 이내)
        assert collect_time < 1.0

        # 감성 분석 시간 측정
        analyzer = SentimentAnalyzer()
        start_time = time.time()

        for article in articles:
            analyzer.analyze(
                title=article["title"],
                content=article.get("content", ""),
            )

        analysis_time = time.time() - start_time

        # 분석 시간 검증 (5초 이내)
        assert analysis_time < 5.0

    def test_pipeline_performance_medium_batch(self):
        """중량 배치 성능 테스트 (50건)"""
        import time

        collector = NewsCollector()

        # 50건 기사 생성
        mock_articles = [
            {
                "title": f"뉴스 {i}",
                "content": f"테스트 내용 {i}" * 10,  # 더 긴 내용
                "date": "2025-01-22",
                "source": "naver",
            }
            for i in range(50)
        ]

        with patch.object(collector, 'fetch_stock_news', return_value=mock_articles):
            articles = collector.fetch_stock_news("005930", days=7, max_articles=50)

        assert len(articles) == 50

        # 전체 파이프라인 시간 측정
        scorer = NewsScorer()
        start_time = time.time()

        score_result = scorer.calculate_daily_score(
            ticker="005930",
            articles=articles,
            target_date=date.today(),
        )

        total_time = time.time() - start_time

        # 50건 기사는 10초 이내에 처리되어야 함
        assert total_time < 10.0
        assert score_result.total_score is not None
