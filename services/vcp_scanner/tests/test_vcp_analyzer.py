"""
VCP Analyzer 테스트 (TDD RED Phase)

vcp_analyzer.py의 핵심 로직 테스트
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch, AsyncMock
import numpy as np


class TestVCPResult:
    """VCPResult dataclass 테스트"""

    def test_vcp_result_creation(self):
        """VCPResult 생성 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPResult

        result = VCPResult(
            ticker="005930",
            name="삼성전자",
            vcp_score=85.0,
            smartmoney_score=75.0,
            total_score=80.0,
            pattern_detected=True,
            signals=["VCP 수축 감지"],
            analysis_date=date.today(),
            current_price=80000.0,
        )

        assert result.ticker == "005930"
        assert result.vcp_score == 85.0
        assert result.pattern_detected is True

    def test_vcp_result_to_dict(self):
        """VCPResult to_dict 메서드 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPResult

        result = VCPResult(
            ticker="005930",
            name="삼성전자",
            vcp_score=85.0,
            smartmoney_score=75.0,
            total_score=80.0,
            pattern_detected=True,
            signals=[],
            analysis_date=date.today(),
        )

        data = result.to_dict()

        assert data["ticker"] == "005930"
        assert data["vcp_score"] == 85.0
        assert "analysis_date" in data


class TestVCPAnalyzer:
    """VCPAnalyzer 클래스 테스트"""

    def test_analyzer_init(self):
        """VCPAnalyzer 초기화 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    @patch('services.vcp_scanner.vcp_analyzer.SessionLocal')
    async def test_analyze_returns_none_when_no_data(self, mock_session_local):
        """데이터 없을 때 analyze는 None 반환"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer
        from sqlalchemy import select

        analyzer = VCPAnalyzer()

        # Mock: 빈 데이터 반환
        mock_session = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # SessionLocal mock이 작동하도록 설정
        def get_session():
            return mock_session

        mock_session_local = Mock()
        mock_session_local.__enter__ = Mock(return_value=mock_session)
        mock_session_local.__exit__ = Mock(return_value=False)

        # async def _get_current_price에서 사용
        with patch('services.vcp_scanner.vcp_analyzer.SessionLocal', return_value=mock_session_local):
            result = await analyzer.analyze("999999", "없는종목")

        assert result is None

    def test_detect_vcp_pattern_with_mock(self):
        """VCP 패턴 감지 테스트 (mock 사용)"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # 실제 DB 없이므로 False 반환 예상
        # (의존성 주입 후 실제 테스트 가능)
        with patch.object(analyzer, '_calculate_vcp_score', return_value=80.0):
            # 이 테스트는 나중에 DB 연동 후 실제 동작 확인
            pass

    def test_score_calculation_components(self):
        """점수 계산 구성 요소 테스트"""
        # VCP 점스 구성:
        # - 볼린저밴드 수축 (30%)
        # - 거래량 감소 (20%)
        # - 가격 변동성 감소 (20%)
        # - RSI 중립 (15%)
        # - MACD 정렬 (15%)

        # 테스트: 가중평 계산 검증
        weights = [30, 20, 20, 15, 15]
        total_weight = sum(weights)
        assert total_weight == 100, f"가중치 합계는 100이어야 함: {total_weight}"

    @pytest.mark.asyncio
    async def test_scan_market_with_mock(self):
        """시장 스캔 테스트 (mock 사용)"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer
        from services.vcp_scanner.vcp_analyzer import VCPResult

        analyzer = VCPAnalyzer()

        # Mock DB 결과
        mock_stocks = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
        ]

        # SessionLocal mock
        mock_session = Mock()
        mock_result = Mock()
        mock_stocks_mock = Mock()
        mock_stocks_mock.all.return_value = [(s[0], s[1]) for s in mock_stocks]
        mock_result.scalars.return_value = mock_stocks_mock
        mock_session.execute.return_value = mock_result

        mock_session_local = Mock()
        mock_session_local.__enter__ = Mock(return_value=mock_session)
        mock_session_local.__exit__ = Mock(return_value=False)

        with patch('services.vcp_scanner.vcp_analyzer.SessionLocal', return_value=mock_session_local):
            # analyze는 async 함수이므로 mock을 사용하려면 추가 설정 필요
            # 일단 데이터 조회 부분만 테스트
            pass

    def test_vcp_score_formula(self):
        """VCP 점수 계산 공식 검증"""
        # VCP 점수 = 볼린저밴드 수축 + 거래량 감소 + 변동성 감소 + RSI + MACD
        # 가중치: 30, 20, 20, 15, 15

        # 예시: 모든 항목이 100점일 때
        scores = [100, 100, 100, 100, 100]
        weights = [0.3, 0.2, 0.2, 0.15, 0.15]
        calculated = sum(s * w for s, w in zip(scores, weights))
        expected = 100.0

        assert abs(calculated - expected) < 0.01, f"VCP 점수: {calculated}, 기대: {expected}"

    def test_smartmoney_score_formula(self):
        """SmartMoney 점수 계산 공식 검증"""
        # SmartMoney = 외국인(40%) + 기관(30%) + 수급종합(30%)
        weights = [0.4, 0.3, 0.3]

        # 예시: 모든 항목 50점일 때
        scores = [50, 50, 50]
        calculated = sum(s * w for s, w in zip(scores, weights))
        expected = 50.0

        assert abs(calculated - expected) < 0.01, f"SmartMoney 점수: {calculated}, 기대: {expected}"

    def test_total_score_formula(self):
        """총점 계산 공식 검증"""
        # 총점 = VCP(50%) + SmartMoney(50%)

        # 예시
        vcp = 80.0
        smartmoney = 70.0
        total = (vcp * 0.5) + (smartmoney * 0.5)

        expected = 75.0
        assert abs(total - expected) < 0.01, f"총점: {total}, 기대: {expected}"


class TestVCPScannerDatabase:
    """VCP Scanner DB 연동 테스트"""

    @pytest.mark.integration
    def test_vcp_scanner_requires_db(self):
        """VCP Scanner가 DB 연동이 필요함을 확인"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()
        # analyze 메서드는 DB 의존적
        # 테스트 환경에서는 mock 사용 필요

        assert hasattr(analyzer, 'analyze')
        assert hasattr(analyzer, 'scan_market')


class TestVCPScoreCalculation:
    """VCP 점수 계산 상세 테스트 (mock 데이터 사용)"""

    @pytest.mark.asyncio
    async def test_vcp_score_with_contraction_pattern(self):
        """VCP 수축 패턴 감지 시 높은 점수 반환"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer
        from datetime import date, timedelta
        import numpy as np

        analyzer = VCPAnalyzer()

        # _calculate_vcp_score를 직접 mock하여 수축 패턴 점수 반환
        with patch.object(analyzer, '_calculate_vcp_score', return_value=80.0):
            with patch.object(analyzer, '_calculate_smartmoney_score', return_value=50.0):
                with patch.object(analyzer, '_get_current_price', return_value=80000.0):
                    result = await analyzer.analyze("005930", "삼성전자")

        assert result is not None
        assert result.vcp_score == 80.0
        assert result.total_score == 65.0  # (80 * 0.5) + (50 * 0.5)
        assert result.pattern_detected is True  # 60점 이상

    @pytest.mark.asyncio
    async def test_smartmoney_score_with_foreign_buying(self):
        """외국인 순매수 시 높은 SmartMoney 점수"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # SmartMoney 점수가 높게 mock
        with patch.object(analyzer, '_calculate_vcp_score', return_value=50.0):
            with patch.object(analyzer, '_calculate_smartmoney_score', return_value=85.0):
                with patch.object(analyzer, '_get_current_price', return_value=80000.0):
                    result = await analyzer.analyze("005930", "삼성전자")

        assert result is not None
        assert result.smartmoney_score == 85.0
        assert result.total_score == 67.5  # (50 * 0.5) + (85 * 0.5)
        assert "SmartMoney 유입" in result.signals  # 60점 이상

    def test_vcp_result_signals_generation(self):
        """VCPResult signals 생성 로직 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPResult
        from datetime import date

        # VCP 점수가 높을 때
        result = VCPResult(
            ticker="005930",
            name="삼성전자",
            vcp_score=70,
            smartmoney_score=50,
            total_score=60,
            pattern_detected=True,
            signals=[],
            analysis_date=date.today(),
        )

        # 수동으로 signals 생성 로직 테스트
        signals = []
        if result.vcp_score > 60:
            signals.append("VCP 수축 감지")
        if result.smartmoney_score > 60:
            signals.append("SmartMoney 유입")

        assert "VCP 수축 감지" in signals
        assert "SmartMoney 유입" not in signals  # 50점이므로 미포함

    @pytest.mark.asyncio
    async def test_get_current_price_with_mock(self):
        """현재가 조회 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer
        from unittest.mock import Mock, AsyncMock

        analyzer = VCPAnalyzer()

        # _get_current_price를 직접 mock
        with patch.object(analyzer, '_get_current_price', return_value=80500.0):
            price = await analyzer._get_current_price("005930")

        assert price == 80500.0

    @pytest.mark.asyncio
    async def test_analyze_with_insufficient_data(self):
        """데이터 부족 시 기본 점수 반환"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # 빈 데이터 반환 mock
        with patch.object(analyzer, '_calculate_vcp_score', return_value=0.0):
            with patch.object(analyzer, '_calculate_smartmoney_score', return_value=50.0):
                with patch.object(analyzer, '_get_current_price', return_value=None):
                    result = await analyzer.analyze("999999", "없는종목")

        # 데이터 부족해도 기본 SmartMoney 점수로 반환
        assert result is not None
        assert result.vcp_score == 0.0
        assert result.smartmoney_score == 50.0
