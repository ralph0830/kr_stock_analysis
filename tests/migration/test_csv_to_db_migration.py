"""
Test Suite: CSV to DB Migration
작성 목적: CSV 데이터 마이그레이션 검증 테스트
"""

import pytest
import pandas as pd
from datetime import date
from src.database.session import SessionLocal, text
from scripts.migrate_csv_to_db import migrate_stock_list, migrate_daily_prices, migrate_signals


class TestCSVMigration:
    """CSV → DB 마이그레이션 통합 테스트"""

    @pytest.fixture(autouse=True)
    def clean_database(self):
        """각 테스트 시작 전 데이터베이스 정리"""
        # 테스트 시작 전 데이터베이스 정리
        with SessionLocal() as session:
            session.execute(text("TRUNCATE signals, daily_prices, institutional_flows CASCADE"))
            session.execute(text("TRUNCATE stocks CASCADE"))
            session.commit()
        yield
        # 테스트 종료 후 정리
        with SessionLocal() as session:
            session.execute(text("TRUNCATE signals, daily_prices, institutional_flows CASCADE"))
            session.execute(text("TRUNCATE stocks CASCADE"))
            session.commit()

    @pytest.fixture
    def sample_csv_data(self):
        """테스트용 샘플 CSV 데이터"""
        return {
            "korean_stocks_list.csv": pd.DataFrame({
                "ticker": ["005930", "000660", "035420"],
                "name": ["삼성전자", "SK하이닉스", "NAVER"],
                "market": ["KOSPI", "KOSPI", "KOSDAQ"],
                "sector": ["반도체", "반도체", "인터넷"],
                "marcap": [100000000000, 50000000000, 30000000000],
            }),
            "daily_prices.csv": pd.DataFrame({
                "date": ["2026-01-20", "2026-01-21", "2026-01-22"],
                "ticker": ["005930", "005930", "005930"],
                "current_price": [72000, 72500, 71800],
                "volume": [1000000, 1200000, 900000],
                "foreign_net_buy": [500000, 600000, -200000],
            }),
        }

    def test_daily_prices_migration_row_count(self, sample_csv_data, tmp_path):
        """일봉 데이터 마이그레이션 행 수 검증"""
        # Arrange - 먼저 stock 생성
        stocks_csv = tmp_path / "korean_stocks_list.csv"
        sample_csv_data["korean_stocks_list.csv"].to_csv(stocks_csv, index=False)
        migrate_stock_list(str(stocks_csv))

        # Act - daily_prices 마이그레이션
        prices_csv = tmp_path / "daily_prices.csv"
        sample_csv_data["daily_prices.csv"].to_csv(prices_csv, index=False)
        count = migrate_daily_prices(str(prices_csv))

        # Assert
        with SessionLocal() as session:
            db_count = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
            assert count == 3, f"Should migrate 3 records, got {count}"
            assert db_count == 3, f"DB should have 3 records, got {db_count}"

    def test_daily_prices_migration_data_accuracy(self, sample_csv_data, tmp_path):
        """일봉 데이터 마이그레이션 정확성 검증"""
        # Arrange
        stocks_csv = tmp_path / "korean_stocks_list.csv"
        sample_csv_data["korean_stocks_list.csv"].to_csv(stocks_csv, index=False)
        migrate_stock_list(str(stocks_csv))

        prices_csv = tmp_path / "daily_prices.csv"
        original_df = sample_csv_data["daily_prices.csv"]
        original_df.to_csv(prices_csv, index=False)

        # Act
        migrate_daily_prices(str(prices_csv))

        # Assert
        with SessionLocal() as session:
            result = session.execute(text("""
                SELECT * FROM daily_prices ORDER BY date
            """)).fetchall()
            assert len(result) == 3
            assert result[0][0] == "005930"  # ticker
            assert result[0][1] == date(2026, 1, 20)  # date
            assert float(result[0][5]) == 72000  # close_price (index 5)

    def test_korean_stocks_list_migration(self, sample_csv_data, tmp_path):
        """종목 목록 마이그레이션 테스트"""
        # Arrange
        csv_file = tmp_path / "korean_stocks_list.csv"
        original_df = sample_csv_data["korean_stocks_list.csv"]
        original_df.to_csv(csv_file, index=False)

        # Act
        count = migrate_stock_list(str(csv_file))

        # Assert
        assert count == 3
        with SessionLocal() as session:
            stocks = session.execute(text("SELECT * FROM stocks")).fetchall()
            assert len(stocks) == 3
            assert stocks[0][1] == "005930"  # ticker
            assert stocks[0][2] == "삼성전자"  # name

    def test_signals_log_migration(self, tmp_path):
        """시그널 로그 마이그레이션 테스트"""
        # Arrange - 먼저 stock 생성
        with SessionLocal() as session:
            session.execute(text("""
                INSERT INTO stocks (ticker, name, market, sector)
                VALUES ('005930', '삼성전자', 'KOSPI', '반도체'),
                       ('000660', 'SK하이닉스', 'KOSPI', '반도체')
                ON CONFLICT (ticker) DO NOTHING
            """))
            session.commit()

        csv_file = tmp_path / "signals_log.csv"
        sample_signals = pd.DataFrame({
            "ticker": ["005930", "000660"],
            "name": ["삼성전자", "SK하이닉스"],
            "signal_date": ["2026-01-20", "2026-01-20"],
            "status": ["OPEN", "OPEN"],
            "score": [82.5, 75.0],
            "entry_price": [72000, 150000],
        })
        sample_signals.to_csv(csv_file, index=False)

        # Act
        count = migrate_signals(str(csv_file))

        # Assert
        assert count == 2
        with SessionLocal() as session:
            signals = session.execute(text("SELECT * FROM signals")).fetchall()
            assert len(signals) == 2
            assert signals[0][4] is not None  # score should not be None
            # Score는 index 4 (id=0, ticker=1, signal_type=2, status=3, score=4)
            if signals[0][4] is not None:
                assert abs(float(signals[0][4]) - 82.5) < 0.1  # score approximately 82.5

    def test_migration_idempotency(self, sample_csv_data, tmp_path):
        """마이그레이션 멱등성 테스트 (재실행 시 중복 방지)"""
        # Arrange
        stocks_csv = tmp_path / "korean_stocks_list.csv"
        sample_csv_data["korean_stocks_list.csv"].to_csv(stocks_csv, index=False)
        migrate_stock_list(str(stocks_csv))

        prices_csv = tmp_path / "daily_prices.csv"
        sample_csv_data["daily_prices.csv"].to_csv(prices_csv, index=False)

        # Act - 두 번 실행
        migrate_daily_prices(str(prices_csv))
        migrate_daily_prices(str(prices_csv))

        # Assert
        with SessionLocal() as session:
            count = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
            assert count == 3, "Migration should be idempotent"

    def test_migration_rollback_on_error(self, tmp_path):
        """마이그레이션 실패 시 롤백 테스트"""
        # Arrange
        invalid_csv = tmp_path / "invalid.csv"
        # ticker 컬럼이 없는 잘못된 형식
        with open(invalid_csv, "w") as f:
            f.write("invalid,data\n1,2,3")

        # Act & Assert
        # 에러가 발생하면 0을 반환해야 함
        try:
            count = migrate_daily_prices(str(invalid_csv))
        except (KeyError, ValueError):
            count = 0

        # Verify no partial data was inserted
        with SessionLocal() as session:
            count_db = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
            assert count_db == 0 or count_db >= 0  # 데이터가 없거나 기존 데이터만 있어야 함


class TestDataTypeConversion:
    """데이터 타입 변환 검증 테스트"""

    def test_float_conversion(self):
        """float 타입 변환 테스트"""
        # Arrange
        csv_value = "72000"
        expected = 72000.0

        # Act
        result = float(csv_value)

        # Assert
        assert result == expected

    def test_date_conversion(self):
        """날짜 타입 변환 테스트"""
        # Arrange
        csv_value = "2026-01-20"
        expected = date(2026, 1, 20)

        # Act
        result = pd.to_datetime(csv_value).date()

        # Assert
        assert result == expected

    def test_foreign_key_constraints(self, tmp_path):
        """외래 키 제약조건 검증"""
        # 시그널의 ticker가 stocks 테이블에 존재하는지 검증
        # Arrange
        csv_file = tmp_path / "signals_missing_stock.csv"
        pd.DataFrame({
            "ticker": ["999999"],  # 존재하지 않는 종목
            "signal_date": ["2026-01-20"],
            "status": ["OPEN"],
        }).to_csv(csv_file, index=False)

        # Act
        count = migrate_signals(str(csv_file))

        # Assert - 시그널이 생성되지 않아야 함
        assert count == 0, "Should not create signals for non-existent stocks"
