"""
NewsCollector ELW Tests (TDD: RED Phase)
ELW 티커 뉴스 수집 테스트

Phase 3: RED - 실패하는 테스트 먼저 작성
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.collectors.news_collector import NewsCollector, NewsArticle


class TestNewsCollectorELW:
    """ELW 티커 뉴스 수집 테스트"""

    @pytest.fixture
    def collector(self):
        """NewsCollector 인스턴스"""
        return NewsCollector()

    def test_is_elw_ticker(self, collector):
        """ELW 티커 식별 테스트"""
        from services.chatbot.ticker_parser import get_ticker_parser

        parser = get_ticker_parser()

        # Type 1 ELW
        assert parser.is_elw("0001A0") is True

        # Type 2 ELW
        assert parser.is_elw("005930A") is True

        # 표준 티커
        assert parser.is_elw("005930") is False

    def test_fetch_stock_news_elw_uses_search_url(self, collector):
        """ELW 티커는 네이버 검색 URL 사용"""
        with patch.object(collector, '_extract_naver_news_urls') as mock_extract:
            mock_extract.return_value = [
                "https://n.news.naver.com/mnews/article/001/0001234567"
            ]

            with patch.object(collector, '_fetch_article_details') as mock_details:
                mock_details.return_value = {
                    "title": "테스트 뉴스",
                    "url": "https://n.news.naver.com/mnews/article/001/0001234567",
                    "source": "테스트언론사",
                    "published_at": datetime.now().isoformat(),
                    "content": "테스트 내용",
                }

                # ELW 티커 Type 1
                collector.fetch_stock_news("0001A0", days=7, max_articles=5)

                # 검색 URL이 사용되어야 함
                mock_extract.assert_called_once()
                call_args = mock_extract.call_args
                query = call_args[0][0] if call_args[0] else call_args[1].get('query', '')
                # 검색어가 티커이거나 티커+ELW 조합이어야 함
                assert "0001A0" in query or "0001" in query

    def test_fetch_stock_news_elw_no_results(self, collector):
        """ELW 티커 뉴스가 없을 때 빈 리스트 반환"""
        with patch.object(collector, '_extract_naver_news_urls') as mock_extract:
            mock_extract.return_value = []

            articles = collector.fetch_stock_news("0001A0", days=7, max_articles=5)

            assert articles == []

    def test_fetch_stock_news_standard_ticker_unchanged(self, collector):
        """표준 티커는 기존 로직 사용 (회귀 테스트)"""
        with patch.object(collector, '_fetch_naver_news') as mock_naver:
            mock_naver.return_value = [
                NewsArticle(
                    title="삼성전자 뉴스",
                    content="내용",
                    source="네이버뉴스",
                    url="https://n.news.naver.com/mnews/article/001/0001234567",
                    published_at=datetime.now(),
                    ticker="005930",
                )
            ]

            articles = collector.fetch_stock_news("005930", days=7, max_articles=5)

            # 표준 뉴스 수집 메서드가 호출되어야 함
            mock_naver.assert_called_once()
            assert len(articles) > 0

    def test_elw_naver_search_url_format(self, collector):
        """네이버 뉴스 검색 URL 형식 확인"""
        from urllib.parse import urlparse, parse_qs

        # ELW 티커에 대한 검색 URL 생성
        ticker = "0001A0"
        search_url = f"https://search.naver.com/search.naver?where=news&query={ticker}"

        parsed = urlparse(search_url)
        params = parse_qs(parsed.query)

        assert params["where"][0] == "news"
        assert "0001A0" in params["query"][0]

    def test_extract_naver_news_urls_from_search(self, collector):
        """네이버 검색 결과에서 뉴스 URL 추출"""
        mock_html = """
        <html>
            <body>
                <a href="https://n.news.naver.com/mnews/article/001/0001234567">기사1</a>
                <a href="https://n.news.naver.com/mnews/article/002/0001234568">기사2</a>
                <a href="https://example.com/not-naver">다른사이트</a>
            </body>
        </html>
        """

        with patch.object(collector.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            urls = collector._extract_naver_news_urls("0001A0", max_results=10)

            # 네이버 뉴스 URL만 추출되어야 함
            assert len(urls) == 2
            assert all(url.startswith("https://n.news.naver.com/") for url in urls)
