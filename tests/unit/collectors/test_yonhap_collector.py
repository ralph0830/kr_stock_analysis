"""
YonhapCollector 단위 테스트 (Phase 2: RED)
TDD - 연합뉴스 RSS 피드 파싱 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from requests import Response

from src.collectors.yonhap_collector import YonhapCollector


class TestYonhapRSSParsing:
    """연합뉴스 RSS 파싱 테스트 (Phase 2)"""

    @pytest.fixture
    def collector(self):
        """YonhapCollector fixture"""
        return YonhapCollector()

    @pytest.fixture
    def mock_response(self):
        """Mock 응답 fixture"""
        mock_resp = Mock(spec=Response)
        mock_resp.status_code = 200
        return mock_resp

    # RED TEST 1: 연합뉴스 RSS 피드 파싱
    @pytest.mark.red
    @patch("src.collectors.yonhap_collector.requests.Session.get")
    def test_yonhap_rss_parsing(self, mock_get, collector, mock_response):
        """
        연합뉴스 RSS 피드 파싱

        RSS XML에서 기사 제목, 링크, 날짜 추출
        """
        # 연합뉴스 RSS XML (실제 구조 기반)
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>연합뉴스 경제</title>
                <item>
                    <title>삼성전자, 4분기 실적 발표</title>
                    <link>https://www.yna.co.kr/view/AKR2026013000000051</link>
                    <description>삼성전자가 30일 4분기 실적을 발표했다...</description>
                    <pubDate>Fri, 30 Jan 2026 14:00:00 +0900</pubDate>
                    <author>연합뉴스</author>
                </item>
                <item>
                    <title>SK하이닉스, HBM 생산 확대</title>
                    <link>https://www.yna.co.kr/view/AKR2026013000000052</link>
                    <description>SK하이닉스가 HBM 생산을 확대한다...</description>
                    <pubDate>Fri, 30 Jan 2026 13:30:00 +0900</pubDate>
                    <author>연합뉴스</author>
                </item>
            </channel>
        </rss>
        """

        mock_response.text = rss_xml
        mock_get.return_value = mock_response

        articles = collector.fetch_rss_news(max_articles=10)

        assert len(articles) >= 2, "최소 2개의 기사가 추출되어야 함"
        assert articles[0]["title"] == "삼성전자, 4분기 실적 발표"
        assert articles[0]["url"] == "https://www.yna.co.kr/view/AKR2026013000000051"
        assert articles[0]["source"] == "연합뉴스"

    # RED TEST 2: URL 추출 검증
    @pytest.mark.red
    @patch("src.collectors.yonhap_collector.requests.Session.get")
    def test_extract_article_urls(self, mock_get, collector, mock_response):
        """
        RSS 피드에서 기사 URL 추출

        연합뉴스 기사 URL 형식 확인
        """
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>테스트 기사</title>
                    <link>https://www.yna.co.kr/view/AKR2026013000000051</link>
                    <pubDate>Fri, 30 Jan 2026 14:00:00 +0900</pubDate>
                </item>
            </channel>
        </rss>
        """

        mock_response.text = rss_xml
        mock_get.return_value = mock_response

        # _wait_for_rate_limit mock
        with patch.object(collector, "_wait_for_rate_limit"):
            articles = collector.fetch_rss_news(max_articles=10)

        assert len(articles) > 0, "기사가 추출되어야 함"
        url = articles[0]["url"]
        assert url.startswith("https://www.yna.co.kr/"), \
            f"URL이 연합뉴스 도메인이어야 함: {url}"

    # RED TEST 3: 날짜 파싱
    @pytest.mark.red
    def test_parse_rfc822_date(self, collector):
        """
        RFC 822 날짜 포맷 파싱

        RSS pubDate 형식: "Fri, 30 Jan 2026 14:00:00 +0900"
        """
        date_str = "Fri, 30 Jan 2026 14:00:00 +0900"
        parsed = collector._parse_rss_date(date_str)

        assert isinstance(parsed, datetime), "datetime 객체를 반환해야 함"
        assert parsed.year == 2026
        assert parsed.month == 1
        assert parsed.day == 30
        assert parsed.hour == 14

    # RED TEST 4: 종목별 뉴스 검색
    @pytest.mark.red
    @patch("src.collectors.yonhap_collector.requests.Session.get")
    def test_fetch_ticker_news(self, mock_get, collector, mock_response):
        """
        종목별 연합뉴스 검색

        삼성전자 관련 뉴스 필터링
        """
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>삼성전자, 실적 호조</title>
                    <link>https://www.yna.co.kr/view/AKR2026013000000051</link>
                    <pubDate>Fri, 30 Jan 2026 14:00:00 +0900</pubDate>
                </item>
                <item>
                    <title>LG전자, 신제품 출시</title>
                    <link>https://www.yna.co.kr/view/AKR2026013000000052</link>
                    <pubDate>Fri, 30 Jan 2026 13:00:00 +0900</pubDate>
                </item>
            </channel>
        </rss>
        """

        mock_response.text = rss_xml
        mock_get.return_value = mock_response

        # _wait_for_rate_limit mock
        with patch.object(collector, "_wait_for_rate_limit"):
            articles = collector.fetch_ticker_news("005930", days=7, max_articles=10)

        # 삼성전자 관련 기사만 필터링
        assert all("삼성전자" in a["title"] for a in articles), \
            "삼성전자 관련 기사만 추출되어야 함"


class TestETFNewsCollector:
    """ETF 관련 뉴스 크롤러 테스트 (Phase 2)"""

    @pytest.fixture
    def collector(self):
        """ETFNewsCollector fixture"""
        from src.collectors.etfnews_collector import ETFNewsCollector
        return ETFNewsCollector()

    @pytest.fixture
    def mock_response(self):
        """Mock 응답 fixture"""
        mock_resp = Mock(spec=Response)
        mock_resp.status_code = 200
        return mock_resp

    # RED TEST 5: ETF 뉴스 파싱
    @pytest.mark.red
    @patch("src.collectors.etfnews_collector.requests.Session.get")
    def test_etf_news_parsing(self, mock_get, collector, mock_response):
        """
        ETF 관련 뉴스 파싱

        ETF 관련 키워드가 포함된 뉴스 추출
        """
        html = """
        <html>
        <body>
            <div class="news_list">
                <div class="item">
                    <a href="https://news.etoday.com/etf/article1.html">
                        TIGER ETF, 자산 1조 돌파
                    </a>
                    <span class="date">2026-01-30</span>
                </div>
                <div class="item">
                    <a href="https://news.etoday.com/etf/article2.html">
                        KODEX ETF, 시장 점유율 1위
                    </a>
                    <span class="date">2026-01-30</span>
                </div>
            </div>
        </body>
        </html>
        """

        mock_response.text = html
        mock_get.return_value = mock_response

        articles = collector.fetch_etf_news(max_articles=10)

        assert len(articles) >= 2, "최소 2개의 ETF 뉴스가 추출되어야 함"
        assert any("TIGER" in a["title"] for a in articles), "TIGER ETF 뉴스가 있어야 함"
        assert any("KODEX" in a["title"] for a in articles), "KODEX ETF 뉴스가 있어야 함"

    # RED TEST 6: ETF 키워드 필터링
    @pytest.mark.red
    @pytest.mark.red
    def test_etf_keyword_filtering(self, collector):
        """
        ETF 관련 키워드 필터링

        ETF, TIGER, KODEX, SOL 등 키워드 포함 기사만 추출
        """
        test_titles = [
            ("TIGER 200 ETF, 상승", True),
            ("KODEX 반도체 ETF, 거래량 증가", True),
            ("SOL 금리 선물 ETF, 운용 성과", True),
            ("삼성전자, 실적 발표", False),  # ETF 관련 아님
            ("SK하이닉스, HBM 개발", False),  # ETF 관련 아님
        ]

        for title, is_etf in test_titles:
            result = collector._is_etf_related(title)
            assert result == is_etf, \
                f"'{title}'는 ETF 관련: {is_etf}, 실제: {result}"

    # RED TEST 7: ETF 뉴스 URL 형식
    @pytest.mark.red
    @patch("src.collectors.etfnews_collector.requests.Session.get")
    def test_etf_news_url_format(self, mock_get, collector, mock_response):
        """
        ETF 뉴스 URL 형식 검증
        """
        html = """
        <html>
        <body>
            <div class="news_list">
                <div class="item">
                    <a href="https://news.etoday.com/etf/article1.html">
                        ETF 뉴스
                    </a>
                </div>
            </div>
        </body>
        </html>
        """

        mock_response.text = html
        mock_get.return_value = mock_response

        articles = collector.fetch_etf_news(max_articles=10)

        if len(articles) > 0:
            url = articles[0]["url"]
            assert url.startswith("http"), "URL은 http로 시작해야 함"
            assert "etf" in url.lower() or "etf" in url.lower(), \
                "ETF 뉴스 URL에는 etf가 포함되어야 함"
