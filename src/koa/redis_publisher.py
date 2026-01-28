"""
Redis Pub/Sub 발행자

실시간 데이터를 Redis에 발행하여 여러 컨슈머가 구독할 수 있게 합니다.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import aioredis
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False

from src.koa.base import RealtimePrice
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RedisPublisher:
    """
    Redis Pub/Sub 발행자

    실시간 가격 데이터를 Redis에 발행합니다.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "realtime",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Args:
            redis_url: Redis 연결 URL
            prefix: 채널 접두사
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
        """
        self._redis_url = redis_url
        self._prefix = prefix
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._redis: Optional[aioredis.Redis] = None
        self._connected = False
        self._publish_count = 0
        self._error_count = 0

    async def connect(self) -> bool:
        """
        Redis 연결

        Returns:
            연결 성공 여부
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis module not available, using mock publisher")
            return False

        try:
            if hasattr(aioredis, "from_url"):
                self._redis = await aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                # 이전 버전 aioredis 호환성
                self._redis = await aioredis.create_redis_pool(self._redis_url)

            # 연결 테스트
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis publisher connected: {self._redis_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    async def disconnect(self) -> None:
        """연결 해제"""
        if self._redis:
            try:
                await self._redis.close()
                logger.info("Redis publisher disconnected")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._redis = None
                self._connected = False

    async def publish_price(
        self,
        ticker: str,
        price_data: RealtimePrice
    ) -> bool:
        """
        실시간 가격 발행

        Args:
            ticker: 종목코드
            price_data: 가격 데이터

        Returns:
            발행 성공 여부
        """
        return await self._publish(
            channel=self._get_price_channel(ticker),
            data=self._serialize_price(price_data)
        )

    async def publish_orderbook(
        self,
        ticker: str,
        orderbook_data: Dict[str, Any]
    ) -> bool:
        """
        호가 데이터 발행

        Args:
            ticker: 종목코드
            orderbook_data: 호가 데이터

        Returns:
            발행 성공 여부
        """
        return await self._publish(
            channel=self._get_orderbook_channel(ticker),
            data=json.dumps(orderbook_data, ensure_ascii=False)
        )

    async def publish_message(
        self,
        channel: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        일반 메시지 발행

        Args:
            channel: 채널명
            message: 메시지 데이터

        Returns:
            발행 성공 여부
        """
        return await self._publish(
            channel=f"{self._prefix}:{channel}",
            data=json.dumps(message, ensure_ascii=False)
        )

    async def _publish(
        self,
        channel: str,
        data: str
    ) -> bool:
        """
        Redis 발행 (재시도 로직 포함)

        Args:
            channel: 채널명
            data: 발행할 데이터

        Returns:
            발행 성공 여부
        """
        if not self._connected or not self._redis:
            logger.warning(f"Redis not connected, cannot publish to {channel}")
            self._error_count += 1
            return False

        for attempt in range(self._max_retries):
            try:
                # 발행
                result = await self._redis.publish(channel, data)

                self._publish_count += 1
                logger.debug(
                    f"Published to {channel}: {result} subscribers "
                    f"(total: {self._publish_count})"
                )
                return True

            except Exception as e:
                if attempt < self._max_retries - 1:
                    logger.warning(
                        f"Publish attempt {attempt + 1} failed: {e}, "
                        f"retrying in {self._retry_delay}s..."
                    )
                    await asyncio.sleep(self._retry_delay)
                else:
                    logger.error(
                        f"Failed to publish to {channel} after "
                        f"{self._max_retries} attempts: {e}"
                    )
                    self._error_count += 1
                    return False

        return False

    def _get_price_channel(self, ticker: str) -> str:
        """가격 채널명 생성"""
        return f"{self._prefix}:price:{ticker}"

    def _get_orderbook_channel(self, ticker: str) -> str:
        """호가 채널명 생성"""
        return f"{self._prefix}:orderbook:{ticker}"

    @staticmethod
    def _serialize_price(price_data: RealtimePrice) -> str:
        """가격 데이터 직렬화"""
        return json.dumps({
            "ticker": price_data.ticker,
            "price": price_data.price,
            "change": price_data.change,
            "change_rate": price_data.change_rate,
            "volume": price_data.volume,
            "bid_price": price_data.bid_price,
            "ask_price": price_data.ask_price,
            "timestamp": price_data.timestamp,
        }, ensure_ascii=False)

    def get_stats(self) -> Dict[str, Any]:
        """
        발행 통계

        Returns:
            통계 정보
        """
        return {
            "connected": self._connected,
            "publish_count": self._publish_count,
            "error_count": self._error_count,
            "success_rate": (
                self._publish_count / (self._publish_count + self._error_count)
                if (self._publish_count + self._error_count) > 0
                else 0
            ),
        }

    def is_connected(self) -> bool:
        """연결 상태"""
        return self._connected


class MockRedisPublisher:
    """
    Mock Redis 발행자

    테스트 및 Redis 없이 사용하기 위한 Mock 구현입니다.
    """

    def __init__(self):
        self._connected = False
        self._messages: Dict[str, List[Dict[str, Any]]] = {}
        self._publish_count = 0

    async def connect(self) -> bool:
        """모의 연결"""
        await asyncio.sleep(0.1)  # 연결 지연 시뮬레이션
        self._connected = True
        logger.info("Mock Redis publisher connected")
        return True

    async def disconnect(self) -> None:
        """모의 연결 해제"""
        self._connected = False
        logger.info("Mock Redis publisher disconnected")

    async def publish_price(
        self,
        ticker: str,
        price_data: RealtimePrice
    ) -> bool:
        """모의 가격 발행"""
        if not self._connected:
            return False

        import json
        channel = f"realtime:price:{ticker}"
        data = json.dumps({
            "ticker": price_data.ticker,
            "price": price_data.price,
            "change": price_data.change,
            "change_rate": price_data.change_rate,
            "volume": price_data.volume,
            "timestamp": price_data.timestamp,
        })

        if channel not in self._messages:
            self._messages[channel] = []

        self._messages[channel].append({
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        self._publish_count += 1

        logger.debug(f"Mock published to {channel}: {price_data.price}")
        return True

    async def publish_message(
        self,
        channel: str,
        message: Dict[str, Any]
    ) -> bool:
        """모의 메시지 발행"""
        if not self._connected:
            return False

        full_channel = f"realtime:{channel}"
        if full_channel not in self._messages:
            self._messages[full_channel] = []

        self._messages[full_channel].append({
            "data": message,
            "timestamp": datetime.now().isoformat()
        })
        self._publish_count += 1

        return True

    def get_messages(self, channel: str) -> List[Dict[str, Any]]:
        """발행된 메시지 조회 (테스트용)"""
        return self._messages.get(f"realtime:{channel}", [])

    def clear_messages(self) -> None:
        """메시지 초기화 (테스트용)"""
        self._messages.clear()

    def is_connected(self) -> bool:
        """연결 상태"""
        return self._connected

    def get_publish_count(self) -> int:
        """발행 횟수"""
        return self._publish_count
