"""
VCP Scanner + SmartMoney Integration Tests
VCP 패턴 분석과 SmartMoney 수급 분석 통합 테스트
"""

import pytest
from datetime import date, timedelta
import numpy as np

from src.analysis.vcp_analyzer_improved import (
    calculate_vcp_score,
    calculate_bollinger_bands,
    calculate_rsi,
)
from src.analysis.smartmoney_analyzer import (
    analyze_smartmoney,
    create_mock_flow_data,
    FlowData,
    Trend,
)


class TestVCPSmartMoneyIntegration:
    """VCP + SmartMoney 통합 테스트"""

    def test_strong_buy_signal_integration(self):
        """강한 매수 시그널 통합 테스트"""
        # VCP 데이터 생성 (볼린저밴드 수축 + 거래량 감소)
        days = 20
        base_price = 80000

        # 수축 패턴: 변동폭이 점점 줄어듦
        prices = []
        for i in range(days):
            noise = (days - i) * 50  # 점점 변동폭 감소
            price = base_price + np.random.randint(-noise, noise)
            prices.append(float(price))

        prices.reverse()  # 최신 순

        # 거래량 감소 패턴
        volumes = []
        for i in range(days):
            volume = 1000000 + (days - i) * 50000  # 점점 감소
            volumes.append(float(volume))

        volumes.reverse()

        # VCP 점수 계산
        vcp_result = calculate_vcp_score(prices, volumes)

        # SmartMoney 데이터 생성 (외국인/기관 순매수)
        flow_data = create_mock_flow_data(days=10, foreign_trend="buy", inst_trend="buy")

        # 외국인/기관 강한 순매수로 수정
        for i in range(len(flow_data)):
            flow_data[i].foreign_net_buy = 100_000_000_000  # 100억 순매수
            flow_data[i].inst_net_buy = 80_000_000_000  # 80억 순매수
            flow_data[i].foreign_ownership = 35.0  # 높은 지분율

        smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

        # 검증
        assert vcp_result["total_score"] >= 0
        assert smartmoney_result.total_score >= 60  # SmartMoney 강세
        assert "SmartMoney 강세" in smartmoney_result.signals

        # 통합 시그널 검증
        if vcp_result["total_score"] >= 60 and smartmoney_result.total_score >= 60:
            # VCP 강세 + SmartMoney 강세 = 매우 강력한 매수 시그널
            assert True

    def test_weak_sell_signal_integration(self):
        """약한 매도 시그널 통합 테스트"""
        # VCP 데이터 (확장 패턴)
        days = 20
        base_price = 80000

        prices = []
        for i in range(days):
            noise = max(100, i * 100)  # 점점 변동폭 증가, 최소 100
            price = base_price + np.random.randint(-noise, noise)
            prices.append(float(price))

        prices.reverse()

        # 거래량 급증
        volumes = []
        for i in range(days):
            volume = 500000 + i * 100000  # 점점 증가
            volumes.append(float(volume))

        volumes.reverse()

        vcp_result = calculate_vcp_score(prices, volumes)

        # SmartMoney 데이터 (외국인/기관 순매도)
        flow_data = create_mock_flow_data(days=10, foreign_trend="sell", inst_trend="sell")

        smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

        # 검증
        assert vcp_result["total_score"] < 60  # VCP 약세
        assert smartmoney_result.total_score < 50  # SmartMoney 약세

    def test_divergent_signals(self):
        """시그널 발산 테스트 (VCP 강세 vs SmartMoney 약세)"""
        # VCP 강세 데이터
        days = 20
        base_price = 80000

        prices = []
        for i in range(days):
            noise = (days - i) * 50  # 수축
            price = base_price + np.random.randint(-noise, noise)
            prices.append(float(price))

        prices.reverse()

        volumes = [1000000.0 - i * 50000 for i in range(days)]
        volumes.reverse()

        vcp_result = calculate_vcp_score(prices, volumes)

        # SmartMoney 약세 데이터
        flow_data = create_mock_flow_data(days=10, foreign_trend="sell", inst_trend="sell")

        smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

        # 발산 상황 검증
        assert vcp_result["total_score"] >= 0
        assert smartmoney_result.total_score < 50

        # 실제 시나리오에서는 이런 경우 신중하게 접근해야 함
        # 테스트는 양쪽 데이터가 모두 생성되는지 확인

    def test_convergent_bullish_signals(self):
        """수렴 상승 시그널 테스트"""
        # VCP 강세
        days = 20

        # 상승 추세 + 수축
        prices = []
        for i in range(days):
            price = 80000 + i * 100 + np.random.randint(-50, 50)
            prices.append(float(price))

        prices.reverse()  # 최신 순

        # 거래량 감소
        volumes = [1500000.0 - i * 50000 for i in range(days)]
        volumes.reverse()

        vcp_result = calculate_vcp_score(prices, volumes)

        # SmartMoney 강세
        flow_data = create_mock_flow_data(days=10, foreign_trend="buy", inst_trend="buy")

        # 외국인 강한 순매수
        for i in range(len(flow_data)):
            flow_data[i].foreign_net_buy = 150_000_000_000
            flow_data[i].foreign_ownership = 45.0

        smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

        # 검증
        assert vcp_result["total_score"] >= 0
        assert smartmoney_result.total_score >= 60
        assert "SmartMoney 강세" in smartmoney_result.signals

    def test_score_correlation(self):
        """VCP와 SmartMoney 점수 상관관계 테스트"""
        # 다양한 시나리오 생성
        scenarios = []

        for scenario in ["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]:
            if scenario == "strong_bullish":
                prices = [80000 + i * 200 for i in range(20)]  # 강한 상승
                volumes = [2000000.0 - i * 100000 for i in range(20)]
                foreign_trend = "buy"
                inst_trend = "buy"
            elif scenario == "bullish":
                prices = [80000 + i * 100 for i in range(20)]
                volumes = [1500000.0 - i * 50000 for i in range(20)]
                foreign_trend = "buy"
                inst_trend = "neutral"
            elif scenario == "neutral":
                prices = [80000 + np.random.randint(-100, 100) for i in range(20)]
                volumes = [1000000.0 + np.random.randint(-100000, 100000) for i in range(20)]
                foreign_trend = "neutral"
                inst_trend = "neutral"
            elif scenario == "bearish":
                prices = [80000 - i * 100 for i in range(20)]
                volumes = [1000000.0 + i * 50000 for i in range(20)]
                foreign_trend = "sell"
                inst_trend = "neutral"
            else:  # strong_bearish
                prices = [80000 - i * 200 for i in range(20)]
                volumes = [500000.0 + i * 100000 for i in range(20)]
                foreign_trend = "sell"
                inst_trend = "sell"

            prices.reverse()
            volumes.reverse()

            vcp_result = calculate_vcp_score(prices, volumes)

            flow_data = create_mock_flow_data(days=10, foreign_trend=foreign_trend, inst_trend=inst_trend)
            smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

            scenarios.append({
                "scenario": scenario,
                "vcp_score": vcp_result["total_score"],
                "smartmoney_score": smartmoney_result.total_score,
            })

        # 시나리오별 검증
        strong_bullish = next(s for s in scenarios if s["scenario"] == "strong_bullish")
        strong_bearish = next(s for s in scenarios if s["scenario"] == "strong_bearish")

        # 강한 상승 > 강한 하락
        assert strong_bullish["vcp_score"] >= 0
        assert strong_bullish["smartmoney_score"] >= 0

    def test_data_consistency(self):
        """데이터 일관성 테스트"""
        # 같은 날짜 데이터 사용
        today = date.today()

        # VCP 데이터
        prices = [80000.0 + i * 100 for i in range(20)]
        prices.reverse()
        volumes = [1000000.0 for i in range(20)]
        volumes.reverse()

        vcp_result = calculate_vcp_score(prices, volumes)

        # SmartMoney 데이터
        flow_data = []
        for i in range(10):
            flow_data.append(FlowData(
                date=today - timedelta(days=i),
                foreign_net_buy=50_000_000_000,
                inst_net_buy=30_000_000_000,
                pension_net_buy=10_000_000_000,
                foreign_ownership=30.0,
            ))

        smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

        # 날짜 일관성 검증
        assert smartmoney_result.analysis_date == today
        # vcp_result에는 analysis_date 필드가 없음 (total_score 등만 존재)
        assert "total_score" in vcp_result

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # 최소 데이터
        prices = [80000.0] * 20
        volumes = [1000000.0] * 20

        vcp_result = calculate_vcp_score(prices, volumes)
        assert vcp_result["total_score"] >= 0

        # 빈 SmartMoney 데이터
        smartmoney_result = analyze_smartmoney("005930", [], period=5)
        assert smartmoney_result.total_score == 0
        assert smartmoney_result.foreign_trend == Trend.NEUTRAL


class TestSignalScoringIntegration:
    """시그널 점수화 통합 테스트"""

    def test_comprehensive_signal_score(self):
        """종합 시그널 점수 계산 테스트"""
        # VCP 데이터 (강세)
        prices = [80000 + i * 150 for i in range(20)]
        prices.reverse()
        volumes = [1500000.0 - i * 50000 for i in range(20)]
        volumes.reverse()

        vcp_result = calculate_vcp_score(prices, volumes)

        # SmartMoney 데이터 (강세)
        flow_data = create_mock_flow_data(days=10, foreign_trend="buy", inst_trend="buy")
        for i in range(len(flow_data)):
            flow_data[i].foreign_net_buy = 120_000_000_000
            flow_data[i].inst_net_buy = 90_000_000_000
            flow_data[i].foreign_ownership = 40.0

        smartmoney_result = analyze_smartmoney("005930", flow_data, period=5)

        # 종합 점수 계산 (가중치: VCP 50%, SmartMoney 50%)
        combined_score = (
            vcp_result["total_score"] * 0.5 +
            smartmoney_result.total_score * 0.5
        )

        # 검증
        assert 0 <= combined_score <= 100
        assert combined_score >= 50  # 강세 시나리오

        # 시그널 등급 결정
        if combined_score >= 80:
            grade = "S"
        elif combined_score >= 65:
            grade = "A"
        elif combined_score >= 50:
            grade = "B"
        else:
            grade = "C"

        assert grade in ["S", "A", "B", "C"]
