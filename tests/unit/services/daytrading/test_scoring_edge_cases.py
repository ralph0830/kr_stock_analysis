"""
Daytrading Scoring 경계값 테스트

점수 계산 로직의 경계값, 에러 케이스를 테스트합니다.
TDD 방식으로 작성되었습니다.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from services.daytrading_scanner.models.scoring import (
    # 점수 계산 함수
    calculate_volume_spike_score,
    calculate_momentum_breakout_score,
    calculate_box_breakout_score,
    calculate_ma5_above_score,
    calculate_institution_buy_score,
    calculate_oversold_bounce_score,
    calculate_sector_momentum_score,
    calculate_daytrading_score,
    get_grade_from_score,

    # 데이터 클래스
    DaytradingCheck,
    DaytradingScoreResult,

    # 헬퍼 함수
    _calculate_percentage,
    _is_within_percent,
    _calculate_20d_high_low,
    _check_new_high,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_stock():
    """Mock 종목 데이터"""
    stock = Mock()
    stock.ticker = "005930"
    stock.name = "삼성전자"
    stock.market = "KOSPI"
    stock.sector = "전기전자"
    return stock


@pytest.fixture
def mock_prices():
    """Mock 일봉 데이터 (최신 순)"""
    prices = []
    base_price = 70000
    base_date = datetime.now(timezone.utc)

    for i in range(20):
        price = Mock()
        price.close_price = base_price + (i * 100)
        price.high_price = base_price + (i * 100) + 500
        price.low_price = base_price + (i * 100) - 500
        price.volume = 10000000 + (i * 500000)
        price.date = base_date
        prices.append(price)

    return prices


@pytest.fixture
def mock_flow():
    """Mock 수급 데이터"""
    flow = Mock()
    flow.foreign_net_buy = 50000000000  # 500억
    flow.inst_net_buy = 30000000000  # 300억
    return flow


# =============================================================================
# 1. 거래량 폭증 점수 (15점 만점)
# =============================================================================

class TestVolumeSpikeScore:
    """거래량 폭증 점수 계산 테스트"""

    def test_volume_spike_2x_returns_15(self):
        """
        GIVEN: 현재 거래량이 평균의 2배
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 15점을 반환해야 함
        """
        # Arrange
        current_volume = 20000000
        avg_volume = 10000000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 15

    def test_volume_spike_exactly_2x_returns_15(self):
        """
        GIVEN: 현재 거래량이 정확히 평균의 2배
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 15점을 반환해야 함 (경계값)
        """
        # Arrange
        current_volume = 20000
        avg_volume = 10000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 15

    def test_volume_spike_1_5x_returns_8(self):
        """
        GIVEN: 현재 거래량이 평균의 1.5배
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        current_volume = 15000
        avg_volume = 10000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 8

    def test_volume_spike_between_1_5x_and_2x_returns_8(self):
        """
        GIVEN: 현재 거래량이 평균의 1.5배~2배 사이
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 8점을 반환해야 함
        """
        # Arrange
        current_volume = 17500
        avg_volume = 10000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 8

    def test_volume_spike_below_1_5x_returns_0(self):
        """
        GIVEN: 현재 거래량이 평균의 1.5배 미만
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        current_volume = 14999
        avg_volume = 10000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 0

    def test_volume_spike_normal_volume_returns_0(self):
        """
        GIVEN: 현재 거래량이 평균과 같음
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        current_volume = 10000
        avg_volume = 10000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 0

    def test_volume_spike_zero_avg_volume_returns_0(self):
        """
        GIVEN: 평균 거래량이 0
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 0점을 반환해야 함 (에러 방지)
        """
        # Arrange
        current_volume = 100000
        avg_volume = 0

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 0

    def test_volume_spike_zero_current_volume_returns_0(self):
        """
        GIVEN: 현재 거래량이 0
        WHEN: calculate_volume_spike_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        current_volume = 0
        avg_volume = 10000

        # Act
        score = calculate_volume_spike_score(current_volume, avg_volume)

        # Assert
        assert score == 0


# =============================================================================
# 2. 모멘텀 돌파 점수 (15점 만점)
# =============================================================================

class TestMomentumBreakoutScore:
    """모멘텀 돌파 점수 계산 테스트"""

    def test_new_high_returns_15(self):
        """
        GIVEN: 신고가 갱신
        WHEN: calculate_momentum_breakout_score()를 호출하면
        THEN: 15점을 반환해야 함
        """
        # Arrange
        current_price = 75000
        high_20d = 70000
        new_high_20d = 72000
        is_new_high = True

        # Act
        score = calculate_momentum_breakout_score(
            current_price, high_20d, new_high_20d, is_new_high
        )

        # Assert
        assert score == 15

    def test_2_percent_above_high_returns_15(self):
        """
        GIVEN: 직전 20일 고가보다 +2% 이상
        WHEN: calculate_momentum_breakout_score()를 호출하면
        THEN: 15점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 71400  # 70000 * 1.02
        high_20d = 70000
        new_high_20d = 72000
        is_new_high = False

        # Act
        score = calculate_momentum_breakout_score(
            current_price, high_20d, new_high_20d, is_new_high
        )

        # Assert
        assert score == 15

    def test_1_percent_above_high_returns_8(self):
        """
        GIVEN: 직전 20일 고가보다 +1% 이상
        WHEN: calculate_momentum_breakout_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 70700  # 70000 * 1.01
        high_20d = 70000
        new_high_20d = 72000
        is_new_high = False

        # Act
        score = calculate_momentum_breakout_score(
            current_price, high_20d, new_high_20d, is_new_high
        )

        # Assert
        assert score == 8

    def test_below_1_percent_above_high_returns_0(self):
        """
        GIVEN: 직전 20일 고가보다 +1% 미만
        WHEN: calculate_momentum_breakout_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 70000  # 정확히 고가와 같음
        high_20d = 70000
        new_high_20d = 72000
        is_new_high = False

        # Act
        score = calculate_momentum_breakout_score(
            current_price, high_20d, new_high_20d, is_new_high
        )

        # Assert
        assert score == 0

    def test_zero_high_returns_0(self):
        """
        GIVEN: 직전 20일 고가가 0
        WHEN: calculate_momentum_breakout_score()를 호출하면
        THEN: 0점을 반환해야 함 (에러 방지)
        """
        # Arrange
        current_price = 70000
        high_20d = 0
        new_high_20d = 0
        is_new_high = False

        # Act
        score = calculate_momentum_breakout_score(
            current_price, high_20d, new_high_20d, is_new_high
        )

        # Assert
        assert score == 0


# =============================================================================
# 3. 박스권 탈출 점수 (15점 만점)
# =============================================================================

class TestBoxBreakoutScore:
    """박스권 탈출 점수 계산 테스트"""

    def test_above_box_high_returns_15(self):
        """
        GIVEN: 현재가가 박스 상단 이상
        WHEN: calculate_box_breakout_score()를 호출하면
        THEN: 15점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 70000
        box_high = 70000
        box_low = 65000

        # Act
        score = calculate_box_breakout_score(current_price, box_high, box_low)

        # Assert
        assert score == 15

    def test_above_box_mid_returns_8(self):
        """
        GIVEN: 현재가가 박스 중간 이상
        WHEN: calculate_box_breakout_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 67500  # (70000 + 65000) / 2
        box_high = 70000
        box_low = 65000

        # Act
        score = calculate_box_breakout_score(current_price, box_high, box_low)

        # Assert
        assert score == 8

    def test_below_box_mid_returns_0(self):
        """
        GIVEN: 현재가가 박스 중간 미만
        WHEN: calculate_box_breakout_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 67499
        box_high = 70000
        box_low = 65000

        # Act
        score = calculate_box_breakout_score(current_price, box_high, box_low)

        # Assert
        assert score == 0

    def test_at_box_low_returns_0(self):
        """
        GIVEN: 현재가가 박스 하단
        WHEN: calculate_box_breakout_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        current_price = 65000
        box_high = 70000
        box_low = 65000

        # Act
        score = calculate_box_breakout_score(current_price, box_high, box_low)

        # Assert
        assert score == 0


# =============================================================================
# 4. 5일선 위 점수 (15점 만점)
# =============================================================================

class TestMA5AboveScore:
    """5일선 위 점수 계산 테스트"""

    def test_above_ma5_returns_15(self):
        """
        GIVEN: 현재가가 5일선 위
        WHEN: calculate_ma5_above_score()를 호출하면
        THEN: 15점을 반환해야 함
        """
        # Arrange
        current_price = 71000
        ma5 = 70000

        # Act
        score = calculate_ma5_above_score(current_price, ma5)

        # Assert
        assert score == 15

    def test_within_1_percent_of_ma5_returns_8(self):
        """
        GIVEN: 현재가가 5일선 ±1% 범위 내
        WHEN: calculate_ma5_above_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 70000  # MA5와 같음
        ma5 = 70000

        # Act
        score = calculate_ma5_above_score(current_price, ma5)

        # Assert
        assert score == 8

    def test_within_1_percent_below_ma5_returns_8(self):
        """
        GIVEN: 현재가가 5일선 -1% 범위 내
        WHEN: calculate_ma5_above_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 69300  # 70000 * 0.99
        ma5 = 70000

        # Act
        score = calculate_ma5_above_score(current_price, ma5)

        # Assert
        assert score == 8

    def test_below_1_percent_of_ma5_returns_0(self):
        """
        GIVEN: 현재가가 5일선 -1% 미만
        WHEN: calculate_ma5_above_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        current_price = 69299
        ma5 = 70000

        # Act
        score = calculate_ma5_above_score(current_price, ma5)

        # Assert
        assert score == 0

    def test_zero_ma5_returns_0(self):
        """
        GIVEN: 5일선이 0
        WHEN: calculate_ma5_above_score()를 호출하면
        THEN: 0점을 반환해야 함 (에러 방지)
        """
        # Arrange
        current_price = 70000
        ma5 = 0

        # Act
        score = calculate_ma5_above_score(current_price, ma5)

        # Assert
        assert score == 0


# =============================================================================
# 5. 기관 매수 점수 (15점 만점)
# =============================================================================

class TestInstitutionBuyScore:
    """기관 매수 점수 계산 테스트"""

    def test_100_billion_returns_15(self):
        """
        GIVEN: 기관/외국인 순매수 100억 이상
        WHEN: calculate_institution_buy_score()를 호출하면
        THEN: 15점을 반환해야 함 (경계값)
        """
        # Arrange
        flow = Mock()
        flow.foreign_net_buy = 60000000000  # 600억 (주 단위)
        flow.inst_net_buy = 50000000000  # 500억 (주 단위)

        # Act
        score = calculate_institution_buy_score(flow)

        # Assert
        assert score == 15

    def test_50_billion_returns_8(self):
        """
        GIVEN: 기관/외국인 순매수 50억 이상
        WHEN: calculate_institution_buy_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        flow = Mock()
        flow.foreign_net_buy = 4000000000  # 40억 (주 단위)
        flow.inst_net_buy = 1000000000  # 10억 (주 단위)

        # Act
        score = calculate_institution_buy_score(flow)

        # Assert
        assert score == 8

    def test_below_50_billion_returns_0(self):
        """
        GIVEN: 기관/외국인 순매수 50억 미만
        WHEN: calculate_institution_buy_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        flow = Mock()
        flow.foreign_net_buy = 3000000000  # 30억 (주 단위)
        flow.inst_net_buy = 1000000000  # 10억 (주 단위)

        # Act
        score = calculate_institution_buy_score(flow)

        # Assert
        assert score == 0

    def test_zero_net_buy_returns_0(self):
        """
        GIVEN: 기관/외국인 순매수 0
        WHEN: calculate_institution_buy_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        flow = Mock()
        flow.foreign_net_buy = 0
        flow.inst_net_buy = 0

        # Act
        score = calculate_institution_buy_score(flow)

        # Assert
        assert score == 0

    def test_net_sell_returns_0(self):
        """
        GIVEN: 기관/외국인 순매도
        WHEN: calculate_institution_buy_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        flow = Mock()
        flow.foreign_net_buy = -5000000000  # -50억
        flow.inst_net_buy = -3000000000  # -30억

        # Act
        score = calculate_institution_buy_score(flow)

        # Assert
        assert score == 0


# =============================================================================
# 6. 낙폭 과대 반등 점수 (15점 만점)
# =============================================================================

class TestOversoldBounceScore:
    """낙폭 과대 반등 점수 계산 테스트"""

    def test_big_drop_bounce_returns_15(self):
        """
        GIVEN: 전일 -3% 이상 하락 후 당일 +2% 이상 반등
        WHEN: calculate_oversold_bounce_score()를 호출하면
        THEN: 15점을 반환해야 함 (경계값)
        """
        # Arrange
        prev_close = 70000
        prev_change_rate = -3.0
        current_change_rate = 2.0

        # Act
        score = calculate_oversold_bounce_score(
            prev_close, prev_change_rate, current_change_rate
        )

        # Assert
        assert score == 15

    def test_small_drop_bounce_returns_8(self):
        """
        GIVEN: 전일 -1% 이상 하락 후 당일 양수
        WHEN: calculate_oversold_bounce_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        prev_close = 70000
        prev_change_rate = -1.5  # -1% ~ -3% 사이
        current_change_rate = 0.5

        # Act
        score = calculate_oversold_bounce_score(
            prev_close, prev_change_rate, current_change_rate
        )

        # Assert
        assert score == 8

    def test_no_drop_no_score(self):
        """
        GIVEN: 전일 양수
        WHEN: calculate_oversold_bounce_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        prev_close = 70000
        prev_change_rate = 1.0
        current_change_rate = 2.0

        # Act
        score = calculate_oversold_bounce_score(
            prev_close, prev_change_rate, current_change_rate
        )

        # Assert
        assert score == 0

    def test_drop_still_falling_no_score(self):
        """
        GIVEN: 전일 하락 후 당일도 하락
        WHEN: calculate_oversold_bounce_score()를 호출하면
        THEN: 0점을 반환해야 함
        """
        # Arrange
        prev_close = 70000
        prev_change_rate = -2.0
        current_change_rate = -1.0

        # Act
        score = calculate_oversold_bounce_score(
            prev_close, prev_change_rate, current_change_rate
        )

        # Assert
        assert score == 0

    def test_below_threshold_drop_no_score(self):
        """
        GIVEN: 전일 -1% 미만 하락
        WHEN: calculate_oversold_bounce_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        prev_close = 70000
        prev_change_rate = -0.9
        current_change_rate = 1.0

        # Act
        score = calculate_oversold_bounce_score(
            prev_close, prev_change_rate, current_change_rate
        )

        # Assert
        assert score == 0


# =============================================================================
# 7. 섹터 모멘텀 점수 (15점 만점)
# =============================================================================

class TestSectorMomentumScore:
    """섹터 모멘텀 점수 계산 테스트"""

    def test_top_20_percent_returns_15(self):
        """
        GIVEN: 섹터 내 상위 20%
        WHEN: calculate_sector_momentum_score()를 호출하면
        THEN: 15점을 반환해야 함 (경계값)
        """
        # Arrange
        sector_rank = 2
        sector_total = 10

        # Act
        score = calculate_sector_momentum_score(sector_rank, sector_total)

        # Assert
        assert score == 15

    def test_top_40_percent_returns_8(self):
        """
        GIVEN: 섹터 내 상위 40%
        WHEN: calculate_sector_momentum_score()를 호출하면
        THEN: 8점을 반환해야 함 (경계값)
        """
        # Arrange
        sector_rank = 4
        sector_total = 10

        # Act
        score = calculate_sector_momentum_score(sector_rank, sector_total)

        # Assert
        assert score == 8

    def test_below_40_percent_returns_0(self):
        """
        GIVEN: 섹터 내 하위 60%
        WHEN: calculate_sector_momentum_score()를 호출하면
        THEN: 0점을 반환해야 함 (경계값)
        """
        # Arrange
        sector_rank = 5
        sector_total = 10

        # Act
        score = calculate_sector_momentum_score(sector_rank, sector_total)

        # Assert
        assert score == 0

    def test_zero_sector_total_returns_0(self):
        """
        GIVEN: 섹터 종목 수 0
        WHEN: calculate_sector_momentum_score()를 호출하면
        THEN: 0점을 반환해야 함 (에러 방지)
        """
        # Arrange
        sector_rank = 1
        sector_total = 0

        # Act
        score = calculate_sector_momentum_score(sector_rank, sector_total)

        # Assert
        assert score == 0


# =============================================================================
# 8. 종합 점수 및 등급
# =============================================================================

class TestOverallScoring:
    """종합 점수 및 등급 테스트"""

    def test_grade_s_requires_90_points(self):
        """
        GIVEN: 총 점수 90점 이상
        WHEN: get_grade_from_score()를 호출하면
        THEN: S등급을 반환해야 함 (경계값)
        """
        assert get_grade_from_score(90) == "S"
        assert get_grade_from_score(105) == "S"

    def test_grade_a_requires_75_points(self):
        """
        GIVEN: 총 점수 75점 이상
        WHEN: get_grade_from_score()를 호출하면
        THEN: A등급을 반환해야 함 (경계값)
        """
        assert get_grade_from_score(75) == "A"
        assert get_grade_from_score(89) == "A"

    def test_grade_b_requires_60_points(self):
        """
        GIVEN: 총 점수 60점 이상
        WHEN: get_grade_from_score()를 호출하면
        THEN: B등급을 반환해야 함 (경계값)
        """
        assert get_grade_from_score(60) == "B"
        assert get_grade_from_score(74) == "B"

    def test_grade_c_below_60_points(self):
        """
        GIVEN: 총 점수 60점 미만
        WHEN: get_grade_from_score()를 호출하면
        THEN: C등급을 반환해야 함 (경계값)
        """
        assert get_grade_from_score(59) == "C"
        assert get_grade_from_score(0) == "C"

    def test_calculate_daytrading_score_returns_result(self, mock_stock, mock_prices, mock_flow):
        """
        GIVEN: 완전한 데이터
        WHEN: calculate_daytrading_score()를 호출하면
        THEN: DaytradingScoreResult를 반환해야 함
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

    def test_calculate_daytrading_score_with_insufficient_data(self, mock_stock):
        """
        GIVEN: 데이터가 부족한 가격 데이터
        WHEN: calculate_daytrading_score()를 호출하면
        THEN: 0점 결과를 반환해야 함
        """
        # Arrange
        insufficient_prices = []

        # Act
        result = calculate_daytrading_score(mock_stock, insufficient_prices, Mock())

        # Assert
        assert result.total_score == 0
        assert result.grade == "C"
        assert len(result.checks) == 1
        assert result.checks[0].name == "데이터 부족"

    def test_calculate_daytrading_score_without_db(self, mock_stock, mock_prices, mock_flow):
        """
        GIVEN: DB 세션이 없음
        WHEN: calculate_daytrading_score()를 호출하면
        THEN: 섹터 모멘텀은 0점이어야 함
        """
        # Act
        result = calculate_daytrading_score(mock_stock, mock_prices, mock_flow, db=None)

        # Assert
        # 섹터 모멘텀 체크가 있어야 함
        sector_check = next((c for c in result.checks if "섹터" in c.name), None)
        assert sector_check is not None
        assert sector_check.points == 0


# =============================================================================
# 9. 헬퍼 함수 테스트
# =============================================================================

class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_calculate_percentage_normal_case(self):
        """
        GIVEN: 정상적인 기준값과 현재값
        WHEN: _calculate_percentage()를 호출하면
        THEN: 올바른 백분율을 반환해야 함
        """
        # Arrange
        base = 10000
        current = 10500

        # Act
        result = _calculate_percentage(base, current)

        # Assert
        assert result == 5.0

    def test_calculate_percentage_decrease(self):
        """
        GIVEN: 현재값이 기준값보다 작음
        WHEN: _calculate_percentage()를 호출하면
        THEN: 음수 백분율을 반환해야 함
        """
        # Arrange
        base = 10000
        current = 9500

        # Act
        result = _calculate_percentage(base, current)

        # Assert
        assert result == -5.0

    def test_calculate_percentage_zero_base(self):
        """
        GIVEN: 기준값이 0
        WHEN: _calculate_percentage()를 호출하면
        THEN: 0을 반환해야 함 (에러 방지)
        """
        # Arrange
        base = 0
        current = 10000

        # Act
        result = _calculate_percentage(base, current)

        # Assert
        assert result == 0.0

    def test_is_within_percent_true(self):
        """
        GIVEN: 현재값이 목표값의 ±percent 범위 내
        WHEN: _is_within_percent()를 호출하면
        THEN: True를 반환해야 함
        """
        # Arrange
        current = 10100
        target = 10000
        percent = 1.0

        # Act
        result = _is_within_percent(current, target, percent)

        # Assert
        assert result is True

    def test_is_within_percent_false(self):
        """
        GIVEN: 현재값이 목표값의 ±percent 범위 밖
        WHEN: _is_within_percent()를 호출하면
        THEN: False를 반환해야 함
        """
        # Arrange
        current = 10200
        target = 10000
        percent = 1.0

        # Act
        result = _is_within_percent(current, target, percent)

        # Assert
        assert result is False

    def test_is_within_percent_zero_target(self):
        """
        GIVEN: 목표값이 0
        WHEN: _is_within_percent()를 호출하면
        THEN: False를 반환해야 함 (에러 방지)
        """
        # Arrange
        current = 100
        target = 0
        percent = 1.0

        # Act
        result = _is_within_percent(current, target, percent)

        # Assert
        assert result is False
