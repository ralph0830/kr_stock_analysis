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

# Kiwoom API 설정
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY", "")
KIWOOM_SECRET_KEY = os.getenv("KIWOOM_SECRET_KEY", "")
KIWOOM_BASE_URL = os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com")
KIWOOM_WS_URL = os.getenv("KIWOOM_WS_URL", "wss://api.kiwoom.com:10000/api/dostk/websocket")
USE_KIWOOM_REST = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"


def is_kiwoom_available() -> bool:
    """Kiwoom API 사용 가능 여부 확인"""
    return bool(
        KIWOOM_APP_KEY
        and KIWOOM_SECRET_KEY
        and USE_KIWOOM_REST
    )


# KiwoomRestAPI 클라이언트 캐싱
_kiwoom_api_client: Optional["KiwoomRestAPI"] = None


def _get_kiwoom_client() -> Optional["KiwoomRestAPI"]:
    """KiwoomRestAPI 클라이언트 반환 (싱글톤)"""
    global _kiwoom_api_client

    if not is_kiwoom_available():
        return None

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
            logger.error(f"KiwoomRestAPI client initialization failed: {e}")
            return None

    return _kiwoom_api_client


async def get_kiwoom_current_price(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Kiwoom API에서 현재가 조회

    참고: get_current_price() API ID 문제로 get_daily_prices(days=1)를 대신 사용

    Args:
        ticker: 종목 코드 (6자리)

    Returns:
        현재가 정보 또는 None
    """
    client = _get_kiwoom_client()
    if not client:
        logger.warning("Kiwoom API not configured")
        return None

    try:
        # get_current_price() 대신 get_daily_prices(days=1) 사용
        # (API ID ka10001 문제로 인한 우회)
        prices = await client.get_daily_prices(ticker, days=1)

        if prices and len(prices) > 0:
            latest = prices[0]  # 가장 최근 데이터
            return {
                "ticker": ticker,
                "price": latest.get("price"),
                "change": latest.get("change"),
                "volume": latest.get("volume"),
                "timestamp": latest.get("date"),
            }
        return None

    except Exception as e:
        logger.error(f"Kiwoom current price lookup failed: {e}")
        return None


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
    """
    client = _get_kiwoom_client()
    if not client:
        logger.warning("Kiwoom API not configured")
        return []

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

    except Exception as e:
        logger.error(f"Kiwoom chart data lookup failed: {e}")
        return []


async def get_kiwoom_stock_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Kiwoom API에서 종목 기본 정보 조회

    Args:
        ticker: 종목 코드

    Returns:
        종목 정보 또는 None
    """
    # Kiwoom API에는 종목 기본 정보 엔드포인트가 별도로 없을 수 있음
    # DB 조회를 우선하고, 없을 경우 Kiwoom 가격 조회에서 이름 추출
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

    # Fallback: Kiwoom API에서 가격 정보로 이름 추출 시도
    price_data = await get_kiwoom_current_price(ticker)
    if price_data:
        return {
            "ticker": ticker,
            "name": None,  # Kiwoom API는 종목명을 별도로 제공하지 않음
            "market": "KOSPI" if ticker.startswith("00") else "KOSDAQ",
            "sector": "기타",
        }

    return None


async def get_kiwoom_market_status() -> Dict[str, Any]:
    """
    Kiwoom API에서 시장 전체 상태 조회

    Returns:
        시장 상태 정보
    """
    client = _get_kiwoom_client()
    if not client:
        return {
            "status": "UNKNOWN",
            "kospi": None,
            "kosdaq": None,
            "timestamp": datetime.now().isoformat(),
        }

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

    except Exception as e:
        logger.error(f"Kiwoom market status lookup failed: {e}")
        return {
            "status": "ERROR",
            "kospi": None,
            "kosdaq": None,
            "timestamp": datetime.now().isoformat(),
        }
