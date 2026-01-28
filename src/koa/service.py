"""
실시간 데이터 수신 서비스

KOA Bridge로부터 실시간 데이터를 수신하여 내부 포맷으로 변환합니다.
"""

import asyncio
import threading
from typing import Optional, List, Dict, Any, Callable, Union
from datetime import datetime, timezone
import logging
from queue import Queue

from src.koa.base import IKOABridge, KOAEventType, RealtimePrice
from src.koa.mock import MockKOABridge, AsyncMockKOABridge
from src.koa.redis_publisher import RedisPublisher, MockRedisPublisher
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RealtimeDataService:
    """
    실시간 데이터 서비스

    KOA 브리지를 통해 실시간 주식 데이터를 수신하고
    등록된 핸들러에게 전달합니다.
    """

    def __init__(
        self,
        bridge: Optional[IKOABridge] = None,
        use_mock: bool = True,
        update_interval: float = 1.0
    ):
        """
        Args:
            bridge: KOA 브리지 인스턴스 (None이면 Mock 생성)
            use_mock: Mock 사용 여부
            update_interval: 업데이트 간격 (초, Mock용)
        """
        self._bridge = bridge
        self._use_mock = use_mock
        self._update_interval = update_interval
        self._running = False
        self._subscribed_tickers: set = set()

        # 데이터 핸들러
        self._price_handlers: List[Callable[[str, RealtimePrice], None]] = []

        # 브리지 초기화
        if self._bridge is None:
            if use_mock:
                logger.info("Initializing with Mock KOA Bridge")
                self._bridge = MockKOABridge(
                    auto_update=True,
                    update_interval=update_interval
                )
            else:
                # 실제 KOA 연결 (Windows 필요)
                try:
                    from src.koa.windows import WindowsKOABridge
                    self._bridge = WindowsKOABridge()
                    logger.info("Initialized with Windows KOA Bridge")
                except ImportError:
                    logger.warning("Windows KOA not available, falling back to Mock")
                    self._bridge = MockKOABridge(
                        auto_update=True,
                        update_interval=update_interval
                    )
                    self._use_mock = True

    async def start(self) -> bool:
        """
        서비스 시작

        Returns:
            시작 성공 여부
        """
        if self._running:
            logger.warning("RealtimeDataService already running")
            return True

        try:
            # 브리지 연결
            if asyncio.iscoroutinefunction(self._bridge.connect):
                connected = await self._bridge.connect()
            else:
                connected = self._bridge.connect()

            if not connected:
                logger.error("Failed to connect to KOA bridge")
                return False

            # 로그인 (환경 변수에서 계정 정보 가져오기)
            user_id = self._get_env("KOA_USER_ID", "test_user")
            password = self._get_env("KOA_PASSWORD", "test1234")

            if asyncio.iscoroutinefunction(self._bridge.login):
                logged_in = await self._bridge.login(user_id, password)
            else:
                logged_in = self._bridge.login(user_id, password)

            if not logged_in:
                logger.error("Failed to login to KOA")
                return False

            # 이벤트 핸들러 등록
            self._bridge.register_event(
                KOAEventType.RECEIVE_REAL_DATA,
                self._on_realtime_data
            )
            self._bridge.register_event(
                KOAEventType.EVENT_CONNECT,
                self._on_connect
            )
            self._bridge.register_event(
                KOAEventType.RECEIVE_DISCONNECTED,
                self._on_disconnect
            )

            self._running = True
            logger.info("RealtimeDataService started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting RealtimeDataService: {e}")
            return False

    async def stop(self) -> None:
        """서비스 중지"""
        if not self._running:
            return

        self._running = False

        # 모든 구독 해제
        for ticker in list(self._subscribed_tickers):
            await self.unsubscribe(ticker)

        # 브리지 연결 해제
        if asyncio.iscoroutinefunction(self._bridge.disconnect):
            await self._bridge.disconnect()
        else:
            self._bridge.disconnect()

        logger.info("RealtimeDataService stopped")

    async def subscribe(self, ticker: str) -> bool:
        """
        종목 실시간 데이터 구독

        Args:
            ticker: 종목코드

        Returns:
            구독 성공 여부
        """
        if not self._running:
            logger.warning("Service not running, cannot subscribe")
            return False

        ticker = ticker.zfill(6)

        if ticker in self._subscribed_tickers:
            logger.debug(f"Already subscribed to {ticker}")
            return True

        try:
            if asyncio.iscoroutinefunction(self._bridge.subscribe_realtime):
                result = await self._bridge.subscribe_realtime(ticker)
            else:
                result = self._bridge.subscribe_realtime(ticker)

            if result:
                self._subscribed_tickers.add(ticker)
                logger.info(f"Subscribed to {ticker}")
            return result

        except Exception as e:
            logger.error(f"Error subscribing to {ticker}: {e}")
            return False

    async def unsubscribe(self, ticker: str) -> bool:
        """
        종목 실시간 데이터 구독 해제

        Args:
            ticker: 종목코드

        Returns:
            해제 성공 여부
        """
        ticker = ticker.zfill(6)

        if ticker not in self._subscribed_tickers:
            return True

        try:
            if asyncio.iscoroutinefunction(self._bridge.unsubscribe_realtime):
                result = await self._bridge.unsubscribe_realtime(ticker)
            else:
                result = self._bridge.unsubscribe_realtime(ticker)

            if result:
                self._subscribed_tickers.discard(ticker)
                logger.info(f"Unsubscribed from {ticker}")
            return result

        except Exception as e:
            logger.error(f"Error unsubscribing from {ticker}: {e}")
            return False

    def add_price_handler(
        self,
        handler: Callable[[str, RealtimePrice], None]
    ) -> None:
        """
        가격 업데이트 핸들러 추가

        Args:
            handler: 가격 데이터를 받을 콜백 함수
                     (ticker, price_data) -> None
        """
        self._price_handlers.append(handler)
        logger.debug(f"Added price handler, total: {len(self._price_handlers)}")

    def remove_price_handler(
        self,
        handler: Callable[[str, RealtimePrice], None]
    ) -> None:
        """가격 업데이트 핸들러 제거"""
        if handler in self._price_handlers:
            self._price_handlers.remove(handler)
            logger.debug(f"Removed price handler, total: {len(self._price_handlers)}")

    def get_subscribed_tickers(self) -> List[str]:
        """현재 구독 중인 종목 리스트"""
        return list(self._subscribed_tickers)

    def is_running(self) -> bool:
        """서비스 실행 중 여부"""
        return self._running

    def is_mock(self) -> bool:
        """Mock 모드 사용 중 여부"""
        return self._use_mock

    # 이벤트 핸들러

    def _on_realtime_data(self, ticker: str, price_data: Any) -> None:
        """
        실시간 데이터 수신 처리

        KOA 포맷을 내부 RealtimePrice 포맷으로 변환하여
        등록된 핸들러들에게 전달합니다.
        """
        try:
            # 이미 RealtimePrice 객체면 그대로 사용
            if isinstance(price_data, RealtimePrice):
                formatted_data = price_data
            else:
                # KOA 포맷을 변환
                formatted_data = self._format_price_data(ticker, price_data)

            # 등록된 핸들러들에게 전달
            for handler in self._price_handlers:
                try:
                    handler(ticker, formatted_data)
                except Exception as e:
                    logger.error(f"Error in price handler: {e}")

            logger.debug(
                f"Price update: {ticker} = {formatted_data.price} "
                f"({formatted_data.change_rate:+.2f}%)"
            )

        except Exception as e:
            logger.error(f"Error processing realtime data: {e}")

    def _on_connect(self, connected: bool) -> None:
        """연결 완료 이벤트"""
        if connected:
            logger.info("KOA Bridge connected")
        else:
            logger.error("KOA Bridge connection failed")

    def _on_disconnect(self) -> None:
        """연결 해제 이벤트"""
        logger.warning("KOA Bridge disconnected")
        self._running = False

    def _format_price_data(self, ticker: str, raw_data: Any) -> RealtimePrice:
        """
        KOA 원시 데이터를 RealtimePrice 포맷으로 변환

        Args:
            ticker: 종목코드
            raw_data: KOA에서 받은 원시 데이터

        Returns:
            RealtimePrice 객체
        """
        if isinstance(raw_data, dict):
            return RealtimePrice(
                ticker=ticker,
                price=float(raw_data.get("price", 0)),
                change=float(raw_data.get("change", 0)),
                change_rate=float(raw_data.get("change_rate", 0)),
                volume=int(raw_data.get("volume", 0)),
                bid_price=float(raw_data.get("bid_price", 0)),
                ask_price=float(raw_data.get("ask_price", 0)),
                timestamp=raw_data.get(
                    "timestamp",
                    datetime.now(timezone.utc).isoformat()
                ),
            )
        else:
            # 기본값 반환
            return RealtimePrice(
                ticker=ticker,
                price=0.0,
                change=0.0,
                change_rate=0.0,
                volume=0,
                bid_price=0.0,
                ask_price=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        """환경 변수 가져오기"""
        import os
        return os.environ.get(key, default)


class RealtimeDataSubscriber:
    """
    실시간 데이터 구독자 관리

    여러 종목의 실시간 데이터를 구독하고
    Redis/WS 브로드캐스트로 전달합니다.

    스레드 안전한 Redis 발행을 위해 내부 큐를 사용합니다.
    """

    def __init__(
        self,
        service: RealtimeDataService,
        redis_publisher: Optional[Union[RedisPublisher, MockRedisPublisher]] = None
    ):
        """
        Args:
            service: RealtimeDataService 인스턴스
            redis_publisher: Redis 발행자 (선택 사항, 없으면 Mock 사용)
        """
        self._service = service
        self._redis_publisher = redis_publisher or MockRedisPublisher()

        # 스레드 안전한 큐 (백그라운드 스레드에서의 발행 요청 처리용)
        self._publish_queue: Queue = Queue()
        self._publish_task: Optional[asyncio.Task] = None
        self._queue_lock = threading.Lock()

        # 서비스에 핸들러 등록
        self._service.add_price_handler(self._on_price_update)

    async def start_redis(self) -> bool:
        """
        Redis 발행자 시작

        Returns:
            시작 성공 여부
        """
        if hasattr(self._redis_publisher, 'connect'):
            result = await self._redis_publisher.connect()
            if result:
                # 큐 처리 태스크 시작
                self._publish_task = asyncio.create_task(self._process_publish_queue())
            return result
        # MockRedisPublisher도 큐 처리 시작
        self._publish_task = asyncio.create_task(self._process_publish_queue())
        return True

    async def stop_redis(self) -> None:
        """Redis 발행자 중지"""
        # 큐 처리 태스크 중지
        if self._publish_task:
            self._publish_task.cancel()
            try:
                await self._publish_task
            except asyncio.CancelledError:
                pass
            self._publish_task = None

        if hasattr(self._redis_publisher, 'disconnect'):
            await self._redis_publisher.disconnect()

    async def subscribe_tickers(self, tickers: List[str]) -> Dict[str, bool]:
        """
        여러 종목 구독

        Args:
            tickers: 종목코드 리스트

        Returns:
            {ticker: success} 매핑
        """
        results = {}
        for ticker in tickers:
            result = await self._service.subscribe(ticker)
            results[ticker] = result
        return results

    async def unsubscribe_all(self) -> None:
        """모든 구독 해제"""
        tickers = self._service.get_subscribed_tickers()
        for ticker in tickers:
            await self._service.unsubscribe(ticker)

    def _on_price_update(
        self,
        ticker: str,
        price_data: RealtimePrice
    ) -> None:
        """
        가격 업데이트 처리

        백그라운드 스레드에서 호출되어도 안전하게 큐에 넣습니다.
        """
        # 스레드 안전하게 큐에 추가
        with self._queue_lock:
            self._publish_queue.put((ticker, price_data))
        logger.debug(f"Queued price update for {ticker}")

    async def _process_publish_queue(self) -> None:
        """
        발행 큐 처리 (비동기 태스크)

        큐에 쌓인 가격 업데이트를 순차적으로 Redis에 발행합니다.
        """
        while True:
            try:
                # 큐에서 항목 가져오기 (비차단 방식)
                try:
                    ticker, price_data = await asyncio.to_thread(
                        self._publish_queue.get, timeout=0.1
                    )
                except Exception:
                    # 타임아웃 시 계속 진행
                    await asyncio.sleep(0.01)
                    continue

                # Redis에 발행
                await self._publish_to_redis(ticker, price_data)

                # 큐 항목 마크
                with self._queue_lock:
                    self._publish_queue.task_done()

            except asyncio.CancelledError:
                # 태스크 취소 시 종료
                logger.info("Publish queue processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing publish queue: {e}")
                await asyncio.sleep(0.1)

    async def _publish_to_redis(
        self,
        ticker: str,
        price_data: RealtimePrice
    ) -> None:
        """Redis에 실시간 데이터 발행"""
        if self._redis_publisher:
            try:
                success = await self._redis_publisher.publish_price(ticker, price_data)
                if not success:
                    logger.warning(f"Failed to publish {ticker} to Redis")
            except Exception as e:
                logger.error(f"Error publishing to Redis: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        통계 정보

        Returns:
            서비스 및 발행자 통계
        """
        stats = {
            "service_running": self._service.is_running(),
            "service_mock": self._service.is_mock(),
            "subscribed_tickers": self._service.get_subscribed_tickers(),
            "queue_size": self._publish_queue.qsize(),
        }

        if hasattr(self._redis_publisher, 'get_stats'):
            stats["redis"] = self._redis_publisher.get_stats()
        elif hasattr(self._redis_publisher, 'get_publish_count'):
            stats["mock_publish_count"] = self._redis_publisher.get_publish_count()

        return stats
