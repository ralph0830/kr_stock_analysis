"""
News Collector
뉴스 수집기 - 네이버/다음/연합뉴스 크롤링
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
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
