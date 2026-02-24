"""
일봉 데이터 수집 스크립트

Kiwoom REST API를 사용하여 전 종목의 일봉 데이터를 수집합니다.
"""

import asyncio
import logging
from datetime import datetime

from src.database.session import get_db_session_sync
from sqlalchemy import select
from src.database.models import Stock as StockModel
from services.daytrading_scanner.realtime_data_collector import RealtimeDataCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def collect_all_daily_prices(market: str = "KOSPI", days: int = 30, limit: int = 100):
    """
    전 종목 일봉 데이터 수집

    Args:
        market: 시장 구분 (KOSPI, KOSDAQ, ALL)
        days: 조회 일수
        limit: 최대 종목 수
    """
    logger.info(f"📊 {market} 일봉 데이터 수집 시작... (최대 {limit}종목, {days}일)")

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

        result = db.execute(query.limit(limit))
        stocks = list(result.scalars().all())

        logger.info(f"총 {len(stocks)}개 종목 조회됨")

        # 수집기 생성
        collector = RealtimeDataCollector()

        # 일봉 데이터 수집
        total_collected = 0
        success_count = 0
        failed_count = 0

        for i, stock in enumerate(stocks, 1):
            try:
                count = await collector.collect_daily_prices(
                    ticker=stock.ticker,
                    db=db,
                    days=days,
                )

                total_collected += count

                if count > 0:
                    success_count += 1
                    logger.info(f"[{i}/{len(stocks)}] {stock.ticker} ({stock.name}): {count}건 수집 ✅")
                else:
                    failed_count += 1
                    logger.warning(f"[{i}/{len(stocks)}] {stock.ticker} ({stock.name}): 데이터 없음 ⚠️")

                # Rate Limiting 방지 (0.2초 딜레이)
                await asyncio.sleep(0.2)

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [{i}/{len(stocks)}] {stock.ticker} ({stock.name}): {e}")

        logger.info(f"\n✅ 수집 완료")
        logger.info(f"   총 수집: {total_collected}건")
        logger.info(f"   성공: {success_count}종목")
        logger.info(f"   실패: {failed_count}종목")

        return {
            "total_collected": total_collected,
            "success": success_count,
            "failed": failed_count,
        }


if __name__ == "__main__":
    import sys

    # 파라미터 파싱
    market = sys.argv[1] if len(sys.argv) > 1 else "KOSPI"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    logger.info(f"실행 파라미터: market={market}, days={days}, limit={limit}")

    # 비동기 실행
    result = asyncio.run(collect_all_daily_prices(market=market, days=days, limit=limit))

    logger.info(f"최종 결과: {result}")
