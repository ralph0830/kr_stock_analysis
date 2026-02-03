"""
Celery Tasks - VCP Scanner
VCP 패턴 스캔 비동기 작업
"""

import logging
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.scan_tasks.scan_vcp_patterns", bind=True)
def scan_vcp_patterns(self, market: str = "KOSPI", top_n: int = 30, save_db: bool = True):
    """
    VCP 패턴 스캔 태스크

    Args:
        market: KOSPI 또는 KOSDAQ
        top_n: 상위 N개 종목
        save_db: DB 저장 여부

    Returns:
        스캔 결과
    """
    try:
        logger.info(f"VCP 스캔 시작: {market}, 상위 {top_n}개")

        # VCP Analyzer 직접 호출
        from services.vcp_scanner.vcp_analyzer import VCPAnalyzer

        analyzer = VCPAnalyzer()
        # 동기 태스크에서 비동기 함수 실행
        import asyncio
        results = asyncio.run(analyzer.scan_market(market, top_n))

        logger.info(f"VCP 스캔 완료: {len(results)}개 시그널 발견")

        # DB 저장
        saved_count = 0
        if save_db and results:
            try:
                from services.vcp_scanner.main import save_vcp_signals_to_db
                saved_count = save_vcp_signals_to_db(results)
                logger.info(f"VCP 시그널 {saved_count}개 DB 저장 완료")
            except Exception as db_error:
                logger.error(f"DB 저장 실패: {db_error}")

        return {
            "status": "success",
            "count": len(results),
            "saved": saved_count,
            "results": [r.to_dict() for r in results],
        }

    except Exception as e:
        logger.error(f"VCP 스캔 실패: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.scan_tasks.scan_all_markets")
def scan_all_markets():
    """전체 시장 VCP 스캔"""
    markets = ["KOSPI", "KOSDAQ"]
    results = {}

    for market in markets:
        task = scan_vcp_patterns.delay(market, 30)
        results[market] = task.id

    return {"status": "started", "tasks": results}
