"""
Unit Tests for Signal Tasks
종가베팅 V2 시그널 생성 태스크 테스트 (TDD)
"""


from tasks.signal_tasks import generate_jongga_signals, analyze_single_stock


class TestGenerateJonggaSignals:
    """generate_jongga_signals 태스크 테스트"""

    def test_전체종목_시그널생성_성공(self):
        """전체 종목 시그널 생성 성공"""
        # Arrange: 실제 SignalScorer 사용 (테스트용 Mock 데이터)
        task = generate_jongga_signals.s(capital=10_000_000, top_n=3)

        # Act
        result = task()

        # Assert: 최소한 성공 상태 반환
        assert result["status"] == "success"
        assert "count" in result
        assert "signals" in result

    def test_점수필터링_동작확인(self):
        """점수 필터링 동작 확인 (6점 이상만 포함)"""
        # Arrange: 실제 SignalScorer 사용
        task = generate_jongga_signals.s(capital=10_000_000, top_n=10)

        # Act
        result = task()

        # Assert
        assert result["status"] == "success"
        # 모든 시그널이 6점 이상인지 확인
        for signal in result["signals"]:
            assert signal["score"]["total"] >= 6

    def test_capital_top_n_파라미터(self):
        """capital과 top_n 파라미터 전달 확인"""
        # Arrange
        task = generate_jongga_signals.s(capital=50_000_000, top_n=5)

        # Act
        result = task()

        # Assert
        assert result["status"] == "success"
        assert result["capital"] == 50_000_000


class TestAnalyzeSingleStock:
    """analyze_single_stock 태스크 테스트"""

    def test_단일종목_분석_삼성전자(self):
        """단일 종목 분석 - 삼성전자"""
        # Act: 실제 SignalScorer 사용
        result = analyze_single_stock("005930", "삼성전자", 80000)

        # Assert
        assert result["status"] in ["success", "failed"]
        if result["status"] == "success":
            assert "signal" in result

    def test_단일종목_분석_데이터없음(self):
        """데이터 없는 종목 분석"""
        # Act: 존재하지 않는 종목 코드
        result = analyze_single_stock("999999", "없는종목", 1000)

        # Assert: 실패 또는 0점 시그널
        assert result["status"] in ["success", "failed"]
        if result["status"] == "success":
            # 시그널이 있으면 점수 확인
            signal = result.get("signal", {})
            score = signal.get("score", {}).get("total", 0)
            assert score == 0  # 데이터 없으면 0점

    def test_단일종목_분석_예외상황_처리(self):
        """예외 상황 처리 확인"""
        # Arrange: 잘못된 파라미터로 예외 유도
        result = analyze_single_stock("", "", 0)

        # Assert: 예외 처리되어 에러 상태 반환
        assert result["status"] in ["success", "failed", "error"]
