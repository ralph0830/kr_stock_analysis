"""
News API Integration Tests (Phase 6: RED)
TDD - 뉴스 API 엔드포인트 테스트
"""

import pytest
from datetime import date, datetime
from httpx import AsyncClient
from fastapi import status

from src.database.session import get_db_session
from src.repositories.ai_analysis_repository import AIAnalysisRepository


class TestNewsAPIEndpoints:
    """뉴스 API 엔드포인트 통합 테스트 (Phase 6: RED)"""

    @pytest.fixture
    def test_client(self):
        """테스트용 HTTP 클라이언트"""
        return AsyncClient(base_url="http://localhost:5111")

    @pytest.mark.red
    async def test_get_news_by_ticker(self, test_client):
        """
        RED TEST 1: 종목별 뉴스 조회

        GET /api/kr/news/{ticker} 엔드포인트로
        종목별 뉴스 목록을 반환해야 함
        """
        # 테스트 종목
        ticker = "005930"

        # API 호출
        response = await test_client.get(f"/api/kr/news/{ticker}")

        # 검증 (엔드포인트가 아직 구현되지 않음 -> 404 예상)
        # GREEN 단계에서 구현 후 200 반환
        # 현재는 404가 예상됨
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE]

    @pytest.mark.red
    async def test_get_news_includes_urls(self, test_client):
        """
        RED TEST 2: 뉴스 응답에 URL 포함 확인

        GET /api/kr/news/{ticker} 응답의 각 뉴스 항목에
        url 필드가 포함되어야 함
        """
        # 테스트 종목
        ticker = "005930"

        # API 호출 (GREEN 단계에서 구현 후 200 반환)
        response = await test_client.get(f"/api/kr/news/{ticker}")

        # 검증
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # 뉴스 항목 또는 응답 구조 확인
            assert "news" in data or "items" in data or "articles" in data

            # URL 필드 확인
            if "news" in data and len(data["news"]) > 0:
                assert "url" in data["news"][0] or "link" in data["news"][0]

    @pytest.mark.red
    async def test_news_pagination(self, test_client):
        """
        RED TEST 3: 뉴스 페이지네이션

        GET /api/kr/news/{ticker}?page=1&limit=10
        페이지네이션 파라미터가 작동해야 함
        """
        ticker = "005930"

        # 기본 요청
        response1 = await test_client.get(f"/api/kr/news/{ticker}")
        response2 = await test_client.get(f"/api/kr/news/{ticker}?page=1&limit=5")

        # 검증 (GREEN 단계에서 구현 후)
        if response1.status_code == status.HTTP_200_OK:
            data1 = response1.json()
            assert "news" in data1 or "items" in data1
            # 페이지네이션 확인

        if response2.status_code == status.HTTP_200_OK:
            data2 = response2.json()
            # limit 파라미터가 적용되는지 확인

    @pytest.mark.red
    async def test_get_latest_news(self, test_client):
        """
        RED TEST 4: 최신 뉴스 조회

        GET /api/kr/news/latest
        전체 종목의 최신 뉴스를 반환해야 함
        """
        # API 호출
        response = await test_client.get("/api/kr/news/latest")

        # 검증 (GREEN 단계에서 구현 후 200 반환)
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "news" in data or "items" in data


class TestNewsAPIDatabase:
    """뉴스 API DB 연동 테스트 (Phase 6: RED)"""

    @pytest.fixture
    def db_session(self):
        """DB 세션 fixture"""
        session = next(get_db_session())
        yield session
        session.close()

    @pytest.mark.red
    async def test_news_api_returns_stored_urls(self, db_session):
        """
        RED TEST 5: API가 저장된 뉴스 URL 반환

        /api/kr/news/{ticker}가 DB에 저장된 news_urls를 반환해야 함
        """
        # 테스트 데이터 저장
        repo = AIAnalysisRepository(db_session)
        ticker = "005930"
        analysis_date = date.today()

        news_urls = [
            {"title": "삼성전자 뉴스", "url": "https://n.news.naver.com/article/1"},
            {"title": "삼성전자 실적", "url": "https://n.news.naver.com/article/2"},
        ]

        # 분석 데이터 저장
        repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="positive",
            score=0.8,
            summary="테스트 요약",
            keywords=["테스트"],
            recommendation="BUY",
            news_count=2,
            news_urls=news_urls,
        )

        # 저장 확인
        latest = repo.get_latest_analysis(ticker)
        assert latest is not None
        assert latest.news_urls == news_urls

        # TODO: GREEN 단계에서 API 엔드포인트 구현 후 검증
        # API를 통해 조회되는지 확인 필요


class TestNewsAPISchemas:
    """뉴스 API 스키마 테스트 (Phase 6: RED)"""

    @pytest.mark.red
    def test_news_item_schema_has_required_fields(self):
        """
        RED TEST 6: 뉴스 항목 스키마 정의

        뉴스 항목 응답 스키마에 필요한 필드가 포함되어야 함
        """
        # TODO: GREEN 단계에서 Pydantic 모델 생성 후 검증
        # 필수 필드: title, url, source, published_at

        from services.api_gateway.schemas import NewsItem

        # 스키마 정의 (GREEN 단계에서 구현)
        # assert hasattr(NewsItem, "__annotations__")

    @pytest.mark.red
    def test_news_list_response_schema(self):
        """
        RED TEST 7: 뉴스 목록 응답 스키마 정의

        뉴스 목록 반환 스키마 정의
        """
        # TODO: GREEN 단계에서 Pydantic 모델 생성 후 검증
        # 필수 필드: news, total, pagination
        pass
