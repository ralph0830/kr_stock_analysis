"""
Unit Tests for Signal Tasks
종가베팅 V2 시그널 생성 태스크 테스트 (TDD)
"""

from unittest.mock import Mock, patch

from tasks.signal_tasks import generate_jongga_signals, analyze_single_stock


class TestGenerateJonggaSignals:
    """generate_jongga_signals 태스크 테스트"""

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_전체종목_시그널생성_성공(self, mock_scorer_class):
        """전체 종목 시그널 생성 성공"""
        # Mock 설정
        mock_signal = Mock()
        mock_signal.score.total = 8
        mock_signal.to_dict.return_value = {
            "ticker": "005930",
            "name": "삼성전자",
            "grade": "A",
            "score": {"total": 8}
        }

        mock_scorer = Mock()
        mock_scorer.calculate.return_value = mock_signal
        mock_scorer_class.return_value = mock_scorer

        # Arrange
        task = generate_jongga_signals.s(capital=10_000_000, top_n=3)

        # Act
        result = task()

        # Assert: 최소한 성공 상태 반환
        assert result["status"] == "success"
        assert "count" in result
        assert "signals" in result

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_점수필터링_동작확인(self, mock_scorer_class):
        """점수 필터링 동작 확인 (6점 이상만 포함)"""
        # Mock 설정 - 6점 이상 시그널
        mock_signal_high = Mock()
        mock_signal_high.score.total = 8
        mock_signal_high.to_dict.return_value = {
            "ticker": "005930",
            "name": "삼성전자",
            "grade": "A",
            "score": {"total": 8}
        }

        # Mock 설정 - 6점 미만 시그널
        mock_signal_low = Mock()
        mock_signal_low.score.total = 4
        mock_signal_low.to_dict.return_value = {
            "ticker": "000660",
            "name": "SK하이닉스",
            "grade": "C",
            "score": {"total": 4}
        }

        mock_scorer = Mock()
        # 모든 호출에 대해 충분한 side_effect 제공 (3개 종목)
        mock_scorer.calculate.side_effect = [mock_signal_high, mock_signal_low, mock_signal_high]
        mock_scorer_class.return_value = mock_scorer

        # Arrange
        task = generate_jongga_signals.s(capital=10_000_000, top_n=10)

        # Act
        result = task()

        # Assert
        assert result["status"] == "success"
        # 모든 시그널이 6점 이상인지 확인
        for signal in result["signals"]:
            assert signal["score"]["total"] >= 6

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_capital_top_n_파라미터(self, mock_scorer_class):
        """capital과 top_n 파라미터 전달 확인"""
        # Mock 설정
        mock_signal = Mock()
        mock_signal.score.total = 7
        mock_signal.to_dict.return_value = {
            "ticker": "005930",
            "grade": "B",
            "score": {"total": 7}
        }

        mock_scorer = Mock()
        mock_scorer.calculate.return_value = mock_signal
        mock_scorer_class.return_value = mock_scorer

        # Arrange
        task = generate_jongga_signals.s(capital=50_000_000, top_n=5)

        # Act
        result = task()

        # Assert
        assert result["status"] == "success"
        assert result["capital"] == 50_000_000


class TestAnalyzeSingleStock:
    """analyze_single_stock 태스크 테스트"""

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_단일종목_분석_삼성전자(self, mock_scorer_class):
        """단일 종목 분석 - 삼성전자"""
        # Mock 설정
        mock_signal = Mock()
        mock_signal.to_dict.return_value = {
            "ticker": "005930",
            "name": "삼성전자",
            "grade": "A"
        }

        mock_scorer = Mock()
        mock_scorer.calculate.return_value = mock_signal
        mock_scorer_class.return_value = mock_scorer

        # Act
        result = analyze_single_stock("005930", "삼성전자", 80000)

        # Assert
        assert result["status"] == "success"
        assert "signal" in result

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_단일종목_분석_데이터없음(self, mock_scorer_class):
        """데이터 없는 종목 분석"""
        # Mock 설정 - None 반환 (데이터 없음)
        mock_scorer = Mock()
        mock_scorer.calculate.return_value = None
        mock_scorer_class.return_value = mock_scorer

        # Act: 존재하지 않는 종목 코드
        result = analyze_single_stock("999999", "없는종목", 1000)

        # Assert: 실패 상태
        assert result["status"] == "failed"

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_단일종목_분석_예외상황_처리(self, mock_scorer_class):
        """예외 상황 처리 확인"""
        # Mock 설정 - 예외 발생
        mock_scorer = Mock()
        mock_scorer.calculate.side_effect = Exception("Invalid parameters")
        mock_scorer_class.return_value = mock_scorer

        # Arrange: 잘못된 파라미터로 예외 유도
        result = analyze_single_stock("", "", 0)

        # Assert: 예외 처리되어 에러 상태 반환
        assert result["status"] == "error"
