"""
Chatbot Kiwoom Integration
Kiwoom REST API 연동을 위한 헬퍼 함수
"""

import logging
import os
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from src.kiwoom.rest_api import KiwoomRestAPI

logger = logging.getLogger(__name__)


class KiwoomAPIError(Exception):
    """Kiwoom API 관련 예외 (기본)"""
    def __init__(self, message: str, user_message: str = None):
        super().__init__(message)
        self.user_message = user_message or message

    def __str__(self):
        return self.user_message


class KiwoomTimeoutError(KiwoomAPIError):
    """Kiwoom API 타임아웃 에러"""
    def __init__(self, message: str = "Kiwoom API 응답 시간이 초과되었습니다"):
        user_msg = "현재가 조회에 시간이 너무 오래 걸립니다. 잠시 후 다시 시도해주세요."
        super().__init__(message, user_msg)


class KiwoomRateLimitError(KiwoomAPIError):
    """Kiwoom API Rate Limiting 에러"""
    def __init__(self, message: str = "Kiwoom API 호출 한도 초과"):
        user_msg = "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해주세요."
        super().__init__(message, user_msg)


class KiwoomNotFoundError(KiwoomAPIError):
    """종목을 찾을 수 없는 에러"""
    def __init__(self, ticker: str):
        user_msg = f"종목 코드 {ticker}에 대한 정보를 찾을 수 없습니다. 종목 코드를 확인해주세요."
        super().__init__(f"Stock not found: {ticker}", user_msg)
        self.ticker = ticker


class KiwoomAuthenticationError(KiwoomAPIError):
    """Kiwoom API 인증 에러"""
    def __init__(self, message: str = "Kiwoom API 인증 실패"):
        user_msg = "Kiwoom API 연결에 문제가 있습니다. 관리자에게 문의해주세요."
        super().__init__(message, user_msg)


class KiwoomNetworkError(KiwoomAPIError):
    """Kiwoom API 네트워크 에러"""
    def __init__(self, message: str = "Kiwoom API 네트워크 오류"):
        user_msg = "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해주세요."
        super().__init__(message, user_msg)


# Kiwoom API 설정
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY", "")
KIWOOM_SECRET_KEY = os.getenv("KIWOOM_SECRET_KEY", "")
KIWOOM_BASE_URL = os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com")
KIWOOM_WS_URL = os.getenv("KIWOOM_WS_URL", "wss://api.kiwoom.com:10000/api/dostk/websocket")
USE_KIWOOM_REST = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"


def check_kiwoom_available() -> None:
    """
    Kiwoom API 사용 가능 여부 확인

    Raises:
        KiwoomAPIError: API가 설정되지 않은 경우
    """
    if not (KIWOOM_APP_KEY and KIWOOM_SECRET_KEY):
        raise KiwoomAPIError(
            "Kiwoom API 키가 설정되지 않았습니다. "
            "실시간 가격 정보를 위해 KIWOOM_APP_KEY와 KIWOOM_SECRET_KEY가 필요합니다."
        )

    if not USE_KIWOOM_REST:
        raise KiwoomAPIError(
            "Kiwoom REST API가 비활성화되었습니다. "
            "USE_KIWOOM_REST=true로 설정해주세요."
        )


def is_kiwoom_available() -> bool:
    """Kiwoom API 사용 가능 여부 확인 (호환성용)"""
    try:
        check_kiwoom_available()
        return True
    except KiwoomAPIError:
        return False


# KiwoomRestAPI 클라이언트 캐싱
_kiwoom_api_client: Optional["KiwoomRestAPI"] = None


def _get_kiwoom_client() -> "KiwoomRestAPI":
    """
    KiwoomRestAPI 클라이언트 반환 (싱글톤)

    Raises:
        KiwoomAPIError: API가 설정되지 않은 경우
    """
    global _kiwoom_api_client

    check_kiwoom_available()

    if _kiwoom_api_client is None:
        try:
            from src.kiwoom.base import KiwoomConfig
            from src.kiwoom.rest_api import KiwoomRestAPI

            config = KiwoomConfig(
                app_key=KIWOOM_APP_KEY,
                secret_key=KIWOOM_SECRET_KEY,
                base_url=KIWOOM_BASE_URL,
                ws_url=KIWOOM_WS_URL,
            )
            _kiwoom_api_client = KiwoomRestAPI(config)
            logger.info("KiwoomRestAPI client initialized for chatbot")

        except Exception as e:
            raise KiwoomAPIError(f"KiwoomRestAPI 클라이언트 초기화 실패: {e}")

    return _kiwoom_api_client


async def get_kiwoom_current_price(
    ticker: str,
    max_retries: int = 2,
    retry_delay: float = 0.5
) -> Dict[str, Any]:
    """
    Kiwoom API에서 현재가 조회 (재시도 로직 포함)

    Args:
        ticker: 종목 코드 (6자리)
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간 지연 시간 (초)

    Returns:
        현재가 정보

    Raises:
        KiwoomAPIError: API 조회 실패 시
    """
    import asyncio
    import httpx

    # 종목 코드 유효성 검사 (클라이언트 초기화 전)
    if not ticker or len(ticker) != 6 or not ticker.isdigit():
        raise KiwoomNotFoundError(ticker)

    client = _get_kiwoom_client()

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Fetching price for {ticker}, attempt {attempt + 1}/{max_retries + 1}")

            # get_daily_prices(days=5) 사용 - 최근 영업일 데이터 확보
            prices = await client.get_daily_prices(ticker, days=5)

            if prices and len(prices) > 0:
                latest = prices[-1]  # 가장 최신 데이터 (마지막 요소)
                price = latest.get("price", 0)
                change = latest.get("change", 0)

                # change_rate 계산 (전일대비 등락률)
                change_rate = 0
                if price > 0:
                    prev_price = price - change
                    if prev_price > 0:
                        change_rate = (change / prev_price) * 100

                logger.info(f"Price fetched for {ticker}: {price:,}원 ({change_rate:+.2f}%)")

                return {
                    "ticker": ticker,
                    "price": price,
                    "change": change,
                    "change_rate": round(change_rate, 2),
                    "volume": latest.get("volume", 0),
                    "timestamp": latest.get("date", datetime.now().strftime("%Y%m%d")),
                }

            # 데이터가 없는 경우
            if attempt == max_retries:
                raise KiwoomNotFoundError(ticker)

        except asyncio.TimeoutError as e:
            last_error = KiwoomTimeoutError(f"Timeout fetching price for {ticker}: {e}")
            logger.warning(f"Attempt {attempt + 1} timeout for {ticker}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                last_error = KiwoomRateLimitError(f"Rate limited for {ticker}")
                logger.warning(f"Rate limited for {ticker}")
            elif e.response.status_code == 401:
                raise KiwoomAuthenticationError(f"Authentication failed for {ticker}")
            elif e.response.status_code == 404:
                raise KiwoomNotFoundError(ticker)
            elif e.response.status_code >= 500:
                last_error = KiwoomNetworkError(f"Server error for {ticker}: {e.response.status_code}")
                logger.warning(f"Server error on attempt {attempt + 1} for {ticker}")
            else:
                last_error = KiwoomAPIError(f"HTTP error for {ticker}: {e.response.status_code}")
                logger.error(f"HTTP error for {ticker}: {e.response.status_code}")

        except KiwoomAPIError:
            raise  # 이미 Kiwoom 에러는 다시 던짐

        except Exception as e:
            last_error = KiwoomAPIError(f"Unexpected error for {ticker}: {e}")
            logger.error(f"Unexpected error on attempt {attempt + 1} for {ticker}: {e}")

        # 재시도 전 지연 (exponential backoff)
        if attempt < max_retries:
            delay = retry_delay * (2 ** attempt)  # 0.5, 1.0, 2.0...
            logger.debug(f"Retrying in {delay}s...")
            await asyncio.sleep(delay)

    # 모든 시도 실패
    raise last_error or KiwoomAPIError(f"Failed to fetch price for {ticker} after {max_retries + 1} attempts")


async def get_kiwoom_chart_data(
    ticker: str,
    period: str = "D",
    count: int = 30
) -> List[Dict[str, Any]]:
    """
    Kiwoom API에서 차트 데이터 조회

    Args:
        ticker: 종목 코드
        period: 기간 (D=일, W=주, M=월)
        count: 조회 데이터 수

    Returns:
        차트 데이터 리스트

    Raises:
        KiwoomAPIError: API 조회 실패 시
    """
    client = _get_kiwoom_client()

    try:
        # KiwoomRestAPI.get_daily_prices() 사용
        from datetime import date, timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=count * 2)  # 여유있게

        prices = await client.get_daily_prices(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        # 최근 count개만 반환
        return [
            {
                "date": p.date.isoformat(),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices[-count:]
        ]

    except KiwoomAPIError:
        raise
    except Exception as e:
        raise KiwoomAPIError(f"Kiwoom 차트 데이터 조회 실패: {e}")


async def get_kiwoom_stock_info(ticker: str) -> Dict[str, Any]:
    """
    Kiwoom API에서 종목 기본 정보 조회

    Args:
        ticker: 종목 코드

    Returns:
        종목 정보

    Raises:
        KiwoomAPIError: 조회 실패 시
    """
    # DB 조회를 우선하고, 없을 경우 Kiwoom 가격 조회에서 정보 추출
    from src.repositories.stock_repository import StockRepository
    from src.database.session import get_db_session

    try:
        db = next(get_db_session())
        repo = StockRepository(db)
        stock = repo.get_by_ticker(ticker)

        if stock:
            return {
                "ticker": stock.ticker,
                "name": stock.name,
                "market": stock.market,
                "sector": stock.sector,
            }
    except Exception as e:
        logger.error(f"DB stock lookup failed: {e}")

    # Kiwoom API로 현재가 조회 (API 사용 가능성 확인용)
    try:
        price_data = await get_kiwoom_current_price(ticker)
        return {
            "ticker": ticker,
            "name": None,  # Kiwoom API는 종목명을 별도로 제공하지 않음
            "market": "KOSPI" if ticker.startswith("00") else "KOSDAQ",
            "sector": "기타",
            "price": price_data.get("price"),
            "change": price_data.get("change"),
            "change_rate": price_data.get("change_rate"),
        }
    except KiwoomAPIError:
        # API 실패 시 최소 정보 반환
        return {
            "ticker": ticker,
            "name": None,
            "market": "KOSPI" if ticker.startswith("00") else "KOSDAQ",
            "sector": "기타",
        }


async def get_kiwoom_market_status() -> Dict[str, Any]:
    """
    Kiwoom API에서 시장 전체 상태 조회

    Returns:
        시장 상태 정보

    Raises:
        KiwoomAPIError: API 조회 실패 시
    """
    client = _get_kiwoom_client()

    try:
        # KOSPI, KOSDAQ 지수 데이터 조회
        kospi_data = await client.get_current_price("0001")  # KOSPI 지수
        kosdaq_data = await client.get_current_price("0002")  # KOSDAQ 지수

        return {
            "status": "OPEN",
            "kospi": {
                "price": kospi_data.price if kospi_data else None,
                "change": kospi_data.change if kospi_data else None,
                "change_rate": kospi_data.change_rate if kospi_data else None,
            },
            "kosdaq": {
                "price": kosdaq_data.price if kosdaq_data else None,
                "change": kosdaq_data.change if kosdaq_data else None,
                "change_rate": kosdaq_data.change_rate if kosdaq_data else None,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except KiwoomAPIError:
        raise
    except Exception as e:
        raise KiwoomAPIError(f"Kiwoom 시장 상태 조회 실패: {e}")
