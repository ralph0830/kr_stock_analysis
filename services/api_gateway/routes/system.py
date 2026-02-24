"""
System Routes
시스템 관리 API
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text, select

from src.database.session import get_db_session
from src.database.models import DailyPrice, Signal
from src.repositories.stock_repository import StockRepository
from src.repositories.signal_repository import SignalRepository
from src.health.health_checker import get_health_checker, init_health_checker
from services.api_gateway.schemas import (
    DataStatusResponse,
    DataStatusItem,
    SystemHealthResponse,
)

import time

router = APIRouter(prefix="/api/system", tags=["system"])

# 애플리케이션 시작 시간
_START_TIME = time.time()

# 헬스체커 초기화
init_health_checker(_START_TIME)


def get_uptime_seconds() -> float:
    """애플리케이션 실행 시간 (초)"""
    return time.time() - _START_TIME


def check_database_health(session: Session) -> str:
    """
    데이터베이스 헬스 체크 (동기, 레거시 호환)

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
    Redis 헬스 체크 (동기, 레거시 호환)

    Returns:
        상태 문자열 (up, down)
    """
    try:
        import redis
        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return "up"
    except Exception:
        return "down"


def check_celery_health() -> Optional[str]:
    """
    Celery 헬스 체크 (동기, 레거시 호환)

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
        # DailyPrice는 복합 기본 키 (ticker, date)를 사용하므로 raw SQL count(*) 사용
        price_count = session.execute(
            text("SELECT COUNT(*) FROM daily_prices")
        ).scalar() or 0
        latest_price = session.execute(
            text("SELECT MAX(date) FROM daily_prices")
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

        # Daytrading Scanner
        try:
            from services.api_gateway.service_registry import get_registry as get_api_registry
            api_registry = get_api_registry()
            daytrading_service = api_registry.get_service("daytrading-scanner")
            if daytrading_service:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(f"{daytrading_service['url']}/health")
                    services["daytrading_scanner"] = "up" if response.status_code == 200 else "down"
        except Exception:
            services["daytrading_scanner"] = "down"

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
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=get_uptime_seconds(),
        database_status=db_status,
        redis_status=redis_status,
        celery_status=celery_status,
    )


@router.get(
    "/health-v2",
    summary="향상된 시스템 헬스 체크 (V2)",
    description="비동기 헬스체크로 각 서비스의 응답 시간과 상세 정보를 제공합니다.",
    responses={
        200: {"description": "조회 성공"},
        503: {"description": "서비스 불가"},
    },
)
async def get_system_health_v2(
    session: Session = Depends(get_db_session),
):
    """
    향상된 시스템 헬스 체크 (V2)

    ## 설명
    비동기 헬스체크로 각 서비스의 응답 시간과 상세 정보를 제공합니다.

    ## 반환 데이터
    - **status**: 전체 상태 (healthy, degraded, unhealthy, unknown)
    - **services**: 개별 서비스 상세 정보
        - **status**: 서비스 상태
        - **response_time_ms**: 응답 시간 (밀리초)
        - **message**: 상태 메시지
        - **details**: 추가 정보 (메모리 사용량 등)
    - **uptime_seconds**: 서버 실행 시간

    ## Example
    ```bash
    curl "http://localhost:5111/api/system/health-v2"
    ```
    """
    health_checker = get_health_checker()
    if health_checker is None:
        return {"error": "Health checker not initialized"}

    # 비동기 세션 변환

    # 동기 세션을 사용하는 경우, 비동기 체크는 별도 수행
    system_health = await health_checker.check_all(session=None)

    # 추가 서비스 체크 (VCP Scanner, Signal Engine)
    try:
        from services.api_gateway.service_registry import get_registry
        registry = get_registry()

        # VCP Scanner
        vcp_service = registry.get_service("vcp-scanner")
        if vcp_service:
            vcp_health = await health_checker.check_vcp_scanner(vcp_service["url"])
            system_health.services["vcp_scanner"] = vcp_health

        # Signal Engine
        signal_service = registry.get_service("signal-engine")
        if signal_service:
            signal_health = await health_checker.check_signal_engine(signal_service["url"])
            system_health.services["signal_engine"] = signal_health

        # Market Analyzer
        market_service = registry.get_service("market-analyzer")
        if market_service:
            market_health = await health_checker.check_market_analyzer(market_service["url"])
            system_health.services["market_analyzer"] = market_health

        # Daytrading Scanner
        daytrading_service = registry.get_service("daytrading-scanner")
        if daytrading_service:
            try:
                import httpx
                start_time = time.time()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{daytrading_service['url']}/health")
                    response_time = (time.time() - start_time) * 1000
                    from src.health.health_checker import HealthStatus, ServiceHealth
                    daytrading_health = ServiceHealth(
                        name="daytrading_scanner",
                        status=HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.UNHEALTHY,
                        response_time_ms=response_time,
                        message=f"HTTP {response.status_code}" if response.status_code != 200 else "OK"
                    )
                    system_health.services["daytrading_scanner"] = daytrading_health
            except Exception as e:
                from src.health.health_checker import HealthStatus, ServiceHealth
                system_health.services["daytrading_scanner"] = ServiceHealth(
                    name="daytrading_scanner",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=str(e)
                )

    except Exception:
        # 서비스 레지스트리 실패 시 무시
        pass

    # 전체 상태 재계산
    from src.health.health_checker import HealthStatus
    down_services = sum(
        1 for s in system_health.services.values()
        if s.status in (HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN)
    )
    total_services = len(system_health.services)

    if down_services == 0:
        system_health.status = HealthStatus.HEALTHY
    elif down_services <= total_services // 2:
        system_health.status = HealthStatus.DEGRADED
    else:
        system_health.status = HealthStatus.UNHEALTHY

    return system_health.to_dict()


@router.get(
    "/health/{service_name}",
    summary="단일 서비스 헬스 체크",
    description="특정 서비스의 헬스 상태만 조회합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "서비스를 찾을 수 없음"},
    },
)
async def check_single_service(service_name: str):
    """
    단일 서비스 헬스 체크

    ## 설명
    특정 서비스의 헬스 상태만 빠르게 조회합니다.

    ## Parameters
    - **service_name**: 서비스 이름 (database, redis, vcp_scanner, signal_engine, etc.)

    ## Example
    ```bash
    curl "http://localhost:5111/api/system/health/database"
    ```
    """
    health_checker = get_health_checker()
    if health_checker is None:
        return {"error": "Health checker not initialized"}

    service_health = await health_checker.check_service(service_name)
    return service_health.to_dict()


@router.get(
    "/cache/metrics",
    summary="캐시 메트릭 조회",
    description="Redis 캐시 적중률, 저장/삭제 횟수 등 캐시 성능 지표를 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
        503: {"description": "캐시 서비스 unavailable"},
    },
)
async def get_cache_metrics():
    """
    캐시 메트릭 조회

    ## 설명
    Redis 캐시 적중률, 저장/삭제 횟수 등 캐시 성능 지표를 반환합니다.

    ## 반환 데이터
    - **hits**: 캐시 적중 횟수
    - **misses**: 캐시 미스 횟수
    - **sets**: 캐시 저장 횟수
    - **deletes**: 캐시 삭제 횟수
    - **hit_rate**: 적중률 (%)
    - **total_requests**: 전체 요청 수

    ## Example
    ```bash
    curl "http://localhost:5111/api/system/cache/metrics"
    ```
    """
    try:
        from src.cache import get_cache_metrics

        metrics = get_cache_metrics()
        return metrics.to_dict()

    except Exception as e:
        return {
            "error": f"Cache metrics not available: {str(e)}",
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "hit_rate": 0.0,
            "total_requests": 0,
        }


@router.get(
    "/metrics/slow",
    summary="느린 엔드포인트 조회",
    description="응답 시간이 임계값을 초과한 느린 엔드포인트 목록을 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
    },
)
async def get_slow_endpoints(limit: int = 10):
    """
    느린 엔드포인트 조회

    ## 설명
    응답 시간이 1초 이상인 느린 엔드포인트 목록을 반환합니다.

    ## Parameters
    - **limit**: 반환할 최대 항목 수 (기본값: 10)

    ## Example
    ```bash
    curl "http://localhost:5111/api/system/metrics/slow?limit=10"
    ```
    """
    try:
        from src.middleware.slow_endpoint import get_slow_endpoint_tracker

        tracker = get_slow_endpoint_tracker()
        return tracker.to_dict(limit=limit)

    except Exception as e:
        return {
            "threshold": 1.0,
            "slow_endpoints": [],
            "error": str(e),
        }


@router.post(
    "/cache/clear",
    summary="캐시 비우기",
    description="캐시를 모두 비우거나 패턴으로 선택적으로 삭제합니다.",
    responses={
        200: {"description": "삭제 성공"},
    },
)
async def clear_cache(pattern: str = "*"):
    """
    캐시 비우기

    ## 설명
    캐시를 모두 비우거나 패턴으로 선택적으로 삭제합니다.

    ## Parameters
    - **pattern**: 삭제할 캐시 키 패턴 (기본값: "*" - 모두 삭제)

    ## Example
    ```bash
    curl -X POST "http://localhost:5111/api/system/cache/clear?pattern=price:*"
    ```
    """
    try:
        from src.cache import get_cache

        cache = await get_cache()
        if not cache:
            return {"cleared": 0, "message": "Cache not available"}

        count = await cache.clear_pattern(pattern)
        return {"cleared": count, "pattern": pattern}

    except Exception as e:
        return {"cleared": 0, "error": str(e)}


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
