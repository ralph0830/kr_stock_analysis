"""
Stock Repository 단위 테스트

종목 관련 데이터 접근 계층을 테스트합니다.
CRUD 작업, 쿼리 로직을 검증합니다.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import date, timedelta

from src.repositories.stock_repository import StockRepository
from src.database.models import Stock


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Mock DB 세션"""
    session = MagicMock()
    return session


@pytest.fixture
def stock_repository(mock_session):
    """StockRepository 인스턴스"""
    return StockRepository(mock_session)


@pytest.fixture
def sample_stock():
    """샘플 Stock 객체"""
    stock = Stock()
    stock.id = 1
    stock.ticker = "005930"
    stock.name = "삼성전자"
    stock.market = "KOSPI"
    stock.sector = "전기전자"
    stock.market_cap = 500000000000000
    stock.is_etf = False
    stock.is_admin = False
    return stock


# =============================================================================
# 1. CRUD 기본 테스트
# =============================================================================

class TestStockRepositoryCRUD:
    """StockRepository CRUD 테스트"""

    def test_get_by_ticker_found(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 존재하는 종목코드
        WHEN: get_by_ticker()를 호출하면
        THEN: 해당 종목을 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_stock
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.get_by_ticker("005930")

        # Assert
        assert result is not None
        assert result.ticker == "005930"
        assert result.name == "삼성전자"

    def test_get_by_ticker_not_found(self, stock_repository, mock_session):
        """
        GIVEN: 존재하지 않는 종목코드
        WHEN: get_by_ticker()를 호출하면
        THEN: None을 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.get_by_ticker("999999")

        # Assert
        assert result is None

    def test_list_all_no_filters(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 필터 없는 요청
        WHEN: list_all()를 호출하면
        THEN: 전체 종목 목록을 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_stock]
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.list_all()

        # Assert
        assert len(result) == 1
        assert result[0].ticker == "005930"

    def test_list_all_with_market_filter(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 시장 필터
        WHEN: list_all(market="KOSPI")를 호출하면
        THEN: KOSPI 종목만 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_stock]
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.list_all(market="KOSPI")

        # Assert
        assert len(result) == 1
        assert result[0].market == "KOSPI"


# =============================================================================
# 2. 검색 기능 테스트
# =============================================================================

class TestStockRepositorySearch:
    """StockRepository 검색 기능 테스트"""

    def test_search_by_name(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 종목명 키워드
        WHEN: search()를 호출하면
        THEN: 이름에 키워드가 포함된 종목을 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_stock]
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.search("삼성")

        # Assert
        assert len(result) == 1
        assert "삼성" in result[0].name

    def test_search_by_ticker(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 종목코드 키워드
        WHEN: search()를 호출하면
        THEN: 티커에 키워드가 포함된 종목을 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_stock]
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.search("005930")

        # Assert
        assert len(result) == 1
        assert result[0].ticker == "005930"

    def test_search_empty_result(self, stock_repository, mock_session):
        """
        GIVEN: 없는 키워드
        WHEN: search()를 호출하면
        THEN: 빈 리스트를 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.search("없는종목")

        # Assert
        assert len(result) == 0


# =============================================================================
# 3. 생성 및 업데이트 테스트
# =============================================================================

class TestStockRepositoryCreateUpdate:
    """StockRepository 생성/업데이트 테스트"""

    def test_create_if_not_exists_new_stock(self, stock_repository, mock_session):
        """
        GIVEN: 존재하지 않는 종목
        WHEN: create_if_not_exists()를 호출하면
        THEN: 새 종목이 생성되어야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        new_stock = Stock()
        new_stock.ticker = "000660"
        new_stock.name = "SK하이닉스"
        new_stock.market = "KOSPI"

        stock_repository.create = Mock(return_value=new_stock)

        # Act
        result = stock_repository.create_if_not_exists(
            ticker="000660",
            name="SK하이닉스",
            market="KOSPI"
        )

        # Assert
        assert result is not None
        assert result.ticker == "000660"

    def test_create_if_not_exists_existing_stock(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 이미 존재하는 종목
        WHEN: create_if_not_exists()를 호출하면
        THEN: 기존 종목을 반환해야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_stock
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.create_if_not_exists(
            ticker="005930",
            name="삼성전자",
            market="KOSPI"
        )

        # Assert
        assert result is not None
        assert result.ticker == "005930"

    def test_update_market_cap(self, stock_repository, mock_session, sample_stock):
        """
        GIVEN: 존재하는 종목
        WHEN: update_market_cap()를 호출하면
        THEN: 시가총액이 업데이트되어야 함
        """
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_stock
        mock_session.execute.return_value = mock_result

        # Act
        result = stock_repository.update_market_cap("005930", 600000000000000)

        # Assert
        assert result is not None
        mock_session.commit.assert_called_once()
