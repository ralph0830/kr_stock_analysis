#!/usr/bin/env python3
"""
Ralph Stock - Database Initialization Script

데이터베이스 테이블 생성 및 TimescaleDB 확장 설치

Usage:
    python scripts/init_db.py          # 로컬 실행
    uv run python scripts/init_db.py   # uv 실행
    docker compose run --rm db-init    # Docker 실행
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import init_db, engine
from src.database.models import (
    Stock, Signal, DailyPrice, InstitutionalFlow,
    MarketStatus, BacktestResult, AIAnalysis
)
from src.database.models.daytrading_signal import DaytradingSignal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """데이터베이스 초기화 실행"""
    try:
        logger.info("🔧 데이터베이스 초기화 시작...")

        # 연결 테스트
        with engine.connect() as conn:
            logger.info(f"✅ 데이터베이스 연결 성공: {engine.url.render_as_string(hide_password=True)}")

        # 테이블 생성
        init_db()

        logger.info("✅ 데이터베이스 초기화 완료!")
        logger.info("📋 생성된 테이블:")
        for model in [Stock, Signal, DailyPrice, InstitutionalFlow, MarketStatus, BacktestResult, AIAnalysis, DaytradingSignal]:
            logger.info(f"   - {model.__tablename__}")

    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
