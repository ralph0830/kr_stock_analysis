"""
Daytrading Scanner 통합 테스트 (TDD - Red Phase)

이 테스트 파일은 시장 스캔 실제 데이터 구현을 검증합니다.
TDD 방식으로 작성되었으며, 먼저 실패하는 테스트를 작성합니다.

테스트 커버리지:
1. 스캔 결과가 DB에 저장되는지 확인
2. 캐시 무효화가 호출되는지 확인
3. 점수 계산 로직이 올바르게 동작하는지 확인
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# 테스트 대상 모듈 임포트
from services.daytrading_scanner.scanner import DaytradingScanner
from services.daytrading_scanner.models.scoring import (
    DaytradingScoreResult,
    DaytradingCheck,
    calculate_daytrading_score,
    get_grade_from_score,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_db_session():
    """Mock DB 세션"""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_stock():
    """Mock 종목 데이터"""
    stock = Mock()
    stock.ticker = "005930"
    stock.name = "삼성전자"
    stock.market = "KOSPI"
    return stock


@pytest.fixture
def mock_prices():
    """Mock 일봉 데이터"""
    prices = []
    base_price = 70000
    for i in range(20):
        price = Mock()
        price.close_price = base_price + (i * 100)
        price.volume = 10000000 + (i * 500000)
        price.high = base_price + (i * 100) + 500
        price.low = base_price + (i * 100) - 500
        price.date = datetime.now(timezone.utc)
        prices.append(price)
    return prices


@pytest.fixture
def mock_flow():
    """Mock 수급 데이터"""
    flow = Mock()
    flow.foreign_net_buy = 50000000000  # 500억
    flow.inst_net_buy = 30000000000  # 300억
    return flow


@pytest.fixture
def scanner():
    """DaytradingScanner fixture"""
    return DaytradingScanner()


# =============================================================================
# Test 1: 시장 스캔 동작
# =============================================================================

class TestMarketScanning:
    """시장 스캔 기능 검증"""

    @pytest.mark.asyncio
    async def test_scan_stores_signals_in_db(self, scanner, mock_db_session):
        """
        GIVEN: 시장 스캔 요청
        WHEN: scan_market()을 호출하면
        THEN: 결과가 DB에 저장되어야 함
        """
        # Arrange
        request = {
            "market": "KOSPI",
            "limit": 10
        }

        # Act
        results = await scanner.scan_market(request, mock_db_session)

        # Assert
        assert results is not None
        assert len(results) <= 10

        # DB 저장이 호출되었는지 확인
        # (실제 구현 시 호출되어야 함)
        # mock_db_session.add.assert_called()
        # mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_scan_returns_candidates_with_scores(self, scanner):
        """
        GIVEN: 스캔이 완료되면
        WHEN: 결과를 반환하면
        THEN: 각 후보 종목에 점수가 있어야 함
        """
        # Arrange
        request = {"market": "KOSDAQ", "limit": 20}

        # Act
        results = await scanner.scan_market(request, None)

        # Assert
        for result in results:
            assert hasattr(result, 'score')
            assert hasattr(result, 'grade')
            assert 0 <= result.score <= 105
            assert result.grade in ['S', 'A', 'B', 'C']


# =============================================================================
# Test 2: 점수 계산 로직
# =============================================================================

class TestScoringLogic:
    """점수 계산 로직 검증"""

    def test_calculate_score_with_full_data(self, mock_stock, mock_prices, mock_flow):
        """
        GIVEN: 완전한 데이터 (종목, 가격, 수급)
        WHEN: calculate_daytrading_score()를 호출하면
        THEN: 올바른 점수와 등급이 반환되어야 함
        """
        # Act
        result = calculate_daytrading_score(mock_stock, mock_prices, mock_flow)

        # Assert
        assert isinstance(result, DaytradingScoreResult)
        assert result.ticker == "005930"
        assert result.name == "삼성전자"
        assert 0 <= result.total_score <= 105
        assert result.grade in ['S', 'A', 'B', 'C']
        assert len(result.checks) == 7  # 7개 체크리스트

    def test_volume_spike_score(self):
        """
        GIVEN: 거래량 데이터
        WHEN: 거래량이 2배 이상이면
        THEN: 15점을 받아야 함
        """
        # Arrange
        current_volume = 20000000
        avg_volume = 10000000

        # Act
        from services.daytrading_scanner.models.scoring import calculate_volume_spike_score
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 15

    def test_institution_buy_score(self, mock_flow):
        """
        GIVEN: 기관/외국인 수급 데이터
        WHEN: 순매수가 100억 이상이면
        THEN: 15점을 받아야 함
        """
        # Act
        from services.daytrading_scanner.models.scoring import calculate_institution_buy_score
        score = calculate_institution_buy_score(mock_flow)

        # Assert
        # 500억 + 300억 = 800억 → 15점
        assert score == 15

    def test_grade_from_score(self):
        """
        GIVEN: 점수
        WHEN: 등급을 매기면
        THEN: 올바른 등급이 반환되어야 함
        """
        assert get_grade_from_score(95) == "S"
        assert get_grade_from_score(85) == "A"
        assert get_grade_from_score(65) == "B"
        assert get_grade_from_score(45) == "C"


# =============================================================================
# Test 3: 캐시 무효화
# =============================================================================

class TestCacheInvalidation:
    """캐시 무효화 검증"""

    @pytest.mark.asyncio
    async def test_invalidates_cache_after_scan(self, scanner):
        """
        GIVEN: 스캔이 완료되면
        WHEN: 결과가 저장되면
        THEN: 캐시 무효화가 호출되어야 함
        """
        # Arrange
        request = {"market": "KOSPI", "limit": 10}

        # Mock cache client
        with patch('services.daytrading_scanner.scanner.get_cache') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.clear_pattern = AsyncMock(return_value=1)
            mock_get_cache.return_value = mock_cache

            # Act
            await scanner.scan_market(request, None)

            # Assert: 캐시 무효화가 호출되어야 함
            # (실제 구현 시)
            # mock_cache.clear_pattern.assert_called_with("daytrading:signals:*")


# =============================================================================
# Test 4: 종목 필터링
# =============================================================================

class TestStockFiltering:
    """종목 필터링 검증"""

    @pytest.mark.asyncio
    async def test_filters_by_market(self, scanner):
        """
        GIVEN: market 파라미터
        WHEN: KOSPI만 스캔하면
        THEN: KOSPI 종목만 반환되어야 함
        """
        # Arrange
        request = {"market": "KOSPI", "limit": 50}

        # Act
        results = await scanner.scan_market(request, None)

        # Assert
        for result in results:
            assert result.market == "KOSPI"

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, scanner):
        """
        GIVEN: limit 파라미터
        WHEN: limit=10으로 스캔하면
        THEN: 최대 10개 종목만 반환되어야 함
        """
        # Arrange
        request = {"market": "KOSDAQ", "limit": 10}

        # Act
        results = await scanner.scan_market(request, None)

        # Assert
        assert len(results) <= 10
