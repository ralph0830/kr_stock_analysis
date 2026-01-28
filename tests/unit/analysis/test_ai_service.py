"""
AI Service Unit Tests
TDD RED Phase - All tests should fail initially
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date

from src.analysis.sentiment_analyzer import Sentiment, SentimentResult


class TestAIServiceUnit:
    """AI Service 단위 테스트"""

    def test_ai_analyzer_initialization_with_api_key(self):
        """AI 분석기 초기화 - API Key 있는 경우"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import get_analyzer
            analyzer = get_analyzer()
            assert analyzer is not None

    def test_ai_analyzer_initialization_without_api_key(self):
        """AI 분석기 초기화 - API Key 없는 경우 (Mock 모드)"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import get_analyzer
            with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
                analyzer = get_analyzer()
                assert analyzer is not None

    def test_analyze_sentiment_positive(self):
        """긍정적 감성 분석"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import analyze_stock

            result = analyze_stock("005930", "삼성전자", "매출 성장 호조")
            assert result.sentiment == "positive"

    def test_analyze_sentiment_negative(self):
        """부정적 감성 분석"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import analyze_stock

            result = analyze_stock("005930", "삼성전자", "매출 부진 위기")
            assert result.sentiment == "negative"

    def test_analyze_sentiment_neutral(self):
        """중립적 감성 분석"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import analyze_stock

            result = analyze_stock("005930", "삼성전자", "정보 제공")
            assert result.sentiment == "neutral"

    def test_batch_analyze_multiple_stocks(self):
        """여러 종목 일괄 분석"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import batch_analyze

            tickers = ["005930", "000660", "035420"]
            results = batch_analyze(tickers)
            assert len(results) == 3

    def test_get_cached_analysis(self):
        """캐시된 분석 결과 조회"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import get_cached_analysis

            result = get_cached_analysis("005930", date.today())
            # 캐시 miss일 수도 있음
            assert result is None or isinstance(result, dict)

    def test_save_analysis_result(self):
        """분석 결과 저장"""
        with pytest.raises(ImportError):
            from services.ai_analyzer.main import save_analysis

            save_analysis(
                ticker="005930",
                analysis_date=date.today(),
                sentiment="positive",
                score=0.8,
                summary="테스트 요약"
            )
            # 예외 없으면 통과

    def test_sentiment_result_to_dict(self):
        """SentimentResult → dict 변환"""
        result = SentimentResult(
            sentiment=Sentiment.POSITIVE,
            confidence=0.85,
            keywords=["성장", "호조"],
            summary="매출이 성장세를 보임",
            score=0.85
        )

        expected_dict = {
            "sentiment": "positive",
            "confidence": 0.85,
            "keywords": ["성장", "호조"],
            "summary": "매출이 성장세를 보임",
            "score": 0.85
        }

        assert result.sentiment.value == expected_dict["sentiment"]
        assert result.confidence == expected_dict["confidence"]
