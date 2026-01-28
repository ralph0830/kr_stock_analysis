#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config/settings.py 테스트 (RED Phase)

이 테스트는 PART_01.md의 config.py 동작을 재현합니다.
모든 테스트는 실패(ImportError)해야 정상입니다.
"""

import pytest


# =============================================================================
# 테스트 대상 Import (아직 구현되지 않음)
# =============================================================================
try:
    from src.config.settings import (
        MarketRegime,
        SignalType,
        TrendThresholds,
        MarketGateConfig,
        BacktestConfig,
        ScreenerConfig,
        KOSPI_TICKER,
        KOSDAQ_TICKER,
        USD_KRW_TICKER,
        SECTORS,
    )
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False


# =============================================================================
# MarketRegime Enum 테스트
# =============================================================================
class TestMarketRegime:
    """시장 상태 Enum 테스트"""

    def test_enum_values_exist(self):
        """Enum 값 존재 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("MarketRegime import failed - module not implemented")

        assert MarketRegime.KR_BULLISH is not None
        assert MarketRegime.KR_NEUTRAL is not None
        assert MarketRegime.KR_BEARISH is not None

    def test_enum_value_attributes(self):
        """Enum value 속성 확인 (한글 값)"""
        if not IMPORT_SUCCESS:
            pytest.fail("MarketRegime import failed - module not implemented")

        assert MarketRegime.KR_BULLISH.value == "강세장"
        assert MarketRegime.KR_NEUTRAL.value == "중립"
        assert MarketRegime.KR_BEARISH.value == "약세장"

    def test_enum_members_count(self):
        """Enum 멤버 개수 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("MarketRegime import failed - module not implemented")

        assert len(MarketRegime) == 3


# =============================================================================
# SignalType Enum 테스트
# =============================================================================
class TestSignalType:
    """진입 시그널 유형 Enum 테스트"""

    def test_enum_values_exist(self):
        """Enum 값 존재 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("SignalType import failed - module not implemented")

        assert SignalType.FOREIGNER_BUY is not None
        assert SignalType.INST_SCOOP is not None
        assert SignalType.DOUBLE_BUY is not None

    def test_enum_value_attributes(self):
        """Enum value 속성 확인 (한글 값)"""
        if not IMPORT_SUCCESS:
            pytest.fail("SignalType import failed - module not implemented")

        assert SignalType.FOREIGNER_BUY.value == "외인매수"
        assert SignalType.INST_SCOOP.value == "기관매집"
        assert SignalType.DOUBLE_BUY.value == "쌍끌이"


# =============================================================================
# TrendThresholds dataclass 테스트
# =============================================================================
class TestTrendThresholds:
    """수급 트렌드 판단 기준 dataclass 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("TrendThresholds import failed - module not implemented")

        thresholds = TrendThresholds()

        # 외국인 기본값
        assert thresholds.foreign_strong_buy == 5_000_000
        assert thresholds.foreign_buy == 2_000_000
        assert thresholds.foreign_neutral == -1_000_000
        assert thresholds.foreign_sell == -2_000_000
        assert thresholds.foreign_strong_sell == -5_000_000

    def test_institutional_defaults(self):
        """기관 기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("TrendThresholds import failed - module not implemented")

        thresholds = TrendThresholds()

        assert thresholds.inst_strong_buy == 3_000_000
        assert thresholds.inst_buy == 1_000_000
        assert thresholds.inst_neutral == -500_000
        assert thresholds.inst_sell == -1_000_000
        assert thresholds.inst_strong_sell == -3_000_000

    def test_ratio_defaults(self):
        """비율 기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("TrendThresholds import failed - module not implemented")

        thresholds = TrendThresholds()

        assert thresholds.high_ratio_foreign == 12.0
        assert thresholds.high_ratio_inst == 8.0

    def test_custom_values(self):
        """사용자 정의값 생성"""
        if not IMPORT_SUCCESS:
            pytest.fail("TrendThresholds import failed - module not implemented")

        thresholds = TrendThresholds(
            foreign_buy=3_000_000,
            inst_buy=2_000_000,
            high_ratio_foreign=15.0,
        )

        assert thresholds.foreign_buy == 3_000_000
        assert thresholds.inst_buy == 2_000_000
        assert thresholds.high_ratio_foreign == 15.0


# =============================================================================
# MarketGateConfig dataclass 테스트
# =============================================================================
class TestMarketGateConfig:
    """Market Gate 설정 dataclass 테스트"""

    def test_usd_krw_defaults(self):
        """환율 기준값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("MarketGateConfig import failed - module not implemented")

        config = MarketGateConfig()

        assert config.usd_krw_safe == 1350.0
        assert config.usd_krw_warning == 1400.0
        assert config.usd_krw_danger == 1450.0

    def test_kospi_ma_defaults(self):
        """KOSPI 이평 기간 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("MarketGateConfig import failed - module not implemented")

        config = MarketGateConfig()

        assert config.kospi_ma_short == 20
        assert config.kospi_ma_long == 60

    def test_foreign_threshold(self):
        """외인 수급 기준 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("MarketGateConfig import failed - module not implemented")

        config = MarketGateConfig()
        assert config.foreign_net_buy_threshold == 500_000_000_000  # 5000억원


# =============================================================================
# BacktestConfig dataclass 테스트
# =============================================================================
class TestBacktestConfig:
    """백테스트 설정 dataclass 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.entry_trigger == "DOUBLE_BUY"
        assert config.min_score == 60
        assert config.min_consecutive_days == 3

    def test_exit_conditions(self):
        """청산 조건 기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.stop_loss_pct == 5.0
        assert config.take_profit_pct == 15.0
        assert config.trailing_stop_pct == 5.0
        assert config.max_hold_days == 15

    def test_rsi_exit_threshold(self):
        """RSI 기반 청산 설정 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()
        assert config.rsi_exit_threshold == 70

    def test_foreign_exit_conditions(self):
        """외인 청산 조건 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.exit_on_foreign_sell is True
        assert config.foreign_sell_days == 2

    def test_market_regime_settings(self):
        """Market Regime 설정 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.allowed_regimes == ["KR_BULLISH", "KR_NEUTRAL"]
        assert config.use_usd_krw_gate is True

    def test_capital_management(self):
        """자금 관리 설정 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.initial_capital == 100_000_000  # 1억원
        assert config.position_size_pct == 10.0
        assert config.max_positions == 10

    def test_cost_settings(self):
        """수수료/슬리피지 설정 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.commission_pct == 0.015
        assert config.slippage_pct == 0.1
        assert config.tax_pct == 0.23

    def test_get_total_cost_pct(self):
        """총 거래 비용 계산 메서드 테스트"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        # (0.015 * 2) + 0.1 + 0.23 = 0.36
        expected = (config.commission_pct * 2) + config.slippage_pct + config.tax_pct
        assert config.get_total_cost_pct() == expected
        assert config.get_total_cost_pct() == 0.36

    def test_should_trade_in_regime(self):
        """시장 상태별 거래 가능 여부 테스트"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig()

        assert config.should_trade_in_regime("KR_BULLISH") is True
        assert config.should_trade_in_regime("KR_NEUTRAL") is True
        assert config.should_trade_in_regime("KR_BEARISH") is False

    def test_conservative_preset(self):
        """보수적 설정 프리셋 테스트"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig.conservative()

        assert config.entry_trigger == "DOUBLE_BUY"
        assert config.min_score == 70
        assert config.min_consecutive_days == 5
        assert config.stop_loss_pct == 3.0
        assert config.take_profit_pct == 10.0
        assert config.trailing_stop_pct == 4.0
        assert config.max_hold_days == 10
        assert config.exit_on_foreign_sell is True
        assert config.foreign_sell_days == 1
        assert config.position_size_pct == 5.0
        assert config.max_positions == 5

    def test_aggressive_preset(self):
        """공격적 설정 프리셋 테스트"""
        if not IMPORT_SUCCESS:
            pytest.fail("BacktestConfig import failed - module not implemented")

        config = BacktestConfig.aggressive()

        assert config.entry_trigger == "FOREIGNER_BUY"
        assert config.min_score == 50
        assert config.min_consecutive_days == 3
        assert config.stop_loss_pct == 7.0
        assert config.take_profit_pct == 25.0
        assert config.trailing_stop_pct == 6.0
        assert config.max_hold_days == 20
        assert config.exit_on_foreign_sell is False
        assert config.position_size_pct == 15.0
        assert config.max_positions == 15


# =============================================================================
# ScreenerConfig dataclass 테스트
# =============================================================================
class TestScreenerConfig:
    """스크리너 설정 dataclass 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("ScreenerConfig import failed - module not implemented")

        config = ScreenerConfig()

        assert config.data_source == "naver"
        assert config.lookback_days == 60

    def test_weight_defaults(self):
        """점수 가중치 기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("ScreenerConfig import failed - module not implemented")

        config = ScreenerConfig()

        assert config.weight_foreign == 0.40
        assert config.weight_inst == 0.30
        assert config.weight_technical == 0.20
        assert config.weight_fundamental == 0.10

    def test_weights_sum_to_one(self):
        """가중치 합계가 1.0인지 확인 (부동소수점 오차 허용)"""
        if not IMPORT_SUCCESS:
            pytest.fail("ScreenerConfig import failed - module not implemented")

        config = ScreenerConfig()

        total = (
            config.weight_foreign
            + config.weight_inst
            + config.weight_technical
            + config.weight_fundamental
        )
        # 부동소수점 오차 허용 (pytest.approx 사용)
        assert total == pytest.approx(1.0)

    def test_top_n_default(self):
        """Top N 기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("ScreenerConfig import failed - module not implemented")

        config = ScreenerConfig()
        assert config.top_n == 20

    def test_filter_defaults(self):
        """필터 기본값 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("ScreenerConfig import failed - module not implemented")

        config = ScreenerConfig()

        assert config.min_market_cap == 100_000_000_000  # 1000억
        assert config.min_avg_volume == 100_000
        assert config.exclude_admin is True
        assert config.exclude_etf is True


# =============================================================================
# Constants 테스트
# =============================================================================
class TestConstants:
    """상수 정의 테스트"""

    def test_kospi_ticker(self):
        """KOSPI 티커 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        assert KOSPI_TICKER == "^KS11"

    def test_kosdaq_ticker(self):
        """KOSDAQ 티커 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        assert KOSDAQ_TICKER == "^KQ11"

    def test_usd_krw_ticker(self):
        """USD/KRW 티커 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        assert USD_KRW_TICKER == "KRW=X"

    def test_sectors_structure(self):
        """섹터 딕셔너리 구조 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        assert isinstance(SECTORS, dict)
        assert len(SECTORS) > 0

    def test_sectors_have_tickers(self):
        """각 섹터가 티커 리스트를 가지는지 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        for sector_name, tickers in SECTORS.items():
            assert isinstance(sector_name, str)
            assert isinstance(tickers, list)
            assert all(isinstance(t, str) for t in tickers)

    def test_expected_sectors_exist(self):
        """예상되는 섹터들이 존재하는지 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        expected_sectors = [
            "반도체",
            "2차전지",
            "자동차",
            "조선",
            "금융",
            "바이오",
            "인터넷",
            "에너지",
        ]

        for sector in expected_sectors:
            assert sector in SECTORS, f"섹터 '{sector}'가 SECTORS에 없습니다"

    def test_sector_ticker_format(self):
        """섹터 티커가 6자리 숫자인지 확인"""
        if not IMPORT_SUCCESS:
            pytest.fail("Constants import failed - module not implemented")

        for tickers in SECTORS.values():
            for ticker in tickers:
                assert len(ticker) == 6, f"티커 {ticker}가 6자리가 아닙니다"
                assert ticker.isdigit(), f"티커 {ticker}가 숫자가 아닙니다"


# =============================================================================
# 통합 테스트
# =============================================================================
class TestIntegration:
    """통합 동작 테스트"""

    def test_config_combination(self):
        """여러 config 클래스 함께 사용 테스트"""
        if not IMPORT_SUCCESS:
            pytest.fail("Config import failed - module not implemented")

        trend = TrendThresholds()
        gate = MarketGateConfig()
        backtest = BacktestConfig()
        screener = ScreenerConfig()

        # 각 인스턴스가 정상적으로 생성되었는지 확인
        assert trend is not None
        assert gate is not None
        assert backtest is not None
        assert screener is not None

    def test_enum_and_config_interaction(self):
        """Enum과 config의 상호작용 테스트"""
        if not IMPORT_SUCCESS:
            pytest.fail("Config import failed - module not implemented")

        config = BacktestConfig()

        # Enum 이름으로 regime 검증 (allowed_regimes는 Enum key를 가짐)
        assert config.should_trade_in_regime("KR_BULLISH") is True
        assert config.should_trade_in_regime("KR_BEARISH") is False

        # SignalType과 entry_trigger 비교 (entry_trigger는 Enum name 사용)
        assert config.entry_trigger == SignalType.DOUBLE_BUY.name
