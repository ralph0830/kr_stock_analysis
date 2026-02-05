"""
DaytradingSignal Database Model
단타 매수 신호 모델
"""

from sqlalchemy import Column, String, Integer, Date, DateTime, JSON, Index
from datetime import datetime

from src.database.session import Base


class DaytradingSignal(Base):
    """단타 매수 신호 모델"""
    __tablename__ = "daytrading_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(6), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)  # KOSPI / KOSDAQ

    # 점수 정보
    score = Column(Integer, nullable=False)  # 총 점수 (0-105), 메인 대시보드와 통일
    grade = Column(String(10), nullable=False)  # S, A, B, C

    # 7개 체크리스트 개별 점수
    volume_score = Column(Integer, default=0)  # 거래량 폭증
    momentum_score = Column(Integer, default=0)  # 모멘텀 돌파
    box_score = Column(Integer, default=0)  # 박스권 탈출
    ma5_score = Column(Integer, default=0)  # 5일선 위
    institution_score = Column(Integer, default=0)  # 기관 매수
    oversold_score = Column(Integer, default=0)  # 낙폭 과대
    sector_score = Column(Integer, default=0)  # 섹터 모멘텀

    # 체크리스트 상세 (JSON)
    checks = Column(JSON, nullable=True)  # [{"name": "...", "status": "passed", "points": 15}]

    # 매매 기준가
    entry_price = Column(Integer, nullable=True)  # 진입가
    target_price = Column(Integer, nullable=True)  # 목표가
    stop_loss = Column(Integer, nullable=True)  # 손절가

    # 상태 정보
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # OPEN, CLOSED
    signal_date = Column(Date, nullable=False, index=True)

    # 시간 정보
    entry_time = Column(DateTime, nullable=True)  # 진입 시간
    exit_time = Column(DateTime, nullable=True)  # 청산 시간
    exit_reason = Column(String(50), nullable=True)  # 청산 사유

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_daytrading_signals_date_status", "signal_date", "status"),
        Index("ix_daytrading_signals_score", "score"),
        Index("ix_daytrading_signals_market", "market"),
    )

    def __repr__(self):
        return f"<DaytradingSignal(id={self.id}, ticker={self.ticker}, score={self.score}, grade={self.grade})>"
