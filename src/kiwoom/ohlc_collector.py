"""
키움 WebSocket 기반 실시간 OHLC 수집기

실시간 체결 데이터를 수집하여 OHLC 형태로 집계하고 데이터베이스에 저장합니다.

Kiwoom WebSocket 0B TR (주식체결) 필드:
- 10: 현재가 (체결가)
- 13: 누적거래량
- 20: 체결시간 (HHMMSS)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Set, Optional, List, Callable
import logging

from src.kiwoom.websocket import KiwoomWebSocket
from src.kiwoom.base import KiwoomConfig, KiwoomEventType, RealtimePrice
from src.database.session import get_db_session
from src.repositories.daily_price_repository import DailyPriceRepository
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OHLCBar:
    """실시간 OHLC 바 데이터"""
    ticker: str
    date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    trade_count: int = 0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, price: float, volume: int) -> None:
        """새로운 체결가로 OHLC 업데이트"""
        self.high_price = max(self.high_price, price)
        self.low_price = min(self.low_price, price)
        self.close_price = price
        self.volume = volume  # 누적 거래량
        self.trade_count += 1
        self.last_update = datetime.now(timezone.utc)


@dataclass
class OHLCCollectorConfig:
    """OHLC 수집기 설정"""
    # 구독할 종목 리스트 (비어 있으면 전체 종목)
    tickers: List[str] = field(default_factory=list)

    # DB 저장 간격 (초)
    save_interval: int = 60

    # 최대 구독 종목 수 (Kiwoom 제한)
    max_subscriptions: int = 100

    # 일일 최대 저장 횟수 제한 (과도한 DB 저장 방지)
    max_saves_per_day: int = 1440  # 1분마다 저장 시 하루 1440회

    # 저장 횟수 리셋 시각 (자정)
    save_count: int = 0
    last_save_date: Optional[date] = None


class OHLCCollector:
    """
    실시간 OHLC 수집기

    Kiwoom WebSocket을 통해 실시간 체결 데이터를 수집하고
    OHLC 형태로 집계하여 데이터베이스에 저장합니다.
    """

    def __init__(
        self,
        config: KiwoomConfig,
        collector_config: Optional[OHLCCollectorConfig] = None,
    ):
        """
        초기화

        Args:
            config: 키움 API 설정
            collector_config: 수집기 설정 (선택)
        """
        self._config = config
        self._collector_config = collector_config or OHLCCollectorConfig()

        # WebSocket 클라이언트
        self._ws: Optional[KiwoomWebSocket] = None

        # 실시간 OHLC 바 캐시 (종목별)
        self._ohlc_bars: Dict[str, OHLCBar] = {}

        # 장 시작 가격 캐시 (시가 확인용)
        self._opening_prices: Dict[str, float] = {}

        # 실행 상태
        self._running: bool = False
        self._save_task: Optional[asyncio.Task] = None

        # 이벤트 핸들러
        self._on_trade_callbacks: List[Callable] = []

    @classmethod
    def from_env(cls, tickers: Optional[List[str]] = None) -> 'OHLCCollector':
        """환경변수에서 설정 로드"""
        config = KiwoomConfig.from_env()
        collector_config = OHLCCollectorConfig(
            tickers=tickers or [],
        )
        return cls(config, collector_config)

    async def start(self) -> bool:
        """
        수집기 시작

        Returns:
            시작 성공 여부
        """
        if self._running:
            logger.warning("OHLC 수집기 이미 실행 중")
            return True

        try:
            # WebSocket 클라이언트 생성
            self._ws = KiwoomWebSocket(self._config, debug_mode=self._config.debug_mode)

            # 실시간 데이터 이벤트 핸들러 등록
            self._ws.register_event(
                KiwoomEventType.RECEIVE_REAL_DATA,
                self._on_receive_real_data
            )

            # 연결
            if not await self._ws.connect():
                logger.error("WebSocket 연결 실패")
                return False

            # 종목 구독
            await self._subscribe_tickers()

            # 정기 저장 태스크 시작
            self._running = True
            self._save_task = asyncio.create_task(self._save_loop())

            logger.info(f"OHLC 수집기 시작 완료 - 구독 종목: {len(self._get_subscribe_tickers())}개")
            return True

        except Exception as e:
            logger.error(f"OHLC 수집기 시작 실패: {e}")
            return False

    async def stop(self) -> None:
        """수집기 중지"""
        if not self._running:
            return

        self._running = False

        # 정기 저장 태스크 중지
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass

        # 최종 저장
        await self._save_to_database()

        # WebSocket 연결 해제
        if self._ws:
            await self._ws.disconnect()

        logger.info("OHLC 수집기 중지 완료")

    def _get_subscribe_tickers(self) -> List[str]:
        """구독할 종목 리스트 반환"""
        if self._collector_config.tickers:
            return self._collector_config.tickers

        # 설정된 종목이 없으면 데이터베이스에서 가져오기
        # 기본적으로는 빈 리스트 반환 (명시적으로 설정 필요)
        return []

    async def _subscribe_tickers(self) -> None:
        """종목 구독"""
        tickers = self._get_subscribe_tickers()

        if not tickers:
            logger.warning("구독할 종목이 지정되지 않음")
            return

        # 최대 구독 수 제한
        tickers = tickers[:self._collector_config.max_subscriptions]

        for ticker in tickers:
            try:
                success = await self._ws.subscribe_realtime(ticker)
                if success:
                    logger.debug(f"종목 구독 완료: {ticker}")
                else:
                    logger.warning(f"종목 구독 실패: {ticker}")

                # 구독 간 딜레이 (Rate Limiting 방지)
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"종목 구독 중 오류 ({ticker}): {e}")

    async def _on_receive_real_data(self, price_data: RealtimePrice) -> None:
        """
        실시간 체결가 수신 처리

        Args:
            price_data: 실시간 가격 데이터
        """
        try:
            ticker = price_data.ticker
            current_price = price_data.price
            volume = price_data.volume
            timestamp_str = price_data.timestamp

            # 현재 날짜 (KST)
            now_kst = datetime.now(timezone.utc)
            today = now_kst.date()

            # 첫 거래면 시가로 설정
            if ticker not in self._opening_prices:
                self._opening_prices[ticker] = current_price
                logger.info(f"[{ticker}] 장 시작 시가 설정: {current_price:,}원")

            # OHLC 바 업데이트 또는 생성
            if ticker in self._ohlc_bars:
                # 기존 바 업데이트
                self._ohlc_bars[ticker].update(current_price, volume)
            else:
                # 새 바 생성
                self._ohlc_bars[ticker] = OHLCBar(
                    ticker=ticker,
                    date=today,
                    open_price=current_price,
                    high_price=current_price,
                    low_price=current_price,
                    close_price=current_price,
                    volume=volume,
                    trade_count=1,
                )

            # 콜백 호출
            for callback in self._on_trade_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(price_data)
                    else:
                        callback(price_data)
                except Exception as e:
                    logger.error(f"체결 데이터 콜백 오류: {e}")

            if self._config.debug_mode:
                logger.debug(
                    f"[{ticker}] {current_price:,}원 "
                    f"(H:{self._ohlc_bars[ticker].high_price:,}, "
                    f"L:{self._ohlc_bars[ticker].low_price:,}, "
                    f"V:{volume:,})"
                )

        except Exception as e:
            logger.error(f"실시간 데이터 처리 오류: {e}, price_data: {price_data}")

    async def _save_loop(self) -> None:
        """
        정기 저장 루프

        설정된 간격으로 OHLC 바를 데이터베이스에 저장합니다.
        """
        while self._running:
            try:
                # 설정된 간격 대기
                await asyncio.sleep(self._collector_config.save_interval)

                # 데이터베이스 저장
                await self._save_to_database()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"저장 루프 오류: {e}")

    async def _save_to_database(self) -> None:
        """
        OHLC 바를 데이터베이스에 저장

        저장 횟수 제한을 확인하여 과도한 DB 접근을 방지합니다.
        """
        if not self._ohlc_bars:
            return

        today = date.today()

        # 날짜가 바뀌면 저장 횟수 리셋
        if self._collector_config.last_save_date != today:
            self._collector_config.save_count = 0
            self._collector_config.last_save_date = today

        # 저장 횟수 제한 확인
        if self._collector_config.save_count >= self._collector_config.max_saves_per_day:
            logger.warning("일일 최대 저장 횟수 도달")
            return

        try:
            async with get_db_session() as db:
                repo = DailyPriceRepository(db)

                saved_count = 0
                for ticker, bar in self._ohlc_bars.items():
                    try:
                        # 장 시작 첫 거래인 경우 시가 업데이트
                        is_first = (bar.trade_count == 1)

                        repo.update_realtime_bar(
                            ticker=ticker,
                            trade_date=bar.date,
                            price=bar.close_price,
                            volume=bar.volume,
                            is_first_trade=is_first,
                        )
                        saved_count += 1

                    except Exception as e:
                        logger.error(f"DB 저장 실패 ({ticker}): {e}")

                db.commit()
                self._collector_config.save_count += saved_count

                if saved_count > 0:
                    logger.info(
                        f"OHLC 저장 완료: {saved_count}개 종목 "
                        f"(오늘 {self._collector_config.save_count}/{self._collector_config.max_saves_per_day}회)"
                    )

        except Exception as e:
            logger.error(f"데이터베이스 저장 오류: {e}")

    def add_trade_callback(self, callback: Callable) -> None:
        """
        체결 데이터 콜백 등록

        Args:
            callback: 콜백 함수 (RealtimePrice를 인자로 받음)
        """
        self._on_trade_callbacks.append(callback)

    def remove_trade_callback(self, callback: Callable) -> None:
        """체결 데이터 콜백 해제"""
        if callback in self._on_trade_callbacks:
            self._on_trade_callbacks.remove(callback)

    def get_current_ohlc(self, ticker: str) -> Optional[OHLCBar]:
        """
        현재 OHLC 바 조회

        Args:
            ticker: 종목 코드

        Returns:
            현재 OHLC 바 또는 None
        """
        return self._ohlc_bars.get(ticker)

    def get_all_ohlc(self) -> Dict[str, OHLCBar]:
        """전체 OHLC 바 반환"""
        return self._ohlc_bars.copy()

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._running

    def is_connected(self) -> bool:
        """WebSocket 연결 여부"""
        return self._ws.is_connected() if self._ws else False

    async def add_ticker(self, ticker: str) -> bool:
        """
        실시간 구독 종목 추가

        Args:
            ticker: 종목 코드

        Returns:
            추가 성공 여부
        """
        if self._ws and self._ws.is_connected():
            success = await self._ws.subscribe_realtime(ticker)
            if success and ticker not in self._collector_config.tickers:
                self._collector_config.tickers.append(ticker)
            return success
        return False

    async def remove_ticker(self, ticker: str) -> bool:
        """
        실시간 구독 종목 제거

        Args:
            ticker: 종목 코드

        Returns:
            제거 성공 여부
        """
        if self._ws and self._ws.is_connected():
            success = await self._ws.unsubscribe_realtime(ticker)
            if success and ticker in self._collector_config.tickers:
                self._collector_config.tickers.remove(ticker)
            # 메모리에서도 제거
            if ticker in self._ohlc_bars:
                del self._ohlc_bars[ticker]
            return success
        return False

    def get_subscribed_tickers(self) -> List[str]:
        """현재 구독 중인 종목 리스트"""
        return self._ws.get_subscribe_list() if self._ws else []


# ==================== 편의 함수 ====================

async def collect_ohlc_for_tickers(
    tickers: List[str],
    duration_seconds: Optional[int] = None,
    save_interval: int = 60,
) -> Dict[str, OHLCBar]:
    """
    지정된 종목들의 OHLC 수집

    Args:
        tickers: 수집할 종목 리스트
        duration_seconds: 수집 시간 (초, None이면 무한 대기)
        save_interval: DB 저장 간격 (초)

    Returns:
        수집된 OHLC 바 딕셔너리
    """
    collector = OHLCCollector.from_env(tickers=tickers)
    collector._collector_config.save_interval = save_interval

    try:
        # 수집기 시작
        if not await collector.start():
            logger.error("수집기 시작 실패")
            return {}

        # 지정된 시간 동안 수집
        if duration_seconds:
            await asyncio.sleep(duration_seconds)
        else:
            # 무한 대기 (외부에서 중지 필요)
            while collector.is_running():
                await asyncio.sleep(1)

        return collector.get_all_ohlc()

    finally:
        await collector.stop()


async def collect_ohlc_main(
    tickers: List[str],
    max_duration_seconds: int = 21600,  # 6시간 (장 시간)
) -> None:
    """
    메인 수집 함수 (Celery Task용)

    장 시작 시 호출하여 종료까지 실시간 OHLC를 수집합니다.

    Args:
        tickers: 수집할 종목 리스트
        max_duration_seconds: 최대 수집 시간 (초)
    """
    logger.info(f"OHLC 수집 시작 - 종목: {len(tickers)}개")

    collector = OHLCCollector.from_env(tickers=tickers)
    collector._collector_config.save_interval = 60  # 1분마다 저장

    try:
        if not await collector.start():
            logger.error("수집기 시작 실패")
            return

        # 지정된 시간 동안 수집 또는 종료 시까지 대기
        start_time = datetime.now(timezone.utc)

        while collector.is_running():
            await asyncio.sleep(10)

            # 최대 시간 확인
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= max_duration_seconds:
                logger.info("최대 수집 시간 도달, 수집 종료")
                break

    finally:
        await collector.stop()
        logger.info("OHLC 수집 종료")
