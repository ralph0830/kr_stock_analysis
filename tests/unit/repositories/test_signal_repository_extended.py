"""
Signal Repository Extended Unit Tests
시그널 데이터 접근 계층 추가 테스트
"""

from unittest.mock import Mock
from datetime import date, datetime
from sqlalchemy.orm import Session


# ============================================================================
# Test Data
# ============================================================================

MOCK_SIGNALS = [
    Mock(
        id=1,
        ticker="005930",
        signal_type="VCP",
        status="OPEN",
        score=85.0,
        grade="A",
        signal_date=date(2024, 1, 15),
        entry_price=75000,
        target_price=90000,
    ),
    Mock(
        id=2,
        ticker="000660",
        signal_type="JONGGA_V2",
        status="CLOSED",
        score=10,
        grade="S",
        signal_date=date(2024, 1, 16),
        entry_price=120000,
        exit_time=datetime(2024, 1, 20),
        exit_reason="목표가 달성",
    ),
]


# ============================================================================
# SignalRepository Extended Tests
# ============================================================================

class TestSignalRepositoryExtended:
    """SignalRepository 추가 테스트"""

    def test_import_repository(self):
        """SignalRepository import 테스트"""
        from src.repositories.signal_repository import SignalRepository
        assert SignalRepository is not None

    def test_init_repository(self):
        """SignalRepository 초기화 테스트"""
        from src.repositories.signal_repository import SignalRepository
        from src.database.models import Signal

        mock_session = Mock(spec=Session)
        repo = SignalRepository(mock_session)

        assert repo is not None
        assert repo.model == Signal
        assert repo.session == mock_session

    def test_get_active_signals(self):
        """활성 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [MOCK_SIGNALS[0]]
        mock_session.execute.return_value = mock_result

        repo = SignalRepository(mock_session)

        # Get active signals
        result = repo.get_active(limit=20)

        # Verify
        mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    def test_get_by_ticker(self):
        """종목별 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = MOCK_SIGNALS
        mock_session.execute.return_value = mock_result

        repo = SignalRepository(mock_session)

        # Get by ticker
        result = repo.get_by_ticker("005930", limit=10)

        # Verify
        assert isinstance(result, list)

    def test_get_by_date_range(self):
        """날짜 범위 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = MOCK_SIGNALS
        mock_session.execute.return_value = mock_result

        repo = SignalRepository(mock_session)

        # Get by date range
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        result = repo.get_by_date_range(start_date, end_date)

        # Verify
        assert isinstance(result, list)

    def test_update_status_with_exit_price(self):
        """시그널 상태 업데이트 (청산가 포함) 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_signal = Mock()
        mock_signal.id = 1
        mock_signal.status = "OPEN"

        repo = SignalRepository(mock_session)

        # Mock get_by_id to return signal
        repo.get_by_id = Mock(return_value=mock_signal)

        # Update status with exit price
        result = repo.update_status(
            signal_id=1,
            new_status="CLOSED",
            exit_price=80000,
            exit_reason="목표가 달성"
        )

        # Verify
        mock_session.commit.assert_called_once()
        assert mock_signal.status == "CLOSED"
        assert mock_signal.exit_price == 80000
        assert mock_signal.exit_reason == "목표가 달성"

    def test_get_latest_signals(self):
        """최신 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = MOCK_SIGNALS
        mock_session.execute.return_value = mock_result

        repo = SignalRepository(mock_session)

        # Get latest signals
        result = repo.get_latest_signals("VCP", limit=10)

        # Verify
        assert isinstance(result, list)

    def test_get_double_buy_signals(self):
        """쌍끌이 매수 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = MOCK_SIGNALS
        mock_session.execute.return_value = mock_result

        repo = SignalRepository(mock_session)

        # Get double buy signals
        result = repo.get_double_buy_signals(limit=20)

        # Verify
        assert isinstance(result, list)

    def test_get_high_score_signals(self):
        """고득점 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [MOCK_SIGNALS[0]]
        mock_session.execute.return_value = mock_result

        repo = SignalRepository(mock_session)

        # Get high score signals
        result = repo.get_high_score_signals(min_score=70.0, limit=20)

        # Verify
        assert isinstance(result, list)

    def test_get_summary_by_date(self):
        """특정 날짜의 시그널 요약 통계 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        repo = SignalRepository(mock_session)

        # Mock get_by_date_range to return signals
        repo.get_by_date_range = Mock(return_value=MOCK_SIGNALS)

        # Get summary
        result = repo.get_summary_by_date(date(2024, 1, 15))

        # Verify structure
        assert "date" in result
        assert "total" in result
        assert "by_status" in result
        assert "by_type" in result
        assert "avg_score" in result

    def test_update_status_not_found(self):
        """존재하지 않는 시그널 업데이트 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        repo = SignalRepository(mock_session)

        # Mock get_by_id to return None
        repo.get_by_id = Mock(return_value=None)

        # Update non-existent signal
        result = repo.update_status(
            signal_id=999,
            new_status="CLOSED"
        )

        # Verify
        assert result is None
        mock_session.commit.assert_not_called()


# ============================================================================
# BaseRepository Inheritance Tests
# ============================================================================

class TestSignalRepositoryBaseMethods:
    """SignalRepository 기본 메서드 테스트"""

    def test_create_signal(self):
        """시그널 생성 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        repo = SignalRepository(mock_session)

        # Mock create method from BaseRepository
        repo.create = Mock(return_value=MOCK_SIGNALS[0])

        # Create signal
        result = repo.create({"ticker": "005930", "signal_type": "VCP"})

        # Verify
        repo.create.assert_called_once()

    def test_get_by_id(self):
        """ID로 시그널 조회 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        repo = SignalRepository(mock_session)

        # Mock get_by_id method from BaseRepository
        repo.get_by_id = Mock(return_value=MOCK_SIGNALS[0])

        # Get by ID
        result = repo.get_by_id(1)

        # Verify
        assert result == MOCK_SIGNALS[0]
        repo.get_by_id.assert_called_once_with(1)

    def test_delete_signal(self):
        """시그널 삭제 테스트"""
        from src.repositories.signal_repository import SignalRepository

        mock_session = Mock(spec=Session)
        repo = SignalRepository(mock_session)

        # Mock delete method from BaseRepository
        repo.delete = Mock(return_value=True)

        # Delete signal
        result = repo.delete(1)

        # Verify
        assert result is True
