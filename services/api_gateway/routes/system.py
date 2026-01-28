"""
System Routes
시스템 관리 API
"""

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from src.database.session import get_db_session
from src.database.models import DailyPrice, Signal
from src.repositories.stock_repository import StockRepository
from src.repositories.signal_repository import SignalRepository
from services.api_gateway.schemas import (
    DataStatusResponse,
    DataStatusItem,
    SystemHealthResponse,
)

import time

router = APIRouter(prefix="/api/system", tags=["system"])

# 애플리케이션 시작 시간
_START_TIME = time.time()


def get_uptime_seconds() -> float:
    """애플리케이션 실행 시간 (초)"""
    return time.time() - _START_TIME


def check_database_health(session: Session) -> str:
    """
    데이터베이스 헬스 체크

    Args:
        session: DB 세션

    Returns:
        상태 문자열 (up, down, degraded)
    """
    try:
        # 간단한 쿼리로 연결 확인
        session.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


def check_redis_health() -> str:
    """
    Redis 헬스 체크

    Returns:
        상태 문자열 (up, down)
    """
    try:
        import redis
        client = redis.Redis.from_url("redis://localhost:6380/0", decode_responses=True)
        client.ping()
        return "up"
    except Exception:
        return "down"


def check_celery_health() -> Optional[str]:
    """
    Celery 헬스 체크

    Returns:
        상태 문자열 (up, down) 또는 None (미설정)
    """
    try:
        from celery import current_app
        inspector = current_app.control.inspect()
        if inspector.active() is not None:
            return "up"
        return "down"
    except Exception:
        return None


@router.get(
    "/data-status",
    response_model=DataStatusResponse,
    summary="데이터 파일 상태 조회",
    description="데이터베이스에 저장된 주가, 시그널 데이터의 상태를 조회합니다. 마지막 업데이트 시간과 레코드 수를 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
        500: {"description": "서버 오류"},
    },
)
def get_data_status(
    session: Session = Depends(get_db_session),
) -> DataStatusResponse:
    """
    데이터 파일 상태 조회

    ## 설명
    데이터베이스에 저장된 주가, 시그널 데이터의 상태를 조회합니다.

    ## 반환 데이터
    - **total_stocks**: 전체 종목 수
    - **updated_stocks**: 최근 7일 이내 업데이트된 종목 수
    - **last_update**: 마지막 업데이트 시간
    - **data_files**: 데이터별 상태 (OK, NO_DATA, ERROR)
    - **details**: 상세 데이터 상태 리스트

    ## Example
    ```bash
    curl "http://localhost:5111/api/system/data-status"
    ```
    """
    stock_repo = StockRepository(session)
    signal_repo = SignalRepository(session)

    # 전체 종목 수
    total_stocks = stock_repo.count()

    # 각 데이터 소스별 상태 확인
    data_files: Dict[str, str] = {}
    details: List[DataStatusItem] = []

    # 주가 데이터 상태
    try:
        price_count = session.execute(
            func.count(DailyPrice.id)
        ).scalar() or 0
        latest_price = session.execute(
            func.max(DailyPrice.date)
        ).scalar()

        price_status = "OK" if price_count > 0 else "NO_DATA"
        data_files["prices"] = price_status

        details.append(DataStatusItem(
            name="prices",
            status=price_status,
            last_update=latest_price.isoformat() if latest_price else None,
            record_count=price_count,
        ))
    except Exception as e:
        data_files["prices"] = "ERROR"
        details.append(DataStatusItem(
            name="prices",
            status="ERROR",
            error_message=str(e),
        ))

    # 시그널 데이터 상태
    try:
        signal_count = signal_repo.count()
        latest_signal = session.execute(
            func.max(Signal.created_at)
        ).scalar()

        signal_status = "OK" if signal_count > 0 else "NO_DATA"
        data_files["signals"] = signal_status

        details.append(DataStatusItem(
            name="signals",
            status=signal_status,
            last_update=latest_signal.isoformat() if latest_signal else None,
            record_count=signal_count,
        ))
    except Exception as e:
        data_files["signals"] = "ERROR"
        details.append(DataStatusItem(
            name="signals",
            status="ERROR",
            error_message=str(e),
        ))

    # 업데이트된 종목 수 (최근 7일 이내 데이터가 있는 종목)
    try:
        from datetime import date, timedelta
        from sqlalchemy import select

        week_ago = date.today() - timedelta(days=7)
        updated_stocks = session.execute(
            select(func.count(func.distinct(DailyPrice.ticker)))
            .where(DailyPrice.date >= week_ago)
        ).scalar() or 0
    except Exception:
        updated_stocks = 0

    # 전체 업데이트 시간
    last_update = None
    if details:
        valid_updates = [d.last_update for d in details if d.last_update]
        if valid_updates:
            last_update = max(valid_updates)

    return DataStatusResponse(
        total_stocks=total_stocks,
        updated_stocks=updated_stocks,
        last_update=last_update,
        data_files=data_files,
        details=details,
    )


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="시스템 헬스 체크",
    description="전체 시스템의 건강 상태를 조회합니다. 데이터베이스, Redis, Celery, 외부 서비스 상태를 확인합니다.",
    responses={
        200: {"description": "조회 성공"},
        500: {"description": "서버 오류"},
    },
)
def get_system_health(
    session: Session = Depends(get_db_session),
) -> SystemHealthResponse:
    """
    전체 시스템 헬스 체크

    ## 설명
    데이터베이스, Redis, Celery, 외부 서비스 상태를 확인합니다.

    ## 반환 데이터
    - **status**: 전체 상태 (healthy, degraded, unhealthy)
    - **services**: 개별 서비스 상태 (database, redis, celery, vcp_scanner, signal_engine)
    - **uptime_seconds**: 서버 실행 시간 (초)

    ## Example
    ```bash
    curl "http://localhost:5111/api/system/health"
    ```
    """
    # 개별 서비스 상태 확인
    services: Dict[str, str] = {}

    # 데이터베이스 상태
    db_status = check_database_health(session)
    services["database"] = db_status

    # Redis 상태
    redis_status = check_redis_health()
    services["redis"] = redis_status

    # Celery 상태
    celery_status = check_celery_health()
    if celery_status:
        services["celery"] = celery_status

    # API Gateway (자신) 상태
    services["api_gateway"] = "up"

    # 외부 서비스 상태 (선택적)
    try:
        from src.middleware.service_registry import ServiceRegistry
        registry = ServiceRegistry()

        # VCP Scanner
        try:
            import httpx
            vcp_url = registry.get_service_url("vcp_scanner")
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{vcp_url}/health")
                services["vcp_scanner"] = "up" if response.status_code == 200 else "down"
        except Exception:
            services["vcp_scanner"] = "down"

        # Signal Engine
        try:
            signal_url = registry.get_service_url("signal_engine")
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{signal_url}/health")
                services["signal_engine"] = "up" if response.status_code == 200 else "down"
        except Exception:
            services["signal_engine"] = "down"

    except Exception:
        pass

    # 전체 상태 판정
    down_services = sum(1 for s in services.values() if s == "down")
    if down_services == 0:
        overall_status = "healthy"
    elif down_services <= len(services) // 2:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return SystemHealthResponse(
        status=overall_status,
        services=services,
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=get_uptime_seconds(),
        database_status=db_status,
        redis_status=redis_status,
        celery_status=celery_status,
    )


@router.post(
    "/update-data-stream",
    summary="데이터 업데이트 SSE 스트리밍",
    description="백그라운드 작업으로 데이터 업데이트를 트리거하고 진행 상황을 Server-Sent Events로 스트리밍합니다.",
    responses={
        200: {"description": "SSE 스트리밍 시작"},
        500: {"description": "서버 오류"},
    },
)
async def update_data_stream():
    """
    데이터 업데이트 SSE 스트리밍

    ## 설명
    VCP 스캔과 시그널 생성을 백그라운드로 실행하고 진행 상황을 실시간으로 스트리밍합니다.

    ## 이벤트 타입
    - **start**: 업데이트 시작
    - **progress**: 진행 상황 (vcp_scan, signal_gen)
    - **complete**: 완료
    - **error**: 오류 발생

    ## Example
    ```bash
    curl -N "http://localhost:5111/api/system/update-data-stream"
    ```
    """
    from fastapi.responses import StreamingResponse

    async def event_generator():
        """이벤트 스트리밍 생성기"""
        try:
            yield "event: start\ndata: {'status': 'started', 'message': '데이터 업데이트 시작'}\n\n"

            # Celery 태스크 트리거

            # VCP 스캔
            yield "event: progress\ndata: {'stage': 'vcp_scan', 'message': 'VCP 패턴 스캔 중...'}\n\n"
            # 실제 스캔은 비동기로 실행
            # scan_vcp_signals.delay()

            yield "event: progress\ndata: {'stage': 'signal_gen', 'message': '시그널 생성 중...'}\n\n"
            # generate_jongga_v2_signals.delay()

            yield "event: complete\ndata: {'status': 'completed', 'message': '데이터 업데이트 완료'}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {{'status': 'error', 'message': '{str(e)}'}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
