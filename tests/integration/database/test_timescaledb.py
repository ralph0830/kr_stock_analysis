"""
Test Suite: TimescaleDB 시계열 데이터
작성 목적: TimescaleDB 하이퍼테이블 기능 검증 테스트
"""

import pytest
from datetime import datetime, timedelta
from src.database.session import engine, text


class TestTimescaleDBHypertable:
    """TimescaleDB 하이퍼테이블 테스트"""

    def test_create_hypertable_daily_prices(self):
        """일봉 데이터 하이퍼테이블 생성 테스트"""
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT hypertable_name FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'daily_prices'
            """)).fetchone()
            assert result is not None, "daily_prices hypertable should exist"
            assert result[0] == "daily_prices"

    def test_create_hypertable_institutional_flows(self):
        """수급 데이터 하이퍼테이블 생성 테스트"""
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT hypertable_name FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'institutional_flows'
            """)).fetchone()
            assert result is not None, "institutional_flows hypertable should exist"
            assert result[0] == "institutional_flows"


class TestTimeSeriesQueries:
    """시계열 데이터 쿼리 성능/기능 테스트"""

    @pytest.fixture(autouse=True)
    def sample_data(self):
        """테스트용 샘플 데이터 (자동 실행)"""
        from src.database.session import SessionLocal
        session = SessionLocal()
        try:
            # Create test stock first
            session.execute(text("""
                INSERT INTO stocks (ticker, name, market, sector)
                VALUES ('005930', '삼성전자', 'KOSPI', '반도체')
                ON CONFLICT (ticker) DO NOTHING
            """))

            # Insert sample daily prices
            for i in range(10):
                date_val = (datetime(2026, 1, 1) + timedelta(days=i)).date()
                close_price = 70000 + i * 100
                session.execute(text("""
                    INSERT INTO daily_prices (ticker, date, close_price, volume)
                    VALUES ('005930', :date, :close_price, 1000000)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                """), {"date": date_val, "close_price": close_price})
            session.commit()
        finally:
            session.close()

    def test_time_bucket_query(self):
        """TimescaleDB time_bucket 쿼리 테스트"""
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT time_bucket('1 day', date) AS day, ticker,
                       AVG(close_price) as avg_price
                FROM daily_prices
                WHERE date BETWEEN '2026-01-01' AND '2026-01-10'
                GROUP BY day, ticker
                ORDER BY day
                LIMIT 5
            """)).fetchall()
            assert len(result) > 0, "Should return aggregated data"

    def test_time_range_query_performance(self):
        """시간 범위 쿼리 성능 테스트"""
        import time
        start = time.time()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM daily_prices
                WHERE date BETWEEN '2026-01-01' AND '2026-01-31'
            """)).fetchall()
        elapsed = (time.time() - start) * 1000
        assert elapsed < 100, f"Query too slow: {elapsed}ms"

    def test_auto_partitioning(self):
        """자동 파티셔닝 기능 검증"""
        with engine.begin() as conn:
            # Insert future data
            conn.execute(text("""
                INSERT INTO daily_prices (ticker, date, close_price, volume)
                VALUES ('005930', '2026-06-01', 80000, 1000000)
                ON CONFLICT (ticker, date) DO NOTHING
            """))

            result = conn.execute(text("""
                SELECT * FROM daily_prices WHERE date = '2026-06-01'
            """)).fetchone()
            assert result is not None, "Future data should be insertable"
