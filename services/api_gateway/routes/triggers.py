"""
Trigger Routes
VCP/Signal 스캔 트리거 API
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.repositories.stock_repository import StockRepository
from services.api_gateway.service_registry import ServiceRegistry
from services.api_gateway.schemas import (
    VCPScanResponse,
    SignalGenerationResponse,
    ScanStatusResponse,
    StockSyncResponse,
    VCPSignalItem,
)

import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kr/scan", tags=["triggers"])


def _get_grade_from_score(total_score: float) -> str:
    """점수에 따른 등급 반환"""
    if total_score >= 80:
        return "S"
    elif total_score >= 65:
        return "A"
    elif total_score >= 50:
        return "B"
    return "C"

# 스캔 상태 관리 (메모리 상태 - 프로덕션에서는 Redis 사용 권장)
_scan_state = {
    "vcp_scan_status": "idle",
    "signal_generation_status": "idle",
    "last_vcp_scan": None,
    "last_signal_generation": None,
    "current_operation": None,
    "progress_percentage": 0.0,
}


class VCPScanOptions(BaseModel):
    """VCP 스캔 옵션 모델"""
    market: Optional[str] = None  # KOSPI, KOSDAQ, ALL
    min_score: Optional[float] = None  # 최소 점수
    min_grade: Optional[str] = None  # 최소 등급 (S, A, B, C)
    sync_stocks: Optional[bool] = False  # 스캔 전 종목 동기화 여부


async def run_stock_sync(markets: List[str] = None) -> dict:
    """
    종목 목록 동기화 (Kiwoom REST API에서 전체 종목 가져오기)

    Args:
        markets: 동기화할 시장 리스트 (KOSPI, KOSDAQ, KONEX)

    Returns:
        동기화 결과
    """
    if markets is None:
        markets = ["KOSPI", "KOSDAQ"]

    try:
        # Kiwoom API 설정
        from src.kiwoom.rest_api import KiwoomRestAPI
        from src.kiwoom.base import KiwoomConfig
        import os

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
            from src.database.session import SessionLocal
            from src.repositories.stock_repository import StockRepository

            # 조회할 시장 매핑
            market_map = {
                "KOSPI": "KOSPI",
                "KOSDAQ": "KOSDAQ",
                "KONEX": "KONEX",
            }

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
                                )
                                count += 1
                            except Exception as e:
                                logger.error(f"❌ 종목 저장 실패 {stock_data['ticker']}: {e}")

                        results["synced"] += count

                        if market == "KOSPI":
                            results["kospi_count"] = count
                        elif market == "KOSDAQ":
                            results["kosdaq_count"] = count
                        elif market == "KONEX":
                            results["konex_count"] = count

                        logger.info(f"✅ {market} 종목 {count}개 동기화 완료")

                except Exception as e:
                    logger.error(f"❌ {market} 종목 동기화 실패: {e}")

            return results

        finally:
            await api.disconnect()

    except Exception as e:
        logger.error(f"Stock sync error: {e}")
        raise


class SignalGenerationOptions(BaseModel):
    """시그널 생성 옵션 모델"""
    tickers: Optional[List[str]] = None  # 특정 종목만 생성


def get_scan_state() -> dict:
    """스캔 상태 조회"""
    return _scan_state.copy()


def update_scan_state(**kwargs):
    """스캔 상태 업데이트"""
    _scan_state.update(kwargs)


async def run_vcp_scan(options: VCPScanOptions) -> dict:
    """
    VCP 스캔 비동기 실행

    Args:
        options: 스캔 옵션

    Returns:
        스캔 결과
    """
    started_at = datetime.utcnow().isoformat()

    try:
        update_scan_state(
            vcp_scan_status="running",
            current_operation="VCP 패턴 스캔 중...",
            progress_percentage=0.0,
        )

        registry = ServiceRegistry()
        vcp_service = registry.get_service("vcp-scanner")

        if not vcp_service:
            raise httpx.HTTPError("VCP Scanner service not available")

        vcp_url = vcp_service["url"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            # VCP 스캔 요청 (JSON body)
            scan_request = {
                "market": options.market or "ALL",
                "top_n": 100,  # 상위 100개 스캔
            }

            update_scan_state(progress_percentage=50.0)

            response = await client.post(
                f"{vcp_url}/scan",
                json=scan_request,
            )
            response.raise_for_status()
            result = response.json()

        update_scan_state(
            vcp_scan_status="completed",
            current_operation=None,
            progress_percentage=100.0,
            last_vcp_scan=datetime.utcnow().isoformat(),
        )

        # 결과 파싱 - VCP Scanner 응답 형식에 맞춤 변환
        results = result.get("results", [])
        saved = result.get("saved", False)

        # VCPSignalItem 형식으로 변환
        signal_items = []
        for r in results:
            analysis_date = r.get("analysis_date", "")
            item = VCPSignalItem(
                ticker=r.get("ticker"),
                name=r.get("name"),
                market="KOSPI",  # 기본값
                signal_type="VCP",
                score=r.get("total_score", 0),
                grade=_get_grade_from_score(r.get("total_score", 0)),
                signal_date=analysis_date,
                entry_price=r.get("current_price"),
                target_price=None,
                current_price=r.get("current_price"),
                contraction_ratio=r.get("vcp_score", 0) / 100 if r.get("vcp_score") else None,
                foreign_5d=r.get("foreign_net_5d", 0) or 0,
                inst_5d=r.get("inst_net_5d", 0) or 0,
                created_at=datetime.utcnow().isoformat(),
            )
            # Pydantic 모델을 dict로 변환
            signal_items.append(item.model_dump())

        return VCPScanResponse(
            status="completed",
            scanned_count=len(results),
            found_signals=len(signal_items),
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
            signals=signal_items,
        )

    except Exception as e:
        logger.error(f"VCP scan error: {e}")
        update_scan_state(
            vcp_scan_status="error",
            current_operation=None,
        )
        raise


async def run_signal_generation(options: SignalGenerationOptions) -> dict:
    """
    시그널 생성 비동기 실행

    Args:
        options: 생성 옵션

    Returns:
        생성 결과
    """
    try:
        update_scan_state(
            signal_generation_status="running",
            current_operation="종가베팅 V2 시그널 생성 중...",
            progress_percentage=0.0,
        )

        registry = ServiceRegistry()
        signal_service = registry.get_service("signal_engine")

        if not signal_service:
            raise httpx.HTTPError("Signal Engine service not available")

        signal_url = signal_service["url"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 시그널 생성 요청
            request_data = {}
            if options.tickers:
                request_data["tickers"] = options.tickers

            update_scan_state(progress_percentage=50.0)

            response = await client.post(
                f"{signal_url}/generate",
                json=request_data if request_data else None,
            )
            response.raise_for_status()
            result = response.json()

        update_scan_state(
            signal_generation_status="completed",
            current_operation=None,
            progress_percentage=100.0,
            last_signal_generation=datetime.utcnow().isoformat(),
        )

        return result

    except Exception as e:
        logger.error(f"Signal generation error: {e}")
        update_scan_state(
            signal_generation_status="error",
            current_operation=None,
        )
        raise


@router.post(
    "/vcp",
    response_model=VCPScanResponse,
    summary="VCP 스캔 트리거",
    description="VCP (Volatility Contraction Pattern) 스캔을 실행합니다. 전체 또는 특정 시장의 종목을 스캔하여 VCP 패턴을 탐지합니다.",
    responses={
        200: {"description": "스캔 완료"},
        409: {"description": "이미 진행 중인 스캔이 있음"},
    },
)
async def trigger_vcp_scan(
    background_tasks: BackgroundTasks,
    market: Optional[str] = Query(None, description="시장 (KOSPI/KOSDAQ/ALL)"),
    min_score: Optional[float] = Query(None, description="최소 점수"),
    min_grade: Optional[str] = Query(None, description="최소 등급"),
    sync_stocks: bool = Query(False, description="스캔 전 종목 동기화 여부"),
    session: Session = Depends(get_db_session),
) -> VCPScanResponse:
    """
    VCP 스캔 트리거

    Args:
        background_tasks: 백그라운드 작업
        market: 시장 필터
        min_score: 최소 점수 필터
        min_grade: 최소 등급 필터
        sync_stocks: 스캔 전 종목 동기화 여부
        session: DB 세션

    Returns:
        VCP 스캔 응답
    """
    if _scan_state["vcp_scan_status"] == "running":
        raise HTTPException(status_code=409, detail="VCP scan already in progress")

    # 종목 동기화 (요청 시)
    if sync_stocks:
        update_scan_state(
            current_operation="종목 목록 동기화 중...",
            progress_percentage=0.0,
        )
        try:
            sync_result = await run_stock_sync(["KOSPI", "KOSDAQ"])
            logger.info(f"종목 동기화 완료: {sync_result['synced']}개")
        except Exception as e:
            logger.error(f"종목 동기화 실패: {e}")
            # 동기화 실패해도 스캔은 계속 진행

    options = VCPScanOptions(
        market=market,
        min_score=min_score,
        min_grade=min_grade,
        sync_stocks=sync_stocks,
    )

    started_at = datetime.utcnow().isoformat()

    # 동기 실행
    try:
        # run_vcp_scan()이 이미 VCPScanResponse 모델을 반환
        return await run_vcp_scan(options)

    except httpx.HTTPError as e:
        # VCP Scanner 서비스 unavailable 시 대응
        return VCPScanResponse(
            status="error",
            scanned_count=0,
            found_signals=0,
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
            error_message=f"VCP Scanner service unavailable: {str(e)}",
        )


@router.post(
    "/signals",
    response_model=SignalGenerationResponse,
    summary="종가베팅 V2 시그널 생성 트리거",
    description="종가베팅 V2 시그널 생성을 실행합니다. 12점 스코어링 시스템로 종목을 평가하고 시그널을 생성합니다.",
    responses={
        200: {"description": "생성 완료"},
        409: {"description": "이미 진행 중인 생성이 있음"},
    },
)
async def trigger_signal_generation(
    background_tasks: BackgroundTasks,
    tickers: Optional[List[str]] = Query(None, description="특정 종목만 생성"),
    session: Session = Depends(get_db_session),
) -> SignalGenerationResponse:
    """
    종가베팅 V2 시그널 생성 트리거

    Args:
        background_tasks: 백그라운드 작업
        tickers: 특정 종목 리스트
        session: DB 세션

    Returns:
        시그널 생성 응답
    """
    if _scan_state["signal_generation_status"] == "running":
        raise HTTPException(status_code=409, detail="Signal generation already in progress")

    options = SignalGenerationOptions(tickers=tickers)

    started_at = datetime.utcnow().isoformat()

    # 동기 실행 (테스트용)
    try:
        result = await run_signal_generation(options)

        return SignalGenerationResponse(
            status="completed",
            generated_count=result.get("generated_count", 0),
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
        )

    except httpx.HTTPError as e:
        # Signal Engine 서비스 unavailable 시 대응
        return SignalGenerationResponse(
            status="error",
            generated_count=0,
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
            error_message=f"Signal Engine service unavailable: {str(e)}",
        )


@router.get(
    "/status",
    response_model=ScanStatusResponse,
    summary="스캔 상태 조회",
    description="현재 진행 중인 VCP 스캔 및 시그널 생성의 상태를 조회합니다.",
)
def get_scan_status() -> ScanStatusResponse:
    """
    스캔 상태 조회

    Returns:
        스캔 상태 응답
    """
    state = get_scan_state()

    return ScanStatusResponse(
        vcp_scan_status=state.get("vcp_scan_status", "idle"),
        signal_generation_status=state.get("signal_generation_status", "idle"),
        last_vcp_scan=state.get("last_vcp_scan"),
        last_signal_generation=state.get("last_signal_generation"),
        current_operation=state.get("current_operation"),
        progress_percentage=state.get("progress_percentage"),
    )


@router.post(
    "/sync-stocks",
    response_model=StockSyncResponse,
    summary="종목 목록 동기화",
    description="KRX에서 KOSPI/KOSDAQ 전체 종목 목록을 동기화합니다.",
)
async def sync_stocks(
    background_tasks: BackgroundTasks,
    markets: Optional[List[str]] = Query(
        default=["KOSPI", "KOSDAQ"],
        description="동기화할 시장 (KOSPI, KOSDAQ, KONEX)"
    ),
) -> StockSyncResponse:
    """
    종목 목록 동기화

    Args:
        background_tasks: 백그라운드 작업
        markets: 동기화할 시장 리스트

    Returns:
        종목 동기화 응답
    """
    started_at = datetime.utcnow().isoformat()

    try:
        # 동기 실행 (Celery 태스크로 변경 가능)
        result = await run_stock_sync(markets)

        return StockSyncResponse(
            status="completed",
            synced=result.get("synced", 0),
            kospi_count=result.get("kospi_count", 0),
            kosdaq_count=result.get("kosdaq_count", 0),
            konex_count=result.get("konex_count", 0),
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Stock sync failed: {e}")
        return StockSyncResponse(
            status="error",
            synced=0,
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
            error_message=str(e),
        )


@router.post("/multiple")
async def trigger_multiple_scans(
    background_tasks: BackgroundTasks,
    scan_types: List[str] = Query(..., description="실행할 스캔 타입 (vcp, signals)"),
):
    """
    다중 스캔 트리거

    Args:
        background_tasks: 백그라운드 작업
        scan_types: 실행할 스캔 타입 리스트

    Returns:
        다중 스캔 결과
    """
    results = {}

    for scan_type in scan_types:
        if scan_type == "vcp":
            try:
                vcp_result = await trigger_vcp_scan(background_tasks)
                results["vcp"] = vcp_result.dict()
            except Exception as e:
                results["vcp"] = {"status": "error", "error": str(e)}
        elif scan_type == "signals":
            try:
                signal_result = await trigger_signal_generation(background_tasks)
                results["signals"] = signal_result.dict()
            except Exception as e:
                results["signals"] = {"status": "error", "error": str(e)}

    return results
