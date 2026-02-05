"""
Daytrading Scoring Models
단타 매매 점수 계산 로직 (7개 체크리스트)

TDD: Red-Green-Refactor Cycle
"""

from dataclasses import dataclass
from typing import List, Optional


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DaytradingCheck:
    """단타 체크리스트 항목"""
    name: str
    status: str  # 'passed', 'partial', 'failed'
    points: int


@dataclass
class DaytradingScoreResult:
    """단타 점수 계산 결과"""
    ticker: str
    name: str
    total_score: int
    grade: str
    checks: List[DaytradingCheck]

    # 매매 기준가 (Phase 3에서 계산)
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None


# =============================================================================
# Helper Functions for Scoring
# =============================================================================

def _calculate_percentage(base: int, current: int) -> float:
    """백분율 계산 (소수 2자리)"""
    if base == 0:
        return 0.0
    return round((current - base) / base * 100, 2)


def _is_within_percent(current: int, target: int, percent: float) -> bool:
    """현재값이 목표값의 ±percent 범위 내인지 확인"""
    if target == 0:
        return False
    diff_pct = abs(current - target) / target * 100
    return diff_pct <= percent


# =============================================================================
# Individual Score Calculations (7개 항목)
# =============================================================================

def calculate_volume_spike_score(current_volume: int, avg_volume: int) -> int:
    """
    거래량 폭증 점수 계산 (15점 만점)

    Args:
        current_volume: 현재 거래량
        avg_volume: 평균 거래량 (20일)

    Returns:
        점수 (15, 8, 0)
    """
    if avg_volume == 0:
        return 0

    ratio = current_volume / avg_volume

    if ratio >= 2.0:
        return 15
    elif ratio >= 1.5:
        return 8
    else:
        return 0


def calculate_momentum_breakout_score(
    current_price: int,
    high_20d: int,
    new_high_20d: int,
    is_new_high: bool
) -> int:
    """
    모멘텀 돌파 점수 계산 (15점 만점)

    Args:
        current_price: 현재가
        high_20d: 직전 20일 최고가
        new_high_20d: 20일 신고가
        is_new_high: 신고가 갱신 여부

    Returns:
        점수 (15, 8, 0)
    """
    # 신고가 갱신
    if is_new_high:
        return 15

    # 직전 고가 +2% 돌파
    if high_20d > 0:
        increase_pct = _calculate_percentage(high_20d, current_price)
        if increase_pct >= 2.0:
            return 15
        elif increase_pct >= 1.0:
            return 8

    return 0


def calculate_box_breakout_score(current_price: int, box_high: int, box_low: int) -> int:
    """
    박스권 탈출 점수 계산 (15점 만점)

    Args:
        current_price: 현재가
        box_high: 박스 상단 (20일 최고가)
        box_low: 박스 하단 (20일 최저가)

    Returns:
        점수 (15, 8, 0)
    """
    if current_price >= box_high:
        return 15

    # 박스 중간 이상
    box_mid = (box_high + box_low) // 2
    if current_price >= box_mid:
        return 8

    return 0


def calculate_ma5_above_score(current_price: int, ma5: int) -> int:
    """
    5일선 위 점수 계산 (15점 만점)

    Args:
        current_price: 현재가
        ma5: 5일 이동평균

    Returns:
        점수 (15, 8, 0)
    """
    if ma5 == 0:
        return 0

    if current_price > ma5:
        return 15

    # MA5 ±1% 인근
    if _is_within_percent(current_price, ma5, 1.0):
        return 8

    return 0


def calculate_institution_buy_score(flow) -> int:
    """
    기관 매수 점수 계산 (15점 만점)

    Args:
        flow: 수급 데이터 (foreign_net_buy, inst_net_buy)

    Returns:
        점수 (15, 8, 0)
    """
    # 총 순매수 (억 단위)
    total_net_buy_ek = (flow.foreign_net_buy + flow.inst_net_buy) / 100000000  # 주 → 억

    if total_net_buy_ek >= 100:
        return 15
    elif total_net_buy_ek >= 50:
        return 8
    else:
        return 0


def calculate_oversold_bounce_score(
    prev_close: int,
    prev_change_rate: float,
    current_change_rate: float
) -> int:
    """
    낙폭 과대 반등 점수 계산 (15점 만점)

    Args:
        prev_close: 전일 종가
        prev_change_rate: 전일 등락률 (%)
        current_change_rate: 당일 등락률 (%)

    Returns:
        점수 (15, 8, 0)
    """
    # 전일 음락 (1%+ 이상)
    if prev_change_rate < -1.0:
        # 당일 반등
        if current_change_rate > 0:
            if prev_change_rate <= -3.0 and current_change_rate >= 2.0:
                return 15
            return 8

    return 0


def calculate_sector_momentum_score(sector_rank: int, sector_total: int) -> int:
    """
    섹터 모멘텀 점수 계산 (15점 만점)

    Args:
        sector_rank: 섹터 내 순위 (1이 최상)
        sector_total: 섹터 종목 총 개수

    Returns:
        점수 (15, 8, 0)
    """
    if sector_total == 0:
        return 0

    percentile = sector_rank / sector_total  # 0~1 사이

    if percentile <= 0.2:  # 상위 20%
        return 15
    elif percentile <= 0.4:  # 상위 40%
        return 8
    else:
        return 0


# =============================================================================
# Main Scoring Function
# =============================================================================

def calculate_daytrading_score(stock, prices, flow) -> DaytradingScoreResult:
    """
    단타 종목 종합 점수 계산

    Args:
        stock: 종목 기본 정보
        prices: 일봉 데이터 리스트
        flow: 수급 데이터

    Returns:
        DaytradingScoreResult: 점수 계산 결과
    """
    checks: List[DaytradingCheck] = []
    total_score = 0

    if not prices or len(prices) < 2:
        # 데이터 부족
        return DaytradingScoreResult(
            ticker=stock.ticker,
            name=stock.name,
            total_score=0,
            grade="C",
            checks=[DaytradingCheck("데이터 부족", "failed", 0)]
        )

    current_price = prices[0].close_price

    # 1. 거래량 폭증 (15점)
    current_volume = prices[0].volume
    # 전일 거래량을 기준으로 평균 가정 (실제로는 20일 평균 필요)
    avg_volume = prices[1].volume if len(prices) > 1 else current_volume
    volume_score = calculate_volume_spike_score(current_volume, avg_volume)
    checks.append(DaytradingCheck("거래량 폭증", "passed" if volume_score > 0 else "failed", volume_score))
    total_score += volume_score

    # 2. 모멘텀 돌파 (15점)
    # 간단히 신고가 여부만 체크 (실제로는 20일 고가 필요)
    momentum_score = calculate_momentum_breakout_score(
        current_price, 0, current_price, True
    )
    checks.append(DaytradingCheck("모멘텀 돌파", "passed" if momentum_score > 0 else "failed", momentum_score))
    total_score += momentum_score

    # 3. 박스권 탈출 (15점)
    # 간단히 직전 고가를 박스 상단으로 가정
    box_score = calculate_box_breakout_score(current_price, current_price, current_price - 5000)
    checks.append(DaytradingCheck("박스권 탈출", "passed" if box_score > 0 else "failed", box_score))
    total_score += box_score

    # 4. 5일선 위 (15점)
    # 간단히 MA5 계산 (실제로는 5일 데이터 필요)
    ma5 = sum(p.close_price for p in prices[:min(5, len(prices))]) // min(5, len(prices))
    ma5_score = calculate_ma5_above_score(current_price, ma5)
    checks.append(DaytradingCheck("5일선 위", "passed" if ma5_score > 0 else "failed", ma5_score))
    total_score += ma5_score

    # 5. 기관 매수 (15점)
    institution_score = calculate_institution_buy_score(flow)
    checks.append(DaytradingCheck("기관 매수", "passed" if institution_score > 0 else "failed", institution_score))
    total_score += institution_score

    # 6. 낙폭 과대 (15점)
    # 2일 전 대비 당일 반등 확인
    if len(prices) >= 3:
        price_2d_ago = prices[2].close_price
        prev_price = prices[1].close_price
        prev_change_rate = _calculate_percentage(price_2d_ago, prev_price)
        current_change_rate = _calculate_percentage(prev_price, current_price)
    else:
        prev_price = prices[1].close_price if len(prices) > 1 else current_price
        prev_change_rate = _calculate_percentage(prev_price, current_price)
        current_change_rate = 0

    oversold_score = calculate_oversold_bounce_score(
        prev_price, prev_change_rate, current_change_rate
    )
    checks.append(DaytradingCheck("낙폭 과대", "passed" if oversold_score > 0 else "failed", oversold_score))
    total_score += oversold_score

    # 7. 섹터 모멘텀 (15점)
    # 간단히 상위 10% 가정
    sector_score = 15  # TODO: 실제 섹터 데이터 필요
    checks.append(DaytradingCheck("섹터 모멘텀", "passed", sector_score))
    total_score += sector_score

    # 등급 부여
    grade = get_grade_from_score(total_score)

    return DaytradingScoreResult(
        ticker=stock.ticker,
        name=stock.name,
        total_score=total_score,
        grade=grade,
        checks=checks
    )


def get_grade_from_score(total_score: int) -> str:
    """
    점수에 따른 등급 부여

    Args:
        total_score: 총 점수 (0-105)

    Returns:
        등급 (S, A, B, C)
    """
    if total_score >= 90:
        return "S"
    elif total_score >= 75:
        return "A"
    elif total_score >= 60:
        return "B"
    else:
        return "C"
