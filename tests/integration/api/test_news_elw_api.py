"""
News API ELW Integration Tests (Phase 4)
ELW 티커 API 엔드포인트 통합 테스트
"""

import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from services.api_gateway.routes.news import router


# Test fixture
@pytest.fixture
def app():
    """FastAPI 테스트 앱"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app):
    """비동기 테스트 클라이언트"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestNewsAPIELW:
    """ELW 티커 뉴스 API 테스트"""

    @pytest.mark.asyncio
    async def test_get_news_by_elw_ticker(self, client):
        """ELW 티커로 뉴스 조회 API"""
        # ticker는 NewsCollector에서 처리하므로 mocking 필요
        from unittest.mock import patch, Mock

        mock_articles = [
            Mock(
                title="덕양에너젠 관련 뉴스",
                url="https://n.news.naver.com/mnews/article/001/0001234567",
                source="네이버뉴스",
                published_at=Mock(isoformat=lambda: "2026-01-30T10:00:00"),
            )
        ]

        with patch('src.collectors.news_collector.NewsCollector') as MockCollector:
            mock_collector_instance = Mock()
            mock_collector_instance.fetch_stock_news.return_value = mock_articles
            MockCollector.return_value = mock_collector_instance

            # ELW 티커 Type 1
            response = await client.get("/api/kr/news/0001A0")

            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "0001A0"
            assert "news" in data
            assert len(data["news"]) > 0

    @pytest.mark.asyncio
    async def test_get_news_by_elw_ticker_type2(self, client):
        """ELW 티커 Type 2로 뉴스 조회 API"""
        from unittest.mock import patch, Mock

        mock_articles = [
            Mock(
                title="삼성전자 ELW 관련 뉴스",
                url="https://n.news.naver.com/mnews/article/002/0001234568",
                source="연합뉴스",
                published_at=Mock(isoformat=lambda: "2026-01-30T11:00:00"),
            )
        ]

        with patch('src.collectors.news_collector.NewsCollector') as MockCollector:
            mock_collector_instance = Mock()
            mock_collector_instance.fetch_stock_news.return_value = mock_articles
            MockCollector.return_value = mock_collector_instance

            # ELW 티커 Type 2
            response = await client.get("/api/kr/news/005930A")

            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "005930A"

    @pytest.mark.asyncio
    async def test_get_news_by_standard_ticker_still_works(self, client):
        """표준 6자리 티커 API 여전히 작동 (회귀 테스트)"""
        from unittest.mock import patch, Mock

        mock_articles = [
            Mock(
                title="삼성전자 뉴스",
                url="https://n.news.naver.com/mnews/article/003/0001234569",
                source="이투데이",
                published_at=Mock(isoformat=lambda: "2026-01-30T12:00:00"),
            )
        ]

        with patch('src.collectors.news_collector.NewsCollector') as MockCollector:
            mock_collector_instance = Mock()
            mock_collector_instance.fetch_stock_news.return_value = mock_articles
            MockCollector.return_value = mock_collector_instance

            response = await client.get("/api/kr/news/005930")

            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "005930"
            assert len(data["news"]) == 1

    @pytest.mark.asyncio
    async def test_elw_ticker_format_for_display(self, client):
        """ELW 티커 표시 포맷 확인"""
        from services.chatbot.ticker_parser import get_ticker_parser

        parser = get_ticker_parser()

        # Type 1 ELW
        display = parser.format_for_display("0001A0")
        assert "ELW" in display

        # Type 2 ELW
        display = parser.format_for_display("005930A")
        assert "ELW" in display

        # 표준 티커
        display = parser.format_for_display("005930")
        assert display == "005930"


class TestStocksAPIELW:
    """ELW 티커 종목 API 테스트"""

    @pytest.mark.asyncio
    async def test_stocks_api_elw_fallback_response(self):
        """ELW 티커에 대한 종목 API fallback 응답 확인"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()

        # ELW 티커 Type 1
        result = retriever.search_stocks("0001A0 뉴스")

        assert len(result) > 0
        assert result[0]["ticker"] == "0001A0"
        assert result[0]["_is_fallback"] is True
        # ELW 마켓 표시
        assert "ELW" in result[0]["market"] or result[0]["market"] == "KOSDAQ/KOSDAQ"
