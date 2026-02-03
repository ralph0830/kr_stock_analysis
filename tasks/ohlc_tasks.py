"""
OHLC 수집 Celery 태스크

WebSocket을 통한 실시간 OHLC 데이터 수집을 처리합니다.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from celery import shared_task
from sqlalchemy import select

from tasks.celery_app import celery_app
from src.database.session import get_db_session_sync
from src.database.models import Stock
from src.kiwoom.ohlc_collector import OHLCCollector, collect_ohlc_main

logger = logging.getLogger(__name__)


# 전역 수집기 인스턴스 (태스크 간 공유)
_collector_instance: Optional[OHLCCollector] = None


@shared_task(name="ohlc.start_collection")
def start_ohlc_collection(tickers: Optional[List[str]] = None, duration_seconds: int = 21600) -> dict:
    """
    OHLC 실시간 수집 시작

    Args:
        tickers: 수집할 종목 리스트 (None이면 DB에서 가져오기)
        duration_seconds: 최대 수집 시간 (초, 기본 6시간)

    Returns:
        실행 결과 dict
    """
    global _collector_instance

    # 이미 실행 중인 수집기가 있으면 중지
    if _collector_instance and _collector_instance.is_running():
        logger.warning("OHLC 수집기 이미 실행 중")
        return {"status": "already_running", "tickers": _collector_instance.get_subscribed_tickers()}

    try:
        # 종목 리스트가 없으면 DB에서 가져오기
        if tickers is None:
            tickers = _get_active_tickers_from_db()

        if not tickers:
            logger.error("수집할 종목이 없음")
            return {"status": "error", "message": "No tickers to collect"}

        logger.info(f"OHLC 수집 시작 - 종목: {len(tickers)}개, 최대 시간: {duration_seconds}초")

        # 비동기 실행을 위한 래퍼
        result = asyncio.run(_run_collection(tickers, duration_seconds))

        return result

    except Exception as e:
        logger.error(f"OHLC 수집 시작 실패: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="ohlc.stop_collection")
def stop_ohlc_collection() -> dict:
    """
    OHLC 실시간 수집 중지

    Returns:
        실행 결과 dict
    """
    global _collector_instance

    if not _collector_instance or not _collector_instance.is_running():
        return {"status": "not_running"}

    try:
        # 비동기 중지
        asyncio.run(_stop_collection())

        result = {
            "status": "stopped",
            "tickers": _collector_instance.get_subscribed_tickers() if _collector_instance else [],
        }

        _collector_instance = None
        return result

    except Exception as e:
        logger.error(f"OHLC 수집 중지 실패: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="ohlc.collect_for_tickers")
def collect_ohlc_for_tickers_task(tickers: List[str], duration_seconds: int = 60) -> dict:
    """
    지정된 종목들에 대해 OHLC 수집 (단발성)

    Args:
        tickers: 수집할 종목 리스트
        duration_seconds: 수집 시간 (초)

    Returns:
        수집 결과 dict
    """
    try:
        from src.kiwoom.ohlc_collector import collect_ohlc_for_tickers

        logger.info(f"OHLC 단발성 수집 - 종목: {len(tickers)}개, 시간: {duration_seconds}초")

        ohlc_data = asyncio.run(collect_ohlc_for_tickers(tickers, duration_seconds))

        result = {
            "status": "completed",
            "tickers": list(ohlc_data.keys()),
            "count": len(ohlc_data),
        }

        # 결과 요약
        for ticker, bar in ohlc_data.items():
            result[f"{ticker}_ohlc"] = {
                "open": bar.open_price,
                "high": bar.high_price,
                "low": bar.low_price,
                "close": bar.close_price,
                "volume": bar.volume,
                "trades": bar.trade_count,
            }

        return result

    except Exception as e:
        logger.error(f"OHLC 단발성 수집 실패: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="ohlc.save_snapshot")
def save_ohlc_snapshot() -> dict:
    """
    현재 OHLC 바 스냅샷을 데이터베이스에 저장

    Returns:
        저장 결과 dict
    """
    global _collector_instance

    if not _collector_instance or not _collector_instance.is_running():
        return {"status": "not_running"}

    try:
        # 비동기 저장
        saved_count = asyncio.run(_collector_instance._save_to_database())

        return {
            "status": "saved",
            "tickers": list(_collector_instance.get_all_ohlc().keys()),
            "count": saved_count,
        }

    except Exception as e:
        logger.error(f"OHLC 스냅샷 저장 실패: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="ohlc.get_status")
def get_ohlc_status() -> dict:
    """
    OHLC 수집기 상태 조회

    Returns:
        상태 dict
    """
    global _collector_instance

    if not _collector_instance:
        return {
            "status": "not_initialized",
            "running": False,
            "connected": False,
        }

    ohlc_bars = _collector_instance.get_all_ohlc()

    return {
        "status": "running" if _collector_instance.is_running() else "stopped",
        "running": _collector_instance.is_running(),
        "connected": _collector_instance.is_connected(),
        "subscribed_tickers": _collector_instance.get_subscribed_tickers(),
        "collecting_tickers": list(ohlc_bars.keys()),
        "count": len(ohlc_bars),
        "last_update": max(
            (bar.last_update.isoformat() for bar in ohlc_bars.values()),
            default=None
        ),
    }


# ==================== 내부 헬퍼 함수 ====================

async def _run_collection(tickers: List[str], duration_seconds: int) -> dict:
    """수집 실행 (비동기)"""
    global _collector_instance

    try:
        # 수집기 생성
        from src.kiwoom.base import KiwoomConfig
        config = KiwoomConfig.from_env()

        from src.kiwoom.ohlc_collector import OHLCCollectorConfig
        collector_config = OHLCCollectorConfig(
            tickers=tickers[:100],  # 최대 100개 종목 제한
            save_interval=60,  # 1분마다 저장
        )

        _collector_instance = OHLCCollector(config, collector_config)

        # 수집 시작
        if not await _collector_instance.start():
            return {"status": "error", "message": "Failed to start collector"}

        # 지정된 시간 동안 수집
        start_time = datetime.now(timezone.utc)
        collected_bars = {}

        while _collector_instance.is_running():
            await asyncio.sleep(10)

            # 최대 시간 확인
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= duration_seconds:
                logger.info(f"최대 수집 시간 ({duration_seconds}초) 도달")
                break

        # 최종 결과 수집
        collected_bars = _collector_instance.get_all_ohlc()

        return {
            "status": "completed",
            "tickers": list(collected_bars.keys()),
            "count": len(collected_bars),
            "duration_seconds": int(elapsed),
        }

    except Exception as e:
        logger.error(f"수집 실행 중 오류: {e}")
        return {"status": "error", "message": str(e)}


async def _stop_collection() -> None:
    """수집 중지 (비동기)"""
    global _collector_instance

    if _collector_instance:
        await _collector_instance.stop()


def _get_active_tickers_from_db(limit: int = 100) -> List[str]:
    """
    데이터베이스에서 활성 종목 조회

    Args:
        limit: 최대 종목 수

    Returns:
        종목 코드 리스트
    """
    try:
        with get_db_session_sync() as db:
            # KOSPI 상위 종목 조회 (시가총액 기준)
            query = (
                select(Stock.ticker)
                .where(Stock.market == "KOSPI")
                .where(Stock.is_admin == False)
                .order_by(Stock.market_cap.desc())
                .limit(limit)
            )

            result = db.execute(query)
            tickers = [row[0] for row in result]

            logger.info(f"DB에서 {len(tickers)}개 종목 조회 완료")
            return tickers

    except Exception as e:
        logger.error(f"DB 종목 조회 실패: {e}")
        return []


# ==================== 장 시작/종료 태스크 ====================

@shared_task(name="ohlc.market_open")
def start_market_collection() -> dict:
    """
    장 시작 시 OHLC 수집 시작 (오전 9시 예정)

    Returns:
        실행 결과 dict
    """
    logger.info("장 시작 OHLC 수집 태스크 실행")

    # KOSPI 상위 50종목 수집
    tickers = _get_active_tickers_from_db(limit=50)

    if not tickers:
        return {"status": "error", "message": "No tickers found"}

    # 6시간 수집 (장 시간)
    return start_ohlc_collection(tickers, duration_seconds=6 * 60 * 60)


@shared_task(name="ohlc.market_close")
def end_market_collection() -> dict:
    """
    장 종료 시 OHLC 수집 종료 (오후 3:30 예정)

    Returns:
        실행 결과 dict
    """
    logger.info("장 종료 OHLC 수집 중지 태스크 실행")
    return stop_ohlc_collection()
