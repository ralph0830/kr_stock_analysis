"""
Chatbot Stock Recommender
종목 추천 로직
"""

import logging
from typing import List, Dict, Any, Optional

from services.chatbot.retriever import get_retriever

logger = logging.getLogger(__name__)


class StockRecommender:
    """
    종목 추천기

    VCP/종가베팅 시그널 기반 종목 추천
    """

    def __init__(self):
        """종목 추천기 초기화"""
        self._retriever = get_retriever()

    def recommend_by_vcp(
        self,
        min_score: float = 70.0,
        min_grade: str = "B",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        VCP 시그널 기반 추천

        Args:
            min_score: 최소 점수
            min_grade: 최소 등급 (S/A/B/C)
            limit: 최대 추천 수

        Returns:
            추천 종목 리스트
        """
        try:
            signals = self._retriever.search_signals(
                signal_type="vcp",
                limit=limit * 2  # 필터링을 위해 더 가져옴
            )

            # 점수/등급 필터링
            grade_order = {"S": 4, "A": 3, "B": 2, "C": 1}
            min_grade_value = grade_order.get(min_grade, 0)

            filtered = [
                s for s in signals
                if s.get("score", 0) >= min_score
                and grade_order.get(s.get("grade", "C"), 0) >= min_grade_value
            ]

            # 점수 순 정렬
            filtered.sort(key=lambda x: x.get("score", 0), reverse=True)

            return filtered[:limit]

        except Exception as e:
            logger.error(f"VCP 추천 실패: {e}")
            return []

    def recommend_by_jongga(
        self,
        min_score: int = 6,
        min_grade: str = "B",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        종가베팅 V2 시그널 기반 추천

        Args:
            min_score: 최소 점수 (0-12)
            min_grade: 최소 등급 (S/A/B/C)
            limit: 최대 추천 수

        Returns:
            추천 종목 리스트
        """
        try:
            signals = self._retriever.search_signals(
                signal_type="jongga_v2",
                limit=limit * 2
            )

            # 점수/등급 필터링
            grade_order = {"S": 4, "A": 3, "B": 2, "C": 1}
            min_grade_value = grade_order.get(min_grade, 0)

            filtered = [
                s for s in signals
                if s.get("score", 0) >= min_score
                and grade_order.get(s.get("grade", "C"), 0) >= min_grade_value
            ]

            # 점수 순 정렬
            filtered.sort(key=lambda x: x.get("score", 0), reverse=True)

            return filtered[:limit]

        except Exception as e:
            logger.error(f"종가베팅 추천 실패: {e}")
            return []

    def get_top_picks(
        self,
        strategy: str = "both",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        종합 추천 종목

        Args:
            strategy: 전략 (vcp, jongga, both)
            limit: 최대 추천 수

        Returns:
            추천 종목 리스트
        """
        recommendations = []

        if strategy in ["vcp", "both"]:
            vcp_picks = self.recommend_by_vcp(min_score=70, min_grade="A", limit=limit)
            recommendations.extend(vcp_picks)

        if strategy in ["jongga", "both"]:
            jongga_picks = self.recommend_by_jongga(min_score=8, min_grade="A", limit=limit)
            recommendations.extend(jongga_picks)

        # 중복 제거 (티커 기준)
        seen_tickers = set()
        unique_recommendations = []

        for rec in recommendations:
            ticker = rec.get("ticker")
            if ticker and ticker not in seen_tickers:
                seen_tickers.add(ticker)
                unique_recommendations.append(rec)

        # 종합 점수로 정렬
        unique_recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)

        return unique_recommendations[:limit]

    def get_position_size(self, grade: str) -> float:
        """
        등급별 포지션 사이즈 계산

        Args:
            grade: 등급 (S/A/B/C)

        Returns:
            추천 포지션 비율 (%)
        """
        position_sizes = {
            "S": 15.0,  # 15%
            "A": 12.0,  # 12%
            "B": 10.0,  # 10%
            "C": 5.0,   # 5%
        }
        return position_sizes.get(grade, 5.0)

    def format_recommendation(self, stock: Dict[str, Any]) -> str:
        """
        종목 추천 포맷팅

        Args:
            stock: 종목 정보

        Returns:
            포맷팅된 추천 문자열
        """
        ticker = stock.get("ticker", "")
        signal_type = stock.get("signal_type", "")
        grade = stock.get("grade", "")
        score = stock.get("score", 0)

        # 종목명 조회
        stocks = self._retriever.search_stocks(ticker, limit=1)
        name = stocks[0].get("name", ticker) if stocks else ticker

        # 포지션 사이즈
        position_size = self.get_position_size(grade)

        return (
            f"{name}({ticker}) - {signal_type.upper()} {grade}등급 ({score}점) "
            f"| 추천 비중: {position_size}%"
        )


# 싱글톤 인스턴스
_recommender: Optional[StockRecommender] = None


def get_recommender() -> StockRecommender:
    """종목 추천기 싱글톤 반환"""
    global _recommender
    if _recommender is None:
        _recommender = StockRecommender()
    return _recommender
