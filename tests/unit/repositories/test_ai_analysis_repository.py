"""
AI Analysis Repository Unit Tests
AI 분석 데이터 접근 계층 테스트
"""

from unittest.mock import Mock
from datetime import date


# ============================================================================
# Test Data
# ============================================================================

MOCK_AI_ANALYSIS = Mock(
    id=1,
    ticker="005930",
    name="삼성전자",
    analysis_date=date(2024, 1, 15),
    sentiment="positive",
    score=0.8,
    summary="긍정적인 뉴스 흐름",
    keywords=["반도체", "호재", "수요"],
    recommendation="BUY",
)


# ============================================================================
# AIAnalysisRepository Tests
# ============================================================================

class TestAIAnalysisRepository:
    """AIAnalysisRepository 클래스 테스트"""

    def test_import_repository(self):
        """AIAnalysisRepository import 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository
        assert AIAnalysisRepository is not None

    def test_init_repository(self):
        """AIAnalysisRepository 초기화 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository
        from src.database.models import AIAnalysis

        mock_session = Mock()
        repo = AIAnalysisRepository(mock_session)

        assert repo is not None
        assert repo.model == AIAnalysis
        assert repo.session == mock_session

    def test_get_latest_analysis(self):
        """최신 AI 분석 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = MOCK_AI_ANALYSIS
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get latest analysis
        result = repo.get_latest_analysis("005930")

        # Verify
        mock_session.execute.assert_called_once()
        assert result == MOCK_AI_ANALYSIS

    def test_get_all_analyses(self):
        """전체 AI 분석 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [MOCK_AI_ANALYSIS]
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get all analyses
        result = repo.get_all_analyses(limit=10)

        # Verify
        mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    def test_get_by_ticker(self):
        """종목별 분석 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [MOCK_AI_ANALYSIS]
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get by ticker
        result = repo.get_by_ticker("005930", limit=10)

        # Verify query was called
        mock_session.execute.assert_called_once()

    def test_get_by_date(self):
        """날짜별 분석 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get by date
        result = repo.get_by_date(date(2024, 1, 15))

        # Verify
        assert result == []

    def test_get_available_dates(self):
        """분석 가능 날짜 목록 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.all.return_value = [
            (date(2024, 1, 16),),
            (date(2024, 1, 15),),
        ]
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get available dates
        result = repo.get_available_dates(limit=30)

        # Verify
        assert isinstance(result, list)
        assert len(result) == 2

    def test_save_analysis(self):
        """AI 분석 결과 저장 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        repo = AIAnalysisRepository(mock_session)

        # Mock commit and refresh
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # Save analysis
        result = repo.save_analysis(
            ticker="005930",
            analysis_date=date(2024, 1, 15),
            sentiment="positive",
            score=0.8,
            summary="테스트 분석",
            keywords=["테스트"],
            recommendation="BUY",
        )

        # Verify
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_get_top_positive(self):
        """상위 긍정 종목 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [MOCK_AI_ANALYSIS]
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get top positive
        result = repo.get_top_positive(date(2024, 1, 15), limit=10)

        # Verify
        mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    def test_get_top_negative(self):
        """상위 부정 종목 조회 테스트"""
        from src.repositories.ai_analysis_repository import AIAnalysisRepository

        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AIAnalysisRepository(mock_session)

        # Get top negative
        result = repo.get_top_negative(date(2024, 1, 15), limit=10)

        # Verify
        assert isinstance(result, list)
