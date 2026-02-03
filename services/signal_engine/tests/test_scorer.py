"""
Signal Scorer 테스트 (TDD RED Phase)

scorer.py의 핵심 로직 테스트
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch


class TestScoreDetail:
    """ScoreDetail dataclass 테스트"""

    def test_score_detail_creation(self):
        """ScoreDetail 생성 테스트"""
        from services.signal_engine.scorer import ScoreDetail

        score = ScoreDetail(total=10, news=3, volume=2, chart=2, candle=1, period=1, flow=0)

        assert score.total == 10
        assert score.news == 3
        assert score.volume == 2
        assert score.chart == 2
        assert score.candle == 1
        assert score.period == 1
        assert score.flow == 0

    def test_score_detail_to_dict(self):
        """ScoreDetail to_dict 메서드 테스트"""
        from services.signal_engine.scorer import ScoreDetail

        score = ScoreDetail(total=8)
        result = score.to_dict()

        assert result["total"] == 8
        assert "news" in result
        assert "volume" in result


class TestGrade:
    """Grade Enum 테스트"""

    def test_grade_values(self):
        """Grade Enum 값 확인"""
        from services.signal_engine.scorer import Grade

        assert Grade.S.value == "S"
        assert Grade.A.value == "A"
        assert Grade.B.value == "B"
        assert Grade.C.value == "C"


class TestJonggaSignal:
    """JonggaSignal dataclass 테스트"""

    def test_jongga_signal_creation(self):
        """JonggaSignal 생성 테스트"""
        from services.signal_engine.scorer import JonggaSignal, ScoreDetail, Grade

        score = ScoreDetail(total=10)
        signal = JonggaSignal(
            ticker="005930",
            name="삼성전자",
            score=score,
            grade=Grade.S,
            position_size=100,
            entry_price=80000,
            target_price=92000,
            stop_loss=76000,
            reasons=["긍정적 뉴스 다수"],
            created_at=datetime.now().isoformat(),
        )

        assert signal.ticker == "005930"
        assert signal.name == "삼성전자"
        assert signal.grade == Grade.S

    def test_jongga_signal_to_dict(self):
        """JonggaSignal to_dict 메서드 테스트"""
        from services.signal_engine.scorer import JonggaSignal, ScoreDetail, Grade

        score = ScoreDetail(total=8)
        signal = JonggaSignal(
            ticker="005930",
            name="삼성전자",
            score=score,
            grade=Grade.A,
            position_size=100,
            entry_price=80000,
            target_price=92000,
            stop_loss=76000,
            reasons=[],
            created_at="2026-01-30T10:00:00",
        )

        result = signal.to_dict()

        assert result["ticker"] == "005930"
        assert result["score"]["total"] == 8
        assert result["grade"] == "A"


class TestSignalScorer:
    """SignalScorer 클래스 테스트"""

    def test_scorer_init(self):
        """SignalScorer 초기화 테스트"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()

        assert scorer is not None
        assert scorer._daily_price_repo is None
        assert scorer._vcp_analyzer is None

    def test_calculate_grade_s(self):
        """S급 등급 계산 (10점 이상)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        grade = scorer._calculate_grade(10)

        assert grade == Grade.S

    def test_calculate_grade_a(self):
        """A급 등급 계산 (8점 이상)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        grade = scorer._calculate_grade(8)

        assert grade == Grade.A

    def test_calculate_grade_b(self):
        """B급 등급 계산 (6점 이상)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        grade = scorer._calculate_grade(6)

        assert grade == Grade.B

    def test_calculate_grade_c(self):
        """C급 등급 계산 (6점 미만)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        grade = scorer._calculate_grade(5)

        assert grade == Grade.C

    def test_calculate_position_size_s(self):
        """S급 포지션 크기 계산 (15%)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        capital = 10_000_000  # 1000만원
        price = 80000

        size = scorer._calculate_position_size(capital, price, Grade.S)

        # 1000만원 * 15% / 80000 = 18.75주 → 18주
        assert size == int(capital * 0.15 / price)

    def test_calculate_position_size_a(self):
        """A급 포지션 크기 계산 (12%)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        capital = 10_000_000
        price = 80000

        size = scorer._calculate_position_size(capital, price, Grade.A)

        assert size == int(capital * 0.12 / price)

    def test_calculate_position_size_b(self):
        """B급 포지션 크기 계산 (10%)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        capital = 10_000_000
        price = 80000

        size = scorer._calculate_position_size(capital, price, Grade.B)

        assert size == int(capital * 0.10 / price)

    def test_calculate_position_size_c(self):
        """C급 포지션 크기 계산 (5%)"""
        from services.signal_engine.scorer import SignalScorer, Grade

        scorer = SignalScorer()
        capital = 10_000_000
        price = 80000

        size = scorer._calculate_position_size(capital, price, Grade.C)

        assert size == int(capital * 0.05 / price)

    def test_generate_reasons_multiple(self):
        """매매 사유 생성 (다수)"""
        from services.signal_engine.scorer import SignalScorer, ScoreDetail

        scorer = SignalScorer()
        score = ScoreDetail(
            total=10,
            news=3,
            volume=3,
            chart=1,
            candle=1,
            period=1,
            flow=1,
        )

        reasons = scorer._generate_reasons(score)

        assert len(reasons) >= 4  # news, volume, chart, flow 최소
        assert any("뉴스" in r for r in reasons)
        assert any("거래대금" in r for r in reasons)

    def test_generate_reasons_empty(self):
        """매매 사유 생성 (없을 때)"""
        from services.signal_engine.scorer import SignalScorer, ScoreDetail

        scorer = SignalScorer()
        score = ScoreDetail(total=0)  # 모든 점수 0

        reasons = scorer._generate_reasons(score)

        assert len(reasons) == 1
        assert reasons[0] == "종목 분석 완료"

    def test_calculate_returns_signal_when_dependencies_unavailable(self):
        """의존성 없을 때 calculate 결과 (mock 데이터)"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        # 의존성이 없으므로 모든 점수는 0이 됨
        signal = scorer.calculate("999999", "테스트종목", 50000)

        # 의존성 없어도 기본 시그널은 반환
        assert signal is not None
        assert signal.ticker == "999999"
        assert signal.name == "테스트종목"
        assert signal.score.total == 0  # 모든 점수 0
        assert signal.grade.value == "C"  # 0점은 C등급

    def test_calculate_target_and_stop_prices(self):
        """목표가/손절가 계산 확인"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        signal = scorer.calculate("999998", "테스트종목2", 100000)

        assert signal is not None
        # 목표가: +15% (반올림 처리됨)
        assert signal.target_price in [114999, 115000]  # 부동소수점 반올림
        # 손절가: -5%
        assert signal.stop_loss == 95000

    def test_volume_score_thresholds(self):
        """거래대금 점수 계산 (DB 연동 시 실제 점수 반환)"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        # DB 연동 시 실제 데이터가 있으면 점수 계산
        score = scorer._calculate_volume_score("005930", 80000)
        # 0-3점 범위 내여야 함
        assert 0 <= score <= 3

    def test_chart_score_without_analyzer(self):
        """VCP analyzer 없을 때 차트 점수"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        score = scorer._calculate_chart_score("005930")
        assert score == 0

    def test_candle_score_without_repo(self):
        """DailyPrice repo 없을 때 캔들 점수"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        score = scorer._calculate_candle_score("005930")
        assert score == 0

    def test_period_score_without_repo(self):
        """기간 점수 계산 (DB 연동 시 실제 점수 반환)"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        # DB 연동 시 실제 데이터가 있으면 점수 계산
        score = scorer._calculate_period_score("005930")
        # 0-1점 범위 내여야 함
        assert 0 <= score <= 1

    def test_flow_score_without_repo(self):
        """DailyPrice repo 없을 때 수급 점수"""
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        score = scorer._calculate_flow_score("005930")
        assert score == 0

    @patch('src.collectors.news_collector.NewsCollector')
    @patch('src.analysis.news_scorer.NewsScorer')
    def test_news_score_without_collector(self, mock_news_scorer, mock_news_collector):
        """News collector mock을 사용한 뉴스 점수 테스트"""
        from services.signal_engine.scorer import SignalScorer

        # Mock 설정: 뉴스 없음
        mock_collector_instance = Mock()
        mock_collector_instance.fetch_stock_news.return_value = []
        mock_collector_instance.to_dict = Mock(side_effect=lambda x: x)
        mock_news_collector.return_value = mock_collector_instance

        # NewsScorer mock
        mock_scorer_instance = Mock()
        mock_scorer_instance.calculate_daily_score.return_value = Mock(
            total_score=0, positive_count=0, negative_count=0
        )
        mock_news_scorer.return_value = mock_scorer_instance

        scorer = SignalScorer()
        score = scorer._calculate_news_score("005930")
        assert score == 0
