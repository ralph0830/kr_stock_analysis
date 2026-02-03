"""
Ticker Parser
KRX 티커 파싱 모듈
KOSPI/KOSDAQ 표준 종목코드 + ELW/덕주/상환사채/ETF 지원
"""

import re
import logging
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class TickerType(Enum):
    """티커 유형 분류"""
    STANDARD = "STANDARD"   # 일반 주식 (005930)
    ELW = "ELW"            # ELW/덕주 (0001A0)
    RIGHTS = "RIGHTS"      # 신주인수/권리 (005930A12345)
    ETF = "ETF"            # ETF (005930 etf)
    UNKNOWN = "UNKNOWN"      # 알 수 없음


class TickerParser:
    """
    KR 주식 티커 파서

    다양한 KRX 티커 형식을 파싱하고 검증합니다.
    """

    # 티커 패턴 (구체적인 것부터 순서대로 매칭)
    # KRX 티커 형식 참고:
    # - STANDARD: 005930 (6자리 숫자)
    # - ELW Type 1: 0001A0 (4자리숫자 + 알파벳 + 숫자, KOSDAQ ELW)
    # - ELW Type 2: 005930A (6자리숫자 + 알파벳)
    # - RIGHTS: 005930A12345 (긴 형식)
    PATTERNS = [
        # RIGHTS (신주인수) - 6자리숫자 + 숫자 + 알파벳 (예: 005930A12345)
        r'\d{6}\d*[A-Z]\d{5,}',
        # ELW Type 2 - 6자리숫자 + 알파벳 (예: 005930A)
        r'\d{6}[A-Z]\b',
        # ELW Type 1 - KOSDAQ ELW (예: 0001A0) - 4~5자리숫자 + 알파벳 + 숫자
        r'\d{4,5}[A-Z]\d',
        # 표준 - 6자리 숫자 (예: 005930)
        r'\d{6}',
    ]

    # ELW 패턴 (두 가지 형식 지원)
    # Type 1: 4-5자리숫자 + 알파벳 + 숫자 (예: 0001A0)
    # Type 2: 6자리숫자 + 알파벳 (예: 005930A)
    ELW_PATTERN_TYPE1 = re.compile(r'^\d{4,5}[A-Z]\d$')  # 0001A0 형식
    ELW_PATTERN_TYPE2 = re.compile(r'^\d{6}[A-Z]$')      # 005930A 형식

    def __init__(self):
        """패턴 컴파일 (성능 최적화)"""
        self._combined_pattern = re.compile(
            '|'.join(f'({p})' for p in self.PATTERNS)
        )
        self._elw_pattern_type1 = self.ELW_PATTERN_TYPE1
        self._elw_pattern_type2 = self.ELW_PATTERN_TYPE2
        self._standard_pattern = re.compile(r'^\d{6}$')

    def extract(self, query: str) -> List[str]:
        """
        쿼리에서 모든 티커 패턴 추출

        Args:
            query: 검색 쿼리

        Returns:
            추출된 티커 리스트 (중복 제거, 발견 순)
        """
        if not query:
            return []

        # 모든 패턴으로 검색
        matches = self._combined_pattern.findall(query)
        # findall은 튜플 리스트를 반환하므로 flatten 처리
        flat_matches = []
        for match in matches:
            if isinstance(match, tuple):
                # 첫 번째 비어있지 않은 그룹 선택
                for m in match:
                    if m:
                        flat_matches.append(m)
                        break
            else:
                flat_matches.append(match)

        # 중복 제거하고 순서 유지
        seen = set()
        results = []
        for ticker in flat_matches:
            if ticker not in seen:
                seen.add(ticker)
                results.append(ticker)

        logger.debug(f"Extracted tickers from '{query}': {results}")
        return results

    def extract_first(self, query: str) -> Optional[str]:
        """
        쿼리에서 첫 번째 티커 추출

        Args:
            query: 검색 쿼리

        Returns:
            추출된 티커 또는 None
        """
        tickers = self.extract(query)
        return tickers[0] if tickers else None

    def validate(self, ticker: str) -> bool:
        """
        티커 유효성 검증

        Args:
            ticker: 종목 코드

        Returns:
            유효한 티커이면 True
        """
        if not ticker:
            return False

        # 공백 제거
        ticker = ticker.strip()

        # 길이 체크 (최소 6자, 최대 14자 - RIGHTS)
        if not (6 <= len(ticker) <= 14):
            return False

        # 알파벳/숫자로만 구성
        if not ticker.replace('.', '').replace('-', '').isalnum():
            return False

        # 표준 티커 (6자리 숫자)
        if self._standard_pattern.match(ticker):
            return True

        # ELW 티커 Type 2 (6자리 + 알파벳)
        if self._elw_pattern_type2.match(ticker):
            return True

        # ELW 티커 Type 1 (KOSDAQ ELW: 4-5자리 + 알파벳 + 숫자)
        if self._elw_pattern_type1.match(ticker):
            return True

        # RIGHTS 티커 (더 긴 형식도 허용)
        if re.match(r'^\d{6}\d*[A-Z]\d{5,}$', ticker):
            return True

        return False

    def get_ticker_type(self, ticker: str) -> TickerType:
        """
        티커 유형 분류

        Args:
            ticker: 종목 코드

        Returns:
            TickerType Enum 값
        """
        if not ticker or not self.validate(ticker):
            return TickerType.UNKNOWN

        ticker = ticker.strip()

        # RIGHTS 형식 (가장 긴 패턴 우선 체크)
        if re.match(r'^\d{6}\d*[A-Z]\d{5,}$', ticker):
            return TickerType.RIGHTS

        # ELW 형식 Type 2 (6자리 + 알파벳)
        if self._elw_pattern_type2.match(ticker):
            return TickerType.ELW

        # ELW 형식 Type 1 (KOSDAQ ELW: 4-5자리 + 알파벳 + 숫자)
        if self._elw_pattern_type1.match(ticker):
            return TickerType.ELW

        # 표준 형식
        if self._standard_pattern.match(ticker):
            return TickerType.STANDARD

        return TickerType.UNKNOWN

    def format_for_display(self, ticker: str) -> str:
        """
        표시용 티커 형식 변환

        Args:
            ticker: 종목 코드

        Returns:
            포맷팅된 문자열 (예: "0001A0 (ELW)")
        """
        ticker_type = self.get_ticker_type(ticker)

        type_suffix = {
            TickerType.ELW: " (ELW)",
            TickerType.RIGHTS: " (권리)",
            TickerType.STANDARD: "",
            TickerType.UNKNOWN: "",
        }

        return f"{ticker}{type_suffix[ticker_type]}"

    def is_elw(self, ticker: str) -> bool:
        """ELW 티커인지 확인"""
        ticker = ticker.strip().upper()
        return (self._elw_pattern_type1.match(ticker) is not None or
                self._elw_pattern_type2.match(ticker) is not None)

    def is_standard(self, ticker: str) -> bool:
        """표준 6자리 티커인지 확인"""
        return self.get_ticker_type(ticker) == TickerType.STANDARD

    def normalize_ticker(self, ticker: str) -> str:
        """
        티커 정규화 (공백/하이픈 제거)

        Args:
            ticker: 종목 코드

        Returns:
            정규화된 종목 코드
        """
        return ticker.strip().upper().replace('-', '').replace('.', '')


# 싱글톤
_parser: Optional[TickerParser] = None


def get_ticker_parser() -> TickerParser:
    """티커 파서 싱글톤 반환"""
    global _parser
    if _parser is None:
        _parser = TickerParser()
    return _parser
