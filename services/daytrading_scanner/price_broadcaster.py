"""
실시간 가격 브로드캐스터

단타 시그널 종목들의 실시간 가격 업데이트를 브로드캐스트합니다.
"""

import asyncio
import logging
from typing import Set, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DaytradingPriceBroadcaster:
    """
    단타 가격 브로드캐스터

    단타 시그널 종목들의 실시간 가격 업데이트를 관리합니다.
    기존 price_broadcaster 패턴을 활용하되어 daytrading 종목만 따로 관리합니다.
    """

    def __init__(self, interval_seconds: int = 5):
        """
        초기화

        Args:
            interval_seconds: 가격 조회 간격 (기본 5초)
        """
        self._interval = interval_seconds
        self._tickers: Set[str] = set()
        self._is_running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._connection_manager = None

    def add_ticker(self, ticker: str) -> None:
        """종목 추가"""
        self._tickers.add(ticker)
        logger.debug(f"Added ticker to daytrading price broadcaster: {ticker}")

    def remove_ticker(self, ticker: str) -> None:
        """종목 제거"""
        self._tickers.discard(ticker)
        logger.debug(f"Removed ticker from daytrading price broadcaster: {ticker}")

    def set_connection_manager(self, connection_manager) -> None:
        """ConnectionManager 설정"""
        self._connection_manager = connection_manager

    async def start(self) -> None:
        """브로드캐스트 시작"""
        if self._is_running:
            logger.warning("Daytrading price broadcaster is already running")
            return

        self._is_running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"Daytrading price broadcaster started (tickers: {self._tickers})")

    async def stop(self) -> None:
        """브로드캐스트 중지"""
        if not self._is_running:
            return

        self._is_running = False

        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        logger.info("Daytrading price broadcaster stopped")

    async def _broadcast_loop(self) -> None:
        """브로드캐스트 루프"""
        logger.info("Daytrading price broadcast loop started")

        while self._is_running:
            try:
                if not self._tickers:
                    await asyncio.sleep(self._interval)
                    continue

                # 가격 조회 및 브로드캐스트
                await self._fetch_and_broadcast_prices()

                await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daytrading broadcast loop: {e}")
                await asyncio.sleep(self._interval)

    async def _fetch_and_broadcast_prices(self) -> None:
        """가격 조회 및 브로드캐스트"""
        if not self._connection_manager:
            return

        from services.daytrading_scanner.broadcaster import broadcast_price_update

        for ticker in self._tickers:
            try:
                # DB에서 가격 조회
                price_data = await self._fetch_price_from_db(ticker)
                if price_data:
                    await broadcast_price_update(ticker, price_data, self._connection_manager)
            except Exception as e:
                logger.debug(f"Error broadcasting price for {ticker}: {e}")

    async def _fetch_price_from_db(self, ticker: str) -> Optional[dict]:
        """DB에서 최신 가격 조회"""
        from src.database.session import get_db_session_sync
        from src.database.models import DailyPrice
        from sqlalchemy import select

        try:
            with get_db_session_sync() as db:
                # 최근 일봉 데이터 조회
                query = select(DailyPrice).where(
                    DailyPrice.ticker == ticker
                ).order_by(DailyPrice.date.desc()).limit(2)

                result = db.execute(query)
                prices = list(result.scalars().all())

                if not prices or len(prices) < 2:
                    return None

                current = prices[0]
                prev = prices[1]

                # 등락률 계산
                change = current.close_price - prev.close_price
                change_rate = (change / prev.close_price * 100) if prev.close_price > 0 else 0.0

                return {
                    "price": current.close_price,
                    "change": change,
                    "change_rate": round(change_rate, 2),
                    "volume": current.volume
                }
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            return None

    @property
    def active_tickers(self) -> Set[str]:
        """활성 종목 리스트 반환"""
        return self._tickers.copy()


# 전역 인스턴스
_daytrading_price_broadcaster: Optional[DaytradingPriceBroadcaster] = None


def get_daytrading_price_broadcaster() -> DaytradingPriceBroadcaster:
    """전역 DaytradingPriceBroadcaster 인스턴스 반환"""
    global _daytrading_price_broadcaster
    if _daytrading_price_broadcaster is None:
        _daytrading_price_broadcaster = DaytradingPriceBroadcaster()
    return _daytrading_price_broadcaster
