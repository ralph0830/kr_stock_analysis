"""
실시간 데이터 수집 Celery 태스크

Kiwoom REST API를 사용하여 실시간 데이터를 수집하고 브로드캐스트합니다.
"""

import logging
from celery import shared_task
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@shared_task(name="tasks.collect_all_stocks_daily_prices")
def collect_all_stocks_daily_prices(
    market: str = "ALL",
    days: int = 30,
) -> Dict[str, Any]:
    """
    전 종목 일봉 데이터 수집 태스크

    Args:
        market: 시장 구분 (KOSPI, KOSDAQ, ALL)
        days: 조회 일수

    Returns:
        수집 결과 통계
    """
    from src.database.session import get_db_session_sync
    from sqlalchemy import select
    from src.database.models import Stock as StockModel

    logger.info(f"📊 {market} 전 종목 일봉 데이터 수집 시작...")

    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "details": {},
    }

    try:
        with get_db_session_sync() as db:
            # 종목 조회
            query = select(StockModel).where(
                StockModel.is_etf == False,
                StockModel.is_admin == False,
                StockModel.is_spac == False,
                StockModel.is_bond == False,
                StockModel.is_excluded_etf == False,
            )

            if market != "ALL":
                query = query.where(StockModel.market == market)

            result = db.execute(query.limit(500))
            stocks = list(result.scalars().all())

            logger.info(f"총 {len(stocks)}개 종목 일봉 수집 시작")

            # 비동기 수집 실행
            import asyncio

            async def collect_all():
                from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector
                collector = RealtimeDataCollector()

                total_count = 0
                for stock in stocks:
                    try:
                        count = await collector.collect_daily_prices(
                            ticker=stock.ticker,
                            db=db,
                            days=days,
                        )
                        results["details"][stock.ticker] = count
                        total_count += count

                        if count > 0:
                            results["success"] += 1
                        else:
                            results["failed"] += 1

                        # Rate Limiting 방지
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"❌ {stock.ticker} 일봉 수집 실패: {e}")
                        results["failed"] += 1
                        results["details"][stock.ticker] = 0

                results["total"] = total_count
                return results

            # 비동기 실행
            result = asyncio.run(collect_all())

        logger.info(f"✅ 일봉 데이터 수집 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ 전 종목 일봉 수집 실패: {e}")
        results["error"] = str(e)
        return results


@shared_task(name="tasks.broadcast_realtime_prices")
def broadcast_realtime_prices(
    tickers: List[str],
) -> Dict[str, Any]:
    """
    실시간 가격 브로드캐스트 태스크

    Args:
        tickers: 종목 코드 리스트

    Returns:
        브로드캐스트 결과
    """
    logger.info(f"📡 {len(tickers)}개 종목 실시간 가격 브로드캐스트 시작...")

    results = {
        "total": len(tickers),
        "success": 0,
        "failed": 0,
        "prices": {},
    }

    try:
        import asyncio

        async def collect_and_broadcast():
            from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector
            from src.websocket.server import connection_manager

            collector = RealtimeDataCollector()

            # 수집 및 브로드캐스트
            prices = await collector.collect_and_broadcast_prices(
                tickers=tickers,
                connection_manager=connection_manager,
            )

            for ticker, price_data in prices.items():
                if price_data:
                    results["success"] += 1
                    results["prices"][ticker] = price_data
                else:
                    results["failed"] += 1

            return results

        result = asyncio.run(collect_and_broadcast())

        logger.info(f"✅ 실시간 가격 브로드캐스트 완료: {result['success']}개 성공")
        return result

    except Exception as e:
        logger.error(f"❌ 실시간 가격 브로드캐스트 실패: {e}")
        results["error"] = str(e)
        return results


@shared_task(name="tasks.collect_and_scan_daytrading")
def collect_and_scan_daytrading(
    market: str = "ALL",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    일봉 데이터 수집 후 단타 스캔 태스크

    Args:
        market: 시장 구분
        limit: 스캔 종목 수

    Returns:
        스캔 결과
    """
    logger.info(f"🔍 {market} 일봉 수집 및 단타 스캔 시작...")

    results = {
        "collection": {},
        "scan": {},
    }

    try:
        import asyncio

        async def collect_and_scan():
            # 1. 일봉 데이터 수집
            collection_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collect_all_stocks_daily_prices(market=market, days=20)
            )
            results["collection"] = collection_result

            # 2. 단타 스캔 실행
            from services.daytrading_scanner.scanner import DaytradingScanner
            from src.database.session import get_db_session_sync

            scanner = DaytradingScanner()

            with get_db_session_sync() as db:
                scan_results = await scanner.scan_market(
                    {"market": market, "limit": limit},
                    db
                )

            results["scan"] = {
                "count": len(scan_results),
                "signals": [
                    {
                        "ticker": r.ticker,
                        "name": r.name,
                        "score": r.total_score,
                        "grade": r.grade,
                    }
                    for r in scan_results
                ],
            }

            return results

        result = asyncio.run(collect_and_scan())

        logger.info(f"✅ 일봉 수집 및 단타 스캔 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ 일봉 수집 및 단타 스캔 실패: {e}")
        results["error"] = str(e)
        return results
