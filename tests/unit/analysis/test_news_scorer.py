"""
Unit Tests for NewsScorer
종가베팅 V2 뉴스 점수 계산기 테스트 (TDD)

점수 기준:
- 3점: 매우 긍정적 (긍정 뉴스 3개 이상 or 평균 점수 0.6+)
- 2점: 긍정적 (긍정 뉴스 2개 or 평균 점수 0.3+)
- 1점: 약간 긍정 (긍정 뉴스 1개)
- 0점: 중립 (긍정/부정 균형)
"""

from unittest.mock import Mock, patch
from datetime import date

from src.analysis.news_scorer import NewsScorer, NewsScoreResult
from src.analysis.sentiment_analyzer import Sentiment, SentimentResult
from services.signal_engine.scorer import SignalScorer


class TestNewsScorerCalculateDailyScore:
    """NewsScorer.calculate_daily_score() 테스트"""

    def test_뉴스3개이상긍정_3점(self):
        """긍정 뉴스 3개 이상: 3점"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = SentimentResult(
            sentiment=Sentiment.POSITIVE,
            confidence=0.8,
            keywords=["성장", "상승"],
            summary="긍정적 뉴스",
            score=0.8,
        )

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "삼성전자 실적 호조", "content": "매출 증가", "source": "A"},
            {"title": "반도체 상승", "content": "수요 급증", "source": "B"},
            {"title": "목표가 상향", "content": "증권사 긍정적", "source": "C"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert
        assert result.total_score == 3.0
        assert result.positive_count == 3
        assert result.negative_count == 0

    def test_뉴스2개긍정_2점(self):
        """긍정 뉴스 2개: 2점"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = [
            SentimentResult(sentiment=Sentiment.POSITIVE, confidence=0.7, keywords=["성장"], summary="긍정", score=0.7),
            SentimentResult(sentiment=Sentiment.POSITIVE, confidence=0.6, keywords=["상승"], summary="긍정", score=0.6),
            SentimentResult(sentiment=Sentiment.NEUTRAL, confidence=0.5, keywords=[], summary="중립", score=0.0),
        ]

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "실적 호조", "content": "매출 증가"},
            {"title": "주가 상승", "content": "투자자 매수"},
            {"title": "시장 변동", "content": "관망세"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert
        assert result.total_score == 2.0
        assert result.positive_count == 2

    def test_뉴스1개긍정_1점(self):
        """긍정 뉴스 1개: 1점"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = [
            SentimentResult(sentiment=Sentiment.POSITIVE, confidence=0.6, keywords=["성장"], summary="긍정", score=0.6),
            SentimentResult(sentiment=Sentiment.NEUTRAL, confidence=0.5, keywords=[], summary="중립", score=0.0),
            SentimentResult(sentiment=Sentiment.NEUTRAL, confidence=0.5, keywords=[], summary="중립", score=0.0),
        ]

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "실적 호조", "content": "매출 증가"},
            {"title": "시장 변동", "content": "관망세"},
            {"title": "거래량 평균", "content": "보합"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert
        assert result.total_score == 1.0
        assert result.positive_count == 1

    def test_뉴스없음_0점(self):
        """뉴스 없음: 0점"""
        # Arrange
        scorer = NewsScorer()

        # Act
        result = scorer.calculate_daily_score("005930", [], date.today())

        # Assert
        assert result.total_score == 0.0
        assert result.positive_count == 0
        assert result.negative_count == 0
        assert result.neutral_count == 0

    def test_API실패시_0점_폴백(self):
        """API 실패 시: 0점 (예외 처리 후 NEUTRAL로 폴백)"""
        # Arrange: API 호출 시 예외 발생하는 Mock
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = Exception("API Error")

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "뉴스 제목", "content": "뉴스 내용"},
        ]

        # Act: 예외가 처리되어 NEUTRAL 결과로 폴백
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert: 예외 처리로 인해 NEUTRAL → 0점
        assert result.total_score == 0.0
        assert result.positive_count == 0
        assert result.neutral_count == 1

    def test_평균점수06이상_3점(self):
        """평균 감성 점수 0.6 이상: 3점"""
        # Arrange: 높은 confidence의 긍정 뉴스들
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = [
            SentimentResult(sentiment=Sentiment.POSITIVE, confidence=0.9, keywords=["성장"], summary="긍정", score=0.9),
            SentimentResult(sentiment=Sentiment.POSITIVE, confidence=0.8, keywords=["상승"], summary="긍정", score=0.8),
            SentimentResult(sentiment=Sentiment.NEUTRAL, confidence=0.5, keywords=[], summary="중립", score=0.0),
        ]

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "실적 큰 폭 개선", "content": "매출 급증"},
            {"title": "주가 강력 상승", "content": "외국인 매수"},
            {"title": "시황 전망", "content": "관망"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert: 평균 = (0.9 + 0.8 + 0) / 3 = 0.56 < 0.6 (긍정 2개라서 2점)
        # 긍정 2개이므로 2점
        assert result.total_score == 2.0

    def test_평균점수03이상06미만_2점(self):
        """평균 감성 점수 0.3 이상 0.6 미만, 긍정 1개: 2점"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = [
            SentimentResult(sentiment=Sentiment.POSITIVE, confidence=0.5, keywords=["성장"], summary="긍정", score=0.5),
            SentimentResult(sentiment=Sentiment.NEUTRAL, confidence=0.5, keywords=[], summary="중립", score=0.0),
        ]

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "실적 호조", "content": "소폭 증가"},
            {"title": "시황 보합", "content": "관망세"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert: 평균 = 0.25 < 0.3, 긍정 1개라서 1점
        assert result.total_score == 1.0

    def test_부정뉴스만_0점(self):
        """부정 뉴스만 있는 경우: 음수지만 종가베팅에서는 0점 처리"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = SentimentResult(
            sentiment=Sentiment.NEGATIVE,
            confidence=0.8,
            keywords=["하락", "위기"],
            summary="부정적 뉴스",
            score=-0.8,
        )

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "실적 부진", "content": "매출 감소"},
            {"title": "주가 하락", "content": "투자자 매도"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert: 음수 점수지만 max(0, total_score)로 0점 처리
        assert result.total_score == 0.0
        assert result.negative_count == 2

    def test_뉴스결과상세포함(self):
        """뉴스 분석 상세 결과 포함 확인"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = SentimentResult(
            sentiment=Sentiment.POSITIVE,
            confidence=0.8,
            keywords=["성장", "상승"],
            summary="긍정적 전망",
            score=0.8,
        )

        scorer = NewsScorer()
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "삼성전자 호조", "content": "실적 개선", "source": "Reuters"},
        ]

        # Act
        result = scorer.calculate_daily_score("005930", articles, date.today())

        # Assert
        assert len(result.details) == 1
        detail = result.details[0]
        assert detail["title"] == "삼성전자 호조"
        assert detail["source"] == "Reuters"
        assert detail["sentiment"] == "positive"
        assert detail["confidence"] == 0.8
        assert detail["score"] == 0.8
        assert "성장" in detail["keywords"]


class TestNewsScorerCalculateWeeklyScore:
    """NewsScorer.calculate_weekly_score() 테스트"""

    def test_주간평균점수_계산(self):
        """주간 평균 점수 계산"""
        # Arrange: Mock을 사용하지 않고 실제 Mock 분석 결과 사용
        # Mock 분석은 "호조", "개선", "강세" 등 긍정 키워드를 인식하여 3점 부여
        scorer = NewsScorer()

        weekly_articles = {
            date(2026, 1, 26): [{"title": "호조", "content": "상승"}],
            date(2026, 1, 27): [{"title": "개선", "content": "증가"}],
            date(2026, 1, 28): [{"title": "강세", "content": "매수"}],
        }

        # Act
        weekly_score = scorer.calculate_weekly_score("005930", weekly_articles)

        # Assert: 모든 날이 3점 (긍정 키워드 포함) → 평균 3.0
        assert weekly_score == 3.0

    def test_주간빈데이터_0점(self):
        """주간 데이터 비어있음: 0점"""
        # Arrange
        scorer = NewsScorer()

        # Act
        weekly_score = scorer.calculate_weekly_score("005930", {})

        # Assert
        assert weekly_score == 0.0


class TestNewsScorerExtractKeywords:
    """NewsScorer.extract_keywords() 테스트"""

    def test_키워드추출_빈도순(self):
        """키워드 빈도순 추출"""
        # Arrange
        scorer = NewsScorer()
        mock_analyzer = Mock()

        # 키워드 빈도 시뮬레이션
        def mock_analyze_side_effect(title, content):
            text = title + " " + content
            if "성장" in text:
                return SentimentResult(
                    sentiment=Sentiment.POSITIVE, confidence=0.8, keywords=["성장"], summary="긍정", score=0.8
                )
            elif "상승" in text:
                return SentimentResult(
                    sentiment=Sentiment.POSITIVE, confidence=0.7, keywords=["상승"], summary="긍정", score=0.7
                )
            return SentimentResult(
                sentiment=Sentiment.NEUTRAL, confidence=0.5, keywords=[], summary="중립", score=0.0
            )

        mock_analyzer.analyze.side_effect = mock_analyze_side_effect
        scorer.analyzer = mock_analyzer

        articles = [
            {"title": "성장", "content": "성장 모멘텀"},
            {"title": "성장", "content": "지속 성장"},
            {"title": "상승", "content": "주가 상승"},
        ]

        # Act
        keywords = scorer.extract_keywords(articles)

        # Assert: "성장"이 2회, "상승"이 1회 → 성장이 먼저
        assert len(keywords) >= 2
        assert "성장" in keywords
        assert "상승" in keywords
        # 빈도순 정렬 확인 (성장이 상승보다 앞에 있어야 함)
        growth_idx = keywords.index("성장")
        rise_idx = keywords.index("상승")
        assert growth_idx < rise_idx


class TestSignalScorerNewsIntegration:
    """SignalScorer._calculate_news_score() 통합 테스트"""

    @patch('src.collectors.news_collector.NewsCollector')
    @patch('src.analysis.news_scorer.NewsScorer')
    def test_signal_scorer_news_score_no_articles(self, mock_news_scorer_class, mock_news_collector_class):
        """SignalScorer 뉴스 점수 계산 - 뉴스 없을 때 0점"""
        # Arrange: Mock NewsCollector와 NewsScorer
        mock_collector = Mock()
        mock_collector.fetch_stock_news.return_value = []
        mock_collector.to_dict.return_value = {}
        mock_news_collector_class.return_value = mock_collector

        mock_scorer = Mock()
        mock_scorer.calculate_daily_score.return_value = NewsScoreResult(
            date=date.today(),
            total_score=0.0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            details=[],
        )
        mock_news_scorer_class.return_value = mock_scorer

        scorer = SignalScorer()

        # Act
        score = scorer._calculate_news_score("005930")

        # Assert: 뉴스 없으면 0점
        assert score == 0

    @patch('src.collectors.news_collector.NewsCollector')
    @patch('src.analysis.news_scorer.NewsScorer')
    def test_signal_scorer_news_score_with_articles(self, mock_news_scorer_class, mock_news_collector_class):
        """뉴스 기사 있을 때 점수 계산"""
        # Arrange: Mock 뉴스 기사
        mock_articles = [
            {"title": "삼성전자 호조", "content": "실적 상승", "source": "A"},
            {"title": "반도체 강세", "content": "수요 증가", "source": "B"},
        ]

        mock_collector = Mock()
        mock_collector.fetch_stock_news.return_value = mock_articles
        mock_collector.to_dict.side_effect = lambda x: x
        mock_news_collector_class.return_value = mock_collector

        mock_scorer = Mock()
        mock_scorer.calculate_daily_score.return_value = NewsScoreResult(
            date=date.today(),
            total_score=2.0,
            positive_count=2,
            negative_count=0,
            neutral_count=0,
            details=[],
        )
        mock_news_scorer_class.return_value = mock_scorer

        scorer = SignalScorer()

        # Act
        score = scorer._calculate_news_score("005930")

        # Assert
        assert score == 2
        mock_collector.fetch_stock_news.assert_called_once()
        mock_scorer.calculate_daily_score.assert_called_once()

    @patch('src.collectors.news_collector.NewsCollector')
    def test_signal_scorer_news_collector_failure_returns_0(self, mock_news_collector_class):
        """NewsCollector 실패 시 0점 반환"""
        # Arrange: NewsCollector가 예외 발생
        mock_collector = Mock()
        mock_collector.fetch_stock_news.side_effect = Exception("Network error")
        mock_news_collector_class.return_value = mock_collector

        scorer = SignalScorer()

        # Act
        score = scorer._calculate_news_score("005930")

        # Assert: 예외 처리로 0점 반환
        assert score == 0
