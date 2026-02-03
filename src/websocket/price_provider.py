"""
가격 데이터 제공자
DB에서 실시간 가격 데이터 조회
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone

from src.database.session import SessionLocal
from src.database.models import DailyPrice
from sqlalchemy import select, desc
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class PriceDataProvider:
    """
    가격 데이터 제공자

    DB에서 최신 가격 데이터를 조회하여 제공

    Usage:
        provider = PriceDataProvider()

        # 단일 종목 가격 조회
        price = provider.get_latest_price("005930")

        # 복수 종목 가격 조회
        prices = provider.get_latest_prices(["005930", "000660"])
    """

    def get_latest_price(self, ticker: str) -> Optional[dict]:
        """
        단일 종목 최신 가격 조회

        Args:
            ticker: 종목 코드

        Returns:
            가격 데이터 dict 또는 None
        """
        with SessionLocal() as session:
            # 최신 일자 데이터 조회
            stmt = (
                select(DailyPrice)
                .where(DailyPrice.ticker == ticker)
                .order_by(desc(DailyPrice.date))
                .limit(1)
            )

            result = session.execute(stmt)
            price = result.scalar_one_or_none()

            if not price:
                logger.warning(f"No price data found for {ticker}")
                return None

            return self._format_price_data(price)

    def get_latest_prices(self, tickers: List[str]) -> Dict[str, dict]:
        """
        복수 종목 최신 가격 조회 (단일 쿼리 최적화)

        Args:
            tickers: 종목 코드 리스트

        Returns:
            ticker -> 가격 데이터 매핑
        """
        if not tickers:
            return {}

        with SessionLocal() as session:
            # 각 종목별 최신 일자 데이터 조회 (단일 쿼리)
            # Subquery: 각 종목의 최신 일자 찾기
            from sqlalchemy import func, and_

            latest_dates = (
                select(
                    DailyPrice.ticker,
                    func.max(DailyPrice.date).label('max_date')
                )
                .where(DailyPrice.ticker.in_(tickers))
                .group_by(DailyPrice.ticker)
                .subquery()
            )

            # 메인 쿼리: 최신 일자의 가격 데이터 조회
            stmt = (
                select(DailyPrice)
                .join(
                    latest_dates,
                    and_(
                        DailyPrice.ticker == latest_dates.c.ticker,
                        DailyPrice.date == latest_dates.c.max_date
                    )
                )
            )

            result = session.execute(stmt)
            prices = result.scalars().all()

            # ticker를 키로 하는 딕셔너리 반환
            return {
                price.ticker: self._format_price_data(price)
                for price in prices
            }

    def get_recent_prices(
        self,
        ticker: str,
        days: int = 5
    ) -> List[dict]:
        """
        최근 N일 가격 데이터 조회

        Args:
            ticker: 종목 코드
            days: 조회 일수

        Returns:
            가격 데이터 리스트
        """
        with SessionLocal() as session:
            # 최근 N일 데이터 조회
            stmt = (
                select(DailyPrice)
                .where(DailyPrice.ticker == ticker)
                .order_by(desc(DailyPrice.date))
                .limit(days)
            )

            result = session.execute(stmt)
            prices = result.scalars().all()

            return [
                self._format_price_data(price)
                for price in prices
            ]

    def _format_price_data(self, price: DailyPrice) -> dict:
        """
        가격 데이터 포맷팅

        Args:
            price: DailyPrice 모델 인스턴스

        Returns:
            포맷팅된 dict
        """
        # 전일 대비 등락률 계산
        change = price.close_price - price.open_price
        change_rate = (change / price.open_price * 100) if price.open_price and price.open_price > 0 else 0

        return {
            "ticker": price.ticker,
            "date": price.date.isoformat(),
            "open": float(price.open_price),
            "high": float(price.high_price),
            "low": float(price.low_price),
            "close": float(price.close_price),
            "volume": int(price.volume),
            "change": round(change, 2),
            "change_rate": round(change_rate, 2),
        }


class RealTimePriceService:
    """
    실시간 가격 서비스

    주기적으로 가격 데이터를 조회하여 브로드캐스트

    Usage:
        service = RealTimePriceService(tickers=["005930", "000660"])
        await service.start()
    """

    def __init__(
        self,
        tickers: List[str],
        interval_seconds: int = 5,
        use_real_data: bool = True,
    ):
        """
        Args:
            tickers: 조회할 종목 리스트
            interval_seconds: 조회 주기 (초)
            use_real_data: 실제 데이터 사용 여부 (False이면 Mock 데이터)
        """
        self.tickers = tickers
        self.interval_seconds = interval_seconds
        self.use_real_data = use_real_data
        self.price_provider = PriceDataProvider()
        self._is_running = False
        self._task = None

    async def _broadcast_loop(self):
        """브로드캐스트 루프"""
        from src.websocket.server import connection_manager

        while self._is_running:
            try:
                # 가격 데이터 조회
                if self.use_real_data:
                    # DB 조회는 동기 함수이므로 await 사용 안 함
                    prices = self.price_provider.get_latest_prices(self.tickers)

                    # DB에 데이터가 없으면 Mock 데이터로 fallback
                    if not prices:
                        logger.warning("No price data in DB, falling back to mock data")
                        prices = self._generate_mock_prices()
                    else:
                        # 일부 종목만 데이터가 있는 경우 나머지는 Mock 데이터 채움
                        for ticker in self.tickers:
                            if ticker not in prices:
                                logger.warning(f"No price data for {ticker}, using mock")
                                prices[ticker] = self._generate_mock_price_for_ticker(ticker)
                else:
                    prices = self._generate_mock_prices()

                # 브로드캐스트
                for ticker, data in prices.items():
                    await connection_manager.broadcast(
                        {
                            "type": "price_update",
                            "ticker": ticker,
                            "data": data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        topic=f"price:{ticker}",
                    )

                logger.debug(f"Broadcasted prices for {len(prices)} tickers")

            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")

            # 대기
            import asyncio
            await asyncio.sleep(self.interval_seconds)

    def _generate_mock_prices(self) -> Dict[str, dict]:
        """Mock 가격 데이터 생성 (테스트용)"""
        import random
        mock_prices = {}

        for ticker in self.tickers:
            base_prices = {
                "005930": 82500,  # 삼성전자
                "000660": 92000,  # SK하이닉스
            }

            base_price = base_prices.get(ticker, 50000)
            change = random.randint(-500, 500)
            change_rate = (change / base_price) * 100

            mock_prices[ticker] = {
                "ticker": ticker,
                "date": datetime.now(timezone.utc).date().isoformat(),
                "open": base_price,
                "high": base_price + random.randint(0, 1000),
                "low": base_price - random.randint(0, 1000),
                "close": base_price + change,
                "volume": random.randint(1000000, 20000000),
                "change": change,
                "change_rate": round(change_rate, 2),
            }

        return mock_prices

    def _generate_mock_price_for_ticker(self, ticker: str) -> dict:
        """단일 종목 Mock 가격 데이터 생성"""
        import random

        base_prices = {
            "005930": 82500,  # 삼성전자
            "000660": 92000,  # SK하이닉스
        }

        base_price = base_prices.get(ticker, 50000)
        change = random.randint(-500, 500)
        change_rate = (change / base_price) * 100

        return {
            "ticker": ticker,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "open": base_price,
            "high": base_price + random.randint(0, 1000),
            "low": base_price - random.randint(0, 1000),
            "close": base_price + change,
            "volume": random.randint(1000000, 20000000),
            "change": change,
            "change_rate": round(change_rate, 2),
        }

    async def start(self):
        """서비스 시작"""
        if self._is_running:
            logger.warning("RealTimePriceService is already running")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"RealTimePriceService started for {len(self.tickers)} tickers")

    async def stop(self):
        """서비스 중지"""
        if not self._is_running:
            return

        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("RealTimePriceService stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._is_running


# 전역 서비스 인스턴스 (싱글톤)
_realtime_price_service: Optional[RealTimePriceService] = None


def get_realtime_service() -> Optional[RealTimePriceService]:
    """전역 RealTimePriceService 인스턴스 반환"""
    return _realtime_price_service


def init_realtime_service(
    tickers: List[str],
    interval_seconds: int = 5,
    use_real_data: bool = True,
) -> RealTimePriceService:
    """
    전역 RealTimePriceService 초기화

    Args:
        tickers: 조회할 종목 리스트
        interval_seconds: 조회 주기 (초)
        use_real_data: 실제 데이터 사용 여부

    Returns:
        RealTimePriceService 인스턴스
    """
    global _realtime_price_service

    _realtime_price_service = RealTimePriceService(
        tickers=tickers,
        interval_seconds=interval_seconds,
        use_real_data=use_real_data,
    )

    return _realtime_price_service
