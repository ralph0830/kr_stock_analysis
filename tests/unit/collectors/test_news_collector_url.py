"""
NewsCollector URL 추출 단위 테스트 (Phase 1: RED)
TDD - 실제 뉴스 기사 URL 추출 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from requests import Response

from src.collectors.news_collector import NewsCollector, NewsArticle


class TestNaverNewsURLExtraction:
    """네이버 뉴스 URL 추출 테스트 (Phase 1)"""

    @pytest.fixture
    def collector(self):
        """NewsCollector fixture"""
        return NewsCollector()

    @pytest.fixture
    def mock_response(self):
        """Mock 응답 fixture"""
        mock_resp = Mock(spec=Response)
        mock_resp.status_code = 200
        return mock_resp

    # RED TEST 1: 실제 네이버 뉴스 기사 URL 형식 검증
    @pytest.mark.red
    def test_naver_news_url_format_is_valid(self, collector):
        """
        네이버 뉴스 URL이 올바른 형식인지 확인

        실제 뉴스 URL은 https://n.news.naver.com/mnews/article/{office_id}/{article_id}
        형식이어야 함
        """
        # 올바른 형식의 URL
        valid_url = "https://n.news.naver.com/mnews/article/052/0002308140"

        # URL 형식 검증 함수가 있어야 함
        is_valid = collector._is_valid_naver_news_url(valid_url)

        assert is_valid is True, f"URL {valid_url}은 올바른 네이버 뉴스 URL이어야 함"

    @pytest.mark.red
    def test_naver_news_url_format_invalid(self, collector):
        """올바르지 않은 URL 형식 거부"""
        invalid_urls = [
            "https://news.naver.com/main/main.nhn?mode=LSD&mid=shm&sid1=001",  # 네이버 메인
            "https://finance.naver.com/item/news_news.nhn?code=005930",  # 금융 페이지
            "https://example.com/news/123",  # 다른 도메인
        ]

        for url in invalid_urls:
            is_valid = collector._is_valid_naver_news_url(url)
            assert is_valid is False, f"URL {url}은 올바른 네이버 뉴스 기사 URL이 아님"

    # RED TEST 2: 검색 결과에서 실제 기사 URL 추출
    @pytest.mark.red
    @patch("src.collectors.news_collector.requests.Session.get")
    def test_extract_article_urls_from_search_results(self, mock_get, collector, mock_response):
        """
        네이버 뉴스 검색 결과 HTML에서 실제 기사 URL 추출

        검색 결과 HTML에서 https://n.news.naver.com/mnews/article/...
        형식의 링크를 추출해야 함
        """
        # 네이버 뉴스 검색 결과 HTML (실제 구조 기반)
        html = """
        <html>
        <body>
        <div class="news_area">
            <a href="https://n.news.naver.com/mnews/article/052/0002308140" class="news_tit">
                삼성전자, 4분기 실적 발표
            </a>
            <a href="https://n.news.naver.com/mnews/article/088/0000994665" class="news_tit">
                삼성전자 주가 상승
            </a>
            <a href="https://finance.naver.com/item/news_news.nhn?code=005930">
                금융 페이지 링크 (무시해야 함)
            </a>
        </div>
        </body>
        </html>
        """

        mock_response.text = html
        mock_get.return_value = mock_response

        urls = collector._extract_naver_news_urls("삼성전자")

        # 실제 기사 URL만 추출되었는지 확인
        assert len(urls) >= 2, "최소 2개의 뉴스 URL이 추출되어야 함"
        assert all(url.startswith("https://n.news.naver.com/mnews/article/") for url in urls), \
            "모든 URL이 올바른 네이버 뉴스 형식이어야 함"

    # RED TEST 3: 중복 URL 제거
    @pytest.mark.red
    @patch("src.collectors.news_collector.requests.Session.get")
    def test_duplicate_urls_removed(self, mock_get, collector, mock_response):
        """검색 결과에서 중복 URL 제거"""
        html = """
        <html>
        <body>
        <a href="https://n.news.naver.com/mnews/article/052/0002308140">뉴스 1</a>
        <a href="https://n.news.naver.com/mnews/article/052/0002308140">뉴스 1 (중복)</a>
        <a href="https://n.news.naver.com/mnews/article/088/0000994665">뉴스 2</a>
        </body>
        </html>
        """

        mock_response.text = html
        mock_get.return_value = mock_response

        urls = collector._extract_naver_news_urls("삼성전자")

        assert len(urls) == 2, "중복 URL이 제거되어 2개여야 함"
        assert len(set(urls)) == len(urls), "URL 리스트에 중복이 없어야 함"

    # RED TEST 4: 기사 제목과 URL 함께 추출
    @pytest.mark.red
    @patch("src.collectors.news_collector.requests.Session.get")
    def test_extract_title_and_url_pairs(self, mock_get, collector):
        """
        기사 제목과 URL을 쌍으로 추출

        반환 형식: {"title": "...", "url": "..."}
        """
        # 검색 결과 HTML
        search_html = """
        <html>
        <body>
        <a href="https://n.news.naver.com/mnews/article/052/0002308140">삼성전자 뉴스</a>
        </body>
        </html>
        """

        # Mock 응답 생성
        search_response = Mock()
        search_response.text = search_html
        search_response.status_code = 200
        search_response.raise_for_status = Mock()

        mock_get.return_value = search_response

        # _fetch_article_details를 mock하여 기사 상세 정보 반환
        mock_article_details = {
            "title": "삼성전자, 4분기 영업이익 시상초정 달성",
            "url": "https://n.news.naver.com/mnews/article/052/0002308140",
            "source": "연합뉴스",
            "published_at": "2024-01-30T14:00:00",
            "content": "삼성전자가 4분기 영업이익 시상초정을 달성했습니다."
        }

        # _wait_for_rate_limit와 _fetch_article_details mock
        with patch.object(collector, "_wait_for_rate_limit"), \
             patch.object(collector, "_fetch_article_details", return_value=mock_article_details):
            articles = collector._fetch_naver_news_with_urls("삼성전자", days=7, max_articles=10)

        assert len(articles) > 0, "뉴스 기사가 추출되어야 함"
        assert articles[0]["url"] == "https://n.news.naver.com/mnews/article/052/0002308140"
        assert "삼성전자" in articles[0]["title"] or "영업이익" in articles[0]["title"]

    # RED TEST 5: office_id와 article_id 추출
    @pytest.mark.red
    def test_extract_office_and_article_id(self, collector):
        """
        URL에서 office_id와 article_id 추출

        URL: https://n.news.naver.com/mnews/article/052/0002308140
        office_id: 052
        article_id: 0002308140
        """
        url = "https://n.news.naver.com/mnews/article/052/0002308140"

        office_id, article_id = collector._parse_naver_news_url(url)

        assert office_id == "052", f"office_id는 '052'여야 함, 실제: {office_id}"
        assert article_id == "0002308140", f"article_id는 '0002308140'여야 함, 실제: {article_id}"

    # RED TEST 6: 최신 뉴스 우선 정렬
    @pytest.mark.red
    @patch("src.collectors.news_collector.requests.Session.get")
    def test_latest_news_first(self, mock_get, collector):
        """최신 뉴스가 먼저 오도록 정렬"""
        # 검색 결과 HTML (두 개의 뉴스 URL 포함)
        search_html = """
        <html>
        <body>
        <a href="https://n.news.naver.com/mnews/article/052/0002308140">오늘 뉴스</a>
        <a href="https://n.news.naver.com/mnews/article/088/0000994665">어제 뉴스</a>
        </body>
        </html>
        """

        search_response = Mock()
        search_response.text = search_html
        search_response.status_code = 200
        search_response.raise_for_status = Mock()

        mock_get.return_value = search_response

        # 두 기사의 상세 정보 (다른 날짜)
        mock_article_1 = {
            "title": "오늘 뉴스",
            "url": "https://n.news.naver.com/mnews/article/052/0002308140",
            "source": "언론사1",
            "published_at": "2024-01-30T14:00:00",
            "content": "내용1"
        }

        mock_article_2 = {
            "title": "어제 뉴스",
            "url": "https://n.news.naver.com/mnews/article/088/0000994665",
            "source": "언론사2",
            "published_at": "2024-01-29T10:00:00",
            "content": "내용2"
        }

        # _fetch_article_details가 호출될 때마다 다른 기사 반환
        with patch.object(collector, "_wait_for_rate_limit"), \
             patch.object(collector, "_fetch_article_details", side_effect=[mock_article_1, mock_article_2]):
            articles = collector._fetch_naver_news_with_urls("삼성전자", days=7, max_articles=10)

        assert len(articles) >= 2, "최소 2개의 기사가 필요함"

        # 날짜 내림차순 (최신 먼저)
        first_date = datetime.fromisoformat(articles[0].get("published_at", ""))
        second_date = datetime.fromisoformat(articles[1].get("published_at", ""))

        assert first_date >= second_date, "최신 뉴스가 먼저 나와야 함"


class TestNaverNewsURLValidation:
    """네이버 뉴스 URL 유효성 검증 테스트"""

    @pytest.fixture
    def collector(self):
        return NewsCollector()

    @pytest.mark.red
    def test_valid_naver_news_url_patterns(self, collector):
        """유효한 네이버 뉴스 URL 패턴"""
        valid_urls = [
            "https://n.news.naver.com/mnews/article/052/0002308140",
            "https://n.news.naver.com/mnews/article/001/00123456",
            "https://n.news.naver.com/mnews/article/421/0001234567",
        ]

        for url in valid_urls:
            assert collector._is_valid_naver_news_url(url), f"{url}은 윚한 URL이어야 함"

    @pytest.mark.red
    def test_invalid_naver_news_url_patterns(self, collector):
        """윚지 않은 URL 패턴"""
        invalid_urls = [
            "https://news.naver.com/main/read.nhn?mode=LSD&mid=shm&sid1=101",
            "https://finance.naver.com/item/news_news.nhn",
            "https://m.news.naver.com/mnews/article/052/0002308140",  # m.news도 허용하지 않음
            "https://example.com/article/123",
            "not_a_url",
            "",
        ]

        for url in invalid_urls:
            assert not collector._is_valid_naver_news_url(url), f"{url}은 윚지 않은 URL이어야 함"
