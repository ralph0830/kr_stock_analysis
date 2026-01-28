"""
Performance Repository Unit Tests
누적 수익률 및 성과 분석 테스트
"""

from unittest.mock import Mock, patch
from datetime import date, datetime


# ============================================================================
# Test Data
# ============================================================================

# Mock CLOSED signals with returns
MOCK_CLOSED_SIGNALS = [
    # Win signals
    Mock(
        id=1,
        ticker="005930",
        signal_type="VCP",
        status="CLOSED",
        score=85.0,
        grade="A",
        entry_price=75000,
        signal_date=date(2024, 1, 15),
        exit_time=datetime(2024, 1, 25, 15, 30),
    ),
    Mock(
        id=2,
        ticker="000660",
        signal_type="VCP",
        status="CLOSED",
        score=75.0,
        grade="B",
        entry_price=120000,
        signal_date=date(2024, 1, 16),
        exit_time=datetime(2024, 1, 26, 15, 30),
    ),
    # Loss signal
    Mock(
        id=3,
        ticker="035420",
        signal_type="JONGGA_V2",
        status="CLOSED",
        score=65.0,
        grade="C",
        entry_price=150000,
        signal_date=date(2024, 1, 17),
        exit_time=datetime(2024, 1, 20, 15, 30),
    ),
]

# Mock DailyPrice data for exit prices
MOCK_DAILY_PRICES = {
    "005930": Mock(close_price=80000),  # +6.67% gain
    "000660": Mock(close_price=132000),  # +10% gain
    "035420": Mock(close_price=135000),  # -10% loss
}


# ============================================================================
# PerformanceRepository Tests
# ============================================================================

class TestPerformanceRepository:
    """PerformanceRepository 클래스 테스트"""

    def test_import_repository(self):
        """PerformanceRepository import 테스트"""
        from src.repositories.performance_repository import PerformanceRepository
        assert PerformanceRepository is not None

    @patch('src.repositories.performance_repository.DailyPrice')
    def test_init_repository(self, mock_daily_price):
        """PerformanceRepository 초기화 테스트"""
        from src.repositories.performance_repository import PerformanceRepository

        mock_session = Mock()
        repo = PerformanceRepository(mock_session)

        assert repo is not None
        assert repo.session == mock_session

    @patch('src.repositories.performance_repository.DailyPrice')
    def test_calculate_cumulative_return(self, mock_daily_price_class):
        """누적 수익률 계산 테스트"""
        from src.repositories.performance_repository import PerformanceRepository

        mock_session = Mock()

        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = PerformanceRepository(mock_session)

        # Calculate with no data
        result = repo.calculate_cumulative_return(signal_type="VCP")

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 0  # No signals = empty result

    @patch('src.repositories.performance_repository.DailyPrice')
    def test_calculate_signal_performance(self, mock_daily_price_class):
        """시그널 성과 계산 테스트"""
        from src.repositories.performance_repository import PerformanceRepository

        mock_session = Mock()

        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = PerformanceRepository(mock_session)

        # Calculate with no data
        result = repo.calculate_signal_performance(days=30)

        # Verify result
        assert "total_signals" in result
        assert "win_rate" in result
        assert "avg_return" in result

    @patch('src.repositories.performance_repository.DailyPrice')
    def test_get_performance_by_period(self, mock_daily_price_class):
        """기간별 성과 조회 테스트"""
        from src.repositories.performance_repository import PerformanceRepository

        mock_session = Mock()
        repo = PerformanceRepository(mock_session)

        # Mock empty result
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        # Get performance
        result = repo.get_performance_by_period(period="1mo")

        # Verify result structure
        assert "period" in result
        assert result["period"] == "1mo"
        assert "total_signals" in result
        assert "win_rate" in result
        assert "cumulative_return" in result
        assert "mdd" in result
        assert "sharpe_ratio" in result

    @patch('src.repositories.performance_repository.DailyPrice')
    def test_get_top_performers(self, mock_daily_price_class):
        """최고 성과 종목 조회 테스트"""
        from src.repositories.performance_repository import PerformanceRepository

        mock_session = Mock()

        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = PerformanceRepository(mock_session)

        # Get top performers with no data
        result = repo.get_top_performers(limit=10, days=30)

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 0  # No signals = empty result

    @patch('src.repositories.performance_repository.DailyPrice')
    def test_exception_handling(self, mock_daily_price_class):
        """예외 처리 테스트"""
        from src.repositories.performance_repository import PerformanceRepository

        mock_session = Mock()

        # Mock query to return empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = PerformanceRepository(mock_session)

        # Should handle empty result gracefully
        result = repo.calculate_signal_performance(days=30)

        # Verify default result on empty data
        assert "total_signals" in result
        assert result["total_signals"] == 0


# ============================================================================
# Performance Routes Tests
# ============================================================================

class TestPerformanceRoutes:
    """Performance API 라우트 테스트"""

    def test_import_routes(self):
        """Performance routes import 테스트"""
        from services.api_gateway.routes.performance import router
        assert router is not None
        assert router.prefix == "/api/kr/performance"

    def test_routes_registered(self):
        """라우트 등록 확인 테스트"""
        from services.api_gateway.routes.performance import router

        routes = [route.path for route in router.routes]
        expected_routes = [
            "/cumulative",
            "/by-signal",
            "/by-period",
            "/top-performers",
            "/sharpe-ratio",
        ]

        for expected in expected_routes:
            assert any(expected in route for route in routes), f"Route {expected} not found"

    def test_response_models(self):
        """응답 모델 테스트"""
        from services.api_gateway.routes.performance import (
            CumulativeReturnPoint,
            CumulativeReturnResponse,
            SignalPerformanceResponse,
            PeriodPerformanceResponse,
            TopPerformerItem,
            TopPerformersResponse,
        )

        # Create test instances
        point = CumulativeReturnPoint(
            date="2024-01-15",
            daily_return_pct=2.5,
            cumulative_return_pct=5.0
        )
        assert point.date == "2024-01-15"

        response = CumulativeReturnResponse(
            data=[point],
            total_points=1,
            final_return_pct=5.0
        )
        assert response.total_points == 1

        signal_perf = SignalPerformanceResponse(
            total_signals=10,
            closed_signals=8,
            win_rate=75.0,
            avg_return=5.2,
            best_return=20.0,
            worst_return=-5.0
        )
        assert signal_perf.win_rate == 75.0

        period_perf = PeriodPerformanceResponse(
            period="1mo",
            total_signals=10,
            win_rate=75.0,
            avg_return=5.2,
            cumulative_return=15.0,
            mdd=3.5,
            best_return=20.0,
            worst_return=-5.0,
            sharpe_ratio=1.5
        )
        assert period_perf.period == "1mo"

        top_item = TopPerformerItem(
            ticker="005930",
            signal_type="VCP",
            entry_price=75000,
            exit_price=80000,
            return_pct=6.67,
            signal_date="2024-01-15"
        )
        assert top_item.ticker == "005930"

        top_response = TopPerformersResponse(
            performers=[top_item],
            total_count=1
        )
        assert top_response.total_count == 1
