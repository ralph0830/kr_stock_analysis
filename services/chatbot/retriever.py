"""
Chatbot Knowledge Retriever
RAG 기반 지식 검색 엔진
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.repositories.stock_repository import StockRepository
from src.repositories.signal_repository import SignalRepository
from services.chatbot.kiwoom_integration import (
    is_kiwoom_available,
)

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    지식 검색기

    주식 관련 데이터를 검색하여 RAG를 위한 컨텍스트를 제공합니다.
    """

    def __init__(self):
        """지식 검색기 초기화"""
        self._stock_repo: Optional[StockRepository] = None
        self._signal_repo: Optional[SignalRepository] = None

    def _get_stock_repo(self) -> StockRepository:
        """StockRepository lazy loading"""
        if self._stock_repo is None:
            from src.database.session import get_db_session
            self._stock_repo = StockRepository(get_db_session().__enter__())
        return self._stock_repo

    def _get_signal_repo(self) -> SignalRepository:
        """SignalRepository lazy loading"""
        if self._signal_repo is None:
            from src.database.session import get_db_session
            self._signal_repo = SignalRepository(get_db_session().__enter__())
        return self._signal_repo

    def search_stocks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        종목 검색

        Args:
            query: 검색어 (종목명 또는 티커)
            limit: 최대 결과 수

        Returns:
            종목 리스트
        """
        if not query or len(query.strip()) < 2:
            return []

        try:
            repo = self._get_stock_repo()

            # 티커 검색 (6자리 숫자)
            if query.isdigit() and len(query) == 6:
                stock = repo.get_by_ticker(query)
                if stock:
                    return [{
                        "ticker": stock.ticker,
                        "name": stock.name,
                        "market": stock.market,
                        "sector": stock.sector,
                    }]

            # 이름 검색
            results = repo.search(query, limit=limit)
            return [
                {
                    "ticker": s.ticker,
                    "name": s.name,
                    "market": s.market,
                    "sector": s.sector,
                }
                for s in results
            ]

        except Exception as e:
            logger.error(f"종목 검색 실패: {e}")
            return []

    def search_signals(
        self,
        ticker: Optional[str] = None,
        signal_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        시그널 검색

        Args:
            ticker: 종목 티커 (선택)
            signal_type: 시그널 타입 (vcp, jongga_v2)
            limit: 최대 결과 수

        Returns:
            시그널 리스트
        """
        try:
            repo = self._get_signal_repo()

            if ticker:
                # 특정 종목 시그널
                signals = repo.get_by_ticker(ticker, limit=limit)
            else:
                # 전체 활성 시그널
                signals = repo.get_active(limit=limit)

            return [
                {
                    "ticker": s.ticker,
                    "name": s.name or "",  # Signal 모델에 name이 없을 수 있음
                    "signal_type": s.signal_type,
                    "score": s.score,
                    "grade": s.grade,
                    "created_at": s.signal_date.isoformat() if s.signal_date else None,
                }
                for s in signals
            ]

        except Exception as e:
            logger.error(f"시그널 검색 실패: {e}")
            return []

    def get_market_status(self) -> Dict[str, Any]:
        """
        Market Gate 상태 조회

        Returns:
            Market 상태 정보
        """
        try:
            from src.database.session import get_db_session
            from src.database.models import MarketStatus
            from sqlalchemy import desc

            db = get_db_session().__enter__()
            latest = db.query(MarketStatus).order_by(desc(MarketStatus.date)).first()

            if latest:
                return {
                    "status": latest.gate or "YELLOW",
                    "level": latest.gate_score or 50,
                    "kospi_status": self._get_market_status_text(latest.kospi_change_pct),
                    "kosdaq_status": self._get_market_status_text(latest.kosdaq_change_pct),
                    "updated_at": latest.date.isoformat() if latest.date else None,
                }

            return {
                "status": "YELLOW",
                "level": 50,
                "kospi_status": "정보 없음",
                "kosdaq_status": "정보 없음",
                "updated_at": None,
            }

        except Exception as e:
            logger.error(f"Market Gate 상태 조회 실패: {e}")
            return {
                "status": "UNKNOWN",
                "level": 0,
                "kospi_status": "알 수 없음",
                "kosdaq_status": "알 수 없음",
                "updated_at": None,
            }

    def _get_market_status_text(self, change_pct: Optional[float]) -> str:
        """변동률을 텍스트로 변환"""
        if change_pct is None:
            return "정보 없음"
        elif change_pct > 1.0:
            return "강세"
        elif change_pct > 0:
            return "소폭 상승"
        elif change_pct > -1.0:
            return "소폭 하락"
        else:
            return "약세"

    def search_news(
        self,
        ticker: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        뉴스 검색 (AI Analysis)

        Args:
            ticker: 종목 티커 (선택)
            limit: 최대 결과 수

        Returns:
            뉴스/분석 리스트
        """
        try:
            from src.database.session import get_db_session
            from src.database.models import AIAnalysis
            from sqlalchemy import desc

            db = get_db_session().__enter__()

            query = db.query(AIAnalysis)
            if ticker:
                query = query.filter(AIAnalysis.ticker == ticker)

            results = query.order_by(desc(AIAnalysis.created_at)).limit(limit).all()

            return [
                {
                    "ticker": a.ticker,
                    "summary": a.summary,
                    "recommendation": a.recommendation,
                    "sentiment": a.sentiment,
                    "score": a.score,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in results
            ]

        except Exception as e:
            logger.error(f"뉴스 검색 실패: {e}")
            return []

    def retrieve_context(self, query: str) -> Dict[str, Any]:
        """
        질문에 대한 컨텍스트 검색

        Args:
            query: 사용자 질문

        Returns:
            검색된 컨텍스트
        """
        context = {
            "query": query,
            "query_type": self._classify_query(query),
            "stocks": [],
            "signals": [],
            "news": [],
            "market_status": None,
            "timestamp": datetime.now().isoformat(),
        }

        # 종목 검색
        stocks = self.search_stocks(query)
        if stocks:
            context["stocks"] = stocks[:3]  # 상위 3개

            # 종목별 시그널 검색
            for stock in stocks[:2]:  # 상위 2개 종목만
                signals = self.search_signals(ticker=stock["ticker"], limit=2)
                context["signals"].extend(signals)

            # 종목별 뉴스 검색
            for stock in stocks[:1]:  # 최상위 1개 종목만
                news = self.search_news(ticker=stock["ticker"], limit=2)
                context["news"].extend(news)

        # 시장 상태 (시장 관련 질문인 경우)
        if self._is_market_query(query):
            context["market_status"] = self.get_market_status()

        return context

    def _classify_query(self, query: str) -> str:
        """
        질문 유형 분류

        Returns:
            질문 유형 (stock, market, recommendation, general)
        """
        if any(word in query for word in ["시장", "마켓", "kospi", "kosdaq", "지수"]):
            return "market"
        elif any(word in query for word in ["추천", "매수", "사야", "buy", "recommend"]):
            return "recommendation"
        elif any(word in query for word in ["종목", "삼성", "sk", "네이버", "카카오"]):
            return "stock"
        else:
            return "general"

    def _is_market_query(self, query: str) -> bool:
        """시장 관련 질문인지 확인"""
        market_keywords = ["시장", "마켓", "kospi", "kosdaq", "지수", "현황"]
        return any(word in query.lower() for word in market_keywords)

    async def get_realtime_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Kiwoom API에서 실시간 가격 조회

        Args:
            ticker: 종목 코드

        Returns:
            실시간 가격 정보 또는 None
        """
        if not is_kiwoom_available():
            logger.warning("Kiwoom API not available for realtime price")
            return None

        try:
            from services.chatbot.kiwoom_integration import get_kiwoom_current_price

            price_data = await get_kiwoom_current_price(ticker)
            return price_data

        except Exception as e:
            logger.error(f"실시간 가격 조회 실패: {e}")
            return None

    async def get_realtime_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Kiwoom API에서 실시간 종목 정보 조회

        Args:
            ticker: 종목 코드

        Returns:
            종목 정보 또는 None
        """
        if not is_kiwoom_available():
            logger.warning("Kiwoom API not available for stock info")
            return None

        try:
            from services.chatbot.kiwoom_integration import get_kiwoom_stock_info

            stock_info = await get_kiwoom_stock_info(ticker)
            return stock_info

        except Exception as e:
            logger.error(f"실시간 종목 정보 조회 실패: {e}")
            return None

    async def enrich_with_kiwoom_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        컨텍스트에 Kiwoom 실시간 데이터 추가

        Args:
            context: 기존 컨텍스트

        Returns:
            Kiwoom 데이터가 추가된 컨텍스트
        """
        if not is_kiwoom_available():
            return context

        # 종목이 있으면 실시간 가격 추가
        if context.get("stocks"):
            for stock in context["stocks"]:
                ticker = stock.get("ticker")
                if ticker:
                    price_data = await self.get_realtime_price(ticker)
                    if price_data:
                        stock["realtime_price"] = price_data

        return context


# 싱글톤 인스턴스
_retriever: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    """지식 검색기 싱글톤 반환"""
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever()
    return _retriever
