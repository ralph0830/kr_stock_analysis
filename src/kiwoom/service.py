"""
키움 Realtime Service 구현

REST API + WebSocket을 통합한 서비스를 제공합니다.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable

from src.kiwoom.base import (
    KiwoomConfig,
    KiwoomEventType,
    RealtimePrice,
    IKiwoomBridge,
)
from src.kiwoom.websocket import KiwoomWebSocket
from src.kiwoom.rest_api import KiwoomRestAPI


logger = logging.getLogger(__name__)


class KiwoomRealtimeService:
    """
    키움 Realtime Service

    REST API + WebSocket + Redis 발행을 통합합니다.
    """

    def __init__(
        self,
        bridge: IKiwoomBridge,
        redis_client: Optional[Any] = None,
        rest_api: Optional[KiwoomRestAPI] = None,
    ):
        """
        초기화

        Args:
            bridge: 키움 Bridge 인스턴스
            redis_client: Redis 클라이언트 (선택)
            rest_api: REST API 클라이언트 (선택)
        """
        self._bridge = bridge
        self._redis_client = redis_client
        self._redis_enabled = False
        self._running = False
        self._rest_api = rest_api

    @classmethod
    def from_config(cls, config: KiwoomConfig) -> 'KiwoomRealtimeService':
        """설정에서 Service 생성"""
        if config.use_mock:
            raise RuntimeError("Mock mode is no longer supported. Please disable use_mock in your config.")

        # 실제 Kiwoom WebSocket 생성
        logger.info("Using KiwoomWebSocket (Real Trading)")
        bridge = KiwoomWebSocket(config, debug_mode=config.debug_mode)

        # REST API 클라이언트 생성
        rest_api = KiwoomRestAPI(config)
        logger.info("KiwoomRestAPI created")

        return cls(bridge, rest_api=rest_api)

    # ==================== 라이프사이클 관리 ====================

    async def start(self) -> None:
        """
        Service 시작

        Bridge 연결을 시작합니다.
        """
        if self._running:
            logger.warning("Service already running")
            return

        success = await self._bridge.connect()
        if not success:
            raise RuntimeError("Failed to connect to Kiwoom API")

        self._running = True
        logger.info("Kiwoom Realtime Service started")

    async def stop(self) -> None:
        """
        Service 중지

        Bridge 연결을 해제합니다.
        """
        if not self._running:
            return

        await self._bridge.disconnect()

        # REST API 클라이언트 종료
        if self._rest_api:
            await self._rest_api.close()

        self._running = False
        logger.info("Kiwoom Realtime Service stopped")

    def is_running(self) -> bool:
        """Service 실행 상태 확인"""
        return self._running

    @property
    def rest_api(self) -> Optional[KiwoomRestAPI]:
        """REST API 클라이언트 가져오기"""
        return self._rest_api

    # ==================== 구독 관리 ====================

    async def subscribe(self, ticker: str) -> bool:
        """
        종목 구독

        Args:
            ticker: 종목코드 (6자리)

        Returns:
            구독 성공 여부
        """
        if not self._running:
            logger.warning("Cannot subscribe: service not running")
            return False

        result = await self._bridge.subscribe_realtime(ticker)
        if result:
            logger.info(f"Subscribed to {ticker}")
        else:
            logger.error(f"Failed to subscribe to {ticker}")

        return result

    async def subscribe_many(self, tickers: List[str]) -> List[bool]:
        """
        여러 종목 구독

        Args:
            tickers: 종목코드 리스트

        Returns:
            각 종목별 구독 결과 리스트
        """
        results = []
        for ticker in tickers:
            result = await self.subscribe(ticker)
            results.append(result)
        return results

    async def unsubscribe(self, ticker: str) -> bool:
        """
        종목 구독 해제

        Args:
            ticker: 종목코드

        Returns:
            해제 성공 여부
        """
        result = await self._bridge.unsubscribe_realtime(ticker)
        if result:
            logger.info(f"Unsubscribed from {ticker}")
        return result

    def get_subscribed_tickers(self) -> List[str]:
        """현재 구독 중인 종목 리스트"""
        return self._bridge.get_subscribe_list()

    async def subscribe_index(self, code: str) -> bool:
        """
        업종지수 구독

        Args:
            code: 업종코드 (001: KOSPI, 201: KOSDAQ)

        Returns:
            구독 성공 여부
        """
        if not self._running:
            logger.warning("Cannot subscribe index: service not running")
            return False

        result = await self._bridge.subscribe_index(code)
        if result:
            logger.info(f"Subscribed to index {code}")
        else:
            logger.error(f"Failed to subscribe to index {code}")

        return result

    async def unsubscribe_index(self, code: str) -> bool:
        """
        업종지수 구독 해제

        Args:
            code: 업종코드

        Returns:
            해제 성공 여부
        """
        result = await self._bridge.unsubscribe_index(code)
        if result:
            logger.info(f"Unsubscribed from index {code}")
        return result

    def get_subscribed_indices(self) -> List[str]:
        """현재 구독 중인 지수 리스트"""
        return self._bridge.get_index_list()

    # ==================== 이벤트 핸들러 관리 ====================

    def register_event_handler(
        self,
        event_type: KiwoomEventType,
        callback: Callable,
    ) -> None:
        """
        이벤트 핸들러 등록

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        self._bridge.register_event(event_type, callback)
        logger.debug(f"Registered handler for {event_type}")

    def unregister_event_handler(
        self,
        event_type: KiwoomEventType,
        callback: Callable,
    ) -> None:
        """
        이벤트 핸들러 해제

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        self._bridge.unregister_event(event_type, callback)
        logger.debug(f"Unregistered handler for {event_type}")

    # ==================== Redis 발행 ====================

    def enable_redis_publishing(self) -> None:
        """Redis 발행 활성화"""
        if self._redis_client is None:
            logger.warning("Redis client not configured")
            return

        self._redis_enabled = True

        # 실시간 데이터 이벤트 핸들러 등록
        self._bridge.register_event(
            KiwoomEventType.RECEIVE_REAL_DATA,
            self._publish_to_redis,
        )
        logger.info("Redis publishing enabled")

    def disable_redis_publishing(self) -> None:
        """Redis 발행 비활성화"""
        self._redis_enabled = False
        self._bridge.unregister_event(
            KiwoomEventType.RECEIVE_REAL_DATA,
            self._publish_to_redis,
        )
        logger.info("Redis publishing disabled")

    def _publish_to_redis(self, data: RealtimePrice) -> None:
        """
        실시간 데이터를 Redis로 발행

        Args:
            data: 실시간 가격 데이터
        """
        if not self._redis_enabled or self._redis_client is None:
            return

        try:
            channel = f"prices:{data.ticker}"
            message = {
                "ticker": data.ticker,
                "price": data.price,
                "change": data.change,
                "change_rate": data.change_rate,
                "volume": data.volume,
                "timestamp": data.timestamp,
            }

            # 비동기 발행
            asyncio.create_task(self._redis_client.publish(channel, message))
            logger.debug(f"Published to {channel}: {data.price}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

    # ==================== 상태 조회 ====================

    def get_status(self) -> Dict[str, Any]:
        """
        Service 상태 조회

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "running": self._running,
            "connected": self._bridge.is_connected(),
            "has_token": self._bridge.has_valid_token(),
            "subscribed_count": len(self._bridge.get_subscribe_list()),
            "redis_enabled": self._redis_enabled,
        }
