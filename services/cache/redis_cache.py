"""
Redis Cache - 캐싱 레이어
Redis 기반 고성능 캐싱 구현
"""

import json
import logging
import hashlib
import asyncio
from typing import Optional, Any, Callable, TypeVar, List, Dict
from functools import wraps
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis 연결 설정
REDIS_URL = "redis://localhost:6379/2"
DEFAULT_TTL = 300  # 5분


T = TypeVar("T")


class RedisCache:
    """
    Redis 비동기 캐시 클라이언트

    - 키-값 저장
    - TTL 만료
    - 일괄 조회
    """

    def __init__(self, redis_url: str = REDIS_URL, default_ttl: int = DEFAULT_TTL):
        """
        Args:
            redis_url: Redis URL
            default_ttl: 기본 TTL (초)
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Redis 연결"""
        self._redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info("Redis Cache connected")

    async def disconnect(self):
        """Redis 연결 해제"""
        if self._redis:
            await self._redis.close()
        logger.info("Redis Cache disconnected")

    def _serialize(self, value: Any) -> str:
        """값 직렬화 - 모든 값을 JSON으로 직렬화"""
        return json.dumps(value, ensure_ascii=False)

    def _deserialize(self, value: str) -> Any:
        """값 역직렬화"""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def get(self, key: str) -> Optional[Any]:
        """
        캐시 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        try:
            if not self._redis:
                await self.connect()

            value = await self._redis.get(key)
            if value is None:
                return None

            return self._deserialize(value)

        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        캐시 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: 만료 시간 (초), None이면 기본 TTL 사용

        Returns:
            성공 여부
        """
        try:
            if not self._redis:
                await self.connect()

            serialized = self._serialize(value)
            expire = ttl if ttl is not None else self.default_ttl

            await self._redis.setex(key, expire, serialized)
            logger.debug(f"Cache set: {key} (TTL: {expire}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        try:
            if not self._redis:
                await self.connect()

            await self._redis.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        캐시 존재 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        try:
            if not self._redis:
                await self.connect()

            return await self._redis.exists(key) > 0

        except Exception as e:
            logger.error(f"Cache exists check failed: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        일괄 캐시 조회

        Args:
            keys: 캐시 키 리스트

        Returns:
            {키: 값} 딕셔너리
        """
        try:
            if not self._redis:
                await self.connect()

            values = await self._redis.mget(keys)
            result = {}

            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)

            return result

        except Exception as e:
            logger.error(f"Cache get_many failed: {e}")
            return {}

    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        일괄 캐시 저장

        Args:
            mapping: {키: 값} 딕셔너리
            ttl: 만료 시간 (초)

        Returns:
            성공 여부
        """
        try:
            if not self._redis:
                await self.connect()

            expire = ttl if ttl is not None else self.default_ttl

            # Pipeline 사용하여 일괄 저장
            pipe = self._redis.pipeline()
            for key, value in mapping.items():
                serialized = self._serialize(value)
                pipe.setex(key, expire, serialized)

            await pipe.execute()
            logger.debug(f"Cache set_many: {len(mapping)} keys")
            return True

        except Exception as e:
            logger.error(f"Cache set_many failed: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        패턴으로 캐시 삭제

        Args:
            pattern: 키 패턴 (예: "signals:*")

        Returns:
            삭제된 키 수
        """
        try:
            if not self._redis:
                await self.connect()

            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self._redis.delete(*keys)

            logger.debug(f"Cache cleared pattern: {pattern} ({len(keys)} keys)")
            return len(keys)

        except Exception as e:
            logger.error(f"Cache clear_pattern failed: {e}")
            return 0


# 전역 캐시 인스턴스
_cache: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """전역 캐시 인스턴스 반환"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
        await _cache.connect()
    return _cache


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """
    캐시 키 생성

    Args:
        func_name: 함수명
        args: 위치 인자
        kwargs: 키워드 인자

    Returns:
        캐시 키
    """
    # 인자를 문자열로 변환하여 해시
    args_str = f"{args}:{sorted(kwargs.items())}"
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
    return f"{func_name}:{args_hash}"


def cached(ttl: int = DEFAULT_TTL, key_prefix: Optional[str] = None):
    """
    캐시 데코레이터

    Args:
        ttl: 캐시 만료 시간 (초)
        key_prefix: 캐시 키 접두사 (None이면 함수명 사용)

    Usage:
        @cached(ttl=60)
        async def get_stock_data(ticker: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 캐시 키 생성
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, args, kwargs)

            # 캐시 조회
            cache = await get_cache()
            cached_value = await cache.get(cache_key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 캐시 미스 - 함수 실행
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)

            # 캐시 저장
            await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


# 캐시 키 상수
CACHE_KEY_SIGNALS = "signals:list"
CACHE_KEY_MARKET_GATE = "market:gate"
CACHE_KEY_STOCK_PRICES = "prices:stock"
CACHE_KEY_VCP_RESULTS = "vcp:results"
