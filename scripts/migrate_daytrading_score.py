"""
Daytrading Signal Schema Migration
total_score → score 필드명 변경

실행:
    uv run python scripts/migrate_daytrading_score.py
"""

import logging
import os
import sys

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text
from src.database.session import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """total_score 컬럼을 score로 변경"""

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # 트랜잭션 시작
        trans = conn.begin()

        try:
            # 1. score 컬럼이 이미 존재하는지 확인
            check_column = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'daytrading_signals'
                AND column_name = 'score'
            """)
            result = conn.execute(check_column)
            score_exists = result.first() is not None

            if score_exists:
                logger.info("score 컬럼이 이미 존재합니다. 마이그레이션 건너뜀.")
                trans.commit()
                return

            # 2. total_score 컬럼 확인
            check_total = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'daytrading_signals'
                AND column_name = 'total_score'
            """)
            result = conn.execute(check_total)
            total_exists = result.first() is not None

            if not total_exists:
                logger.info("total_score 컬럼이 존재하지 않습니다. score 컬럼만 생성합니다.")

                # score 컬럼 생성
                conn.execute(text("""
                    ALTER TABLE daytrading_signals
                    ADD COLUMN score INTEGER NOT NULL DEFAULT 0
                """))
                logger.info("score 컬럼 생성 완료")
            else:
                # 3. total_score → score 컬럼명 변경
                logger.info("total_score 컬럼을 score로 변경합니다...")

                # PostgreSQL 9.1+ 방식: ALTER TABLE ... RENAME COLUMN
                conn.execute(text("""
                    ALTER TABLE daytrading_signals
                    RENAME COLUMN total_score TO score
                """))
                logger.info("컬럼명 변경 완료: total_score → score")

            # 4. 인덱스 업데이트
            # 기존 인덱스 삭제 후 새 인덱스 생성
            logger.info("인덱스 업데이트...")

            # ix_daytrading_signals_score 인덱스 확인
            check_index = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'daytrading_signals'
                AND indexname = 'ix_daytrading_signals_score'
            """)
            result = conn.execute(check_index)
            index_exists = result.first() is not None

            if not index_exists:
                conn.execute(text("""
                    CREATE INDEX ix_daytrading_signals_score
                    ON daytrading_signals(score)
                """))
                logger.info("score 인덱스 생성 완료")

            # 5. 기존 total_score 인덱스 삭제 (존재하는 경우)
            check_old_index = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'daytrading_signals'
                AND indexname = 'ix_daytrading_signals_total_score'
            """)
            result = conn.execute(check_old_index)
            old_index_exists = result.first() is not None

            if old_index_exists:
                conn.execute(text("""
                    DROP INDEX IF EXISTS ix_daytrading_signals_total_score
                """))
                logger.info("기존 total_score 인덱스 삭제 완료")

            trans.commit()
            logger.info("✅ 마이그레이션 완료!")

        except Exception as e:
            trans.rollback()
            logger.error(f"❌ 마이그레이션 실패: {e}")
            raise


def rollback():
    """score 컬럼을 다시 total_score로 되돌림"""

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        trans = conn.begin()

        try:
            logger.info("롤백: score → total_score")

            conn.execute(text("""
                ALTER TABLE daytrading_signals
                RENAME COLUMN score TO total_score
            """))

            # 인덱스 롤백
            conn.execute(text("""
                DROP INDEX IF EXISTS ix_daytrading_signals_score
            """))

            conn.execute(text("""
                CREATE INDEX ix_daytrading_signals_total_score
                ON daytrading_signals(total_score)
            """))

            trans.commit()
            logger.info("✅ 롤백 완료!")

        except Exception as e:
            trans.rollback()
            logger.error(f"❌ 롤백 실패: {e}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Daytrading Signal 스키마 마이그레이션")
    parser.add_argument("--rollback", action="store_true", help="롤백 실행")

    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
