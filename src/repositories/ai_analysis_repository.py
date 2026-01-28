"""
AI Analysis Repository
AI 종목 분석 결과 접근 계층
"""

from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from src.repositories.base import BaseRepository
from src.database.models import AIAnalysis


class AIAnalysisRepository(BaseRepository[AIAnalysis]):
    """
    AIAnalysis Repository
    AI 분석 결과 CRUD 작업 처리
    """

    def __init__(self, session: Session):
        super().__init__(AIAnalysis, session)

    def get_latest_analysis(self, ticker: str) -> Optional[AIAnalysis]:
        """
        종목 최신 AI 분석 조회

        Args:
            ticker: 종목 코드

        Returns:
            최신 AIAnalysis 또는 None
        """
        query = select(AIAnalysis).where(
            AIAnalysis.ticker == ticker
        ).order_by(desc(AIAnalysis.analysis_date)).limit(1)

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_all_analyses(
        self,
        analysis_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[AIAnalysis]:
        """
        전체 AI 분석 조회

        Args:
            analysis_date: 분석 날짜 필터 (None이면 전체)
            limit: 최대 반환 수

        Returns:
            AIAnalysis 리스트
        """
        query = select(AIAnalysis)

        if analysis_date:
            query = query.where(AIAnalysis.analysis_date == analysis_date)

        query = query.order_by(
            desc(AIAnalysis.score),
            AIAnalysis.ticker
        ).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_by_ticker(
        self,
        ticker: str,
        limit: int = 10,
    ) -> List[AIAnalysis]:
        """
        종목별 AI 분석 히스토리 조회

        Args:
            ticker: 종목 코드
            limit: 최대 반환 수

        Returns:
            AIAnalysis 리스트 (날짜 내림차순)
        """
        query = select(AIAnalysis).where(
            AIAnalysis.ticker == ticker
        ).order_by(desc(AIAnalysis.analysis_date)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_by_date(
        self,
        analysis_date: date,
    ) -> List[AIAnalysis]:
        """
        특정 날짜 AI 분석 조회

        Args:
            analysis_date: 분석 날짜

        Returns:
            AIAnalysis 리스트
        """
        query = select(AIAnalysis).where(
            AIAnalysis.analysis_date == analysis_date
        ).order_by(desc(AIAnalysis.score))

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_available_dates(self, limit: int = 30) -> List[date]:
        """
        분석 가능 날짜 목록 조회

        Args:
            limit: 최대 반환 수

        Returns:
            분석 날짜 리스트 (내림차순)
        """
        query = select(AIAnalysis.analysis_date).distinct().order_by(
            desc(AIAnalysis.analysis_date)
        ).limit(limit)

        result = self.session.execute(query)
        return [row[0] for row in result.all()]

    def save_analysis(
        self,
        ticker: str,
        analysis_date: date,
        sentiment: str,
        score: float,
        summary: str,
        keywords: List[str],
        recommendation: str,
        confidence: float = 0.5,
        news_count: int = 0,
    ) -> AIAnalysis:
        """
        AI 분석 결과 저장

        Args:
            ticker: 종목 코드
            analysis_date: 분석 날짜
            sentiment: 감성 (positive/negative/neutral)
            score: 감성 점수 (-1.0 ~ 1.0)
            summary: 요약
            keywords: 키워드 리스트
            recommendation: 매수 추천 (BUY/SELL/HOLD)
            confidence: 신뢰도
            news_count: 뉴스 수

        Returns:
            생성된 AIAnalysis
        """
        analysis = AIAnalysis(
            ticker=ticker,
            analysis_date=analysis_date,
            sentiment=sentiment,
            score=score,
            confidence=confidence,
            summary=summary,
            keywords=keywords,
            recommendation=recommendation,
            news_count=news_count,
        )
        self.session.add(analysis)
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def get_top_positive(
        self,
        analysis_date: date,
        limit: int = 10,
    ) -> List[AIAnalysis]:
        """
        상위 긍정 종목 조회

        Args:
            analysis_date: 분석 날짜
            limit: 최대 반환 수

        Returns:
            긍정 감성 AIAnalysis 리스트
        """
        query = select(AIAnalysis).where(
            and_(
                AIAnalysis.analysis_date == analysis_date,
                AIAnalysis.sentiment == "positive",
            )
        ).order_by(desc(AIAnalysis.score)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_top_negative(
        self,
        analysis_date: date,
        limit: int = 10,
    ) -> List[AIAnalysis]:
        """
        상위 부정 종목 조회

        Args:
            analysis_date: 분석 날짜
            limit: 최대 반환 수

        Returns:
            부정 감성 AIAnalysis 리스트
        """
        query = select(AIAnalysis).where(
            and_(
                AIAnalysis.analysis_date == analysis_date,
                AIAnalysis.sentiment == "negative",
            )
        ).order_by(AIAnalysis.score).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())
