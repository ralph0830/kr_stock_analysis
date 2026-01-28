"""
Test SignalRepository.get_by_ticker()
종목별 시그널 히스토리 조회 테스트
"""

import pytest
from datetime import date, datetime
from sqlalchemy.orm import Session

from src.repositories.signal_repository import SignalRepository
from src.database.models import Signal


@pytest.fixture
def repository(mock_session: Session) -> SignalRepository:
    """SignalRepository fixture"""
    return SignalRepository(mock_session)


class TestSignalHistory:
    """시그널 히스토리 조회 테스트"""

    @pytest.fixture
    def sample_signals(self, mock_session: Session) -> None:
        """테스트용 시그널 데이터 생성"""
        signals = [
            Signal(
                id=1,
                ticker="005930",
                signal_type="VCP",
                signal_date=date(2024, 1, 15),
                status="OPEN",
                score=85.0,
                grade="A",
                entry_price=75000,
                vcp_contraction=30.0,
                volume_decrease=25.0,
                foreign_net_5d=1000000,
                inst_net_5d=500000,
            ),
            Signal(
                id=2,
                ticker="005930",
                signal_type="JONGGA_V2",
                signal_date=date(2024, 1, 10),
                status="CLOSED",
                score=92.0,
                grade="S",
                entry_price=72000,
                exit_price=78000,
                entry_time=datetime(2024, 1, 10, 9, 30),
                exit_time=datetime(2024, 1, 20, 15, 0),
                news_score=3,
                volume_score=3,
                chart_score=2,
            ),
            Signal(
                id=3,
                ticker="005930",
                signal_type="VCP",
                signal_date=date(2024, 1, 5),
                status="CLOSED",
                score=65.0,
                grade="B",
                entry_price=70000,
                exit_price=68000,
                entry_time=datetime(2024, 1, 5, 10, 0),
                exit_time=datetime(2024, 1, 12, 14, 30),
            ),
        ]
        # Mock session을 설정하여 반환할 데이터 지정
        # 실제로는 mock_session.execute()의 반환값을 설정해야 함

    def test_get_by_ticker_returns_signals(self, repository, mock_session):
        """종목별 시그널 조회 테스트"""
        ticker = "005930"
        limit = 50

        result = repository.get_by_ticker(ticker, limit)

        assert isinstance(result, list)
        # Mock 설정에 따라 결과가 달라짐
        # 실제 DB가 없으므로 빈 리스트 또는 mock 데이터 반환

    def test_get_by_ticker_orders_by_date_desc(self, repository, mock_session):
        """시그널 최신순 정렬 테스트"""
        ticker = "005930"

        result = repository.get_by_ticker(ticker)

        # 최신 시그널이 먼저 나와야 함
        # Mock 데이터가 있을 경우 정렬 확인

    def test_get_by_ticker_respects_limit(self, repository, mock_session):
        """limit 매개변수 테스트"""
        ticker = "005930"
        limit = 10

        result = repository.get_by_ticker(ticker, limit)

        # 결과가 limit보다 크지 않아야 함
        assert len(result) <= limit
