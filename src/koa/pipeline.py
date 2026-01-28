"""
실시간 데이터 파이프라인 관리자

KOA → Redis → WebSocket → 프론트엔드 흐름을 통합 관리합니다.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from src.koa.service import RealtimeDataService, RealtimeDataSubscriber
from src.koa.base import RealtimePrice
from src.koa.redis_publisher import RedisPublisher, MockRedisPublisher
from src.utils.logging_config import get_logger

# 기존 WebSocket 시스템 연동
try:
    from src.websocket.server import connection_manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    connection_manager = None

logger = get_logger(__name__)


class RealtimePipelineManager:
    """
    실시간 데이터 파이프라인 관리자

    KOA → Redis → WebSocket → 프론트엔드
    """

    def __init__(
        self,
        use_koa: bool = True,  # 실제 KOA 사용 여부
        use_redis: bool = True,  # Redis 사용 여부
        update_interval: float = 1.0
    ):
        """
        Args:
            use_koa: 실제 KOA 사용 (False면 Mock 사용)
            use_redis: Redis 사용 (False면 Mock Redis 사용)
            update_interval: 업데이트 간격 (초)
        """
        self._use_koa = use_koa
        self._use_redis = use_redis
        self._update_interval = update_interval
        self._running = False

        # 서비스들
        self._koa_service: Optional[RealtimeDataService] = None
        self._subscriber: Optional[RealtimeDataSubscriber] = None
        self._redis_publisher: Optional[RedisPublisher] = None

    async def start(self) -> bool:
        """
        파이프라인 시작

        Returns:
            시작 성공 여부
        """
        if self._running:
            logger.warning("RealtimePipelineManager already running")
            return True

        try:
            # 1. KOA 서비스 시작 (항상 생성 - Mock 또는 실제)
            logger.info(f"Starting KOA service (use_koa={self._use_koa})...")
            self._koa_service = RealtimeDataService(
                use_mock=not self._use_koa,
                update_interval=self._update_interval
            )

            if not await self._koa_service.start():
                logger.error("Failed to start KOA service")
                return False

            logger.info("KOA service started")

            # 2. Redis 발행자 시작
            if self._use_redis:
                logger.info("Starting Redis publisher...")

                # 환경 변수에서 Redis URL 가져오기
                import os
                redis_url = os.environ.get(
                    "REDIS_URL",
                    "redis://localhost:6380/0"
                )

                self._redis_publisher = RedisPublisher(
                    redis_url=redis_url
                )

                if not await self._redis_publisher.connect():
                    logger.warning("Failed to connect to Redis, using mock publisher")
                    self._redis_publisher = MockRedisPublisher()
                    await self._redis_publisher.connect()
            else:
                self._redis_publisher = MockRedisPublisher()
                await self._redis_publisher.connect()
                logger.info("Using Mock Redis publisher (use_redis=False)")

            # 3. 구독자 설정
            self._subscriber = RealtimeDataSubscriber(
                service=self._koa_service,
                redis_publisher=self._redis_publisher
            )

            # Redis 발행자 시작
            await self._subscriber.start_redis()

            # 4. WebSocket 브로드캐스트 핸들러 등록
            if WEBSOCKET_AVAILABLE:
                self._setup_websocket_handler()
            else:
                logger.warning("WebSocket not available")

            self._running = True
            logger.info("RealtimePipelineManager started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start RealtimePipelineManager: {e}")
            return False

    async def stop(self) -> None:
        """파이프라인 중지"""
        if not self._running:
            return

        self._running = False

        # 구독자 정리
        if self._subscriber:
            await self._subscriber.stop_redis()
            await self._subscriber.unsubscribe_all()

        # KOA 서비스 정지
        if self._koa_service:
            await self._koa_service.stop()

        # Redis 발행자 정지
        if self._redis_publisher:
            await self._redis_publisher.disconnect()

        logger.info("RealtimePipelineManager stopped")

    async def subscribe_tickers(self, tickers: List[str]) -> Dict[str, bool]:
        """
        종목 구독

        Args:
            tickers: 종목코드 리스트

        Returns:
            {ticker: success} 매핑
        """
        if not self._running:
            logger.warning("Pipeline not running")
            return {t: False for t in tickers}

        return await self._subscriber.subscribe_tickers(tickers)

    async def unsubscribe_all(self) -> None:
        """모든 구독 해제"""
        if self._subscriber:
            await self._subscriber.unsubscribe_all()

    def _setup_websocket_handler(self) -> None:
        """WebSocket 브로드캐스트 핸들러 설정"""
        if not connection_manager:
            return

        # KOA에서 받은 가격 데이터를 WebSocket으로 브로드캐스트
        def on_koa_price(ticker: str, price_data: RealtimePrice) -> None:
            """KOA 가격 → WebSocket 브로드캐스트"""
            try:
                # 현재 실행 중인 이벤트 루프가 있을 때만 브로드캐스트
                try:
                    loop = asyncio.get_running_loop()
                    # 이벤트 루프가 있으면 코루틴 스케줄링
                    asyncio.ensure_future(
                        self._broadcast_price(ticker, price_data),
                        loop=loop
                    )
                except RuntimeError:
                    # 이벤트 루프가 없으면 로그만 남기고 건너뜀
                    logger.debug("No event loop for WebSocket broadcast")
                logger.debug(f"Broadcast to WebSocket: {ticker} = {price_data.price}")

            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}")

        async def _broadcast_price(ticker: str, price_data: RealtimePrice) -> None:
            """가격 브로드캐스트 (비동기)"""
            try:
                await connection_manager.broadcast(
                    {
                        "type": "price_update",
                        "ticker": ticker,
                        "data": {
                            "price": price_data.price,
                            "change": price_data.change,
                            "change_rate": price_data.change_rate,
                            "volume": price_data.volume,
                        },
                        "timestamp": price_data.timestamp,
                    },
                    topic=f"price:{ticker}"
                )
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")

        # 비동기 함수를 인스턴스에 저장하여 참조 유지
        self._broadcast_price = _broadcast_price

        # KOA 서비스에 핸들러 등록
        if self._koa_service:
            self._koa_service.add_price_handler(on_koa_price)
            logger.info("WebSocket handler registered with KOA service")

    def get_stats(self) -> Dict[str, Any]:
        """
        파이프라인 상태 통계

        Returns:
            상태 정보
        """
        stats = {
            "running": self._running,
            "use_koa": self._use_koa,
            "use_redis": self._use_redis,
            "subscribed_tickers": [],
        }

        if self._subscriber:
            stats.update(self._subscriber.get_stats())

        return stats

    def is_running(self) -> bool:
        """파이프라인 실행 중 여부"""
        return self._running

    async def health_check(self) -> Dict[str, Any]:
        """
        헬스 체크

        Returns:
            각 컴포넌트 상태
        """
        health = {
            "pipeline": "running" if self._running else "stopped",
            "koa_service": "unknown",
            "redis_publisher": "unknown",
            "websocket": "available" if WEBSOCKET_AVAILABLE else "unavailable",
        }

        if self._koa_service:
            health["koa_service"] = "running" if self._koa_service.is_running() else "stopped"

        if self._redis_publisher:
            health["redis_publisher"] = "connected" if self._redis_publisher.is_connected() else "disconnected"

        return health


# 전역 파이프라인 관리자
_pipeline_manager: Optional[RealtimePipelineManager] = None


def get_pipeline_manager() -> Optional[RealtimePipelineManager]:
    """전역 파이프라인 관리자 반환"""
    return _pipeline_manager


async def init_pipeline_manager(
    use_koa: bool = True,
    use_redis: bool = True,
    tickers: List[str] = None,
    update_interval: float = 1.0
) -> RealtimePipelineManager:
    """
    전역 파이프라인 관리자 초기화

    Args:
        use_koa: 실제 KOA 사용 여부 (환경 변수에서 결정 가능)
        use_redis: Redis 사용 여부
        tickers: 초기 구독 종목 리스트
        update_interval: 업데이트 간격

    Returns:
        RealtimePipelineManager 인스턴스
    """
    global _pipeline_manager

    # 환경 변수 확인
    import os
    koa_app_key = os.environ.get("KIWOOM_APP_KEY")
    has_koa_key = bool(koa_app_key and koa_app_key != "your_koa_app_key")

    # KOA 키가 없으면 자동으로 Mock 모드
    if use_koa and not has_koa_key:
        logger.warning(
            "KIWOOM_APP_KEY not set or using default value. "
            "Falling back to Mock KOA mode."
        )
        use_koa = False

    # 관리자 생성
    _pipeline_manager = RealtimePipelineManager(
        use_koa=use_koa,
        use_redis=use_redis,
        update_interval=update_interval
    )

    # 시작
    if await _pipeline_manager.start():
        logger.info("Pipeline manager initialized successfully")

        # 초기 종목 구독
        if tickers:
            results = await _pipeline_manager.subscribe_tickers(tickers)
            logger.info(f"Initial subscriptions: {results}")
    else:
        logger.error("Failed to start pipeline manager")
        _pipeline_manager = None

    return _pipeline_manager


async def shutdown_pipeline_manager() -> None:
    """파이프라인 관리자 종료"""
    global _pipeline_manager

    if _pipeline_manager:
        await _pipeline_manager.stop()
        _pipeline_manager = None
        logger.info("Pipeline manager shutdown complete")
