"""
VCP Scanner API 테스트 (TDD RED Phase)

FastAPI 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock


class TestHealthEndpoint:
    """헬스체크 엔드포인트 테스트"""

    def test_health_endpoint(self):
        """/health 엔드포인트 테스트"""
        from services.vcp_scanner.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "vcp-scanner"


class TestScanEndpoint:
    """스캔 엔드포인트 테스트"""

    @patch('services.vcp_scanner.main.get_analyzer')
    def test_scan_endpoint(self, mock_get_analyzer):
        """/scan 엔드포인트 테스트"""
        from services.vcp_scanner.main import app
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer, VCPResult
        from datetime import date

        # Mock analyzer 설정
        mock_analyzer = AsyncMock(spec=VCPAnalyzer)
        mock_analyzer.scan_market.return_value = [
            VCPResult(
                ticker="005930",
                name="삼전자",
                vcp_score=85.0,
                smartmoney_score=75.0,
                total_score=80.0,
                pattern_detected=True,
                signals=["VCP 수축 감지"],
                analysis_date=date.today(),
                current_price=80000.0,
            ),
        ]
        mock_get_analyzer.return_value = mock_analyzer

        client = TestClient(app)
        response = client.post(
            "/scan",
            json={"market": "KOSPI", "top_n": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data

    @patch('services.vcp_scanner.main.get_analyzer')
    def test_scan_with_min_score_filter(self, mock_get_analyzer):
        """최소 점수 필터 테스트"""
        from services.vcp_scanner.main import app
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer, VCPResult
        from datetime import date

        # 모든 결과
        all_results = [
            VCPResult(
                ticker="005930",
                name="삼전자",
                vcp_score=85.0,
                smartmoney_score=75.0,
                total_score=80.0,
                pattern_detected=True,
                signals=[],
                analysis_date=date.today(),
            ),
            VCPResult(
                ticker="000660",
                name="SK하이닉스",
                vcp_score=40.0,
                smartmoney_score=50.0,
                total_score=45.0,
                pattern_detected=False,
                signals=[],
                analysis_date=date.today(),
            ),
        ]

        # Mock analyzer: min_score 파라미터에 따라 필터링
        def mock_scan_market(market, top_n, min_score=0.0):
            return [r for r in all_results if r.total_score >= min_score]

        mock_analyzer = AsyncMock(spec=VCPAnalyzer)
        mock_analyzer.scan_market.side_effect = mock_scan_market
        mock_get_analyzer.return_value = mock_analyzer

        client = TestClient(app)
        response = client.post(
            "/scan",
            json={"market": "KOSPI", "top_n": 10, "min_score": 50.0}
        )

        assert response.status_code == 200
        data = response.json()
        # 50점 이상만 필터링되어야 함
        assert len(data["results"]) == 1
        assert data["results"][0]["ticker"] == "005930"
        assert data["results"][0]["total_score"] == 80.0


class TestAnalyzeEndpoint:
    """단일 종목 분석 엔드포인트 테스트"""

    @patch('services.vcp_scanner.main.get_analyzer')
    def test_analyze_endpoint(self, mock_get_analyzer):
        """/analyze/{ticker} 엔드포인트 테스트"""
        from services.vcp_scanner.main import app
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer, VCPResult
        from datetime import date

        # Mock analyzer 설정
        mock_analyzer = AsyncMock(spec=VCPAnalyzer)
        mock_analyzer.analyze.return_value = VCPResult(
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
        mock_get_analyzer.return_value = mock_analyzer

        client = TestClient(app)
        response = client.get("/analyze/005930")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "005930"
        assert data["name"] == "삼성전자"
        assert "vcp_score" in data

    @patch('services.vcp_scanner.main.get_analyzer')
    def test_analyze_not_found(self, mock_get_analyzer):
        """종목을 찾을 수 없을 때 404 반환"""
        from services.vcp_scanner.main import app
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        # Mock analyzer: None 반환 (종목 없음)
        mock_analyzer = AsyncMock(spec=VCPAnalyzer)
        mock_analyzer.analyze.return_value = None
        mock_get_analyzer.return_value = mock_analyzer

        client = TestClient(app)
        response = client.get("/analyze/999999")

        assert response.status_code == 404
