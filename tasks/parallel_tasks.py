"""
Celery Parallel Tasks

태스크 병렬 처리를 위한 group/chord 활용 예시
"""
import logging
from typing import List, Dict, Any

from celery import group, chord, signature
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.parallel_tasks.process_single_ticker")
def process_single_ticker(ticker: str) -> Dict[str, Any]:
    """
    단일 종목 처리 태스크

    병렬 처리를 위한 기본 단위 태스크

    Args:
        ticker: 종목 코드

    Returns:
        처리 결과
    """
    try:
        logger.info(f"종목 처리 시작: {ticker}")

        # TODO: 실제 종목 분석 로직
        result = {
            "ticker": ticker,
            "status": "processed",
            "score": 50.0,
        }

        logger.info(f"종목 처리 완료: {ticker}")
        return result

    except Exception as e:
        logger.error(f"종목 처리 실패 {ticker}: {e}")
        return {
            "ticker": ticker,
            "status": "error",
            "error": str(e),
        }


@celery_app.task(name="tasks.parallel_tasks.aggregate_results")
def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    병렬 처리 결과 집계 태스크

    Chord 콜백으로 사용

    Args:
        results: 개별 태스크 결과 리스트

    Returns:
        집계 결과
    """
    try:
        processed_count = sum(1 for r in results if r.get("status") == "processed")
        error_count = sum(1 for r in results if r.get("status") == "error")

        logger.info(f"결과 집계: {processed_count}개 성공, {error_count}개 실패")

        return {
            "total": len(results),
            "processed": processed_count,
            "errors": error_count,
            "results": results,
        }

    except Exception as e:
        logger.error(f"결과 집계 실패: {e}")
        return {
            "total": 0,
            "processed": 0,
            "errors": 0,
            "error": str(e),
        }


@celery_app.task(name="tasks.parallel_tasks.scan_tickers_parallel")
def scan_tickers_parallel(tickers: List[str], batch_size: int = 10) -> Dict[str, Any]:
    """
    여러 종목을 병렬로 스캔

    Group을 사용한 병렬 처리

    Args:
        tickers: 종목 코드 리스트
        batch_size: 한 번에 처리할 종목 수

    Returns:
        스캔 결과
    """
    try:
        logger.info(f"병렬 스캔 시작: {len(tickers)}개 종목")

        # 태스크 그룹 생성
        job = group(
            process_single_ticker.s(ticker)
            for ticker in tickers[:batch_size]
        )

        # 그룹 실행
        result = job.apply_async()

        # 결과 대기
        results = result.get(timeout=300)

        processed_count = sum(1 for r in results if r.get("status") == "processed")

        logger.info(f"병렬 스캔 완료: {processed_count}/{len(results)}개 성공")

        return {
            "status": "success",
            "total": len(results),
            "processed": processed_count,
            "results": results,
        }

    except Exception as e:
        logger.error(f"병렬 스캔 실패: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


@celery_app.task(name="tasks.parallel_tasks.scan_tickers_chord")
def scan_tickers_chord(tickers: List[str]) -> str:
    """
    여러 종목을 병렬로 스캔 후 결과 집계

    Chord를 사용한 병렬 처리 + 집계

    Args:
        tickers: 종목 코드 리스트

    Returns:
        태스크 ID (추적용)
    """
    try:
        logger.info(f"Chord 스캔 시작: {len(tickers)}개 종목")

        # Chord: 병렬 태스크 + 콜백
        job = chord(
            (process_single_ticker.s(ticker) for ticker in tickers),
            aggregate_results.s()
        )

        # 비동기 실행
        result = job.apply_async()

        logger.info(f"Chord 태스크 시작: {result.id}")

        return result.id

    except Exception as e:
        logger.error(f"Chord 스캔 실패: {e}")
        return ""


@celery_app.task(name="tasks.parallel_tasks.update_multiple_markets")
def update_multiple_markets(markets: List[str]) -> Dict[str, Any]:
    """
    여러 시장 데이터를 병렬로 업데이트

    Args:
        markets: 시장 코드 리스트 (예: ["KS11", "KQ11"])

    Returns:
        업데이트 결과
    """
    try:
        logger.info(f"다중 시장 업데이트: {markets}")

        # Market Gate 업데이트 태스크
        from tasks.market_tasks import update_market_gate

        # 병렬 실행
        job = group(
            update_market_gate.s()
            for _ in markets
        )

        result = job.apply_async()
        results = result.get(timeout=600)

        return {
            "status": "success",
            "markets": markets,
            "results": results,
        }

    except Exception as e:
        logger.error(f"다중 시장 업데이트 실패: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


# 태스크 우선순위 설정
# Celery 5.2+에서는 task_routing_key와 priority 옵션 사용


class TaskPriority:
    """태스크 우선순위 상수"""

    HIGH = 9      # 높은 우선순위 (긴급 작업)
    MEDIUM = 5    # 중간 우선순위 (기본 작업)
    LOW = 1       # 낮은 우선순위 (배치 작업)


@celery_app.task(
    name="tasks.parallel_tasks.urgent_signal_scan",
    priority=TaskPriority.HIGH,
)
def urgent_signal_scan(tickers: List[str]) -> Dict[str, Any]:
    """
    긴급 시그널 스캔 태스크

    높은 우선순위로 실행되어 먼저 처리됨

    Args:
        tickers: 스캔할 종목 리스트

    Returns:
        스캔 결과
    """
    try:
        logger.info(f"긴급 시그널 스캔: {len(tickers)}개 종목")

        # TODO: 실제 시그널 스캔 로직

        return {
            "status": "success",
            "tickers": tickers,
            "priority": "high",
        }

    except Exception as e:
        logger.error(f"긴급 시그널 스캔 실패: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


@celery_app.task(
    name="tasks.parallel_tasks.batch_data_update",
    priority=TaskPriority.LOW,
)
def batch_data_update() -> Dict[str, Any]:
    """
    배치 데이터 업데이트 태스크

    낮은 우선순위로 실행되어 다른 작업이 없을 때 처리됨

    Returns:
        업데이트 결과
    """
    try:
        logger.info("배치 데이터 업데이트 시작")

        # TODO: 실제 배치 업데이트 로직

        return {
            "status": "success",
            "priority": "low",
        }

    except Exception as e:
        logger.error(f"배치 데이터 업데이트 실패: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
