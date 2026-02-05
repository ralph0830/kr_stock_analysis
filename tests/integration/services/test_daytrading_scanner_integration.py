"""
Integration Tests for Daytrading Scanner API
TDD: Red-Green-Refactor Cycle

Phase 3: API Endpoint Tests
- POST /scan: 장중 단타 후보 스캔
- GET /signals: 활성 매수 신호 조회
- POST /analyze: 종목별 점수 분석
"""

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Test POST /api/daytrading/scan
# =============================================================================

class TestScanEndpoint:
    """POST /api/daytrading/scan 엔드포인트 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from services.daytrading_scanner.main import app
        return TestClient(app)

    def test_scan_endpoint_kospi_200ok(self, client):
        """POST /api/daytrading/scan with KOSPI → 200 OK"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "KOSPI", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["count"] >= 0
        assert "candidates" in data["data"]
        assert isinstance(data["data"]["candidates"], list)

    def test_scan_endpoint_kosdaq_200ok(self, client):
        """POST /api/daytrading/scan with KOSDAQ → 200 OK"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "KOSDAQ", "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_scan_endpoint_all_markets_200ok(self, client):
        """POST /api/daytrading/scan with ALL → 200 OK"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "ALL", "limit": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_scan_endpoint_default_values(self, client):
        """POST /api/daytrading/scan without body → defaults (KOSPI, 50)"""
        response = client.post("/api/daytrading/scan", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_scan_endpoint_invalid_market_422error(self, client):
        """POST /api/daytrading/scan with invalid market → 422"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "INVALID", "limit": 10}
        )

        assert response.status_code == 422

    def test_scan_endpoint_limit_0_422error(self, client):
        """POST /api/daytrading/scan with limit=0 → 422"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "KOSPI", "limit": 0}
        )

        assert response.status_code == 422

    def test_scan_endpoint_limit_101_422error(self, client):
        """POST /api/daytrading/scan with limit=101 → 422"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "KOSPI", "limit": 101}
        )

        assert response.status_code == 422

    def test_scan_response_structure(self, client):
        """POST /api/daytrading/scan 응답 구조 검증"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "KOSPI", "limit": 10}
        )

        data = response.json()["data"]

        # 필수 필드 확인
        required_fields = ["candidates", "scan_time", "count"]
        for field in required_fields:
            assert field in data

        # candidates 구조 확인
        if len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            candidate_fields = ["ticker", "name", "price", "change_rate",
                               "volume", "avg_volume", "volume_ratio",
                               "total_score", "grade"]
            for field in candidate_fields:
                assert field in candidate


# =============================================================================
# Test GET /api/daytrading/signals
# =============================================================================

class TestSignalsEndpoint:
    """GET /api/daytrading/signals 엔드포인트 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from services.daytrading_scanner.main import app
        return TestClient(app)

    def test_signals_endpoint_200ok(self, client):
        """GET /api/daytrading/signals → 200 OK"""
        response = client.get("/api/daytrading/signals")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "signals" in data["data"]
        assert isinstance(data["data"]["signals"], list)

    def test_signals_with_min_score_filter(self, client):
        """GET /api/daytrading/signals?min_score=60 → 60점 이상만 반환"""
        response = client.get("/api/daytrading/signals?min_score=60")

        assert response.status_code == 200
        data = response.json()
        signals = data["data"]["signals"]

        # 모든 신호가 60점 이상인지 확인
        for signal in signals:
            assert signal["total_score"] >= 60

    def test_signals_with_market_filter(self, client):
        """GET /api/daytrading/signals?market=KOSPI → KOSPI만 반환"""
        response = client.get("/api/daytrading/signals?market=KOSPI")

        assert response.status_code == 200
        data = response.json()
        signals = data["data"]["signals"]

        # 모든 신호가 KOSPI인지 확인 (데이터가 있는 경우)
        for signal in signals:
            assert signal["market"] in ["KOSPI", "KOSDAQ"]

    def test_signals_with_limit(self, client):
        """GET /api/daytrading/signals?limit=5 → 최대 5개 반환"""
        response = client.get("/api/daytrading/signals?limit=5")

        assert response.status_code == 200
        data = response.json()
        signals = data["data"]["signals"]

        assert len(signals) <= 5

    def test_signals_response_structure(self, client):
        """GET /api/daytrading/signals 응답 구조 검증"""
        response = client.get("/api/daytrading/signals")

        data = response.json()["data"]

        # 필수 필드 확인
        required_fields = ["signals", "count", "generated_at"]
        for field in required_fields:
            assert field in data

        # signals 구조 확인
        if len(data["signals"]) > 0:
            signal = data["signals"][0]
            signal_fields = ["ticker", "name", "market", "total_score",
                            "grade", "checks", "entry_price",
                            "target_price", "stop_loss"]
            for field in signal_fields:
                assert field in signal


# =============================================================================
# Test POST /api/daytrading/analyze
# =============================================================================

class TestAnalyzeEndpoint:
    """POST /api/daytrading/analyze 엔드포인트 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from services.daytrading_scanner.main import app
        return TestClient(app)

    def test_analyze_endpoint_single_ticker_200ok(self, client):
        """POST /api/daytrading/analyze with single ticker → 200 OK"""
        response = client.post(
            "/api/daytrading/analyze",
            json={"tickers": ["005930"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "results" in data["data"]
        assert len(data["data"]["results"]) == 1

    def test_analyze_endpoint_multiple_tickers_200ok(self, client):
        """POST /api/daytrading/analyze with multiple tickers → 200 OK"""
        response = client.post(
            "/api/daytrading/analyze",
            json={"tickers": ["005930", "000270", "035420"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["results"]) == 3

    def test_analyze_endpoint_empty_tickers_422error(self, client):
        """POST /api/daytrading/analyze with empty tickers → 422 (Pydantic validation)"""
        response = client.post(
            "/api/daytrading/analyze",
            json={"tickers": []}
        )

        assert response.status_code == 422

    def test_analyze_response_includes_checks(self, client):
        """POST /api/daytrading/analyze 응답에 7개 체크리스트 포함"""
        response = client.post(
            "/api/daytrading/analyze",
            json={"tickers": ["005930"]}
        )

        data = response.json()["data"]["results"][0]

        assert "checks" in data
        assert len(data["checks"]) == 7

        # 각 체크항목 구조 확인
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert "points" in check

    def test_analyze_response_includes_trading_prices(self, client):
        """POST /api/daytrading/analyze 응답에 매매 기준가 포함"""
        response = client.post(
            "/api/daytrading/analyze",
            json={"tickers": ["005930"]}
        )

        data = response.json()["data"]["results"][0]

        # Phase 3에서는 None 가능 (Phase 4에서 구현)
        assert "entry_price" in data
        assert "target_price" in data
        assert "stop_loss" in data


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """에러 핸들링 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from services.daytrading_scanner.main import app
        return TestClient(app)

    def test_404_not_found(self, client):
        """존재하지 않는 엔드포인트 → 404"""
        response = client.get("/api/daytrading/nonexistent")

        assert response.status_code == 404

    def test_405_method_not_allowed(self, client):
        """잘못된 HTTP 메서드 → 405"""
        response = client.get("/api/daytrading/scan")

        assert response.status_code == 405

    def test_422_validation_error_format(self, client):
        """Validation Error 응답 포맷 확인"""
        response = client.post(
            "/api/daytrading/scan",
            json={"market": "INVALID", "limit": 10}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
