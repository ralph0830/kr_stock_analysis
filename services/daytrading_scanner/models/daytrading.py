"""
Daytrading Scanner Pydantic Models
요청/응답 모델 정의
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


# =============================================================================
# Request Models
# =============================================================================

class ScanRequest(BaseModel):
    """스캔 요청 모델"""
    market: str = Field(default="KOSPI", description="시장 (KOSPI/KOSDAQ)")
    limit: int = Field(default=50, ge=1, le=100, description="반환 개수 (1-100)")

    @field_validator('market')
    @classmethod
    def validate_market(cls, v: str) -> str:
        """시장 값 검증"""
        valid_markets = ["KOSPI", "KOSDAQ", "ALL"]
        if v.upper() not in valid_markets:
            raise ValueError(f"market must be one of {valid_markets}")
        return v.upper()


# =============================================================================
# Response Models
# =============================================================================

class CandidateData(BaseModel):
    """후보 종목 데이터 모델"""
    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    price: int = Field(..., description="현재가")
    change_rate: float = Field(..., description="등락률 (%)")
    volume: int = Field(..., description="거래량")
    avg_volume: int = Field(..., description="평균 거래량")
    volume_ratio: float = Field(..., description="거래량 비율 (현재/평균)")


class CandidateDataWithScore(CandidateData):
    """점수 포함 후보 종목 데이터"""
    score: int = Field(default=0, description="총 점수")
    grade: str = Field(default="C", description="등급")
    entry_price: Optional[int] = Field(None, description="진입가")
    target_price: Optional[int] = Field(None, description="목표가")
    stop_loss: Optional[int] = Field(None, description="손절가")


class ScanResponseData(BaseModel):
    """스캔 응답 데이터 모델"""
    candidates: List[CandidateDataWithScore]
    scan_time: str
    count: int


class ScanResponse(BaseModel):
    """스캔 응답 모델"""
    success: bool
    data: ScanResponseData


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    service: str
    version: str
    timestamp: Optional[str] = None


# =============================================================================
# Signal Models (Phase 3에서 확장)
# =============================================================================

class DaytradingCheck(BaseModel):
    """단타 체크리스트 항목"""
    name: str
    status: str  # 'passed', 'partial', 'failed'
    points: int


class DaytradingStock(BaseModel):
    """단타 분석 종목 모델"""
    ticker: str
    name: str
    price: int
    change_rate: float
    volume: int
    avg_volume: int
    volume_ratio: float
    score: int
    grade: str  # 'S', 'A', 'B', 'C'
    checks: List[DaytradingCheck]
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None


class DaytradingSignal(BaseModel):
    """단타 매수 신호 모델"""
    ticker: str
    name: str
    market: str = "KOSPI"  # 시장 정보
    score: int  # 총 점수 (테스트와 일치)
    grade: str = "C"  # 등급
    checks: List[DaytradingCheck] = []  # 체크리스트
    signal_type: str = "WATCH"  # 'STRONG_BUY', 'BUY', 'WATCH'
    current_price: Optional[int] = None  # 현재가 (실시간 가격 연동용)
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None
    reasons: List[str] = []


class SignalsResponseData(BaseModel):
    """신호 응답 데이터 모델"""
    signals: List[DaytradingSignal]
    count: int
    generated_at: str  # 생성 시간 (테스트와 일치)


class SignalsResponse(BaseModel):
    """신호 응답 모델"""
    success: bool
    data: SignalsResponseData


class AnalyzeRequest(BaseModel):
    """분석 요청 모델"""
    tickers: List[str] = Field(..., min_length=1, description="종목 코드 리스트")


class AnalyzeCheck(BaseModel):
    """분석 체크리스트 항목"""
    name: str
    status: str
    points: int


class AnalyzeResult(BaseModel):
    """분석 결과 모델"""
    ticker: str
    name: str
    score: int
    grade: str
    checks: List[AnalyzeCheck]
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None


class AnalyzeResponseData(BaseModel):
    """분석 응답 데이터 모델"""
    results: List[AnalyzeResult]
    count: int
    analyzed_at: str


class AnalyzeResponse(BaseModel):
    """분석 응답 모델"""
    success: bool
    data: AnalyzeResponseData
