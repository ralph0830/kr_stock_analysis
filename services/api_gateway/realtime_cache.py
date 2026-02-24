"""
실시간 가격 캐시 레이어

WebSocket으로 수신한 실시간 가격 데이터를 캐싱하고,
API 엔드포인트에서 최신 가격을 제공합니다.

데이터 소스 우선순위:
1. WebSocket 실시간 데이터 (Kiwoom REST API)
2. DB의 최신 일봉 데이터 (fallback)
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RealtimePrice:
    """실시간 가격 데이터 모델"""
    ticker: str
    price: float
    change: float
    change_rate: float
    volume: int
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: str = "unknown"  # kiwoom_ws, kiwoom_rest, db

    def to_dict(self) -> Dict[str, Any]:
        """dict 형식으로 변환"""
        d = asdict(self)
        if self.timestamp:
            d["timestamp"] = self.timestamp.isoformat()
        return d

    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """
        데이터 유효성 확인

        Args:
            max_age_seconds: 최대 허용 데이터 나이 (초)

        Returns:
            True if data is stale (older than max_age_seconds)
        """
        if not self.timestamp:
            return True

        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age > max_age_seconds


class RealtimePriceCache:
    """
    실시간 가격 캐시

    WebSocket에서 수신한 실시간 가격을 저장하고,
    API 엔드포인트에서 조회하여 DB 데이터와의 불일치를 해결합니다.

    Usage:
        cache = RealtimePriceCache()

        # WebSocket 메시지 수신 시 업데이트
        cache.update_from_ws_message({
            "ticker": "005930",
            "data": {"price": 80000, "change": 1000, ...}
        })

        # API에서 캐시 조회
        price = cache.get("005930")
        if price and not price.is_stale():
            return price.to_dict()
        else:
            # DB에서 조회...
    """

    def __init__(self, max_age_seconds: int = 60):
        """
        초기화

        Args:
            max_age_seconds: 캐시 데이터 최대 유효 시간 (초)
        """
        self._cache: Dict[str, RealtimePrice] = {}
        self._max_age_seconds = max_age_seconds
        self._lock = asyncio.Lock()

    def update(self, ticker: str, price: RealtimePrice) -> None:
        """
        캐시 업데이트

        Args:
            ticker: 종목 코드
            price: 실시간 가격 데이터
        """
        self._cache[ticker] = price
        logger.debug(f"Updated price cache: {ticker} = {price.price} ({price.source})")

    def update_from_ws_message(self, message: Dict[str, Any]) -> None:
        """
        WebSocket 메시지에서 캐시 업데이트

        Args:
            message: WebSocket 메시지
                {
                    "ticker": "005930",
                    "data": {"price": 80000, "change": 1000, "change_rate": 1.25, ...},
                    "source": "kiwoom_ws"
                }
        """
        try:
            ticker = message.get("ticker")
            data = message.get("data", {})
            source = message.get("source", "unknown")

            if not ticker or not data:
                return

            # timestamp 파싱
            timestamp_str = message.get("timestamp")
            timestamp = None
            if timestamp_str:
                try:
                    if timestamp_str.endswith("Z"):
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            price = RealtimePrice(
                ticker=ticker,
                price=float(data.get("price", 0)),
                change=float(data.get("change", 0)),
                change_rate=float(data.get("change_rate", 0)),
                volume=int(data.get("volume", 0)),
                bid_price=float(data.get("bid_price", 0)) if data.get("bid_price") else None,
                ask_price=float(data.get("ask_price", 0)) if data.get("ask_price") else None,
                timestamp=timestamp,
                source=source,
            )

            self.update(ticker, price)
            logger.info(f"Price cache updated from WS: {ticker} = {price.price} ({source})")

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse WS message for cache: {e}, message: {message}")

    def get(self, ticker: str) -> Optional[RealtimePrice]:
        """
        캐시에서 가격 조회

        Args:
            ticker: 종목 코드

        Returns:
            RealtimePrice 또는 None (없거나 만료된 경우)
        """
        price = self._cache.get(ticker)
        if price and not price.is_stale(self._max_age_seconds):
            return price
        return None

    def get_dict(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 가격을 dict 형식으로 조회

        Args:
            ticker: 종목 코드

        Returns:
            가격 dict 또는 None
        """
        price = self.get(ticker)
        return price.to_dict() if price else None

    def get_all(self) -> Dict[str, RealtimePrice]:
        """모든 캐시 데이터 반환 (복사본)"""
        return self._cache.copy()

    def remove(self, ticker: str) -> None:
        """캐시에서 종목 제거"""
        self._cache.pop(ticker, None)

    def clear(self) -> None:
        """모든 캐시 삭제"""
        self._cache.clear()

    def cleanup_stale(self) -> int:
        """
        만료된 캐시 데이터 정리

        Returns:
            삭제된 항목 수
        """
        stale_keys = [
            ticker for ticker, price in self._cache.items()
            if price.is_stale(self._max_age_seconds)
        ]

        for ticker in stale_keys:
            self._cache.pop(ticker)

        if stale_keys:
            logger.info(f"Cleaned up {len(stale_keys)} stale cache entries")

        return len(stale_keys)

    async def cleanup_task(self, interval_seconds: int = 60):
        """
        주기적으로 만료된 캐시 정리

        Args:
            interval_seconds: 정리 간격 (초)
        """
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                self.cleanup_stale()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 반환

        Returns:
            캐시 통계 dict
        """
        total = len(self._cache)
        stale = sum(
            1 for price in self._cache.values()
            if price.is_stale(self._max_age_seconds)
        )

        # 소스별 분류
        by_source: Dict[str, int] = {}
        for price in self._cache.values():
            by_source[price.source] = by_source.get(price.source, 0) + 1

        return {
            "total_entries": total,
            "stale_entries": stale,
            "valid_entries": total - stale,
            "max_age_seconds": self._max_age_seconds,
            "by_source": by_source,
        }


# 전역 캐시 인스턴스
_realtime_price_cache: Optional[RealtimePriceCache] = None


def get_realtime_price_cache() -> RealtimePriceCache:
    """
    전역 RealtimePriceCache 인스턴스 반환

    Returns:
        RealtimePriceCache 인스턴스
    """
    global _realtime_price_cache
    if _realtime_price_cache is None:
        _realtime_price_cache = RealtimePriceCache(max_age_seconds=60)
    return _realtime_price_cache
