"""
KR Stock - Database Configuration
PostgreSQL + TimescaleDB 설정
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kr_stock"
)

# Engine 설정
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,  # True로 설정하면 SQL 로그 출력
    future=True,  # SQLAlchemy 2.0 스타일
)

# SessionFactory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# Base 모델
Base = declarative_base()


def get_db_session() -> Session:
    """
    데이터베이스 세션 생성 (Dependency Injection용)

    Yields:
        Session: SQLAlchemy 세션
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """
    데이터베이스 초기화
    - 테이블 생성
    - TimescaleDB 확장 설치
    """
    from src.database.models import Stock, Signal, DailyPrice, InstitutionalFlow

    # 테이블 생성
    Base.metadata.create_all(bind=engine)

    # TimescaleDB 확장 설치
    with engine.begin() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        # 하이퍼테이블 생성 (기존 테이블 있으면 스킵)
        try:
            conn.execute("""
                SELECT create_hypertable('daily_prices', 'date', if_not_exists => TRUE);
            """)
            conn.execute("""
                SELECT create_hypertable('institutional_flows', 'date', if_not_exists => TRUE);
            """)
        except Exception:
            pass  # 이미 존재하면 무시
