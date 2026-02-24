"""
실시간 데이터 수집기

Kiwoom REST API를 사용하여 일봉 데이터와 실시간 가격을 수집합니다.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)


class RealtimeDataCollector:
    """
    실시간 데이터 수집기

    Kiwoom REST API를 사용하여 일봉 데이터와 실시간 가격을 수집합니다.
    """

    def __init__(self, kiwoom_api=None):
        """
        초기화

        Args:
            kiwoom_api: KiwoomRestAPI 인스턴스 (선택, 없으면 환경변수에서 생성)
        """
        self._api = kiwoom_api

    async def _get_api(self):
        """API 인스턴스 가져오기 (lazy init)"""
        if self._api is None:
            from src.kiwoom.rest_api import KiwoomRestAPI
            self._api = KiwoomRestAPI.from_env()
        return self._api

    async def collect_daily_prices(
        self,
        ticker: str,
        db,
        days: int = 30,
        base_date: Optional[str] = None,
        adjusted_price: bool = True,
    ) -> int:
        """
        단일 종목 일봉 데이터 수집

        Args:
            ticker: 종목 코드 (6자리)
            db: DB 세션
            days: 조회 일수
            base_date: 기준일자 (YYYYMMDD, None이면 오늘)
            adjusted_price: 수정주가 사용 여부

        Returns:
            수집된 데이터 수
        """
        api = await self._get_api()

        try:
            # Kiwoom API에서 일봉 차트 데이터 조회
            chart_data = await api.get_stock_daily_chart(
                ticker=ticker,
                days=days,
                base_date=base_date,
                adjusted_price=adjusted_price,
            )

            if not chart_data:
                logger.debug(f"No daily chart data for {ticker}")
                return 0

            # DB에 저장
            count = 0
            for item in chart_data:
                try:
                    # 날짜 변환 (YYYYMMDD -> YYYY-MM-DD)
                    date_str = item.get("date", "")
                    if len(date_str) == 8:
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        formatted_date = date_str

                    # UPSERT 사용 (ON CONFLICT)
                    db.execute(
                        text("""
                            INSERT INTO daily_prices (
                                ticker, date, open_price, high_price, low_price,
                                close_price, volume
                            ) VALUES (
                                :ticker, :date, :open, :high, :low, :close, :volume
                            )
                            ON CONFLICT (ticker, date) DO UPDATE SET
                                open_price = EXCLUDED.open_price,
                                high_price = EXCLUDED.high_price,
                                low_price = EXCLUDED.low_price,
                                close_price = EXCLUDED.close_price,
                                volume = EXCLUDED.volume
                        """),
                        {
                            "ticker": ticker,
                            "date": formatted_date,
                            "open": item.get("open", 0),
                            "high": item.get("high", 0),
                            "low": item.get("low", 0),
                            "close": item.get("close", 0),
                            "volume": item.get("volume", 0),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Error inserting daily price for {ticker} {date_str}: {e}")

            db.commit()
            logger.info(f"Collected {count} daily prices for {ticker}")
            return count

        except Exception as e:
            logger.error(f"Error collecting daily prices for {ticker}: {e}")
            db.rollback()
            return 0

    async def collect_daily_prices_for_tickers(
        self,
        tickers: List[str],
        db,
        days: int = 30,
        base_date: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        다중 종목 일봉 데이터 수집

        Args:
            tickers: 종목 코드 리스트
            db: DB 세션
            days: 조회 일수
            base_date: 기준일자

        Returns:
            종목별 수집된 데이터 수 딕셔너리
        """
        results = {}

        for ticker in tickers:
            try:
                count = await self.collect_daily_prices(
                    ticker=ticker,
                    db=db,
                    days=days,
                    base_date=base_date,
                )
                results[ticker] = count

                # Rate Limiting 방지를 위한 딜레이
                import asyncio
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error collecting daily prices for {ticker}: {e}")
                results[ticker] = 0

        return results

    async def collect_current_price(
        self,
        ticker: str,
    ) -> Optional[Dict[str, Any]]:
        """
        현재가 수집

        Args:
            ticker: 종목 코드

        Returns:
            현재가 정보 딕셔너리 또는 None
        """
        api = await self._get_api()

        try:
            price_data = await api.get_current_price(ticker)

            if price_data is None:
                logger.debug(f"No current price data for {ticker}")
                return None

            return {
                "ticker": ticker,
                "price": price_data.price,
                "change": price_data.change,
                "change_rate": price_data.change_rate,
                "volume": price_data.volume,
                "bid_price": price_data.bid_price,
                "ask_price": price_data.ask_price,
                "timestamp": price_data.timestamp,
            }

        except Exception as e:
            logger.error(f"Error collecting current price for {ticker}: {e}")
            return None

    async def collect_current_prices_for_tickers(
        self,
        tickers: List[str],
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        다중 종목 현재가 수집

        Redis에서 실시간 가격을 우선 조회하고, 없으면 Kiwoom API를 사용합니다.

        Args:
            tickers: 종목 코드 리스트

        Returns:
            종목별 현재가 정보 딕셔너리
        """
        # 먼저 Redis에서 실시간 가격 조회
        results = await self._get_prices_from_redis(tickers)

        # Redis에서 가져오지 못한 종목은 Kiwoom API로 조회
        missing_tickers = [t for t in tickers if t not in results or results[t] is None]
        if missing_tickers:
            logger.info(f"Redis에 없는 종목 {len(missing_tickers)}개를 Kiwoom API로 조회")
            for ticker in missing_tickers:
                try:
                    price_data = await self.collect_current_price(ticker)
                    results[ticker] = price_data

                    # Rate Limiting 방지
                    import asyncio
                    await asyncio.sleep(0.05)

                except Exception as e:
                    logger.error(f"Error collecting current price for {ticker}: {e}")
                    results[ticker] = None

        return results

    async def _get_prices_from_redis(
        self,
        tickers: List[str],
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        API Gateway 내부 엔드포인트에서 실시간 가격 조회

        API Gateway의 PriceUpdateBroadcaster가 캐시한 가격 데이터를 읽어옵니다.

        Args:
            tickers: 종목 코드 리스트

        Returns:
            종목별 현재가 정보 딕셔너리
        """
        try:
            import httpx
            import os

            # API Gateway 내부 엔드포인트 URL
            api_gateway_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:5111")
            tickers_param = ",".join(tickers)

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{api_gateway_url}/internal/prices",
                    params={"tickers": tickers_param}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        cached_prices = data.get("data", {})

                        # 결과 변환
                        results = {}
                        for ticker in tickers:
                            if ticker in cached_prices:
                                price_data = cached_prices[ticker]
                                results[ticker] = {
                                    "price": price_data.get("price", 0),
                                    "change": price_data.get("change", 0),
                                    "change_rate": price_data.get("change_rate", 0.0),
                                    "volume": price_data.get("volume", 0),
                                    "timestamp": price_data.get("timestamp"),
                                }
                                logger.debug(f"API Gateway에서 {ticker} 가격 조회: {price_data.get('price')}")
                            else:
                                results[ticker] = None

                        logger.info(f"API Gateway에서 {len([r for r in results.values() if r is not None])}/{len(tickers)} 종목 가격 조회")
                        return results

        except Exception as e:
            logger.warning(f"API Gateway 가격 조회 실패: {e}, Kiwoom API fallback 예정")

        return {ticker: None for ticker in tickers}

    async def collect_and_broadcast_prices(
        self,
        tickers: List[str],
        connection_manager=None,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        현재가 수집 후 브로드캐스트

        Args:
            tickers: 종목 코드 리스트
            connection_manager: WebSocket ConnectionManager (선택)

        Returns:
            종목별 현재가 정보 딕셔너리
        """
        # 현재가 수집
        prices = await self.collect_current_prices_for_tickers(tickers)

        # 브로드캐스트
        if connection_manager:
            from services.daytrading_scanner.broadcaster import broadcast_price_update

            for ticker, price_data in prices.items():
                if price_data:
                    try:
                        await broadcast_price_update(
                            ticker=ticker,
                            price_data=price_data,
                            connection_manager=connection_manager,
                        )
                    except Exception as e:
                        logger.error(f"Error broadcasting price for {ticker}: {e}")

        return prices
