"""
Unit Tests for VCPAnalyzer
종가베팅 V2 차트 패턴 분석기 테스트 (TDD)

VCP 패턴: 볼린저밴드 수축 + 거래량 감소
52주 고가 근접: 현재가가 52주 고가의 95% 이상
"""

from unittest.mock import Mock, patch
from datetime import date, timedelta
from dataclasses import dataclass

from src.analysis.vcp_analyzer_improved import VCPAnalyzer, calculate_bollinger_bands


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


class TestVCPAnalyzerDetectPattern:
    """VCPAnalyzer.detect_vcp_pattern() 테스트"""

    @patch('src.analysis.vcp_analyzer_improved.calculate_vcp_score')
    def test_vcp패턴_감지성공_60점이상(self, mock_calculate_vcp_score):
        """VCP 패턴 감지: 60점 이상"""
        # Arrange: VCP 점수 60점 이상 반환
        mock_calculate_vcp_score.return_value = {
            "total_score": 70.0,
            "bb_contraction": 30.0,
            "volume_decrease": 20.0,
            "volatility_decrease": 20.0,
        }

        mock_repo = Mock()
        prices = self._create_vcp_pattern_prices()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=prices)

        analyzer = VCPAnalyzer(daily_price_repo=mock_repo)

        # Act
        result = analyzer.detect_vcp_pattern("005930")

        # Assert: 60점 이상이므로 VCP 패턴 감지
        assert result is True

    def test_vcp패턴_미감지_데이터부족(self):
        """데이터 부족 시 VCP 패턴 미감지"""
        # Arrange: 20일 미만 데이터
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[
            MockDailyPrice(
                date=date.today() - timedelta(days=i),
                open_price=80000, high_price=81000, low_price=79000, close_price=80000, volume=1000000
            )
            for i in range(10)
        ])

        analyzer = VCPAnalyzer(daily_price_repo=mock_repo)

        # Act
        result = analyzer.detect_vcp_pattern("005930")

        # Assert
        assert result is False

    def test_vcp패턴_미감지_레포지토리없음(self):
        """Repository 없을 때 VCP 패턴 미감지"""
        # Arrange: Repository 없음
        analyzer = VCPAnalyzer(daily_price_repo=None)

        # Act
        result = analyzer.detect_vcp_pattern("005930")

        # Assert
        assert result is False

    def test_vcp패턴_예외처리(self):
        """예외 발생 시 VCP 패턴 미감지"""
        # Arrange: 예외 발생하는 Mock
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(side_effect=Exception("DB Error"))

        analyzer = VCPAnalyzer(daily_price_repo=mock_repo)

        # Act
        result = analyzer.detect_vcp_pattern("005930")

        # Assert: 예외 처리로 False 반환
        assert result is False

    def _create_vcp_pattern_prices(self):
        """VCP 패턴을 형성하는 Mock 데이터 생성 헬퍼"""
        # 볼린저밴드 수축 패턴: 변동성이 점차 감소
        prices = []
        base_price = 80000
        base_volume = 1000000

        for i in range(60):
            # 점차 변동성 감소
            volatility = max(100, 2000 - i * 30)
            noise = (i % 5 - 2) * volatility

            prices.append(MockDailyPrice(
                date=date.today() - timedelta(days=60 - i),
                open_price=base_price + noise,
                high_price=base_price + noise + volatility,
                low_price=base_price + noise - volatility,
                close_price=base_price + noise,
                volume=base_volume + (i % 3 - 1) * 50000,  # 거래량도 감소
            ))

        return prices


class TestVCPAnalyzer52WeekHigh:
    """VCPAnalyzer.is_near_52w_high() 테스트"""

    def test_52주고가_근접_95퍼센트이상(self):
        """52주 고가 근접: 95% 이상"""
        # Arrange
        mock_repo = Mock()
        prices = self._create_52w_prices(current_price=95000, max_high=100000)
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=prices)

        analyzer = VCPAnalyzer(daily_price_repo=mock_repo)

        # Act
        result = analyzer.is_near_52w_high("005930", threshold=0.95)

        # Assert: 95000 >= 100000 * 0.95 = 95000
        assert result is True

    def test_52주고가_미근접_95퍼센트미만(self):
        """52주 고가 미근접: 95% 미만"""
        # Arrange
        mock_repo = Mock()
        prices = self._create_52w_prices(current_price=94000, max_high=100000)
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=prices)

        analyzer = VCPAnalyzer(daily_price_repo=mock_repo)

        # Act
        result = analyzer.is_near_52w_high("005930", threshold=0.95)

        # Assert: 94000 < 95000
        assert result is False

    def test_52주고가_데이터없음_False(self):
        """데이터 없을 때 False"""
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range = Mock(return_value=[])

        analyzer = VCPAnalyzer(daily_price_repo=mock_repo)

        # Act
        result = analyzer.is_near_52w_high("005930")

        # Assert
        assert result is False

    def test_52주고가_레포지토리없음_False(self):
        """Repository 없을 때 False"""
        # Arrange
        analyzer = VCPAnalyzer(daily_price_repo=None)

        # Act
        result = analyzer.is_near_52w_high("005930")

        # Assert
        assert result is False

    def _create_52w_prices(self, current_price: int, max_high: int):
        """52주 데이터 Mock 생성 헬퍼"""
        prices = []
        for i in range(365):
            # 고가 설정 (max_high 포함)
            high = max_high if i == 100 else current_price + (i % 1000)
            prices.append(MockDailyPrice(
                date=date.today() - timedelta(days=365 - i),
                open_price=current_price,
                high_price=high,
                low_price=current_price - 1000,
                close_price=current_price,
                volume=1000000,
            ))

        return prices


class TestCalculateBollingerBands:
    """calculate_bollinger_bands() 함수 테스트"""

    def test_볼린저밴드_계산_정상(self):
        """볼린저밴드 정상 계산"""
        # Arrange: 30일 데이터
        prices = [80000 + i * 100 + (i % 5 - 2) * 500 for i in range(30)]

        # Act
        upper, middle, lower = calculate_bollinger_bands(prices, period=20)

        # Assert
        assert upper is not None
        assert middle is not None
        assert lower is not None
        assert len(upper) == 11  # 30 - 20 + 1
        assert len(middle) == 11
        assert len(lower) == 11
        # 상단 > 중간 > 하단
        assert upper[0] > middle[0]
        assert middle[0] > lower[0]

    def test_볼린저밴드_데이터부족_None(self):
        """데이터 부족 시 None 반환"""
        # Arrange: 10일 데이터 (period=20 필요)
        prices = [80000 + i * 100 for i in range(10)]

        # Act
        upper, middle, lower = calculate_bollinger_bands(prices, period=20)

        # Assert
        assert upper is None
        assert middle is None
        assert lower is None
