"""
Celery Collection Tasks
데이터 수집 Celery 태스크 정의
"""

from datetime import date, timedelta
from typing import Optional
import logging
import asyncio
from celery import shared_task
from sqlalchemy import text

from src.database.session import SessionLocal
from src.repositories.stock_repository import StockRepository
from src.collectors.krx_collector import KRXCollector
from src.kiwoom.rest_api import KiwoomRestAPI
from src.kiwoom.base import KiwoomConfig
import os

logger = logging.getLogger(__name__)


def _get_kiwoom_api() -> KiwoomRestAPI:
    """Kiwoom API 인스턴스 생성"""
    config = KiwoomConfig.from_env()
    return KiwoomRestAPI(config)


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
    전체 데이터 동기화 태스크 (Kiwoom API 사용)

    1. 종목 마스터 수집 (DB 기존 데이터 사용)
    2. 전 종목 일봉 데이터 수집 (Kiwoom API ka10081)
    3. 수급 데이터는 별도 처리

    Returns:
        수집 결과 통계
    """
    logger.info("🚀 전체 데이터 동기화 시작 (Kiwoom API)...")

    results = {
        "stocks": 0,
        "daily_prices": 0,
        "supply_demand": 0,
        "errors": 0,
    }

    # Kiwoom API 초기화
    try:
        api = _get_kiwoom_api()
    except Exception as e:
        logger.error(f"❌ Kiwoom API 초기화 실패: {e}")
        return results

    # 1. DB에서 전체 종목 조회
    with SessionLocal() as session:
        tickers = session.execute(
            text("SELECT ticker, name FROM stocks ORDER BY ticker")
        ).fetchall()

    logger.info(f"📋 {len(tickers)}개 종목 일봉 데이터 수집 시작...")

    # 2. 각 종목별로 Kiwoom API에서 일봉 데이터 수집
    for ticker, name in tickers:
        try:
            # Kiwoom API 호출 (새로운 event loop 사용)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                chart_data = loop.run_until_complete(_fetch_chart_data(api, ticker))
            finally:
                loop.close()

            if not chart_data:
                logger.warning(f"⚠️ {ticker} ({name}) 일봉 데이터 없음")
                continue

            # DB에 저장
            count = _save_daily_prices(ticker, chart_data)
            results["daily_prices"] += count

            # Rate limiting (Kiwoom API 제한)
            import time
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"❌ {ticker} ({name}) 일봉 수집 실패: {e}")
            results["errors"] += 1

    # API 연결 종료
    try:
        asyncio.run(api.close())
    except:
        pass

    logger.info(f"✅ 전체 데이터 동기화 완료: {results}")
    return results


async def _fetch_chart_data(api: KiwoomRestAPI, ticker: str) -> list:
    """Kiwoom API에서 일봉 데이터 조회"""
    try:
        data = await api.get_stock_daily_chart(
            ticker=ticker,
            days=30,
            adjusted_price=True
        )
        return data or []
    except Exception as e:
        logger.error(f"Kiwoom API 오류 {ticker}: {e}")
        return []


def _save_daily_prices(ticker: str, chart_data: list) -> int:
    """일봉 데이터를 DB에 저장"""
    if not chart_data:
        return 0

    count = 0
    with SessionLocal() as session:
        for item in chart_data:
            try:
                # 날짜 형식 변환 (정수 또는 문자열 모두 처리)
                date_val = item.get("date", "")
                date_str = str(date_val) if date_val else ""

                if len(date_str) == 8:
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                elif len(date_str) == 10 and "-" in date_str:
                    formatted_date = date_str  # 이미 YYYY-MM-DD 형식
                else:
                    logger.warning(f"잘못된 날짜 형식 {ticker}: {date_str}")
                    continue

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
                        "ticker": ticker,
                        "date": formatted_date,
                        "open": item.get("open") or item.get("open_pric"),
                        "high": item.get("high") or item.get("high_pric"),
                        "low": item.get("low") or item.get("low_pric"),
                        "close": item.get("close") or item.get("cur_prc"),
                        "volume": item.get("volume") or item.get("trde_qty"),
                    },
                )
                count += 1
            except Exception as e:
                logger.error(f"❌ 일봉 저장 실패 {ticker} {item.get('date')}: {e}")

        session.commit()

    logger.info(f"✅ {ticker} 일봉 {count}개 저장 완료")
    return count
