"""
Unit Tests for SignalScorer
종가베팅 V2 점수 계산기 테스트 (TDD)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
from dataclasses import dataclass

from services.signal_engine.scorer import (
    SignalScorer,
    ScoreDetail,
    Grade,
    JonggaSignal,
)


# Mock DailyPrice 모델
@dataclass
class MockDailyPrice:
    """테스트용 DailyPrice 모델"""
    date: date
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int


class TestVolumeScore:
    """거래대금 점수 계산 테스트

    점수 기준 (수정됨):
    - 3점: 5,000억 원 이상 (5,000,000,000,000)
    - 2점: 1,000억 원 이상 (1,000,000,000,000)
    - 1점: 300억 원 이상 (300,000,000,000)
    - 0점: 300억 원 미만
    """

    def test_calculate_volume_score_5000억이상_3점(self):
        """거래대금 5,000억 이상: 3점 (대형주 우량주)"""
        # Arrange: close_price=100000, volume=60000000 → 6조 원 (5,000억 이상)
        mock_price = MockDailyPrice(
            date=date.today(),
            open_price=100000,
            high_price=105000,
            low_price=95000,
            close_price=100000,
            volume=60_000_000  # 100,000원 * 60,000,000주 = 6조 원
        )
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[mock_price])
        scorer = SignalScorer(daily_price_repo=mock_repo)

        # Act
        score = scorer._calculate_volume_score("005930", 100000)

        # Assert
        assert score == 3, f"Expected 3점 for 6조 원 거래대금, got {score}"

    def test_calculate_volume_score_1000억이상_2점(self):
        """거래대금 1,000억 이상: 2점 (중형주)"""
        # Arrange: close_price=50000, volume=30000000 → 1.5조 원 (1,000억 이상)
        mock_price = MockDailyPrice(
            date=date.today(),
            open_price=50000,
            high_price=51000,
            low_price=49000,
            close_price=50000,
            volume=30_000_000  # 50,000원 * 30,000,000주 = 1.5조 원
        )
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[mock_price])
        scorer = SignalScorer(daily_price_repo=mock_repo)

        # Act
        score = scorer._calculate_volume_score("035420", 50000)

        # Assert
        assert score == 2, f"Expected 2점 for 1.5조 원 거래대금, got {score}"

    def test_calculate_volume_score_300억이상_1점(self):
        """거래대금 300억 이상: 1점 (소형주)"""
        # Arrange: close_price=100000, volume=4000000 → 4,000억 원 (300억 이상)
        mock_price = MockDailyPrice(
            date=date.today(),
            open_price=95000,
            high_price=105000,
            low_price=90000,
            close_price=100000,
            volume=4_000_000  # 100,000원 * 4,000,000주 = 4,000억 원
        )
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[mock_price])
        scorer = SignalScorer(daily_price_repo=mock_repo)

        # Act
        score = scorer._calculate_volume_score("005380", 100000)

        # Assert
        assert score == 1, f"Expected 1점 for 4,000억 원 거래대금, got {score}"

    def test_calculate_volume_score_300억미만_0점(self):
        """거래대금 300억 미만: 0점"""
        # Arrange: close_price=10000, volume=100000 → 10억 원 (300억 미만)
        mock_price = MockDailyPrice(
            date=date.today(),
            open_price=9500,
            high_price=10500,
            low_price=9000,
            close_price=10000,
            volume=100_000  # 10,000원 * 100,000주 = 10억 원
        )
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[mock_price])
        scorer = SignalScorer(daily_price_repo=mock_repo)

        # Act
        score = scorer._calculate_volume_score("000660", 10000)

        # Assert
        assert score == 0, f"Expected 0점 for 10억 원 거래대금, got {score}"

    def test_calculate_volume_score_정확히300억_1점(self):
        """거래대금 정확히 300억: 1점 (경계값 테스트)"""
        # Arrange: close_price=10000, volume=30000000 → 3,000억 원
        mock_price = MockDailyPrice(
            date=date.today(),
            open_price=9500,
            high_price=10500,
            low_price=9000,
            close_price=10000,
            volume=30_000_000  # 10,000원 * 30,000,000주 = 3,000억 원
        )
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[mock_price])
        scorer = SignalScorer(daily_price_repo=mock_repo)

        # Act
        score = scorer._calculate_volume_score("000660", 10000)

        # Assert
        assert score == 1, f"Expected 1점 for 3,000억 원 거래대금, got {score}"

    def test_calculate_volume_score_데이터없음_0점(self, mock_repo_empty):
        """데이터 없음: 0점"""
        # Arrange
        scorer = SignalScorer(daily_price_repo=mock_repo_empty)

        # Act
        score = scorer._calculate_volume_score("005930", 80000)

        # Assert
        assert score == 0

    def test_calculate_volume_score_Repository없음_0점(self):
        """Repository 없음: 0점"""
        # Arrange: _get_daily_price_repo가 None을 반환하도록 mock
        scorer = SignalScorer(daily_price_repo=None)
        with patch.object(scorer, '_get_daily_price_repo', return_value=None):
            # Act
            score = scorer._calculate_volume_score("005930", 80000)

            # Assert
            assert score == 0


@pytest.fixture
def mock_repo_empty():
    """Mock DailyPriceRepository with no data"""
    repo = Mock()
    repo.get_by_ticker_and_date_range = Mock(return_value=[])
    return repo


class TestChartScore:
    """차트 패턴 점수 계산 테스트"""

    def test_calculate_chart_score_vcp_신고가근접_2점(self, mock_vcp_analyzer):
        """VCP 패턴 + 52주 고가 근접: 2점"""
        # Arrange
        mock_vcp_analyzer.detect_vcp_pattern.return_value = True
        mock_vcp_analyzer.is_near_52w_high.return_value = True
        scorer = SignalScorer(vcp_analyzer=mock_vcp_analyzer)

        # Act
        score = scorer._calculate_chart_score("005930")

        # Assert
        assert score == 2

    def test_calculate_chart_score_vcp만_1점(self, mock_vcp_analyzer):
        """VCP 패턴만: 1점"""
        # Arrange
        mock_vcp_analyzer.detect_vcp_pattern.return_value = True
        mock_vcp_analyzer.is_near_52w_high.return_value = False
        scorer = SignalScorer(vcp_analyzer=mock_vcp_analyzer)

        # Act
        score = scorer._calculate_chart_score("005930")

        # Assert
        assert score == 1

    def test_calculate_chart_score_신고가만_1점(self, mock_vcp_analyzer):
        """52주 고가 근접만: 1점"""
        # Arrange
        mock_vcp_analyzer.detect_vcp_pattern.return_value = False
        mock_vcp_analyzer.is_near_52w_high.return_value = True
        scorer = SignalScorer(vcp_analyzer=mock_vcp_analyzer)

        # Act
        score = scorer._calculate_chart_score("005930")

        # Assert
        assert score == 1

    def test_calculate_chart_score_조건미충족_0점(self, mock_vcp_analyzer):
        """둘 다 미충족: 0점"""
        # Arrange
        mock_vcp_analyzer.detect_vcp_pattern.return_value = False
        mock_vcp_analyzer.is_near_52w_high.return_value = False
        scorer = SignalScorer(vcp_analyzer=mock_vcp_analyzer)

        # Act
        score = scorer._calculate_chart_score("005930")

        # Assert
        assert score == 0

    def test_calculate_chart_score_데이터부족_0점(self, mock_vcp_analyzer):
        """데이터 부족: 0점"""
        # Arrange
        mock_vcp_analyzer.detect_vcp_pattern.side_effect = ValueError("데이터 부족")
        scorer = SignalScorer(vcp_analyzer=mock_vcp_analyzer)

        # Act
        score = scorer._calculate_chart_score("005930")

        # Assert
        assert score == 0


@pytest.fixture
def mock_vcp_analyzer():
    """VCPAnalyzer Mock"""
    analyzer = Mock()
    analyzer.detect_vcp_pattern = Mock()
    analyzer.is_near_52w_high = Mock()
    return analyzer


class TestCandleScore:
    """캔들 점수 계산 테스트"""

    def test_calculate_candle_score_양봉돌파_1점(self):
        """장대양봉 돌파: 1점"""
        # Arrange
        scorer = SignalScorer()

        # Act & Assert - TODO: Implement after test structure is defined
        # score = scorer._calculate_candle_score("005930")
        # assert score == 1
        pass

    def test_calculate_candle_score_음봉_0점(self):
        """음봉: 0점"""
        # Arrange
        scorer = SignalScorer()

        # Act & Assert
        # score = scorer._calculate_candle_score("005930")
        # assert score == 0
        pass


class TestPeriodScore:
    """기간조정 점수 계산 테스트"""

    def test_calculate_period_score_3일이내반등_1점(self):
        """하락 후 3일 이내 반등: 1점"""
        pass

    def test_calculate_period_score_기간초과_0점(self):
        """3일 초과: 0점"""
        pass


class TestFlowScore:
    """수급 점수 계산 테스트"""

    def test_calculate_flow_score_쌍끌이_2점(self):
        """외국인+기관 동시 순매수: 2점"""
        pass

    def test_calculate_flow_score_외국인만_1점(self):
        """외국인만 순매수: 1점"""
        pass

    def test_calculate_flow_score_기관만_1점(self):
        """기관만 순매수: 1점"""
        pass

    def test_calculate_flow_score_수급없음_0점(self):
        """수급 없음: 0점"""
        pass


class TestGradeCalculation:
    """등급 산정 테스트"""

    def test_calculate_grade_10점이상_S급(self):
        """10점 이상: S급"""
        scorer = SignalScorer()
        grade = scorer._calculate_grade(10)
        assert grade == Grade.S

    def test_calculate_grade_8점이상_A급(self):
        """8점 이상: A급"""
        scorer = SignalScorer()
        grade = scorer._calculate_grade(8)
        assert grade == Grade.A

    def test_calculate_grade_6점이상_B급(self):
        """6점 이상: B급"""
        scorer = SignalScorer()
        grade = scorer._calculate_grade(6)
        assert grade == Grade.B

    def test_calculate_grade_6점미만_C급(self):
        """6점 미만: C급"""
        scorer = SignalScorer()
        grade = scorer._calculate_grade(5)
        assert grade == Grade.C


class TestPositionSize:
    """포지션 크기 계산 테스트"""

    def test_calculate_position_size_S급_15퍼센트(self):
        """S급: 15%"""
        scorer = SignalScorer()
        size = scorer._calculate_position_size(10_000_000, 1000, Grade.S)
        assert size == 1500  # 10M * 0.15 / 1000

    def test_calculate_position_size_A급_12퍼센트(self):
        """A급: 12%"""
        scorer = SignalScorer()
        size = scorer._calculate_position_size(10_000_000, 1000, Grade.A)
        assert size == 1200

    def test_calculate_position_size_B급_10퍼센트(self):
        """B급: 10%"""
        scorer = SignalScorer()
        size = scorer._calculate_position_size(10_000_000, 1000, Grade.B)
        assert size == 1000

    def test_calculate_position_size_C급_5퍼센트(self):
        """C급: 5%"""
        scorer = SignalScorer()
        size = scorer._calculate_position_size(10_000_000, 1000, Grade.C)
        assert size == 500


class TestReasonsGeneration:
    """매매 사유 생성 테스트"""

    def test_generate_reasons_뉴스우수(self):
        """뉴스 점수 높을 때"""
        scorer = SignalScorer()
        score = ScoreDetail(total=5, news=3, volume=0, chart=0, candle=0, period=0, flow=0)
        reasons = scorer._generate_reasons(score)
        assert "긍정적 뉴스 다수" in reasons

    def test_generate_reasons_여러항목(self):
        """여러 항목에서 사유 생성"""
        scorer = SignalScorer()
        score = ScoreDetail(total=7, news=2, volume=2, chart=1, candle=1, period=0, flow=1)
        reasons = scorer._generate_reasons(score)
        assert len(reasons) >= 4

    def test_generate_reasons_사유없음_기본값(self):
        """사유 없을 때 기본값"""
        scorer = SignalScorer()
        score = ScoreDetail(total=0, news=0, volume=0, chart=0, candle=0, period=0, flow=0)
        reasons = scorer._generate_reasons(score)
        assert reasons == ["종목 분석 완료"]
