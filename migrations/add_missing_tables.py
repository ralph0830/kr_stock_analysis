"""
Add missing tables: daily_prices and market_status

Revision ID: 002
Create Date: 2026-02-02
"""
import logging
import os
import sys
from sqlalchemy import text, create_engine
from dotenv import load_dotenv

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 환경 변수 로드
load_dotenv()

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/ralph_stock"
)

# Engine 설정
engine = create_engine(DATABASE_URL)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """
    누락된 테이블 생성:
    - daily_prices: 일봉 데이터 (TimescaleDB 하이퍼테이블)
    - market_status: 시장 상태 (Market Gate)
    """
    with engine.begin() as conn:
        # 1. daily_prices 테이블 생성
        logger.info("Creating daily_prices table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                ticker VARCHAR(6) NOT NULL REFERENCES stocks(ticker) ON DELETE CASCADE,
                date DATE NOT NULL,
                open_price FLOAT,
                high_price FLOAT,
                low_price FLOAT,
                close_price FLOAT NOT NULL,
                volume BIGINT NOT NULL,
                foreign_net_buy INTEGER DEFAULT 0,
                inst_net_buy INTEGER DEFAULT 0,
                retail_net_buy INTEGER DEFAULT 0,
                foreign_net_buy_amount BIGINT DEFAULT 0,
                inst_net_buy_amount BIGINT DEFAULT 0,
                trading_value BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, date)
            );
        """))

        # 인덱스 생성
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_daily_prices_date ON daily_prices(date DESC);
        """))
        logger.info("✅ daily_prices table created")

        # 2. market_status 테이블 생성
        logger.info("Creating market_status table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS market_status (
                id SERIAL PRIMARY KEY,
                date DATE UNIQUE NOT NULL,
                kospi FLOAT,
                kospi_change_pct FLOAT DEFAULT 0.0,
                kosdaq FLOAT,
                kosdaq_change_pct FLOAT DEFAULT 0.0,
                usd_krw FLOAT,
                usd_krw_change_pct FLOAT DEFAULT 0.0,
                gate VARCHAR(10),
                gate_score INTEGER DEFAULT 50,
                gate_reasons TEXT,
                sector_scores JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 인덱스 생성
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_market_status_date ON market_status(date DESC);
        """))
        logger.info("✅ market_status table created")

        # 3. TimescaleDB 하이퍼테이블 변환 (daily_prices)
        try:
            conn.execute(text("""
                SELECT create_hypertable('daily_prices', 'date', if_not_exists => TRUE);
            """))
            logger.info("✅ daily_prices converted to TimescaleDB hypertable")
        except Exception as e:
            logger.warning(f"TimescaleDB hypertable creation warning: {e}")

    logger.info("🎉 Migration completed successfully!")


def downgrade():
    """마이그레이션 롤백"""
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS daily_prices CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS market_status CASCADE;"))
    logger.info("Rollback completed")


if __name__ == "__main__":
    upgrade()
