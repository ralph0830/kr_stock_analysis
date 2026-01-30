"""
News API Routes (Phase 6: GREEN)
뉴스 조회 API 엔드포인트 구현
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.repositories.ai_analysis_repository import AIAnalysisRepository
from services.api_gateway.schemas import NewsItem, NewsListResponse

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/api/kr/news",
    tags=["news"],
)


def _convert_news_urls_to_items(news_urls: Optional[List[dict]]) -> List[NewsItem]:
    """
    news_urls 딕셔너리 리스트를 NewsItem 리스트로 변환

    Args:
        news_urls: [{"title": "...", "url": "..."}, ...] 형식의 리스트

    Returns:
        NewsItem 리스트
    """
    if not news_urls:
        return []

    items = []
    for item in news_urls:
        # URL에서 소스 추출 (간단 구현)
        url = item.get("url", "")
        source = "Unknown"

        if "naver" in url:
            source = "네이버뉴스"
        elif "yonhap" in url:
            source = "연합뉴스"
        elif "etoday" in url:
            source = "이투데이"
        elif "hankyung" in url:
            source = "한국경제"

        items.append(NewsItem(
            title=item.get("title", ""),
            url=url,
            source=source,
            published_at=item.get("published_at"),  # ISO format string
        ))

    return items


@router.get(
    "/latest",
    response_model=NewsListResponse,
    responses={
        200: {
            "description": "최신 뉴스 목록 반환 성공",
        },
    },
)
async def get_latest_news(
    limit: int = Query(default=20, ge=1, le=100, description="반환할 최대 뉴스 수"),
    days: int = Query(default=7, ge=1, le=30, description="조회 기간 (일수)"),
    db: Session = Depends(get_db_session),
):
    """
    최신 뉴스 조회 (Phase 6: GREEN)

    ## 설명
    전체 종목의 최신 뉴스를 반환합니다.

    ## Parameters
    - **limit**: 반환할 최대 뉴스 수 (기본 20, 최대 100)
    - **days**: 조회 기간 (일수, 기본 7일)

    ## 반환 데이터
    - **news**: 뉴스 항목 리스트 (title, url, source, published_at)
    - **total**: 전체 뉴스 수

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/news/latest?limit=50&days=7"
    ```
    """
    try:
        # Repository 인스턴스 생성
        repo = AIAnalysisRepository(db)

        # 최근 N일 내 분석 조회
        from datetime import date, timedelta
        cutoff_date = date.today() - timedelta(days=days)

        # 모든 최신 분석 조회 (간단 구현: 전체 종목 최신 분석)
        # TODO: 성능 최적화를 위해 캐시 또는 별도 테이블 고려
        all_news_items = []

        # 주요 종목 리스트 (KOSPI 대종목)
        major_tickers = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "005380",  # 현대차
            "066570",  # LG전자
            "028260",  # 삼성물산
            "105560",  # KB금융
            "035720",  # 카카오
        ]

        for ticker in major_tickers:
            try:
                latest_analysis = repo.get_latest_analysis(ticker)
                if latest_analysis and latest_analysis.analysis_date >= cutoff_date:
                    items = _convert_news_urls_to_items(latest_analysis.news_urls)
                    # 종목 정보를 추가하기 위해 ticker를 함께 저장
                    for item in items:
                        # URL 쿼리 파라미터로 ticker 전달 (프론트엔드에서 활용)
                        if "?" in item.url:
                            item.url += f"&ref_ticker={ticker}"
                        else:
                            item.url += f"?ref_ticker={ticker}"
                    all_news_items.extend(items)
            except Exception as e:
                logger.warning(f"Failed to fetch news for {ticker}: {e}")
                continue

        # 날짜순 정렬 (최신순)
        # published_at이 있는 것优先
        all_news_items.sort(
            key=lambda x: x.published_at or "1970-01-01T00:00:00",
            reverse=True
        )

        # limit 적용
        paginated_news = all_news_items[:limit]

        return NewsListResponse(
            ticker=None,  # 전체 종목
            news=paginated_news,
            total=len(all_news_items),
            page=1,
            limit=limit,
            has_more=len(all_news_items) > limit,
        )

    except Exception as e:
        logger.error(f"Error fetching latest news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest news: {str(e)}"
        )


@router.get(
    "/{ticker}",
    response_model=NewsListResponse,
    responses={
        200: {
            "description": "뉴스 목록 반환 성공",
        },
        404: {
            "description": "종목 분석 데이터 없음",
        },
    },
)
async def get_news_by_ticker(
    ticker: str,
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    limit: int = Query(default=20, ge=1, le=100, description="페이지당 뉴스 수"),
    db: Session = Depends(get_db_session),
):
    """
    종목별 뉴스 조회 (Phase 6: GREEN)

    ## 설명
    특정 종목의 AI 분석에 포함된 뉴스 목록을 반환합니다.

    ## Parameters
    - **ticker**: 종목 코드 (6자리, 예: 005930)
    - **page**: 페이지 번호 (기본 1)
    - **limit**: 페이지당 뉴스 수 (기본 20, 최대 100)

    ## 반환 데이터
    - **news**: 뉴스 항목 리스트 (title, url, source, published_at)
    - **total**: 전체 뉴스 수
    - **page**: 현재 페이지
    - **limit**: 페이지당 뉴스 수

    ## 사용 예시
    ```bash
    curl "http://localhost:5111/api/kr/news/005930?page=1&limit=20"
    ```
    """
    try:
        # Repository 인스턴스 생성
        repo = AIAnalysisRepository(db)

        # 최신 분석 조회
        latest_analysis = repo.get_latest_analysis(ticker)

        if not latest_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for ticker: {ticker}"
            )

        # news_urls 변환
        news_items = _convert_news_urls_to_items(latest_analysis.news_urls)

        # 페이지네이션 적용
        total = len(news_items)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_news = news_items[start_idx:end_idx]

        return NewsListResponse(
            ticker=ticker,
            news=paginated_news,
            total=total,
            page=page,
            limit=limit,
            has_more=end_idx < total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch news: {str(e)}"
        )
