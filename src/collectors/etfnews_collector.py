"""
ETF News Collector
ETF 관련 뉴스 수집
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from src.collectors.base_collector import BaseNewsCollector

logger = logging.getLogger(__name__)


class ETFNewsCollector(BaseNewsCollector):
    """
    ETF 관련 뉴스 수집기

    다양한 뉴스 소스에서 ETF 관련 기사 수집
    """

    # ETF 관련 키워드
    ETF_KEYWORDS = [
        "ETF", "TIGER", "KODEX", "SOL", "KOSEF",
        "선물 ETF", "레버리지", "인버스",
        "상장지수펀드", "집합투자증권",
    ]

    # ETF 뉴스 소스
    ETF_NEWS_SOURCES = [
        "https://news.etoday.com/etf/news_list.php",
        "https://www.fnnews.com/news/etf",
    ]

    def fetch_news(
        self,
        days: int = 7,
        max_articles: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        ETF 관련 뉴스 수집

        Args:
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
        """
        return self.fetch_etf_news(days=days, max_articles=max_articles)

    def _is_etf_related(self, text: str) -> bool:
        """
        ETF 관련 키워드 포함 여부 확인

        Args:
            text: 검사할 텍스트

        Returns:
            ETF 관련이면 True
        """
        text_upper = text.upper()
        return any(keyword.upper() in text_upper for keyword in self.ETF_KEYWORDS)

    def fetch_etf_news(
        self,
        days: int = 7,
        max_articles: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        ETF 관련 뉴스 수집

        Args:
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 딕셔너리 리스트
        """
        all_articles = []

        for source_url in self.ETF_NEWS_SOURCES:
            try:
                articles = self._fetch_from_source(source_url, days, max_articles)
                all_articles.extend(articles)
            except Exception as e:
                logger.debug(f"ETF 뉴스 소스 수집 실패 ({source_url}): {e}")
                continue

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

    def _fetch_from_source(
        self,
        source_url: str,
        days: int,
        max_articles: int,
    ) -> List[Dict[str, Any]]:
        """
        특정 소스에서 ETF 뉴스 수집

        Args:
            source_url: 뉴스 소스 URL
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 리스트
        """
        articles = []

        try:
            self._wait_for_rate_limit()
            response = self.session.get(source_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 일반적인 뉴스 목록 구조
            news_items = soup.select(".news_list .item, .article, .news_item, .list_item")

            if not news_items:
                # 대신 CSS 선택자
                news_items = soup.find_all("a", href=re.compile(r"/article|/news"))

            for item in news_items[:max_articles * 2]:  # 필터링을 위해 더 많이 가져옴
                try:
                    title, url, date_str = self._parse_news_item(item, source_url)

                    if not title or not url:
                        continue

                    # ETF 관련 키워드 필터링
                    if not self._is_etf_related(title):
                        continue

                    # 날짜 파싱
                    published_at = self._parse_date(date_str) if date_str else datetime.now()

                    # 날짜 범위 확인
                    if (datetime.now() - published_at).days > days:
                        continue

                    articles.append({
                        "title": title,
                        "url": url,
                        "content": "",  # 본문 수집은 별도 요청 필요
                        "source": self._extract_source(source_url),
                        "published_at": published_at.isoformat(),
                    })

                    if len(articles) >= max_articles:
                        break

                except Exception as e:
                    logger.debug(f"뉴스 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"ETF 뉴스 수집 실패 ({source_url}): {e}")

        return articles

    def _parse_news_item(self, item, base_url: str) -> tuple:
        """
        뉴스 아이템 파싱

        Args:
            item: BeautifulSoup element
            base_url: 기본 URL

        Returns:
            (title, url, date_str) 튜플
        """
        title = ""
        url = ""
        date_str = ""

        # 링크 요소
        if item.name == "a":
            link_elem = item
        else:
            link_elem = item.find("a")

        if link_elem:
            title = link_elem.get_text(strip=True)
            href = link_elem.get("href", "")

            if href:
                # 상대 경로를 절대 경로로 변환
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    url = f"{parsed.scheme}://{parsed.netloc}{href}"
                elif not href.startswith("http"):
                    url = base_url + href
                else:
                    url = href

        # 날짜 요소
        date_elem = item.find(class_=re.compile(r"date|time", re.I))
        if date_elem:
            date_str = date_elem.get_text(strip=True)

        # 제목이 없는 경우
        if not title:
            title_elem = item.find(class_=re.compile(r"title|subject", re.I))
            if title_elem:
                title = title_elem.get_text(strip=True)

        return title, url, date_str

    def _parse_date(self, date_str: str) -> datetime:
        """
        다양한 날짜 포맷 파싱

        Args:
            date_str: 날짜 문자열

        Returns:
            datetime 객체
        """
        date_str = date_str.strip()

        # 다양한 포맷 시도
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # "2026년 1월 30일" 형식
        if "년" in date_str and "월" in date_str and "일" in date_str:
            date_str = re.sub(r"[년월일]", " ", date_str)
            date_str = date_str.strip()
            try:
                return datetime.strptime(date_str, "%Y %m %d")
            except ValueError:
                pass

        logger.debug(f"날짜 파싱 실패: {date_str}")
        return datetime.now()

    def _extract_source(self, url: str) -> str:
        """
        URL에서 뉴스 소스 추출

        Args:
            url: 뉴스 URL

        Returns:
            소스 이름
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        # 도메인에서 소스 추출
        if "etoday" in domain:
            return "이투데이"
        elif "fnnews" in domain:
            return "파이낸셜뉴스"
        elif "mt" in domain:
            return "머니투데이"
        elif "sedaily" in domain:
            return "서울경제"
        else:
            return "ETF 뉴스"

    def fetch_etf_by_ticker(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        종목 관련 ETF 뉴스 검색

        Args:
            ticker: 종목 코드
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 리스트
        """
        all_articles = self.fetch_etf_news(days=days, max_articles=50)

        # 종목 관련 ETF 뉴스 필터링
        ticker_names = {
            "005930": ["삼성전자", "TIGER 삼성", "KODEX 삼성"],
            "000660": ["SK하이닉스", "TIGER 하이닉스"],
            "035420": ["NAVER", "TIGER 네이버"],
            "035720": ["카카오", "TIGER 카카오"],
        }

        search_keywords = ticker_names.get(ticker, [ticker])

        filtered = []
        for article in all_articles:
            title = article.get("title", "")

            # 검색 키워드 포함 확인
            if any(keyword in title for keyword in search_keywords):
                filtered.append(article)

                if len(filtered) >= max_articles:
                    break

        return filtered
