"""
Celery Collection Tasks
데이터 수집 Celery 태스크 정의
"""

from datetime import date, timedelta
from typing import Optional
import logging
from celery import shared_task
from sqlalchemy import text

from src.database.session import SessionLocal
from src.repositories.stock_repository import StockRepository
from src.collectors.krx_collector import KRXCollector

logger = logging.getLogger(__name__)


@shared_task(name="tasks.collect_stock_list")
def collect_stock_list(market: str = "KOSPI") -> int:
    """
    종목 마스터 수집 태스크

    Args:
        market: 시장 구분 (KOSPI, KOSDAQ, ALL)

    Returns:
        수집된 종목 수
    """
    logger.info(f"📋 {market} 종목 목록 수집 시작...")

    collector = KRXCollector()
    stocks = collector.fetch_stock_list(market=market)

    count = 0
    with SessionLocal() as session:
        repo = StockRepository(session)

        for stock_data in stocks:
            try:
                repo.create_if_not_exists(
                    ticker=stock_data["ticker"],
                    name=stock_data["name"],
                    market=stock_data["market"],
                    sector=stock_data.get("sector", ""),
                    market_cap=stock_data.get("market_cap", 0),
                )
                count += 1
            except Exception as e:
                logger.error(f"❌ 종목 저장 실패 {stock_data['ticker']}: {e}")

    logger.info(f"✅ {market} 종목 {count}개 수집 완료")
    return count


@shared_task(name="tasks.collect_daily_prices")
def collect_daily_prices(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    """
    일별 시세 수집 태스크

    Args:
        ticker: 종목코드
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        수집된 데이터 수
    """
    logger.info(f"📊 {ticker} 일봉 데이터 수집 시작...")

    # 날짜 파싱
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    collector = KRXCollector()
    df = collector.fetch_daily_prices(ticker, start_date=start, end_date=end)

    if df.empty:
        period_str = f"{start_date} ~ {end_date}" if start_date and end_date else "지정 기간"
        logger.warning(f"⚠️  {ticker} 일봉 데이터 없음 (기간: {period_str})")
        return 0

    count = 0
    with SessionLocal() as session:
        for _, row in df.iterrows():
            try:
                session.execute(
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
                        "ticker": row["ticker"],
                        "date": row["date"],
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": int(row["volume"]),
                    },
                )
                count += 1
            except Exception as e:
                logger.error(f"❌ 일봉 저장 실패 {ticker} {row['date']}: {e}")

        session.commit()

    # 수집 완료 로그에 기간 정보 추가
    period_str = f"{start_date} ~ {end_date}" if start_date and end_date else "전체 기간"
    logger.info(f"✅ {ticker} 일봉 {count}개 수집 완료 (기간: {period_str})")
    return count


@shared_task(name="tasks.collect_supply_demand")
def collect_supply_demand(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    """
    외국인/기관 수급 데이터 수집 태스크

    Args:
        ticker: 종목코드
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        수집된 데이터 수
    """
    logger.info(f"💰 {ticker} 수급 데이터 수집 시작...")

    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    collector = KRXCollector()
    df = collector.fetch_supply_demand(ticker, start_date=start, end_date=end)

    if df.empty:
        logger.warning(f"⚠️  {ticker} 수급 데이터 없음")
        return 0

    count = 0
    with SessionLocal() as session:
        for _, row in df.iterrows():
            try:
                # 수급 데이터 업데이트
                session.execute(
                    text("""
                        UPDATE daily_prices
                        SET
                            foreign_net_buy = :foreign_net_buy,
                            inst_net_buy = :inst_net_buy
                        WHERE ticker = :ticker AND date = :date
                    """),
                    {
                        "ticker": ticker,
                        "date": row["date"],
                        "foreign_net_buy": row.get("foreign_net_buy", 0),
                        "inst_net_buy": row.get("inst_net_buy", 0),
                    },
                )
                count += 1
            except Exception as e:
                logger.error(f"❌ 수급 데이터 저장 실패 {ticker} {row['date']}: {e}")

        session.commit()

    logger.info(f"✅ {ticker} 수급 데이터 {count}개 수집 완료")
    return count


@shared_task(name="tasks.sync_all_data")
def sync_all_data() -> dict:
    """
    전체 데이터 동기화 태스크

    1. 종목 마스터 수집
    2. 전 종목 일봉 데이터 수집 (최근 30일)
    3. 전 종목 수급 데이터 수집 (최근 30일)

    Returns:
        수집 결과 통계
    """
    logger.info("🚀 전체 데이터 동기화 시작...")

    results = {
        "stocks": 0,
        "daily_prices": 0,
        "supply_demand": 0,
    }

    # 1. 종목 마스터 수집
    results["stocks"] += collect_stock_list("KOSPI")
    results["stocks"] += collect_stock_list("KOSDAQ")

    # 2. 일봉/수급 데이터 수집
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    with SessionLocal() as session:
        # 전체 종목 조회
        tickers = session.execute(
            text("SELECT ticker FROM stocks ORDER BY market")
        ).fetchall()

    for (ticker,) in tickers:
        try:
            results["daily_prices"] += collect_daily_prices(
                ticker,
                start_date.isoformat(),
                end_date.isoformat(),
            )
            results["supply_demand"] += collect_supply_demand(
                ticker,
                start_date.isoformat(),
                end_date.isoformat(),
            )
        except Exception as e:
            logger.error(f"❌ {ticker} 데이터 수집 실패: {e}")

    logger.info(f"✅ 전체 데이터 동기화 완료: {results}")
    return results
