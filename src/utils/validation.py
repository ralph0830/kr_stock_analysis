"""
Input Validation Utilities

입력 검증 및 보안 유틸리티
"""
import re
import logging
from typing import Optional, List
from html import escape

logger = logging.getLogger(__name__)


# SQL Injection 패턴
SQL_INJECTION_PATTERNS = [
    r"(\b UNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)",
    r"(--|#|/\*|\*/)",
    r"(\bOR\b\s+\w+\s*=\s*\w+|\bAND\b\s+\w+\s*=\s*\w+)",  # OR 1=1
    r"(\bEXEC\b|\bEXECUTE\b)",
]

# XSS 패턴
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",  # onclick=, onload= 등
    r"<iframe[^>]*>",
    r"<embed[^>]*>",
    r"<object[^>]*>",
]

# 종목코드 패턴 (6자리 숫자)
TICKER_PATTERN = re.compile(r"^\d{6}$")

# 이메일 패턴
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_ticker(ticker: str) -> bool:
    """
    종목코드 검증

    Args:
        ticker: 종목코드 (6자리 숫자)

    Returns:
        유효 여부
    """
    if not ticker or not isinstance(ticker, str):
        return False

    return TICKER_PATTERN.match(ticker) is not None


def validate_email(email: str) -> bool:
    """
    이메일 검증

    Args:
        email: 이메일 주소

    Returns:
        유효 여부
    """
    if not email or not isinstance(email, str):
        return False

    return EMAIL_PATTERN.match(email) is not None


def detect_sql_injection(text: str) -> bool:
    """
    SQL Injection 공격 탐지

    Args:
        text: 검증할 텍스트

    Returns:
        공격 여부
    """
    if not text or not isinstance(text, str):
        return False

    text_upper = text.upper()

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_upper, re.IGNORECASE):
            logger.warning(f"SQL Injection detected: {text[:100]}")
            return True

    return False


def detect_xss(text: str) -> bool:
    """
    XSS 공격 탐지

    Args:
        text: 검증할 텍스트

    Returns:
        공격 여부
    """
    if not text or not isinstance(text, str):
        return False

    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            logger.warning(f"XSS detected: {text[:100]}")
            return True

    return False


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    문자열 정제

    - HTML escaping
    - 길이 제한
    - NULL 바이트 제거

    Args:
        text: 정제할 문자열
        max_length: 최대 길이

    Returns:
        정제된 문자열
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # NULL 바이트 제거
    text = text.replace("\x00", "")

    # HTML escaping
    text = escape(text)

    # 길이 제한
    if len(text) > max_length:
        text = text[:max_length]

    return text


def validate_query_params(params: dict) -> dict:
    """
    쿼리 파라미터 검증

    Args:
        params: 쿼리 파라미터 dict

    Returns:
        검증된 파라미터 dict
    """
    validated = {}

    for key, value in params.items():
        if value is None:
            continue

        # SQL Injection/XSS 검사
        if isinstance(value, str):
            if detect_sql_injection(value) or detect_xss(value):
                logger.warning(f"Malicious input detected in param '{key}'")
                continue

            value = sanitize_string(value)

        validated[key] = value

    return validated


def validate_pagination(
    limit: int = 100,
    offset: int = 0,
    max_limit: int = 1000,
) -> tuple[int, int]:
    """
    페이지네이션 파라미터 검증

    Args:
        limit: 가져올 항목 수
        offset: 건너뛸 항목 수
        max_limit: 최대 허용 limit

    Returns:
        (검증된 limit, 검증된 offset)
    """
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 100

    try:
        offset = int(offset)
    except (ValueError, TypeError):
        offset = 0

    # 범위 검증
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)

    return limit, offset


def validate_ticker_list(tickers: List[str]) -> List[str]:
    """
    종목코드 리스트 검증

    Args:
        tickers: 종목코드 리스트

    Returns:
        검증된 종목코드 리스트
    """
    if not tickers:
        return []

    validated = []

    for ticker in tickers:
        if validate_ticker(ticker):
            validated.append(ticker)

    return validated


class SecurityValidator:
    """
    보안 검증기

    여러 검증을 한 번에 수행
    """

    @staticmethod
    def validate_user_input(text: str, max_length: int = 1000) -> tuple[bool, Optional[str]]:
        """
        사용자 입력 검증

        Args:
            text: 검증할 텍스트
            max_length: 최대 길이

        Returns:
            (유효 여부, 에러 메시지)
        """
        if not text:
            return True, None

        if not isinstance(text, str):
            return False, "Input must be a string"

        if len(text) > max_length:
            return False, f"Input too long (max {max_length} characters)"

        if detect_sql_injection(text):
            return False, "Invalid input detected"

        if detect_xss(text):
            return False, "Invalid input detected"

        return True, None

    @staticmethod
    def sanitize_and_validate(text: str, max_length: int = 1000) -> str:
        """
        정제 및 검증 (검증 실패 시 빈 문자열 반환)

        Args:
            text: 정제할 텍스트
            max_length: 최대 길이

        Returns:
            정제된 문자열 (검증 실패 시 "")
        """
        is_valid, _ = SecurityValidator.validate_user_input(text, max_length)

        if not is_valid:
            return ""

        return sanitize_string(text, max_length)
