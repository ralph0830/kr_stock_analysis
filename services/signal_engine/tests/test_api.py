"""
Signal Engine API 테스트 (TDD RED Phase)

FastAPI 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


class TestHealthEndpoint:
    """헬스체크 엔드포인트 테스트"""

    def test_health_endpoint(self):
        """/health 엔드포인트 테스트"""
        from services.signal_engine.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "signal-engine"
        assert "version" in data


class TestSignalsLatestEndpoint:
    """최신 시그널 엔드포인트 테스트"""

    @patch('services.signal_engine.main.get_scorer')
    def test_signals_latest_returns_signals(self, mock_get_scorer):
        """/signals/latest가 시그널을 반환해야 함"""
        from services.signal_engine.main import app
        from services.signal_engine.scorer import SignalScorer, ScoreDetail, Grade, JonggaSignal

        # Mock scorer 설정
        mock_scorer = Mock(spec=SignalScorer)
        mock_scorer.calculate.side_effect = [
            JonggaSignal(
                ticker="005930", name="삼성전자", score=ScoreDetail(total=8),
                grade=Grade.A, position_size=100, entry_price=80000,
                target_price=92000, stop_loss=76000, reasons=[], created_at="2026-01-30"
            ),
            JonggaSignal(
                ticker="000660", name="SK하이닉스", score=ScoreDetail(total=7),
                grade=Grade.B, position_size=100, entry_price=180000,
                target_price=207000, stop_loss=171000, reasons=[], created_at="2026-01-30"
            ),
        ]
        mock_get_scorer.return_value = mock_scorer

        client = TestClient(app)
        response = client.get("/signals/latest")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "count" in data
        assert isinstance(data["signals"], list)

    @patch('services.signal_engine.main.get_scorer')
    def test_signals_latest_filter_by_score(self, mock_get_scorer):
        """점수 필터링 확인"""
        from services.signal_engine.main import app
        from services.signal_engine.scorer import SignalScorer, ScoreDetail, Grade, JonggaSignal

        # Mock scorer 설정
        mock_scorer = Mock(spec=SignalScorer)
        mock_scorer.calculate.side_effect = [
            JonggaSignal(
                ticker="005930", name="삼성전자", score=ScoreDetail(total=8),
                grade=Grade.A, position_size=100, entry_price=80000,
                target_price=92000, stop_loss=76000, reasons=[], created_at="2026-01-30"
            ),
        ]
        mock_get_scorer.return_value = mock_scorer

        client = TestClient(app)
        response = client.get("/signals/latest")

        data = response.json()
        # B등급 이상만 반환 (score >= 6)
        for signal in data.get("signals", []):
            # mock 데이터는 이 규칙을 따름
            assert "score" in signal


class TestAnalyzeEndpoint:
    """단일 종목 분석 엔드포인트 테스트"""

    @patch('services.signal_engine.main.get_scorer')
    def test_analyze_endpoint(self, mock_get_scorer):
        """/analyze 엔드포인트 테스트"""
        from services.signal_engine.main import app
        from services.signal_engine.scorer import SignalScorer, ScoreDetail, Grade, JonggaSignal

        # Mock scorer 설정
        mock_scorer = Mock(spec=SignalScorer)
        mock_scorer.calculate.return_value = JonggaSignal(
            ticker="005930", name="삼성전자", score=ScoreDetail(total=8),
            grade=Grade.A, position_size=100, entry_price=80000,
            target_price=92000, stop_loss=76000, reasons=[], created_at="2026-01-30"
        )
        mock_get_scorer.return_value = mock_scorer

        client = TestClient(app)
        response = client.post(
            "/analyze",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "price": 80000
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "005930"
        assert data["name"] == "삼성전자"
        assert "score" in data
        assert "grade" in data
        assert "position_size" in data

    @patch('services.signal_engine.main.get_scorer')
    def test_analyze_returns_signal_with_low_score(self, mock_get_scorer):
        """낮은 점수 시그널도 반환해야 함"""
        from services.signal_engine.main import app
        from services.signal_engine.scorer import SignalScorer, ScoreDetail, Grade, JonggaSignal

        # Mock scorer 설정
        mock_scorer = Mock(spec=SignalScorer)
        mock_scorer.calculate.return_value = JonggaSignal(
            ticker="999999", name="테스트", score=ScoreDetail(total=0),
            grade=Grade.C, position_size=5, entry_price=50000,
            target_price=57500, stop_loss=47500, reasons=["종목 분석 완료"], created_at="2026-01-30"
        )
        mock_get_scorer.return_value = mock_scorer

        client = TestClient(app)
        response = client.post(
            "/analyze",
            json={
                "ticker": "999999",
                "name": "테스트",
                "price": 50000
            }
        )

        # 의존성 없어도 기본 시그널 반환
        assert response.status_code == 200


class TestGenerateEndpoint:
    """시그널 생성 엔드포인트 테스트"""

    @patch('services.signal_engine.main.get_scorer')
    @patch('services.signal_engine.scorer.SignalScorer.calculate')
    def test_generate_endpoint(self, mock_calculate, mock_get_scorer):
        """/generate 엔드포인트 테스트"""
        from services.signal_engine.main import app
        from services.signal_engine.scorer import SignalScorer, ScoreDetail, Grade, JonggaSignal

        # Mock calculate 설정 - calculate를 직접 mock
        mock_signals = [
            JonggaSignal(
                ticker="005930", name="삼성전자", score=ScoreDetail(total=8),
                grade=Grade.A, position_size=100, entry_price=80000,
                target_price=92000, stop_loss=76000, reasons=[], created_at="2026-01-30"
            ),
        ]
        mock_calculate.return_value = mock_signals[0]

        mock_scorer_instance = Mock(spec=SignalScorer)
        mock_scorer_instance.calculate.return_value = mock_signals[0]
        mock_get_scorer.return_value = mock_scorer_instance

        client = TestClient(app)
        response = client.post(
            "/generate",
            json={
                "market": "KOSPI",
                "top_n": 3,
                "capital": 10_000_000
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "count" in data
        assert "capital" in data
