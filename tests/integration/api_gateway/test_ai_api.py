"""
AI API Integration Tests
TDD GREEN Phase - Tests should pass with implementation
"""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date
from sqlalchemy.orm import Session

from services.api_gateway.main import app
from src.database.session import get_db_session
from src.database.models import Stock, AIAnalysis


@pytest.fixture
async def client(test_db_session):
    """Test Client Fixture"""
    # Dependency override
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_stock(test_db_session: Session):
    """Sample Stock 데이터"""
    # 기존 데이터 삭제
    test_db_session.query(AIAnalysis).filter(AIAnalysis.ticker == "005930").delete()
    test_db_session.query(Stock).filter(Stock.ticker == "005930").delete()
    test_db_session.commit()

    stock = Stock(
        ticker="005930",
        name="삼성전자",
        market="KOSPI",
        sector="반도체",
        market_cap=500000000000000,
    )
    test_db_session.add(stock)
    test_db_session.commit()
    test_db_session.refresh(stock)
    return stock


@pytest.fixture
def sample_ai_analysis(test_db_session: Session, sample_stock: Stock):
    """Sample AI Analysis 데이터"""
    analysis = AIAnalysis(
        ticker=sample_stock.ticker,
        analysis_date=date.today(),
        sentiment="positive",
        score=0.75,
        confidence=0.85,
        summary="반도체 수요 증가로 실적 호조 기대",
        keywords=["반도체", "수요", "실적"],
        recommendation="BUY",
        news_count=5,
    )
    test_db_session.add(analysis)
    test_db_session.commit()
    test_db_session.refresh(analysis)
    return analysis


class TestAIAPIIntegration:
    """AI API 통합 테스트"""

    async def test_ai_summary_api_success(
        self, client: AsyncClient, sample_ai_analysis
    ):
        """종목 AI 요약 API - 성공"""
        response = await client.get(f"/api/kr/ai-summary/{sample_ai_analysis.ticker}")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == sample_ai_analysis.ticker
        assert data["sentiment"] == "positive"

    async def test_ai_summary_api_not_found(self, client: AsyncClient):
        """종목 AI 요약 API - 종목 없음"""
        response = await client.get("/api/kr/ai-summary/999999")

        assert response.status_code == 404

    async def test_ai_summary_api_no_analysis(self, client: AsyncClient, sample_stock):
        """종목 AI 요약 API - 분석 없음"""
        response = await client.get(f"/api/kr/ai-summary/{sample_stock.ticker}")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == sample_stock.ticker
        assert data["sentiment"] is None

    async def test_ai_analysis_api(self, client: AsyncClient):
        """전체 AI 분석 API"""
        response = await client.get("/api/kr/ai-analysis")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    async def test_ai_history_dates_api(self, client: AsyncClient):
        """분석 가능 날짜 API"""
        response = await client.get("/api/kr/ai-history-dates")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    async def test_ai_history_by_date_api(
        self, client: AsyncClient, sample_ai_analysis
    ):
        """특정 날짜 분석 API"""
        date_str = sample_ai_analysis.analysis_date.isoformat()
        response = await client.get(f"/api/kr/ai-history/{date_str}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_trigger_analysis_api(
        self, client: AsyncClient, sample_stock
    ):
        """AI 분석 트리거 API"""
        response = await client.post(f"/api/kr/ai-analyze/{sample_stock.ticker}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["ticker"] == sample_stock.ticker

    async def test_ai_sentiment_score_range(self, client: AsyncClient):
        """감성 점수 범위 검증 (-1.0 ~ 1.0)"""
        # 먼저 분석을 생성
        await client.post("/api/kr/ai-analyze/005930")

        response = await client.get("/api/kr/ai-analysis")

        if response.status_code == 200:
            data = response.json()
            if "analyses" in data:
                for analysis in data["analyses"]:
                    score = analysis.get("score", 0)
                    assert -1.0 <= score <= 1.0

    async def test_ai_all_endpoints_implemented(
        self, client: AsyncClient, sample_stock
    ):
        """모든 AI 엔드포인트 구현 확인"""
        endpoints = [
            f"/api/kr/ai-summary/{sample_stock.ticker}",
            "/api/kr/ai-analysis",
            "/api/kr/ai-history-dates",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            # 구현되었으므로 404가 아니어야 함
            assert response.status_code != 404
