"""
KR Stock - Database Models
SQLAlchemy 2.0 기반 ORM 모델 정의
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Date, Numeric, Text, ForeignKey, Index, BigInteger, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, date

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(6), ForeignKey("stocks.ticker"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

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

    # Indexes (TimescaleDB에서 자동으로 시간에 따른 파티셔닝)
    __table_args__ = (
        Index("ix_daily_prices_ticker_date", "ticker", "date"),
        UniqueConstraint("ticker", "date", name="uq_daily_prices_ticker_date"),
    )

    def __repr__(self):
        return f"<DailyPrice(ticker={self.ticker}, date={self.date}, close={self.close_price})>"


class InstitutionalFlow(Base):
    """기관/외국인 수급 데이터 (TimescaleDB 하이퍼테이블)"""
    __tablename__ = "institutional_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(6), ForeignKey("stocks.ticker"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

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

    # Indexes
    __table_args__ = (
        Index("ix_institutional_flows_ticker_date", "ticker", "date"),
        UniqueConstraint("ticker", "date", name="uq_institutional_flows_ticker_date"),
    )

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
