"""
Base Collector Interface
모든 뉴스 수집기의 기반 클래스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

import requests


class BaseNewsCollector(ABC):
    """
    뉴스 수집기 기반 클래스

    모든 뉴스 수집기가 구현해야 할 공통 인터페이스
    """

    # 요청 간격 (하위 클래스에서 오버라이드 가능)
    REQUEST_INTERVAL = 1.0

    # User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def __init__(self):
        """BaseNewsCollector 초기화"""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        """요청 간격 준수"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self.REQUEST_INTERVAL:
            sleep_time = self.REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    @abstractmethod
    def fetch_news(
        self,
        days: int = 7,
        max_articles: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        뉴스 수집 (추상 메서드)

        Args:
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수
            **kwargs: 추가 파라미터

        Returns:
            기사 정보 딕셔너리 리스트
            [
                {
                    "title": "기사 제목",
                    "url": "기사 URL",
                    "content": "기사 요약/본문",
                    "source": "언론사",
                    "published_at": "2026-01-30T10:00:00",
                }
            ]
        """
        pass

    def fetch_by_ticker(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        종목별 뉴스 수집 (기본 구현)

        하위 클래스에서 오버라이드하여 최적화 가능

        Args:
            ticker: 종목 코드
            days: 수집할 날짜 범위
            max_articles: 최대 기사 수

        Returns:
            기사 정보 리스트
        """
        # 기본 구현: 전체 뉴스 가져온 후 필터링
        all_articles = self.fetch_news(days=days, max_articles=100)

        # 종목명 매핑 (하위 클래스에서 오버라이드)
        ticker_names = self._get_ticker_names()
        search_name = ticker_names.get(ticker, ticker)

        # 종목 관련 기사 필터링
        filtered = []
        for article in all_articles:
            if self._is_ticker_related(article, search_name):
                filtered.append(article)

                if len(filtered) >= max_articles:
                    break

        return filtered

    def _get_ticker_names(self) -> Dict[str, str]:
        """
        종목 코드-이름 매핑 (기본 구현)

        하위 클래스에서 확장 가능

        Returns:
            {ticker: name} 딕셔너리
        """
        return {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035420": "NAVER",
            "035720": "카카오",
            "005380": "현대차",
        }

    def _is_ticker_related(self, article: Dict[str, Any], search_name: str) -> bool:
        """
        기사가 종목 관련인지 확인 (기본 구현)

        Args:
            article: 기사 정보
            search_name: 검색할 종목명

        Returns:
            종목 관련이면 True
        """
        title = article.get("title", "")
        content = article.get("content", "")

        return search_name in title or search_name in content

    def _normalize_datetime(self, dt: Optional[datetime]) -> Optional[datetime]:
        """
        datetime을 naive datetime으로 정규화

        Args:
            dt: datetime 객체 (aware 또는 naive)

        Returns:
            naive datetime 객체
        """
        if dt is None:
            return None

        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)

        return dt

    def _is_within_days(self, published_at: Any, days: int) -> bool:
        """
        날짜가 범위 내인지 확인

        Args:
            published_at: 날짜 (datetime 또는 str)
            days: 허용된 날짜 범위

        Returns:
            범위 내이면 True
        """
        if published_at is None:
            return True

        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at)

        # timezone-aware를 naive로 변환
        published_at = self._normalize_datetime(published_at)

        if published_at is None:
            return True

        return (datetime.now() - published_at).days <= days
