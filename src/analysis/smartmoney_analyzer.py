"""
SmartMoney 수급 분석 모듈
외국인/기관 수급 데이터 기반 SmartMoney 점수 계산
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class Trend(Enum):
    """수급 추향"""
    STRONG_BUY = "strong_buy"  # 강한 순매수
    BUY = "buy"  # 순매수
    NEUTRAL = "neutral"  # 중립
    SELL = "sell"  # 순매도
    STRONG_SELL = "strong_sell"  # 강한 순매도


@dataclass
class FlowData:
    """수급 데이터"""
    date: date
    foreign_net_buy: int  # 외국인 순매수 (원)
    inst_net_buy: int  # 기관 순매수 (원)
    pension_net_buy: int  # 연기금 순매수 (원)
    foreign_ownership: float  # 외국인 지분율 (%)


@dataclass
class SmartMoneyResult:
    """SmartMoney 분석 결과"""
    ticker: str
    analysis_date: date
    foreign_trend: Trend
    inst_trend: Trend
    pension_trend: Trend
    foreign_score: float  # 외국인 점수 (0-40)
    inst_score: float  # 기관 점수 (0-30)
    pension_score: float  # 연기금 점수 (0-15)
    ownership_score: float  # 외국인 지분율 점수 (0-15)
    total_score: float  # 총점 (0-100)
    signals: List[str]

    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "analysis_date": self.analysis_date.isoformat(),
            "foreign_trend": self.foreign_trend.value,
            "inst_trend": self.inst_trend.value,
            "pension_trend": self.pension_trend.value,
            "foreign_score": self.foreign_score,
            "inst_score": self.inst_score,
            "pension_score": self.pension_score,
            "ownership_score": self.ownership_score,
            "total_score": self.total_score,
            "signals": self.signals,
        }


def calculate_trend(
    values: List[int],
    period: int = 5,
) -> Tuple[Trend, float]:
    """
    수급 추향 계산

    Args:
        values: 순매수 데이터 리스트 (최신 순)
        period: 분석 기간 (기본 5일)

    Returns:
        (추향, 평균 순매수) 튜플
    """
    if len(values) < period:
        return Trend.NEUTRAL, 0.0

    recent_values = values[:period]
    avg_value = np.mean(recent_values)

    # 연속 순매수/순매도 일수 계산
    consecutive_buy = 0
    consecutive_sell = 0

    for v in recent_values:
        if v > 0:
            consecutive_buy += 1
            consecutive_sell = 0
        elif v < 0:
            consecutive_sell += 1
            consecutive_buy = 0
        else:
            consecutive_buy = 0
            consecutive_sell = 0

    # 추향 판단
    if consecutive_buy >= period - 1:
        if avg_value > 0:
            return Trend.STRONG_BUY, avg_value
        return Trend.BUY, avg_value
    elif consecutive_sell >= period - 1:
        if avg_value < 0:
            return Trend.STRONG_SELL, avg_value
        return Trend.SELL, avg_value
    elif avg_value > 0:
        return Trend.BUY, avg_value
    elif avg_value < 0:
        return Trend.SELL, avg_value
    else:
        return Trend.NEUTRAL, 0.0


def calculate_foreign_score(
    trend: Trend,
    avg_value: float,
    ownership: float,
) -> float:
    """
    외국인 점수 계산 (0-40점)

    - 추향 (20점)
    - 순매수 규모 (10점)
    - 지분율 (10점)

    Args:
        trend: 외국인 수급 추향
        avg_value: 평균 순매수 (원)
        ownership: 외국인 지분율 (%)

    Returns:
        외국인 점수 (0-40)
    """
    score = 0.0

    # 1. 추향 점수 (20점)
    trend_scores = {
        Trend.STRONG_BUY: 20.0,
        Trend.BUY: 15.0,
        Trend.NEUTRAL: 10.0,
        Trend.SELL: 5.0,
        Trend.STRONG_SELL: 0.0,
    }
    score += trend_scores.get(trend, 10.0)

    # 2. 순매수 규모 점수 (10점)
    # 100억 이상 순매수: 10점
    # 50억 이상: 7점
    # 10억 이상: 5점
    # 양수: 3점
    # 음수: 0점
    abs_value = abs(avg_value)
    if abs_value >= 100_000_000_000:  # 100억 이상
        score += 10.0
    elif abs_value >= 50_000_000_000:  # 50억 이상
        score += 7.0
    elif abs_value >= 10_000_000_000:  # 10억 이상
        score += 5.0
    elif avg_value > 0:
        score += 3.0

    # 3. 지분율 점수 (10점)
    ownership_score = calculate_ownership_score(ownership) * (10.0 / 15.0)  # 15점 만점을 10점으로 환산
    score += ownership_score

    return min(score, 40.0)


def calculate_inst_score(
    trend: Trend,
    avg_value: float,
) -> float:
    """
    기관 점수 계산 (0-30점)

    - 추향 (15점)
    - 순매수 규모 (15점)

    Args:
        trend: 기관 수급 추향
        avg_value: 평균 순매수 (원)

    Returns:
        기관 점수 (0-30)
    """
    score = 0.0

    # 1. 추향 점수 (15점)
    trend_scores = {
        Trend.STRONG_BUY: 15.0,
        Trend.BUY: 12.0,
        Trend.NEUTRAL: 7.5,
        Trend.SELL: 3.0,
        Trend.STRONG_SELL: 0.0,
    }
    score += trend_scores.get(trend, 7.5)

    # 2. 순매수 규모 점수 (15점)
    # 100억 이상 순매수: 15점
    # 50억 이상: 10점
    # 10억 이상: 5점
    # 양수: 2점
    # 음수: 0점
    abs_value = abs(avg_value)
    if abs_value >= 100_000_000_000:  # 100억 이상
        score += 15.0
    elif abs_value >= 50_000_000_000:  # 50억 이상
        score += 10.0
    elif abs_value >= 10_000_000_000:  # 10억 이상
        score += 5.0
    elif avg_value > 0:
        score += 2.0

    return min(score, 30.0)


def calculate_pension_score(
    trend: Trend,
    avg_value: float,
) -> float:
    """
    연기금 점수 계산 (0-15점)

    - 추향 (8점)
    - 순매수 규모 (7점)

    Args:
        trend: 연기금 수급 추향
        avg_value: 평균 순매수 (원)

    Returns:
        연기금 점수 (0-15)
    """
    score = 0.0

    # 1. 추향 점수 (8점)
    trend_scores = {
        Trend.STRONG_BUY: 8.0,
        Trend.BUY: 6.0,
        Trend.NEUTRAL: 4.0,
        Trend.SELL: 2.0,
        Trend.STRONG_SELL: 0.0,
    }
    score += trend_scores.get(trend, 4.0)

    # 2. 순매수 규모 점수 (7점)
    # 50억 이상 순매수: 7점
    # 20억 이상: 5점
    # 5억 이상: 3점
    # 양수: 1점
    # 음수: 0점
    abs_value = abs(avg_value)
    if avg_value > 0:  # 순매수만 점수 부여
        if abs_value >= 50_000_000_000:  # 50억 이상
            score += 7.0
        elif abs_value >= 20_000_000_000:  # 20억 이상
            score += 5.0
        elif abs_value >= 5_000_000_000:  # 5억 이상
            score += 3.0
        else:
            score += 1.0

    return min(score, 15.0)


def calculate_ownership_score(ownership: float) -> float:
    """
    외국인 지분율 점수 계산 (0-15점)

    - 50% 이상: 15점
    - 30% 이상: 12점
    - 20% 이상: 10점
    - 10% 이상: 7점
    - 5% 이상: 5점
    - 5% 미만: 0점

    Args:
        ownership: 외국인 지분율 (%)

    Returns:
        지분율 점수 (0-15)
    """
    if ownership >= 50:
        return 15.0
    elif ownership >= 30:
        return 12.0
    elif ownership >= 20:
        return 10.0
    elif ownership >= 10:
        return 7.0
    elif ownership >= 5:
        return 5.0
    else:
        return 0.0


def analyze_smartmoney(
    ticker: str,
    flow_data: List[FlowData],
    period: int = 5,
) -> SmartMoneyResult:
    """
    SmartMoney 수급 분석

    Args:
        ticker: 종목코드
        flow_data: 수급 데이터 리스트 (최신 순)
        period: 분석 기간 (기본 5일)

    Returns:
        SmartMoneyResult
    """
    if not flow_data:
        logger.warning(f"{ticker} 수급 데이터 없음")
        return SmartMoneyResult(
            ticker=ticker,
            analysis_date=date.today(),
            foreign_trend=Trend.NEUTRAL,
            inst_trend=Trend.NEUTRAL,
            pension_trend=Trend.NEUTRAL,
            foreign_score=0.0,
            inst_score=0.0,
            pension_score=0.0,
            ownership_score=0.0,
            total_score=0.0,
            signals=[],
        )

    # 데이터 추출
    foreign_values = [d.foreign_net_buy for d in flow_data]
    inst_values = [d.inst_net_buy for d in flow_data]
    pension_values = [d.pension_net_buy for d in flow_data]

    # 최신 지분율
    latest_ownership = flow_data[0].foreign_ownership

    # 추향 계산
    foreign_trend, foreign_avg = calculate_trend(foreign_values, period)
    inst_trend, inst_avg = calculate_trend(inst_values, period)
    pension_trend, pension_avg = calculate_trend(pension_values, period)

    # 점수 계산
    foreign_score = calculate_foreign_score(foreign_trend, foreign_avg, latest_ownership)
    inst_score = calculate_inst_score(inst_trend, inst_avg)
    pension_score = calculate_pension_score(pension_trend, pension_avg)
    ownership_score = calculate_ownership_score(latest_ownership)

    # 총점 계산
    total_score = foreign_score + inst_score + pension_score + ownership_score

    # 시그널 생성
    signals = []

    if foreign_trend in [Trend.BUY, Trend.STRONG_BUY]:
        signals.append("외국인 순매수")
    elif foreign_trend in [Trend.SELL, Trend.STRONG_SELL]:
        signals.append("외국인 순매도")

    if inst_trend in [Trend.BUY, Trend.STRONG_BUY]:
        signals.append("기관 순매수")
    elif inst_trend in [Trend.SELL, Trend.STRONG_SELL]:
        signals.append("기관 순매도")

    if pension_trend in [Trend.BUY, Trend.STRONG_BUY]:
        signals.append("연기금 순매수")

    if total_score >= 60:
        signals.append("SmartMoney 강세")

    return SmartMoneyResult(
        ticker=ticker,
        analysis_date=flow_data[0].date,
        foreign_trend=foreign_trend,
        inst_trend=inst_trend,
        pension_trend=pension_trend,
        foreign_score=foreign_score,
        inst_score=inst_score,
        pension_score=pension_score,
        ownership_score=ownership_score,
        total_score=total_score,
        signals=signals,
    )


def create_mock_flow_data(
    days: int = 20,
    foreign_trend: str = "buy",
    inst_trend: str = "neutral",
) -> List[FlowData]:
    """
    목업 수급 데이터 생성 (테스트용)

    Args:
        days: 데이터 일수
        foreign_trend: 외국인 추향 (buy/sell/neutral)
        inst_trend: 기관 추향 (buy/sell/neutral)

    Returns:
        FlowData 리스트
    """
    today = date.today()
    data = []

    base_foreign = 50_000_000_000 if foreign_trend == "buy" else -50_000_000_000
    base_inst = 30_000_000_000 if inst_trend == "buy" else -30_000_000_000

    for i in range(days):
        # 일자별 변동 추가
        foreign_noise = (i % 3 - 1) * 10_000_000_000
        inst_noise = (i % 5 - 2) * 5_000_000_000

        if foreign_trend == "neutral":
            foreign_value = (i % 2) * 20_000_000_000 + foreign_noise
        else:
            foreign_value = base_foreign + foreign_noise

        if inst_trend == "neutral":
            inst_value = (i % 2) * 10_000_000_000 + inst_noise
        else:
            inst_value = base_inst + inst_noise

        data.append(FlowData(
            date=today - timedelta(days=i),
            foreign_net_buy=int(foreign_value),
            inst_net_buy=int(inst_value),
            pension_net_buy=int(10_000_000_000 + (i % 3) * 5_000_000_000),
            foreign_ownership=25.0 + (i % 10) * 0.5,
        ))

    return data
