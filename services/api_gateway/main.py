"""
KR Stock - API Gateway
FastAPI 기반 API Gateway 구현
"""
# ruff: noqa: E402  # dotenv 로드 후 import 필요

import logging
from fastapi import FastAPI, HTTPException, status, Request, Query, Depends

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import httpx
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

from services.api_gateway.service_registry import get_registry
from src.database.session import get_db_session
from src.database.models import MarketStatus, DailyPrice
from src.repositories.stock_repository import StockRepository
from sqlalchemy import select, desc

# WebSocket, 메트릭, 미들웨어
from src.websocket.routes import router as websocket_router
from src.websocket.server import price_broadcaster
from src.utils.metrics import metrics_registry
from src.middleware.metrics_middleware import MetricsMiddleware
from src.middleware.logging_middleware import RequestLoggingMiddleware
from src.middleware.request_id import RequestIDMiddleware
from src.middleware.slow_endpoint import SlowEndpointMiddleware

# 대시보드
from services.api_gateway.dashboard import router as dashboard_router

# Kiwoom 연동
from src.api_gateway.kiwoom_integration import (
    create_kiwoom_integration,
    setup_kiwoom_routes,
)
from src.websocket.server import connection_manager, price_broadcaster

# API 스키마
from services.api_gateway.schemas import (
    HealthCheckResponse,
    SignalResponse,
    MarketGateStatus,
    MetricsResponse,
    RealtimePricesRequest,
    StockDetailResponse,
    ChartPoint,
    StockChartResponse,
    FlowDataPoint,
    StockFlowResponse,
    SignalHistoryItem,
    SignalHistoryResponse,
    BacktestStatsItem,
    BacktestKPIResponse,
)


# Lifespan 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Kiwoom WebSocket 연결 추적
    kiwoom_ws = None

    # Startup
    print("🚀 API Gateway Starting...")
    print("📡 Registering services...")
    registry = get_registry()
    print(f"✅ Registered {len(registry.list_services())} services")

    # Kiwoom REST API 연동 시작
    print("📡 Initializing Kiwoom REST API integration...")
    kiwoom_integration = create_kiwoom_integration()
    await kiwoom_integration.startup()

    # Kiwoom WebSocket 직접 연결 및 실시간 데이터 브로드캐스트 설정
    print("📡 Connecting to Kiwoom WebSocket for real-time prices...")
    kiwoom_pipeline = kiwoom_integration.pipeline

    if kiwoom_pipeline:
        # Pipeline이 실행될 때까지 대기
        import asyncio
        for attempt in range(10):  # 최대 10초 대기
            if kiwoom_pipeline.is_running():
                print("✅ Kiwoom Pipeline is running")
                break
            print(f"⏳ Waiting for Kiwoom Pipeline... ({attempt + 1}/10)")
            await asyncio.sleep(1)

        if kiwoom_pipeline.is_running():
            # 실시간 데이터 브로드캐스트 콜백 등록
            from src.kiwoom.base import KiwoomEventType

            async def broadcast_price_to_frontend(price_data):
                """Kiwoom 실시간 데이터를 프론트엔드 WebSocket으로 브로드캐스트"""
                try:
                    await connection_manager.broadcast(
                        {
                            "type": "price_update",
                            "ticker": price_data.ticker,
                            "data": {
                                "price": price_data.price,
                                "change": price_data.change,
                                "change_rate": price_data.change_rate,
                                "volume": price_data.volume,
                                "bid_price": price_data.bid_price,
                                "ask_price": price_data.ask_price,
                            },
                            "timestamp": price_data.timestamp,
                            "source": "kiwoom_ws",
                        },
                        topic=f"price:{price_data.ticker}",
                    )
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Broadcasted Kiwoom price: {price_data.ticker} = {price_data.price}")
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error broadcasting price: {e}")

            # 이벤트 핸들러 등록
            kiwoom_pipeline.register_event_handler(
                KiwoomEventType.RECEIVE_REAL_DATA,
                broadcast_price_to_frontend
            )
            print("✅ Kiwoom price broadcast handler registered")

            # 기본 종목 구독 (삼성전자, SK하이닉스, NAVER, 현대차)
            default_tickers = ["005930", "000660", "035420", "005380"]
            for ticker in default_tickers:
                try:
                    await kiwoom_pipeline.subscribe(ticker)
                    price_broadcaster.add_ticker(ticker)
                    print(f"✅ Subscribed to {ticker}")
                except Exception as e:
                    print(f"⚠️ Failed to subscribe to {ticker}: {e}")

            # Kiwoom WebSocket Bridge 연결 (기존 호환성 유지)
            try:
                from src.websocket.kiwoom_bridge import init_kiwoom_ws_bridge
                await init_kiwoom_ws_bridge(kiwoom_pipeline)
                print("✅ Kiwoom WebSocket Bridge connected")
            except Exception as e:
                print(f"⚠️ Kiwoom WebSocket Bridge: {e}")

        else:
            print("⚠️ Kiwoom Pipeline failed to start. Real-time prices not available.")

    # Kiwoom REST API가 구성된 경우 Price Broadcaster 시작 (Pipeline 상관없이)
    # WebSocket 연결 문제로 우회: REST API로만 가격 조회 후 브로드캐스트
    import os
    use_kiwoom_rest = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"
    has_api_keys = bool(os.getenv("KIWOOM_APP_KEY") and os.getenv("KIWOOM_SECRET_KEY"))

    if use_kiwoom_rest and has_api_keys:
        print("📡 Starting Price Broadcaster (REST API mode)...")
        await price_broadcaster.start()
        print("✅ Price Broadcaster started")
    else:
        print("⚠️ Real-time price broadcasting not available (Kiwoom REST API not configured)")

    yield

    # Shutdown
    print("🛑 API Gateway Shutting down...")

    # Kiwoom WebSocket Bridge 중지
    print("📡 Stopping Kiwoom WebSocket Bridge...")
    try:
        from src.websocket.kiwoom_bridge import shutdown_kiwoom_ws_bridge
        await shutdown_kiwoom_ws_bridge()
        print("✅ Kiwoom WebSocket Bridge stopped")
    except Exception as e:
        print(f"⚠️ Error stopping Kiwoom WebSocket Bridge: {e}")

    # 가격 브로드캐스터 중지
    print("📡 Stopping Price Broadcaster...")
    await price_broadcaster.stop()
    print("✅ Price Broadcaster stopped")

    # Kiwoom 연동 중지
    print("📡 Stopping Kiwoom REST API integration...")
    await kiwoom_integration.shutdown()


app = FastAPI(
    title="KR Stock API Gateway",
    description="""
    ## 한국 주식 분석 시스템 API Gateway

    Open Architecture 기반 마이크로서비스 한국 주식 분석 시스템의 API Gateway입니다.

    ## 주요 기능
    - **VCP 패턴 스캐너**: 볼린저밴드 수축 패턴 탐지
    - **종가베팅 V2 시그널**: 12점 scoring 기반 매매 시그널
    - **실시간 가격 브로드캐스팅**: WebSocket 기반 실시간 가격 업데이트
    - **SmartMoney 수급 분석**: 외국인/기관 수급 데이터 분석

    ## 지원 서비스
    - VCP Scanner (port 5112)
    - Signal Engine (port 5113)
    - Market Analyzer (port 5114)
    - Real-time Price Broadcaster
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,

    # OpenAPI 설정
    openapi_tags=[
        {
            "name": "health",
            "description": "헬스 체크 및 시스템 상태 확인",
        },
        {
            "name": "signals",
            "description": "VCP 및 종가베팅 시그널 조회",
        },
        {
            "name": "market",
            "description": "Market Gate 및 시장 상태",
        },
        {
            "name": "realtime",
            "description": "실시간 가격 정보",
        },
        {
            "name": "metrics",
            "description": "Prometheus 메트릭 및 모니터링",
        },
        {
            "name": "dashboard",
            "description": "모니터링 대시보드",
        },
        {
            "name": "kiwoom",
            "description": "키움증권 REST API 연동 (실시간 시세, 주문)",
        },
        {
            "name": "stocks",
            "description": "종목 상세, 차트, 수급, 시그널 조회",
        },
        {
            "name": "ai",
            "description": "AI 종목 분석 및 감성 분석",
        },
        {
            "name": "chatbot",
            "description": "AI 챗봇 및 종목 추천",
        },
        {
            "name": "performance",
            "description": "누적 수익률 및 성과 분석",
        },
    ],

    # Contact 정보
    contact={
        "name": "KR Stock Team",
        "email": "support@krstock.example.com",
    },

    # 라이선스 정보
    license_info={
        "name": "MIT",
    },
)


# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 ID 미들웨어 (가장 먼저 실행)
app.add_middleware(RequestIDMiddleware)

# 느린 엔드포인트 추적 미들웨어
app.add_middleware(SlowEndpointMiddleware, threshold=1.0)

# 요청/응답 로깅 미들웨어 (CORS 다음, Metrics 이전)
app.add_middleware(
    RequestLoggingMiddleware,
    skip_paths=["/health", "/metrics", "/readiness"],
    log_body=False,  # 바디 로깅 비활성화 (성능 및 보안)
)

# 메트릭 수집 미들웨어
app.add_middleware(MetricsMiddleware)

# WebSocket 라우터 포함
app.include_router(websocket_router)

# 대시보드 라우터 포함
app.include_router(dashboard_router)

# 백테스트 라우터 포함
from services.api_gateway.routes.backtest import router as backtest_router
app.include_router(backtest_router)
print("✅ Backtest routes registered")

# Stocks 라우터 포함
from services.api_gateway.routes.stocks import router as stocks_router
app.include_router(stocks_router)
print("✅ Stocks routes registered")

# AI 라우터 포함
from services.api_gateway.routes.ai import router as ai_router
app.include_router(ai_router)
print("✅ AI routes registered")

# System 라우터 포함
from services.api_gateway.routes.system import router as system_router
app.include_router(system_router)
print("✅ System routes registered")

# Triggers 라우터 포함
from services.api_gateway.routes.triggers import router as triggers_router
app.include_router(triggers_router)
print("✅ Triggers routes registered")

# Kiwoom 라우터 설정 (항상 등록, 내부에서可用性 체크)
from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
ws_bridge = get_kiwoom_ws_bridge()
setup_kiwoom_routes(app, ws_bridge=ws_bridge)
print("✅ Kiwoom routes registered")

# Chatbot 라우터 포함
from services.api_gateway.routes.chatbot import router as chatbot_router
app.include_router(chatbot_router)
print("✅ Chatbot routes registered")

# Performance 라우터 포함
from services.api_gateway.routes.performance import router as performance_router
app.include_router(performance_router)
print("✅ Performance routes registered")


# ============================================================================
# Health Check
# ============================================================================

@app.get(
    "/health",
    tags=["health"],
    response_model=HealthCheckResponse,
    responses={
        200: {
            "description": "서비스 정상",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "api-gateway",
                        "version": "2.0.0",
                    }
                }
            }
        }
    },
)
async def health_check():
    """
    API Gateway 헬스 체크

    서비스가 정상 동작 중인지 확인합니다.
    """
    return HealthCheckResponse(
        status="healthy",
        service="api-gateway",
        version="2.0.0",
        timestamp=datetime.now(),
    )


@app.get(
    "/",
    tags=["health"],
    responses={
        200: {
            "description": "루트 엔드포인트 정보",
            "content": {
                "application/json": {
                    "example": {
                        "message": "KR Stock API Gateway",
                        "version": "2.0.0",
                        "docs": "/docs",
                        "status": "operational",
                    }
                }
            }
        }
    },
)
async def root():
    """
    루트 엔드포인트

    API Gateway의 기본 정보와 문서 링크를 반환합니다.
    """


    return {
        "message": "KR Stock API Gateway",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
    }


# ============================================================================
# Metrics (Prometheus)
# ============================================================================

@app.get(
    "/metrics",
    tags=["metrics"],
    responses={
        200: {
            "description": "Prometheus 텍스트 형식 메트릭",
            "content": {
                "text/plain": {
                    "example": "# HELP api_requests_total Total API requests\napi_requests_total 1250\n"
                }
            }
        }
    },
)
async def prometheus_metrics():
    """
    Prometheus 메트릭 엔드포인트

    Prometheus 텍스트 형식으로 메트릭을 반환합니다.
    """
    metrics = metrics_registry.export()
    return PlainTextResponse(
        content=metrics,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get(
    "/api/metrics",
    tags=["metrics"],
    response_model=MetricsResponse,
    responses={
        200: {
            "description": "JSON 형식 메트릭",
        }
    },
)
async def json_metrics(
    metric_type: Optional[str] = None,
    limit: int = 10,
):
    """
    JSON 메트릭 엔드포인트

    JSON 형식으로 모든 메트릭을 반환합니다.

    - **metric_type**: 필터링할 메트릭 타입 (counter, gauge, histogram)
    - **limit**: 반환할 메트릭 수
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

    return MetricsResponse(
        metrics=metrics_list,
        total=len(all_metrics),
        filtered=len(metrics_list),
    )


@app.post(
    "/api/metrics/reset",
    tags=["metrics"],
    responses={
        200: {
            "description": "메트릭 리셋 성공",
        }
    },
)
async def reset_metrics():
    """
    메트릭 리셋 엔드포인트 (개발/테스트용)

    모든 메트릭을 0으로 리셋합니다.
    """
    metrics_registry.reset_all()
    return {"message": "All metrics reset"}


# ============================================================================
# KR Market Routes (Proxy to VCP Scanner)
# ============================================================================

@app.get(
    "/api/kr/signals",
    tags=["signals"],
    response_model=List[SignalResponse],
    responses={
        200: {
            "description": "시그널 목록 반환 성공",
        },
        503: {
            "description": "VCP Scanner 서비스 unavailable",
        }
    },
)
async def get_kr_signals(
    limit: int = Query(default=20, ge=1, le=100, description="반환할 시그널 수"),
):
    """
    활성 VCP 시그널 조회

    VCP Scanner 서비스로 프록시하여 시그널 목록을 반환합니다.

    - **limit**: 반환할 최대 시그널 수 (1-100)
    """
    registry = get_registry()

    # VCP Scanner 서비스 조회
    vcp_scanner = registry.get_service("vcp-scanner")
    if not vcp_scanner:
        raise HTTPException(
            status_code=503,
            detail="VCP Scanner service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{vcp_scanner['url']}/signals",
                params={"limit": limit},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # VCP Scanner 응답 변환
            signals_data = data.get("signals", []) if isinstance(data, dict) and "signals" in data else []

            # VCP 결과를 SignalResponse 형식으로 변환
            transformed_signals = []
            for signal in signals_data:
                # total_score를 기반으로 등급 계산
                total_score = signal.get("total_score", 0)
                if total_score >= 80:
                    grade = "S"
                elif total_score >= 70:
                    grade = "A"
                elif total_score >= 60:
                    grade = "B"
                else:
                    grade = "C"

                # analysis_date가 YYYY-MM-DD 형식이면 ISO datetime으로 변환
                analysis_date = signal.get("analysis_date")
                if analysis_date and len(analysis_date) == 10:  # YYYY-MM-DD
                    created_at = f"{analysis_date}T00:00:00"
                else:
                    created_at = datetime.now().isoformat()

                transformed_signals.append({
                    "ticker": signal.get("ticker", ""),
                    "name": signal.get("name", ""),
                    "signal_type": "vcp",
                    "score": total_score,
                    "grade": grade,
                    "entry_price": None,
                    "target_price": None,
                    "created_at": created_at
                })

            return transformed_signals

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"VCP Scanner error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"VCP Scanner unavailable: {str(e)}",
            )


@app.get(
    "/api/kr/market-gate",
    tags=["market"],
    response_model=MarketGateStatus,
    responses={
        200: {
            "description": "Market Gate 상태 반환 성공",
        },
        503: {
            "description": "Market Analyzer 서비스 unavailable",
        }
    },
)
async def get_kr_market_gate(db: Session = Depends(get_db_session)):
    """
    Market Gate 상태 조회

    데이터베이스에서 가장 최신 Market Gate 상태를 반환합니다.

    - **GREEN**: 매수 우위 (전체 매수)
    - **YELLOW**: 관망 (일부 매수)
    - **RED**: 매도 (현금 보유 현금 비중 ↑)
    """
    from services.api_gateway.schemas import SectorItem

    # 데이터베이스에서 가장 최신 MarketStatus 조회
    market_status = db.query(MarketStatus).order_by(MarketStatus.date.desc()).first()

    # KOSPI/KOSDAQ 상태 결정
    def get_market_status(change_pct: Optional[float]) -> str:
        if change_pct is None:
            return "정보 없음"
        elif change_pct > 1.0:
            return "강세"
        elif change_pct > 0:
            return "소폭 상승"
        elif change_pct > -1.0:
            return "소폭 하락"
        else:
            return "약세"

    # 섹터 신호 결정 (변동률 기반)
    def get_sector_signal(change_pct: float) -> str:
        if change_pct > 1.0:
            return "bullish"
        elif change_pct < -1.0:
            return "bearish"
        else:
            return "neutral"

    # 섹터 점수 계산 (0-100)
    def get_sector_score(change_pct: float) -> float:
        # 변동률을 기반으로 50점 기준 ±50점 부여
        return max(0, min(100, 50 + (change_pct * 10)))

    if not market_status:
        # 데이터가 없는 경우 빈 섹터 목록 반환
        return MarketGateStatus(
            status="YELLOW",
            level=50,
            kospi_status="데이터 없음",
            kosdaq_status="데이터 없음",
            kospi_close=None,
            kospi_change_pct=None,
            kosdaq_close=None,
            kosdaq_change_pct=None,
            sectors=[],  # 빈 배열 반환 (mock 데이터 제거)
            updated_at=datetime.now().isoformat(),
        )

    kospi_status = get_market_status(market_status.kospi_change_pct)
    kosdaq_status = get_market_status(market_status.kosdaq_change_pct)

    # 섹터 데이터 생성 (MarketStatus의 JSON 필드 활용)
    sectors = []
    if market_status.sector_scores:
        # sector_scores는 JSON 형식으로 저장: [{"name": "반도체", "change_pct": 2.5}, ...]
        try:
            import json
            sector_data_list = json.loads(market_status.sector_scores) if isinstance(market_status.sector_scores, str) else market_status.sector_scores
            for sector in sector_data_list:
                sectors.append(SectorItem(
                    name=sector.get("name", "알 수 없음"),
                    signal=get_sector_signal(sector.get("change_pct", 0)),
                    change_pct=sector.get("change_pct", 0),
                    score=get_sector_score(sector.get("change_pct", 0)),
                ))
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse sector data: {e}")

    # 섹터 데이터가 없으면 빈 배열 반환 (mock 데이터 제거)
    if not sectors:
        logger.warning("No sector data available in database")

    return MarketGateStatus(
        status=market_status.gate or "YELLOW",
        level=market_status.gate_score or 50,
        kospi_status=kospi_status,
        kosdaq_status=kosdaq_status,
        kospi_close=market_status.kospi,  # 컬럼명 수정: kospi_close → kospi
        kospi_change_pct=market_status.kospi_change_pct,
        kosdaq_close=market_status.kosdaq,  # 컬럼명 수정: kosdaq_close → kosdaq
        kosdaq_change_pct=market_status.kosdaq_change_pct,
        sectors=sectors,
        updated_at=market_status.created_at.isoformat() if market_status.created_at else datetime.now().isoformat(),
    )


@app.get(
    "/api/kr/backtest-kpi",
    tags=["backtest"],
    response_model=BacktestKPIResponse,
    responses={
        200: {
            "description": "백테스트 KPI 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "vcp": {
                            "strategy": "vcp",
                            "status": "OK",
                            "count": 42,
                            "win_rate": 65.5,
                            "avg_return": 3.2,
                            "profit_factor": 1.8,
                        },
                        "closing_bet": {
                            "strategy": "jongga_v2",
                            "status": "Accumulating",
                            "count": 1,
                            "message": "최소 2일 데이터 필요",
                        },
                    }
                }
            }
        }
    },
)
async def get_backtest_kpi(db: Session = Depends(get_db_session)):
    """
    백테스트 KPI 조회 (대시보드용)

    VCP 및 종가베팅 V2 전략의 백테스트 결과 요약을 반환합니다.

    ## 반환 데이터
    - **vcp**: VCP 전략 백테스트 통계
    - **closing_bet**: 종가베팅 V2 전략 백테스트 통계
    """
    from src.repositories.backtest_repository import BacktestRepository

    repo = BacktestRepository(db)

    # VCP 전략 백테스트 통계
    vcp_summary = repo.get_summary(config_name="vcp")
    if vcp_summary["total_backtests"] >= 2:
        vcp_stats = BacktestStatsItem(
            strategy="vcp",
            status="OK",
            count=vcp_summary["total_backtests"],
            win_rate=vcp_summary["avg_win_rate"],
            avg_return=vcp_summary["avg_return_pct"],
            profit_factor=vcp_summary.get("profit_factor"),
        )
    else:
        vcp_stats = BacktestStatsItem(
            strategy="vcp",
            status="Accumulating" if vcp_summary["total_backtests"] == 1 else "No Data",
            count=vcp_summary["total_backtests"],
            message="최소 2일 데이터 필요" if vcp_summary["total_backtests"] == 1 else "데이터 없음",
        )

    # 종가베팅 V2 전략 백테스트 통계
    jongga_summary = repo.get_summary(config_name="jongga_v2")
    if jongga_summary["total_backtests"] >= 2:
        closing_bet_stats = BacktestStatsItem(
            strategy="jongga_v2",
            status="OK",
            count=jongga_summary["total_backtests"],
            win_rate=jongga_summary["avg_win_rate"],
            avg_return=jongga_summary["avg_return_pct"],
            profit_factor=jongga_summary.get("profit_factor"),
        )
    else:
        closing_bet_stats = BacktestStatsItem(
            strategy="jongga_v2",
            status="Accumulating" if jongga_summary["total_backtests"] == 1 else "No Data",
            count=jongga_summary["total_backtests"],
            message="최소 2일 데이터 필요" if jongga_summary["total_backtests"] == 1 else "데이터 없음",
        )

    return BacktestKPIResponse(
        vcp=vcp_stats,
        closing_bet=closing_bet_stats,
    )


@app.get(
    "/api/kr/jongga-v2/latest",
    tags=["signals"],
    response_model=List[SignalResponse],
    responses={
        200: {
            "description": "최신 종가베팅 V2 시그널 반환 성공",
        },
        503: {
            "description": "Signal Engine 서비스 unavailable",
        }
    },
)
async def get_jongga_v2_latest():
    """
    최신 종가베팅 V2 시그널 조회

    Signal Engine 서비스로 프록시하여 최신 종가베팅 V2 시그널을 반환합니다.

    종가베팅 V2는 뉴스, 거래량, 차트, 캔들, 기간, 수급 등 12가지 항목으로 종목을 평가합니다.
    """
    registry = get_registry()

    # Signal Engine 서비스 조회
    signal_engine = registry.get_service("signal-engine")
    if not signal_engine:
        raise HTTPException(
            status_code=503,
            detail="Signal Engine service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{signal_engine['url']}/signals/latest",
                timeout=15.0,  # AI 분석이 포함되어 시간 더 소료
            )
            response.raise_for_status()
            data = response.json()

            # Signal Engine 응답 변환
            signals_data = data.get("signals", []) if isinstance(data, dict) else data

            # signal_type 추가 (score 객체는 그대로 유지)
            transformed_signals = []
            for signal in signals_data:
                transformed = dict(signal)
                # signal_type 추가 (기본값: "jongga_v2")
                transformed["signal_type"] = "jongga_v2"
                # score 객체는 그대로 유지 (detail 포함)
                transformed_signals.append(transformed)

            return transformed_signals

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Signal Engine error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Signal Engine unavailable: {str(e)}",
            )


@app.post(
    "/api/kr/jongga-v2/analyze",
    tags=["signals"],
    responses={
        200: {
            "description": "종가베팅 V2 단일 종목 분석 성공",
            "content": {
                "application/json": {
                    "example": {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "score": {"total": 8, "news": 2, "volume": 2, "chart": 1, "candle": 1, "period": 1, "flow": 0},
                        "grade": "A",
                        "position_size": 1200,
                        "entry_price": 80000,
                        "target_price": 92000,
                        "stop_loss": 76000,
                        "reasons": ["긍정적 뉴스 다수", "거래대금 급증"],
                        "created_at": "2026-01-28T10:48:55",
                    }
                }
            }
        },
        503: {
            "description": "Signal Engine 서비스 unavailable",
        }
    },
)
async def analyze_jongga_v2(request: dict):
    """
    종가베팅 V2 단일 종목 분석

    Signal Engine 서비스로 프록시하여 단일 종목의 종가베팅 V2 시그널을 생성합니다.

    - **ticker**: 종목 코드 (6자리)
    - **name**: 종목명
    - **price**: 현재가
    """
    registry = get_registry()

    # Signal Engine 서비스 조회
    signal_engine = registry.get_service("signal-engine")
    if not signal_engine:
        raise HTTPException(
            status_code=503,
            detail="Signal Engine service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{signal_engine['url']}/analyze",
                json=request,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Signal Engine error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Signal Engine unavailable: {str(e)}",
            )


# ============================================================================
# Stock Detail & Chart Routes
# ============================================================================

@app.get(
    "/api/kr/stocks/{ticker}",
    tags=["signals"],
    response_model=StockDetailResponse,
    responses={
        200: {
            "description": "종목 상세 정보 반환 성공",
        },
        404: {
            "description": "종목을 찾을 수 없음",
        },
    },
)
async def get_stock_detail(ticker: str, db: Session = Depends(get_db_session)):
    """
    종목 상세 정보 조회

    데이터베이스에서 종목 기본 정보와 최신 가격을 반환합니다.

    - **ticker**: 종목 코드 (6자리)
    """
    # 종목 정보 조회
    stock_repo = StockRepository(db)
    stock = stock_repo.get_by_ticker(ticker)

    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"종목을 찾을 수 없습니다: {ticker}"
        )

    # 최신 가격 정보 조회
    latest_price = db.execute(
        select(DailyPrice)
        .where(DailyPrice.ticker == ticker)
        .order_by(desc(DailyPrice.date))
        .limit(1)
    ).scalar_one_or_none()

    # 응답 생성
    return StockDetailResponse(
        ticker=stock.ticker,
        name=stock.name,
        market=stock.market,
        sector=stock.sector,
        current_price=latest_price.close_price if latest_price else None,
        price_change=None,  # TODO: Calculate from previous day
        price_change_pct=None,  # TODO: Calculate from previous day
        volume=latest_price.volume if latest_price else None,
        updated_at=latest_price.date if latest_price else None,
    )


@app.get(
    "/api/kr/stocks/{ticker}/chart",
    tags=["signals"],
    response_model=StockChartResponse,
    responses={
        200: {
            "description": "차트 데이터 반환 성공",
        },
        404: {
            "description": "종목을 찾을 수 없음",
        },
    },
)
async def get_stock_chart(
    ticker: str,
    period: str = Query(default="6mo", description="기간 (1mo, 3mo, 6mo, 1y)"),
    db: Session = Depends(get_db_session)
):
    """
    종목 차트 데이터 조회

    데이터베이스에서 기간별 OHLCV 데이터를 반환합니다.
    TimescaleDB hypertable을 활용하여 빠른 조회를 지원합니다.

    - **ticker**: 종목 코드 (6자리)
    - **period**: 기간 (1mo, 3mo, 6mo, 1y)
    """
    # 종목 존재 확인
    stock_repo = StockRepository(db)
    stock = stock_repo.get_by_ticker(ticker)

    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"종목을 찾을 수 없습니다: {ticker}"
        )

    # 기간 계산
    from datetime import timedelta
    period_days = {
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
    }
    days = period_days.get(period, 180)

    cutoff_date = datetime.now().date() - timedelta(days=days)

    # 차트 데이터 조회
    chart_data = db.execute(
        select(DailyPrice)
        .where(DailyPrice.ticker == ticker)
        .where(DailyPrice.date >= cutoff_date)
        .order_by(DailyPrice.date)
    ).scalars().all()

    # 응답 생성
    return StockChartResponse(
        ticker=ticker,
        period=period,
        data=[
            ChartPoint(
                date=price.date,
                open=price.open_price or 0,
                high=price.high_price or 0,
                low=price.low_price or 0,
                close=price.close_price,
                volume=price.volume,
            )
            for price in chart_data
        ],
        total_points=len(chart_data),
    )


# ============================================================================
# Fallback Routes (Flask legacy) - 이전 단계 호환성용
# ============================================================================


@app.post(
    "/api/kr/realtime-prices",
    tags=["realtime"],
    summary="실시간 가격 일괄 조회",
    description="여러 종목의 실시간 가격 정보를 일괄 조회합니다. 이전 Flask 라우팅 호환용 엔드포인트입니다.",
    responses={
        200: {"description": "조회 성공"},
        503: {"description": "실시간 서비스 unavailable"},
    },
)
async def get_kr_realtime_prices(request: RealtimePricesRequest):
    """
    실시간 가격 일괄 조회 (이전 Flask 라우팅 호환)

    ## 설명
    여러 종목의 실시간 가격 정보를 일괄 조회합니다.

    ## Request Body
    - **tickers**: 종목 코드 리스트

    ## 반환 데이터
    - **prices**: 종목별 실시간 가격 정보
    """
    # TODO: Price Service 또는 Data Collector로 프록시
    return {"prices": {}}


@app.get(
    "/api/kr/stock-chart/{ticker}",
    tags=["stocks"],
    summary="종목 차트 데이터 조회 (레거시)",
    description="특정 종목의 차트 데이터(OHLCV)를 조회합니다. 이전 Flask 라우팅 호환용 엔드포인트입니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "종목을 찾을 수 없음"},
    },
)
async def get_kr_stock_chart(ticker: str, period: str = "6mo"):
    """
    종목 차트 데이터 조회 (레거시 호환용)

    ## 설명
    특정 종목의 차트 데이터를 조회합니다.
    최신 버전은 `/api/kr/stocks/{ticker}/chart`를 사용하세요.

    ## Parameters
    - **ticker**: 종목 코드 (6자리)
    - **period**: 기간 (1mo, 3mo, 6mo, 1y)
    """
    # TODO: Data Service 또는 VCP Scanner로 프록시
    return {"ticker": ticker, "data": []}


@app.get(
    "/api/kr/stocks/{ticker}/flow",
    tags=["stocks"],
    response_model=StockFlowResponse,
    responses={
        200: {
            "description": "종목 수급 데이터 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "ticker": "005930",
                        "period_days": 20,
                        "data": [
                            {
                                "date": "2026-01-20",
                                "foreign_net": 1500000,
                                "inst_net": 800000,
                                "foreign_net_amount": 120000000000,
                                "inst_net_amount": 64000000000,
                                "supply_demand_score": 65.5,
                            }
                        ],
                        "smartmoney_score": 72.5,
                        "total_points": 20,
                    }
                }
            }
        },
        404: {
            "description": "종목을 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "code": 404,
                        "detail": "Stock not found: 005930",
                    }
                }
            }
        }
    },
)
async def get_stock_flow(
    ticker: str,
    days: int = Query(default=20, ge=5, le=60, description="조회 기간 (일수, 5-60)"),
    session: Session = Depends(get_db_session),
):
    """
    종목 수급 데이터 조회 (외국인/기관 순매수)

    ## 설명
    특정 종목의 외국인/기관 수급 데이터를 조회합니다.

    ## Parameters
    - **ticker**: 종목 코드 (6자리, 예: 005930)
    - **days**: 조회 기간 (일수, 기본 20일, 최대 60일)

    ## 반환 데이터
    - **foreign_net**: 외국인 순매수 (주)
    - **inst_net**: 기관 순매수 (주)
    - **smartmoney_score**: SmartMoney 종합 점수 (0-100)
      - 외국인 40%, 기관 30% 가중

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/stocks/005930/flow?days=20"
    ```
    """
    try:
        # Repository 인스턴스 생성
        stock_repo = StockRepository(session)

        # 수급 데이터 조회
        flow_data = stock_repo.get_institutional_flow(ticker, days)

        # 종목 존재 확인
        stock = stock_repo.get_by_ticker(ticker)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock not found: {ticker}"
            )

        # SmartMoney 점수 계산 (외국인 40%, 기관 30%, 기본 30%)
        if flow_data:
            # 최근 5일 평균 순매수로 점수 계산
            recent_flow = flow_data[-5:] if len(flow_data) >= 5 else flow_data

            # 외국인 평균 순매수
            avg_foreign = sum(f.foreign_net_buy or 0 for f in recent_flow) / len(recent_flow)
            foreign_score = min(100, max(0, 50 + (avg_foreign / 100000) * 10))  # 기본 50점

            # 기관 평균 순매수
            avg_inst = sum(f.inst_net_buy or 0 for f in recent_flow) / len(recent_flow)
            inst_score = min(100, max(0, 50 + (avg_inst / 100000) * 10))  # 기본 50점

            # 종합 점수 (외국인 40%, 기관 30%)
            smartmoney_score = (foreign_score * 0.4) + (inst_score * 0.3) + 30  # 기본 30점
        else:
            smartmoney_score = 50.0  # 데이터 없을 때 기본 점수

        # 응답 데이터 변환
        response_data = [
            FlowDataPoint(
                date=flow.date,
                foreign_net=flow.foreign_net_buy or 0,
                inst_net=flow.inst_net_buy or 0,
                foreign_net_amount=flow.foreign_net_buy_amount,
                inst_net_amount=flow.inst_net_buy_amount,
                supply_demand_score=flow.supply_demand_score,
            )
            for flow in flow_data
        ]

        return StockFlowResponse(
            ticker=ticker,
            period_days=days,
            data=response_data,
            smartmoney_score=round(smartmoney_score, 2),
            total_points=len(response_data),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch flow data: {str(e)}"
        )


@app.get(
    "/api/kr/stocks/{ticker}/signals",
    tags=["stocks"],
    response_model=SignalHistoryResponse,
    responses={
        200: {
            "description": "종목 시그널 히스토리 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "ticker": "005930",
                        "total_signals": 10,
                        "open_signals": 2,
                        "closed_signals": 8,
                        "avg_return_pct": 5.2,
                        "win_rate": 75.0,
                        "signals": [
                            {
                                "id": 1,
                                "ticker": "005930",
                                "signal_type": "VCP",
                                "signal_date": "2024-01-15",
                                "status": "OPEN",
                                "score": 85.0,
                                "grade": "A",
                                "entry_price": 75000,
                                "exit_price": None,
                                "entry_time": "2024-01-15T09:30:00",
                                "exit_time": None,
                                "return_pct": None,
                            }
                        ],
                    }
                }
            }
        },
        404: {
            "description": "종목을 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "code": 404,
                        "detail": "Stock not found: 005930",
                    }
                }
            }
        }
    },
)
async def get_stock_signals(
    ticker: str,
    limit: int = Query(default=50, ge=1, le=100, description="최대 조회 수"),
    session: Session = Depends(get_db_session),
):
    """
    종목 시그널 히스토리 조회

    ## 설명
    특정 종목의 과거 시그널 내역을 조회합니다.

    ## Parameters
    - **ticker**: 종목 코드 (6자리, 예: 005930)
    - **limit**: 최대 조회 수 (기본 50, 최대 100)

    ## 반환 데이터
    - **signal_type**: VCP 또는 JONGGA_V2
    - **status**: OPEN (진행중) 또는 CLOSED (종료)
    - **return_pct**: 수익률 (%)
    - **win_rate**: 승률 (%)

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/stocks/005930/signals?limit=50"
    ```
    """
    try:
        from src.repositories.signal_repository import SignalRepository

        # Repository 인스턴스 생성
        signal_repo = SignalRepository(session)
        stock_repo = StockRepository(session)

        # 종목 존재 확인
        stock = stock_repo.get_by_ticker(ticker)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock not found: {ticker}"
            )

        # 시그널 히스토리 조회
        signals = signal_repo.get_by_ticker(ticker, limit)

        # 통계 계산
        open_signals = sum(1 for s in signals if s.status == "OPEN")
        closed_signals = sum(1 for s in signals if s.status == "CLOSED")

        # 수익률 계산 (CLOSED 시그널만)
        closed_signal_list = [s for s in signals if s.status == "CLOSED" and s.entry_price and s.exit_price]
        if closed_signal_list:
            returns = []
            for s in closed_signal_list:
                if s.exit_price and s.entry_price and s.entry_price > 0:
                    return_pct = ((s.exit_price - s.entry_price) / s.entry_price) * 100
                    s.return_pct = round(return_pct, 2)
                    returns.append(return_pct)

            avg_return_pct = round(sum(returns) / len(returns), 2) if returns else None
            win_rate = round(sum(1 for r in returns if r > 0) / len(returns) * 100, 2) if returns else None
        else:
            avg_return_pct = None
            win_rate = None

        # 응답 데이터 변환
        response_signals = [
            SignalHistoryItem(
                id=s.id,
                ticker=s.ticker,
                signal_type=s.signal_type,
                signal_date=s.signal_date,
                status=s.status,
                score=s.score,
                grade=s.grade,
                entry_price=s.entry_price,
                exit_price=s.exit_price,
                entry_time=s.entry_time,
                exit_time=s.exit_time,
                return_pct=s.return_pct if hasattr(s, 'return_pct') else None,
                exit_reason=s.exit_reason,
            )
            for s in signals
        ]

        return SignalHistoryResponse(
            ticker=ticker,
            total_signals=len(signals),
            open_signals=open_signals,
            closed_signals=closed_signals,
            avg_return_pct=avg_return_pct,
            win_rate=win_rate,
            signals=response_signals,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch signal history: {str(e)}"
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "detail": str(exc),
            "path": str(request.url.path),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.api_gateway.main:app",
        host="0.0.0.0",
        port=5111,
        reload=True,
    )
