"""
Daytrading Scanner - 시장 스캔 서비스

실제 시장 데이터를 기반으로 단타 매매 기회 종목을 스캔합니다.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Stock, DailyPrice
from src.repositories.stock_repository import StockRepository
from src.repositories.daytrading_signal_repository import DaytradingSignalRepository
from services.daytrading_scanner.models.scoring import (
    DaytradingScoreResult,
    DaytradingCheck,
    calculate_daytrading_score,
    get_grade_from_score,
)

logger = logging.getLogger(__name__)


class DaytradingScanner:
    """
    단타 시장 스캐너

    실제 시장 데이터를 기반으로 단타 매매 기회 종목을 스캔합니다.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        초기화

        Args:
            db: DB 세션 (선택, 없으면 실행 시 생성)
        """
        self._db = db
        # Repository는 실행 시 주입

    async def scan_market(
        self,
        request: Dict[str, Any],
        db: Optional[Session] = None
    ) -> List[DaytradingScoreResult]:
        """
        시장 스캔 실행

        Args:
            request: 스캔 요청 (market, limit)
            db: DB 세션 (선택)

        Returns:
            스캔 결과 리스트
        """
        market = request.get("market")
        limit = request.get("limit", 50)

        # DB 세션 확인
        if db is None:
            from src.database.session import get_db_session_sync
            db = get_db_session_sync()

        # 종목 조회
        stocks = self._get_stocks(db, market)
        logger.info(f"Scanning {len(stocks)} stocks (market: {market or 'ALL'})")

        # 점수 계산
        results = []
        for stock in stocks[:limit]:
            try:
                # 일봉 데이터 조회
                prices = self._get_recent_prices(db, stock.ticker, days=20)
                if not prices or len(prices) < 5:
                    logger.debug(f"Insufficient price data for {stock.ticker}")
                    continue

                # 수급 데이터 조회 (Mock - 실제로는 institutional_flows 테이블)
                flow = self._get_mock_flow_data(stock.ticker)

                # 점수 계산
                score_result = calculate_daytrading_score(stock, prices, flow)

                # 결과 추가
                results.append(score_result)

                # DB 저장
                await self._save_signal(db, score_result, prices[0])

            except Exception as e:
                logger.error(f"Error scanning {stock.ticker}: {e}")

        # 캐시 무효화
        await self._invalidate_cache()

        logger.info(f"Scan complete: {len(results)} candidates found")
        return results

    def _get_stocks(self, db: Optional[Session], market: Optional[str]) -> List[Stock]:
        """종목 리스트 조회"""
        # 기존 방식 사용 (SQLAlchemy 1.x/2.x 호환)
        from src.database.models import Stock as StockModel

        if db is None:
            return []

        # SQLAlchemy Core 방식으로 쿼리
        query = select(StockModel).where(
            StockModel.is_etf == False,
            StockModel.is_admin == False,
            StockModel.is_spac == False,
            StockModel.is_bond == False,
            StockModel.is_excluded_etf == False,
        )

        if market:
            query = query.where(StockModel.market == market)

        # 거래량 순 정렬 (우선 스캔)
        # query = query.order_by(Stock.volume.desc())

        result = db.execute(query.limit(200))
        return list(result.scalars().all())

    def _get_recent_prices(
        self,
        db: Optional[Session],
        ticker: str,
        days: int = 20
    ) -> List[DailyPrice]:
        """최근 일봉 데이터 조회"""
        from src.database.models import DailyPrice as DailyPriceModel

        if db is None:
            return []

        since_date = datetime.now(timezone.utc) - timedelta(days=days * 2)

        query = select(DailyPriceModel).where(
            DailyPriceModel.ticker == ticker,
            DailyPriceModel.date >= since_date
        ).order_by(DailyPriceModel.date.desc()).limit(days)

        result = db.execute(query)
        return list(result.scalars().all())

    def _get_mock_flow_data(self, ticker: str) -> Any:
        """Mock 수급 데이터 (Phase 4에서 실제 데이터로 대체)"""
        # Flow 데이터 객체 생성
        class MockFlow:
            def __init__(self):
                self.foreign_net_buy = 0
                self.inst_net_buy = 0
        return MockFlow()

    async def _save_signal(
        self,
        db: Optional[Session],
        score_result: DaytradingScoreResult,
        current_price
    ) -> None:
        """시그널 DB 저장"""
        try:
            from src.repositories.daytrading_signal_repository import DaytradingSignalRepository
            from src.database.models import DaytradingSignal

            signal_repo = DaytradingSignalRepository(db)

            # 기존 시그널 확인
            existing = db.query(DaytradingSignal).filter_by(
                ticker=score_result.ticker,
                status="OPEN"
            ).first()

            # 체크리스트를 JSON 형식으로 변환
            checks_json = [
                {
                    "name": check.name,
                    "status": check.status,
                    "points": check.points
                }
                for check in score_result.checks
            ]

            if existing:
                # 업데이트
                existing.score = score_result.total_score
                existing.grade = score_result.grade
                existing.checks = checks_json
                existing.entry_price = current_price.close_price
                existing.target_price = int(current_price.close_price * 1.05)
                existing.stop_loss = int(current_price.close_price * 0.97)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                # 신규 생성
                new_signal = DaytradingSignal(
                    ticker=score_result.ticker,
                    name=score_result.name,
                    market="KOSPI" if score_result.ticker.startswith("00") else "KOSDAQ",
                    score=score_result.total_score,
                    grade=score_result.grade,
                    checks=checks_json,
                    entry_price=current_price.close_price,
                    target_price=int(current_price.close_price * 1.05),
                    stop_loss=int(current_price.close_price * 0.97),
                    status="OPEN",
                    created_at=datetime.now(timezone.utc)
                )
                db.add(new_signal)

            db.commit()
            logger.debug(f"Saved signal for {score_result.ticker}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving signal for {score_result.ticker}: {e}")

    async def _invalidate_cache(self) -> None:
        """캐시 무효화"""
        try:
            from src.cache.cache_client import get_cache
            cache = await get_cache()
            if cache:
                deleted = await cache.clear_pattern("daytrading:signals:*")
                if deleted > 0:
                    logger.info(f"Invalidated {deleted} daytrading signal cache entries")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
