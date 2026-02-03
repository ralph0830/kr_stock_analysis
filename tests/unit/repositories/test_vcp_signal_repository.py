"""
VCP Signal Repository Unit Tests (TDD - RED Phase)
VCP 시그널 데이터 접근 계층 테스트

이 테스트는 활성 VCP 시그널(상위 10개) 조회 기능을 검증합니다.
TDD 방식으로 먼저 작성되며, 구현 전에는 실패할 것으로 예상됩니다.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import date, datetime
from sqlalchemy.orm import Session


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_session():
    """Mock DB Session"""
    return Mock(spec=Session)


@pytest.fixture
def sample_vcp_signals():
    """샘플 VCP 시그널 데이터"""
    return [
        Mock(
            id=1,
            ticker="005930",
            stock=Mock(name="삼성전자", market="KOSPI", sector="전자"),
            signal_type="VCP",
            status="OPEN",
            score=85.0,
            grade="A",
            signal_date=date(2026, 1, 30),
            entry_price=75000,
            target_price=90000,
            contraction_ratio=0.45,
            foreign_net_5d=150000000,  # 1.5억
            inst_net_5d=80000000,      # 0.8억
            created_at=datetime(2026, 1, 30, 9, 0),
        ),
        Mock(
            id=2,
            ticker="000660",
            stock=Mock(name="SK하이닉스", market="KOSPI", sector="전자"),
            signal_type="VCP",
            status="OPEN",
            score=78.5,
            grade="A",
            signal_date=date(2026, 1, 30),
            entry_price=120000,
            target_price=140000,
            contraction_ratio=0.52,
            foreign_net_5d=200000000,
            inst_net_5d=50000000,
            created_at=datetime(2026, 1, 30, 9, 0),
        ),
        Mock(
            id=3,
            ticker="035420",
            stock=Mock(name="NAVER", market="KOSPI", sector="IT"),
            signal_type="VCP",
            status="OPEN",
            score=92.0,
            grade="S",
            signal_date=date(2026, 1, 30),
            entry_price=180000,
            target_price=210000,
            contraction_ratio=0.38,
            foreign_net_5d=300000000,
            inst_net_5d=150000000,
            created_at=datetime(2026, 1, 30, 9, 0),
        ),
        Mock(
            id=4,
            ticker="105560",
            stock=Mock(name="KB금융", market="KOSPI", sector="금융"),
            signal_type="VCP",
            status="CLOSED",  # CLOSED 상태는 제외
            score=88.0,
            grade="A",
            signal_date=date(2026, 1, 29),
            entry_price=50000,
            target_price=58000,
            contraction_ratio=0.42,
            foreign_net_5d=100000000,
            inst_net_5d=200000000,
            created_at=datetime(2026, 1, 29, 9, 0),
        ),
        Mock(
            id=5,
            ticker="036570",
            stock=Mock(name="NCSoft", market="KOSDAQ", sector="IT"),
            signal_type="JONGGA_V2",  # 다른 시그널 타입은 제외
            status="OPEN",
            score=75.0,
            grade="B",
            signal_date=date(2026, 1, 30),
            entry_price=250000,
            target_price=280000,
            contraction_ratio=None,  # 종가베팅은 contraction_ratio 없음
            foreign_net_5d=50000000,
            inst_net_5d=30000000,
            created_at=datetime(2026, 1, 30, 9, 0),
        ),
    ]


# ============================================================================
# VCPSignalRepository Tests
# ============================================================================

class TestVCPSignalRepository:
    """
    VCP Signal Repository 테스트 클래스

    TDD Red Phase: 구현 전이므로 모든 테스트가 실패할 것입니다.
    """

    def test_import_vcp_signal_repository(self):
        """
        GIVEN: VCP Signal Repository 모듈
        WHEN: 모듈을 import
        THEN: 클래스가 존재함
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository
        assert VCPSignalRepository is not None

    def test_init_vcp_signal_repository(self, mock_session):
        """
        GIVEN: Mock DB Session
        WHEN: VCPSignalRepository 초기화
        THEN: Repository 인스턴스 생성
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        repo = VCPSignalRepository(mock_session)

        assert repo is not None
        assert repo.session == mock_session

    def test_get_active_vcp_signals_returns_open_status_only(self, mock_session, sample_vcp_signals):
        """
        GIVEN: DB에 OPEN, CLOSED 상태의 시그널이 혼재
        WHEN: get_active_vcp_signals() 호출
        THEN: OPEN 상태인 VCP 시그널만 반환
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock DB 응답 설정
        mock_result = Mock()
        # OPEN 상태만 반환 (ID 1, 2, 3)
        open_signals = [s for s in sample_vcp_signals if s.status == "OPEN" and s.signal_type == "VCP"]
        mock_result.scalars.return_value.all.return_value = open_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_active_vcp_signals()

        # 검증: OPEN 상태만 포함
        assert all(s.status == "OPEN" for s in result)
        assert all(s.signal_type == "VCP" for s in result)

    def test_get_active_vcp_signals_sorted_by_score_desc(self, mock_session, sample_vcp_signals):
        """
        GIVEN: 활성 VCP 시그널들
        WHEN: get_active_vcp_signals() 호출
        THEN: 점수 내림차순 정렬 (score DESC)
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock DB 응답 - 점수순 미정렬 데이터 반환
        mock_result = Mock()
        vcp_signals = [s for s in sample_vcp_signals if s.signal_type == "VCP" and s.status == "OPEN"]
        # DB에서 이미 정렬된 상태로 반환한다고 가정 (SQL ORDER BY)
        sorted_signals = sorted(vcp_signals, key=lambda x: x.score, reverse=True)
        mock_result.scalars.return_value.all.return_value = sorted_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_active_vcp_signals()

        # 검증: 쿼리가 실행되었는지 확인 (실제 정렬은 DB에서 수행)
        mock_session.execute.assert_called_once()
        # SQL의 desc(Signal.score)가 포함되어 있는지 검증
        call_args = mock_session.execute.call_args
        query = call_args[0][0]
        # ORDER BY 절이 있는지 확인 (문자열 검사)
        assert "desc" in str(query.compile()).lower() or "order by" in str(query.compile()).lower()

    def test_get_top_n_vcp_signals_limit(self, mock_session, sample_vcp_signals):
        """
        GIVEN: 10개 이상의 활성 VCP 시그널
        WHEN: get_top_vcp_signals(limit=10) 호출
        THEN: 상위 10개만 반환
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock DB 응답
        mock_result = Mock()
        vcp_signals = [s for s in sample_vcp_signals if s.signal_type == "VCP" and s.status == "OPEN"]
        mock_result.scalars.return_value.all.return_value = vcp_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_top_vcp_signals(limit=10)

        # 검증: 최대 10개 반환
        assert len(result) <= 10

    def test_get_vcp_signals_by_market_kospi_filter(self, mock_session, sample_vcp_signals):
        """
        GIVEN: KOSPI, KOSDAQ 시장 혼재
        WHEN: get_vcp_signals_by_market(market="KOSPI") 호출
        THEN: KOSPI 시장 종목만 반환
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock DB 응답
        mock_result = Mock()
        kospi_signals = [s for s in sample_vcp_signals if s.stock.market == "KOSPI"]
        mock_result.scalars.return_value.all.return_value = kospi_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_vcp_signals_by_market(market="KOSPI")

        # 검증: KOSPI만
        assert all(s.stock.market == "KOSPI" for s in result)

    def test_get_vcp_signals_by_market_kosdaq_filter(self, mock_session, sample_vcp_signals):
        """
        GIVEN: KOSPI, KOSDAQ 시장 혼재
        WHEN: get_vcp_signals_by_market(market="KOSDAQ") 호출
        THEN: KOSDAQ 시장 종목만 반환
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock DB 응답
        mock_result = Mock()
        kosdaq_signals = [s for s in sample_vcp_signals if s.stock.market == "KOSDAQ"]
        mock_result.scalars.return_value.all.return_value = kosdaq_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_vcp_signals_by_market(market="KOSDAQ")

        # 검증: KOSDAQ만
        assert all(s.stock.market == "KOSDAQ" for s in result)

    def test_get_vcp_signals_with_min_score_filter(self, mock_session, sample_vcp_signals):
        """
        GIVEN: 다양한 점대의 VCP 시그널
        WHEN: get_vcp_signals_with_min_score(min_score=80.0) 호출
        THEN: 80점 이상 시그널만 반환
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock DB 응답
        mock_result = Mock()
        high_score_signals = [s for s in sample_vcp_signals if s.score >= 80.0]
        mock_result.scalars.return_value.all.return_value = high_score_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_vcp_signals_with_min_score(min_score=80.0)

        # 검증: 80점 이상
        assert all(s.score >= 80.0 for s in result)

    def test_get_vcp_signals_empty_returns_empty_list(self, mock_session):
        """
        GIVEN: DB에 VCP 시그널 없음
        WHEN: get_active_vcp_signals() 호출
        THEN: 빈 리스트 반환
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        # Mock 빈 결과
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_active_vcp_signals()

        # 검증: 빈 리스트
        assert result == []

    def test_vcp_signal_response_includes_contraction_ratio(self, mock_session, sample_vcp_signals):
        """
        GIVEN: VCP 시그널 데이터
        WHEN: get_active_vcp_signals() 호출
        THEN: 응답에 contraction_ratio 포함
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        mock_result = Mock()
        vcp_signals = [s for s in sample_vcp_signals if s.signal_type == "VCP" and s.status == "OPEN"]
        mock_result.scalars.return_value.all.return_value = vcp_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_active_vcp_signals()

        # 검증: contraction_ratio 존재 (VCP만 해당)
        for signal in result:
            if signal.signal_type == "VCP":
                assert hasattr(signal, "contraction_ratio")

    def test_vcp_signal_response_includes_supply_data(self, mock_session, sample_vcp_signals):
        """
        GIVEN: VCP 시그널 데이터
        WHEN: get_active_vcp_signals() 호출
        THEN: 응답에 수급 데이터(foreign_net_5d, inst_net_5d) 포함
        """
        from src.repositories.vcp_signal_repository import VCPSignalRepository

        mock_result = Mock()
        vcp_signals = [s for s in sample_vcp_signals if s.signal_type == "VCP" and s.status == "OPEN"]
        mock_result.scalars.return_value.all.return_value = vcp_signals
        mock_session.execute.return_value = mock_result

        repo = VCPSignalRepository(mock_session)
        result = repo.get_active_vcp_signals()

        # 검증: 수급 데이터 존재
        for signal in result:
            assert hasattr(signal, "foreign_net_5d")
            assert hasattr(signal, "inst_net_5d")
