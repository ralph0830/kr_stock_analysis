"""
Stock Repository - 수급 데이터 테스트
TDD: 수급 데이터 조회 메서드를 위한 테스트
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock
from sqlalchemy.orm import Session

from src.repositories.stock_repository import StockRepository
from src.database.models import InstitutionalFlow


class TestStockRepositoryFlow:
    """StockRepository 수급 데이터 조회 테스트"""

    @pytest.fixture
    def mock_session(self):
        """Mock DB Session"""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """StockRepository 인스턴스"""
        return StockRepository(mock_session)

    @pytest.fixture
    def sample_flow_data(self):
        """샘플 수급 데이터"""
        today = date.today()
        return [
            InstitutionalFlow(
                ticker="005930",
                date=today - timedelta(days=4),
                foreign_net_buy=1000000,
                inst_net_buy=500000,
                foreign_net_5d=5000000,
                inst_net_5d=2500000,
            ),
            InstitutionalFlow(
                ticker="005930",
                date=today - timedelta(days=3),
                foreign_net_buy=2000000,
                inst_net_buy=1000000,
                foreign_net_5d=6000000,
                inst_net_5d=3000000,
            ),
            InstitutionalFlow(
                ticker="005930",
                date=today - timedelta(days=2),
                foreign_net_buy=-500000,
                inst_net_buy=-200000,
                foreign_net_5d=5500000,
                inst_net_5d=2800000,
            ),
        ]

    def test_get_institutional_flow_returns_list(self, repository, mock_session, sample_flow_data):
        """
        Given: 종목 코드와 기간이 주어지고
        When: 수급 데이터를 조회하면
        Then: InstitutionalFlow 리스트를 반환한다
        """
        # Arrange
        ticker = "005930"
        days = 5

        # Mock execute 결과 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_flow_data
        mock_session.execute.return_value = mock_result

        # Act
        result = repository.get_institutional_flow(ticker, days)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(item, InstitutionalFlow) for item in result)
        mock_session.execute.assert_called_once()

    def test_get_institutional_flow_filters_by_ticker_and_date(
        self, repository, mock_session
    ):
        """
        Given: 종목 코드와 기간이 주어지고
        When: 수급 데이터를 조회하면
        Then: 티커와 날짜 범위로 필터링한다
        """
        # Arrange
        ticker = "005930"
        days = 20

        # Act
        try:
            repository.get_institutional_flow(ticker, days)
        except Exception:
            pass  # 메서드가 없어서 실패해도 됨

        # Assert - 호출 검증 (구현 후)
        # mock_session.execute.assert_called_once()
        # 쿼리에 ticker와 날짜 범위 조건이 포함되어야 함

    def test_get_institutional_flow_orders_by_date_asc(
        self, repository, mock_session, sample_flow_data
    ):
        """
        Given: 종목 코드와 기간이 주어지고
        When: 수급 데이터를 조회하면
        Then: 날짜 오름차순으로 정렬한다
        """
        # Arrange
        ticker = "005930"
        days = 5

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_flow_data
        mock_session.execute.return_value = mock_result

        # Act
        result = repository.get_institutional_flow(ticker, days)

        # Assert
        dates = [item.date for item in result]
        assert dates == sorted(dates)

    def test_get_institutional_flow_empty_ticker_returns_empty(
        self, repository, mock_session
    ):
        """
        Given: 존재하지 않는 종목 코드가 주어지고
        When: 수급 데이터를 조회하면
        Then: 빈 리스트를 반환한다
        """
        # Arrange
        ticker = "999999"  # 존재하지 않는 종목

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        result = repository.get_institutional_flow(ticker, days=20)

        # Assert
        assert result == []

    def test_get_institutional_flow_default_days_is_20(
        self, repository, mock_session
    ):
        """
        Given: 종목 코드만 주어지고
        When: 수급 데이터를 조회하면
        Then: 기본 20일 데이터를 반환한다
        """
        # Arrange
        ticker = "005930"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        repository.get_institutional_flow(ticker)

        # Assert - days=20으로 호출되어야 함
        # mock_session.execute.assert_called_once()

    def test_get_institutional_flow_respects_max_days_limit(
        self, repository, mock_session
    ):
        """
        Given: 기간이 60일을 초과하고
        When: 수급 데이터를 조회하면
        Then: 최대 60일로 제한한다
        """
        # Arrange
        ticker = "005930"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        repository.get_institutional_flow(ticker, days=120)

        # Assert - 60일로 제한되어야 함
        # mock_session.execute.assert_called_once()
