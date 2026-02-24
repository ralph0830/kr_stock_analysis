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

    # 거래정지 상태 캐시 (1시간 유효)
    _suspended_stocks_cache: Dict[str, str] = {}
    _suspended_cache_time: Optional[float] = None
    _SUSPENDED_CACHE_TTL = 3600  # 1시간

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

        logger.info(f"🔍 scan_market called: market={market}, limit={limit}")

        # DB 세션 전달 시 바로 사용
        if db is not None:
            return await self._scan_with_db(db, market, limit)

        # DB 세션 없으면 새로 생성
        from src.database.session import get_db_session_sync
        with get_db_session_sync() as db:
            return await self._scan_with_db(db, market, limit)

    async def _scan_with_db(
        self,
        db: Session,
        market: Optional[str],
        limit: int
    ) -> List[DaytradingScoreResult]:
        """DB 세션을 사용한 실제 스캔 로직"""
        # 종목 조회
        stocks = self._get_stocks(db, market)
        logger.info(f"Scanning {len(stocks)} stocks (market: {market or 'ALL'})")

        # Kiwoom API 클라이언트 초기화
        kiwoom_api = None
        suspended_stocks: Dict[str, str] = {}  # 거래정지 종목 목록

        try:
            from src.kiwoom.rest_api import KiwoomRestAPI
            kiwoom_api = KiwoomRestAPI.from_env()
            await kiwoom_api.issue_token()
            logger.info("Kiwoom API token issued successfully")

            # 거래정지 종목 목록 조회
            suspended_stocks = await self._get_suspended_stocks(kiwoom_api)
            logger.info(f"거래정지 종목 {len(suspended_stocks)}개 필터링 대상")

        except Exception as e:
            logger.warning(f"Kiwoom API initialization failed: {e}, using DB data only")
            suspended_stocks = {}

        # 점수 계산
        results = []
        scanned_count = 0
        suspended_count = 0  # 거래정지 제외 카운트

        for stock in stocks[:limit]:
            try:
                scanned_count += 1

                # 거래정지 종목 필터링 (신규)
                if kiwoom_api and self._is_trading_suspended(stock.ticker, suspended_stocks):
                    suspended_count += 1
                    state = suspended_stocks.get(stock.ticker, "알 수 없음")
                    logger.info(f"거래정지 종목 제외: {stock.ticker} {stock.name} ({state})")
                    continue

                # Kiwoom API에서 실시간 일봉 데이터 조회 시도
                api_prices = None
                api_flow = None

                if kiwoom_api:
                    try:
                        # 일봉 데이터 조회 (ka10081)
                        chart_data = await kiwoom_api.get_stock_daily_chart(
                            ticker=stock.ticker,
                            days=20,
                            adjusted_price=True
                        )

                        if chart_data and len(chart_data) >= 5:
                            # Kiwoom API 데이터를 DailyPrice 형식으로 변환
                            api_prices = self._convert_chart_to_daily_prices(stock.ticker, chart_data)
                            logger.debug(f"Kiwoom API data retrieved for {stock.ticker}: {len(api_prices)} days")

                            # 일별거래상세 조회 (ka10015) - 외국인/기관 순매수
                            trade_data = await kiwoom_api.get_daily_trade_detail(stock.ticker)
                            if trade_data:
                                api_flow = self._convert_trade_to_flow(trade_data)
                                logger.debug(f"Trade detail retrieved for {stock.ticker}")

                    except Exception as api_error:
                        logger.debug(f"Kiwoom API call failed for {stock.ticker}: {api_error}")

                # API 데이터 없으면 DB에서 조회 (fallback)
                if not api_prices:
                    api_prices = self._get_recent_prices(db, stock.ticker, days=20)
                    if api_prices:
                        logger.debug(f"Using DB data for {stock.ticker}")

                if not api_prices or len(api_prices) < 5:
                    logger.debug(f"Insufficient price data for {stock.ticker}")
                    continue

                # API 데이터 없으면 DB에서 수급 데이터 조회 (fallback)
                if not api_flow:
                    api_flow = self._get_flow_data(db, stock.ticker, days=5)

                # 점수 계산 (DB 세션 전달하여 섹터 모멘텀 계산)
                score_result = calculate_daytrading_score(stock, api_prices, api_flow, db)

                # 결과 추가
                results.append(score_result)

                # DB 저장
                await self._save_signal(db, score_result, api_prices[0])

                # Rate Limiting 방지
                if scanned_count % 10 == 0:
                    import asyncio
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error scanning {stock.ticker}: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        # Kiwoom API 정리
        if kiwoom_api:
            try:
                await kiwoom_api.close()
            except Exception as e:
                logger.debug(f"Error closing Kiwoom API: {e}")

        # 캐시 무효화
        await self._invalidate_cache()

        logger.info(
            f"스캔 완료: 전체 {scanned_count}개 중 "
            f"거래정지 {suspended_count}개 제외, "
            f"결과 {len(results)}개"
        )
        return results

    # ==================== 거래정지 종목 필터링 ====================

    async def _get_suspended_stocks(self, kiwoom_api) -> Dict[str, str]:
        """
        거래정지 종목 목록 조회 (캐싱 활용)

        Args:
            kiwoom_api: KiwoomRestAPI 인스턴스

        Returns:
            {종목코드: 종목상태} 딕셔너리
        """
        import time

        current_time = time.time()

        # 캐시 유효성 확인
        if (self._suspended_cache_time and
            current_time - self._suspended_cache_time < self._SUSPENDED_CACHE_TTL):
            logger.debug("거래정지 종목 캐시 사용")
            return self._suspended_stocks_cache

        # API 호출로 갱신
        try:
            suspended = await kiwoom_api.get_suspended_stocks("ALL")
            self._suspended_stocks_cache = suspended
            self._suspended_cache_time = current_time
            return suspended
        except Exception as e:
            logger.warning(f"거래정지 종목 조회 실패: {e}, 캐시된 데이터 사용")
            return self._suspended_stocks_cache

    @staticmethod
    def _is_trading_suspended(
        ticker: str,
        suspended_stocks: Dict[str, str]
    ) -> bool:
        """
        종목이 거래정지인지 확인

        Args:
            ticker: 종목코드
            suspended_stocks: 거래정지 종목 목록

        Returns:
            거래정지 여부
        """
        return ticker in suspended_stocks

    async def _invalidate_cache(self) -> None:
        """캐시 무효화"""
        try:
            from src.cache.cache_client import get_cache
            cache = await get_cache()
            if cache:
                deleted = await cache.clear_pattern("daytrading:signals:*")
                if deleted > 0:
                    logger.info(f"Invalidated {deleted} daytrading signal cache entries")
        except ImportError as e:
            logger.debug(f"Cache module not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

    # ==================== 종목 및 가격 데이터 조회 ====================

    def _get_stocks(self, db: Optional[Session], market: Optional[str]) -> List[Stock]:
        """종목 리스트 조회"""
        # 기존 방식 사용 (SQLAlchemy 1.x/2.x 호환)
        from src.database.models import Stock as StockModel

        if db is None:
            return []

        # SQLAlchemy Core 방식으로 쿼리 (None 값 처리)
        # 조건: is_etf가 False이거나 None인 것만 선택
        conditions = []
        for field in [StockModel.is_etf, StockModel.is_admin, StockModel.is_spac,
                       StockModel.is_bond, StockModel.is_excluded_etf]:
            conditions.append((field == False) | (field.is_(None)))

        from sqlalchemy import and_
        query = select(StockModel).where(and_(*conditions))

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

        # UTC timezone 대신 date만 비교 (시간대 문제 해결)
        # 최근 days일 전 날짜 계산
        from datetime import date, timedelta

        # 우선 최근 데이터 조회 (최근 90일 이내)
        since_date = date.today() - timedelta(days=days * 2)

        query = select(DailyPriceModel).where(
            DailyPriceModel.ticker == ticker,
            DailyPriceModel.date >= since_date
        ).order_by(DailyPriceModel.date.desc()).limit(days)

        result = db.execute(query)
        prices = list(result.scalars().all())

        # 최근 데이터가 없으면 전체 데이터에서 최근 N개 조회 (fallback)
        if not prices:
            query_all = select(DailyPriceModel).where(
                DailyPriceModel.ticker == ticker
            ).order_by(DailyPriceModel.date.desc()).limit(days)

            result_all = db.execute(query_all)
            prices = list(result_all.scalars().all())

            if prices:
                latest = prices[0].date if prices else None
                oldest = prices[-1].date if len(prices) > 0 else None
                logger.info(f"[FALLBACK] Using older data for {ticker}: {oldest} to {latest}")

        # 디버깅: 조회된 데이터 로그
        if prices:
            latest = prices[0].date if prices else None
            oldest = prices[-1].date if len(prices) > 0 else None
            logger.debug(f"Retrieved {len(prices)} prices for {ticker}: {oldest} to {latest}")
        else:
            logger.debug(f"No prices found for {ticker}")

        return prices

    def _get_flow_data(self, db: Session, ticker: str, days: int = 5) -> Any:
        """
        실제 수급 데이터 조회 (DailyPrice 테이블 활용)

        Args:
            db: DB 세션
            ticker: 종목 코드
            days: 조회 기간 (일)

        Returns:
            Flow 데이터 객체 (foreign_net_buy, inst_net_buy)
        """
        from src.repositories.daily_price_repository import DailyPriceRepository

        price_repo = DailyPriceRepository(db)
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days * 2)  # 주말 등을 고려해 여유있게

        try:
            prices = price_repo.get_by_ticker_and_date_range(ticker, start_date, end_date)

            if not prices or len(prices) < 3:
                # 데이터 부족 시 Mock 반환
                return self._get_mock_flow_data(ticker)

            # Flow 데이터 객체 생성
            class FlowData:
                def __init__(self, foreign_net: int, inst_net: int):
                    self.foreign_net_buy = foreign_net
                    self.inst_net_buy = inst_net

            # 최근 N일 합계 계산 (최신 데이터 순)
            recent_prices = prices[-days:] if len(prices) >= days else prices
            total_foreign = sum(p.foreign_net_buy or 0 for p in recent_prices)
            total_inst = sum(p.inst_net_buy or 0 for p in recent_prices)

            return FlowData(total_foreign, total_inst)

        except Exception as e:
            logger.warning(f"Error fetching flow data for {ticker}: {e}, using mock")
            return self._get_mock_flow_data(ticker)

    def _get_mock_flow_data(self, ticker: str) -> Any:
        """Mock 수급 데이터 (fallback용)"""
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
            from datetime import date

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

            # signal_date: 오늘 날짜
            today = date.today()

            if existing:
                # 업데이트
                existing.score = score_result.total_score
                existing.grade = score_result.grade
                existing.checks = checks_json
                existing.entry_price = current_price.close_price
                existing.target_price = int(current_price.close_price * 1.05)
                existing.stop_loss = int(current_price.close_price * 0.97)
                existing.signal_date = today
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
                    signal_date=today,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(new_signal)

            db.commit()
            logger.debug(f"Saved signal for {score_result.ticker}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving signal for {score_result.ticker}: {e}")

    # ==================== Kiwoom API 데이터 변환 ====================

    def _convert_chart_to_daily_prices(
        self,
        ticker: str,
        chart_data: List[Dict]
    ) -> List[DailyPrice]:
        """
        Kiwoom API 일봉 차트 데이터를 DailyPrice 객체 리스트로 변환

        Args:
            ticker: 종목코드
            chart_data: Kiwoom API에서 반환한 일봉 차트 데이터

        Returns:
            DailyPrice 객체 리스트
        """
        from src.database.models import DailyPrice as DailyPriceModel
        from datetime import datetime

        result = []
        for item in chart_data:
            # 날짜 변환 (YYYYMMDD -> YYYY-MM-DD)
            date_str = item.get("date", "")
            if len(date_str) == 8:
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                formatted_date = date_str

            # 날짜를 date 객체로 변환
            try:
                date_obj = datetime.strptime(formatted_date, "%Y-%m-%d").date()
            except ValueError:
                date_obj = datetime.now().date()

            # 가격 데이터 확인
            close_price = item.get("close", 0)

            # DailyPrice 유사 객체 생성
            class PriceData:
                def __init__(self, ticker, date_obj, open_price, high_price, low_price, close_price, volume):
                    self.ticker = ticker
                    self.date = date_obj
                    self.open_price = open_price
                    self.high_price = high_price
                    self.low_price = low_price
                    self.close_price = close_price
                    self.volume = volume
                    self.foreign_net_buy = 0
                    self.inst_net_buy = 0

            result.append(PriceData(
                ticker=ticker,
                date_obj=date_obj,
                open_price=item.get("open", 0),
                high_price=item.get("high", 0),
                low_price=item.get("low", 0),
                close_price=close_price,
                volume=item.get("volume", 0),
            ))

        # 디버깅용 로그
        if result:
            logger.debug(f"Converted {len(result)} price records for {ticker}, latest close: {result[0].close_price}")

        return result

    def _convert_trade_to_flow(self, trade_data: List[Dict]) -> Any:
        """
        Kiwoom API 일별거래상세 데이터를 Flow 객체로 변환

        Args:
            trade_data: Kiwoom API에서 반환한 일별거래상세 데이터

        Returns:
            Flow 데이터 객체
        """
        # 최근 5일 합계 계산
        recent_data = trade_data[-5:] if len(trade_data) >= 5 else trade_data

        total_foreign = sum(d.get("foreign_net_buy", 0) for d in recent_data)
        total_inst = sum(d.get("inst_net_buy", 0) for d in recent_data)

        class FlowData:
            def __init__(self, foreign_net: int, inst_net: int):
                self.foreign_net_buy = foreign_net
                self.inst_net_buy = inst_net

        return FlowData(total_foreign, total_inst)
