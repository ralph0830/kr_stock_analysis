"""
Event Bus - Redis Pub/Sub 기반 이벤트 버스
서비스 간 비동기 이벤트 통신
"""

import json
import logging
import asyncio
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import redis.asyncio as redis

logger = logging.getLogger(__name__)


# Redis 연결 설정
REDIS_URL = "redis://localhost:6379/1"


@dataclass
class Event:
    """이벤트 기본 클래스"""
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    source: str

    def to_json(self) -> str:
        """JSON 직렬화"""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """JSON 역직렬화"""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class SignalEvent(Event):
    """시그널 이벤트"""
    ticker: str
    signal_type: str  # "vcp", "jongga_v2"
    score: int
    grade: str


@dataclass
class MarketUpdateEvent(Event):
    """마켓 업데이트 이벤트"""
    gate_status: str  # "GREEN", "YELLOW", "RED"
    score: int


class EventBus:
    """
    Redis Pub/Sub 기반 이벤트 버스

    - 이벤트 발행 (publish)
    - 이벤트 구독 (subscribe)
    - 핸들러 등록/실행
    """

    def __init__(self, redis_url: str = REDIS_URL):
        """
        Args:
            redis_url: Redis URL
        """
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.PubSub] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._listening = False

    async def connect(self):
        """Redis 연결"""
        self._redis = await redis.from_url(self.redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        logger.info("Event Bus connected to Redis")

    async def disconnect(self):
        """Redis 연결 해제"""
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("Event Bus disconnected")

    async def publish(self, channel: str, event: Event):
        """
        이벤트 발행

        Args:
            channel: 채널명
            event: 이벤트 객체
        """
        try:
            if not self._redis:
                await self.connect()

            message = event.to_json()
            await self._redis.publish(channel, message)
            logger.debug(f"Event published: {channel} - {event.event_type}")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def subscribe(self, channel: str, handler: Callable):
        """
        채널 구독 및 핸들러 등록

        Args:
            channel: 채널명
            handler: 이벤트 핸들러 함수
        """
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        logger.debug(f"Handler registered for channel: {channel}")

    async def start_listening(self):
        """이벤트 리스닝 시작"""
        if not self._pubsub:
            await self.connect()

        # 모든 채널 구독
        for channel in self._handlers.keys():
            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

        self._listening = True

        # 메시지 리스닝 루프
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                await self._handle_message(message)

    async def _handle_message(self, message: Dict[str, Any]):
        """
        수신한 메시지 처리

        Args:
            message: Redis PubSub 메시지
        """
        try:
            channel = message["channel"]
            data = message["data"]

            # 이벤트 역직렬화
            event = Event.from_json(data)

            # 등록된 핸들러 실행
            handlers = self._handlers.get(channel, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    async def stop_listening(self):
        """이벤트 리스닝 중지"""
        self._listening = False
        if self._pubsub:
            # 모든 채널 구독 해지
            for channel in self._handlers.keys():
                await self._pubsub.unsubscribe(channel)
        logger.info("Event Bus listening stopped")


# 전역 이벤트 버스 인스턴스
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """전역 이벤트 버스 인스턴스 반환"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus


async def publish_event(channel: str, event: Event):
    """
    이벤트 발행 헬퍼 함수

    Args:
        channel: 채널명
        event: 이벤트 객체
    """
    bus = await get_event_bus()
    await bus.publish(channel, event)


async def subscribe_event(channel: str, handler: Callable):
    """
    이벤트 구독 헬퍼 함수

    Args:
        channel: 채널명
        handler: 이벤트 핸들러
    """
    bus = await get_event_bus()
    await bus.subscribe(channel, handler)


# 이벤트 채널 상수
CHANNEL_SIGNAL_CREATED = "signals:created"
CHANNEL_SIGNAL_UPDATED = "signals:updated"
CHANNEL_MARKET_GATE = "market:gate"
CHANNEL_PRICE_UPDATE = "prices:update"


# 이벤트 생성 헬퍼 함수
def create_signal_event(
    ticker: str,
    signal_type: str,
    score: int,
    grade: str,
    source: str = "vcp-scanner"
) -> SignalEvent:
    """시그널 이벤트 생성"""
    return SignalEvent(
        event_type="signal.created",
        data={
            "ticker": ticker,
            "signal_type": signal_type,
        },
        timestamp=datetime.now().isoformat(),
        source=source,
        ticker=ticker,
        signal_type=signal_type,
        score=score,
        grade=grade,
    )


def create_market_update_event(
    gate_status: str,
    score: int,
    source: str = "market-analyzer"
) -> MarketUpdateEvent:
    """마켓 업데이트 이벤트 생성"""
    return MarketUpdateEvent(
        event_type="market.updated",
        data={
            "gate_status": gate_status,
            "score": score,
        },
        timestamp=datetime.now().isoformat(),
        source=source,
        gate_status=gate_status,
        score=score,
    )
