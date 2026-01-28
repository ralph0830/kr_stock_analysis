"""
VCP 분석 개선 모듈
실제 차트 데이터 기반 볼린저밴드 및 VCP 패턴 분석
"""

import logging
from typing import Optional, List, Tuple
from datetime import date, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class VCPAnalyzer:
    """
    VCP 패턴 분석기

    DailyPriceRepository를 사용하여 VCP 패턴을 분석하고
    52주 고가 근접 여부를 판단합니다.
    """

    def __init__(self, daily_price_repo=None):
        """
        VCPAnalyzer 초기화

        Args:
            daily_price_repo: DailyPriceRepository 인스턴스 (선택사항)
        """
        self._daily_price_repo = daily_price_repo

    def detect_vcp_pattern(self, ticker: str, threshold: float = 60.0) -> bool:
        """
        VCP 패턴 감지

        Args:
            ticker: 종목코드
            threshold: VCP 점수 임계값 (기본 60점)

        Returns:
            VCP 패턴 감지 여부
        """
        try:
            # Repository가 없으면 기존 함수 사용 (Mock 데이터)
            if self._daily_price_repo is None:
                logger.warning(f"{ticker} Repository 없음, VCP 패턴 미감지")
                return False

            # 최근 60일 데이터 조회
            end_date = date.today()
            start_date = end_date - timedelta(days=90)

            prices = self._daily_price_repo.get_by_ticker_and_date_range(
                ticker, start_date, end_date
            )

            if len(prices) < 20:
                return False

            # 가격 및 거래량 리스트 추출
            price_list = [p.close_price for p in prices]
            volume_list = [p.volume for p in prices]

            # VCP 점수 계산
            scores = calculate_vcp_score(price_list, volume_list)
            return scores["total_score"] >= threshold

        except Exception as e:
            logger.error(f"{ticker} VCP 패턴 감지 실패: {e}")
            return False

    def is_near_52w_high(self, ticker: str, threshold: float = 0.95) -> bool:
        """
        52주 고가 근접 여부 확인

        Args:
            ticker: 종목코드
            threshold: 근접 기준 (기본 95%)

        Returns:
            52주 고가 근접 여부
        """
        try:
            if self._daily_price_repo is None:
                logger.warning(f"{ticker} Repository 없음, 52주 고가 확인 불가")
                return False

            # 최근 365일 데이터 조회
            end_date = date.today()
            start_date = end_date - timedelta(days=400)

            prices = self._daily_price_repo.get_by_ticker_and_date_range(
                ticker, start_date, end_date
            )

            if not prices:
                return False

            # 52주 고가 찾기
            max_high = max(p.high_price for p in prices)
            current_price = prices[-1].close_price

            return current_price >= (max_high * threshold)

        except Exception as e:
            logger.error(f"{ticker} 52주 고가 확인 실패: {e}")
            return False


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    볼린저밴드 계산

    Args:
        prices: 가격 리스트 (최신 순)
        period: 이동평균 기간 (기본 20일)
        std_dev: 표준편차 배수 (기본 2)

    Returns:
        (상단 밴드, 중간 밴드, 하단 밴드) 튜플
    """
    if len(prices) < period:
        logger.warning(f"가격 데이터 부족 (필요: {period}일, 실제: {len(prices)}일)")
        return None, None, None

    # 최신 데이터가 뒤에 오도록 정렬
    prices_array = np.array(prices[::-1])

    # 이동평균 (SMA)
    sma = np.convolve(prices_array, np.ones(period) / period, mode='valid')

    # 표준편차
    # rolling standard deviation 계산
    std = []
    for i in range(len(prices_array) - period + 1):
        window = prices_array[i:i + period]
        std.append(np.std(window))
    std = np.array(std)

    # 볼린저밴드
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)

    return upper_band, sma, lower_band


def calculate_contraction_ratio(
    upper_band: float,
    lower_band: float,
    historical_bands: List[Tuple[float, float]],
    period: int = 20,
) -> float:
    """
    밴드폭 수축률 계산

    Args:
        upper_band: 현재 상단 밴드
        lower_band: 현재 하단 밴드
        historical_bands: 과거 밴드 데이터 리스트 [(upper, lower), ...]
        period: 평균 계산 기간

    Returns:
        수축률 (0~1 사이 값, 작을수록 수축)
    """
    if not historical_bands:
        return 0.5

    # 현재 밴드폭
    current_bandwidth = upper_band - lower_band

    # 과거 밴드폭 계산
    historical_widths = [(upper - lower) for upper, lower in historical_bands[-period:]]
    avg_bandwidth = np.mean(historical_widths)

    if avg_bandwidth == 0:
        return 0.5

    # 수축률 (현재 / 과거 평균)
    contraction_ratio = current_bandwidth / avg_bandwidth

    return contraction_ratio


def calculate_volume_ratio(
    volumes: List[float],
    recent_period: int = 5,
    baseline_period: int = 20,
) -> float:
    """
    거래량 감소율 계산

    Args:
        volumes: 거래량 리스트 (최신 순)
        recent_period: 최근 기간 (기본 5일)
        baseline_period: 기준 기간 (기본 20일)

    Returns:
        거래량 비율 (최근/기준, 1 미만이면 감소)
    """
    if len(volumes) < baseline_period:
        logger.warning(f"거래량 데이터 부족 (필요: {baseline_period}일, 실제: {len(volumes)}일)")
        return 1.0

    # volumes는 이미 최신 순 (index 0이 최신)
    volumes_array = np.array(volumes)

    # 최근 거래량 평균 (index 0~recent_period-1)
    recent_avg = np.mean(volumes_array[:recent_period])

    # 기준 거래량 평균 (index recent_period~baseline_period-1)
    baseline_avg = np.mean(volumes_array[recent_period:baseline_period])

    if baseline_avg == 0:
        return 1.0

    # 거래량 비율
    volume_ratio = recent_avg / baseline_avg

    return volume_ratio


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    RSI (Relative Strength Index) 계산

    Args:
        prices: 가격 리스트 (최신 순)
        period: RSI 기간 (기본 14)

    Returns:
        RSI 값 (0~100) 또는 None (데이터 부족)
    """
    if len(prices) < period + 1:
        return None

    # prices는 최신 순 (index 0이 최신)
    # RSI 계산을 위해 오래된 순으로 정렬
    prices_array = np.array(prices[::-1])

    # 가격 변화 계산
    deltas = np.diff(prices_array)

    # 상승/하락 분리
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # 평균 상승/하락 (Wilder 방식: 단순 이동평균)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        return 100.0

    # RS 계산
    rs = avg_gain / avg_loss

    # RSI 계산
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_vcp_score(
    prices: List[float],
    volumes: List[float],
    bb_period: int = 20,
    bb_std: float = 2.0,
) -> dict:
    """
    VCP 점수 계산 (실제 데이터 기반)

    Args:
        prices: 가격 리스트 (최신 순)
        volumes: 거래량 리스트 (최신 순)
        bb_period: 볼린저밴드 기간
        bb_std: 볼린저밴드 표준편차

    Returns:
        점수 상세 딕셔너리
    """
    scores = {
        "total_score": 0.0,
        "bb_contraction": 0.0,  # 볼린저밴드 수축 (30%)
        "volume_decrease": 0.0,  # 거래량 감소 (20%)
        "volatility_decrease": 0.0,  # 변동성 감소 (20%)
        "rsi_neutral": 0.0,  # RSI 중립 (15%)
        "price_position": 0.0,  # 가격 위치 (15%)
    }

    if len(prices) < bb_period:
        logger.warning(f"VCP 분석 데이터 부족 (필요: {bb_period}일, 실제: {len(prices)}일)")
        return scores

    # 1. 볼린저밴드 계산
    upper_band, middle_band, lower_band = calculate_bollinger_bands(
        prices, bb_period, bb_std
    )

    if upper_band is None:
        return scores

    # 현재 가격
    current_price = prices[0]

    # 볼린저밴드 수축률
    historical_bands = list(zip(upper_band[:-1], lower_band[:-1]))
    contraction_ratio = calculate_contraction_ratio(
        upper_band[-1],
        lower_band[-1],
        historical_bands,
        bb_period,
    )

    # 수축 점수 (수축률이 낮을수록 높은 점수)
    # 0.5 미만: 30점 만점
    # 0.5-0.7: 20점
    # 0.7-0.9: 10점
    # 0.9 이상: 0점
    if contraction_ratio < 0.5:
        bb_score = 30.0
    elif contraction_ratio < 0.7:
        bb_score = 20.0
    elif contraction_ratio < 0.9:
        bb_score = 10.0
    else:
        bb_score = 0.0

    scores["bb_contraction"] = bb_score

    # 2. 거래량 감소 점수
    volume_ratio = calculate_volume_ratio(volumes, recent_period=5, baseline_period=20)

    # 거래량 비율이 낮을수록 높은 점수 (감소했을 때)
    # 0.5 미만: 20점 만점
    # 0.5-0.7: 15점
    # 0.7-0.9: 10점
    # 0.9 이상: 5점
    # 1.1 이상 (증가): 0점
    if volume_ratio < 0.5:
        vol_score = 20.0
    elif volume_ratio < 0.7:
        vol_score = 15.0
    elif volume_ratio < 0.9:
        vol_score = 10.0
    elif volume_ratio < 1.1:
        vol_score = 5.0
    else:
        vol_score = 0.0

    scores["volume_decrease"] = vol_score

    # 3. 변동성 감소 점수 (표준편차 기반)
    recent_volatility = np.std(prices[:5]) / np.mean(prices[:5]) if np.mean(prices[:5]) > 0 else 0
    baseline_volatility = np.std(prices[5:25]) / np.mean(prices[5:25]) if np.mean(prices[5:25]) > 0 else 0

    if baseline_volatility > 0:
        vol_change = recent_volatility / baseline_volatility
        # 변동성이 감소했을 때 높은 점수
        if vol_change < 0.5:
            vol_decrease_score = 20.0
        elif vol_change < 0.8:
            vol_decrease_score = 15.0
        elif vol_change < 1.0:
            vol_decrease_score = 10.0
        else:
            vol_decrease_score = 0.0
    else:
        vol_decrease_score = 0.0

    scores["volatility_decrease"] = vol_decrease_score

    # 4. RSI 중립 점수
    rsi = calculate_rsi(prices, period=14)

    if rsi is not None:
        # RSI가 40~60 사이일 때 높은 점수 (중립)
        if 40 <= rsi <= 60:
            rsi_score = 15.0
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            rsi_score = 10.0
        elif 20 <= rsi < 30 or 70 < rsi <= 80:
            rsi_score = 5.0
        else:
            rsi_score = 0.0
    else:
        rsi_score = 0.0

    scores["rsi_neutral"] = rsi_score

    # 5. 가격 위치 점수 (볼린저밴드 내 위치)
    current_upper = upper_band[-1]
    current_lower = lower_band[-1]
    band_width = current_upper - current_lower

    if band_width > 0:
        price_position = (current_price - current_lower) / band_width

        # 중간에 위치할 때 높은 점수 (0.4~0.6)
        if 0.4 <= price_position <= 0.6:
            pos_score = 15.0
        elif 0.3 <= price_position < 0.4 or 0.6 < price_position <= 0.7:
            pos_score = 10.0
        elif 0.2 <= price_position < 0.3 or 0.7 < price_position <= 0.8:
            pos_score = 5.0
        else:
            pos_score = 0.0
    else:
        pos_score = 0.0

    scores["price_position"] = pos_score

    # 총점 계산
    scores["total_score"] = (
        scores["bb_contraction"] +
        scores["volume_decrease"] +
        scores["volatility_decrease"] +
        scores["rsi_neutral"] +
        scores["price_position"]
    )

    return scores


def analyze_vcp_pattern(
    prices: List[float],
    volumes: List[float],
    threshold: float = 60.0,
) -> dict:
    """
    VCP 패턴 분석

    Args:
        prices: 가격 리스트 (최신 순)
        volumes: 거래량 리스트 (최신 순)
        threshold: VCP 패턴 감지 임계값 (기본 60점)

    Returns:
        분석 결과 딕셔너리
    """
    scores = calculate_vcp_score(prices, volumes)
    pattern_detected = scores["total_score"] >= threshold

    signals = []
    if scores["bb_contraction"] >= 20:
        signals.append("볼린저밴드 수축")
    if scores["volume_decrease"] >= 15:
        signals.append("거래량 감소")
    if scores["volatility_decrease"] >= 15:
        signals.append("변동성 감소")
    if scores["rsi_neutral"] >= 10:
        signals.append("RSI 중립 구간")

    return {
        "vcp_score": scores["total_score"],
        "pattern_detected": pattern_detected,
        "signals": signals,
        "details": scores,
    }
