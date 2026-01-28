"""
AI Routes
AI 종목 분석 API
"""

from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.database.models import Stock, AIAnalysis
from src.repositories.stock_repository import StockRepository
from src.repositories.ai_analysis_repository import AIAnalysisRepository
from src.analysis.sentiment_analyzer import SentimentAnalyzer
from services.api_gateway.schemas import (
    AIAnalysisResponse,
    AIAnalysisListResponse,
    AIHistoryDatesResponse,
    AIAnalysisItem,
)


router = APIRouter(prefix="/api/kr", tags=["ai"])


def get_recommendation(score: float, sentiment: str) -> str:
    """
    감성 점수 → 매수 추천 변환

    Args:
        score: 감성 점수 (-1.0 ~ 1.0)
        sentiment: 감성 라벨

    Returns:
        매수 추천 (BUY/SELL/HOLD/OVERWEIGHT/UNDERWEIGHT)
    """
    if sentiment == "positive":
        if score >= 0.5:
            return "BUY"
        else:
            return "OVERWEIGHT"
    elif sentiment == "negative":
        if score <= -0.5:
            return "SELL"
        else:
            return "UNDERWEIGHT"
    else:
        return "HOLD"


@router.get("/ai-summary/{ticker}", response_model=AIAnalysisResponse)
def get_ai_summary(
    ticker: str,
    session: Session = Depends(get_db_session),
) -> AIAnalysisResponse:
    """
    종목 AI 요약 조회

    Args:
        ticker: 종목 코드
        session: DB 세션

    Returns:
        AI 분석 요약

    Raises:
        HTTPException: 종목을 찾을 수 없음 (404)
    """
    # 종목 존재 확인
    stock_repo = StockRepository(session)
    stock = stock_repo.get_by_ticker(ticker)

    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    # 최신 AI 분석 조회
    ai_repo = AIAnalysisRepository(session)
    analysis = ai_repo.get_latest_analysis(ticker)

    if not analysis:
        # 분석이 없으면 빈 결과 반환
        return AIAnalysisResponse(
            ticker=ticker,
            name=stock.name,
            analysis_date=None,
            sentiment=None,
            score=None,
            summary=None,
            keywords=[],
            recommendation=None,
        )

    return AIAnalysisResponse(
        ticker=ticker,
        name=stock.name,
        analysis_date=analysis.analysis_date.isoformat(),
        sentiment=analysis.sentiment,
        score=analysis.score,
        summary=analysis.summary,
        keywords=analysis.keywords or [],
        recommendation=analysis.recommendation,
    )


@router.get("/ai-analysis", response_model=AIAnalysisListResponse)
def get_ai_analysis(
    analysis_date: Optional[str] = Query(
        default=None, description="분석 날짜 (YYYY-MM-DD)"
    ),
    limit: int = Query(default=50, ge=1, le=100, description="최대 반환 수"),
    session: Session = Depends(get_db_session),
) -> AIAnalysisListResponse:
    """
    전체 AI 분석 조회

    Args:
        analysis_date: 분석 날짜 필터
        limit: 최대 반환 수
        session: DB 세션

    Returns:
        AI 분석 목록
    """
    ai_repo = AIAnalysisRepository(session)

    target_date = None
    if analysis_date:
        try:
            target_date = datetime.strptime(analysis_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
            )

    analyses = ai_repo.get_all_analyses(analysis_date=target_date, limit=limit)

    items = [
        AIAnalysisItem(
            id=a.id,
            ticker=a.ticker,
            analysis_date=a.analysis_date.isoformat(),
            sentiment=a.sentiment,
            score=a.score,
            summary=a.summary,
            keywords=a.keywords or [],
            recommendation=a.recommendation,
        )
        for a in analyses
    ]

    return AIAnalysisListResponse(
        analyses=items,
        total=len(items),
        analysis_date=target_date.isoformat() if target_date else None,
    )


@router.get("/ai-history-dates", response_model=AIHistoryDatesResponse)
def get_ai_history_dates(
    limit: int = Query(default=30, ge=1, le=365, description="최대 반환 수"),
    session: Session = Depends(get_db_session),
) -> AIHistoryDatesResponse:
    """
    분석 가능 날짜 목록 조회

    Args:
        limit: 최대 반환 수
        session: DB 세션

    Returns:
        분석 가능 날짜 목록
    """
    ai_repo = AIAnalysisRepository(session)
    dates = ai_repo.get_available_dates(limit=limit)

    return AIHistoryDatesResponse(
        dates=[d.isoformat() for d in dates],
        total=len(dates),
    )


@router.get("/ai-history/{date_str}", response_model=AIAnalysisListResponse)
def get_ai_history_by_date(
    date_str: str,
    session: Session = Depends(get_db_session),
) -> AIAnalysisListResponse:
    """
    특정 날짜 AI 분석 조회

    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)
        session: DB 세션

    Returns:
        해당 날짜의 AI 분석 목록

    Raises:
        HTTPException: 잘못된 날짜 형식
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )

    ai_repo = AIAnalysisRepository(session)
    analyses = ai_repo.get_by_date(target_date)

    items = [
        AIAnalysisItem(
            id=a.id,
            ticker=a.ticker,
            analysis_date=a.analysis_date.isoformat(),
            sentiment=a.sentiment,
            score=a.score,
            summary=a.summary,
            keywords=a.keywords or [],
            recommendation=a.recommendation,
        )
        for a in analyses
    ]

    return AIAnalysisListResponse(
        analyses=items,
        total=len(items),
        analysis_date=date_str,
    )


@router.post("/ai-analyze/{ticker}")
def trigger_ai_analysis(
    ticker: str,
    session: Session = Depends(get_db_session),
) -> dict:
    """
    AI 분석 트리거

    Args:
        ticker: 종목 코드
        session: DB 세션

    Returns:
        분석 트리거 결과

    Raises:
        HTTPException: 종목을 찾을 수 없음
    """
    # 종목 존재 확인
    stock_repo = StockRepository(session)
    stock = stock_repo.get_by_ticker(ticker)

    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    # 분석 수행 (비동기 처리 가능)
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(
        title=f"{stock.name}({ticker}) 뉴스 분석",
        content=f"{stock.name} 최근 뉴스 감성 분석"
    )

    # 결과 저장
    ai_repo = AIAnalysisRepository(session)
    recommendation = get_recommendation(result.score, result.sentiment.value)

    ai_repo.save_analysis(
        ticker=ticker,
        analysis_date=date.today(),
        sentiment=result.sentiment.value,
        score=result.score,
        summary=result.summary,
        keywords=result.keywords,
        recommendation=recommendation,
        confidence=result.confidence,
        news_count=0,
    )

    return {
        "status": "completed",
        "ticker": ticker,
        "sentiment": result.sentiment.value,
        "score": result.score,
        "recommendation": recommendation,
    }
