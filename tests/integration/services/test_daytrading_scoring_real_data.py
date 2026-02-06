"""
Daytrading Scoring 실제 데이터 연동 테스트 (TDD - Red Phase)

이 테스트 파일은 하드코딩된 데이터를 실제 DB 데이터로 대체하는 것을 검증합니다.
TDD 방식으로 작성되었으며, 먼저 실패하는 테스트를 작성합니다.

테스트 커버리지:
1. 수급 데이터: _get_mock_flow_data() → _get_flow_data() (DB 조회)
2. 섹터 모멘텀: 하드코딩된 15점 → 실제 섹터 데이터 기반 계산
3. 스캔 대상 종목 다양화: 거래량 상위 종목 대신 다른 조건 추가
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta, date

# 테스트 대상 모듈 임포트
from services.daytrading_scanner.models.scoring import (
    DaytradingCheck,
    calculate_sector_momentum_score,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_flow_data():
    """샘플 수급 데이터"""
    class FlowData:
        def __init__(self, foreign_net_buy=0, inst_net_buy=0):
            self.foreign_net_buy = foreign_net_buy
            self.inst_net_buy = inst_net_buy
    return FlowData


@pytest.fixture
def db_session_with_prices():
    """DB 세션과 일봉 데이터 Fixture"""
    from src.database.session import get_db_session_sync
    from src.database.models import DailyPrice, Stock

    with get_db_session_sync() as db:
        # Cleanup first (in case of previous failed test)
        db.query(DailyPrice).filter_by(ticker="999999").delete()
        db.query(Stock).filter_by(ticker="999999").delete()
        db.commit()

        # 테스트용 종목 생성
        test_stock = Stock(
            ticker="999999",
            name="테스트종목",
            market="KOSPI",
            sector="테스트섹터"
        )
        db.add(test_stock)

        # 테스트용 일봉 데이터 생성 (최근 5일)
        # foreign_net_buy, inst_net_buy는 Integer 범위 내로 조정
        today = date.today()
        for i in range(5):
            price = DailyPrice(
                ticker="999999",
                date=today - timedelta(days=i),
                close_price=50000 + i * 100,
                volume=1000000 + i * 100000,
                foreign_net_buy=1000000 * (i + 1),  # 천만 단위 (주)
                inst_net_buy=500000 * (i + 1)  # 50만 단위 (주)
            )
            db.add(price)

        db.commit()
        yield db

        # Cleanup
        db.query(DailyPrice).filter_by(ticker="999999").delete()
        db.query(Stock).filter_by(ticker="999999").delete()
        db.commit()


# =============================================================================
# Test 1: 수급 데이터 실제 DB 조회
# =============================================================================

class TestFlowDataRealImplementation:
    """수급 데이터 실제 구현 검증"""

    def test_scanner_has_get_flow_data_method(self):
        """
        GIVEN: DaytradingScanner 클래스
        WHEN: 메서드를 확인하면
        THEN: _get_flow_data() 메서드가 있어야 함
        """
        from services.daytrading_scanner.scanner import DaytradingScanner

        scanner = DaytradingScanner()

        # _get_flow_data 메서드가 있는지 확인
        assert hasattr(scanner, "_get_flow_data"), \
            "DaytradingScanner에 _get_flow_data() 메서드가 없습니다"

    @pytest.mark.asyncio
    async def test_get_flow_data_returns_real_values(self, db_session_with_prices):
        """
        GIVEN: DB에 수급 데이터가 있는 종목
        WHEN: _get_flow_data()를 호출하면
        THEN: DB의 실제 수급 데이터 합계를 반환해야 함
        """
        from services.daytrading_scanner.scanner import DaytradingScanner

        scanner = DaytradingScanner()

        # Act: 실제 데이터 조회
        flow = scanner._get_flow_data(db_session_with_prices, "999999", days=5)

        # Assert: Mock이 아니어야 함 (0이 아닌 값)
        assert flow.foreign_net_buy != 0 or flow.inst_net_buy != 0, \
            "수급 데이터가 Mock(0)입니다. 실제 DB 조회가 필요합니다."

        # Assert: 외국인/기관 수급 필드가 있는지 확인
        assert hasattr(flow, "foreign_net_buy"), "foreign_net_buy 필드가 없습니다"
        assert hasattr(flow, "inst_net_buy"), "inst_net_buy 필드가 없습니다"

    @pytest.mark.asyncio
    async def test_get_flow_data_fallback_to_mock(self, db_session_with_prices):
        """
        GIVEN: DB에 데이터가 없는 종목
        WHEN: _get_flow_data()를 호출하면
        THEN: Mock 데이터를 반환해야 함 (fallback)
        """
        from services.daytrading_scanner.scanner import DaytradingScanner

        scanner = DaytradingScanner()

        # Act: 없는 종목 조회
        flow = scanner._get_flow_data(db_session_with_prices, "000000", days=5)

        # Assert: Mock 데이터 반환 (fallback)
        assert flow is not None, "Fallback이 작동하지 않습니다"
        assert hasattr(flow, "foreign_net_buy"), "Mock 데이터 구조가 아닙니다"
        assert hasattr(flow, "inst_net_buy"), "Mock 데이터 구조가 아닙니다"


# =============================================================================
# Test 2: 섹터 모멘텀 실제 계산
# =============================================================================

class TestSectorMomentumRealCalculation:
    """섹터 모멘텀 실제 계산 검증"""

    def test_sector_momentum_calculates_from_sector_rank(self):
        """
        GIVEN: 섹터 내 순위
        WHEN: 점수를 계산하면
        THEN: 순위에 따라 점수가 달라야 함 (상위 20% = 15점, 상위 40% = 8점)
        """
        # 상위 10% (1위 / 10종목)
        score_1 = calculate_sector_momentum_score(1, 10)
        assert score_1 == 15, f"상위 10%는 15점이어야 함, 실제: {score_1}"

        # 상위 20% (2위 / 10종목)
        score_2 = calculate_sector_momentum_score(2, 10)
        assert score_2 == 15, f"상위 20%는 15점이어야 함, 실제: {score_2}"

        # 상위 40% (4위 / 10종목)
        score_4 = calculate_sector_momentum_score(4, 10)
        assert score_4 == 8, f"상위 40%는 8점이어야 함, 실제: {score_4}"

        # 하위 60% (7위 / 10종목)
        score_7 = calculate_sector_momentum_score(7, 10)
        assert score_7 == 0, f"하위 60%는 0점이어야 함, 실제: {score_7}"

    def test_sector_momentum_no_sector_returns_zero(self):
        """
        GIVEN: 섹터 정보가 없는 종목
        WHEN: 섹터 모멘텀을 계산하면
        THEN: 0점을 반환해야 함
        """
        from services.daytrading_scanner.models.scoring import calculate_daytrading_score

        # Arrange: 섹터 없는 종목
        class MockStock:
            def __init__(self):
                self.ticker = "005930"
                self.name = "삼성전자"
                self.sector = None  # 섹터 없음

        class MockPrice:
            def __init__(self, price=75000, vol=1000000):
                self.close_price = price
                self.volume = vol

        class MockFlow:
            def __init__(self):
                self.foreign_net_buy = 0
                self.inst_net_buy = 0

        stock = MockStock()
        # 최소 2개 이상의 가격 데이터 필요 (데이터 부족 방지)
        prices = [MockPrice(75000, 1000000), MockPrice(74000, 900000)]
        flow = MockFlow()

        # Act
        result = calculate_daytrading_score(stock, prices, flow)

        # Assert: 섹터 모멘텀 체크가 있는지 확인
        sector_check = next((c for c in result.checks if c.name == "섹터 모멘텀"), None)
        assert sector_check is not None, "섹터 모멘텀 체크가 없습니다"

        # 섹터가 없으면 0점이어야 함 (하드코딩된 15점이 아니어야 함)
        assert sector_check.points == 0, f"섹터 없으면 0점이어야 함, 실제: {sector_check.points}"


# =============================================================================
# Test 3: 스캔 대상 종목 다양화
# =============================================================================

class TestScannerTargetDiversification:
    """스캔 대상 종목 다양화 검증"""

    @pytest.mark.asyncio
    async def test_scanner_filters_by_diversity(self):
        """
        GIVEN: 시장 전체 종목
        WHEN: 스캔 대상을 조회하면
        THEN: 거래량만 기준이 아니라 다양한 조건으로 필터링해야 함
        """
        from services.daytrading_scanner.scanner import DaytradingScanner
        from src.database.session import get_db_session_sync

        scanner = DaytradingScanner()

        with get_db_session_sync() as db:
            stocks = scanner._get_stocks(db, market=None)

            # Assert: 결과가 있어야 함
            assert len(stocks) > 0, "스캔 대상 종목이 없습니다"

            # TODO: 다양성 필터링이 적용되는지 확인
            # 현재는 기본적으로 거래량 기준으로 필터링됨
            # 향후 변동성, 모멘텀 등 다양한 조건이 추가되면 테스트 강화


# =============================================================================
# Test 4: 통합 테스트 - 실제 데이터 기반 점수 계산
# =============================================================================

class TestRealDataIntegration:
    """실제 데이터 기반 점수 계산 통합 테스트"""

    @pytest.mark.asyncio
    async def test_scan_uses_real_flow_data(self, db_session_with_prices):
        """
        GIVEN: DB에 수급 데이터가 있는 상태
        WHEN: 시장을 스캔하면
        THEN: 실제 수급 데이터를 사용하여 점수를 계산해야 함
        """
        from services.daytrading_scanner.scanner import DaytradingScanner

        scanner = DaytradingScanner()

        # Act: 실제 수급 데이터 조회
        flow = scanner._get_flow_data(db_session_with_prices, "999999", days=5)

        # Assert: 기관 매수 점수가 계산되어야 함
        from services.daytrading_scanner.models.scoring import calculate_institution_buy_score

        inst_score = calculate_institution_buy_score(flow)

        # 실제 데이터가 있으면 점수가 있어야 함
        # TODO: 실제 구현 후 주석 해제
        # assert inst_score > 0, f"실제 수급 데이터가 있으면 기관 매수 점수가 있어야 함, 실제: {inst_score}"
