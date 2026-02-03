"""
Celery Tasks - Stock Sync
종목 동기화 비동기 작업 (Kiwoom REST API)
"""

import logging
import os
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.sync_tasks.sync_stock_list", bind=True)
def sync_stock_list(self, markets: list = None):
    """
    종목 마스터 동기화 태스크 (Kiwoom REST API 사용)

    Args:
        markets: 동기화할 시장 리스트 (KOSPI, KOSDAQ, KONEX)

    Returns:
        동기화 결과
    """
    if markets is None:
        markets = ["KOSPI", "KOSDAQ"]

    try:
        logger.info(f"종목 동기화 시작: {markets}")

        # 비동기 함수를 동기 태스크에서 실행
        import asyncio

        results = asyncio.run(_sync_stock_list_async(markets))

        logger.info(f"종목 동기화 완료: {results}")
        return results

    except Exception as e:
        logger.error(f"종목 동기화 실패: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "error", "message": str(e)}


async def _sync_stock_list_async(markets: list) -> dict:
    """
    종목 목록 동기화 비동기 함수

    Args:
        markets: 시장 리스트

    Returns:
        동기화 결과
    """
    from src.kiwoom.rest_api import KiwoomRestAPI
    from src.kiwoom.base import KiwoomConfig
    from src.database.session import SessionLocal
    from src.repositories.stock_repository import StockRepository
    import os

    # Kiwoom API 설정
    app_key = os.getenv("KIWOOM_APP_KEY")
    secret_key = os.getenv("KIWOOM_SECRET_KEY")
    base_url = os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com")
    ws_url = os.getenv("KIWOOM_WS_URL", "wss://api.kiwoom.com:10000/api/dostk/websocket")

    if not app_key or not secret_key:
        raise Exception("Kiwoom API keys not configured")

    config = KiwoomConfig(
        app_key=app_key,
        secret_key=secret_key,
        base_url=base_url,
        ws_url=ws_url,
        use_mock=False,
    )

    api = KiwoomRestAPI(config)

    results = {
        "synced": 0,
        "kospi_count": 0,
        "kosdaq_count": 0,
        "konex_count": 0,
    }

    try:
        # 토큰 발급
        await api.connect()

        # 종목 목록 조회 및 저장
        for market in markets:
            try:
                # 종목 목록 조회
                stocks = await api.get_stock_list(market)

                # DB 저장
                with SessionLocal() as session:
                    repo = StockRepository(session)
                    count = 0

                    for stock_data in stocks:
                        try:
                            repo.create_if_not_exists(
                                ticker=stock_data["ticker"],
                                name=stock_data["name"],
                                market=stock_data["market"],
                                sector="",
                                market_cap=0,
                                is_spac=stock_data.get("is_spac", False),  # 스팩 종목 여부
                                is_bond=stock_data.get("is_bond", False),  # 회사채/채권 종목 여부
                                is_excluded_etf=stock_data.get("is_excluded_etf", False),  # 제외할 ETF/ETN 여부
                            )
                            count += 1
                        except Exception as e:
                            logger.error(f"종목 저장 실패 {stock_data['ticker']}: {e}")

                    results["synced"] += count

                    if market == "KOSPI":
                        results["kospi_count"] = count
                    elif market == "KOSDAQ":
                        results["kosdaq_count"] = count
                    elif market == "KONEX":
                        results["konex_count"] = count

                    logger.info(f"{market} 종목 {count}개 동기화 완료")

            except Exception as e:
                logger.error(f"{market} 종목 동기화 실패: {e}")

        return results

    finally:
        await api.disconnect()


@celery_app.task(name="tasks.sync_tasks.trigger_vcp_scan_via_api")
def trigger_vcp_scan_via_api():
    """
    VCP 스캔 트리거 태스크 (API Gateway 호출)

    Returns:
        스캔 결과
    """
    import httpx

    try:
        logger.info("VCP 스캔 트리거 시작 (API Gateway)")

        # API Gateway의 VCP 스캔 엔드포인트 호출
        api_url = os.getenv("API_GATEWAY_URL", "http://localhost:5111")

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{api_url}/api/kr/scan/vcp",
                params={
                    "market": "ALL",
                    "sync_stocks": False,  # 별도로 종목 동기화 실행
                },
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"VCP 스캔 완료: {result.get('scanned_count')}개 스캔, {result.get('found_signals')}개 시그널")
        return result

    except Exception as e:
        logger.error(f"VCP 스캔 실패: {e}")
        return {"status": "error", "message": str(e)}
