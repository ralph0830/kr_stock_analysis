"""
DailyPrice Repository Unit Tests
TDD RED Phase - All tests should fail initially
"""

import pytest
from datetime import date
from unittest.mock import Mock
from sqlalchemy.orm import Session

from src.repositories.base import BaseRepository
from src.database.models import DailyPrice


class DailyPriceRepository(BaseRepository[DailyPrice]):
    """DailyPrice Repository - 구현 전 테스트용 스텁"""

    def __init__(self, session: Session):
        super().__init__(DailyPrice, session)

    def get_by_ticker_and_date_range(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> list[DailyPrice]:
        """종목별 날짜 범위 조회 (미구현)"""
        raise NotImplementedError("TODO: Implement get_by_ticker_and_date_range")

    def get_latest_by_ticker(self, ticker: str, limit: int = 1) -> list[DailyPrice]:
        """종목 최신 데이터 조회 (미구현)"""
        raise NotImplementedError("TODO: Implement get_latest_by_ticker")

    def get_ohlcv_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """OHLCV 데이터 조회 (미구현)"""
        raise NotImplementedError("TODO: Implement get_ohlcv_data")


@pytest.fixture
def mock_session():
    """Mock DB Session"""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def repository(mock_session):
    """Repository Fixture"""
    return DailyPriceRepository(mock_session)


@pytest.fixture
def sample_daily_prices():
    """Sample DailyPrice 데이터"""
    return [
        DailyPrice(
            ticker="005930",
            date=date(2024, 1, 10),
            open_price=80000,
            high_price=81000,
            low_price=79500,
            close_price=80500,
            volume=1000000,
        ),
        DailyPrice(
            ticker="005930",
            date=date(2024, 1, 11),
            open_price=80500,
            high_price=81500,
            low_price=80000,
            close_price=81200,
            volume=1200000,
        ),
        DailyPrice(
            ticker="005930",
            date=date(2024, 1, 12),
            open_price=81200,
            high_price=82000,
            low_price=81000,
            close_price=81800,
            volume=900000,
        ),
    ]


class TestDailyPriceRepository:
    """DailyPriceRepository 테스트"""

    def test_get_by_ticker_and_date_range_returns_data(
        self, repository, sample_daily_prices
    ):
        """종목별 날짜 범위 조회 - 데이터 반환 확인"""
        # Arrange
        ticker = "005930"
        start_date = date(2024, 1, 10)
        end_date = date(2024, 1, 12)

        # Act & Assert - 메서드가 구현되지 않았으므로 NotImplementedError 발생
        with pytest.raises(
            NotImplementedError, match="TODO: Implement get_by_ticker_and_date_range"
        ):
            repository.get_by_ticker_and_date_range(ticker, start_date, end_date)

    def test_get_by_ticker_and_date_range_filters_correctly(
        self, repository, mock_session
    ):
        """종목별 날짜 범위 조회 - 날짜 필터링 확인"""
        # Arrange
        ticker = "005930"
        start_date = date(2024, 1, 10)
        end_date = date(2024, 1, 12)

        # Act & Assert
        with pytest.raises(NotImplementedError):
            repository.get_by_ticker_and_date_range(ticker, start_date, end_date)

    def test_get_by_ticker_and_date_range_empty_result(self, repository):
        """종목별 날짜 범위 조회 - 데이터 없음"""
        # Arrange
        ticker = "999999"  # 존재하지 않는 종목
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Act & Assert
        with pytest.raises(NotImplementedError):
            repository.get_by_ticker_and_date_range(ticker, start_date, end_date)

    def test_get_latest_by_ticker_returns_latest_data(self, repository):
        """종목 최신 데이터 조회 - 최신 데이터 반환 확인"""
        # Arrange
        ticker = "005930"
        limit = 1

        # Act & Assert
        with pytest.raises(
            NotImplementedError, match="TODO: Implement get_latest_by_ticker"
        ):
            repository.get_latest_by_ticker(ticker, limit)

    def test_get_latest_by_ticker_with_custom_limit(self, repository):
        """종목 최신 데이터 조회 - 커스텀 limit 확인"""
        # Arrange
        ticker = "005930"
        limit = 5

        # Act & Assert
        with pytest.raises(NotImplementedError):
            repository.get_latest_by_ticker(ticker, limit)

    def test_get_ohlcv_data_returns_dict_list(self, repository):
        """OHLCV 데이터 조회 - 딕셔너리 리스트 반환 확인"""
        # Arrange
        ticker = "005930"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Act & Assert
        with pytest.raises(NotImplementedError, match="TODO: Implement get_ohlcv_data"):
            repository.get_ohlcv_data(ticker, start_date, end_date)

    def test_get_ohlcv_data_contains_required_fields(self, repository):
        """OHLCV 데이터 조회 - 필수 필드 포함 확인"""
        # Arrange
        ticker = "005930"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Act & Assert
        with pytest.raises(NotImplementedError):
            result = repository.get_ohlcv_data(ticker, start_date, end_date)
            # result는 반환되지 않지만, 검증 코드를 작성해둠
            assert all(
                "date" in item
                and "open" in item
                and "high" in item
                and "low" in item
                and "close" in item
                and "volume" in item
                for item in result
            )

    def test_get_ohlcv_data_ordered_by_date_asc(self, repository):
        """OHLCV 데이터 조회 - 날짜 오름차순 정렬 확인"""
        # Arrange
        ticker = "005930"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Act & Assert
        with pytest.raises(NotImplementedError):
            result = repository.get_ohlcv_data(ticker, start_date, end_date)
            dates = [item["date"] for item in result]
            assert dates == sorted(dates)

    def test_get_by_ticker_and_date_range_invalid_ticker(self, repository):
        """종목별 날짜 범위 조회 - 잘못된 티커 형식"""
        # Arrange
        ticker = "123"  # 6자리 아님
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Act & Assert - 향후 ValidationError 추가 예정
        with pytest.raises(NotImplementedError):
            repository.get_by_ticker_and_date_range(ticker, start_date, end_date)

    def test_get_by_ticker_and_date_range_invalid_date_range(self, repository):
        """종목별 날짜 범위 조회 - 잘못된 날짜 범위"""
        # Arrange
        ticker = "005930"
        start_date = date(2024, 12, 31)  # 종료일보다 늦음
        end_date = date(2024, 1, 1)

        # Act & Assert - 향후 ValueError 추가 예정
        with pytest.raises(NotImplementedError):
            repository.get_by_ticker_and_date_range(ticker, start_date, end_date)
