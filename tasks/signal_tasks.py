"""
Celery Tasks - Signal Engine
종가베팅 V2 시그널 생성 비동기 작업
"""

import logging
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.signal_tasks.generate_jongga_signals", bind=True)
def generate_jongga_signals(
    self,
    capital: int = 10_000_000,
    top_n: int = 30,
    market: str = "KOSPI",
    min_score: int = 6
):
    """
    종가베팅 V2 시그널 생성 태스크

    Args:
        capital: 총 자본 (기본 1000만원)
        top_n: 상위 N개 종목
        market: 시장 (KOSPI/KOSDAQ/ALL)
        min_score: 최소 점수 (0-12)

    Returns:
        생성된 시그널 리스트
    """
    try:
        logger.info(f"종가베팅 시그널 생성 시작: 자본 {capital}, 상위 {top_n}개, 시장 {market}, 최소점수 {min_score}")

        # Signal Engine 호출
        # TODO: 실제 종목 스캔 로직
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()

        # Mock 종목 리스트
        mock_stocks = [
            ("005930", "삼성전자", 80000),
            ("000660", "SK하이닉스", 180000),
            ("035420", "NAVER", 250000),
        ][:top_n]

        signals = []
        for ticker, name, price in mock_stocks:
            signal = scorer.calculate(ticker, name, price)
            if signal:
                score_total = signal.score.total if hasattr(signal.score, 'total') else 0
                if score_total >= 6:
                    signals.append(signal.to_dict())

        # 등급순 정렬
        grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        signals.sort(key=lambda s: grade_order[s["grade"]])

        logger.info(f"종가베팅 시그널 생성 완료: {len(signals)}개")

        return {
            "status": "success",
            "count": len(signals),
            "capital": capital,
            "signals": signals,
        }

    except Exception as e:
        logger.error(f"시그널 생성 실패: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.signal_tasks.analyze_single_stock")
def analyze_single_stock(ticker: str, name: str, price: int):
    """단일 종목 시그널 분석"""
    try:
        from services.signal_engine.scorer import SignalScorer

        scorer = SignalScorer()
        signal = scorer.calculate(ticker, name, price)

        if not signal:
            return {"status": "failed", "ticker": ticker}

        return {
            "status": "success",
            "signal": signal.to_dict(),
        }

    except Exception as e:
        logger.error(f"종목 분석 실패 ({ticker}): {e}")
        return {"status": "error", "message": str(e)}
