"""
Celery News Tasks
뉴스 수집 및 감성 분석 태스크
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

from celery import shared_task

from src.collectors.news_collector import NewsCollector
from src.analysis.sentiment_analyzer import SentimentAnalyzer
from src.analysis.news_scorer import NewsScorer

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
