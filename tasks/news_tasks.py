"""
Celery News Tasks
뉴스 수집 및 감성 분석 태스크

Phase 5: 자동 뉴스 수집 스케줄
- DB에 news_urls 자동 저장
- Celery Beat 스케줄러 연동
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Any

from celery import shared_task
from celery.schedules import crontab

from src.collectors.news_collector import NewsCollector
from src.analysis.sentiment_analyzer import SentimentAnalyzer
from src.analysis.news_scorer import NewsScorer
from src.database.session import get_db_session
from src.repositories.ai_analysis_repository import AIAnalysisRepository

logger = logging.getLogger(__name__)


@shared_task(name="news.collect", bind=True, max_retries=3)
def collect_news(ticker: str, days: int = 7, max_articles: int = 50) -> Dict[str, Any]:
    """
    종목 뉴스 수집 태스크

    Args:
        ticker: 종목코드
        days: 수집할 날짜 범위 (기본 7일)
        max_articles: 최대 기사 수 (기본 50건)

    Returns:
        수집 결과 딕셔너리
    """
    try:
        logger.info(f"📰 {ticker} 뉴스 수집 시작 (최근 {days}일, 최대 {max_articles}건)")

        # 뉴스 수집
        collector = NewsCollector()
        articles = collector.fetch_stock_news(
            ticker=ticker,
            days=days,
            max_articles=max_articles,
        )

        logger.info(f"✅ {ticker} 뉴스 {len(articles)}건 수집 완료")

        return {
            "ticker": ticker,
            "collected_count": len(articles),
            "success": True,
            "articles": [collector.to_dict(a) for a in articles[:5]],  # 최대 5건만 반환
        }

    except Exception as e:
        logger.error(f"❌ {ticker} 뉴스 수집 실패: {e}")
        # 재시도
        raise self.retry(exc=e, countdown=60)  # 1분 후 재시도


@shared_task(name="news.analyze_sentiment", bind=True, max_retries=3)
def analyze_sentiment(ticker: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    뉴스 감성 분석 태스크

    Args:
        ticker: 종목코드
        articles: 뉴스 기사 리스트

    Returns:
        분석 결과 딕셔너리
    """
    try:
        logger.info(f"🤖 {ticker} 뉴스 감성 분석 시작 ({len(articles)}건)")

        # 감성 분석기 초기화
        analyzer = SentimentAnalyzer()

        # 배치 분석
        results = []
        for article in articles:
            result = analyzer.analyze(
                title=article["title"],
                content=article.get("content", ""),
            )
            results.append({
                "title": article["title"],
                "sentiment": result.sentiment.value,
                "confidence": result.confidence,
                "score": result.score,
                "keywords": result.keywords,
            })

        # 통계
        positive_count = sum(1 for r in results if r["sentiment"] == "positive")
        negative_count = sum(1 for r in results if r["sentiment"] == "negative")
        neutral_count = sum(1 for r in results if r["sentiment"] == "neutral")

        logger.info(
            f"✅ {ticker} 감성 분석 완료 "
            f"(긍정: {positive_count}, 부정: {negative_count}, 중립: {neutral_count})"
        )

        return {
            "ticker": ticker,
            "analyzed_count": len(results),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "results": results[:5],  # 최대 5건만 반환
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ {ticker} 감성 분석 실패: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(name="news.calculate_scores", bind=True, max_retries=3)
def calculate_news_scores(ticker: str, articles: List[Dict[str, Any]], target_date: str) -> Dict[str, Any]:
    """
    일일 뉴스 점수 계산 태스크

    Args:
        ticker: 종목코드
        articles: 뉴스 기사 리스트
        target_date: 대상 날짜 (YYYY-MM-DD)

    Returns:
        점수 계산 결과
    """
    try:
        logger.info(f"📊 {ticker} {target_date} 뉴스 점수 계산 시작")

        # 날짜 파싱
        analysis_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        # 뉴스 점수 계산
        scorer = NewsScorer()
        result = scorer.calculate_daily_score(
            ticker=ticker,
            articles=articles,
            target_date=analysis_date,
        )

        logger.info(
            f"✅ {ticker} {target_date} 뉴스 점수: {result.total_score:.1f} "
            f"(긍정: {result.positive_count}, 부정: {result.negative_count})"
        )

        return {
            "ticker": ticker,
            "date": target_date,
            "total_score": result.total_score,
            "positive_count": result.positive_count,
            "negative_count": result.negative_count,
            "neutral_count": result.neutral_count,
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ {ticker} 뉴스 점수 계산 실패: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(name="news.collect_all_stocks", bind=True, max_retries=3)
def collect_all_stocks_news(market: str = "KOSPI", days: int = 7, max_articles: int = 30) -> Dict[str, Any]:
    """
    전체 종목 뉴스 수집 태스크

    Args:
        market: 시장 구분 (KOSPI, KOSDAQ)
        days: 수집할 날짜 범위
        max_articles: 종목별 최대 기사 수

    Returns:
        수집 결과 요약
    """
    try:
        logger.info(f"📰 {market} 전체 종목 뉴스 수집 시작")

        # 간단 구현: 주요 종목 리스트
        stocks = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035420", "NAVER"),
            ("066570", "LG전자"),
            ("005380", "현대차"),
        ]

        logger.info(f"📋 {len(stocks)}개 종목 뉴스 수집 대상")

        # 각 종목별 뉴스 수집
        results = []
        for ticker, name in stocks:
            try:
                task_result = collect_news(ticker, days, max_articles)
                results.append({
                    "ticker": ticker,
                    "name": name,
                    "collected": task_result.get("collected_count", 0),
                })
            except Exception as e:
                logger.error(f"❌ {ticker} 뉴스 수집 실패: {e}")
                results.append({
                    "ticker": ticker,
                    "name": name,
                    "collected": 0,
                    "error": str(e),
                })

        total_collected = sum(r.get("collected", 0) for r in results)

        logger.info(f"✅ {market} 전체 종목 뉴스 수집 완료 (총 {total_collected}건)")

        return {
            "market": market,
            "target_count": len(stocks),
            "success_count": sum(1 for r in results if r.get("collected", 0) > 0),
            "total_collected": total_collected,
            "results": results[:10],  # 최대 10종목만 반환
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ {market} 전체 종목 뉴스 수집 실패: {e}")
        raise self.retry(exc=e, countdown=120)  # 2분 후 재시도


@shared_task(name="news.pipeline", bind=True, max_retries=3)
def news_pipeline_task(ticker: str, days: int = 7, max_articles: int = 30) -> Dict[str, Any]:
    """
    뉴스 파이프라인 태스크 (수집 → 분석 → 점수화)

    Args:
        ticker: 종목코드
        days: 수집할 날짜 범위
        max_articles: 최대 기사 수

    Returns:
        파이프라인 실행 결과
    """
    try:
        logger.info(f"🔄 {ticker} 뉴스 파이프라인 시작")

        # 1. 뉴스 수집
        collect_result = collect_news(ticker, days, max_articles)
        collected_count = collect_result["collected_count"]
        articles = collect_result["articles"]

        if collected_count == 0:
            logger.warning(f"⚠️  {ticker} 수집된 뉴스 없음")
            return {
                "ticker": ticker,
                "stage": "collect",
                "success": False,
                "reason": "no_articles",
            }

        # 2. 감성 분석
        analyze_result = analyze_sentiment(ticker, articles)
        positive_count = analyze_result["positive_count"]
        negative_count = analyze_result["negative_count"]

        # 3. 점수 계산
        today = date.today().isoformat()
        score_result = calculate_news_scores(ticker, articles, today)

        logger.info(
            f"✅ {ticker} 뉴스 파이프라인 완료 "
            f"(수집: {collected_count}건, 점수: {score_result['total_score']:.1f})"
        )

        return {
            "ticker": ticker,
            "stage": "complete",
            "collected_count": collected_count,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_score": score_result["total_score"],
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ {ticker} 뉴스 파이프라인 실패: {e}")
        raise self.retry(exc=e, countdown=120)


# 태스크 체이닝 예시
@shared_task(name="news.collect_and_analyze", bind=True)
def collect_and_analyze_news(ticker: str):
    """
    뉴스 수집 후 감성 분석 (체이닝 예시)

    Args:
        ticker: 종목코드

    Returns:
        감성 분석 결과
    """
    # 뉴스 수집
    collect_result = collect_news(ticker, days=7, max_articles=30)

    # 결과에서 articles 추출
    articles = collect_result["articles"]

    # 감성 분석 (체이닝)
    return analyze_sentiment(ticker, articles)


# ============================================================================
# Phase 5: 자동 뉴스 수집 스케줄 태스크 (GREEN)
# ============================================================================

@shared_task(name="news.collect_and_save", bind=True, max_retries=3)
def collect_and_save_task(
    self,  # Celery task binding (self)
    ticker: str,
    days: int = 7,
    max_articles: int = 30,
) -> Dict[str, Any]:
    """
    뉴스 수집 및 DB 저장 태스크 (Phase 5: GREEN)

    수집된 뉴스와 URL을 DB에 자동 저장

    Args:
        self: Celery task instance (bind=True)
        ticker: 종목 코드
        days: 수집할 날짜 범위
        max_articles: 최대 기사 수

    Returns:
        저장 결과 딕셔너리
    """
    session = None
    try:
        logger.info(f"🔄 {ticker} 뉴스 수집 및 DB 저장 시작")

        # 1. 뉴스 수집
        collector = NewsCollector()
        articles = collector.fetch_stock_news(
            ticker=ticker,
            days=days,
            max_articles=max_articles,
        )

        if not articles:
            logger.warning(f"⚠️  {ticker} 수집된 뉴스 없음")
            return {
                "ticker": ticker,
                "success": False,
                "reason": "no_articles",
                "saved_count": 0,
            }

        # 2. news_urls 추출
        news_urls = [
            {"title": article.get("title", ""), "url": article.get("url", "")}
            for article in articles
            if article.get("url")  # URL이 있는 기사만
        ]

        # 3. 감성 분석
        analyzer = SentimentAnalyzer()

        # 전체 분석을 위한 텍스트 결합
        all_titles = " ".join([a.get("title", "") for a in articles])
        all_content = " ".join([a.get("content", "") for a in articles])

        sentiment_result = analyzer.analyze(
            title=all_titles,
            content=all_content[:2000],  # 제한
        )

        # 4. DB 저장
        # get_db_session()는 제너레이터, next()로 session 추출
        session_gen = get_db_session()
        session = next(session_gen)
        repo = AIAnalysisRepository(session)

        analysis = repo.save_analysis(
            ticker=ticker,
            analysis_date=date.today(),
            sentiment=sentiment_result.sentiment.value,
            score=sentiment_result.score,
            summary=f"최근 {len(articles)}건의 뉴스 분석 결과입니다.",
            keywords=sentiment_result.keywords[:5],  # 상위 5개 키워드
            recommendation=_get_recommendation_from_sentiment(sentiment_result.sentiment.value),
            confidence=sentiment_result.confidence,
            news_count=len(articles),
            news_urls=news_urls,  # 🔑 Phase 5: news_urls 저장
        )

        logger.info(
            f"✅ {ticker} 뉴스 저장 완료 "
            f"(기사: {len(articles)}건, URLs: {len(news_urls)}건, "
            f"감성: {sentiment_result.sentiment.value})"
        )

        return {
            "ticker": ticker,
            "success": True,
            "collected_count": len(articles),
            "saved_count": 1,
            "news_urls_count": len(news_urls),
            "sentiment": sentiment_result.sentiment.value,
            "score": sentiment_result.score,
            "analysis_id": analysis.id,
        }

    except Exception as e:
        logger.error(f"❌ {ticker} 뉴스 저장 실패: {e}")
        # self.retry는 Celery task binding이 필요
        return {
            "ticker": ticker,
            "success": False,
            "error": str(e),
        }

    finally:
        if session:
            session.close()


@shared_task(name="news.collect_multiple_and_save", bind=True, max_retries=3)
def collect_multiple_and_save(
    self,
    tickers: List[str],
    days: int = 7,
    max_articles: int = 30,
) -> Dict[str, Any]:
    """
    여러 종목 뉴스 수집 및 DB 저장 (Phase 5: GREEN)

    Args:
        self: Celery task instance
        tickers: 종목 코드 리스트
        days: 수집할 날짜 범위
        max_articles: 종목별 최대 기사 수

    Returns:
        저장 결과 요약
    """
    logger.info(f"🔄 {len(tickers)}개 종목 뉴스 수집 시작")

    results = []
    success_count = 0
    total_urls = 0

    for ticker in tickers:
        try:
            result = collect_and_save_task(self, ticker, days, max_articles)
            results.append({
                "ticker": ticker,
                "success": result.get("success", False),
                "news_count": result.get("collected_count", 0),
                "urls_count": result.get("news_urls_count", 0),
            })

            if result.get("success"):
                success_count += 1
                total_urls += result.get("news_urls_count", 0)

        except Exception as e:
            logger.error(f"❌ {ticker} 처리 실패: {e}")
            results.append({
                "ticker": ticker,
                "success": False,
                "error": str(e),
            })

    logger.info(
        f"✅ 일괄 처리 완료 "
        f"(성공: {success_count}/{len(tickers)}, 총 URL: {total_urls}건)"
    )

    return {
        "total_tickers": len(tickers),
        "success_count": success_count,
        "total_urls": total_urls,
        "results": results,
        "success": True,
    }


@shared_task(name="news.scheduled_daily_collection", bind=True, max_retries=3)
def scheduled_daily_collection(
    self,
    market: str = "KOSPI",
    days: int = 7,
    max_articles: int = 30,
) -> Dict[str, Any]:
    """
    일일 스케줄 뉴스 수집 (Phase 5: GREEN)

    Celery Beat에서 호출되는 일일 뉴스 수집 태스크

    Args:
        self: Celery task instance
        market: 시장 구분 (KOSPI, KOSDAQ)
        days: 수집할 날짜 범위
        max_articles: 종목별 최대 기사 수

    Returns:
        수집 결과
    """
    logger.info(f"📅 {market} 일일 뉴스 수집 스케줄 실행")

    # 주요 종목 리스트
    major_stocks = {
        "KOSPI": ["005930", "000660", "035420", "005380", "066570", "028260", "105560", "035720"],
        "KOSDAQ": ["051910", "247540", "323410", "086520", "251270"],
    }

    tickers = major_stocks.get(market, major_stocks["KOSPI"])

    return collect_multiple_and_save(self, tickers, days, max_articles)


def _get_recommendation_from_sentiment(sentiment: str) -> str:
    """
    감성 분석 결과로 추천사항 생성

    Args:
        sentiment: 감성 (positive/negative/neutral)

    Returns:
        추천사항 (BUY/SELL/HOLD)
    """
    if sentiment == "positive":
        return "BUY"
    elif sentiment == "negative":
        return "SELL"
    else:
        return "HOLD"
