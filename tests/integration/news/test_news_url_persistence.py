"""
News URL Persistence Integration Tests (Phase 3: RED)
TDD - 뉴스 수집 시 URL 저장 및 조회 테스트
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch

from src.database.session import get_db_session
from src.repositories.ai_analysis_repository import AIAnalysisRepository
from src.collectors.news_collector import NewsCollector
from services.chatbot.retriever import KnowledgeRetriever


class TestNewsURLPersistence:
    """뉴스 URL 저장 영속성 테스트 (Phase 3)"""

    @pytest.fixture
    def db_session(self):
        """DB 세션 fixture"""
        session = next(get_db_session())
        yield session
        session.close()

    @pytest.fixture
    def repo(self, db_session):
        """AIAnalysisRepository fixture"""
        return AIAnalysisRepository(db_session)

    # RED TEST 1: 뉴스 수집 시 URL 저장
    @pytest.mark.red
    def test_news_collection_saves_urls(self, repo):
        """
        뉴스 수집 후 DB에 실제 URL 저장 확인

        수집된 뉴스 기사의 URL이 AIAnalysis 테이블에 news_urls로 저장되어야 함
        """
        # 테스트용 뉴스 데이터
        ticker = "005930"
        analysis_date = date.today()

        news_urls = [
            {"title": "삼성전자 4분기 실적 발표", "url": "https://n.news.naver.com/mnews/article/052/0002308140"},
            {"title": "삼성전자 주가 상승", "url": "https://n.news.naver.com/mnews/article/088/0000994665"},
            {"title": "삼전 HBM 양산", "url": "https://n.news.naver.com/mnews/article/123/0002376871"},
        ]

        # DB에 저장
        analysis = repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="positive",
            score=0.8,
            summary="삼성전자 4분기 실적이 호조입니다.",
            keywords=["삼성전자", "실적", "HBM"],
            recommendation="BUY",
            confidence=0.8,
            news_count=len(news_urls),
            news_urls=news_urls,
        )

        # 저장된 레코드 확인
        assert analysis.news_urls is not None, "news_urls가 저장되어야 함"
        assert len(analysis.news_urls) == 3, "3개의 URL이 저장되어야 함"

        # URL 내용 확인
        saved_urls = analysis.news_urls
        assert saved_urls[0]["title"] == "삼성전자 4분기 실적 발표"
        assert saved_urls[0]["url"] == "https://n.news.naver.com/mnews/article/052/0002308140"

    # RED TEST 2: retriever에서 URL 반환
    @pytest.mark.red
    def test_retriever_returns_urls(self, repo):
        """
        Retriever가 DB에서 조회한 데이터에 URL을 포함하여 반환

        search_news() 메서드가 news_urls 필드를 포함해야 함
        """
        # 테스트 데이터 저장
        ticker = "005930"
        analysis_date = date.today()

        news_urls = [
            {"title": "삼성전자 뉴스", "url": "https://n.news.naver.com/mnews/article/052/0002308140"},
        ]

        repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="positive",
            score=0.8,
            summary="삼성전자 분석",
            keywords=["삼성전자"],
            recommendation="BUY",
            news_count=1,
            news_urls=news_urls,
        )

        # Retriever로 조회
        retriever = KnowledgeRetriever()
        news_results = retriever.search_news(ticker=ticker, limit=5)

        # URL이 포함되어 있는지 확인
        assert len(news_results) > 0, "뉴스 검색 결과가 있어야 함"

        result = news_results[0]
        assert "news_urls" in result, "결과에 news_urls 필드가 있어야 함"
        assert isinstance(result["news_urls"], list), "news_urls는 리스트여야 함"

        if len(result["news_urls"]) > 0:
            url_info = result["news_urls"][0]
            assert "url" in url_info, "URL 정보에 url 키가 있어야 함"
            assert url_info["url"] == "https://n.news.naver.com/mnews/article/052/0002308140", \
                f"저장된 URL이 반환되어야 함, 실제: {url_info['url']}"

    # RED TEST 3: 여러 뉴스 URL 중복 없이 저장
    @pytest.mark.red
    def test_multiple_news_urls_stored(self, repo):
        """
        여러 뉴스 기사의 URL이 중복 없이 저장

        동일한 analysis에 여러 news_urls가 저장될 때 중복 처리
        """
        ticker = "005930"
        analysis_date = date.today()

        news_urls = [
            {"title": "뉴스 1", "url": "https://n.news.naver.com/mnews/article/052/0001"},
            {"title": "뉴스 2", "url": "https://n.news.naver.com/mnews/article/088/0002"},
            {"title": "뉴스 3", "url": "https://n.news.naver.com/mnews/article/123/0003"},
        ]

        # 저장
        analysis = repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="positive",
            score=0.6,
            summary="분석",
            keywords=["test"],
            recommendation="HOLD",
            news_count=3,
            news_urls=news_urls,
        )

        # 중복 확인
        urls = [u["url"] for u in analysis.news_urls]
        assert len(urls) == len(set(urls)), "URL에 중복이 없어야 함"

    # RED TEST 4: 빈 news_urls 처리
    @pytest.mark.red
    def test_empty_news_urls_handling(self, repo):
        """
        news_urls가 없는 경우 빈 리스트로 저장

        뉴스가 없을 때는 빈 리스트로 저장되어야 함
        """
        ticker = "000660"
        analysis_date = date.today()

        # news_urls 없이 저장
        analysis = repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="neutral",
            score=0.0,
            summary="분석",
            keywords=[],
            recommendation="HOLD",
            news_count=0,
            news_urls=None,  # 명시적으로 None
        )

        assert analysis.news_urls == [], "news_urls는 빈 리스트여야 함"

    # RED TEST 5: news_urls로 최신 분석 조회
    @pytest.mark.red
    def test_get_latest_analysis_includes_urls(self, repo):
        """
        최신 AI 분석 조회 시 news_urls 포함

        get_latest_analysis()가 news_urls를 반환해야 함
        """
        ticker = "035420"
        analysis_date = date.today()

        news_urls = [
            {"title": "NAVER 뉴스", "url": "https://n.news.naver.com/mnews/article/016/0001"},
        ]

        repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="positive",
            score=0.7,
            summary="NAVER 분석",
            keywords=["NAVER"],
            recommendation="BUY",
            news_count=1,
            news_urls=news_urls,
        )

        # 최신 분석 조회
        latest = repo.get_latest_analysis(ticker)

        assert latest is not None, "최신 분석이 조회되어야 함"
        assert latest.news_urls is not None, "news_urls 필드가 있어야 함"
        assert len(latest.news_urls) > 0, "news_urls가 있어야 함"
        assert latest.news_urls[0]["url"] == "https://n.news.naver.com/mnews/article/016/0001"

    # RED TEST 6: news_urls 형식 검증
    @pytest.mark.red
    def test_news_urls_format_validation(self, repo):
        """
        news_urls JSON 필드 형식 검증

        저장된 news_urls가 올바른 JSONB 형식인지 확인
        """
        ticker = "005380"
        analysis_date = date.today()

        news_urls = [
            {"title": "현대차 뉴스", "url": "https://n.news.naver.com/mnews/article/052/0001"},
        ]

        analysis = repo.save_analysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment="positive",
            score=0.6,
            summary="현대차 분석",
            keywords=["현대차"],
            recommendation="BUY",
            news_count=1,
            news_urls=news_urls,
        )

        # DB에서 다시 조회하여 형식 확인
        latest = repo.get_latest_analysis(ticker)

        assert latest is not None
        assert isinstance(latest.news_urls, list), "news_urls는 리스트 타입이어야 함"

        for url_info in latest.news_urls:
            assert isinstance(url_info, dict), "각 항목은 딕셔너리여야 함"
            assert "title" in url_info, "title 키가 있어야 함"
            assert "url" in url_info, "url 키가 있어야 함"
            assert isinstance(url_info["url"], str), "url은 문자열이어야 함"


class TestChatbotShowsURLs:
    """챗봇 응답 URL 표시 테스트 (Phase 3)"""

    @pytest.fixture
    def retriever(self):
        """KnowledgeRetriever fixture"""
        return KnowledgeRetriever()

    # RED TEST 7: 챗봇 RAG 프롬프트에 URL 포함
    @pytest.mark.red
    def test_chatbot_prompt_includes_urls(self, retriever):
        """
        챗봇 RAG 프롬프트에 news_urls 포함 확인

        build_rag_prompt()가 news_urls를 컨텍스트에 포함해야 함
        """
        from services.chatbot.prompts import build_rag_prompt

        # news_urls가 포함된 mock context
        context = {
            "stocks": [
                {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "market": "KOSPI",
                    "sector": "전기/전자",
                }
            ],
            "news": [
                {
                    "summary": "삼성전자 4분기 실적이 호조입니다.",
                    "news_urls": [
                        {"title": "삼성전자 4분기 실적 발표", "url": "https://n.news.naver.com/mnews/article/052/0002308140"},
                    ],
                }
            ],
        }

        # 프롬프트 빌드
        prompt = build_rag_prompt("삼성전자 어떄?", context=context)

        # 프롬프트에 news_urls 포함 확인
        assert "news_urls" in prompt or "📰 참고 뉴스" in prompt, \
            "프롬프트에 news_urls 섹션이 있어야 함"
        assert "https://n.news.naver.com" in prompt, \
            "프롬프트에 실제 뉴스 URL이 포함되어야 함"

    # RED TEST 8: 여러 뉴스 링크 표시
    @pytest.mark.red
    def test_multiple_news_links_in_prompt(self, retriever):
        """
        여러 뉴스 링크가 마크다운 형식으로 표시

        3개의 뉴스 링크가 마크다운 링크 형식으로 변환되어야 함
        """
        from services.chatbot.prompts import build_rag_prompt

        context = {
            "news": [
                {
                    "summary": "뉴스 요약 1",
                    "news_urls": [
                        {"title": "뉴스 1", "url": "https://n.news.naver.com/article/001"},
                        {"title": "뉴스 2", "url": "https://n.news.naver.com/article/002"},
                    ],
                }
            ],
        }

        prompt = build_rag_prompt("뉴스 알려줘", context=context)

        # 마크다운 링크 형식 확인: [title](url)
        assert "[뉴스 1](https://n.news.naver.com/article/001)" in prompt, \
            "첫 번째 링크가 마크다운 형식이어야 함"
        assert "[뉴스 2](https://n.news.naver.com/article/002)" in prompt, \
            "두 번째 링크가 마크다운 형식이어야 함"

    # RED TEST 9: 빈 news_urls 처리
    @pytest.mark.red
    def test_empty_news_urls_in_prompt(self, retriever):
        """
        news_urls가 없을 때 프롬프트 처리

        뉴스 링크가 없어도 에러 없이 프롬프트가 생성되어야 함
        """
        from services.chatbot.prompts import build_rag_prompt

        context = {
            "news": [
                {
                    "summary": "분석 내용",
                    "news_urls": [],  # 빈 리스트
                }
            ],
        }

        # 에러 없이 프롬프트 생성
        prompt = build_rag_prompt("분석 결과", context=context)

        assert prompt is not None, "프롬프트가 생성되어야 함"
        assert "분석 내용" in prompt, "내용이 포함되어야 함"
