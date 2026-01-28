"""
Test Suite: VCP Scanner Service (GREEN Phase)
VCP Scanner 서비스 테스트
"""

import pytest
from httpx import AsyncClient, ASGITransport

from services.vcp_scanner.main import app
from services.vcp_scanner.vcp_analyzer import VCPAnalyzer


class TestVCPEndpoints:
    """VCP Scanner 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 엔드포인트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["service"] == "vcp-scanner"

    @pytest.mark.asyncio
    async def test_get_signals(self):
        """/signals 엔드포인트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/signals?limit=20")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    @pytest.mark.asyncio
    async def test_scan_stocks(self):
        """/scan 엔드포인트 - VCP 패턴 스캔"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/scan", json={"market": "KOSPI", "top_n": 30})

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_analyze_stock(self):
        """/analyze/{ticker} 엔드포인트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/analyze/005930")

        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "total_score" in data


class TestVCPScannerLogic:
    """VCP Scanner 비즈니스 로직 테스트"""

    @pytest.mark.asyncio
    async def test_vcp_analyzer_init(self):
        """VCP Analyzer 초기화 테스트"""
        analyzer = VCPAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_analyze_stock(self):
        """종목 분석 테스트"""
        analyzer = VCPAnalyzer()
        result = await analyzer.analyze("005930", "삼성전자")

        assert result is not None
        assert result.ticker == "005930"
        assert 0 <= result.total_score <= 100

    @pytest.mark.asyncio
    async def test_scan_market(self):
        """시장 전체 스캔 테스트"""
        analyzer = VCPAnalyzer()
        results = await analyzer.scan_market("KOSPI", top_n=10)

        assert isinstance(results, list)
        # 점수순 정렬 확인
        if len(results) > 1:
            assert results[0].total_score >= results[1].total_score


class TestVCPDatabaseIntegration:
    """VCP Scanner - Database 연동 테스트 (추후 구현)"""

    @pytest.mark.skip(reason="DB integration not implemented yet")
    def test_save_signal_to_db(self):
        """시그널 DB 저장 테스트"""
        pass

    @pytest.mark.skip(reason="DB integration not implemented yet")
    def test_get_active_signals(self):
        """활성 시그널 조회 테스트"""
        pass


class TestVCPMarketData:
    """VCP Scanner - 시장 데이터 수집 테스트 (추후 구현)"""

    @pytest.mark.skip(reason="Market data collection not implemented yet")
    @pytest.mark.asyncio
    async def test_collect_stock_data(self):
        """종목 데이터 수집 테스트"""
        pass

    @pytest.mark.skip(reason="Market data collection not implemented yet")
    @pytest.mark.asyncio
    async def test_collect_institutional_flow(self):
        """기관 매매 수급 데이터 수집 테스트"""
        pass
