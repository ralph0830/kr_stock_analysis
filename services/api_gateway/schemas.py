"""
API Gateway Pydantic 모델 및 태그
API 문서화를 위한 데이터 모델 정의
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime, date


# ============================================================================
# Request/Response Models
# ============================================================================


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""

    status: str
    service: str
    version: str
    timestamp: Optional[datetime] = None


class SignalResponse(BaseModel):
    """VCP 시그널 응답 모델"""

    ticker: str
    name: str
    signal_type: str
    score: float
    grade: str
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    created_at: datetime


class SectorItem(BaseModel):
    """섹터 아이템 모델"""

    name: str  # 섹터명 (예: 반도체, 2차전지, 자동차)
    signal: str  # bullish, neutral, bearish
    change_pct: float  # 변동률 (%)
    score: Optional[float] = None  # 섹터 점수 (0-100)


class MarketGateStatus(BaseModel):
    """Market Gate 상태 모델"""

    status: str
    level: int
    kospi_status: str
    kosdaq_status: str
    kospi_close: Optional[float] = None  # KOSPI 종가
    kospi_change_pct: Optional[float] = None  # KOSPI 변동률 (%)
    kosdaq_close: Optional[float] = None  # KOSDAQ 종가
    kosdaq_change_pct: Optional[float] = None  # KOSDAQ 변동률 (%)
    sectors: List[SectorItem] = []  # 섹터별 상태
    updated_at: datetime


class ErrorDetail(BaseModel):
    """에러 상세 모델"""

    status: str = "error"
    code: int
    detail: str
    path: str


class MetricsResponse(BaseModel):
    """메트릭 응답 모델"""

    metrics: List[Dict[str, Any]]
    total: int
    filtered: int


class SystemOverview(BaseModel):
    """시스템 개요 모델"""

    status: str
    uptime_seconds: float
    timestamp: str
    services: Dict[str, str]


class ConnectionInfo(BaseModel):
    """연결 정보 모델"""

    active_connections: int
    subscriptions: Dict[str, int]
    broadcaster_running: bool


# ============================================================================
# Request Models
# ============================================================================


class RealtimePricesRequest(BaseModel):
    """실시간 가격 요청 모델"""

    tickers: List[str] = Field(default_factory=list)
    max_age_seconds: Optional[int] = 60


class StockChartRequest(BaseModel):
    """종목 차트 요청 모델"""

    ticker: str
    period: str = "6mo"

    @field_validator('period')
    @classmethod
    def validate_period(cls, v):
        """기간 검증"""
        valid_periods = ["1mo", "3mo", "6mo", "1y"]
        if v not in valid_periods:
            raise ValueError(f"Invalid period. Must be one of: {valid_periods}")
        return v


class SignalListRequest(BaseModel):
    """시그널 목록 요청 모델"""

    limit: int = Field(default=20, ge=1, le=100)
    status: Optional[str] = None
    min_score: Optional[float] = Field(default=None, ge=0, le=100)


class StockDetailResponse(BaseModel):
    """종목 상세 응답 모델"""

    ticker: str
    name: str
    market: str
    sector: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    updated_at: Optional[datetime] = None


class ChartPoint(BaseModel):
    """차트 데이터 포인트 모델"""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockChartResponse(BaseModel):
    """종목 차트 응답 모델"""

    ticker: str
    period: str
    data: List[ChartPoint]
    total_points: int


class FlowDataPoint(BaseModel):
    """수급 데이터 포인트 모델"""

    date: date
    foreign_net: int  # 외국인 순매수 (주)
    inst_net: int  # 기관 순매수 (주)
    foreign_net_amount: Optional[int] = None  # 외국인 순매수 금액 (원)
    inst_net_amount: Optional[int] = None  # 기관 순매수 금액 (원)
    supply_demand_score: Optional[float] = None  # 수급 점수


class StockFlowResponse(BaseModel):
    """종목 수급 데이터 응답 모델"""

    ticker: str
    period_days: int
    data: List[FlowDataPoint]
    smartmoney_score: float  # SmartMoney 점수 (0-100)
    total_points: int


# ============================================================================
# Signal History Models
# ============================================================================


class SignalHistoryItem(BaseModel):
    """시그널 히스토리 아이템 모델"""

    model_config = {"from_attributes": True}  # Pydantic v2: ORM 모드에서 모델 변환 허용

    id: int
    ticker: str
    signal_type: str  # VCP or JONGGA_V2
    signal_date: date
    status: str  # OPEN or CLOSED
    score: Optional[float] = None
    grade: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    return_pct: Optional[float] = None  # 수익률 (%)
    exit_reason: Optional[str] = None


class SignalHistoryResponse(BaseModel):
    """종목 시그널 히스토리 응답 모델"""

    ticker: str
    total_signals: int
    open_signals: int
    closed_signals: int
    avg_return_pct: Optional[float] = None  # 평균 수익률 (%)
    win_rate: Optional[float] = None  # 승률 (%)
    signals: List[SignalHistoryItem]


# ============================================================================
# Backtest Result Models
# ============================================================================


class BacktestResultItem(BaseModel):
    """백테스트 결과 아이템 모델"""

    model_config = {"from_attributes": True}  # Pydantic v2: ORM 모드에서 모델 변환 허용

    id: int
    config_name: str  # 백테스트 설정명
    backtest_date: date  # 백테스트 기준 날짜
    total_trades: int  # 총 거래 횟수
    winning_trades: int  # 수익 거래 수
    losing_trades: int  # 손실 거래 수
    win_rate: Optional[float] = None  # 승률 (%)
    total_return_pct: float  # 총 수익률 (%)
    max_drawdown_pct: Optional[float] = None  # 최대 낙폭 (%)
    sharpe_ratio: Optional[float] = None  # 샤프 비율
    avg_return_per_trade: Optional[float] = None  # 평균 수익률/거래 (%)
    profit_factor: Optional[float] = None  # 프로핏 팩터
    created_at: datetime  # 생성 일시


class BacktestSummaryResponse(BaseModel):
    """백테스트 요약 응답 모델"""

    total_backtests: int  # 총 백테스트 수
    avg_return_pct: float  # 평균 수익률 (%)
    avg_win_rate: float  # 평균 승률 (%)
    best_return_pct: float  # 최고 수익률 (%)
    worst_return_pct: float  # 최저 수익률 (%)
    avg_sharpe_ratio: float  # 평균 샤프 비율
    avg_max_drawdown_pct: float  # 평균 최대 낙폭 (%)


class BacktestStatsItem(BaseModel):
    """백테스트 전략별 통계 아이템"""

    strategy: str  # vcp, jongga_v2
    status: str  # OK, Accumulating, No Data
    count: int  # 총 백테스트 수
    win_rate: Optional[float] = None  # 승률 (%)
    avg_return: Optional[float] = None  # 평균 수익률 (%)
    profit_factor: Optional[float] = None  # 프로핏 팩터
    message: Optional[str] = None  # 상태 메시지


class BacktestKPIResponse(BaseModel):
    """백테스트 KPI 응답 모델 (대시보드용)"""

    vcp: BacktestStatsItem  # VCP 전략 통계
    closing_bet: BacktestStatsItem  # 종가베팅 V2 전략 통계


class BacktestListResponse(BaseModel):
    """백테스트 목록 응답 모델"""

    results: List[BacktestResultItem]
    total: int


# ============================================================================
# AI Analysis Models
# ============================================================================


class AIAnalysisItem(BaseModel):
    """AI 분석 아이템 모델"""

    id: int
    ticker: str
    analysis_date: str  # ISO format date
    sentiment: str  # positive, negative, neutral
    score: float  # -1.0 ~ 1.0
    summary: str
    keywords: List[str]
    recommendation: str  # BUY, SELL, HOLD, OVERWEIGHT, UNDERWEIGHT


class AIAnalysisResponse(BaseModel):
    """AI 종목 분석 응답 모델"""

    ticker: str
    name: str
    analysis_date: Optional[str] = None
    sentiment: Optional[str] = None
    score: Optional[float] = None
    summary: Optional[str] = None
    keywords: List[str] = []
    recommendation: Optional[str] = None


class AIAnalysisListResponse(BaseModel):
    """AI 분석 목록 응답 모델"""

    analyses: List[AIAnalysisItem]
    total: int
    analysis_date: Optional[str] = None


class AIHistoryDatesResponse(BaseModel):
    """AI 분석 가능 날짜 응답 모델"""

    dates: List[str]  # ISO format dates
    total: int


# ============================================================================
# System Management Models
# ============================================================================


class DataStatusItem(BaseModel):
    """개별 데이터 상태 모델"""

    name: str  # prices, signals, flows, etc.
    status: str  # OK, ERROR, STALE
    last_update: Optional[str] = None  # ISO format timestamp
    record_count: Optional[int] = None
    error_message: Optional[str] = None


class ServiceStatusItem(BaseModel):
    """개별 서비스 상태 모델"""

    name: str  # api_gateway, vcp_scanner, signal_engine, etc.
    status: str  # up, down, degraded
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class DataStatusResponse(BaseModel):
    """데이터 상태 응답 모델"""

    total_stocks: int
    updated_stocks: int
    last_update: Optional[str] = None  # ISO format timestamp
    data_files: Dict[str, str]  # {"prices": "OK", "signals": "OK"}
    details: List[DataStatusItem] = []


class SystemHealthResponse(BaseModel):
    """시스템 헬스 체크 응답 모델"""

    status: str  # healthy, degraded, unhealthy
    services: Dict[str, str]  # {"api_gateway": "up", "vcp_scanner": "up"}
    timestamp: str  # ISO format timestamp
    uptime_seconds: Optional[float] = None
    database_status: str
    redis_status: str
    celery_status: Optional[str] = None


# ============================================================================
# Trigger Management Models
# ============================================================================


class VCPSignalItem(BaseModel):
    """VCP 시그널 아이템 모델"""

    ticker: str
    name: str
    signal_type: str  # VCP
    score: float
    grade: str  # S, A, B, C
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    detected_at: Optional[str] = None  # ISO format timestamp


class VCPScanResponse(BaseModel):
    """VCP 스캔 응답 모델"""

    status: str  # started, completed, error
    scanned_count: int
    found_signals: int
    started_at: str  # ISO format timestamp
    completed_at: Optional[str] = None  # ISO format timestamp
    error_message: Optional[str] = None
    signals: List[VCPSignalItem] = []


class SignalGenerationResponse(BaseModel):
    """시그널 생성 응답 모델"""

    status: str  # started, completed, error
    generated_count: int
    started_at: str  # ISO format timestamp
    completed_at: Optional[str] = None  # ISO format timestamp
    error_message: Optional[str] = None


class ScanStatusResponse(BaseModel):
    """스캔 상태 응답 모델"""

    vcp_scan_status: str  # idle, running, completed, error
    signal_generation_status: str  # idle, running, completed, error
    last_vcp_scan: Optional[str] = None  # ISO format timestamp
    last_signal_generation: Optional[str] = None  # ISO format timestamp
    current_operation: Optional[str] = None  # 현재 진행 중인 작업
    progress_percentage: Optional[float] = None  # 진행률 (0-100)


# ============================================================================
# News Models (Phase 6)
# ============================================================================


class NewsItem(BaseModel):
    """뉴스 항목 모델 (Phase 6: GREEN)"""

    title: str  # 뉴스 제목
    url: str  # 뉴스 기사 URL
    source: Optional[str] = None  # 뉴스 소스 (네이버, 연합뉴스, etc.)
    published_at: Optional[str] = None  # ISO format timestamp


class NewsListResponse(BaseModel):
    """뉴스 목록 응답 모델 (Phase 6: GREEN)"""

    ticker: Optional[str] = None  # 종목 코드
    news: List[NewsItem]  # 뉴스 목록
    total: int  # 전체 뉴스 수
    page: int = 1  # 현재 페이지
    limit: int = 20  # 페이지당 뉴스 수
    has_more: bool = False  # 더 많은 뉴스 존재 여부


# ============================================================================
# VCP Signal Models (Phase: 활성 VCP 시그널 상위 10개)
# ============================================================================


class VCPSignalItem(BaseModel):
    """VCP 시그널 아이템 모델"""

    model_config = {"from_attributes": True}  # Pydantic v2: ORM 모드에서 모델 변환 허용

    ticker: str  # 종목 코드
    name: str  # 종목명
    market: str  # KOSPI/KOSDAQ
    signal_type: str  # VCP
    score: float  # VCP 점수 (0-100)
    grade: str  # S/A/B/C
    signal_date: str  # ISO format date
    entry_price: Optional[float] = None  # 진입가
    target_price: Optional[float] = None  # 목표가
    current_price: Optional[float] = None  # 현재가
    contraction_ratio: Optional[float] = None  # 수축률 (0-1)
    foreign_5d: int = 0  # 외국인 5일 순매수 (주)
    inst_5d: int = 0  # 기관 5일 순매수 (주)
    created_at: str  # 생성 일시 (ISO format)


class VCPSignalsResponse(BaseModel):
    """VCP 시그널 목록 응답 모델"""

    signals: List[VCPSignalItem]  # 시그널 목록 (상위 N개)
    count: int  # 시그널 수
    generated_at: Optional[str] = None  # 생성 일시 (ISO format)


class SignalsListResponse(BaseModel):
    """전체 시그널 목록 응답 모델 (VCP + 종가베팅 V2)"""

    signals: List[VCPSignalItem]  # 시그널 목록
    count: int  # 전체 시그널 수
    vcp_count: int = 0  # VCP 시그널 수
    jongga_count: int = 0  # 종가베팅 시그널 수
    generated_at: Optional[str] = None  # 생성 일시


# ============================================================================
# Stock Sync Models (Phase: 전체 종목 동기화)
# ============================================================================


class StockSyncResponse(BaseModel):
    """종목 동기화 응답 모델"""

    status: str  # started, completed, error
    synced: int  # 동기화된 종목 수
    kospi_count: int = 0  # KOSPI 종목 수
    kosdaq_count: int = 0  # KOSDAQ 종목 수
    konex_count: int = 0  # KONEX 종목 수
    started_at: str  # ISO format timestamp
    completed_at: Optional[str] = None  # ISO format timestamp
    error_message: Optional[str] = None


# ============================================================================
# Realtime Price Models
# ============================================================================


class RealtimePriceResponse(BaseModel):
    """실시간 가격 응답 모델"""

    ticker: str  # 종목 코드
    name: Optional[str] = None  # 종목명
    price: float  # 현재가
    change: float  # 전일대비
    change_percent: float  # 전일대비 등락률 (%)
    volume: int  # 거래량
    bid_price: Optional[float] = None  # 매수호가
    ask_price: Optional[float] = None  # 매도호가
    timestamp: str  # 응답 시간 (ISO format)
    source: str  # 데이터 소스 (cache, kiwoom, database)
