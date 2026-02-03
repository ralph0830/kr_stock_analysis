"""
VCP Scanner 통합 테스트
실제 DB 연동이 필요한 테스트 (integration marker 사용)
"""

import pytest
import os
from datetime import date

# DB 연결 설정
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ralph_stock")


@pytest.mark.integration
class TestVCPScannerIntegration:
    """VCP Scanner DB 연동 통합 테스트"""

    @pytest.mark.asyncio
    async def test_analyzer_with_real_db(self):
        """실제 DB를 사용한 분석기 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # 실제 종목 분석 (데이터가 있다고 가정)
        result = await analyzer.analyze("005930", "삼성전자")

        # 결과가 None이 아니어야 함 (데이터가 있다면)
        # 데이터가 없을 수도 있으므로 None 체크만
        if result is not None:
            assert result.ticker == "005930"
            assert result.name == "삼성전자"
            assert 0 <= result.vcp_score <= 100
            assert 0 <= result.smartmoney_score <= 100
            assert 0 <= result.total_score <= 100

    @pytest.mark.asyncio
    async def test_get_current_price_with_real_db(self):
        """실제 DB에서 현재가 조회 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        price = await analyzer._get_current_price("005930")

        # 데이터가 있다면 float 반환
        if price is not None:
            assert isinstance(price, float)
            assert price > 0

    @pytest.mark.asyncio
    async def test_vcp_score_calculation_with_real_data(self):
        """실제 데이터로 VCP 점수 계산 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # _calculate_vcp_score 직접 호출
        score = await analyzer._calculate_vcp_score("005930")

        # 점수 범위 검증
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_smartmoney_score_calculation_with_real_data(self):
        """실제 데이터로 SmartMoney 점수 계산 테스트"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # _calculate_smartmoney_score 직접 호출
        score = await analyzer._calculate_smartmoney_score("005930")

        # 점수 범위 검증
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_scan_market_with_real_db(self):
        """실제 DB에서 시장 스캔 테스트 (소규모)"""
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()

        # 상위 5개만 스캔 (테스트 속도)
        results = await analyzer.scan_market(market="KOSPI", top_n=5, min_score=0.0)

        # 결과 검증
        assert isinstance(results, list)
        for result in results:
            assert result.ticker is not None
            assert result.name is not None
            assert 0 <= result.total_score <= 100


@pytest.mark.integration
class TestVCPScannerAPIIntegration:
    """VCP Scanner API 통합 테스트"""

    def test_health_endpoint(self):
        """헬스체크 엔드포인트 테스트"""
        from fastapi.testclient import TestClient
        from services.vcp_scanner.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_signals_endpoint(self):
        """시그널 조회 엔드포인트 테스트"""
        from fastapi.testclient import TestClient
        from services.vcp_scanner.main import app

        client = TestClient(app)
        response = client.get("/signals?limit=5&market=KOSPI")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "count" in data

    def test_analyze_endpoint(self):
        """단일 종목 분석 엔드포인트 테스트"""
        from fastapi.testclient import TestClient
        from services.vcp_scanner.main import app

        client = TestClient(app)
        response = client.get("/analyze/005930")

        # 데이터가 있으면 200, 없으면 404
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["ticker"] == "005930"
