"""
Celery Tasks - Market Data
시장 데이터 수집 및 업데이트 비동기 작업
"""

import asyncio
import logging
import os
from datetime import date, datetime
from typing import Optional

from tasks.celery_app import celery_app
from src.database.session import get_db_session
from src.repositories.market_repository import MarketRepository

logger = logging.getLogger(__name__)

# Kiwoom 지수 종목코드 (주식기본정보 API 사용)
KOSPI_CODE = "KS11"    # KOSPI 지수 코드
KOSDAQ_CODE = "KQ11"   # KOSDAQ 지수 코드

# 섹터 ETF ticker (KODEX)
# 참고: https://www.krx.co.kr/main/main.jsp
SECTOR_ETFS = {
    "반도체": "069500",    # KODEX 반도체
    "2차전지": "305720",   # KODEX 2차전지
    "자동차": "116380",    # KODEX 자동차
    "바이오": "327610",    # KODEX 바이오
    "금융": "091160",      # KODEX 은행
    "통신": "327580",      # KODEX 통신
}


def run_async(coro):
    """동기 함수에서 async 함수 실행을 위한 헬퍼"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def fetch_index_prices():
    """
    지수 데이터 수집 (Naver Finance > Kiwoom REST API)

    1. Naver Finance 실시간 지수 API (우선)
    2. Kiwoom REST API (대안)

    Returns:
        지수 데이터 딕셔너리
    """
    import requests

    # 1. Naver Finance 실시간 지수 API (우선)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
        }

        # KOSPI 지수 조회
        kospi_url = "https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI"
        response = requests.get(kospi_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("datas") and len(data["datas"]) > 0:
                item = data["datas"][0]
                kospi_data = {
                    "code": "KS11",
                    "name": "KOSPI",
                    "price": float(item.get("closePriceRaw", 0)),
                    "change": float(item.get("compareToPreviousClosePriceRaw", 0)),
                    "change_pct": float(item.get("fluctuationsRatioRaw", 0)),
                }
                logger.info(f"Naver KOSPI: {kospi_data['price']} ({kospi_data['change_pct']:.2f}%)")
            else:
                kospi_data = None
        else:
            kospi_data = None

        # KOSDAQ 지수 조회
        kosdaq_url = "https://polling.finance.naver.com/api/realtime/domestic/index/KOSDAQ"
        response = requests.get(kosdaq_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("datas") and len(data["datas"]) > 0:
                item = data["datas"][0]
                kosdaq_data = {
                    "code": "KQ11",
                    "name": "KOSDAQ",
                    "price": float(item.get("closePriceRaw", 0)),
                    "change": float(item.get("compareToPreviousClosePriceRaw", 0)),
                    "change_pct": float(item.get("fluctuationsRatioRaw", 0)),
                }
                logger.info(f"Naver KOSDAQ: {kosdaq_data['price']} ({kosdaq_data['change_pct']:.2f}%)")
            else:
                kosdaq_data = None
        else:
            kosdaq_data = None

        # Naver API에서 데이터를 가져왔으면 섹터 ETF도 조회
        if kospi_data and kosdaq_data and kospi_data.get("price", 0) > 0:
            sector_scores = []

            # 섹터 ETF도 Naver Finance에서 조회
            for sector_name, ticker in SECTOR_ETFS.items():
                try:
                    # Naver Finance 종목 실시간 시세
                    item_url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{ticker}"
                    response = requests.get(item_url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("datas") and len(data["datas"]) > 0:
                            item = data["datas"][0]
                            change_pct = float(item.get("fluctuationsRatioRaw", 0))
                            sector_scores.append({
                                "name": sector_name,
                                "ticker": ticker,
                                "change_pct": change_pct,
                            })
                            logger.info(f"Naver {sector_name} ({ticker}): {change_pct:.2f}%")
                except Exception as e:
                    logger.warning(f"섹터 ETF {sector_name} 조회 실패: {e}")

            return {
                "kospi": kospi_data,
                "kosdaq": kosdaq_data,
                "sectors": sector_scores,
            }

    except Exception as e:
        logger.error(f"Naver Finance 지수 데이터 수집 실패: {e}")

    # 2. Kiwoom REST API (대안)
    try:
        from src.kiwoom.rest_api import KiwoomRestAPI

        api = KiwoomRestAPI.from_env()

        # 토큰 발급
        if not api.is_token_valid():
            await api.issue_token()

        # KOSPI/KOSDAQ 지수 조회
        kospi_data = await api.get_index_price(KOSPI_CODE)
        kosdaq_data = await api.get_index_price(KOSDAQ_CODE)

        await api.close()

        # Kiwoom에서 데이터를 가져왔으면 섹터 ETF도 Kiwoom로 조회
        if kospi_data and kosdaq_data and kospi_data.get("price"):
            sector_scores = []
            for sector_name, ticker in SECTOR_ETFS.items():
                etf_data = await api.get_current_price(ticker)
                if etf_data:
                    sector_scores.append({
                        "name": sector_name,
                        "ticker": ticker,
                        "change_pct": etf_data.change_rate,
                    })

            await api.close()

            return {
                "kospi": kospi_data,
                "kosdaq": kosdaq_data,
                "sectors": sector_scores,
            }
    except Exception as e:
        logger.error(f"Kiwoom API 지수 데이터 수집 실패: {e}")

    # 모든 API 실패 시 None 반환
    logger.warning("모든 지수 데이터 수집 실패")
    return None


@celery_app.task(name="tasks.market_tasks.update_market_gate", bind=True)
def update_market_gate(self):
    """
    Market Gate 업데이트 태스크

    Naver Finance 실시간 API를 사용하여 KOSPI/KOSDAQ 지수 데이터를 수집하고
    데이터베이스에 저장합니다.

    Returns:
        Market Gate 상태
    """
    try:
        logger.info("Market Gate 업데이트 시작")

        # Naver Finance API로 지수 데이터 수집
        result = run_async(fetch_index_prices())

        if not result:
            # API 실패 시 mock 데이터 반환
            logger.warning("지수 데이터 수집 실패, 기본값 사용")
            kospi = None
            kospi_change_pct = 0.0
            kosdaq = None
            kosdaq_change_pct = 0.0
            sector_scores = []
        else:
            kospi_data = result.get("kospi")
            kosdaq_data = result.get("kosdaq")
            sector_scores = result.get("sectors", [])

            kospi = kospi_data.get("price") if kospi_data else None
            kospi_change_pct = kospi_data.get("change_pct") if kospi_data else 0.0
            kosdaq = kosdaq_data.get("price") if kosdaq_data else None
            kosdaq_change_pct = kosdaq_data.get("change_pct") if kosdaq_data else 0.0

            logger.info(f"지수 데이터 수집 완료: KOSPI={kospi} ({kospi_change_pct:.2f}%), "
                       f"KOSDAQ={kosdaq} ({kosdaq_change_pct:.2f}%)")

        # DB에 저장
        db = next(get_db_session())
        try:
            repo = MarketRepository(db)

            # Gate 상태 계산
            gate, gate_score = repo.calculate_gate_status(
                kospi_change_pct=kospi_change_pct,
                kosdaq_change_pct=kosdaq_change_pct,
                sector_scores=sector_scores,
            )

            # Market Status 생성/업데이트
            today = date.today()
            market_status = repo.create_or_update(
                date=today,
                kospi=kospi,
                kospi_change_pct=kospi_change_pct,
                kosdaq=kosdaq,
                kosdaq_change_pct=kosdaq_change_pct,
                gate=gate,
                gate_score=gate_score,
                sector_scores=sector_scores,
            )

            logger.info(f"Market Gate 업데이트 완료: {gate} (레벨 {gate_score})")

            result = {
                "status": "success",
                "gate": gate,
                "score": gate_score,
                "kospi": kospi,
                "kosdaq": kosdaq,
                "date": today.isoformat(),
            }
        finally:
            db.close()

        return result

    except Exception as e:
        logger.error(f"Market Gate 업데이트 실패: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.market_tasks.collect_institutional_flow")
def collect_institutional_flow(tickers: list[str] = None):
    """
    기관 매매 수급 데이터 수집

    Args:
        tickers: 종목코드 리스트 (None이면 전체)

    Returns:
        수급 데이터
    """
    try:
        logger.info(f"기관 매매 수급 수집 시작: {len(tickers) if tickers else '전체'}개 종목")

        # TODO: pykrx 또는 FinanceDataReader로 수급 데이터 수집

        # Mock 데이터
        flow_data = {
            "collected_at": None,
            "count": 0,
            "flows": [],
        }

        if tickers:
            for ticker in tickers:
                flow_data["flows"].append({
                    "ticker": ticker,
                    "foreigner": 0,
                    "institution": 0,
                })
            flow_data["count"] = len(tickers)

        logger.info(f"기관 매매 수급 수집 완료: {flow_data['count']}개")

        return {
            "status": "success",
            "data": flow_data,
        }

    except Exception as e:
        logger.error(f"기관 매매 수급 수집 실패: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.market_tasks.update_stock_prices")
def update_stock_prices():
    """전 종목 실시간 가격 업데이트"""
    try:
        logger.info("전 종목 가격 업데이트 시작")

        # TODO: pykrx 또는 yfinance로 가격 데이터 업데이트

        return {
            "status": "success",
            "updated": 0,
        }

    except Exception as e:
        logger.error(f"가격 업데이트 실패: {e}")
        return {"status": "error", "message": str(e)}
