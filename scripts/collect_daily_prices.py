#!/usr/bin/env python
"""
Kiwoom API를 사용하여 일별 가격 데이터 수집

DB에 있는 종목들의 최근 30일치 데이터를 수집하여 DB에 저장합니다.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import SessionLocal
from src.database.models import Stock, DailyPrice, InstitutionalFlow
from src.kiwoom.base import KiwoomConfig
from src.kiwoom.rest_api import KiwoomRestAPI
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def collect_for_stock(api: KiwoomRestAPI, ticker: str, name: str, days: int = 30) -> Dict[str, int]:
    """
    단일 종목에 대한 일별 가격 데이터 수집

    Args:
        api: KiwoomRestAPI 인스턴스
        ticker: 종목코드
        name: 종목명
        days: 수집할 일수

    Returns:
        수집된 데이터 개수 딕셔너리 {prices, flows}
    """
    logger.info(f"📊 {name}({ticker}) 데이터 수집 시작...")

    try:
        # 일별 가격 데이터 조회
        price_data_list = await api.get_daily_prices(ticker=ticker, days=days)

        if not price_data_list:
            logger.warning(f"⚠️ {name}({ticker}) - 수집된 데이터 없음")
            return {"prices": 0, "flows": 0}

        # 데이터 저장
        session = SessionLocal()
        prices_count = 0
        flows_count = 0

        try:
            for price_data in price_data_list:
                date_str = price_data["date"]
                date_obj = datetime.strptime(date_str, "%Y%m%d").date()

                # DailyPrice 저장
                # 중복 체크
                existing = session.query(DailyPrice).filter(
                    DailyPrice.ticker == ticker,
                    DailyPrice.date == date_obj
                ).first()

                if not existing:
                    daily_price = DailyPrice(
                        ticker=ticker,
                        date=date_obj,
                        open_price=price_data["price"],  # 현재가만 제공되어 임시 사용
                        high_price=price_data["price"],   # 추후 OHLC 제공 시 수정
                        low_price=price_data["price"],    # 추후 OHLC 제공 시 수정
                        close_price=price_data["price"],
                        volume=price_data["volume"],
                        # 수급 데이터 (foreign_net_buy, inst_net_buy)
                        foreign_net_buy=price_data.get("foreign", 0),
                        inst_net_buy=price_data.get("institution", 0),
                        retail_net_buy=price_data.get("individual", 0),
                        # 거래대금 (추후 계산)
                        trading_value=price_data.get("price", 0) * price_data.get("volume", 0),
                    )
                    session.add(daily_price)
                    prices_count += 1
                else:
                    # 기존 데이터 업데이트
                    existing.close_price = price_data["price"]
                    existing.volume = price_data["volume"]
                    existing.foreign_net_buy = price_data.get("foreign", 0)
                    existing.inst_net_buy = price_data.get("institution", 0)
                    existing.retail_net_buy = price_data.get("individual", 0)

                # InstitutionalFlow 저장
                existing_flow = session.query(InstitutionalFlow).filter(
                    InstitutionalFlow.ticker == ticker,
                    InstitutionalFlow.date == date_obj
                ).first()

                if not existing_flow:
                    inst_flow = InstitutionalFlow(
                        ticker=ticker,
                        date=date_obj,
                        foreign_net_buy=price_data.get("foreign", 0),
                        inst_net_buy=price_data.get("institution", 0),
                    )
                    session.add(inst_flow)
                    flows_count += 1
                else:
                    existing_flow.foreign_net_buy = price_data.get("foreign", 0)
                    existing_flow.inst_net_buy = price_data.get("institution", 0)

            session.commit()
            logger.info(f"✅ {name}({ticker}) - {prices_count}개 가격, {flows_count}개 수급 데이터 저장")

        except Exception as e:
            session.rollback()
            logger.error(f"❌ {name}({ticker}) - DB 저장 실패: {e}")
            raise
        finally:
            session.close()

        return {"prices": prices_count, "flows": flows_count}

    except Exception as e:
        logger.error(f"❌ {name}({ticker}) - 데이터 수집 실패: {e}")
        return {"prices": 0, "flows": 0}


async def collect_all_stocks(days: int = 30):
    """
    DB에 있는 모든 종목의 일별 가격 데이터 수집

    Args:
        days: 수집할 일수
    """
    logger.info("=" * 60)
    logger.info("🚀 일별 가격 데이터 수집 시작")
    logger.info("=" * 60)

    # API 초기화
    config = KiwoomConfig.from_env()
    api = KiwoomRestAPI(config)

    try:
        # 토큰 발급
        logger.info("🔑 토큰 발급 중...")
        await api.issue_token()
        logger.info("✅ 토큰 발급 완료")

        # DB에서 종목 목록 조회
        session = SessionLocal()
        try:
            stocks = session.query(Stock.ticker, Stock.name).all()
            stock_list = [(ticker, name) for ticker, name in stocks]
        finally:
            session.close()

        logger.info(f"📋 총 {len(stock_list)}개 종목 데이터 수집 예정")

        # 각 종목별 데이터 수집
        total_prices = 0
        total_flows = 0

        for ticker, name in stock_list:
            result = await collect_for_stock(api, ticker, name, days)
            total_prices += result["prices"]
            total_flows += result["flows"]

            # Rate Limiting 방지를 위해 종목 간 0.5초 지연
            await asyncio.sleep(0.5)

        logger.info("=" * 60)
        logger.info("✅ 데이터 수집 완료")
        logger.info(f"   - 총 가격 데이터: {total_prices}개")
        logger.info(f"   - 총 수급 데이터: {total_flows}개")
        logger.info("=" * 60)

        # DB 상태 확인
        session = SessionLocal()
        try:
            price_count = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
            flow_count = session.execute(text("SELECT COUNT(*) FROM institutional_flows")).scalar()

            print("\n📊 현재 DB 상태:")
            print(f"   - daily_prices: {price_count}개")
            print(f"   - institutional_flows: {flow_count}개")
        finally:
            session.close()

    finally:
        await api.close()


async def show_db_status():
    """DB 현재 상태 출력"""
    session = SessionLocal()
    try:
        stock_count = session.execute(text("SELECT COUNT(*) FROM stocks")).scalar()
        price_count = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
        flow_count = session.execute(text("SELECT COUNT(*) FROM institutional_flows")).scalar()

        print(f"\n📊 현재 DB 상태:")
        print(f"   - stocks: {stock_count}개")
        print(f"   - daily_prices: {price_count}개")
        print(f"   - institutional_flows: {flow_count}개")

        # daily_prices 데이터가 있으면 종목별 개수 출력
        if price_count > 0:
            result = session.execute(text("""
                SELECT ticker, COUNT(*) as cnt
                FROM daily_prices
                GROUP BY ticker
                ORDER BY ticker
            """))
            print(f"\n📈 종목별 가격 데이터:")
            for row in result:
                print(f"   - {row[0]}: {row[1]}개")
    finally:
        session.close()


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Kiwoom API 일별 가격 데이터 수집")
    parser.add_argument("--days", type=int, default=30, help="수집할 일수 (기본값: 30)")
    parser.add_argument("--status", action="store_true", help="DB 상태만 확인")
    args = parser.parse_args()

    if args.status:
        await show_db_status()
        return

    await collect_all_stocks(days=args.days)


if __name__ == "__main__":
    asyncio.run(main())
