"""
Redis Cache Client

캐시 TTL 관리, 적중률 모니터링, warm-up 기능 제공
"""
import json
import logging
from datetime import timedelta
from typing import Optional, Any, Callable, TypeVar
from functools import wraps
from functools import lru_cache as _lru_cache

import redis.asyncio as aioredis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


# TTL 설정 (초 단위)
class CacheTTL:
    """캐시 TTL 상수"""
    # 가격 데이터: 5분 (실시간 성격)
    PRICE = 300
    # 시그널 데이터: 15분 (분석 결과)
    SIGNAL = 900
    # 시장 데이터: 1분 (빈번한 조회)
    MARKET = 60
    # 종목 기본 정보: 1시간 (잘 변하지 않음)
    STOCK_INFO = 3600
    # AI 분석: 30분 (비용 절감)
    AI_ANALYSIS = 1800
    # 백테스트: 1시간
    BACKTEST = 3600
    # 섹터 데이터: 5분
    SECTOR = 300
    # 뉴스: 1시간
    NEWS = 3600


class CacheMetrics:
    """캐시 적중률 모니터링"""

    def __init__(self):
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

    @property
    def hit_rate(self) -> float:
        """적중률 계산"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return round(self._hits / total * 100, 2)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def sets(self) -> int:
        return self._sets

    @property
    def deletes(self) -> int:
        return self._deletes

    def record_hit(self) -> None:
        """캐시 적중 기록"""
        self._hits += 1

    def record_miss(self) -> None:
        """캐시 미스 기록"""
        self._misses += 1

    def record_set(self) -> None:
        """캐시 저장 기록"""
        self._sets += 1

    def record_delete(self) -> None:
        """캐시 삭제 기록"""
        self._deletes += 1

    def reset(self) -> None:
        """통계 초기화"""
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

    def to_dict(self) -> dict[str, Any]:
        """통계 dict 반환"""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "deletes": self._deletes,
            "hit_rate": self.hit_rate,
            "total_requests": self._hits + self._misses,
        }


# 전역 메트릭 인스턴스
_cache_metrics = CacheMetrics()


def get_cache_metrics() -> CacheMetrics:
    """캐시 메트릭 인스턴스 반환"""
    return _cache_metrics


class CacheClient:
    """
    Redis 비동기 캐시 클라이언트

    ## 사용 예시
    ```python
    cache = CacheClient()

    # 설정
    await cache.initialize()

    # 저장/조회
    await cache.set("key", {"data": "value"}, ttl=60)
    data = await cache.get("key")

    # 삭제
    await cache.delete("key")
    await cache.clear_pattern("user:*")
    ```
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        key_prefix: str = "ralph_stock:",
    ):
        self._url = url
        self._key_prefix = key_prefix
        self._client: Optional[Redis] = None
        self._metrics = _cache_metrics

    async def initialize(self) -> None:
        """Redis 연결 초기화"""
        try:
            self._client = await aioredis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info(f"Redis cache connected: {self._url}")
        except Exception as e:
            logger.warning(f"Redis cache connection failed: {e}")
            self._client = None

    async def close(self) -> None:
        """연결 종료"""
        if self._client:
            await self._client.close()
            logger.info("Redis cache connection closed")

    def _make_key(self, key: str) -> str:
        """키에 접두사 추가"""
        return f"{self._key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        캐시 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        if not self._client:
            return None

        try:
            full_key = self._make_key(key)
            value = await self._client.get(full_key)

            if value is not None:
                self._metrics.record_hit()
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            else:
                self._metrics.record_miss()
                return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self._metrics.record_miss()
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        캐시 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: 만료 시간(초), None이면 영구

        Returns:
            성공 여부
        """
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)

            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)

            if ttl:
                await self._client.setex(full_key, ttl, serialized)
            else:
                await self._client.set(full_key, serialized)

            self._metrics.record_set()
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)
            await self._client.delete(full_key)
            self._metrics.record_delete()
            return True

        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """캐시 존재 여부 확인"""
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)
            return await self._client.exists(full_key) > 0
        except Exception:
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        패턴으로 캐시 삭제

        Args:
            pattern: 삭제할 키 패턴 (예: "user:*")

        Returns:
            삭제된 항목 수
        """
        if not self._client:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self._client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                await self._client.delete(*keys)

            return len(keys)

        except Exception as e:
            logger.warning(f"Cache clear pattern error: {e}")
            return 0

    async def warm_up(
        self,
        data: dict[str, tuple[Any, int]],
    ) -> dict[str, bool]:
        """
        캸시 warm-up (서비스 시작시 미리 로드)

        Args:
            data: {key: (value, ttl)} 형태의 데이터

        Returns:
            {key: success} 형태의 결과
        """
        results = {}

        for key, (value, ttl) in data.items():
            results[key] = await self.set(key, value, ttl=ttl)

        loaded_count = sum(1 for v in results.values() if v)
        logger.info(f"Cache warm-up completed: {loaded_count}/{len(results)} loaded")

        return results

    @property
    def metrics(self) -> CacheMetrics:
        """캐시 메트릭"""
        return self._metrics


# 전역 캐시 클라이언트 인스턴스
_cache_client: Optional[CacheClient] = None


async def get_cache() -> Optional[CacheClient]:
    """
    전역 캐시 클라이언트 반환

    사용 전에 initialize() 호출 필요
    """
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
        await _cache_client.initialize()
    return _cache_client


def cached(
    ttl: int = CacheTTL.SIGNAL,
    key_prefix: str = "",
):
    """
    함수 결과 캐싱 데코레이터

    ## 사용 예시
    ```python
    @cached(ttl=CacheTTL.PRICE, key_prefix="price:")
    async def get_stock_price(ticker: str) -> dict:
        # 비싼 계산...
        return {"price": 50000}
    ```

    Args:
        ttl: 캐시 만료 시간(초)
        key_prefix: 캐시 키 접두사
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 캐시 키 생성
            func_name = func.__name__
            args_str = "_".join(str(a) for a in args)
            kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f"{key_prefix}{func_name}:{args_str}:{kwargs_str}"

            # 캐시 시도
            cache = await get_cache()
            if cache:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

            # 캐시 미스 - 함수 실행
            result = await func(*args, **kwargs)

            # 결과 캐싱
            if cache:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator
