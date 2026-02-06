"""
Daytrading Scanner Proxy Router
단타 스캐너 서비스 (port 5115)로 프록시

캐싱 레이어 추가 (Redis 기반)
- TTL: 5분 (300초)
- 캐시 키: daytrading:signals:{min_score}:{market}:{limit}:{format}

메인 대시보드와의 응답 구조 통일
- format 파라미터 지원 (list/object)
- format=list: 리스트 직접 반환 (기본)
- format=object: { signals, count, generated_at } 반환
"""

import httpx
import json
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

# 유연한 import (테스트 환경 지원)
try:
    from api_gateway.service_registry import get_registry
except ImportError:
    from services.api_gateway.service_registry import get_registry

# 캐시 클라이언트 import
try:
    from src.cache.cache_client import get_cache, CacheTTL
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logging.warning("Cache client not available - caching disabled")

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/daytrading",
    tags=["daytrading"],
)


async def _get_cache_key(min_score: int, market: Optional[str], limit: int, format: str = "list") -> str:
    """캐시 키 생성 (format 포함)"""
    market_part = market.lower() if market else "all"
    return f"daytrading:signals:{min_score}:{market_part}:{limit}:{format}"


async def _invalidate_daytrading_cache() -> None:
    """단타 시그널 캐시 무효화 (POST /scan 호출 후)"""
    if not CACHE_AVAILABLE:
        return

    try:
        cache = await get_cache()
        if cache:
            # 패턴으로 모든 daytrading signals 캐시 삭제
            deleted = await cache.clear_pattern("daytrading:signals:*")
            if deleted > 0:
                logger.info(f"Invalidated {deleted} daytrading signal cache entries")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")


# ============================================================================
# Daytrading Signals
# ============================================================================

@router.get("/signals")
async def get_daytrading_signals(
    min_score: int = Query(default=0, ge=0, le=105, description="최소 점수"),
    market: Optional[str] = Query(default=None, description="시장 (KOSPI/KOSDAQ)"),
    limit: int = Query(default=50, ge=1, le=100, description="최대 반환 개수"),
    format: str = Query(default="list", description="응답 형식 (list/object)"),
):
    """
    단타 매수 신호 조회

    Daytrading Scanner 서비스로 프록시하여 활성 신호 목록을 반환합니다.
    Redis 캐싱이 적용되어 있어 5분 TTL로 캐시됩니다.

    - **min_score**: 최소 점수 (0-105)
    - **market**: 시장 필터 (KOSPI/KOSDAQ)
    - **limit**: 최대 반환 개수
    - **format**: 응답 형식 (list=리스트 직접 반환, object={signals, count, generated_at})

    메인 대시보드와 통일된 응답 구조를 제공합니다.
    """
    # format 파라미터 검증
    if format not in ["list", "object"]:
        raise HTTPException(
            status_code=400,
            detail="format must be 'list' or 'object'"
        )

    # 캐시 시도
    cache_key = await _get_cache_key(min_score, market, limit, format)
    if CACHE_AVAILABLE:
        try:
            cache = await get_cache()
            cached_data = await cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_data
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")

    # Daytrading Scanner 서비스 조회
    registry = get_registry()
    daytrading_scanner = registry.get_service("daytrading-scanner")
    if not daytrading_scanner:
        raise HTTPException(
            status_code=503,
            detail="Daytrading Scanner service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            params = {"min_score": min_score, "limit": limit}
            if market:
                params["market"] = market

            response = await client.get(
                f"{daytrading_scanner['url']}/api/daytrading/signals",
                params=params,
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()

            # format 파라미터에 따라 응답 변환
            if format == "list":
                # 리스트 직접 반환 (메인 대시보드와 동일)
                signals_data = result.get("data", {}).get("signals", [])
                response_to_cache = signals_data
            else:
                # object 형식 반환
                signals_data = result.get("data", {}).get("signals", [])
                response_to_cache = {
                    "signals": signals_data,
                    "count": len(signals_data),
                    "generated_at": result.get("data", {}).get("generated_at", "")
                }

            # 캐시 저장 (5분 TTL)
            if CACHE_AVAILABLE:
                try:
                    cache = await get_cache()
                    await cache.set(cache_key, response_to_cache, ttl=CacheTTL.SIGNAL)
                    logger.debug(f"Cached: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            # Daytrading 시그널 종목들을 daytrading_price_broadcaster에 추가 (실시간 가격 브로드캐스트용)
            signal_tickers = [s.get("ticker") for s in signals_data if s.get("ticker")]
            if signal_tickers:
                try:
                    from services.api_gateway.main import daytrading_price_broadcaster
                    if daytrading_price_broadcaster:
                        for ticker in signal_tickers:
                            daytrading_price_broadcaster.add_ticker(ticker)
                        logger.info(f"Added daytrading signal tickers to price broadcaster: {signal_tickers}")
                except ImportError:
                    pass  # 테스트 환경 등에서 무시
                except Exception as e:
                    logger.warning(f"Failed to add tickers to price broadcaster: {e}")

            return response_to_cache

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Daytrading Scanner error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Daytrading Scanner unavailable: {str(e)}",
            )


@router.post("/scan")
async def scan_daytrading_market(request: dict):
    """
    장중 단타 후보 종목 스캔

    Daytrading Scanner 서비스로 프록시하여 시장을 스캔합니다.
    스캔 완료 후 기존 캐시를 무효화합니다.

    ## Request Body
    - **market**: KOSPI 또는 KOSDAQ
    - **limit**: 최대 반환 개수 (1-100)
    """
    registry = get_registry()

    # Daytrading Scanner 서비스 조회
    daytrading_scanner = registry.get_service("daytrading-scanner")
    if not daytrading_scanner:
        raise HTTPException(
            status_code=503,
            detail="Daytrading Scanner service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{daytrading_scanner['url']}/api/daytrading/scan",
                json=request,
                timeout=30.0,  # 스캔에 시간 더 소요
            )
            response.raise_for_status()
            result = response.json()

            # 스캔 완료 후 캐시 무효화
            await _invalidate_daytrading_cache()

            return result

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Daytrading Scanner error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Daytrading Scanner unavailable: {str(e)}",
            )


@router.post("/analyze")
async def analyze_daytrading_stocks(request: dict):
    """
    종목별 단타 점수 분석

    Daytrading Scanner 서비스로 프록시하여 종목을 분석합니다.

    ## Request Body
    - **tickers**: 분석할 종목 코드 리스트
    """
    registry = get_registry()

    # Daytrading Scanner 서비스 조회
    daytrading_scanner = registry.get_service("daytrading-scanner")
    if not daytrading_scanner:
        raise HTTPException(
            status_code=503,
            detail="Daytrading Scanner service not available"
        )

    # 프록시 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{daytrading_scanner['url']}/api/daytrading/analyze",
                json=request,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Daytrading Scanner error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Daytrading Scanner unavailable: {str(e)}",
            )
