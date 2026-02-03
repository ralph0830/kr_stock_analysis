# 백엔드 실시간 가격 브로드캐스팅 분석 보고서

**분석 일자**: 2026-02-03
**분석 유형**: 백엔드 검사 및 루트 원인 분석
**심각도**: 높음 (기능 미작동)

---

## 1. 실행 요약

### 1.1 문제 현상

**실시간 가격 브로드캐스팅 시스템이 ELW 종목을 지원하지 않음**

| 항목 | 상태 |
|------|------|
| Kiwoom WebSocket Bridge | ✅ 실행 중 |
| Kiwoom REST API | ✅ 데이터 수신 중 |
| Price Broadcaster | ✅ 실행 중 |
| ELW 종목 구독 처리 | ❌ `isdigit()` 체크로 차단 |
| 구독자 수 | 0명 (모든 price 토픽) |

### 1.2 핵심 발견

**백엔드 코드의 `ticker.isdigit()` 체크가 ELW 종목 차단**

```python
# src/websocket/server.py:162-177
if topic.startswith("price:"):
    ticker = topic.split(":", 1)[1]

    # ticker는 6자리 숫자여야 함  ← 문제!
    if ticker.isdigit() and len(ticker) == 6:
        ws_bridge = get_kiwoom_ws_bridge()
        if ws_bridge and ws_bridge.is_running():
            asyncio.create_task(ws_bridge.add_ticker(ticker))
```

### 1.3 데이터 흐름 분석

```
프론트엔드 → WebSocket 서버 → KiwoomWebSocketBridge → Kiwoom Pipeline
                ↓                    ↓                    ↓
          subscribe() 처리       active_tickers 체크   실시간 데이터 수신
          (isdigit() 차단)       (등록 안 됨)           (전송 안 됨)
```

---

## 2. 상세 분석

### 2.1 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Server                         │
│  ┌──────────────────┐        ┌──────────────────────────┐  │
│  │ ConnectionManager│        │ PriceUpdateBroadcaster   │  │
│  │                  │        │                          │  │
│  │ - active_conn    │        │ - DEFAULT_TICKERS        │  │
│  │ - subscriptions  │◄───────│ - _active_tickers        │  │
│  └────────┬─────────┘        └───────────┬──────────────┘  │
│           │                               │                 │
│  ┌────────▼───────────────────────────────▼───────────┐    │
│  │           subscribe(topic) 메서드                  │    │
│  │                                                       │    │
│  │  if topic.startswith("price:"):                     │    │
│  │      ticker = topic.split(":", 1)[1]                │    │
│  │      if ticker.isdigit() and len(ticker) == 6:  ← 문제!│
│  │          ws_bridge.add_ticker(ticker)               │    │
│  └───────────────────────────┬───────────────────────────┘    │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              KiwoomWebSocketBridge                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  _on_realtime_data(price: RealtimePrice)            │   │
│  │                                                       │   │
│  │  if ticker not in self._active_tickers:             │   │
│  │      return  ← 구독 중이 아니면 브로드캐스트 안 함  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  _active_tickers: Set[str]  (isdigit() 통과한 종목만 저장)  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 실제 브로드캐스트 로그 분석

```
[WS BRIDGE] Broadcasting price update for 000660: 890000.0
[BROADCAST] Topic=price:000660, subscribers=0
[BROADCAST] No recipients found to send to
```

**분석**:
1. ✅ Kiwoom WebSocket Bridge가 실시간 가격 수신 (SK하이닉스 890,000원)
2. ✅ `price:000660` 토픽으로 브로드캐스트 시도
3. ❌ `subscribers=0` → 구독자가 없어 전송 안 됨

**왜 구독자가 0명인가?**
- 프론트엔드는 ELW 종목(`0015N0`, `493330`, ...) 구독 시도
- 백엔드 `subscribe()` 메서드에서 ELW 차단 (`isdigit()` 체크)
- `subscriptions` 딕셔너리에 ELW 토픽이 등록되지 않음
- 따라서 브로드캐스트 시 구독자를 찾지 못함

### 2.3 WebSocket 통계 분석

**엔드포인트**: `GET /ws/stats`

```json
{
  "active_connections": 1,
  "subscriptions": {
    "price:005930": 0,
    "price:000660": 0,
    "signals": 0,
    "market-gate": 7
  },
  "bridge_running": true,
  "bridge_tickers": [
    "035420", "217590", "491000", "005380",
    "000020", "028260", "005930", "000660", "493330"
  ],
  "broadcaster_running": true,
  "active_tickers": [],
  "heartbeat_running": false
}
```

**분석**:
- `bridge_tickers`: 일부 ELW 포함 (`217590`, `491000`, `493330`)
- `subscriptions`: ELW 토픽 누락 (`price:0015N0` 등 없음)
- `active_tickers`: 비어있음 → `price_broadcaster`에 종목 없음

### 2.4 코드 분석

#### ConnectionManager.subscribe()

**파일**: `src/websocket/server.py:144-177`

```python
def subscribe(self, client_id: str, topic: str) -> None:
    """
    토픽 구독

    Note:
        topic이 'price:{ticker}' 형식이면 자동으로 KiwoomWebSocketBridge에 ticker 추가
    """
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    self.subscriptions[topic].add(client_id)  # ← 구독자 등록
    logger.info(f"Client {client_id} subscribed to {topic}")

    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ticker는 6자리 숫자여야 함  ← 문제!
        if ticker.isdigit() and len(ticker) == 6:
            # KiwoomWebSocketBridge에 ticker 추가 (실시간 데이터)
            from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                import asyncio
                asyncio.create_task(ws_bridge.add_ticker(ticker))
                print(f"[WS BRIDGE] Added ticker to KiwoomWebSocketBridge: {ticker}")
            else:
                # WebSocket 브릿지가 없으면 price_broadcaster에 추가 (폴링 fallback)
                from src.websocket.server import price_broadcaster
                price_broadcaster.add_ticker(ticker)
```

**문제점**:
1. `self.subscriptions[topic].add(client_id)`는 무조건 실행됨
2. 하지만 `isdigit()` 체크를 통과하지 못하면 `ws_bridge.add_ticker()`가 호출되지 않음
3. 결과: 구독자는 등록되었지만, 실시간 데이터를 받을 `active_tickers`에는 추가되지 않음

#### KiwoomWebSocketBridge._on_realtime_data()

**파일**: `src/websocket/kiwoom_bridge.py:99-115`

```python
async def _on_realtime_data(self, price: RealtimePrice) -> None:
    """
    실시간 데이터 수신 시 처리

    Args:
        price: 실시간 가격 데이터
    """
    if not self._running:
        print(f"[WS BRIDGE] Not running, ignoring price data for {price.ticker}")
        return

    ticker = price.ticker

    # 구독 중인 종목인지 확인
    if ticker not in self._active_tickers:  # ← active_tickers에 없으면 무시
        print(f"[WS BRIDGE] Ticker {ticker} not in active_tickers: {self._active_tickers}")
        return

    # WebSocket으로 브로드캐스트
    try:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"[WS BRIDGE] Broadcasting price update for {ticker}: {price.price}")
        await connection_manager.broadcast(
            {
                "type": "price_update",
                "ticker": ticker,
                "data": {
                    "price": price.price,
                    "change": price.change,
                    "change_rate": price.change_rate,
                    "volume": price.volume,
                    "bid_price": price.bid_price,
                    "ask_price": price.ask_price,
                },
                "timestamp": timestamp,
            },
            topic=f"price:{ticker}",
        )
```

**문제점**:
- `active_tickers`에 등록되지 않은 종목은 브로드캐스트되지 않음
- ELW 종목은 `isdigit()` 체크로 인해 `active_tickers`에 추가되지 않음

#### ELW 종목 코드 형식

| 종목 | 코드 | `isdigit()` | 길이 | 통과 여부 |
|------|------|-------------|------|----------|
| 아로마티카 | `0015N0` | False | 6 | ❌ |
| 지에프아이 | `493330` | True | 6 | ✅ |
| 티엠씨 | `217590` | True | 6 | ✅ |
| 엔비알모션 | `0004V0` | False | 6 | ❌ |
| 리브스메드 | `491000` | True | 6 | ✅ |
| 유진챔피언 | `0120X0` | False | 6 | ❌ |

---

## 3. 근본 원인 (Root Cause)

### 3.1 직접 원인

**`ticker.isdigit()` 체크가 ELW 종목을 차단**

```python
# src/websocket/server.py:165
if ticker.isdigit() and len(ticker) == 6:  # ELW 차단
```

### 3.2 설계상 문제

1. **일반 종목 가정**: 시스템이 모든 종목 코드가 6자리 숫자라고 가정
2. **ELW 미고려**: ELW(상장지수증권) 코드는 숫자+알파벳 조합
3. **구독자-브로드캐스트 불일치**: 구독자는 등록되지만 브로드캐스터는 전송 안 함

### 3.3 Kiwoom API 제약사항

Kiwoom API에서 ELW 종목 처리:

| 항목 | KOSPI/KOSDAQ | ELW |
|------|--------------|-----|
| 종목 코드 | 6자리 숫자 | 6자리 (숫자+알파벳) |
| 실시간 데이터 | 지원 | 지원 (확인 필요) |
| REST API | 지원 | 지원 (확인 필요) |

---

## 4. 영향 분석

### 4.1 기능적 영향

| 기능 | 영향 |
|------|------|
| ELW 종목 실시간 가격 | ❌ 미작동 |
| KOSPI 대종목 실시간 가격 | ⚠️ 구독자 없어 동작 안 함 |
| Market Gate 실시간 지수 | ✅ 정상 |

### 4.2 시스템 영향

1. **구독 처리 불일치**: 구독자는 등록되지만 실시간 데이터를 받지 못함
2. **데이터 무단손**: Kiwoom에서 ELW 데이터를 받아도 전송되지 않음
3. **리소스 낭비**: WebSocket 연결은 유지되지만 데이터 전송 안 됨

---

## 5. 백엔드 개선 제안

### 5.1 우선순위 1: ELW 지원 추가 (높음)

#### ticker 검증 로직 수정

**파일**: `src/websocket/server.py`

```python
# ConnectionManager 클래스에 메서드 추가
class ConnectionManager:
    # ... 기존 코드 ...

    def _is_valid_ticker(self, ticker: str) -> bool:
        """
        종목 코드 유효성 검증

        - KOSPI/KOSDAQ: 6자리 숫자
        - ELW: 6자리 (숫자+알파벳 조합)

        Args:
            ticker: 종목 코드

        Returns:
            bool: 유효한 종목 코드이면 True
        """
        if not ticker or len(ticker) != 6:
            return False

        # 전체 숫자이거나, 알파벳이 포함된 6자리 코드
        if ticker.isdigit():
            return True

        # ELW 형식: 숫자+알파벞 조합
        has_digit = any(c.isdigit() for c in ticker)
        has_alpha = any(c.isalpha() for c in ticker)

        return has_digit and has_alpha

    def subscribe(self, client_id: str, topic: str) -> None:
        """토픽 구독 (ELW 지원)"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()

        self.subscriptions[topic].add(client_id)
        logger.info(f"Client {client_id} subscribed to {topic}")

        # price:{ticker} 형식이면 ticker 검증 후 추가
        if topic.startswith("price:"):
            ticker = topic.split(":", 1)[1]

            # ELW 포함한 종목 코드 검증
            if self._is_valid_ticker(ticker):
                # KiwoomWebSocketBridge에 ticker 추가
                from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
                ws_bridge = get_kiwoom_ws_bridge()
                if ws_bridge and ws_bridge.is_running():
                    import asyncio
                    asyncio.create_task(ws_bridge.add_ticker(ticker))
                    logger.info(f"[WS BRIDGE] Added ticker: {ticker}")
                else:
                    # Fallback: price_broadcaster에 추가
                    from src.websocket.server import price_broadcaster
                    price_broadcaster.add_ticker(ticker)
            else:
                logger.warning(f"Invalid ticker format: {ticker}")

    def unsubscribe(self, client_id: str, topic: str) -> None:
        """토픽 구독 취소 (ELW 지원)"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

            # 구독자가 없으면 ticker 제거
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]

                # price:{ticker} 형식이면 ticker 제거
                if topic.startswith("price:"):
                    ticker = topic.split(":", 1)[1]

                    from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge
                    ws_bridge = get_kiwoom_ws_bridge()
                    if ws_bridge and ws_bridge.is_running():
                        import asyncio
                        asyncio.create_task(ws_bridge.remove_ticker(ticker))
                        logger.info(f"[WS BRIDGE] Removed ticker: {ticker}")
```

#### KiwoomWebSocketBridge ELW 지원

**파일**: `src/websocket/kiwoom_bridge.py`

```python
class KiwoomWebSocketBridge:
    # ... 기존 코드 ...

    def _is_valid_ticker(self, ticker: str) -> bool:
        """ELW 포함한 종목 코드 유효성 검증"""
        if not ticker or len(ticker) != 6:
            return False

        if ticker.isdigit():
            return True

        has_digit = any(c.isdigit() for c in ticker)
        has_alpha = any(c.isalpha() for c in ticker)

        return has_digit and has_alpha

    async def add_ticker(self, ticker: str) -> bool:
        """종목 구독 추가 (ELW 지원)"""
        if not self._is_valid_ticker(ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            return False

        if ticker in self._active_tickers:
            return True

        self._active_tickers.add(ticker)
        logger.info(f"[WS BRIDGE] Added ticker to active_tickers: {ticker}")
        return True

    async def remove_ticker(self, ticker: str) -> bool:
        """종목 구독 제거"""
        if ticker in self._active_tickers:
            self._active_tickers.discard(ticker)
            logger.info(f"[WS BRIDGE] Removed ticker from active_tickers: {ticker}")
        return True
```

### 5.2 우선순위 2: PriceUpdateBroadcaster 개선 (중간)

**파일**: `src/websocket/price_provider.py`

기존 `PriceUpdateBroadcaster`에 구독 기반 트래킹 추가:

```python
from collections import defaultdict
from typing import Set, Dict

class PriceUpdateBroadcaster:
    """
    주기적 가격 브로드캐스터 (구독 기반 개선)

    - DEFAULT_TICKERS: 기본 모니터링 종목
    - 구독자가 있는 종목만 우선 브로드캐스트
    """

    DEFAULT_TICKERS = ["005930", "000660", "035420", "005380", "028260"]

    def __init__(self, interval_seconds: int = 5):
        self._interval_seconds = interval_seconds
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._active_tickers: Set[str] = set()
        # 추가: 구독자 트래킹
        self._subscriber_counts: Dict[str, int] = defaultdict(int)

    def add_ticker(self, ticker: str) -> None:
        """종목 추가"""
        self._active_tickers.add(ticker)
        logger.info(f"[BROADCAST] Added ticker: {ticker}")

    def remove_ticker(self, ticker: str) -> None:
        """종목 제거"""
        self._active_tickers.discard(ticker)
        logger.info(f"[BROADCAST] Removed ticker: {ticker}")

    def update_subscriber_count(self, ticker: str, count: int) -> None:
        """
        구독자 수 업데이트 (ConnectionManager에서 호출)

        구독자가 0이면 해당 종목 브로드캐스트 스킵
        """
        self._subscriber_counts[ticker] = count
        if count == 0 and ticker in self._active_tickers:
            logger.info(f"[BROADCAST] No subscribers for {ticker}, keeping in active_tickers")
```

### 5.3 우선순위 3: ELW 폴링 Fallback (중간)

#### Celery Beat를 이용한 ELW 폴링

**파일**: `tasks/elw_tasks.py` (신규)

```python
"""
ELW 종목 폴링 태스크

Kiwoom WebSocket이 지원하지 않는 ELW 종목의 경우
주기적으로 REST API로 가격 조회
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from src.database.session import get_db_session
from src.database.models import Stock
from src.kiwoom.rest_api import KiwoomRestAPI
from src.cache.cache_client import CacheClient

logger = logging.getLogger(__name__)


async def _get_elw_tickers() -> List[str]:
    """
    ELW 종목 목록 조회

    Returns:
        ELW 종목 코드 리스트
    """
    async with get_db_session() as db:
        # ELW 종목: 6자리 코드 중 알파벳 포함
        result = await db.execute(
            select(Stock.ticker).where(
                Stock.ticker.regexp_match("^[0-9]{5}[A-Z0-9]$")
            )
        )
        return [row[0] for row in result.fetchall()]


async def _fetch_elw_prices(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    ELW 종목 가격 조회

    Args:
        tickers: 종목 코드 리스트

    Returns:
        {ticker: price_data} 딕셔너리
    """
    cache = CacheClient()
    prices = {}

    for ticker in tickers:
        try:
            # 캐시 확인
            cached = await cache.get(f"price:{ticker}")
            if cached:
                prices[ticker] = cached
                continue

            # Kiwoom REST API 조회
            api = KiwoomRestAPI.from_env()
            daily_prices = await api.get_daily_prices(ticker, days=1)

            if daily_prices:
                price_data = {
                    "price": daily_prices[0].close,
                    "change": daily_prices[0].close - daily_prices[0].open,
                    "change_rate": ((daily_prices[0].close - daily_prices[0].open) / daily_prices[0].open * 100)
                    if daily_prices[0].open > 0 else 0,
                    "volume": daily_prices[0].volume,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                prices[ticker] = price_data

                # 캐시 저장 (30초 TTL)
                await cache.set(f"price:{ticker}", price_data, ttl=30)

        except Exception as e:
            logger.error(f"Failed to fetch price for {ticker}: {e}")

    return prices


@shared_task(name="tasks.elw_tasks.fetch_elw_prices")
def fetch_elw_prices_sync() -> Dict[str, Any]:
    """
    ELW 종목 가격 폴링 (동기 wrapper)

    Celery Beat에서 주기적 실행 (장중 10초 간격)

    Returns:
        실행 결과
    """
    import asyncio

    try:
        # 비동기 함수 실행
        result = asyncio.run(_fetch_elw_prices_task())
        return result
    except Exception as e:
        logger.error(f"ELW price fetch task failed: {e}")
        return {"status": "error", "message": str(e)}


async def _fetch_elw_prices_task() -> Dict[str, Any]:
    """ELW 가격 조회 비동기 태스크"""
    tickers = await _get_elw_tickers()
    logger.info(f"Fetching prices for {len(tickers)} ELW tickers")

    prices = await _fetch_elw_prices(tickers)

    # WebSocket으로 브로드캐스트
    from src.websocket.server import connection_manager

    for ticker, price_data in prices.items():
        await connection_manager.broadcast(
            {
                "type": "price_update",
                "ticker": ticker,
                "data": price_data,
                "timestamp": price_data["timestamp"],
            },
            topic=f"price:{ticker}",
        )

    return {
        "status": "success",
        "count": len(prices),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

**Celery Beat 설정**: `tasks/celery_app.py`

```python
# 기존 beat_schedule에 추가
app.conf.beat_schedule = {
    # ... 기존 스케줄 ...
    "fetch-elw-prices": {
        "task": "tasks.elw_tasks.fetch_elw_prices_sync",
        "schedule": 10.0,  # 10초 간격
        "options": {"expires": 5.0},
    },
}
```

### 5.4 우선순위 4: CacheClient 활용 캐싱 (낮음)

프로젝트에 이미 구현된 `CacheClient` 활용:

```python
# src/cache/cache_client.py (기존)
from src.cache.cache_client import CacheClient

async def get_realtime_price(ticker: str) -> Optional[Dict[str, Any]]:
    """
    캐시된 실시간 가격 조회

    Args:
        ticker: 종목 코드

    Returns:
        가격 데이터 또는 None
    """
    cache = CacheClient()
    return await cache.get(f"price:{ticker}")


async def set_realtime_price(ticker: str, price_data: Dict[str, Any]) -> None:
    """
    실시간 가격 캐시 저장

    Args:
        ticker: 종목 코드
        price_data: 가격 데이터
    """
    cache = CacheClient()
    await cache.set(f"price:{ticker}", price_data, ttl=60)  # 1분 TTL
```

---

## 6. API 엔드포인트 개선

### 6.1 실시간 가격 엔드포인트

**파일**: `services/api_gateway/routes/stocks.py`

```python
from fastapi import Query
from src.cache.cache_client import CacheClient

@router.get("/realtime-price")
async def get_realtime_prices(
    tickers: str = Query(..., description="콤마로 구분된 종목 코드"),
    include_elw: bool = Query(False, description="ELW 포함 여부")
):
    """
    실시간 가격 조회 (폴링용)

    - 일반 종목: CacheClient에서 조회
    - ELW 종목: Kiwoom REST API에서 조회
    """
    ticker_list = [t.strip() for t in tickers.split(",")]
    cache = CacheClient()
    prices = {}

    for ticker in ticker_list:
        # 캐시 확인
        cached = await cache.get(f"price:{ticker}")
        if cached:
            prices[ticker] = cached
            continue

        # ELW 종목 처리
        if include_elw and not ticker.isdigit():
            api = get_kiwoom_api()
            if api:
                try:
                    daily_prices = await api.get_daily_prices(ticker, days=1)
                    if daily_prices:
                        price_data = {
                            "price": daily_prices[0].close,
                            "change": daily_prices[0].close - daily_prices[0].open,
                            "change_rate": ((daily_prices[0].close - daily_prices[0].open)
                                          / daily_prices[0].open * 100)
                            if daily_prices[0].open > 0 else 0,
                            "volume": daily_prices[0].volume,
                        }
                        prices[ticker] = price_data
                        # 캐시 저장
                        await cache.set(f"price:{ticker}", price_data, ttl=30)
                except Exception as e:
                    logger.error(f"Failed to fetch price for {ticker}: {e}")
        else:
            # 일반 종목 DB 조회
            from src.repositories.daily_price_repository import DailyPriceRepository
            async with get_db_session() as db:
                repo = DailyPriceRepository(db)
                latest = await repo.get_latest_price(ticker)
                if latest:
                    prices[ticker] = {
                        "price": latest.close,
                        "change": latest.close - latest.open,
                        "volume": latest.volume,
                    }

    return {
        "prices": prices,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

---

## 7. 테스트 계획

### 7.1 단위 테스트

**파일**: `tests/unit/test_websocket_elw.py` (신규)

```python
import pytest
from src.websocket.server import ConnectionManager


class TestConnectionManagerELW:
    """ConnectionManager ELW 지원 테스트"""

    def test_is_valid_ticker_kospi(self):
        """KOSPI 종목 코드 검증"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("005930") is True
        assert manager._is_valid_ticker("000660") is True
        assert manager._is_valid_ticker("035420") is True

    def test_is_valid_ticker_elw(self):
        """ELW 종목 코드 검증"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("0015N0") is True
        assert manager._is_valid_ticker("0004V0") is True
        assert manager._is_valid_ticker("0120X0") is True

    def test_is_valid_ticker_invalid(self):
        """잘못된 종목 코드"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("12345") is False  # 5자리
        assert manager._is_valid_ticker("1234567") is False  # 7자리
        assert manager._is_valid_ticker("ABCDEF") is False  # 알파벳만
        assert manager._is_valid_ticker("") is False  # 빈 문자열

    def test_subscribe_elw_ticker(self):
        """ELW 종목 구독 테스트"""
        manager = ConnectionManager()
        client_id = "test_client"

        # ELW 종목 구독
        manager.subscribe(client_id, "price:0015N0")

        # 구독 확인
        assert "price:0015N0" in manager.subscriptions
        assert client_id in manager.subscriptions["price:0015N0"]

    def test_unsubscribe_elw_ticker(self):
        """ELW 종목 구독 취소 테스트"""
        manager = ConnectionManager()
        client_id = "test_client"

        # 구독 후 취소
        manager.subscribe(client_id, "price:0015N0")
        manager.unsubscribe(client_id, "price:0015N0")

        # 구독 제거 확인
        assert "price:0015N0" not in manager.subscriptions
```

### 7.2 통합 테스트

**파일**: `tests/integration/test_elw_realtime.py` (신규)

```python
import pytest
from httpx import AsyncClient
from src.websocket.server import connection_manager
from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge


@pytest.mark.asyncio
class TestELWRealtimeFlow:
    """ELW 실시간 가격 흐름 테스트"""

    async def test_elw_subscribe_via_ws(self):
        """WebSocket을 통한 ELW 구독 테스트"""
        # 테스트용 WebSocket 연결 시뮬레이션
        client_id = "test_client"
        ticker = "0015N0"

        # 구독
        connection_manager.subscribe(client_id, f"price:{ticker}")

        # 구독 확인
        assert f"price:{ticker}" in connection_manager.subscriptions
        assert client_id in connection_manager.subscriptions[f"price:{ticker}"]

    async def test_elw_kiwoom_bridge_registration(self):
        """KiwoomWebSocketBridge 등록 테스트"""
        ws_bridge = get_kiwoom_ws_bridge()
        if not ws_bridge:
            pytest.skip("KiwoomWebSocketBridge not available")

        ticker = "0015N0"
        result = await ws_bridge.add_ticker(ticker)

        # 등록 확인
        assert result is True
        assert ticker in ws_bridge.get_active_tickers()

        # 정리
        await ws_bridge.remove_ticker(ticker)

    async def test_elw_price_broadcast(self, mock_kiwoom_price):
        """ELW 가격 브로드캐스트 테스트"""
        from src.kiwoom.base import RealtimePrice

        ws_bridge = get_kiwoom_ws_bridge()
        if not ws_bridge:
            pytest.skip("KiwoomWebSocketBridge not available")

        ticker = "0015N0"

        # 구독 설정
        connection_manager.subscribe("test_client", f"price:{ticker}")
        await ws_bridge.add_ticker(ticker)

        # 모의 가격 데이터 생성
        mock_price = RealtimePrice(
            ticker=ticker,
            price=50000,
            change=1000,
            change_rate=2.0,
            volume=10000,
            bid_price=49500,
            ask_price=50500,
        )

        # 브로드캐스트 (실제로는 Kiwoom에서 수신)
        # 테스트에서는 직접 호출
        await ws_bridge._on_realtime_data(mock_price)

        # 정리
        await ws_bridge.remove_ticker(ticker)
        connection_manager.unsubscribe("test_client", f"price:{ticker}")
```

---

## 8. 권장 사항

### 8.1 단기 (즉시 실행)

**`isdigit()` 체크 제거 및 `_is_valid_ticker()` 추가**

1. `ConnectionManager._is_valid_ticker()` 메서드 추가
2. `subscribe()`, `unsubscribe()`에서 검증 로직 적용
3. `KiwoomWebSocketBridge`에 동일한 검증 로직 추가
4. 단위 테스트 작성으로 ELW 종목 처리 확인

### 8.2 중기 (1-2주)

1. **구독 기반 브로드캐스터**: `PriceUpdateBroadcaster`에 구독자 트래킹 추가
2. **ELW 폴링 Fallback**: `tasks/elw_tasks.py` Celery 태스크 구현
3. **API 엔드포인트 개선**: `/realtime-price`에 ELW 지원 추가

### 8.3 장기 (1개월 이상)

1. Kiwoom API ELW 지원 완전 검증
2. 모니터링 및 알림 시스템 구축
3. 성능 최적화 (배치 조회, 캐싱 전략)

---

## 9. 참고 자료

### 9.1 관련 파일

| 경로 | 설명 |
|------|------|
| `src/websocket/server.py` | WebSocket 서버 및 ConnectionManager |
| `src/websocket/kiwoom_bridge.py` | Kiwoom WebSocket Bridge |
| `src/websocket/price_provider.py` | PriceUpdateBroadcaster |
| `src/cache/cache_client.py` | Redis 캐시 클라이언트 |
| `src/kiwoom/rest_api.py` | Kiwoom REST API 클라이언트 |
| `tasks/celery_app.py` | Celery 설정 |
| `services/api_gateway/routes/stocks.py` | 주식 관련 API 엔드포인트 |

### 9.2 API 엔드포인트

```
GET /ws/stats               # WebSocket 통계
POST /ws/subscribe/{ticker} # 종목 구독 추가
DELETE /ws/subscribe/{ticker} # 종목 구독 제거
GET /ws/tickers             # 활성 종목 목록
GET /api/stocks/realtime-price # 실시간 가격 조회 (개선 제안)
```

### 9.3 환경 변수

```bash
# .env
USE_KIWOOM_REST=true        # Kiwoom REST API 사용 여부
REDIS_URL=redis://localhost:6380/0  # Redis URL
CELERY_BROKER_URL=redis://localhost:6380/1  # Celery Broker
```

---

*보고서 종료*
