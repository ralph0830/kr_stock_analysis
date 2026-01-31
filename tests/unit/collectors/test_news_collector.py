"""
NewsCollector 단위 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from requests import Response

from src.collectors.news_collector import NewsCollector, NewsArticle


class TestNewsCollector:
    """NewsCollector 단위 테스트"""

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

    def test_init(self, collector):
        """초기화 테스트"""
        assert collector.session is not None
        assert "User-Agent" in collector.session.headers

    def test_wait_for_rate_limit(self, collector):
        """Rate limiting 테스트"""
        import time

        start = time.time()
        collector._wait_for_rate_limit()
        first_wait = time.time() - start

        # 첫 번째 요청은 대기하지 않음
        assert first_wait < 0.1

        start = time.time()
        collector._wait_for_rate_limit()
        second_wait = time.time() - start

        # 두 번째 요청은 REQUEST_INTERVAL(1초)만큼 대기
        assert second_wait >= 0.9  # 약간의 오차 허용

    @patch.object(NewsCollector, "_fetch_naver_news")
    @patch.object(NewsCollector, "_fetch_daum_news")
    @patch.object(NewsCollector, "_fetch_yonhap_news")
    def test_fetch_stock_news(
        self,
        mock_yonhap,
        mock_daum,
        mock_naver,
        collector,
    ):
        """종목 뉴스 수집 테스트"""
        # Mock 설정
        mock_articles = [
            NewsArticle(
                title="테스트 뉴스 1",
                content="내용 1",
                source="테스트 언론사",
                url="https://example.com/1",
                published_at=datetime.now(),
                ticker="005930",
            ),
            NewsArticle(
                title="테스트 뉴스 2",
                content="내용 2",
                source="테스트 언론사",
                url="https://example.com/2",
                published_at=datetime.now(),
                ticker="005930",
            ),
        ]

        mock_naver.return_value = mock_articles[:1]
        mock_daum.return_value = mock_articles[1:2]
        mock_yonhap.return_value = []

        # 테스트
        articles = collector.fetch_stock_news(
            ticker="005930",
            days=7,
            max_articles=10,
        )

        # 검증
        assert len(articles) == 2
        assert mock_naver.called
        assert mock_daum.called
        assert mock_yonhap.called

    def test_to_dict(self, collector):
        """NewsArticle을 딕셔너리로 변환 테스트"""
        article = NewsArticle(
            title="테스트",
            content="내용",
            source="언론사",
            url="https://example.com",
            published_at=datetime(2024, 1, 15, 10, 30),
            ticker="005930",
        )

        result = collector.to_dict(article)

        assert result["title"] == "테스트"
        assert result["content"] == "내용"
        assert result["source"] == "언론사"
        assert result["url"] == "https://example.com"
        assert result["published_at"] == "2024-01-15T10:30:00"
        assert result["ticker"] == "005930"

    def test_to_dict_list(self, collector):
        """NewsArticle 리스트 변환 테스트"""
        articles = [
            NewsArticle(
                title=f"뉴스 {i}",
                content=f"내용 {i}",
                source="언론사",
                url=f"https://example.com/{i}",
                published_at=datetime.now(),
                ticker="005930",
            )
            for i in range(3)
        ]

        result = collector.to_dict_list(articles)

        assert len(result) == 3
        assert all(isinstance(item, dict) for item in result)

    @patch("src.collectors.news_collector.requests.Session.get")
    def test_fetch_naver_news_success(self, mock_get, collector, mock_response):
        """네이버 뉴스 수집 성공 테스트"""
        # HTML 응답 Mock (실제 네이버 뉴스 링크 형식)
        # 최신 날짜 사용 (7일 이내)
        from datetime import datetime, timedelta
        recent_date = (datetime.now() - timedelta(days=1)).strftime("%Y.%m.%d %H:%M")

        html = f"""
        <table class="type5">
            <tr>
                <td class="title">
                    <a href="/item/news_read.naver?article_id=0001234567&office_id=001&code=005930">삼성전자 실적이 좋아서 주가가 상승할 것으로 예상됩니다</a>
                </td>
                <td class="date">{recent_date}</td>
                <td class="info">테스트언론사</td>
            </tr>
            <tr>
                <td class="title">
                    <a href="/item/news_read.naver?article_id=0001234568&office_id=002&code=005930">삼성전자 관련 주요 이슈 정리 및 시장 전망 분석 리포트</a>
                </td>
                <td class="date">{recent_date}</td>
                <td class="info">테스트언론사2</td>
            </tr>
        </table>
        """

        mock_response.text = html
        mock_get.return_value = mock_response

        articles = collector._fetch_naver_news("005930", days=7, max_articles=10)

        # 검증 (본문은 빈 문자열이므로 제외)
        assert len(articles) == 2
        assert articles[0].title == "삼성전자 실적이 좋아서 주가가 상승할 것으로 예상됩니다"
        assert articles[0].source == "테스트언론사"
        assert articles[0].content == ""
        assert articles[0].url == "https://n.news.naver.com/mnews/article/001/0001234567"

    def test_parse_naver_date_normal(self, collector):
        """일반 날짜 파싱 테스트"""
        result = collector._parse_naver_date("2024.01.15 14:30")
        assert result == datetime(2024, 1, 15, 14, 30)

    def test_parse_naver_date_today(self, collector):
        """'오늘' 날짜 파싱 테스트"""
        result = collector._parse_naver_date("오늘 10:00")
        today = datetime.now().date()
        assert result.date() == today
        assert result.hour == 10
        assert result.minute == 0

    def test_parse_naver_date_yesterday(self, collector):
        """'어제' 날짜 파싱 테스트"""
        result = collector._parse_naver_date("어제 16:30")
        yesterday = datetime.now().date() - timedelta(days=1)
        assert result.date() == yesterday
        assert result.hour == 16
        assert result.minute == 30

    def test_parse_naver_date_invalid(self, collector):
        """잘못된 날짜 파싱 테스트"""
        result = collector._parse_naver_date("invalid")
        # 오류 시 현재 시간 반환
        assert isinstance(result, datetime)

    @patch("src.collectors.news_collector.requests.Session.get")
    def test_fetch_article_content_success(self, mock_get, collector, mock_response):
        """기사 본문 수집 성공 테스트"""
        html = """
        <div class="articleBody">
            <p>테스트 본문입니다.</p>
            <p>여러 줄의 내용이 있습니다.</p>
            <div class="ad">광고</div>
        </div>
        """

        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        content = collector._fetch_article_content("https://example.com/article")

        # 광고 제거되고 본문만 추출
        assert "테스트 본문입니다." in content
        assert "여러 줄의 내용이 있습니다." in content
        # 광고는 제거됨
        assert "광고" not in content or "ad" not in content.lower()

    def test_duplicate_removal(self, collector):
        """중복 제거 테스트"""
        from unittest.mock import patch

        # 중복 URL을 가진 기사들
        mock_articles = [
            NewsArticle(
                title="뉴스 1",
                content="내용 1",
                source="A",
                url="https://example.com/duplicate",
                published_at=datetime.now(),
                ticker="005930",
            ),
            NewsArticle(
                title="뉴스 2",
                content="내용 2",
                source="B",
                url="https://example.com/duplicate",  # 중복 URL
                published_at=datetime.now(),
                ticker="005930",
            ),
            NewsArticle(
                title="뉴스 3",
                content="내용 3",
                source="C",
                url="https://example.com/unique",
                published_at=datetime.now(),
                ticker="005930",
            ),
        ]

        with patch.object(collector, "_fetch_naver_news", return_value=[]):
            with patch.object(collector, "_fetch_daum_news", return_value=[]):
                with patch.object(collector, "_fetch_yonhap_news", return_value=mock_articles):
                    articles = collector.fetch_stock_news("005930", days=7, max_articles=10)

        # 중복 제거되어 2건만 남음
        assert len(articles) == 2

        # URL 중복 확인
        urls = [a.url for a in articles]
        assert len(urls) == len(set(urls))
