"""
SmartMoney 수급 분석 테스트
"""

import pytest
from datetime import date, timedelta
from src.analysis.smartmoney_analyzer import (
    FlowData,
    Trend,
    calculate_trend,
    calculate_foreign_score,
    calculate_inst_score,
    calculate_pension_score,
    calculate_ownership_score,
    analyze_smartmoney,
    create_mock_flow_data,
)


class TestCalculateTrend:
    """수급 추향 계산 테스트"""

    def test_strong_buy_trend(self):
        """강한 순매수 추세 테스트"""
        values = [100, 150, 200, 180, 220]  # 5일 연속 순매수

        trend, avg = calculate_trend(values, period=5)

        assert trend == Trend.STRONG_BUY
        assert avg > 0

    def test_strong_sell_trend(self):
        """강한 순매도 추세 테스트"""
        values = [-100, -150, -200, -180, -220]  # 5일 연속 순매도

        trend, avg = calculate_trend(values, period=5)

        assert trend == Trend.STRONG_SELL
        assert avg < 0

    def test_buy_trend(self):
        """순매수 추세 테스트"""
        values = [100, -50, 80, 120, 60]  # 전체 양수, 연속 아님

        trend, avg = calculate_trend(values, period=5)

        assert trend == Trend.BUY
        assert avg > 0

    def test_sell_trend(self):
        """순매도 추세 테스트"""
        values = [-100, 50, -80, -120, -60]  # 전체 음수

        trend, avg = calculate_trend(values, period=5)

        assert trend == Trend.SELL
        assert avg < 0

    def test_neutral_trend(self):
        """중립 추세 테스트"""
        values = [0, 0, 0, 0, 0]  # 모두 0

        trend, avg = calculate_trend(values, period=5)

        assert trend == Trend.NEUTRAL
        assert avg == 0

    def test_insufficient_data(self):
        """데이터 부족 시 테스트"""
        values = [100, 50]  # 2일 데이터

        trend, avg = calculate_trend(values, period=5)

        assert trend == Trend.NEUTRAL
        assert avg == 0.0


class TestForeignScore:
    """외국인 점수 계산 테스트"""

    def test_strong_buy_high_score(self):
        """강한 순매수 높은 점수"""
        score = calculate_foreign_score(
            Trend.STRONG_BUY,
            avg_value=150_000_000_000,  # 150억
            ownership=30.0,
        )

        assert score >= 35  # 최대 40점

    def test_strong_sell_low_score(self):
        """강한 순매도 낮은 점수"""
        score = calculate_foreign_score(
            Trend.STRONG_SELL,
            avg_value=-150_000_000_000,
            ownership=30.0,  # 지분율 30% = 12점(15점 만점) = 8점(10점 만점)
        )

        # STRONG_SELL(0점) + 순매도 0점 + 지분율 8점 = 8점
        assert score <= 20  # 추향 점수 없음

    def test_ownership_bonus(self):
        """지분율 가산점 테스트"""
        score_high = calculate_foreign_score(Trend.BUY, 50_000_000_000, 50.0)
        score_low = calculate_foreign_score(Trend.BUY, 50_000_000_000, 5.0)

        assert score_high > score_low

    def test_max_score(self):
        """최대 점수 제한 테스트"""
        # 최대 조건: STRONG_BUY + 100억+ 순매수
        score = calculate_foreign_score(
            Trend.STRONG_BUY,
            avg_value=200_000_000_000,
            ownership=60.0,
        )

        assert score <= 40.0


class TestInstScore:
    """기관 점수 계산 테스트"""

    def test_strong_buy_high_score(self):
        """강한 순매수 높은 점수"""
        score = calculate_inst_score(Trend.STRONG_BUY, 100_000_000_000)

        assert score >= 25  # 최대 30점

    def test_neutral_medium_score(self):
        """중립 중간 점수"""
        score = calculate_inst_score(Trend.NEUTRAL, 0)

        assert score >= 5  # 최소 추향 점수

    def test_max_score(self):
        """최대 점수 제한"""
        score = calculate_inst_score(Trend.STRONG_BUY, 200_000_000_000)

        assert score <= 30.0


class TestPensionScore:
    """연기금 점수 계산 테스트"""

    def test_buy_score(self):
        """순매수 점수"""
        score = calculate_pension_score(Trend.BUY, 30_000_000_000)

        assert score > 5

    def test_sell_score(self):
        """순매도 낮은 점수"""
        score = calculate_pension_score(Trend.SELL, -30_000_000_000)

        assert score < 5

    def test_max_score(self):
        """최대 점수 제한"""
        score = calculate_pension_score(Trend.STRONG_BUY, 100_000_000_000)

        assert score <= 15.0


class TestOwnershipScore:
    """지분율 점수 계산 테스트"""

    def test_high_ownership(self):
        """높은 지분율 높은 점수"""
        score = calculate_ownership_score(60.0)

        assert score == 15.0

    def test_medium_ownership(self):
        """중간 지분율"""
        score = calculate_ownership_score(25.0)

        assert score == 10.0

    def test_low_ownership(self):
        """낮은 지분율 낮은 점수"""
        score = calculate_ownership_score(3.0)

        assert score == 0.0

    def test_threshold_5_percent(self):
        """5% 임계값 테스트"""
        score_4 = calculate_ownership_score(4.9)
        score_5 = calculate_ownership_score(5.0)

        assert score_4 < score_5


class TestAnalyzeSmartMoney:
    """SmartMoney 분석 통합 테스트"""

    def test_buy_signals(self):
        """순매수 시그널 테스트"""
        flow_data = create_mock_flow_data(days=10, foreign_trend="buy", inst_trend="buy")

        result = analyze_smartmoney("005930", flow_data, period=5)

        assert result.ticker == "005930"
        assert result.foreign_trend in [Trend.BUY, Trend.STRONG_BUY]
        assert result.inst_trend in [Trend.BUY, Trend.STRONG_BUY]
        assert "외국인 순매수" in result.signals
        assert "기관 순매수" in result.signals
        assert result.total_score > 0

    def test_sell_signals(self):
        """순매도 시그널 테스트"""
        flow_data = create_mock_flow_data(days=10, foreign_trend="sell", inst_trend="sell")

        result = analyze_smartmoney("005930", flow_data, period=5)

        assert result.foreign_trend in [Trend.SELL, Trend.STRONG_SELL]
        assert result.inst_trend in [Trend.SELL, Trend.STRONG_SELL]
        assert result.total_score < 50  # 낮은 점수

    def test_smartmoney_strong_signal(self):
        """SmartMoney 강세 시그널 테스트"""
        # 강한 순매수 데이터
        flow_data = []
        today = date.today()

        for i in range(10):
            flow_data.append(FlowData(
                date=today - timedelta(days=i),
                foreign_net_buy=150_000_000_000,  # 150억 순매수
                inst_net_buy=100_000_000_000,  # 100억 순매수
                pension_net_buy=50_000_000_000,  # 50억 순매수
                foreign_ownership=40.0,  # 높은 지분율
            ))

        result = analyze_smartmoney("005930", flow_data, period=5)

        assert result.total_score >= 60
        assert "SmartMoney 강세" in result.signals

    def test_empty_data(self):
        """데이터 없을 때 테스트"""
        result = analyze_smartmoney("005930", [], period=5)

        assert result.total_score == 0
        assert result.foreign_trend == Trend.NEUTRAL
        assert result.inst_trend == Trend.NEUTRAL
        assert result.signals == []

    def test_result_dict_conversion(self):
        """결과 딕셔너리 변환 테스트"""
        flow_data = create_mock_flow_data(days=10)
        result = analyze_smartmoney("005930", flow_data, period=5)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["ticker"] == "005930"
        assert "foreign_trend" in result_dict
        assert "total_score" in result_dict
        assert "signals" in result_dict


class TestCreateMockFlowData:
    """목업 데이터 생성 테스트"""

    def test_create_mock_data(self):
        """목업 데이터 생성 테스트"""
        data = create_mock_flow_data(days=5, foreign_trend="buy")

        assert len(data) == 5
        assert all(isinstance(d, FlowData) for d in data)

    def test_foreign_buy_trend(self):
        """외국인 순매수 추세 목업"""
        data = create_mock_flow_data(days=10, foreign_trend="buy")

        # 최근 5일 평균이 양수여야 함
        recent_avg = sum(d.foreign_net_buy for d in data[:5]) / 5
        assert recent_avg > 0

    def test_foreign_sell_trend(self):
        """외국인 순매도 추세 목업"""
        data = create_mock_flow_data(days=10, foreign_trend="sell")

        # 최근 5일 평균이 음수여야 함
        recent_avg = sum(d.foreign_net_buy for d in data[:5]) / 5
        assert recent_avg < 0

    def test_ownership_range(self):
        """지분율 범위 테스트"""
        data = create_mock_flow_data(days=20)

        # 모든 지분율이 20% ~ 30% 사이
        for d in data:
            assert 20 <= d.foreign_ownership <= 30
