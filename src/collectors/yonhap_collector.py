"""
Yonhap News Collector
연합뉴스 RSS 피드 파싱
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from src.collectors.base_collector import BaseNewsCollector

logger = logging.getLogger(__name__)


class YonhapCollector(BaseNewsCollector):
    """
    연합뉴스 RSS 수집기

    연합뉴스 RSS 피드에서 경제/금융 뉴스 수집
    """

    # 연합뉴스 RSS 피드 URL
    YONHAP_ECONOMY_RSS = "https://www.yonhapnewstv.co.kr/category/economy/feed"
    YONHAP_FINANCE_RSS = "https://www.yonhapnewstv.co.kr/category/finance/feed"

    def fetch_news(
        self,
        days: int = 7,
        max_articles: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        연합뉴스 전체 뉴스 수집

        Args:
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
        """
        return self.fetch_all_news(days=days, max_articles=max_articles)

    def fetch_rss_news(
        self,
        rss_url: Optional[str] = None,
        max_articles: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        연합뉴스 RSS 피드에서 뉴스 수집

        Args:
            rss_url: RSS 피드 URL (None이면 기본 경제 RSS 사용)
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
        """
        if rss_url is None:
            rss_url = self.YONHAP_ECONOMY_RSS

        articles = []

        try:
            self._wait_for_rate_limit()
            response = self.session.get(rss_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "xml")

            # RSS item 추출
            items = soup.find_all("item")

            for item in items[:max_articles]:
                try:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    date_elem = item.find("pubDate")
                    author_elem = item.find("author")

                    if not title_elem or not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = link_elem.get_text(strip=True)
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    # 날짜 파싱
                    published_at = None
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        published_at = self._parse_rss_date(date_str)

                    if not published_at:
                        published_at = datetime.now()

                    source = author_elem.get_text(strip=True) if author_elem else "연합뉴스"

                    # timezone-aware datetime을 naive로 변환
                    pub_at = published_at
                    if isinstance(pub_at, datetime) and pub_at.tzinfo is not None:
                        pub_at = pub_at.replace(tzinfo=None)

                    articles.append({
                        "title": title,
                        "url": url,
                        "content": description[:500],  # 요약만 저장
                        "source": source,
                        "published_at": pub_at.isoformat() if isinstance(pub_at, datetime) else pub_at,
                    })

                except Exception as e:
                    logger.debug(f"RSS item 파싱 오류: {e}")
                    continue

            logger.debug(f"연합뉴스 RSS에서 {len(articles)}건 수집")

        except Exception as e:
            logger.error(f"연합뉴스 RSS 수집 실패: {e}")

        return articles

    def fetch_ticker_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        종목별 연합뉴스 검색

        Args:
            ticker: 종목 코드
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
        """
        # 종목명 매핑 (간단 버전)
        ticker_names = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035420": "NAVER",
            "035720": "카카오",
            "005380": "현대차",
        }

        search_name = ticker_names.get(ticker, ticker)

        # 전체 RSS 가져오기
        all_articles = self.fetch_rss_news(max_articles=50)

        # 종목 관련 기사 필터링
        filtered = []
        for article in all_articles:
            # 제목이나 내용에 종목명이 포함된 경우
            if search_name in article["title"] or search_name in article.get("content", ""):
                # 날짜 범위 확인
                published_at = article.get("published_at")
                if published_at:
                    if isinstance(published_at, str):
                        published_at = datetime.fromisoformat(published_at)

                    # timezone-aware datetime을 naive로 변환
                    if published_at.tzinfo is not None:
                        published_at = published_at.replace(tzinfo=None)

                    if (datetime.now() - published_at).days > days:
                        continue

                filtered.append(article)

                if len(filtered) >= max_articles:
                    break

        return filtered

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """
        RFC 822 날짜 파싱

        Args:
            date_str: RFC 822 형식 날짜 문자열
                예: "Fri, 30 Jan 2026 14:00:00 +0900"

        Returns:
            datetime 객체 또는 None
        """
        try:
            # RFC 822 포맷
            date_str = date_str.strip()
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")

        except ValueError:
            # 다른 포맷 시도
            try:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    logger.debug(f"날짜 파싱 실패: {date_str}")
                    return None

    def fetch_all_news(
        self,
        days: int = 7,
        max_articles: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        모든 연합뉴스 RSS 수집

        Args:
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
        """
        all_articles = []

        # 경제 + 금융 RSS
        for rss_url in [self.YONHAP_ECONOMY_RSS, self.YONHAP_FINANCE_RSS]:
            articles = self.fetch_rss_news(rss_url, max_articles=max_articles)

            # 날짜 범위 필터링
            for article in articles:
                published_at = article.get("published_at")
                if published_at:
                    if isinstance(published_at, str):
                        published_at = datetime.fromisoformat(published_at)

                    # timezone-aware datetime을 naive로 변환
                    if published_at.tzinfo is not None:
                        published_at = published_at.replace(tzinfo=None)

                    if (datetime.now() - published_at).days > days:
                        continue

                all_articles.append(article)

        # 중복 제거 및 정렬
        seen_urls = set()
        unique_articles = []
        for article in sorted(all_articles, key=lambda x: x.get("published_at", ""), reverse=True):
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

                if len(unique_articles) >= max_articles:
                    break

        return unique_articles[:max_articles]
