"""
VCP 분석 개선 모듈 테스트
"""

import numpy as np
from src.analysis.vcp_analyzer_improved import (
    calculate_bollinger_bands,
    calculate_contraction_ratio,
    calculate_volume_ratio,
    calculate_rsi,
    calculate_vcp_score,
    analyze_vcp_pattern,
)


class TestBollingerBands:
    """볼린저밴드 계산 테스트"""

    def test_calculate_bollinger_bands(self):
        """볼린저밴드 계산 테스트"""
        # 테스트 데이터 (30일)
        prices = [70000 + i * 100 + (i % 5) * 200 for i in range(30)]

        upper, middle, lower = calculate_bollinger_bands(prices, period=20, std_dev=2.0)

        assert upper is not None
        assert middle is not None
        assert lower is not None
        assert len(upper) == 11  # 30 - 20 + 1
        assert len(middle) == 11
        assert len(lower) == 11

        # 상단 > 중간 > 하단
        assert upper[-1] > middle[-1]
        assert middle[-1] > lower[-1]

    def test_insufficient_data(self):
        """데이터 부족 시 테스트"""
        prices = [70000, 70100, 70200]  # 3일 데이터 (20일 필요)

        upper, middle, lower = calculate_bollinger_bands(prices, period=20)

        assert upper is None
        assert middle is None
        assert lower is None

    def test_bollinger_bandwidth(self):
        """볼린저밴드 폭 테스트"""
        # 일정한 가격 (변동성 없음)
        prices = [70000] * 30

        upper, middle, lower = calculate_bollinger_bands(prices, period=20)

        # 변동성이 없으면 밴드폭이 0
        assert upper is not None
        assert lower is not None
        assert np.isclose(upper[-1], lower[-1], atol=1)


class TestContractionRatio:
    """수축률 계산 테스트"""

    def test_calculate_contraction_ratio(self):
        """수축률 계산 테스트"""
        # 과거 데이터 (넓은 밴드)
        historical_bands = [(80000, 60000)] * 20

        # 현재 데이터 (좁은 밴드)
        current_upper = 75000
        current_lower = 65000

        ratio = calculate_contraction_ratio(
            current_upper,
            current_lower,
            historical_bands,
            period=20,
        )

        # 수축률 = 10000 / 20000 = 0.5
        assert ratio == 0.5

    def test_contraction_narrowing(self):
        """밴드폭 수축 테스트"""
        historical_bands = [(80000, 60000)] * 20

        # 매우 좁은 밴드
        ratio = calculate_contraction_ratio(
            71000, 69000, historical_bands, 20
        )

        # 수축률 = 2000 / 20000 = 0.1
        assert ratio == 0.1

    def test_empty_historical(self):
        """과거 데이터 없을 때 테스트"""
        ratio = calculate_contraction_ratio(75000, 65000, [], 20)

        assert ratio == 0.5


class TestVolumeRatio:
    """거래량 비율 계산 테스트"""

    def test_volume_decrease(self):
        """거래량 감소 테스트"""
        # 최근 5일: 감소
        # 기간 6-25일: 정상
        volumes = [100000] * 5 + [200000] * 15

        ratio = calculate_volume_ratio(volumes, recent_period=5, baseline_period=20)

        # 100000 / 200000 = 0.5
        assert ratio == 0.5

    def test_volume_increase(self):
        """거래량 증가 테스트"""
        volumes = [300000] * 5 + [200000] * 15

        ratio = calculate_volume_ratio(volumes, recent_period=5, baseline_period=20)

        # 300000 / 200000 = 1.5
        assert ratio == 1.5

    def test_insufficient_data(self):
        """데이터 부족 시 테스트"""
        volumes = [100000, 150000, 200000]  # 3일 데이터

        ratio = calculate_volume_ratio(volumes, recent_period=5, baseline_period=20)

        # 데이터 부족 시 1.0 반환
        assert ratio == 1.0


class TestRSI:
    """RSI 계산 테스트"""

    def test_calculate_rsi(self):
        """RSI 계산 테스트"""
        # 상승 추세 (최신 순: 최신이 높음)
        # 최신 5일: 72000~71900, 이전: 70100~70000
        prices = [72000 - i * 100 for i in range(20)]

        rsi = calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 0 <= rsi <= 100
        # 상승 추세면 RSI가 높음
        assert rsi > 50

    def test_rsi_downtrend(self):
        """하락 추세 RSI 테스트"""
        # 하락 추세 (최신 순: 최신이 낮음)
        # 최신 5일: 70000~70100, 이전: 71900~72000
        prices = [70000 + i * 100 for i in range(20)]

        rsi = calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 0 <= rsi <= 100
        # 하락 추세면 RSI가 낮음
        assert rsi < 50

    def test_insufficient_data(self):
        """데이터 부족 시 RSI 테스트"""
        prices = [70000, 70100, 70200]  # 3일 데이터

        rsi = calculate_rsi(prices, period=14)

        assert rsi is None


class TestVCPScore:
    """VCP 점수 계산 테스트"""

    def test_calculate_vcp_score(self):
        """VCP 점수 계산 테스트"""
        # VCP 패턴 데이터 (수축 + 거래량 감소)
        prices = [75000 + (i % 10) * 50 for i in range(30)]  # 횡보장
        volumes = [100000] * 5 + [200000] * 15 + [300000] * 10  # 거래량 감소

        scores = calculate_vcp_score(prices, volumes)

        assert scores["total_score"] >= 0
        assert scores["total_score"] <= 100
        assert scores["bb_contraction"] >= 0
        assert scores["volume_decrease"] >= 0

    def test_vcp_score_breakdown(self):
        """VCP 점수 상세 분석 테스트"""
        # 최소 데이터
        prices = [70000 + i * 10 for i in range(25)]
        volumes = [100000] * 25

        scores = calculate_vcp_score(prices, volumes)

        # 모든 항목 점수 확인
        assert "bb_contraction" in scores
        assert "volume_decrease" in scores
        assert "volatility_decrease" in scores
        assert "rsi_neutral" in scores
        assert "price_position" in scores
        assert "total_score" in scores

    def test_insufficient_data(self):
        """데이터 부족 시 VCP 점수 테스트"""
        prices = [70000, 70100, 70200]  # 3일 데이터
        volumes = [100000, 150000, 200000]

        scores = calculate_vcp_score(prices, volumes)

        # 데이터 부족 시 모든 점수 0
        assert scores["total_score"] == 0


class TestVCPAnalyze:
    """VCP 패턴 분석 테스트"""

    def test_analyze_vcp_pattern(self):
        """VCP 패턴 분석 테스트"""
        # 강한 VCP 패턴
        prices = [75000] * 30  # 완전 횡보
        volumes = [100000] * 10 + [200000] * 20  # 거래량 감소

        result = analyze_vcp_pattern(prices, volumes, threshold=50)

        assert "vcp_score" in result
        assert "pattern_detected" in result
        assert "signals" in result
        assert "details" in result
        assert isinstance(result["signals"], list)

    def test_pattern_detected(self):
        """VCP 패턴 감지 테스트"""
        # 수축 패턴
        prices = [70000 + (i % 5) * 10 for i in range(30)]
        volumes = [50000] * 5 + [200000] * 25

        result = analyze_vcp_pattern(prices, volumes, threshold=30)

        # 낮은 임계값이면 패턴 감지
        if result["vcp_score"] >= 30:
            assert result["pattern_detected"] is True

    def test_pattern_not_detected(self):
        """VCP 패턴 미감지 테스트"""
        # 명확한 추세 (패턴 아님)
        prices = [70000 + i * 500 for i in range(30)]  # 강한 상승
        volumes = [200000] * 10 + [300000] * 20  # 거래량 증가

        result = analyze_vcp_pattern(prices, volumes, threshold=70)

        # 높은 임계값이면 패턴 미감지
        if result["vcp_score"] < 70:
            assert result["pattern_detected"] is False
