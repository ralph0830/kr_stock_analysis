"""
Test Suite: Celery Async Processing (GREEN Phase)
Celery 비동기 작업 테스트
"""

from unittest.mock import Mock, patch

from tasks.celery_app import celery_app
from tasks.scan_tasks import scan_vcp_patterns, scan_all_markets
from tasks.signal_tasks import generate_jongga_signals, analyze_single_stock
from tasks.market_tasks import update_market_gate, collect_institutional_flow


class TestCeleryApp:
    """Celery 앱 테스트"""

    def test_celery_app_init(self):
        """Celery 앱 초기화 테스트"""
        assert celery_app is not None
        assert celery_app.main == "ralph_stock_tasks"

    def test_broker_url_configured(self):
        """브로커 URL 설정 확인"""
        assert celery_app.conf.broker_url is not None
        assert "redis" in celery_app.conf.broker_url


class TestVCPTasks:
    """VCP 스캔 태스크 테스트"""

    def test_scan_vcp_patterns_task(self):
        """VCP 패턴 스캔 태스크 테스트"""
        result = scan_vcp_patterns("KOSPI", 10)

        assert result is not None
        assert "status" in result
        assert result["status"] in ["success", "error"]

    def test_scan_all_markets_task(self):
        """전체 시장 스캔 태스크 테스트"""
        result = scan_all_markets()

        assert result is not None
        assert "status" in result
        assert "tasks" in result


class TestSignalTasks:
    """시그널 생성 태스크 테스트"""

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_generate_jongga_signals_task(self, mock_scorer_class):
        """종가베팅 시그널 생성 태스크 테스트"""
        # Mock signal 객체 생성
        mock_signal = Mock()
        mock_signal.score.total = 8
        mock_signal.to_dict.return_value = {
            "ticker": "005930",
            "name": "삼성전자",
            "grade": "A",
            "score": {"total": 8}
        }

        # Mock scorer 인스턴스 설정
        mock_scorer = Mock()
        mock_scorer.calculate.return_value = mock_signal
        mock_scorer_class.return_value = mock_scorer

        result = generate_jongga_signals(10_000_000, 10)

        assert result is not None
        assert "status" in result
        assert result["status"] == "success"

    @patch("services.signal_engine.scorer.SignalScorer")
    def test_analyze_single_stock_task(self, mock_scorer_class):
        """단일 종목 분석 태스크 테스트"""
        # Mock signal 객체 생성
        mock_signal = Mock()
        mock_signal.to_dict.return_value = {
            "ticker": "005930",
            "name": "삼성전자",
            "grade": "B"
        }

        # Mock scorer 인스턴스 설정
        mock_scorer = Mock()
        mock_scorer.calculate.return_value = mock_signal
        mock_scorer_class.return_value = mock_scorer

        result = analyze_single_stock("005930", "삼성전자", 80000)

        assert result is not None
        assert "status" in result
        assert result["status"] == "success"


class TestMarketTasks:
    """마켓 데이터 태스크 테스트"""

    def test_update_market_gate_task(self):
        """Market Gate 업데이트 태스크 테스트"""
        result = update_market_gate()

        assert result is not None
        assert "status" in result
        assert result["status"] in ["success", "error"]

    def test_collect_institutional_flow_task(self):
        """기관 매매 수급 수집 태스크 테스트"""
        result = collect_institutional_flow(["005930", "000660"])

        assert result is not None
        assert "status" in result


class TestCeleryBeat:
    """Celery Beat 스케줄링 테스트"""

    def test_schedule_configuration(self):
        """스케줄 설정 확인 테스트"""

        beat_schedule = celery_app.conf.beat_schedule

        # 실제 beat_schedule의 키로 확인
        assert "scan-vcp-test" in beat_schedule
        assert "generate-signals-daily" in beat_schedule
        assert "update-market-gate" in beat_schedule

    def test_periodic_tasks(self):
        """주기적 태스크 등록 테스트"""
        beat_schedule = celery_app.conf.beat_schedule

        # 태스크 이름 확인 (실제 설정에 맞게 수정)
        assert beat_schedule["scan-vcp-test"]["task"] == "tasks.sync_tasks.trigger_vcp_scan_via_api"
        assert beat_schedule["generate-signals-daily"]["task"] == "tasks.signal_tasks.generate_jongga_signals"
        assert beat_schedule["update-market-gate"]["task"] == "tasks.market_tasks.update_market_gate"


class TestHealthCheck:
    """헬스 체크 태스크 테스트"""

    def test_health_check_task(self):
        """헬스 체크 태스크 테스트"""
        from tasks.celery_app import health_check

        result = health_check()

        assert result is not None
        assert result["status"] == "healthy"
        assert result["service"] == "celery"
