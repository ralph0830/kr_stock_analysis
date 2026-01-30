"""
Price Cache Layer (TDD Phase 2 - GREEN)

Redis 기반 현재가 캐싱 레이어
"""

import logging
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Redis 클라이언트 캐싱
_redis_client: Optional["Redis"] = None


async def get_redis_client() -> "Redis":
    """
    Redis 클라이언트 반환 (싱글톤)

    Raises:
        ConnectionError: Redis 연결 실패 시
    """
    global _redis_client

    if _redis_client is None:
        try:
            import redis.asyncio as aioredis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
            _redis_client = await aioredis.from_url(redis_url, decode_responses=True)
            logger.info(f"Redis cache client initialized: {redis_url}")

        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise ConnectionError(f"Redis 연결 실패: {e}")

    return _redis_client


def make_cache_key(ticker: str) -> str:
    """
    캐시 키 생성

    Args:
        ticker: 종목 코드

    Returns:
        캐시 키 (형식: price:{ticker})
    """
    return f"price:{ticker}"


async def get_cached_price(ticker: str) -> Optional[Dict[str, Any]]:
    """
    캐시된 현재가 조회

    캐시에 있으면 반환하고, 없으면 Kiwoom API에서 가져와 캐시에 저장

    Args:
        ticker: 종목 코드

    Returns:
        현재가 정보 또는 None
    """
    from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

    cache_key = make_cache_key(ticker)

    try:
        # 캐시 시도
        client = await get_redis_client()
        cached = await client.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for {ticker}")
            return json.loads(cached)

        # 캐시 미스 - API 호출
        logger.debug(f"Cache miss for {ticker}, fetching from Kiwoom API")
        price_data = await get_kiwoom_current_price(ticker)

        # 캐시 저장 (TTL 30초)
        await client.setex(cache_key, 30, json.dumps(price_data))
        logger.info(f"Cached price for {ticker}: {price_data['price']}원")

        return price_data

    except KiwoomAPIError as e:
        logger.error(f"Kiwoom API error for {ticker}: {e}")
        raise
    except Exception as e:
        logger.error(f"Cache get error for {ticker}: {e}")
        # 캐시 실패해도 API는 시도
        try:
            return await get_kiwoom_current_price(ticker)
        except Exception:
            return None


async def invalidate_price_cache(ticker: str) -> bool:
    """
    특정 종목의 캐시 무효화

    Args:
        ticker: 종목 코드

    Returns:
        성공 여부
    """
    try:
        client = await get_redis_client()
        cache_key = make_cache_key(ticker)
        await client.delete(cache_key)
        logger.info(f"Cache invalidated for {ticker}")
        return True

    except Exception as e:
        logger.error(f"Cache invalidation error for {ticker}: {e}")
        return False


async def invalidate_all_price_cache() -> int:
    """
    모든 가격 캐시 무효화

    Returns:
        삭제된 캐시 수
    """
    try:
        client = await get_redis_client()
        # price: 패턴의 모든 키 찾기
        keys = []
        async for key in client.scan_iter(match="price:*"):
            keys.append(key)

        if keys:
            await client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} price cache entries")

        return len(keys)

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        return 0


def cached_price(ttl: int = 30):
    """
    현재가 조회 캐싱 데코레이터

    Args:
        ttl: 캐시 유효 시간 (초)

    Usage:
        @cached_price(ttl=30)
        async def get_stock_price(ticker: str) -> Dict:
            ...
    """
    def decorator(func):
        async def wrapper(ticker: str, *args, **kwargs):
            cache_key = make_cache_key(ticker)

            try:
                client = await get_redis_client()
                cached = await client.get(cache_key)

                if cached:
                    return json.loads(cached)

            except Exception:
                pass  # 캐시 실패 시 함수 계속 실행

            # 함수 실행
            result = await func(ticker, *args, **kwargs)

            # 캐시 저장
            try:
                client = await get_redis_client()
                await client.setex(cache_key, ttl, json.dumps(result))
            except Exception:
                pass  # 캐시 저장 실패해도 결과 반환

            return result

        return wrapper
    return decorator


async def warmup_cache(tickers: list[str]) -> Dict[str, Any]:
    """
    캐시预热 - 여러 종목의 현재가를 미리 가져와 캐시

    Args:
        tickers: 종목 코드 리스트

    Returns:
        캐시된 가격 정보 딕셔너리
    """
    results = {}

    for ticker in tickers:
        try:
            price_data = await get_cached_price(ticker)
            results[ticker] = price_data
        except Exception as e:
            logger.warning(f"Warmup failed for {ticker}: {e}")

    logger.info(f"Cache warmup completed: {len(results)}/{len(tickers)} tickers")
    return results


async def close_redis_client():
    """Redis 클라이언트 연결 종료"""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis cache client closed")
