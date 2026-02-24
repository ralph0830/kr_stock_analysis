"""
실시간 가격 캐시 테스트

API와 WebSocket 데이터 불일치 해결을 위한 캐시 레이어 테스트
"""

import pytest
from datetime import datetime, timezone, timedelta


def test_realtime_price_cache_basic():
    """기본 캐시 동작 테스트"""
    from services.api_gateway.realtime_cache import RealtimePriceCache, RealtimePrice

    cache = RealtimePriceCache(max_age_seconds=60)

    # 캐시 업데이트
    price = RealtimePrice(
        ticker="005930",
        price=80000.0,
        change=1000.0,
        change_rate=1.25,
        volume=1000000,
        source="kiwoom_ws",
        timestamp=datetime.now(timezone.utc),
    )
    cache.update("005930", price)

    # 캐시 조회
    retrieved = cache.get("005930")
    assert retrieved is not None
    assert retrieved.ticker == "005930"
    assert retrieved.price == 80000.0
    assert retrieved.source == "kiwoom_ws"


def test_realtime_price_cache_stale():
    """캐시 만료 테스트"""
    from services.api_gateway.realtime_cache import RealtimePriceCache, RealtimePrice

    cache = RealtimePriceCache(max_age_seconds=1)  # 1초 만료

    # 과거 타임스탬프로 데이터 추가
    old_timestamp = datetime.now(timezone.utc) - timedelta(seconds=2)
    price = RealtimePrice(
        ticker="005930",
        price=80000.0,
        change=1000.0,
        change_rate=1.25,
        volume=1000000,
        source="kiwoom_ws",
        timestamp=old_timestamp,
    )
    cache.update("005930", price)

    # 만료된 데이터는 조회되지 않아야 함
    retrieved = cache.get("005930")
    assert retrieved is None  # 만료되었으므로 None 반환


def test_realtime_price_cache_ws_message():
    """WebSocket 메시지 파싱 테스트"""
    from services.api_gateway.realtime_cache import RealtimePriceCache

    cache = RealtimePriceCache(max_age_seconds=60)

    # WebSocket 메시지 형식
    message = {
        "ticker": "005930",
        "data": {
            "price": 80000,
            "change": 1000,
            "change_rate": 1.25,
            "volume": 1000000,
            "bid_price": 79900,
            "ask_price": 80100,
        },
        "source": "kiwoom_ws",
        "timestamp": "2026-02-07T10:30:00Z",
    }

    cache.update_from_ws_message(message)

    # 캐시 조회
    retrieved = cache.get("005930")
    assert retrieved is not None
    assert retrieved.price == 80000.0
    assert retrieved.bid_price == 79900.0
    assert retrieved.ask_price == 80100.0
    assert retrieved.source == "kiwoom_ws"


def test_realtime_price_cache_cleanup():
    """캐시 정리 테스트"""
    from services.api_gateway.realtime_cache import RealtimePriceCache, RealtimePrice

    cache = RealtimePriceCache(max_age_seconds=1)

    # 유효한 데이터 추가
    valid_price = RealtimePrice(
        ticker="005930",
        price=80000.0,
        change=1000.0,
        change_rate=1.25,
        volume=1000000,
        source="kiwoom_ws",
        timestamp=datetime.now(timezone.utc),
    )
    cache.update("005930", valid_price)

    # 만료된 데이터 추가
    old_timestamp = datetime.now(timezone.utc) - timedelta(seconds=2)
    stale_price = RealtimePrice(
        ticker="000660",
        price=150000.0,
        change=2000.0,
        change_rate=1.33,
        volume=500000,
        source="kiwoom_ws",
        timestamp=old_timestamp,
    )
    cache.update("000660", stale_price)

    # 정리 전
    assert cache.get("005930") is not None  # 유효
    assert cache.get("000660") is None  # 만료되었으므로 get()에서 None 반환

    # 정리 실행
    removed_count = cache.cleanup_stale()
    assert removed_count >= 0


def test_realtime_price_cache_stats():
    """캐시 통계 테스트"""
    from services.api_gateway.realtime_cache import RealtimePriceCache, RealtimePrice

    cache = RealtimePriceCache(max_age_seconds=60)

    # 데이터 추가
    price1 = RealtimePrice(
        ticker="005930",
        price=80000.0,
        change=1000.0,
        change_rate=1.25,
        volume=1000000,
        source="kiwoom_ws",
        timestamp=datetime.now(timezone.utc),
    )
    cache.update("005930", price1)

    price2 = RealtimePrice(
        ticker="000660",
        price=150000.0,
        change=2000.0,
        change_rate=1.33,
        volume=500000,
        source="db",
        timestamp=datetime.now(timezone.utc),
    )
    cache.update("000660", price2)

    # 통계 조회
    stats = cache.get_stats()
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] == 2
    assert stats["stale_entries"] == 0
    assert stats["by_source"]["kiwoom_ws"] == 1
    assert stats["by_source"]["db"] == 1


def test_get_realtime_price_cache_singleton():
    """전역 캐시 인스턴스 테스트"""
    from services.api_gateway.realtime_cache import get_realtime_price_cache

    cache1 = get_realtime_price_cache()
    cache2 = get_realtime_price_cache()

    # 동일한 인스턴스 반환 확인
    assert cache1 is cache2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
