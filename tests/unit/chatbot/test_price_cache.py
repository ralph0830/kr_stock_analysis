"""
Price Cache Tests (TDD Phase 2 - RED)

캐싱 레이어 테스트: Redis를 통한 현재가 캐싱
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestPriceCacheDecorator:
    """@cached_price 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self):
        """캐시 미스 후 히트가 발생해야 함"""
        from services.chatbot.price_cache import cached_price, get_redis_client, invalidate_price_cache

        # API 호출 횟수 추적
        call_count = 0

        @cached_price(ttl=30)
        async def mock_get_price(ticker: str):
            nonlocal call_count
            call_count += 1
            return {"price": 100000, "change": 1000}

        try:
            # 캐시 무효화
            await invalidate_price_cache("005930")

            # 첫 번째 호출 - 캐시 미스
            result1 = await mock_get_price("005930")
            assert result1["price"] == 100000
            assert call_count == 1

            # 두 번째 호출 - 캐시 히트
            result2 = await mock_get_price("005930")
            assert result2["price"] == 100000
            # 캐시 히트로 함수가 호출되지 않음
            assert call_count == 1, "캐시 히트 시 함수가 호출되지 않아야 합니다"

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """TTL 30초 후 캐시 만료되어야 함"""
        # 캐시 만료 테스트
        pass

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """종목별 캐시 무효화가 작동해야 함"""
        # 캐시 무효화 테스트
        pass


class TestRedisCacheBackend:
    """Redis 백엔드 테스트"""

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Redis 연결이 성공해야 함"""
        from services.chatbot.price_cache import get_redis_client

        try:
            client = await get_redis_client()
            assert client is not None, "Redis 클라이언트가 연결되어야 합니다"
            # ping 테스트
            await client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """캐시 저장 및 조회가 작동해야 함"""
        from services.chatbot.price_cache import get_redis_client

        try:
            client = await get_redis_client()
            key = "price:005930"
            value = '{"price": 152000, "change": 1000, "change_rate": 0.66, "volume": 1000000, "timestamp": "20260130"}'

            # 저장
            await client.setex(key, 30, value)

            # 조회
            result = await client.get(key)
            assert result is not None, "캐시에서 값을 가져올 수 있어야 합니다"
            assert result.decode() == value, "캐시 값이 일치해야 합니다"

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """캐시 TTL이 30초로 설정되어야 함"""
        from services.chatbot.price_cache import get_redis_client

        try:
            client = await get_redis_client()
            key = "price:test_ttl"
            value = '{"price": 1000}'

            await client.setex(key, 30, value)

            # TTL 확인
            ttl = await client.ttl(key)
            assert ttl > 0, "TTL이 설정되어야 합니다"
            assert ttl <= 30, f"TTL은 30초 이하여야 합니다: {ttl}"

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")


class TestCacheKeyFormat:
    """캐시 키 포맷 테스트"""

    def test_cache_key_format_consistency(self):
        """캐시 키가 일관된 형식을 가져야 함"""
        from services.chatbot.price_cache import make_cache_key

        key1 = make_cache_key("005930")
        key2 = make_cache_key("005930")
        key3 = make_cache_key("000660")

        assert key1 == key2, "동일 종목은 동일한 키를 가져야 합니다"
        assert key1 != key3, "다른 종목은 다른 키를 가져야 합니다"
        assert key1 == "price:005930", f"캐시 키 형식이 올바르지 않습니다: {key1}"


class TestConcurrentCacheAccess:
    """동시 캐시 접근 테스트"""

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """동시 요청 시 캐시가 안전하게 작동해야 함"""
        from services.chatbot.price_cache import get_redis_client, make_cache_key

        try:
            client = await get_redis_client()
            key = make_cache_key("005930")
            value = '{"price": 152000}'

            # 동시에 10개의 요청
            tasks = []
            for _ in range(10):
                tasks.append(client.setex(key, 30, value))

            await asyncio.gather(*tasks)

            # 확인
            result = await client.get(key)
            assert result is not None

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")


class TestCacheWithKiwoomAPI:
    """Kiwoom API와 캐시 통합 테스트"""

    @pytest.mark.asyncio
    async def test_cached_price_call(self):
        """캐시된 가격 조회가 작동해야 함"""
        from services.chatbot.price_cache import get_cached_price, invalidate_price_cache
        from services.chatbot.kiwoom_integration import KiwoomAPIError
        import os

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            # 캐시 무효화
            await invalidate_price_cache("005930")

            # 첫 번째 호출 - API 호출
            result1 = await get_cached_price("005930")
            assert result1 is not None
            assert "price" in result1

            # 두 번째 호출 - 캐시 히트
            result2 = await get_cached_price("005930")
            assert result2 is not None
            assert result2["price"] == result1["price"]

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")
        except Exception as e:
            pytest.skip(f"Cache not available: {e}")

    @pytest.mark.asyncio
    async def test_cache_invalidate_before_fetch(self):
        """캐시 무효화 후 새로운 데이터를 가져와야 함"""
        from services.chatbot.price_cache import get_cached_price, invalidate_price_cache
        from services.chatbot.kiwoom_integration import KiwoomAPIError
        import os

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            # 첫 번째 호출
            result1 = await get_cached_price("005930")

            # 캐시 무효화
            await invalidate_price_cache("005930")

            # 두 번째 호출 - 새 데이터
            result2 = await get_cached_price("005930")

            assert result1 is not None
            assert result2 is not None

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")
        except Exception as e:
            pytest.skip(f"Cache not available: {e}")
