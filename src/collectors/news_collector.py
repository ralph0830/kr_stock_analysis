"""
News Collector
뉴스 수집기 - 네이버/다음/연합뉴스 크롤링
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """뉴스 기사 데이터 클래스"""
    title: str
    content: str
    source: str  # 언론사
    url: str
    published_at: datetime
    ticker: str  # 종목코드


class NewsCollector:
    """
    뉴스 수집기

    네이버/다음/연합뉴스에서 종목 관련 뉴스 수집
    """

    # 요청 간격 (robots.txt 준수)
    REQUEST_INTERVAL = 1.0  # 1초

    # User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    # RSS 피드 URL
    NAVER_FINANCE_RSS = "https://finance.naver.com/news/news_list.naver?mode=RSS"
    DAUM_FINANCE_RSS = "https://news.daum.net/breakingnews/economic"
    YONHAP_ECONOMY_RSS = "https://www.yonhapnewstv.co.kr/category/economy/feed"

    # 네이버 뉴스 URL 패턴 (Phase 1: 실제 기사 URL 추출)
    NAVER_NEWS_URL_PATTERN = re.compile(
        r'https://n\.news\.naver\.com/mnews/article/(\d+)/(\d+)'
    )

    def __init__(self):
        """NewsCollector 초기화"""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        """요청 간격 준수 (rate limiting)"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self.REQUEST_INTERVAL:
            sleep_time = self.REQUEST_INTERVAL - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def fetch_stock_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50,
    ) -> List[NewsArticle]:
        """
        종목 관련 뉴스 수집

        Args:
            ticker: 종목코드 (예: "005930" for 삼성전자)
            days: 수집할 날짜 범위 (기본 7일)
            max_articles: 최대 기사 수 (기본 50건)

        Returns:
            뉴스 기사 리스트
        """
        logger.info(f"📰 {ticker} 뉴스 수집 시작 (최근 {days}일, 최대 {max_articles}건)")

        # 네이버 뉴스 수집 (주요 소스)
        articles = self._fetch_naver_news(ticker, days, max_articles)

        # 부족하면 다음 뉴스 수집
        if len(articles) < max_articles:
            additional = self._fetch_daum_news(ticker, days, max_articles - len(articles))
            articles.extend(additional)

        # 부족하면 연합뉴스 수집
        if len(articles) < max_articles:
            additional = self._fetch_yonhap_news(ticker, days, max_articles - len(articles))
            articles.extend(additional)

        # 날짜순 정렬 및 중복 제거
        seen_urls = set()
        unique_articles = []
        for article in sorted(articles, key=lambda x: x.published_at, reverse=True):
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

            if len(unique_articles) >= max_articles:
                break

        logger.info(f"✅ {ticker} 뉴스 {len(unique_articles)}건 수집 완료")
        return unique_articles[:max_articles]

    def _fetch_naver_news(
        self,
        ticker: str,
        days: int,
        max_articles: int,
    ) -> List[NewsArticle]:
        """
        네이버 금융 뉴스 수집

        네이버 금융 종목 페이지 뉴스 크롤링
        """
        articles = []

        try:
            # 네이버 금융 종목 뉴스 URL
            url = f"https://finance.naver.com/item/news_news.nhn?code={ticker}&page=1"

            self._wait_for_rate_limit()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 뉴스 목록 추출
            news_list = soup.select("table.type5 tr")

            for row in news_list:
                try:
                    # 제목 및 링크
                    title_element = row.select_one("td.title a")
                    if not title_element:
                        continue

                    title = title_element.get_text(strip=True)
                    article_url = title_element.get("href", "")

                    # 정보원 및 날짜
                    info_element = row.select_one("td.info")
                    if not info_element:
                        continue

                    info_text = info_element.get_text(strip=True)
                    parts = info_text.split()

                    if len(parts) < 2:
                        continue

                    source = parts[0]
                    date_str = parts[1]

                    # 날짜 파싱
                    published_at = self._parse_naver_date(date_str)

                    # 날짜 범위 확인
                    if (datetime.now() - published_at).days > days:
                        continue

                    # 본문 수집 (별도 요청)
                    content = self._fetch_article_content(article_url)

                    articles.append(NewsArticle(
                        title=title,
                        content=content,
                        source=source,
                        url=article_url,
                        published_at=published_at,
                        ticker=ticker,
                    ))

                    if len(articles) >= max_articles:
                        break

                except Exception as e:
                    logger.debug(f"네이버 뉴스 파싱 오류: {e}")
                    continue

            logger.debug(f"네이버 뉴스 {len(articles)}건 수집")

        except Exception as e:
            logger.error(f"네이버 뉴스 수집 실패: {e}")

        return articles

    def _fetch_daum_news(
        self,
        ticker: str,
        days: int,
        max_articles: int,
    ) -> List[NewsArticle]:
        """
        다음 금융 뉴스 수집

        다음 금융 종목 페이지 뉴스 크롤링
        """
        # TODO: 다음 뉴스 크롤링 구현
        logger.debug("다음 뉴스 수집 (아직 구현되지 않음)")
        return []

    def _fetch_yonhap_news(
        self,
        ticker: str,
        days: int,
        max_articles: int,
    ) -> List[NewsArticle]:
        """
        연합뉴스 경제 뉴스 수집

        연합뉴스 RSS 피드 파싱
        """
        # TODO: 연합뉴스 RSS 구현
        logger.debug("연합뉴스 수집 (아직 구현되지 않음)")
        return []

    def _fetch_article_content(self, url: str) -> str:
        """
        기사 본문 수집

        Args:
            url: 기사 URL

        Returns:
            기사 본문 텍스트
        """
        try:
            self._wait_for_rate_limit()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 네이버 뉴스 본문 추출
            content_element = soup.select_one("div.articleBody")
            if content_element:
                # 불필요한 요소 제거
                for element in content_element.select("script, style, .ad"):
                    element.decompose()

                content = content_element.get_text(separator="\n", strip=True)
                return content[:5000]  # 최대 5000자 제한

        except Exception as e:
            logger.debug(f"본문 수집 실패 ({url}): {e}")

        return ""

    def _parse_naver_date(self, date_str: str) -> datetime:
        """
        네이버 뉴스 날짜 파싱

        Args:
            date_str: 날짜 문자열 (예: "2024.01.15 14:30")

        Returns:
            datetime 객체
        """
        try:
            # 공백 제거
            date_str = date_str.strip()

            # 오늘/어제 표현 처리
            if date_str.startswith("오늘"):
                today = datetime.now().date()
                time_part = date_str.split()[1] if len(date_str.split()) > 1 else "00:00"
                hour, minute = map(int, time_part.split(":"))
                return datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)

            elif date_str.startswith("어제"):
                yesterday = datetime.now().date() - timedelta(days=1)
                time_part = date_str.split()[1] if len(date_str.split()) > 1 else "00:00"
                hour, minute = map(int, time_part.split(":"))
                return datetime.combine(yesterday, datetime.min.time()).replace(hour=hour, minute=minute)

            # 일반 날짜 포맷 (2024.01.15 14:30)
            date_str = date_str.replace(".", "").replace(":", "")
            return datetime.strptime(date_str, "%Y%m%d %H%M")

        except Exception as e:
            logger.debug(f"날짜 파싱 실패 ({date_str}): {e}")
            return datetime.now()

    # ==========================================================================
    # Phase 1: 네이버 뉴스 실제 URL 추출 메서드
    # ==========================================================================

    def _is_valid_naver_news_url(self, url: str) -> bool:
        """
        네이버 뉴스 실제 기사 URL인지 확인

        Args:
            url: 검사할 URL

        Returns:
            올바른 네이버 뉴스 기사 URL이면 True
        """
        if not url:
            return False

        # 네이버 뉴스 기사 URL 패턴 확인
        # https://n.news.naver.com/mnews/article/{office_id}/{article_id}
        return bool(self.NAVER_NEWS_URL_PATTERN.match(url))

    def _parse_naver_news_url(self, url: str) -> Tuple[str, str]:
        """
        네이버 뉴스 URL에서 office_id와 article_id 추출

        Args:
            url: 네이버 뉴스 기사 URL

        Returns:
            (office_id, article_id) 튜플

        Raises:
            ValueError: 올바르지 않은 URL인 경우
        """
        match = self.NAVER_NEWS_URL_PATTERN.match(url)
        if not match:
            raise ValueError(f"올바르지 않은 네이버 뉴스 URL: {url}")

        office_id = match.group(1)
        article_id = match.group(2)
        return office_id, article_id

    def _extract_naver_news_urls(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[str]:
        """
        네이버 뉴스 검색에서 실제 기사 URL 추출

        Args:
            query: 검색어 (종목명 또는 티커)
            max_results: 최대 결과 수

        Returns:
            네이버 뉴스 기사 URL 리스트 (중복 제거됨)
        """
        urls = []

        try:
            # 네이버 뉴스 검색 URL
            search_url = (
                f"https://search.naver.com/search.naver"
                f"?where=news&sm=tab_pge&query={query}&sort=1&start=1"
            )

            self._wait_for_rate_limit()
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 뉴스 검색 결과에서 링크 추출
            for link in soup.find_all("a", href=True):
                href = link["href"]

                # 올바른 네이버 뉴스 URL인지 확인
                if self._is_valid_naver_news_url(href):
                    if href not in urls:  # 중복 제거
                        urls.append(href)

                    if len(urls) >= max_results:
                        break

            logger.debug(f"검색 '{query}'에서 {len(urls)}개의 뉴스 URL 추출")

        except Exception as e:
            logger.error(f"네이버 뉴스 검색 실패 ({query}): {e}")

        return urls

    def _fetch_naver_news_with_urls(
        self,
        query: str,
        days: int = 7,
        max_articles: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        네이버 뉴스 검색으로 기사 수집 (실제 URL 포함)

        Args:
            query: 검색어 (종목명 또는 티커)
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
            [
                {
                    "title": "기사 제목",
                    "url": "https://n.news.naver.com/mnews/article/...",
                    "source": "언론사",
                    "published_at": "2024-01-30T10:00:00",
                    "content": "기사 본문"
                }
            ]
        """
        articles = []

        try:
            # URL 추출
            urls = self._extract_naver_news_urls(query, max_results=max_articles)

            for url in urls:
                try:
                    # 기사 상세 정보 가져오기
                    article_data = self._fetch_article_details(url)
                    if not article_data:
                        continue

                    # 날짜 범위 확인
                    published_at = article_data.get("published_at")
                    if published_at and (datetime.now() - published_at).days > days:
                        continue

                    articles.append(article_data)

                    if len(articles) >= max_articles:
                        break

                except Exception as e:
                    logger.debug(f"기사 수집 실패 ({url}): {e}")
                    continue

            # 최신 뉴스 우선 정렬
            articles.sort(
                key=lambda x: x.get("published_at", datetime.min),
                reverse=True
            )

            logger.debug(f"총 {len(articles)}건의 뉴스 수집 완료")

        except Exception as e:
            logger.error(f"네이버 뉴스 수집 실패: {e}")

        return articles

    def _fetch_article_details(self, url: str) -> Optional[Dict[str, Any]]:
        """
        네이버 뉴스 기사 상세 정보 수집

        Args:
            url: 기사 URL

        Returns:
            기사 정보 딕셔너리 또는 None
        """
        try:
            self._wait_for_rate_limit()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 제목 추출
            title_elem = soup.select_one("h2#title_area") or soup.select_one("h3.title") or soup.select_one("meta[property='og:title']")
            title = ""
            if title_elem:
                if title_elem.name == "meta":
                    title = title_elem.get("content", "")
                else:
                    title = title_elem.get_text(strip=True)

            # 언론사 추출
            source_elem = soup.select_one(".media_end_head_top_link_text") or soup.select_one(".press_name") or soup.select_one("meta[property='og:article:author']")
            source = ""
            if source_elem:
                if source_elem.name == "meta":
                    source = source_elem.get("content", "")
                else:
                    source = source_elem.get_text(strip=True)

            # 날짜 추출
            date_elem = soup.select_one(".media_end_head_info_datestamp_bunch") or soup.select_one(".date") or soup.select_one("meta[property='article:published_time']")
            published_at = None
            if date_elem:
                if date_elem.name == "meta":
                    date_str = date_elem.get("content", "")
                    try:
                        published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except:
                        pass
                else:
                    date_text = date_elem.get_text(strip=True)
                    # 여러 날짜 포맷 시도
                    published_at = self._parse_news_date(date_text)

            if not published_at:
                published_at = datetime.now()

            # 본문 추출
            content_elem = soup.select_one("#newsct_article") or soup.select_one(".article_body") or soup.select_one("div#articleBody")
            content = ""
            if content_elem:
                # 불필요한 요소 제거
                for elem in content_elem.select("script, style, .ad, .caption"):
                    elem.decompose()

                content = content_elem.get_text(separator="\n", strip=True)[:5000]

            return {
                "title": title,
                "url": url,
                "source": source,
                "published_at": published_at.isoformat() if isinstance(published_at, datetime) else published_at,
                "content": content,
            }

        except Exception as e:
            logger.debug(f"기사 상세 수집 실패 ({url}): {e}")
            return None

    def _parse_news_date(self, date_str: str) -> Optional[datetime]:
        """
        다양한 뉴스 날짜 포맷 파싱

        Args:
            date_str: 날짜 문자열

        Returns:
            datetime 객체 또는 None
        """
        try:
            # 다양한 포맷 시도
            formats = [
                "%Y.%m.%d. %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y%m%d%H%M",
            ]

            date_str = date_str.strip()
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            # "2024.01.30." 형식 처리
            if re.match(r"\d{4}\.\d{2}\.\d{2}\.", date_str):
                date_str = date_str.rstrip(".") + " 00:00"
                return datetime.strptime(date_str, "%Y.%m.%d %H:%M")

        except Exception as e:
            logger.debug(f"날짜 파싱 실패 ({date_str}): {e}")

        return None

    # ==========================================================================
    # 기존 메서드
    # ==========================================================================

    def to_dict(self, article: NewsArticle) -> Dict[str, Any]:
        """
        NewsArticle을 딕셔너리로 변환

        Args:
            article: NewsArticle 객체

        Returns:
            딕셔너리
        """
        return {
            "title": article.title,
            "content": article.content,
            "source": article.source,
            "url": article.url,
            "published_at": article.published_at.isoformat(),
            "ticker": article.ticker,
        }

    def to_dict_list(self, articles: List[NewsArticle]) -> List[Dict[str, Any]]:
        """
        NewsArticle 리스트를 딕셔너리 리스트로 변환

        Args:
            articles: NewsArticle 리스트

        Returns:
            딕셔너리 리스트
        """
        return [self.to_dict(article) for article in articles]
