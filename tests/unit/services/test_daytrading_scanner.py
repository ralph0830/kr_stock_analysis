"""
Unit Tests for Daytrading Scanner
TDD: Red-Green-Refactor Cycle

Phase 1: Backend Foundation Tests
- Health check endpoint
- Pydantic models validation
"""

import pytest
from datetime import datetime
from pydantic import ValidationError


# =============================================================================
# Test Models (Pydantic)
# These tests will FAIL until we implement the models
# =============================================================================

class TestScanRequestModel:
    """ScanRequest Pydantic 모델 테스트"""

    def test_scan_request_기본값_검증(self):
        """ScanRequest 기본값: market='KOSPI', limit=50"""
        # Arrange & Act & Assert
        from services.daytrading_scanner.models.daytrading import ScanRequest

        request = ScanRequest()
        assert request.market == "KOSPI"
        assert request.limit == 50

    def test_scan_request_kosdaq_생성(self):
        """ScanRequest KOSDAQ market 생성"""
        from services.daytrading_scanner.models.daytrading import ScanRequest

        request = ScanRequest(market="KOSDAQ", limit=30)
        assert request.market == "KOSDAQ"
        assert request.limit == 30

    def test_scan_request_limit_최소값_검증(self):
        """ScanRequest limit 최소값: 1"""
        from services.daytrading_scanner.models.daytrading import ScanRequest

        request = ScanRequest(market="KOSPI", limit=1)
        assert request.limit == 1

    def test_scan_request_limit_최대값_검증(self):
        """ScanRequest limit 최대값: 100"""
        from services.daytrading_scanner.models.daytrading import ScanRequest

        request = ScanRequest(market="KOSPI", limit=100)
        assert request.limit == 100

    def test_scan_request_limit_0_유효성에러(self):
        """ScanRequest limit=0 → ValidationError"""
        from services.daytrading_scanner.models.daytrading import ScanRequest

        with pytest.raises(ValidationError):
            ScanRequest(market="KOSPI", limit=0)

    def test_scan_request_limit_101_유효성에러(self):
        """ScanRequest limit=101 → ValidationError"""
        from services.daytrading_scanner.models.daytrading import ScanRequest

        with pytest.raises(ValidationError):
            ScanRequest(market="KOSPI", limit=101)

    def test_scan_request_invalid_market_에러(self):
        """ScanRequest 잘못된 market → ValidationError"""
        from services.daytrading_scanner.models.daytrading import ScanRequest

        with pytest.raises(ValidationError):
            ScanRequest(market="INVALID", limit=10)


class TestScanResponseModel:
    """ScanResponse Pydantic 모델 테스트"""

    def test_scan_response_생성(self):
        """ScanResponse 생성 성공"""
        from services.daytrading_scanner.models.daytrading import (
            ScanResponse, ScanResponseData, CandidateDataWithScore
        )

        candidates = [
            CandidateDataWithScore(
                ticker="005930",
                name="삼성전자",
                price=72000,
                change_rate=2.5,
                volume=15000000,
                avg_volume=8000000,
                volume_ratio=1.88,
                total_score=90,
                grade="S"
            )
        ]

        data = ScanResponseData(
            candidates=candidates,
            scan_time="2026-02-04T14:30:00+09:00",
            count=1
        )

        response = ScanResponse(
            success=True,
            data=data
        )

        assert response.success is True
        assert response.data.count == 1
        assert len(response.data.candidates) == 1
        assert response.data.candidates[0].ticker == "005930"


class TestHealthCheckResponse:
    """HealthCheckResponse 모델 테스트"""

    def test_health_check_response_기본값(self):
        """HealthCheckResponse 기본값 검증"""
        from services.daytrading_scanner.models.daytrading import HealthCheckResponse

        response = HealthCheckResponse(
            status="healthy",
            service="daytrading-scanner",
            version="1.0.0"
        )

        assert response.status == "healthy"
        assert response.service == "daytrading-scanner"
        assert response.version == "1.0.0"


# =============================================================================
# Test FastAPI App (Health Check)
# These tests will FAIL until we implement the app
# =============================================================================

class TestHealthCheckEndpoint:
    """Health Check Endpoint 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from services.daytrading_scanner.main import app
        from fastapi.testclient import TestClient

        return TestClient(app)

    def test_health_check_returns_200_ok(self, client):
        """GET /health → 200 OK"""
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "daytrading-scanner"
        assert "version" in data

    def test_health_check_response_구조(self, client):
        """Health check 응답 구조 검증"""
        response = client.get("/health")

        data = response.json()
        required_fields = ["status", "service", "version"]
        for field in required_fields:
            assert field in data


class TestScanEndpoint:
    """POST /scan Endpoint 테스트 (기본 구조만 테스트)"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from services.daytrading_scanner.main import app
        from fastapi.testclient import TestClient

        return TestClient(app)

    def test_scan_endpoint_kospi_200ok(self, client):
        """POST /api/daytrading/scan with KOSPI → 200 OK"""
        # TODO: Phase 3에서 실제 구현
        # 현재는 엔드포인트만 존재 확인
        response = client.post("/api/daytrading/scan", json={"market": "KOSPI", "limit": 10})

        # 422 expected for now (not implemented yet)
        assert response.status_code in [200, 422, 501]

    def test_scan_endpoint_invalid_market_400error(self, client):
        """POST /api/daytrading/scan with invalid market → validation error"""
        response = client.post("/api/daytrading/scan", json={"market": "INVALID", "limit": 10})

        # Should fail validation
        assert response.status_code == 422
