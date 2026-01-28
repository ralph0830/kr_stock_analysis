"""
AI Routes Unit Tests
TDD GREEN Phase - Tests should pass with implementation
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
from fastapi import HTTPException

from src.analysis.sentiment_analyzer import SentimentResult, Sentiment


@pytest.fixture
def mock_ai_analysis():
    """Mock AI 분석 결과"""
    return {
        "ticker": "005930",
        "name": "삼성전자",
        "analysis_date": "2024-01-27",
        "sentiment": "positive",
        "score": 0.75,
        "summary": "반도체 수요 증가로 실적 호조 기대",
        "keywords": ["반도체", "수요", "실적"],
        "recommendation": "BUY",
    }


@pytest.fixture
def mock_ai_history():
    """Mock AI 분석 히스토리"""
    dates = ["2024-01-25", "2024-01-26", "2024-01-27"]
    return [
        date.fromisoformat(d)
        for d in dates
    ]


class TestAIRoutesUnit:
    """AI Routes 단위 테스트"""

    def test_get_ai_summary_found(self, mock_ai_history):
        """AI 종목 요약 조회 - 분석 존재"""
        from services.api_gateway.routes.ai import get_ai_summary
        from src.database.models import AIAnalysis

        mock_session = Mock()
        mock_stock = Mock()
        mock_stock.name = "삼성전자"

        mock_analysis = AIAnalysis(
            id=1,
            ticker="005930",
            analysis_date=date.today(),
            sentiment="positive",
            score=0.75,
            summary="테스트 요약",
            keywords=["키워드"],
            recommendation="BUY",
        )

        mock_stock_repo = Mock()
        mock_stock_repo.get_by_ticker.return_value = mock_stock

        mock_ai_repo = Mock()
        mock_ai_repo.get_latest_analysis.return_value = mock_analysis

        with patch(
            "services.api_gateway.routes.ai.StockRepository",
            return_value=mock_stock_repo,
        ):
            with patch(
                "services.api_gateway.routes.ai.AIAnalysisRepository",
                return_value=mock_ai_repo,
            ):
                result = get_ai_summary("005930", mock_session)
                assert result.ticker == "005930"
                assert result.sentiment == "positive"

    def test_get_ai_summary_not_found(self):
        """AI 종목 요약 조회 - 종목 없음"""
        from services.api_gateway.routes.ai import get_ai_summary

        mock_session = Mock()
        mock_stock_repo = Mock()
        mock_stock_repo.get_by_ticker.return_value = None

        with patch(
            "services.api_gateway.routes.ai.StockRepository",
            return_value=mock_stock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_ai_summary("999999", mock_session)
            assert exc_info.value.status_code == 404

    def test_get_ai_summary_no_analysis(self):
        """AI 종목 요약 조회 - 분석 없음"""
        from services.api_gateway.routes.ai import get_ai_summary
        from services.api_gateway.routes.ai import AIAnalysisResponse

        mock_session = Mock()
        mock_stock = Mock()
        mock_stock.name = "삼성전자"

        mock_stock_repo = Mock()
        mock_stock_repo.get_by_ticker.return_value = mock_stock

        mock_ai_repo = Mock()
        mock_ai_repo.get_latest_analysis.return_value = None

        with patch(
            "services.api_gateway.routes.ai.StockRepository",
            return_value=mock_stock_repo,
        ):
            with patch(
                "services.api_gateway.routes.ai.AIAnalysisRepository",
                return_value=mock_ai_repo,
            ):
                result = get_ai_summary("005930", mock_session)
                assert result.ticker == "005930"
                assert result.sentiment is None

    def test_get_ai_analysis_success(self):
        """전체 AI 분석 조회 - 성공"""
        from services.api_gateway.routes.ai import get_ai_analysis
        from src.database.models import AIAnalysis

        mock_session = Mock()
        mock_repo = Mock()

        mock_analysis = AIAnalysis(
            id=1,
            ticker="005930",
            analysis_date=date.today(),
            sentiment="positive",
            score=0.75,
            summary="요약",
            keywords=[],
            recommendation="BUY",
        )

        mock_repo.get_all_analyses.return_value = [mock_analysis]

        with patch(
            "services.api_gateway.routes.ai.AIAnalysisRepository",
            return_value=mock_repo,
        ):
            result = get_ai_analysis(None, 10, mock_session)
            assert result.total == 1
            assert len(result.analyses) == 1

    def test_get_ai_history_dates(self, mock_ai_history):
        """분석 가능 날짜 조회"""
        from services.api_gateway.routes.ai import get_ai_history_dates

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_available_dates.return_value = mock_ai_history

        with patch(
            "services.api_gateway.routes.ai.AIAnalysisRepository",
            return_value=mock_repo,
        ):
            result = get_ai_history_dates(30, mock_session)
            assert result.total == 3

    def test_get_ai_history_by_date(self):
        """특정 날짜 분석 조회"""
        from services.api_gateway.routes.ai import get_ai_history_by_date
        from src.database.models import AIAnalysis

        mock_session = Mock()

        mock_analysis = AIAnalysis(
            id=1,
            ticker="005930",
            analysis_date=date(2024, 1, 27),
            sentiment="positive",
            score=0.75,
            summary="요약",
            keywords=[],
            recommendation="BUY",
        )

        mock_repo = Mock()
        mock_repo.get_by_date.return_value = [mock_analysis]

        with patch(
            "services.api_gateway.routes.ai.AIAnalysisRepository",
            return_value=mock_repo,
        ):
            result = get_ai_history_by_date("2024-01-27", mock_session)
            assert result.total == 1

    def test_trigger_ai_analysis(self):
        """AI 분석 트리거"""
        from services.api_gateway.routes.ai import trigger_ai_analysis
        from services.api_gateway.routes.ai import get_recommendation

        mock_session = Mock()
        mock_stock = Mock()
        mock_stock.name = "삼성전자"

        mock_stock_repo = Mock()
        mock_stock_repo.get_by_ticker.return_value = mock_stock

        mock_ai_repo = Mock()
        mock_ai_repo.save_analysis.return_value = Mock()

        with patch(
            "services.api_gateway.routes.ai.StockRepository",
            return_value=mock_stock_repo,
        ):
            with patch(
                "services.api_gateway.routes.ai.AIAnalysisRepository",
                return_value=mock_ai_repo,
            ):
                with patch(
                    "services.api_gateway.routes.ai.SentimentAnalyzer"
                ) as mock_analyzer:
                    mock_result = SentimentResult(
                        sentiment=Sentiment.POSITIVE,
                        confidence=0.75,
                        keywords=["성장"],
                        summary="호조",
                        score=0.75
                    )
                    mock_analyzer.analyze.return_value = mock_result

                    result = trigger_ai_analysis("005930", mock_session)
                    assert result["status"] == "completed"
                    assert result["ticker"] == "005930"

    def test_get_recommendation_from_score(self):
        """감성 점수 → 매수 추천 변환"""
        from services.api_gateway.routes.ai import get_recommendation

        # 강력 긍정
        assert get_recommendation(0.75, "positive") == "BUY"
        # 긍정
        assert get_recommendation(0.3, "positive") == "OVERWEIGHT"
        # 중립
        assert get_recommendation(0.0, "neutral") == "HOLD"
        # 부정
        assert get_recommendation(-0.3, "negative") == "UNDERWEIGHT"
        # 강력 부정
        assert get_recommendation(-0.75, "negative") == "SELL"

    def test_ai_analysis_response_model(self, mock_ai_analysis):
        """AIAnalysisResponse 모델 검증"""
        from services.api_gateway.schemas import AIAnalysisResponse

        response = AIAnalysisResponse(**mock_ai_analysis)
        assert response.ticker == "005930"
        assert response.sentiment == "positive"

    def test_ai_summary_to_sentiment_result(self):
        """AI 분석 결과 → SentimentResult 변환"""
        result = SentimentResult(
            sentiment=Sentiment.POSITIVE,
            confidence=0.75,
            keywords=["반도체", "수요"],
            summary="실적 호조",
            score=0.75
        )

        assert result.sentiment == Sentiment.POSITIVE
        assert result.score > 0
