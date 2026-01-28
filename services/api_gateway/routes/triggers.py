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
from services.api_gateway.service_registry import ServiceRegistry
from services.api_gateway.schemas import (
    VCPScanResponse,
    SignalGenerationResponse,
    ScanStatusResponse,
    VCPSignalItem,
)

import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kr/scan", tags=["triggers"])

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
    try:
        update_scan_state(
            vcp_scan_status="running",
            current_operation="VCP 패턴 스캔 중...",
            progress_percentage=0.0,
        )

        registry = ServiceRegistry()
        vcp_service = registry.get_service("vcp_scanner")

        if not vcp_service:
            raise httpx.HTTPError("VCP Scanner service not available")

        vcp_url = vcp_service["url"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            # VCP 스캔 요청
            scan_params = {}
            if options.market:
                scan_params["market"] = options.market
            if options.min_score is not None:
                scan_params["min_score"] = options.min_score

            update_scan_state(progress_percentage=50.0)

            response = await client.post(
                f"{vcp_url}/scan",
                params=scan_params,
            )
            response.raise_for_status()
            result = response.json()

        update_scan_state(
            vcp_scan_status="completed",
            current_operation=None,
            progress_percentage=100.0,
            last_vcp_scan=datetime.utcnow().isoformat(),
        )

        return result

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


@router.post("/vcp", response_model=VCPScanResponse)
async def trigger_vcp_scan(
    background_tasks: BackgroundTasks,
    market: Optional[str] = Query(None, description="시장 (KOSPI/KOSDAQ)"),
    min_score: Optional[float] = Query(None, description="최소 점수"),
    min_grade: Optional[str] = Query(None, description="최소 등급"),
    session: Session = Depends(get_db_session),
) -> VCPScanResponse:
    """
    VCP 스캔 트리거

    Args:
        background_tasks: 백그라운드 작업
        market: 시장 필터
        min_score: 최소 점수 필터
        min_grade: 최소 등급 필터
        session: DB 세션

    Returns:
        VCP 스캔 응답
    """
    if _scan_state["vcp_scan_status"] == "running":
        raise HTTPException(status_code=409, detail="VCP scan already in progress")

    options = VCPScanOptions(
        market=market,
        min_score=min_score,
        min_grade=min_grade,
    )

    started_at = datetime.utcnow().isoformat()

    # 비동기 실행을 위해 백그라운드 태스크에 추가
    # 실제 구현에서는 Celery 태스크 사용 권장

    # 동기 실행 (테스트용)
    try:
        result = await run_vcp_scan(options)

        return VCPScanResponse(
            status="completed",
            scanned_count=result.get("scanned_count", 0),
            found_signals=result.get("found_signals", 0),
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
            signals=[
                VCPSignalItem(**signal) for signal in result.get("signals", [])
            ] if "signals" in result else [],
        )

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


@router.post("/signals", response_model=SignalGenerationResponse)
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


@router.get("/status", response_model=ScanStatusResponse)
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
