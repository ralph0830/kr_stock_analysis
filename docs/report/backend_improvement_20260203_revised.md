# 백엔드 개선 방안 (보완판)
**전체 종목 실시간 가격 지원**

작성 일자: 2026-02-03
목표: VCP 스캐너로 선별된 모든 종목(KOSPI/KOSDAQ/ELW)의 실시간 가격 브로드캐스트

---

## 0. 기존 코드와의 통합

### 0.1 이미 구현된 기능 활용

```python
# 기존 CacheClient 활용 (src/cache/cache_client.py)
from src.cache.cache_client import CacheClient, CacheTTL, get_cache

# 가격 캐싱
cache = await get_cache()
await cache.set(f"price:{ticker}", price_data, ttl=CacheTTL.PRICE)  # 300초

# 기존 HeartbeatManager, RedisSubscriber 유지
from src.websocket.server import HeartbeatManager, RedisSubscriber
```

### 0.2 최소 변경 원칙

| 컴포넌트 | 상태 | 변경 필요 여부 |
|----------|------|----------------|
| `CacheClient` | ✅ 구현됨 | ❌ 변경 없음 |
| `HeartbeatManager` | ✅ 구현됨 | ❌ 변경 없음 |
| `RedisSubscriber` | ✅ 구현됨 | ❌ 변경 없음 |
| `PriceUpdateBroadcaster` | ✅ 구현됨 | ⚠️ ELW 지원 추가 |
| `ConnectionManager.subscribe()` | ✅ 구현됨 | ⚠️ ticker 유효성 검사 수정 |
| `KiwoomWebSocketBridge` | ✅ 구현됨 | ⚠️ ELW 식별 추가 |

---

## 1. 현재 시스템 분석

### 1.1 브로드캐스터 현황

```python
# src/websocket/server.py:260-261
class PriceUpdateBroadcaster:
    # 기본 종목 (마켓 개장 시 항상 포함)
    DEFAULT_TICKERS = {"005930", "000660", "035420", "005380", "028260", "000020"}
    # 삼성전자, SK하이닉스, NAVER, 현대차, 삼성물산, 동화약품
```

**문제점**:
- 고정 6종목만 브로드캐스트
- 나머지 KOSPI/KOSDAQ 종목은 미지원
- ELW 종목은 전혀 미지원

### 1.2 구독 처리 로직

```python
# src/websocket/server.py:162-176
def subscribe(self, client_id: str, topic: str) -> None:
    # ...
    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ticker는 6자리 숫자여야 함  ← 문제! ELW 제외됨
        if ticker.isdigit() and len(ticker) == 6:
            # ... KiwoomWebSocketBridge에 ticker 추가
```

**문제점**:
- `ticker.isdigit()` 체크로 ELW 종목(0015N0 등) 제외됨
- 6자리 ELW(493330)는 통과하지만 Kiwoom 브리지에서 미지원

---

## 2. ELW 종목코드 분석

### 2.1 ELW 형식

| 종류 | 형식 | 예시 | 비고 |
|------|------|------|------|
| KOSPI ELW | 6자리 (알파벳 포함) | 0015N0, 0025N0, 0035N0 | N=Call, M=Put |
| KOSDAQ ELW | 6자리 숫자 | 493330-523330 | 특정 범위 내 |
| K-OTC | 10자리 숫자 | 0152301010 | 일단 미지원 |

### 2.2 ticker 유효성 검사 수정

**파일**: `src/websocket/server.py`

```python
def _is_valid_ticker(self, ticker: str) -> bool:
    """
    종목코드 유효성 검사 (ELW 포함)

    - KOSPI/KOSDAQ: 6자리 숫자
    - ELW: 6자리 (숫자+알파벳 또는 일부 6자리 숫자)
    - K-OTC: 10자리 숫자 (미지원)

    Args:
        ticker: 종목코드

    Returns:
        유효 여부
    """
    # 빈 문자열 체크
    if not ticker:
        return False

    # 길이 체크
    if len(ticker) < 6:
        return False

    # K-OTC: 10자리 (일단 미지원)
    if len(ticker) == 10:
        logger.debug(f"[VALIDATION] K-OTC ticker not supported: {ticker}")
        return False

    # 알파벳만으로 된 종목코드는 유효하지 않음
    if ticker.isalpha():
        return False

    # 6자리 이상이면 유효 (KOSPI, KOSDAQ, ELW 모두 포함)
    # 숫자+알파벳 조합(ELW) 또는 6자리 숫자
    if len(ticker) == 6:
        return True

    return False
```

---

## 3. 구독 처리 개선

### 3.1 ConnectionManager.subscribe() 수정

**파일**: `src/websocket/server.py`

```python
def subscribe(self, client_id: str, topic: str) -> None:
    """
    토픽 구독 (전체 종목 지원)

    Args:
        client_id: 클라이언트 ID
        topic: 구독할 토픽 (예: "price:005930", "price:0015N0")

    Note:
        topic이 'price:{ticker}' 형식이면 자동으로 KiwoomWebSocketBridge에 ticker 추가
        ELW 종목도 지원합니다.
    """
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    self.subscriptions[topic].add(client_id)
    logger.info(f"Client {client_id} subscribed to {topic}")

    # price:{ticker} 형식 처리
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ELW 지원: isdigit() 체크 → _is_valid_ticker()로 변경
        if self._is_valid_ticker(ticker):
            # KiwoomWebSocketBridge에 ticker 추가 (ELW 포함)
            from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                import asyncio
                asyncio.create_task(ws_bridge.add_ticker(ticker))
                print(f"[WS BRIDGE] Added ticker to KiwoomWebSocketBridge: {ticker}")
            else:
                # WebSocket 브릿지가 없으면 price_broadcaster에 추가
                from src.websocket.server import price_broadcaster
                price_broadcaster.add_ticker(ticker)
        else:
            logger.warning(f"[SUBSCRIBE] Invalid ticker format: {ticker}")
```

### 3.2 unsubscribe() 메서드도 동일하게 수정

```python
def unsubscribe(self, client_id: str, topic: str) -> None:
    """토픽 구독 취소 (전체 종목 지원)"""
    if topic in self.subscriptions:
        self.subscriptions[topic].discard(client_id)

        # 구독자가 없으면 토픽 삭제 및 브릿지에서 ticker 제거
        if not self.subscriptions[topic]:
            del self.subscriptions[topic]

            # price:{ticker} 형식이면 브릿지에서 ticker 제거
            if topic.startswith("price:"):
                ticker = topic.split(":", 1)[1]
                # ticker 유효성 검사 (ELW 포함)
                if self._is_valid_ticker(ticker):
                    # ... 제거 로직
```

---

## 4. Kiwoom 브리지 ELW 처리

### 4.1 KiwoomWebSocketBridge ELW 식별

**파일**: `src/websocket/kiwoom_bridge.py`

```python
class KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket Bridge

    전체 종목 실시간 지원을 위한 ELW 처리 개선
    """

    def __init__(self):
        # ...
        self._active_tickers: Set[str] = set()
        self._elw_polling_tasks: Dict[str, asyncio.Task] = {}

    def _is_elw_ticker(self, ticker: str) -> bool:
        """
        ELW 종목 체크

        ELW 형식:
        - 0015N0 (알파벳 포함 6자리) - KOSPI ELW
        - 493330 (일부 6자리 숫자) - KOSDAQ ELW

        Args:
            ticker: 종목코드

        Returns:
            ELW 여부
        """
        # 알파벳 포함 체크 (KOSPI ELW)
        if any(c.isalpha() for c in ticker):
            return True

        # KOSDAQ ELW 코드 범위 (493330-523330)
        if ticker.isdigit() and len(ticker) == 6:
            ticker_int = int(ticker)
            if 493330 <= ticker_int <= 523330:
                return True

        return False

    async def add_ticker(self, ticker: str) -> bool:
        """
        종목 구독 추가 (ELW 지원)

        Args:
            ticker: 종목코드 (ELW 포함)

        Returns:
            성공 여부
        """
        if ticker in self._active_tickers:
            return True

        # ELW 체크
        is_elw = self._is_elw_ticker(ticker)

        if is_elw:
            logger.info(f"[WS BRIDGE] Adding ELW ticker: {ticker}")
            # ELW는 폴링 방식 사용 (WebSocket 실시간 미지원)
            self._start_elw_polling(ticker)
            self._active_tickers.add(ticker)
            return True
        else:
            # 일반 종목 처리
            self._active_tickers.add(ticker)
            logger.info(f"Added ticker to KiwoomWebSocketBridge: {ticker}")
            return True

    def _start_elw_polling(self, elw_ticker: str) -> None:
        """
        ELW 폴링 태스크 시작 (Celery 사용)
        """
        from tasks.elw_tasks import start_elw_polling

        if elw_ticker not in self._elw_polling_tasks:
            task = start_elw_polling.delay(elw_ticker)
            self._elw_polling_tasks[elw_ticker] = task
            logger.info(f"[WS BRIDGE] Started ELW polling for {elw_ticker}")

    async def remove_ticker(self, ticker: str) -> bool:
        """종목 구독 제거"""
        self._active_tickers.discard(ticker)
        # ELW 폴링 태스크 중지
        if ticker in self._elw_polling_tasks:
            task = self._elw_polling_tasks.pop(ticker)
            if task and not task.ready():
                task.revoke(terminate=True)
            logger.info(f"[WS BRIDGE] Stopped ELW polling for {ticker}")
        logger.info(f"Removed ticker from KiwoomWebSocketBridge: {ticker}")
        return True
```

---

## 5. ELW 폴링 태스크

### 5.1 ELW 태스크 구현

**파일**: `tasks/elw_tasks.py` (신규)

```python
"""
ELW 종목 폴링 태스크

WebSocket 실시간 지원이 어려운 ELW 종목을 위한 폴링 대체
"""

import asyncio
from datetime import datetime
from celery import shared_task
from sqlalchemy import select

from src.database.session import get_db_session
from src.database.models import DailyPrice, Stock
from src.kiwoom.rest_api import get_kiwoom_api
from src.cache.cache_client import CacheClient, CacheTTL, get_cache
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def start_elw_polling(ticker: str):
    """
    ELW 종목 폴링 시작

    Args:
        ticker: ELW 종목코드
    """
    logger.info(f"[ELW POLLING] Started polling for {ticker}")
    # Celery beat를 통한 스케줄링으로 처리
    # (별도 beat 스케줄러 설정 필요)
    return {"status": "started", "ticker": ticker}


@shared_task(bind=True)
async def fetch_elw_prices(tickers: list[str]) -> dict:
    """
    ELW 종목 가격 폴링

    Args:
        tickers: ELW 종목코드 리스트

    Returns:
        {ticker: price_data} 딕셔너리
    """
    results = {}

    try:
        api = await get_kiwoom_api()
        if not api:
            logger.error("[ELW POLLING] Kiwoom API not available")
            return results

        # 토큰 발급
        await api.issue_token()

        # 캐시 클라이언트
        cache = await get_cache()

        # 각 종목별로 가격 조회
        for ticker in tickers:
            try:
                # 캐시 확인
                cache_key = f"price:elw:{ticker}"
                cached = await cache.get(cache_key)
                if cached:
                    results[ticker] = cached
                    logger.debug(f"[ELW POLLING] Cache hit for {ticker}")
                    continue

                # 일봉 데이터 조회 (가장 최근 데이터)
                daily_prices = await api.get_daily_prices(ticker, days=1)

                if daily_prices and len(daily_prices) > 0:
                    latest = daily_prices[0]
                    price = latest.get("price", 0)
                    change = latest.get("change", 0)
                    base_price = price - change
                    change_rate = (change / base_price * 100) if base_price > 0 else 0.0

                    price_data = {
                        "ticker": ticker,
                        "price": price,
                        "change": change,
                        "change_rate": change_rate,
                        "volume": latest.get("volume", 0),
                        "timestamp": latest.get("date", datetime.now().isoformat()),
                        "is_elw": True,
                    }

                    results[ticker] = price_data

                    # 캐시 저장 (5분 TTL)
                    await cache.set(cache_key, price_data, ttl=CacheTTL.PRICE)
                    logger.debug(f"[ELW POLLING] Fetched price for {ticker}: {price}")

            except Exception as e:
                logger.error(f"[ELW POLLING] Failed to fetch {ticker}: {e}")
                results[ticker] = None

    except Exception as e:
        logger.error(f"[ELW POLLING] Error: {e}")

    # 브로드캐스트 (WebSocket으로 실시간 전송)
    from src.websocket.server import connection_manager

    for ticker, data in results.items():
        if data:
            try:
                await connection_manager.broadcast(
                    {
                        "type": "price_update",
                        "ticker": ticker,
                        "data": data,
                        "timestamp": datetime.now().isoformat(),
                        "is_polling": True,
                    },
                    topic=f"price:{ticker}",
                )
                logger.info(f"[ELW POLLING] Broadcasted {ticker}")
            except Exception as e:
                logger.error(f"[ELW POLLING] Failed to broadcast {ticker}: {e}")

    return results


@shared_task(bind=True)
def sync_elw_tickers_from_db():
    """
    DB에 있는 모든 ELW 종목을 동기화하여 폴링 대상 종목 리스트 반환
    """
    async with get_db_session() as db:
        # ELW 종목 조회 (알파벳이 포함된 6자리)
        result = await db.execute(
            select(Stock)
            .where(Stock.listing_status == "Y")
            .where(Stock.ticker.regexp_match("[A-Za-z]"))  # 알파벳 포함
            .where(Stock.ticker.length() == 6)
        )

        elw_stocks = result.scalars().all()

    logger.info(f"[ELW SYNC] Found {len(elw_stocks)} ELW stocks")
    return [stock.ticker for stock in elw_stocks]
```

---

## 6. 폴링 API 엔드포인트

### 6.1 실시간 가격 조회 API

**파일**: `services/api_gateway/routes/stocks.py`

```python
from fastapi import Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from src.kiwoom.rest_api import get_kiwoom_api
from src.cache.cache_client import CacheClient, CacheTTL, get_cache


class PollingPriceResponse(BaseModel):
    """폴링 가격 응답"""
    ticker: str
    price: float
    change: float
    change_rate: float
    volume: int
    timestamp: str
    is_realtime: bool  # 항상 False (폴링 데이터)
    is_elw: bool = False


@router.get("/realtime-prices/polling")
async def get_realtime_prices_polling(
    tickers: str = Query(..., description="콤마로 구분된 종목코드"),
    include_elw: bool = Query(True, description="ELW 포함 여부"),
    cache_ttl: int = Query(10, description="캐시 유효시간(초)"),
):
    """
    실시간 가격 조회 (폴링 방식)

    - WebSocket 미지원 종목(ELW, K-OTC)을 위한 폴링 엔드포인트
    - 캐싱을 통한 응답 속도 향상
    - 전체 종목 지원

    Args:
        tickers: 콤마로 구분된 종목코드 (예: "005930,000660,0015N0")
        include_elw: ELW 포함 여부
        cache_ttl: 캐시 유효시간(초)
    """
    from src.websocket.server import ConnectionManager

    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]

    # 캐시 클라이언트
    cache = await get_cache()

    # ticker 유효성 검사
    manager = ConnectionManager()
    valid_tickers = [t for t in ticker_list if manager._is_valid_ticker(t)]

    # ELW 필터링
    if not include_elw:
        valid_tickers = [t for t in valid_tickers if not any(c.isalpha() for c in t)]

    # 캐시된 데이터 조회
    cached_data = {}
    missed_tickers = []

    for ticker in valid_tickers:
        cache_key = f"price:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            cached_data[ticker] = cached
        else:
            missed_tickers.append(ticker)

    # 캐시 miss인 종목만 조회
    if missed_tickers:
        # Kiwoom API 호출
        api = await get_kiwoom_api()
        if not api:
            raise HTTPException(
                status_code=503,
                detail="Kiwoom API not available"
            )

        # 토큰 발급
        await api.issue_token()

        # 종목별 가격 조회
        for ticker in missed_tickers:
            try:
                # 일봉 데이터 조회 (가장 최신 종가)
                daily_prices = await api.get_daily_prices(ticker, days=1)

                if daily_prices and len(daily_prices) > 0:
                    latest = daily_prices[0]
                    price = latest.get("price", 0)
                    change = latest.get("change", 0)
                    base_price = price - change
                    change_rate = (change / base_price * 100) if base_price > 0 else 0.0

                    price_data = {
                        "ticker": ticker,
                        "price": price,
                        "change": change,
                        "change_rate": change_rate,
                        "volume": latest.get("volume", 0),
                        "timestamp": latest.get("date", datetime.now().isoformat()),
                        "is_realtime": False,  # 폴링 데이터임
                        "is_elw": any(c.isalpha() for c in ticker),
                    }

                    # 캐시 저장
                    await cache.set(f"price:{ticker}", price_data, ttl=CacheTTL.PRICE)

                    cached_data[ticker] = price_data

            except Exception as e:
                logger.error(f"[POLLING] Failed to fetch price for {ticker}: {e}")

    # 전체 종목 데이터 반환
    return {
        "prices": cached_data,
        "cached": len(cached_data) - len(missed_tickers),
        "fetched": len(missed_tickers),
        "total": len(valid_tickers),
    }
```

---

## 7. VCP 스캐너 전체 종목 확장

### 7.1 스캔 요청 모델 확장

**파일**: `services/vcp_scanner/main.py`

```python
from pydantic import BaseModel
from typing import Optional, Literal


class ScanRequest(BaseModel):
    """스캔 요청 모델 (전체 종목 지원)"""

    # 시장 선택
    market: Literal["KOSPI", "KOSDAQ", "ALL"] = "ALL"

    # 종목 필터
    exclude_elw: bool = True
    min_market_cap: Optional[int] = None
    max_tickers: int = 100
    top_n: int = 30

    # 정렬 옵션
    sort_by: Literal["score", "market_cap", "volume"] = "score"
    sort_order: Literal["desc", "asc"] = "desc"

    # 점수 필터
    min_score: float = 0.0


@router.post("/scan", response_model=ScanResponse)
async def scan_vcp_patterns(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    VCP 패턴 스캔 실행 (전체 종목 지원)

    개선사항:
    - 전체 종목 대상
    - ELW 필터링 옵션
    - 시가총액 필터링
    - 동시성 높은 비동기 처리
    """
    analyzer = get_analyzer()

    # 종목 리스트 조회 (전체 종목)
    async with get_db_session() as db:
        # 시장 필터링
        markets = {
            "KOSPI": ["0"],
            "KOSDAQ": ["10"],
            "ALL": ["0", "10"],
        }[request.market]

        # 쿼리 빌딩
        query = (
            select(Stock)
            .where(Stock.listing_status == "Y")  # 상장 종목만
            .where(Stock.market_code.in_(markets))
        )

        # ELW 제외
        if request.exclude_elw:
            # 알파벳 포함 종목 제외 (ELW)
            query = query.where(~Stock.ticker.regexp_match("[A-Za-z]"))
            logger.info(f"[SCAN] Excluding ELW stocks")

        # 시가총액 필터
        if request.min_market_cap:
            query = query.where(Stock.market_cap >= request.min_market_cap)
            logger.info(f"[SCAN] Min market cap: {request.min_market_cap}")

        # 최대 종목 수 제한
        query = query.order_by(Stock.market_cap.desc()).limit(request.max_tickers)

        result = await db.execute(query)
        stocks = result.scalars().all()

        logger.info(f"[SCAN] Scanning {len(stocks)} stocks from {request.market}")

    # 비동기 VCP 분석
    import asyncio

    async def analyze_single(stock: Stock) -> Optional[VCPResult]:
        try:
            return await analyzer.analyze(stock.ticker, stock.name)
        except Exception as e:
            logger.error(f"[SCAN] Error analyzing {stock.ticker}: {e}")
            return None

    # 병렬 분석 (세마포어로 동시성 제어)
    semaphore = asyncio.Semaphore(10)  # 동시 10개 제한

    async def analyze_with_semaphore(stock: Stock):
        async with semaphore:
            return await analyze_single(stock)

    tasks = [analyze_with_semaphore(stock) for stock in stocks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 유효한 결과 필터링
    valid_results = [
        r for r in results
        if r and isinstance(r, VCPResult) and r.pattern_detected
    ]

    # 점수 필터
    if request.min_score > 0:
        valid_results = [r for r in valid_results if r.total_score >= request.min_score]

    # 정렬
    if request.sort_by == "score":
        valid_results.sort(key=lambda x: x.total_score, reverse=(request.sort_order == "desc"))
    elif request.sort_by == "market_cap":
        valid_results.sort(key=lambda x: x.current_price or 0, reverse=(request.sort_order == "desc"))
    elif request.sort_by == "volume":
        valid_results.sort(key=lambda x: x.volume or 0, reverse=(request.sort_order == "desc"))

    # 상위 N개 선택
    top_results = valid_results[:request.top_n]

    # DB 저장
    saved_count = 0
    try:
        saved_count = save_vcp_signals_to_db(top_results)
    except Exception as db_error:
        logger.warning(f"DB 저장 실패 (스캔 결과는 반환): {db_error}")

    from datetime import datetime
    return ScanResponse(
        results=[r.to_dict() for r in top_results],
        count=len(top_results),
        scanned_at=datetime.now().isoformat(),
        saved=saved_count > 0,
    )
```

---

## 8. Celery Beat 스케줄링

### 8.1 ELW 폴링 스케줄

**파일**: `tasks/celery_app.py`

```python
from celery.schedules import crontab
from tasks.elw_tasks import sync_elw_tickers_from_db, fetch_elw_prices


@celery_app.on_after_configure
def setup_periodic_tasks(sender, **kwargs):
    """
    Celery Beat 주기 작업 설정

    - ELW 종목 폴링 스케줄
    - 캐시 갱신
    """
    # ELW 종목 동기화 (매일 오전 8:30)
    sender.add_periodic_task(
        "sync-elw-tickers",
        sync_elw_tickers_from_db.s(),
        crontab(hour=8, minute=30),
    )

    # ELW 종목 폴링 (장 중 30초 간격, 평일 9:30-15:30)
    sender.add_periodic_task(
        "poll-elw-prices",
        poll_elw_prices_in_market_hours(),
        crontab(
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/1",  # 1분 간격 (Celery 최소 단위)
        ),
    )

    # 가격 캐시 무효화 (장 마감 15:30)
    sender.add_periodic_task(
        "invalidate-price-cache",
        invalidate_price_cache_async.s(),
        crontab(hour=15, minute=30),
    )


@celery_app.task
def poll_elw_prices_in_market_hours():
    """
    장 중 시간대 ELW 종목 폴링

    9:30 - 15:30 사이 1분 간격으로 폴링
    """
    import asyncio

    # ELW 종목 리스트 가져오기
    elw_tickers = asyncio.run(sync_elw_tickers_from_db())

    if not elw_tickers:
        logger.warning("[CELERY] No ELW tickers to poll")
        return

    # 가격 조회 및 브로드캐스트
    results = asyncio.run(fetch_elw_prices(elw_tickers))

    logger.info(f"[CELERY] Polled {len(results)} ELW prices")


@celery_app.task
def invalidate_price_cache_async():
    """
    가격 캐시 무효화 (Celery Task)
    """
    import asyncio
    from src.cache.cache_client import get_cache

    async def _invalidate():
        cache = await get_cache()
        if cache:
            await cache.clear_pattern("price:*")

    asyncio.run(_invalidate())
```

---

## 9. 에러 핸들링 및 재시도 정책

### 9.1 Kiwoom API 장애 대비 Fallback

```python
class FallbackPriceFetcher:
    """
    Kiwoom API 장애 대비 폴백 가격 조회기

    1. Kiwoom REST API (1차)
    2. DB 캐시 (2차)
    3. Mock 데이터 (개발용, 3차)
    """

    async def fetch_price(self, ticker: str) -> Optional[dict]:
        """다중 소스 가격 조회"""
        # 1차: Kiwoom API
        try:
            api = await get_kiwoom_api()
            if api:
                prices = await api.get_daily_prices(ticker, days=1)
                if prices:
                    return self._format_price(prices[0])
        except Exception as e:
            logger.warning(f"Kiwoom API failed for {ticker}: {e}")

        # 2차: DB 캐시
        try:
            from src.websocket.price_provider import PriceDataProvider
            provider = PriceDataProvider()
            prices = provider.get_latest_prices([ticker])
            if prices and ticker in prices:
                return prices[ticker]
        except Exception as e:
            logger.warning(f"DB fallback failed for {ticker}: {e}")

        # 3차: Mock (개발용)
        if os.getenv("DEVELOPMENT") == "true":
            logger.warning(f"Using mock price for {ticker}")
            return self._mock_price(ticker)

        return None
```

### 9.2 WebSocket 연결 복구

```python
class ReconnectingWebSocketBridge:
    """
    재연결 지원 WebSocket 브릿지
    """

    def __init__(self, max_retries: int = 10, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._retry_count = 0

    async def connect_with_retry(self, url: str):
        """재시도 포함 연결"""
        while self._retry_count < self.max_retries:
            try:
                # 연결 시도
                await self._connect(url)
                self._retry_count = 0  # 성공 시 초기화
                return
            except Exception as e:
                self._retry_count += 1
                delay = self.base_delay * (2 ** self._retry_count)  # 지수 백오프
                logger.warning(f"Connection failed ({self._retry_count}/{self.max_retries}), retrying in {delay}s")
                await asyncio.sleep(delay)

        raise ConnectionError(f"Failed to connect after {self.max_retries} retries")
```

---

## 10. 보안 및 속도 제한

### 10.1 API Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/realtime-prices/polling")
@limiter.limit("60/minute")  # 분당 60회
async def get_realtime_prices_polling(...):
    ...
```

### 10.2 WebSocket 연결 제한

```python
class ConnectionManager:
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """연결 수 제한 적용"""
        if len(self.active_connections) >= self.max_connections:
            logger.warning(f"Max connections reached: {self.max_connections}")
            await websocket.close(code=1008, reason="Max connections reached")
            return False

        self.active_connections[client_id] = websocket
        return True
```

---

## 11. 데이터베이스 인덱스

### 11.1 실시간 조회 성능 최적화

```sql
-- 종목별 시가총액 인덱스 (스캔 대상 종목 선별에 필요)
CREATE INDEX IF NOT EXISTS idx_stock_market_cap_desc
ON stocks(market_code, market_cap DESC)
WHERE listing_status = 'Y';

-- 종목 코드 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_ticker
ON stocks(ticker);

-- 일일 가격 인덱스 (최신 데이터 조회)
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date_desc
ON daily_prices(ticker, date DESC);

-- ELW 종목 식별을 위한 컬럼 추가
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS ticker_category VARCHAR(10);
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS realtime_supported BOOLEAN DEFAULT TRUE;

-- ELW 종목 업데이트
UPDATE stocks
SET
    ticker_category = CASE
        WHEN ticker ~ '[A-Za-z]' THEN 'ELW'
        WHEN LENGTH(ticker) = 10 THEN 'OTC'
        WHEN market_code = '0' THEN 'KOSPI'
        WHEN market_code = '10' THEN 'KOSDAQ'
        ELSE 'UNKNOWN'
    END,
    realtime_supported = CASE
        WHEN ticker ~ '[A-Za-z]' THEN FALSE  -- ELW
        WHEN LENGTH(ticker) = 10 THEN FALSE  -- OTC
        ELSE TRUE
    END;
```

---

## 12. 모니터링 강화

### 12.1 브로드캐스터 메트릭

**파일**: `src/websocket/metrics.py` (신규)

```python
"""
브로드캐스터 성능 모니터링
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, Any


class BroadcasterMetrics:
    """
    브로드캐스터 성능 모니터링
    """

    def __init__(self):
        self._broadcast_counts = defaultdict(int)
        self._subscriber_counts = defaultdict(lambda: defaultdict(int))
        self._last_broadcast_time = None
        self._error_counts = defaultdict(int)

    def record_broadcast(self, ticker: str, subscriber_count: int):
        """브로드캐스트 기록"""
        self._broadcast_counts[ticker] += 1
        self._subscriber_counts[ticker][subscriber_count] += 1
        self._last_broadcast_time = datetime.now()

    def record_error(self, ticker: str):
        """에러 기록"""
        self._error_counts[ticker] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 반환"""
        return {
            "total_broadcasts": sum(self._broadcast_counts.values()),
            "broadcasts_by_ticker": dict(self._broadcast_counts),
            "subscriber_counts": {k: dict(v) for k, v in self._subscriber_counts.items()},
            "error_counts": dict(self._error_counts),
            "last_broadcast_time": self._last_broadcast_time.isoformat() if self._last_broadcast_time else None,
        }

    def reset_metrics(self) -> None:
        """메트릭 초기화 (매일 초기화)"""
        self._broadcast_counts.clear()
        self._subscriber_counts.clear()
        self._error_counts.clear()


# 전역 인스턴스
broadcaster_metrics = BroadcasterMetrics()


# 메트릭 엔드포인트
@router.get("/ws/metrics")
async def websocket_metrics():
    """WebSocket 브로드캐스터 메트릭"""
    return broadcaster_metrics.get_metrics()
```

---

## 13. 단계별 구현 계획 (수정)

### Phase 1: ELW 유효성 검사 수정 (1일)

| 작업 | 내용 | 파일 |
|------|------|------|
| ticker 유효성 검사 수정 | `_is_valid_ticker()` 추가 | `src/websocket/server.py` |
| subscribe() 수정 | `isdigit()` 체크 제거 | `src/websocket/server.py` |
| unsubscribe() 수정 | 동일하게 적용 | `src/websocket/server.py` |

### Phase 2: ELW 폴링 지원 (3일)

| 작업 | 내용 | 파일 |
|------|------|------|
| ELW 종목 식별 함수 | `_is_elw_ticker()` | `src/websocket/kiwoom_bridge.py` |
| ELW 폴링 태스크 | `fetch_elw_prices()` | `tasks/elw_tasks.py` |
| Celery Beat 스케줄링 | ELW 주기적 폴링 | `tasks/celery_app.py` |

### Phase 3: 폴링 API 엔드포인트 (2일)

| 작업 | 내용 | 파일 |
|------|------|------|
| 폴링 엔드포인트 구현 | `/api/kr/realtime-prices/polling` | `services/api_gateway/routes/stocks.py` |
| 캐시 통합 | 기존 `CacheClient` 활용 | `services/api_gateway/routes/stocks.py` |

### Phase 4: VCP 스캐너 전체 종목 확장 (3일)

| 작업 | 내용 | 파일 |
|------|------|------|
| 스캔 요청 모델 확장 | `ScanRequest` | `services/vcp_scanner/main.py` |
| 전체 종목 스캔 로직 | DB 쿼리 최적화 | `services/vcp_scanner/main.py` |
| ELW 필터링 옵션 추가 | `exclude_elw` | `services/vcp_scanner/main.py` |

### Phase 5: 모니터링 강화 (2일)

| 작업 | 내용 | 파일 |
|------|------|------|
| 메트릭 모니터링 추가 | `BroadcasterMetrics` | `src/websocket/metrics.py` |
| 메트릭 엔드포인트 | `/ws/metrics` | `services/api_gateway/routes/stocks.py` |

---

## 14. 테스트 및 검증

### 14.1 단위 테스트

```python
# tests/unit/test_broadcaster.py

import pytest
from src.websocket.server import ConnectionManager

def test_is_valid_ticker():
    """종목코드 유효성 검사 테스트"""
    manager = ConnectionManager()

    # 일반 주식
    assert manager._is_valid_ticker("005930") == True
    assert manager._is_valid_ticker("000660") == True

    # ELW
    assert manager._is_valid_ticker("0015N0") == True
    assert manager._is_valid_ticker("493330") == True

    # K-OTC
    assert manager._is_valid_ticker("0152301010") == False

    # 잘못된 형식
    assert manager._is_valid_ticker("") == False
    assert manager._is_valid_ticker("123") == False
    assert manager._is_valid_ticker("ABC") == False


def test_elw_identification():
    """ELW 종목 식별 테스트"""
    from src.websocket.kiwoom_bridge import KiwoomWebSocketBridge

    bridge = KiwoomWebSocketBridge()

    # KOSPI ELW (알파벳 포함)
    assert bridge._is_elw_ticker("0015N0") == True
    assert bridge._is_elw_ticker("0025N0") == True

    # KOSDAQ ELW (범위 내 숫자)
    assert bridge._is_elw_ticker("493330") == True
    assert bridge._is_elw_ticker("523330") == True

    # 일반 주식
    assert bridge._is_elw_ticker("005930") == False
    assert bridge._is_elw_ticker("000660") == False
```

### 14.2 통합 테스트

```python
# tests/integration/test_elw_polling.py

import pytest
from tasks.elw_tasks import fetch_elw_prices

@pytest.mark.asyncio
async def test_elw_price_fetching():
    """ELW 가격 폴링 테스트"""
    elw_tickers = ["0015N0", "493330"]

    results = await fetch_elw_prices(elw_tickers)

    assert len(results) > 0
    # 가격 데이터 확인
    for ticker, data in results.items():
        if data:
            assert "price" in data
            assert "change" in data
            assert data["is_elw"] == True


@pytest.mark.asyncio
async def test_polling_api():
    """폴링 API 엔드포인트 테스트"""
    from fastapi.testclient import TestClient
    from services.api_gateway.main import app

    client = TestClient(app)
    response = client.get("/api/kr/realtime-prices/polling?tickers=005930,0015N0")

    assert response.status_code == 200
    data = response.json()
    assert "prices" in data
    assert data["total"] > 0
```

---

## 15. 운영 가이드

### 15.1 장 시작/종료 스케줄링

```python
# 장 시작 전 (8:50)
- 기본 종목 브로드캐스터 시작
- ELW 종목 리스트 동기화

# 장 중 (9:30 - 15:30)
- 실시간 가격 브로드캐스트 (5초 간격)
- ELW 폴링 (1분 간격)

# 장 마감 후 (15:30)
- 가격 캐시 무효화
- 브로드캐스터 중지 (또는 기본 종목만)
```

### 15.2 캐시 TTL 튜닝

| 데이터 유형 | 개장 시 | 장 마감 후 |
|-------------|---------|------------|
| 가격 (PRICE) | 60초 | 300초 |
| 시그널 (SIGNAL) | 900초 | 3600초 |
| 시장 (MARKET) | 30초 | 300초 |

### 15.3 모니터링 알림 설정

```python
# 알림 조건
- 브로드캐스트 실패율 > 10%
- ELW 폴링 실패 > 5분 연속
- WebSocket 연결 수 < 1 (정상이면 0 이상)
- 캐시 적중률 < 50%
```

---

## 16. 요약

### 16.1 기존 코드 활용

- ✅ `CacheClient` - 가격 캐싱
- ✅ `HeartbeatManager` - ping/pong
- ✅ `RedisSubscriber` - Celery → WebSocket

### 16.2 신규 구현 필요

- ⚠️ `_is_valid_ticker()` - ELW 유효성 검사
- ⚠️ `_is_elw_ticker()` - ELW 식별
- ⚠️ `tasks/elw_tasks.py` - ELW 폴링
- ⚠️ `/realtime-prices/polling` - 폴링 API
- ⚠️ `BroadcasterMetrics` - 메트릭

### 16.3 수정 필요

- ⚠️ `ConnectionManager.subscribe()` - ticker.isdigit() 제거
- ⚠️ `services/vcp_scanner/main.py` - ScanRequest 모델 확장

---

*백엔드 개선 방안 (보완판) 종료*
