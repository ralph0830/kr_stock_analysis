"""
Ralph Stock - Database Models
SQLAlchemy 2.0 기반 ORM 모델 정의
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Date, Text, ForeignKey, Index, BigInteger, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database.session import Base


class Stock(Base):
    """종목 기본 정보"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)  # KOSPI / KOSDAQ
    sector = Column(String(50), nullable=True)
    market_cap = Column(BigInteger, nullable=True)  # 시가총액 (원)
    is_etf = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)  # 관리종목
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    daily_prices = relationship("DailyPrice", back_populates="stock", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="stock", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stock(ticker={self.ticker}, name={self.name}, market={self.market})>"


class Signal(Base):
    """VCP/종가베팅 시그널"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(6), ForeignKey("stocks.ticker"), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # VCP, JONGGA_V2
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # OPEN, CLOSED
    score = Column(Float, nullable=True)
    grade = Column(String(10), nullable=True)  # S, A, B, C

    # VCP 관련
    contraction_ratio = Column(Float, nullable=True)
    pivot_high = Column(Float, nullable=True)

    # 종가베팅 관련
    total_score = Column(Integer, nullable=True)
    news_score = Column(Integer, nullable=True)
    supply_score = Column(Integer, nullable=True)

    # 진입/청산 정보
    entry_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    exit_reason = Column(String(50), nullable=True)

    # 수급 정보 (진입 시점)
    foreign_net_5d = Column(Integer, default=0)
    inst_net_5d = Column(Integer, default=0)

    # 기관/외국인 추세
    foreign_trend = Column(String(20))
    inst_trend = Column(String(20))

    signal_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="signals")

    # Indexes
    __table_args__ = (
        Index("ix_signals_signal_date_status", "signal_date", "status"),
        Index("ix_signals_type_status", "signal_type", "status"),
    )

    def __repr__(self):
        return f"<Signal(id={self.id}, ticker={self.ticker}, type={self.signal_type}, status={self.status})>"


class DailyPrice(Base):
    """일봉 데이터 (TimescaleDB 하이퍼테이블)"""
    __tablename__ = "daily_prices"

    # Composite primary key for TimescaleDB: (ticker, date)
    ticker = Column(String(6), ForeignKey("stocks.ticker"), primary_key=True, nullable=False)
    date = Column(Date, primary_key=True, nullable=False)

    # OHLCV
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)

    # 수급 데이터 (외국인/기관)
    foreign_net_buy = Column(Integer, default=0)
    inst_net_buy = Column(Integer, default=0)
    retail_net_buy = Column(Integer, default=0)

    # 기관 상세
    foreign_net_buy_amount = Column(BigInteger, default=0)  # 금액 (원)
    inst_net_buy_amount = Column(BigInteger, default=0)

    # 거래대금
    trading_value = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="daily_prices")

    def __repr__(self):
        return f"<DailyPrice(ticker={self.ticker}, date={self.date}, close={self.close_price})>"


class InstitutionalFlow(Base):
    """기관/외국인 수급 데이터 (TimescaleDB 하이퍼테이블)"""
    __tablename__ = "institutional_flows"

    # Composite primary key for TimescaleDB: (ticker, date)
    ticker = Column(String(6), ForeignKey("stocks.ticker"), primary_key=True, nullable=False)
    date = Column(Date, primary_key=True, nullable=False)

    # 외국인
    foreign_net_buy = Column(Integer, default=0)
    foreign_consecutive_days = Column(Integer, default=0)
    foreign_trend = Column(String(20))  # buying, selling, neutral

    # 기관
    inst_net_buy = Column(Integer, default=0)
    inst_consecutive_days = Column(Integer, default=0)
    inst_trend = Column(String(20))

    # 집계 (5일/20일/60일)
    foreign_net_5d = Column(Integer, default=0)
    foreign_net_20d = Column(Integer, default=0)
    foreign_net_60d = Column(Integer, default=0)
    inst_net_5d = Column(Integer, default=0)
    inst_net_20d = Column(Integer, default=0)
    inst_net_60d = Column(Integer, default=0)

    # 수급 점수
    supply_demand_score = Column(Float, default=50.0)
    supply_demand_stage = Column(String(20))

    # 매집 신호
    is_double_buy = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<InstitutionalFlow(ticker={self.ticker}, date={self.date}, score={self.supply_demand_score})>"


class MarketStatus(Base):
    """시장 상태 (Market Gate)"""
    __tablename__ = "market_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, index=True)

    # 지수
    kospi = Column(Float, nullable=True)
    kospi_change_pct = Column(Float, default=0.0)
    kosdaq = Column(Float, nullable=True)
    kosdaq_change_pct = Column(Float, default=0.0)

    # 환율
    usd_krw = Column(Float, nullable=True)
    usd_krw_change_pct = Column(Float, default=0.0)

    # Market Gate
    gate = Column(String(10))  # GREEN, YELLOW, RED
    gate_score = Column(Integer, default=50)
    gate_reasons = Column(Text, nullable=True)

    # 섹터 점수 (JSON으로 저장)
    sector_scores = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MarketStatus(date={self.date}, gate={self.gate}, score={self.gate_score})>"


class BacktestResult(Base):
    """백테스트 결과"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(String(100), nullable=False, index=True)  # 백테스트 설정명 (예: vcp_conservative)
    backtest_date = Column(Date, nullable=False, index=True)  # 백테스트 기준 날짜

    # 거래 통계
    total_trades = Column(Integer, nullable=False, default=0)  # 총 거래 횟수
    winning_trades = Column(Integer, nullable=False, default=0)  # 수익 거래 수
    losing_trades = Column(Integer, nullable=False, default=0)  # 손실 거래 수

    # 수익률 지표
    win_rate = Column(Float, nullable=True)  # 승률 (%)
    total_return_pct = Column(Float, nullable=False)  # 총 수익률 (%)
    max_drawdown_pct = Column(Float, nullable=True)  # 최대 낙폭 (%)
    sharpe_ratio = Column(Float, nullable=True)  # 샤프 비율
    avg_return_per_trade = Column(Float, nullable=True)  # 평균 수익률/거래 (%)
    profit_factor = Column(Float, nullable=True)  # 프로핏 팩터 (총수익/총손실)

    # 추가 메타데이터
    extra_metadata = Column(JSON, nullable=True)  # 추가 정보 (JSON)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index("ix_backtest_config_date", "config_name", "backtest_date"),
        Index("ix_backtest_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<BacktestResult(id={self.id}, config={self.config_name}, return={self.total_return_pct}%)"


class AIAnalysis(Base):
    """AI 종목 분석 결과"""
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(6), ForeignKey("stocks.ticker"), nullable=False, index=True)
    analysis_date = Column(Date, nullable=False, index=True)

    # 감성 분석 결과
    sentiment = Column(String(20), nullable=False)  # positive, negative, neutral
    score = Column(Float, nullable=False)  # -1.0 ~ 1.0
    confidence = Column(Float, default=0.5)  # 0 ~ 1

    # 분석 내용
    summary = Column(Text, nullable=True)  # 요약
    keywords = Column(JSON, nullable=True)  # 키워드 리스트
    recommendation = Column(String(20), nullable=True)  # BUY, SELL, HOLD

    # 뉴스 출처 (참고한 뉴스 링크)
    news_urls = Column(JSON, nullable=True, default=list)  # [{"title": "...", "url": "..."}]

    # 추가 정보
    news_count = Column(Integer, default=0)  # 분석한 뉴스 수
    model_version = Column(String(50), default="v1.0")  # 모델 버전

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_ai_analysis_ticker_date", "ticker", "analysis_date"),
        Index("ix_ai_analysis_date", "analysis_date"),
    )

    def __repr__(self):
        return f"<AIAnalysis(id={self.id}, ticker={self.ticker}, sentiment={self.sentiment})>"
