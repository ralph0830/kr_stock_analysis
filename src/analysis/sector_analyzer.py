"""
Sector Analyzer
섹터별 종가베팅 V2 점수 집계
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy.orm import Session
from src.database.models import Stock
from src.database.session import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class SectorScore:
    """섹터 점수 결과"""
    sector: str
    avg_score: float
    max_score: float
    max_score_ticker: str
    max_score_name: str
    stock_count: int
    top_stocks: List[Dict[str, Any]]  # 상위 3개 종목


class SectorAnalyzer:
    """
    섹터별 점수 집계기

    종가베팅 V2 점수를 섹터별로 집계하여
    Market Gate 시각화에 활용
    """

    # 섹터 분류 (예시)
    SECTOR_MAPPING = {
        "반도체": "반도체",
        "자동차": "자동차",
        "바이오": "바이오/헬스케어",
        "IT": "IT/소프트웨어",
        "통신": "통신",
        "금융": "금융",
        "건설": "건설",
        "에너지": "에너지",
        "철강": "철강/비철금속",
        "화학": "화학",
        "음식": "음식/음료",
        "유통": "유통",
        "종이": "종이/섬유",
        "의료": "의료/서비스",
        "운송": "운송",
        "전기": "전기/전자",
        "기계": "기계",
        "국방": "국방",
        "교육": "교육",
        "오락": "오락/여가",
        "여행": "여가/레저",
        "함선": "함선",
    }

    def __init__(self, session: Optional[Session] = None):
        """
        SectorAnalyzer 초기화

        Args:
            session: DB 세션 (선택사항)
        """
        self.session = session or SessionLocal()

    def calculate_sector_scores(
        self,
        min_score: int = 0
    ) -> List[SectorScore]:
        """
        섹터별 점수 계산

        Args:
            min_score: 최소 점수 필터 (기본 0점)

        Returns:
            섹터 점수 리스트
        """
        try:
            # 전체 종목 조회
            stocks = self.session.query(
                Stock.ticker,
                Stock.name,
                Stock.sector,
                Stock.market
            ).all()

            if not stocks:
                logger.warning("종목 데이터 없음")
                return []

            # 섹터별 점수 집계
            sector_data = defaultdict(lambda: {
                "scores": [],
                "stocks": []
            })

            for stock in stocks:
                sector = stock.sector or "미분류"
                sector_data[sector]["stocks"].append({
                    "ticker": stock.ticker,
                    "name": stock.name,
                    "sector": sector,
                    "market": stock.market,
                })

            # 실제 점수는 SignalScorer를 통해 계산해야 하므로
            # 여기서는 섹터별 종목 개수만 반환
            results = []
            for sector, data in sector_data.items():
                results.append(SectorScore(
                    sector=sector,
                    avg_score=0.0,
                    max_score=0.0,
                    max_score_ticker="",
                    max_score_name="",
                    stock_count=len(data["stocks"]),
                    top_stocks=data["stocks"][:3]  # 상위 3개
                ))

            # 평균 점순 순 정렬
            results.sort(key=lambda x: x.avg_score, reverse=True)

            return results

        except Exception as e:
            logger.error(f"섹터 점수 계산 실패: {e}")
            return []

    def get_sector_stocks(self, sector: str) -> List[Dict[str, Any]]:
        """
        특정 섹터의 종목 리스트 조회

        Args:
            sector: 섹터명

        Returns:
            종목 리스트
        """
        try:
            stocks = self.session.query(
                Stock.ticker,
                Stock.name,
                Stock.sector,
                Stock.market
            ).filter(Stock.sector == sector).all()

            return [
                {
                    "ticker": s.ticker,
                    "name": s.name,
                    "sector": s.sector,
                    "market": s.market,
                }
                for s in stocks
            ]

        except Exception as e:
            logger.error(f"섹터 종목 조회 실패 ({sector}): {e}")
            return []

    def get_all_sectors(self) -> List[str]:
        """
        전체 섹터 리스트 조회

        Returns:
            섹터 이름 리스트
        """
        try:
            sectors = self.session.query(Stock.sector).distinct().all()
            return [s[0] for s in sectors if s[0]]

        except Exception as e:
            logger.error(f"섹터 리스트 조회 실패: {e}")
            return []
