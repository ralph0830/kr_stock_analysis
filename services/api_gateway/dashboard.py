"""
모니터링 대시보드 API
시스템 상태, 메트릭, 연결 정보 제공
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from src.utils.metrics import metrics_registry
from src.websocket.server import connection_manager
from src.websocket.price_provider import get_realtime_service
from services.api_gateway.service_registry import get_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ============================================================================
# Response Models
# ============================================================================


class SystemStatus(BaseModel):
    """시스템 상태 모델"""
    status: str  # healthy, degraded, unhealthy
    uptime_seconds: float
    timestamp: str
    services: Dict[str, str]


class MetricData(BaseModel):
    """메트릭 데이터 모델"""
    name: str
    type: str
    value: Any
    help: str


class ConnectionInfo(BaseModel):
    """연결 정보 모델"""
    active_connections: int
    subscriptions: Dict[str, int]
    broadcaster_running: bool


class SignalSummary(BaseModel):
    """시그널 요약 모델"""
    total_signals: int
    active_signals: int
    latest_signals: List[Dict]


# ============================================================================
# Overview Endpoints
# ============================================================================


@router.get("/overview", response_model=SystemStatus)
async def get_system_overview():
    """
    시스템 상태 개요

    Returns:
        SystemStatus: 전체 시스템 상태
    """
    # 서비스 레지스트리 상태 확인
    registry = get_registry()
    services = registry.list_services()

    # 서비스 상태 매핑
    service_status = {}
    for service in services:
        service_status[service["name"]] = "registered"

    # 실시간 서비스 상태
    realtime_service = get_realtime_service()
    if realtime_service:
        service_status["realtime_broadcaster"] = (
            "running" if realtime_service.is_running() else "stopped"
        )

    # 전체 상태 계산
    running_count = sum(
        1 for status in service_status.values()
        if status in ["running", "registered"]
    )
    total_count = len(service_status)

    if running_count == total_count:
        overall_status = "healthy"
    elif running_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return SystemStatus(
        status=overall_status,
        uptime_seconds=_get_uptime(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=service_status,
    )


@router.get("/metrics")
async def get_metrics_data(
    metric_type: Optional[str] = None,
    limit: int = 10,
):
    """
    메트릭 데이터 조회

    Args:
        metric_type: 필터링할 메트릭 타입 (counter, gauge, histogram)
        limit: 반환할 메트릭 수

    Returns:
        메트릭 데이터 리스트
    """
    all_metrics = metrics_registry.get_all_metrics()

    # 타입 필터링
    if metric_type:
        all_metrics = {
            name: data
            for name, data in all_metrics.items()
            if data.get("type") == metric_type
        }

    # 제한
    metrics_list = []
    for name, data in list(all_metrics.items())[:limit]:
        metrics_list.append({
            "name": name,
            "type": data.get("type"),
            "value": data.get("value"),
            "help": data.get("help"),
        })

    return {
        "metrics": metrics_list,
        "total": len(all_metrics),
        "filtered": len(metrics_list),
    }


@router.get("/connections", response_model=ConnectionInfo)
async def get_connection_info():
    """
    실시간 연결 상태

    Returns:
        ConnectionInfo: 연결 정보
    """
    # 활성 연결 수
    active_connections = len(connection_manager.active_connections)

    # 구독 정보
    subscriptions: Dict[str, int] = {}
    for topic, subscribers in connection_manager.subscriptions.items():
        subscriptions[topic] = len(subscribers)

    # 브로드캐스터 상태
    realtime_service = get_realtime_service()
    broadcaster_running = (
        realtime_service.is_running()
        if realtime_service
        else False
    )

    return ConnectionInfo(
        active_connections=active_connections,
        subscriptions=subscriptions,
        broadcaster_running=broadcaster_running,
    )


@router.get("/signals")
async def get_signal_summary(
    limit: int = 10,
    status: Optional[str] = None,
):
    """
    최신 시그널 요약

    Args:
        limit: 반환할 시그널 수
        status: 필터링할 상태 (active, closed, all)

    Returns:
        SignalSummary: 시그널 요약
    """
    registry = get_registry()

    # Signal Engine 서비스 조회
    signal_engine = registry.get_service("signal-engine")
    if not signal_engine:
        # 서비스 없으면 Mock 데이터 반환
        return _get_mock_signal_summary(limit)

    # Signal Engine으로 프록시
    import httpx

    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status

            response = await client.get(
                f"{signal_engine['url']}/signals",
                params=params,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "total_signals": data.get("total", 0),
                "active_signals": data.get("active", 0),
                "latest_signals": data.get("signals", []),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Signal Engine error: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Signal Engine error: {e.response.text}",
            )
        except httpx.RequestError as e:
            logger.error(f"Signal Engine unavailable: {e}")
            # Fallback to mock data
            return _get_mock_signal_summary(limit)


@router.get("/health")
async def dashboard_health():
    """
    대시보드 헬스 체크

    Returns:
        헬스 상태
    """
    checks = {
        "metrics": metrics_registry is not None,
        "websocket": connection_manager is not None,
        "service_registry": get_registry() is not None,
    }

    all_healthy = all(checks.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Utility Functions
# ============================================================================


def _get_uptime() -> float:
    """
    시스템 가동 시간 계산

    Returns:
        가동 시간 (초)
    """
    # TODO: 실제 애플리케이션 시작 시간 추적 필요
    # 현재는 임시로 0 반환
    return 0.0


def _get_mock_signal_summary(limit: int) -> Dict:
    """
    Mock 시그널 요약 생성

    Args:
        limit: 반환할 시그널 수

    Returns:
        Mock 시그널 요약
    """
    mock_signals = []
    for i in range(min(limit, 5)):
        mock_signals.append({
            "id": f"mock_signal_{i}",
            "ticker": "005930" if i % 2 == 0 else "000660",
            "status": "active",
            "score": 10 - i,
            "entry_date": datetime.now(timezone.utc).isoformat(),
        })

    return {
        "total_signals": 5,
        "active_signals": 3,
        "latest_signals": mock_signals,
    }
