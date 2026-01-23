"""
CSV to DB Migration Script
CSV 파일 기반 데이터를 PostgreSQL/TimescaleDB로 마이그레이션
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Optional
from tqdm import tqdm

# 상위 디렉토리 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import SessionLocal, engine, init_db
from src.database.models import Stock, Signal, DailyPrice, InstitutionalFlow
from src.repositories.stock_repository import StockRepository


def migrate_stock_list(csv_path: str) -> int:
    """
    종목 목록 마이그레이션

    Args:
        csv_path: korean_stocks_list.csv 파일 경로

    Returns:
        마이그레이션된 종목 수
    """
    if not os.path.exists(csv_path):
        print(f"⚠️  File not found: {csv_path}")
        return 0

    print(f"📋 Migrating stock list from {csv_path}...")
    df = pd.read_csv(csv_path, dtype={"ticker": str})

    # ticker 6자리로 zero-padding
    df["ticker"] = df["ticker"].str.zfill(6)

    with SessionLocal() as session:
        repo = StockRepository(session)

        count = 0
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Stocks"):
            try:
                repo.create_if_not_exists(
                    ticker=row["ticker"],
                    name=row["name"],
                    market=row.get("market", "KOSPI"),
                    sector=row.get("sector", ""),
                    market_cap=row.get("marcap", 0),
                    is_etf=row.get("is_etf", False),
                    is_admin=row.get("is_admin", False),
                )
                count += 1
            except Exception as e:
                print(f"❌ Error inserting {row['ticker']}: {e}")

    print(f"✅ Migrated {count} stocks")
    return count


def migrate_daily_prices(csv_path: str) -> int:
    """
    일봉 데이터 마이그레이션

    Args:
        csv_path: daily_prices.csv 파일 경로

    Returns:
        마이그레이션된 행 수
    """
    if not os.path.exists(csv_path):
        print(f"⚠️  File not found: {csv_path}")
        return 0

    print(f"📊 Migrating daily prices from {csv_path}...")
    df = pd.read_csv(csv_path, dtype={"ticker": str})
    df["ticker"] = df["ticker"].str.zfill(6)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    with SessionLocal() as session:
        count = 0
        batch_size = 1000
        records = []

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Daily Prices"):
            try:
                record = DailyPrice(
                    ticker=row["ticker"],
                    date=row["date"],
                    open_price=row.get("open", row.get("current_price")),
                    high_price=row.get("high", row.get("current_price")),
                    low_price=row.get("low", row.get("current_price")),
                    close_price=row["current_price"],
                    volume=row.get("volume", 0),
                    foreign_net_buy=row.get("foreign_net_buy", 0),
                    inst_net_buy=row.get("inst_net_buy", 0),
                    foreign_net_buy_amount=row.get("foreign_net_buy_amount", 0),
                    inst_net_buy_amount=row.get("inst_net_buy_amount", 0),
                    trading_value=row.get("trading_value", 0),
                )
                records.append(record)
                count += 1

                # Batch insert
                if len(records) >= batch_size:
                    session.bulk_save_objects(records)
                    session.commit()
                    records = []

            except Exception as e:
                print(f"❌ Error inserting {row['ticker']} {row['date']}: {e}")

        # 남은 레코드 삽입
        if records:
            session.bulk_save_objects(records)
            session.commit()

    print(f"✅ Migrated {count} daily price records")
    return count


def migrate_signals(csv_path: str) -> int:
    """
    시그널 로그 마이그레이션

    Args:
        csv_path: signals_log.csv 파일 경로

    Returns:
        마이그레이션된 시그널 수
    """
    if not os.path.exists(csv_path):
        print(f"⚠️  File not found: {csv_path}")
        return 0

    print(f"🎯 Migrating signals from {csv_path}...")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"ticker": str})
    df["ticker"] = df["ticker"].str.zfill(6)
    df["signal_date"] = pd.to_datetime(df["signal_date"]).dt.date

    with SessionLocal() as session:
        repo = SignalRepository(session)
        stock_repo = StockRepository(session)

        count = 0
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Signals"):
            try:
                # 종목 존재 확인
                stock = stock_repo.get_by_ticker(row["ticker"])
                if not stock:
                    print(f"⚠️  Stock not found: {row['ticker']}, skipping...")
                    continue

                signal = Signal(
                    ticker=row["ticker"],
                    signal_type="VCP",  # 기본 VCP
                    status=row.get("status", "OPEN"),
                    score=row.get("score", 0.0),
                    contraction_ratio=row.get("contraction_ratio", 0.0),
                    entry_price=row.get("entry_price", 0.0),
                    foreign_net_5d=row.get("foreign_5d", 0),
                    inst_net_5d=row.get("inst_5d", 0),
                    signal_date=row["signal_date"],
                    foreign_trend=row.get("foreign_trend"),
                    inst_trend=row.get("inst_trend"),
                )
                session.add(signal)
                count += 1

            except Exception as e:
                print(f"❌ Error inserting signal {row['ticker']}: {e}")

        session.commit()

    print(f"✅ Migrated {count} signals")
    return count


def verify_migration(csv_path: str, table_name: str) -> bool:
    """
    마이그레이션 검증 (CSV vs DB row count)

    Args:
        csv_path: CSV 파일 경로
        table_name: 테이블 이름

    Returns:
        검증 통과 여부
    """
    import csv

    # CSV row count
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        csv_count = sum(1 for _ in reader) - 1  # 헤더 제외

    # DB row count
    with SessionLocal() as session:
        if table_name == "stocks":
            db_count = session.execute("SELECT COUNT(*) FROM stocks").scalar()
        elif table_name == "daily_prices":
            db_count = session.execute("SELECT COUNT(*) FROM daily_prices").scalar()
        elif table_name == "signals":
            db_count = session.execute("SELECT COUNT(*) FROM signals").scalar()
        else:
            print(f"⚠️  Unknown table: {table_name}")
            return False

    success = csv_count == db_count
    if success:
        print(f"✅ {table_name}: CSV={csv_count:,} rows == DB={db_count:,} rows")
    else:
        print(f"❌ {table_name}: Mismatch! CSV={csv_count:,}, DB={db_count:,}")

    return success


def main():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("🚀 KR Stock - CSV to DB Migration")
    print("=" * 60)
    print()

    # 데이터 디렉토리 경로
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    # 데이터베이스 초기화
    print("🔧 Initializing database...")
    init_db()
    print()

    # 마이그레이션 실행
    migrations = [
        ("korean_stocks_list.csv", "stocks", migrate_stock_list),
        ("daily_prices.csv", "daily_prices", migrate_daily_prices),
        ("signals_log.csv", "signals", migrate_signals),
    ]

    for csv_file, table_name, migrate_func in migrations:
        csv_path = os.path.join(data_dir, csv_file)

        if not os.path.exists(csv_path):
            print(f"⚠️  Skipping {csv_file} (not found)")
            print()
            continue

        # 마이그레이션
        migrate_func(csv_path)

        # 검증
        verify_migration(csv_path, table_name)
        print()

    print("=" * 60)
    print("✅ Migration completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
