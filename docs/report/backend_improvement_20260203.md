# 백엔드 개선 방안
**전체 종목 실시간 가격 지원**

작성 일자: 2026-02-03
목표: VCP 스캐너로 선별된 모든 종목(KOSPI/KOSDAQ/ELW)의 실시간 가격 브로드캐스트

---

## 1. 현재 시스템 분석

### 1.1 브로드캐스터 현황

```python
# src/websocket/server.py
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
# src/websocket/server.py:144-177
def subscribe(self, client_id: str, topic: str) -> None:
    # ...

    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ticker는 6자리 숫자여야 함  ← 문제!
        if ticker.isdigit() and len(ticker) == 6:
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
```

**문제점**:
- `ticker.isdigit()` 체크로 ELW 종목(0015N0 등) 제외됨
- 6자리 ELW(493330)는 통과하지만 Kiwoom 브리지에서 미지원

---

## 2. 동적 브로드캐스터 구현

### 2.1 구독 기반 브로드캐스터

**파일**: `src/websocket/server.py`

```python
class DynamicPriceBroadcaster(PriceUpdateBroadcaster):
    """
    구독 기반 동적 가격 브로드캐스터

    클라이언트가 구독하는 종목만 실시간으로 브로드캐스트
    """

    def __init__(self, interval_seconds: int = 5):
        super().__init__(interval_seconds)
        self._subscribed_tickers: Dict[str, Set[str]] = defaultdict(set)
        # {ticker: {client_id1, client_id2, ...}}

    def get_subscribed_tickers(self) -> Set[str]:
        """구독 중인 모든 종목 반환"""
        # 한 명 이상이 구독한 종목만
        return {
            ticker for ticker, clients in self._subscribed_tickers.items()
            if len(clients) > 0
        }

    def add_ticker_subscription(self, client_id: str, ticker: str) -> None:
        """
        종목 구독 추가

        Args:
            client_id: 클라이언트 ID
            ticker: 종목코드
        """
        self._subscribed_tickers[ticker].add(client_id)
        logger.info(f"[BROADCASTER] Client {client_id[:8]} subscribed to {ticker}")
        logger.debug(f"[BROADCASTER] Current subscriptions: {self.get_subscribed_tickers()}")

    def remove_ticker_subscription(self, client_id: str, ticker: str) -> None:
        """
        종목 구독 제거
        """
        if ticker in self._subscribed_tickers:
            self._subscribed_tickers[ticker].discard(client_id)

            # 구독자가 0명이면 Kiwoom 브리지에서도 제거
            if len(self._subscribed_tickers[ticker]) == 0:
                ws_bridge = get_kiwoom_ws_bridge()
                if ws_bridge:
                    asyncio.create_task(ws_bridge.remove_ticker(ticker))
                logger.info(f"[BROADCASTER] No more subscribers for {ticker}, removed")

    def get_subscriber_count(self, ticker: str) -> int:
        """종목별 구독자 수 반환"""
        return len(self._subscribed_tickers.get(ticker, set()))

    async def _broadcast_loop(self):
        """브로드캐스트 루프 (동적 종목 지원)"""
        while self._is_running:
            try:
                # 브로드캐스트할 종목 결정
                # 1. 구독된 종목 (우선)
                # 2. 기본 종목 (구독자가 없을 때만)
                subscribed_tickers = self.get_subscribed_tickers()

                if not subscribed_tickers:
                    # 구독자가 없으면 기본 종목만 브로드캐스트
                    tickers_to_broadcast = self.DEFAULT_TICKERS
                    logger.debug("[BROADCASTER] No subscriptions, using default tickers")
                else:
                    # 구독된 종목 + 기본 종목 합치
                    tickers_to_broadcast = subscribed_tickers | self.DEFAULT_TICKERS

                if not tickers_to_broadcast:
                    await asyncio.sleep(self.interval_seconds)
                    continue

                logger.info(f"[BROADCASTER] Broadcasting {len(tickers_to_broadcast)} tickers: {tickers_to_broadcast}")

                # 가격 데이터 조회
                if os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
                    price_updates = await self._fetch_prices_from_kiwoom(tickers_to_broadcast)
                else:
                    price_updates = await self._fetch_prices_from_db(tickers_to_broadcast)

                if not price_updates:
                    logger.warning("[BROADCASTER] Failed to fetch prices")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                # 브로드캐스트
                for ticker, data in price_updates.items():
                    subscriber_count = self.get_subscriber_count(ticker)
                    logger.info(f"[BROADCAST] Broadcasting {ticker} to {subscriber_count} subscribers")

                    await connection_manager.broadcast(
                        {
                            "type": "price_update",
                            "ticker": ticker,
                            "data": data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        topic=f"price:{ticker}",
                    )

            except Exception as e:
                logger.error(f"[BROADCASTER] Error in broadcast loop: {e}")

            await asyncio.sleep(self.interval_seconds)


# 전역 인스턴스 교체
price_broadcaster = DynamicPriceBroadcaster()
```

### 2.2 구독 처리 수정

**파일**: `src/websocket/server.py`

```python
def subscribe(self, client_id: str, topic: str) -> None:
    """
    토피 구독 (전체 종목 지원)

    Args:
        client_id: 클라이언트 ID
        topic: 구독할 토픽 (예: "price:005930", "price:0015N0")
    """
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    self.subscriptions[topic].add(client_id)
    logger.info(f"[SUBSCRIBE] Client {client_id[:8]}... → topic: {topic}")

    # price:{ticker} 형식 처리
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ELW 지원: isdigit() 체크 제거
        # 대신 유효성 검증으로 변경
        if self._is_valid_ticker(ticker):
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                # Kiwoom 브리지에 추가 (ELW 포함)
                asyncio.create_task(ws_bridge.add_ticker(ticker))
                logger.info(f"[WS BRIDGE] Added ticker: {ticker}")
            else:
                # 브리지 없으면 브로드캐스터에 추가
                price_broadcaster.add_ticker_subscription(client_id, ticker)
        else:
            logger.warning(f"[SUBSCRIBE] Invalid ticker format: {ticker}")

def _is_valid_ticker(self, ticker: str) -> bool:
    """
    종목코드 유효성 검사

    - KOSPI/KOSDAQ: 6자리 숫자
    - ELW: 6자리 (숫자+알파벳 또는 일부 6자리 숫자)
    - K-OTC: 10자리 숫자 (일단 미지원)
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

    # ELW 체크 (알파벳 포함)
    if ticker.isalpha():
        return False

    # 6자리 이상이면 유효 (KOSPI, KOSDAQ, ELW 모두 포함)
    if len(ticker) >= 6:
        return True

    return False
```

---

## 3. ELW 종목 지원

### 3.1 Kiwoom 브리지 ELW 처리

**파일**: `src/websocket/kiwoom_bridge.py`

```python
class KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket 브리지

    전체 종목 실시간 지원을 위한 개선
    """

    def __init__(self, ...):
        # ...
        self._subscribed_tickers: Set[str] = set()
        self._elw_polling_tasks: Dict[str, asyncio.Task] = {}

    async def add_ticker(self, ticker: str) -> bool:
        """
        종목 추가 (ELW 지원)

        Args:
            ticker: 종목코드 (ELW 포함)

        Returns:
            성공 여부
        """
        if ticker in self._subscribed_tickers:
            return True

        # ELW 체크
        is_elw = self._is_elw_ticker(ticker)

        if is_elw:
            logger.info(f"[WS BRIDGE] Adding ELW ticker: {ticker}")

            # Kiwoom WebSocket ELW 구독 시도
            success = await self._subscribe_elw_via_websocket(ticker)

            if not success:
                # WebSocket 실패 시 폴링으로 대체
                logger.info(f"[WS BRIDGE] ELW WebSocket failed, using polling for {ticker}")
                self._start_elw_polling(ticker)

            self._subscribed_tickers.add(ticker)
            return success
        else:
            # 일반 종목 처리
            return await self._subscribe_regular_ticker(ticker)

    def _is_elw_ticker(self, ticker: str) -> bool:
        """
        ELW 종목 체크

        ELW 형식:
        - 0015N0 (알파벳 포함 6자리)
        - 493330 (일부 6자리 ELW)
        """
        # 알파벳 포함 체크
        if any(c.isalpha() for c in ticker):
            return True

        # ELW 코드 범위 (KRX ELW는 특정 범위)
        # 예: 493330-523330
        elw_ranges = [
            (493330, 523330),  # KOSDAQ ELW
            (0015N0, 0035N0),  # KOSPI ELW (일부)
        ]

        for ticker_int in range(int(ticker), int(ticker) + 1):
            if any(start <= ticker_int <= end for start, end in elw_ranges):
                return True

        return False

    async def _subscribe_elw_via_websocket(self, elw_ticker: str) -> bool:
        """
        ELW WebSocket 구독 시도
        """
        try:
            # Kiwoom WebSocket ELW 전용 TR 사용
            elw_code = self._convert_to_elw_tr_code(elw_ticker)

            # 구독 메시지 전송
            message = {
                "tr_type": "ELW",  # ELW 전용 타입
                "ticker": elw_ticker,
                "elw_code": elw_code,
            }

            # Kiwoom WebSocket 전송 (구현 필요)
            await self._send_to_kiwoom_ws(message)

            logger.info(f"[WS BRIDGE] ELW subscription attempted: {elw_ticker}")
            return True

        except Exception as e:
            logger.error(f"[WS BRIDGE] ELW subscription failed: {e}")
            return False

    def _convert_to_elw_tr_code(self, ticker: str) -> str:
        """
        종목코드를 ELW TR 코드로 변환
        """
        # Kiwoom ELW TR 코드 변환 로직
        if "N" in ticker.upper():
            # 0015N0 -> 015N 형식
            return ticker.lstrip("0")
        return ticker

    def _start_elw_polling(self, elw_ticker: str) -> None:
        """
        ELW 폴링 태스크 시작
        """
        from tasks.elw_tasks import start_elw_polling

        if elw_ticker not in self._elw_polling_tasks:
            task = start_elw_polling.delay(elw_ticker)
            self._elw_polling_tasks[elw_ticker] = task
            logger.info(f"[WS BRIDGE] Started ELW polling for {elw_ticker}")
```

### 3.2 ELW 폴링 태스크

**파일**: `tasks/elw_tasks.py`

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

    # Celery beat를 통한 스케줄마다 폴링
    # (별도 beat 스케줄러 설정 필요)
    pass


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

        # 각 종목별로 가격 조회
        for ticker in tickers:
            try:
                # 일봉 데이터 조회 (가장 최근 데이터)
                daily_prices = await api.get_daily_prices(ticker, days=1)

                if daily_prices and len(daily_prices) > 0:
                    latest = daily_prices[0]
                    price = latest.get("price", 0)
                    change = latest.get("change", 0)
                    base_price = price - change
                    change_rate = (change / base_price * 100) if base_price > 0 else 0.0

                    results[ticker] = {
                        "ticker": ticker,
                        "price": price,
                        "change": change,
                        "change_rate": change_rate,
                        "volume": latest.get("volume", 0),
                        "timestamp": latest.get("date", datetime.now().isoformat()),
                        "is_elw": True,
                    }

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

    return [stock.ticker for stock in elw_stocks]
```

---

## 4. VCP 스캐너 전 종목 확장

### 4.1 스캔 엔드포인트 개선

**파일**: `services/vcp_scanner/main.py`

```python
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


@router.post("/scan")
async def trigger_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks
):
    """
    VCP 전체 종목 스캔

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
    async def analyze_single(stock: Stock) -> Optional[VCPResult]:
        try:
            return await analyzer.analyze(stock.ticker, stock.name)
        except Exception as e:
            logger.error(f"[SCAN] Error analyzing {stock.ticker}: {e}")
            return None

    # 병렬 분석 (동시성 확보)
    tasks = [
        analyze_single(stock)
        for stock in stocks
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 유효한 결과 필터링
    valid_results = [
        r for r in results
        if r and isinstance(r, VCPResult) and r.pattern_detected
    ]

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
    await save_signals(top_results)

    logger.info(f"[SCAN] Completed. Found {len(top_results)} signals")

    return {
        "total_scanned": len(stocks),
        "valid_signals": len(valid_results),
        "returned": len(top_results),
        "market": request.market,
        "filters": {
            "exclude_elw": request.exclude_elw,
            "min_market_cap": request.min_market_cap,
        },
        "results": [r.to_dict() for r in top_results],
    }


async def save_signals(signals: List[VCPResult]) -> None:
    """
    시그널 DB 저장
    """
    async with get_db_session() as db:
        # 기존 시그널 삭제
        await db.execute(delete(Signal).where(Signal.analysis_date == datetime.now().date()))

        # 새 시그널 저장
        for signal in signals:
            db_signal = Signal(
                ticker=signal.ticker,
                name=signal.name,
                signal_type="bullish" if signal.vcp_score > 70 else "bearish",
                grade=calculate_grade(signal.total_score),
                score=signal.total_score,
                vcp_score=signal.vcp_score,
                smartmoney_score=signal.smartmoney_score,
                entry_price=signal.current_price,
                target_price=calculate_target_price(signal.current_price, signal.total_score),
                analysis_date=signal.analysis_date,
            )
            db.add(db_signal)

        await db.commit()
```

---

## 5. 폴링 API 엔드포인트

### 5.1 실시간 가격 조회 API

**파일**: `services/api_gateway/routes/stocks.py`

```python
from fastapi import Query, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from src.kiwoom.rest_api import get_kiwoom_api


class PollingPriceResponse(BaseModel):
    """폴링 가격 응답"""
    ticker: str
    price: float
    change: float
    change_rate: float
    volume: int
    timestamp: str
    is_realtime: bool  # 항상 False (폴링 데이터)


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
    from src.websocket.cache_layer import RedisPriceCache

    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]

    # 캐시 확인
    cache = RedisPriceCache(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # 캐시된 데이터 조회
    cached_data = await cache.get_prices_batch(ticker_list)

    # 캐시 miss인 종목만 조회
    missed_tickers = [t for t in ticker_list if t not in cached_data]

    if missed_tickers:
        # ELW 필터링
        if not include_elw:
            missed_tickers = [t for t in missed_tickers if t.isdigit()]

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
                    }

                    # 캐시 저장
                    await cache.set_price(ticker, price_data)

                    cached_data[ticker] = price_data

            except Exception as e:
                logger.error(f"[POLLING] Failed to fetch price for {ticker}: {e}")

    # 전체 종목 데이터 반환
    return {
        "prices": cached_data,
        "cached": len(cached_data),
        "fetched": len(missed_tickers),
        "total": len(ticker_list),
    }
```

### 5.2 캐시 계층 구현

**파일**: `src/websocket/cache_layer.py`

```python
"""
실시간 가격 캐시 계층

WebSocket 미지원 종목을 위한 폴링 데이터 캐싱
"""

import json
import redis.asyncio as redis
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RedisPriceCache:
    """
    실시간 가격 Redis 캐시
    """

    - WebSocket 데이터를 캐싱하여 폴링 부하 감소
    - ELW/소형주 폴링 데이터 캐싱
    - TTL 기반 자동 만료
    """

    def __init__(self, redis_url: str, default_ttl: int = 10):
        """
        Args:
            redis_url: Redis 연결 URL
            default_ttl: 기본 캐시 유효시간(초)
        """
        self.redis = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.default_ttl = default_ttl

    async def get_price(self, ticker: str) -> Optional[Dict]:
        """
        종목별 캐시된 가격 조회

        Args:
            ticker: 종목코드

        Returns:
            가격 데이터 또는 None
        """
        key = f"price:{ticker}"
        data = await self.redis.get(key)

        if data:
            logger.debug(f"[CACHE] Cache hit for {ticker}")
            return json.loads(data)

        logger.debug(f"[CACHE] Cache miss for {ticker}")
        return None

    async def set_price(self, ticker: str, price_data: Dict, ttl: Optional[int] = None) -> None:
        """
        종목별 가격 캐시 저장

        Args:
            ticker: 종목코드
            price_data: 가격 데이터
            ttl: 캐시 유효시간(초), None이면 기본값 사용
        """
        key = f"price:{ticker}"
        ttl = ttl or self.default_ttl

        await self.redis.setex(
            key,
            ttl,
            json.dumps(price_data, ensure_ascii=False)
        )
        logger.debug(f"[CACHE] Cached price for {ticker} (TTL: {ttl}s)")

    async def get_prices_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        일괄 캐시 조회

        Args:
            tickers: 종목코드 리스트

        Returns:
            {ticker: price_data} 딕셔너리
        """
        keys = [f"price:{t}" for t in tickers]

        # 파이프라인으로 여러 키 조회 (멀티 get)
        pipeline = self.redis.pipeline()
        for key in keys:
            pipeline.get(key)

        results = await pipeline.execute()

        cached = {}
        for ticker, data in zip(tickers, results):
            if data:
                try:
                    cached[ticker] = json.loads(data)
                except json.JSONDecodeError:
                    logger.error(f"[CACHE] Failed to decode cache for {ticker}")

        logger.info(f"[CACHE] Batch cache hit: {len(cached)}/{len(tickers)}")
        return cached

    async def invalidate_ticker(self, ticker: str) -> None:
        """
        종목별 캐시 무효화
        """
        key = f"price:{ticker}"
        await self.redis.delete(key)
        logger.info(f"[CACHE] Invalidated cache for {ticker}")

    async def invalidate_all(self) -> None:
        """
        전체 가격 캐시 무효화
        """
        keys = await self.redis.keys("price:*")
        if keys:
            await self.redis.delete(*keys)
            logger.info(f"[CACHE] Invalidated {len(keys)} price caches")

    async def get_all_cached_prices(self) -> Dict[str, Dict]:
        """
        전체 캐시된 가격 조회
        """
        keys = await self.redis.keys("price:*")

        if not keys:
            return {}

        # 배치로 조회 (1000개씩)
        all_data = {}
        for i in range(0, len(keys), 1000):
            batch = keys[i:i+1000]
            pipeline = self.redis.pipeline()
            for key in batch:
                pipeline.get(key)

            results = await pipeline.execute()

            for key, data in zip(batch, results):
                if data:
                    ticker = key.split(":")[1]
                    try:
                        all_data[ticker] = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error(f"[CACHE] Failed to decode cache for {ticker}")

        return all_data


# 전역 인스턴스
_price_cache: Optional[RedisPriceCache] = None

def get_price_cache() -> RedisPriceCache:
    """가격 캐시 인스턴스 반환"""
    global _price_cache
    if _price_cache is None:
        _price_cache = RedisPriceCache(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
    return _price_cache
```

---

## 6. Celery Beat 스케줄링

### 6.1 ELW 폴링 스케줄

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
        crontab(hour=8, minute=30,
    )

    # ELW 종목 폴링 (장 중 10초 간격, 평일 9:30-15:30)
    sender.add_periodic_task(
        "poll-elw-prices",
        poll_elw_prices_in_market_hours(),
        crontab(
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/10",  # 10초 간격
        ),
    )

    # 가격 캐시 무효화 (장 마감 15:30)
    sender.add_periodic_task(
        "invalidate-price-cache",
        invalidate_price_cache_async.s(),
        crontab(hour=15, minute=30,
    )


@celery_app.task
async def poll_elw_prices_in_market_hours():
    """
    장 중 시간대 ELW 종목 폴링

    9:30 - 15:30 사이 10초 간격으로 폴링
    """
    from tasks.elw_tasks import sync_elw_tickers_from_db

    # ELW 종목 리스트 가져오기
    elw_tickers = await sync_elw_tickers_from_db()

    if not elw_tickers:
        logger.warning("[CELERY] No ELW tickers to poll")
        return

    # 가격 조회 및 브로드캐스트
    from tasks.elw_tasks import fetch_elw_prices

    results = await fetch_elw_prices(elw_tickers)

    logger.info(f"[CELERY] Polled {len(results)} ELW prices")


@celery_app.task
def invalidate_price_cache_async():
    """
    가격 캐시 무효화 (Celery Task)
    """
    from src.websocket.cache_layer import get_price_cache

    import asyncio

    async def _invalidate():
        cache = get_price_cache()
        await cache.invalidate_all()

    asyncio.run(_invalidate())
```

---

## 7. 데이터베이스 인덱스

### 7.1 실시간 조회 성능 최적화

```sql
-- 종목별 시가총액 인덱스 (스캔 대상 종목 선별에 필요)
CREATE INDEX IF NOT EXISTS idx_stock_market_cap_desc
ON stocks(market_code, market_cap DESC);

-- 종목 코드 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_ticker
ON stocks(ticker);

-- 일일 가격 인덱스 (최신 데이터 조회)
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date_desc
ON daily_prices(ticker, date DESC);

-- 실시간 지원 구분을 위한 컬럼 추가
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS realtime_supported BOOLEAN DEFAULT TRUE;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS ticker_category VARCHAR(10);

-- ELW 종목 업데이트
UPDATE stocks
SET
    ticker_category = CASE
        WHEN ticker REGEXP '[A-Za-z]' THEN 'ELW'
        WHEN LENGTH(ticker) = 10 THEN 'OTC'
        WHEN market_code = '0' THEN 'KOSPI'
        WHEN market_code = '10' THEN 'KOSDAQ'
        ELSE 'UNKNOWN'
    END,
    realtime_supported = CASE
        WHEN ticker REGEXP '[A-Za-z]' THEN FALSE  -- ELW
        WHEN LENGTH(ticker) = 10 THEN FALSE  -- OTC
        ELSE TRUE
    END;
```

---

## 8. 모니터링 및 로그

### 8.1 브로드캐스터 성능 모니터링

```python
# src/websocket/metrics.py

class BroadcasterMetrics:
    """
    브로드캐스터 성능 모니터링
    """

    def __init__(self):
        self._broadcast_counts = defaultdict(int)
        self._subscriber_counts = defaultdict(lambda: defaultdict(int))
        self._last_broadcast_time = None

    def record_broadcast(self, ticker: str, subscriber_count: int):
        """브로드캐스트 기록"""
        self._broadcast_counts[ticker] += 1
        self._subscriber_counts[ticker][subscriber_count] += 1
        self._last_broadcast_time = datetime.now()

    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 반환"""
        return {
            "total_broadcasts": sum(self._broadcast_counts.values()),
            "broadcasts_by_ticker": dict(self._broadcast_counts),
            "subscriber_counts": {k: dict(v) for k, v in self._subscriber_counts.items()},
            "last_broadcast_time": self._last_broadcast_time.isoformat() if self._last_broadcast_time else None,
        }

    def reset_metrics(self) -> None:
        """메트릭 초기화 (매일 초기화)"""
        self._broadcast_counts.clear()
        self._subscriber_counts.clear()


broadcaster_metrics = BroadcasterMetrics()


# 메트릭 엔드포인트
@router.get("/ws/metrics")
async def websocket_metrics():
    """WebSocket 브로드캐스터 메트릭"""
    return broadcaster_metrics.get_metrics()
```

---

## 9. 단계별 구현 계획

### Phase 1: 구독 기반 브로드캐스터 (1주)

| 작업 | 내용 | 파일 |
|------|------|------|
| 동적 브로드캐스터 클래스 | `DynamicPriceBroadcaster` | `src/websocket/server.py` |
| 구독 트래킹 수정 | `_subscribed_tickers` 관리 | `src/websocket/server.py` |
| ticker 유효성 검사 수정 | `_is_valid_ticker()` | `src/websocket/server.py` |
| 메트릭 모니터링 추가 | `BroadcasterMetrics` | `src/websocket/metrics.py` |

### Phase 2: ELW 폴링 지원 (1주)

| 작업 | 내용 | 파일 |
|------|------|------|
| ELW 종목 식별 함수 | `_is_elw_ticker()` | `src/websocket/kiwoom_bridge.py` |
| ELW 폴링 태스크 | `fetch_elw_prices()` | `tasks/elw_tasks.py` |
| Celery Beat 스케줄링 | ELW 주기적 폴링 | `tasks/celery_app.py` |

### Phase 3: 폴링 API 엔드포인트 (1주)

| 작업 | 내용 | 파일 |
|------|------|------|
| 폴링 엔드포인트 구현 | `/api/kr/realtime-prices/polling` | `services/api_gateway/routes/stocks.py` |
| 캐시 계층 구현 | `RedisPriceCache` | `src/websocket/cache_layer.py` |

### Phase 4: VCP 스캐너 전체 종목 확장 (2주)

| 작업 | 내용 | 파일 |
|------|------|------|
| 스캔 요청 모델 확장 | `ScanRequest` | `services/vcp_scanner/main.py` |
| 전체 종목 스캔 로직 | DB 쿼리 최적화 | `services/vcp_scanner/main.py` |
| ELW 필터링 옵션 추가 | `exclude_elw` | `services/vcp_scanner/main.py` |

---

## 10. 성능 최적화

### 10.1 데이터베이스 쿼리 최적화

```sql
-- 실시간 조회를 위한 인덱스
CREATE INDEX CONCURRENTLY idx_stocks_realtime
ON stocks(market_code, realtime_supported, market_cap DESC)
WHERE realtime_supported = TRUE;

-- VCP 스캔을 위한 인덱스
CREATE INDEX CONCURRENTLY idx_stocks_vcp_scan
ON stocks(listing_status, market_code, market_cap DESC)
WHERE listing_status = 'Y';
```

### 10_2 스캔 병렬화

```python
# 비동기 제너레이터를 활용한 병렬 스캔
import asyncio
from collections import defaultdict

async def analyze_all_stocks_analyzer(analyzer, stocks):
    """
    병렬 VCP 분석 (제너레이터 패턴)
    """
    semaphore = asyncio.Semaphore(10)  # 동시 10개 제한

    async def analyze_with_semaphore(stock):
        async with semaphore:
            return await analyzer.analyze(stock.ticker, stock.name)

    tasks = [analyze_with_semaphore(stock) for stock in stocks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

---

## 11. 테스트 및 검증

### 11_1 단위 테스트

```python
# tests/unit/test_broadcaster.py

import pytest
from src.websocket.server import DynamicPriceBroadcaster

def test_subscribed_tickers():
    """구독 종목 추가 테스트"""
    broadcaster = DynamicPriceBroadcaster()

    broadcaster.add_ticker_subscription("client1", "005930")
    broadcaster.add_ticker_subscription("client2", "005930")
    broadcaster.add_ticker_subscription("client1", "000660")

    assert broadcaster.get_subscriber_count("005930") == 2
    assert broadcaster.get_subscriber_count("000660") == 1

    assert broadcaster.get_subscribed_tickers() == {"005930", "000660"}


def test_elw_ticker_validation():
    """ELW 종목 유효성 검사 테스트"""
    from src.websocket.server import ConnectionManager

    manager = ConnectionManager()

    # 일반 주식
    assert manager._is_valid_ticker("005930") == True
    assert manager._is_valid_ticker("000660") == True

    # ELW
    assert manager._is_valid_ticker("0015N0") == True
    assert manager._is_valid_ticker("493330") == True

    # K-OTC
    assert manager._is_valid_ticker("0152301010") == False
```

---

*백엔드 개선 방안 종료*
