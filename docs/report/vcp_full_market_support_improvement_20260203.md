# VCP 스캐너 전체 종목 지원 개선 방안

**작성 일자**: 2026-02-03
**목적**: VCP 스캐너가 전 종목(KOSPI/KOSDAQ/ELW/K-OTC)을 스캔하고 실시간 가격을 제공하도록 개선

---

## 1. 현재 상태 분석

### 1.1 KRX 종목 코드 체계

| 구분 | 코드 형식 | 예시 | 비고 |
|------|-----------|------|------|
| **KOSPI 대형주** | 6자리 숫자 | 005930(삼성전자), 000660(SK하이닉스) | |
| **KOSPI 중/소형주** | 6자리 숫자 | 028260(삼성물산), 000020(동화약품) | |
| **KOSDAQ** | 6자리 숫자 | 051910(LG화학), 068270(셀트리온) | |
| **KOSPI ELW** | 6자리 + 1자리 | 0015N0, 0035N0, 0075N0 | 숫자+알파벳 |
| **KOSDAQ ELW** | 6자리 + 1자리 | 493330, 513330, 523330 | 6자리지만 ELW |
| **K-OTC** | 10자리 숫자 | 0152301010 (일반 ETF 제외) | |

### 1.2 현재 시스템 지원 현황

| 구분 | VCP 스캔 | 실시간 가격 | 문제 |
|------|-----------|-------------|------|
| **KOSPI 대형주** | ✅ | ✅ | |
| **KOSPI 중/소형주** | ✅ | ✅ (DEFAULT_TICKERS에 일부만) | 전체 미지원 |
| **KOSDAQ** | ✅ | ❌ | 미지원 |
| **ELW** | ✅ | ❌ | ticker.isdigit() 필터링 |
| **K-OTC** | ❌ | ❌ | 미지원 |

### 1.3 현재 브로드캐스터 설정

```python
# src/websocket/server.py
class PriceUpdateBroadcaster:
    DEFAULT_TICKERS = {"005930", "000660", "035420", "005380", "028260", "000020"}
    # 삼성전자, SK하이닉스, NAVER, 현대차, 삼성물산, 동화약품
```

**문제**:
- 고정 6종목만 브로드캐스트
- 나머지 KOSPI/KOSDAQ 종목은 실시간 지원 안 됨

---

## 2. 프론트엔드 개선점

### 2.1 실시간 가격 표시 개선

#### 문제
- 랜딩 페이지에서 시그널 종목(ELW)의 실시간 가격을 표시할 수 없음
- "데이터 대기 중..." 메시지가 지속됨

#### 개선 방안 A: 실시간 지원 종목 표시

```typescript
// frontend/app/page.tsx

// 실시간 지원 여부 체크 함수
const isRealtimeSupported = (ticker: string): boolean => {
  // ELW 체크 (숫자 5자리 + 알파벳 1자리)
  if (ticker.length === 6 && /[A-Za-z]/.test(ticker)) {
    return false;
  }
  // K-OTC 체크 (10자리)
  if (ticker.length === 10) {
    return false;
  }
  return true;
};

// 컴포넌트에서 지원 여부 표시
<RealtimePriceCard
  ticker={ticker}
  name={name}
  showRealtimeBadge={isRealtimeSupported(ticker)}  // 실시간 지원 뱃지 표시
/>
```

#### 개선 방안 B: 폴링 Fallback

```typescript
// frontend/components/RealtimePriceCard.tsx

// WebSocket 미지원 종목에 대한 폴링
export function RealtimePriceCard({ ticker, name }: RealtimePriceCardProps) {
  const { prices, getPrice, connected } = useRealtimePrices([ticker]);
  const realtimePrice = getPrice(ticker);

  // WebSocket으로 데이터 없으면 폴링으로 대체
  const [pollingPrice, setPollingPrice] = useState<StockPrice | null>(null);

  useEffect(() => {
    if (realtimePrice || connected) return;  // WebSocket 정상이면 폴링 안 함

    // 10초마다 폴링
    const fetchPollingPrice = async () => {
      try {
        const prices = await apiClient.getRealtimePrices([ticker]);
        setPollingPrice(prices[ticker] || null);
      } catch (e) {
        console.error(`Polling failed for ${ticker}:`, e);
      }
    };

    fetchPollingPrice();
    const interval = setInterval(fetchPollingPrice, 10000);

    return () => clearInterval(interval);
  }, [ticker, realtimePrice, connected]);

  const displayPrice = realtimePrice || pollingPrice;

  if (!displayPrice) {
    return <LoadingState />;
  }

  return <PriceDisplay data={displayPrice} isRealtime={!!realtimePrice} />;
}
```

#### 개선 방안 C: 종목별 실시간 지원 안내

```typescript
// frontend/components/RealtimePriceCard.tsx

interface RealtimePriceCardProps {
  ticker: string;
  name: string;
}

function getRealtimeSupportInfo(ticker: string): {
  supported: boolean;
  reason?: string;
} {
  // ELW 종목
  if (/[A-Za-z]/.test(ticker)) {
    return {
      supported: false,
      reason: "ELW 종목은 실시간 지원이 제한됩니다 (폴링으로 업데이트됨)",
    };
  }

  // K-OTC
  if (ticker.length === 10) {
    return {
      supported: false,
      reason: "K-OTC 종목은 실시간 지원이 제한됩니다",
    };
  }

  return { supported: true };
}

export function RealtimePriceCard({ ticker, name }: RealtimePriceCardProps) {
  const { supported, reason } = getRealtimeSupportInfo(ticker);
  const { prices, getPrice, connected } = useRealtimePrices(
    supported ? [ticker] : []  // 지원하지 않으면 구독 안 함
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold">{name}</h3>
          <p className="text-sm text-gray-500">{ticker}</p>
        </div>
        {!supported && (
          <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
            폴링 업데이트
          </span>
        )}
        {supported && connected && (
          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
            실시간
          </span>
        )}
      </div>

      {!supported && reason && (
        <p className="text-xs text-gray-500 mt-2">{reason}</p>
      )}

      {/* 가격 표시 */}
      <PriceDisplay ticker={ticker} />
    </div>
  );
}
```

### 2.2 시그널 종목 필터링 UI

```typescript
// frontend/app/page.tsx

const [marketFilter, setMarketFilter] = useState<"ALL" | "KOSPI" | "KOSDAQ">("ALL");
const [excludeELW, setExcludeELW] = useState(true);

// 필터링된 시그널
const filteredSignals = useMemo(() => {
  return signals.filter(signal => {
    if (marketFilter !== "ALL" && signal.market !== marketFilter) {
      return false;
    }
    if (excludeELW && isELW(signal.ticker)) {
      return false;
    }
    return true;
  });
}, [signals, marketFilter, excludeELW]);

// UI
<div className="flex gap-2 mb-4">
  <select
    value={marketFilter}
    onChange={(e) => setMarketFilter(e.target.value as any)}
    className="px-3 py-2 border rounded"
  >
    <option value="ALL">전체 시장</option>
    <option value="KOSPI">KOSPI</option>
    <option value="KOSDAQ">KOSDAQ</option>
  </select>

  <label className="flex items-center gap-2">
    <input
      type="checkbox"
      checked={excludeELW}
      onChange={(e) => setExcludeELW(e.target.checked)}
    />
    <span>ELW 제외</span>
  </label>
</div>
```

### 2.3 실시간 지원 종목 확장

```typescript
// frontend/hooks/useWebSocket.ts

// 실시간 지원 종목 목록
const REALTIME_SUPPORTED_TICKERS = new Set([
  "005930", "000660", "035420", "005380", "028260", "000020",
  // KOSDAQ 인기 종목
  "051910", "068270", "035720", "006400", "005930",
  // ... 확장 가능
]);

export function useRealtimePrices(tickers: string[]) {
  // 실시간 지원 종목만 구독
  const supportedTickers = tickers.filter(t =>
    REALTIME_SUPPORTED_TICKERS.has(t) || !isELW(t)
  );

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
    onPriceUpdate: (price) => { /* ... */ },
  });

  useEffect(() => {
    if (connected) {
      supportedTickers.forEach(t => subscribe(`price:${t}`));
    }
  }, [supportedTickers, connected, subscribe]);
}
```

---

## 3. 백엔드 개선점

### 3.1 브로드캐스터 동적 종목 관리

#### 문제
- 현재 DEFAULT_TICKERS가 고정되어 있음
- ELW/소형주 종목이 브로드캐스트되지 않음

#### 개선 방안 A: 구독 기반 동적 브로드캐스트

```python
# src/websocket/server.py

class DynamicPriceBroadcaster(PriceUpdateBroadcaster):
    """
    구독 기반 동적 가격 브로드캐스터

    클라이언트가 구독하는 종목만 브로드캐스트
    """

    def __init__(self, interval_seconds: int = 5):
        super().__init__(interval_seconds)
        self._subscribed_tickers: Set[str] = set()

    def add_subscribed_ticker(self, ticker: str) -> None:
        """클라이언트가 구독한 종목 추가"""
        self._subscribed_tickers.add(ticker)
        logger.info(f"[BROADCASTER] Added subscribed ticker: {ticker}")

    def remove_subscribed_ticker(self, ticker: str) -> None:
        """구독 해제 종목 제거"""
        self._subscribed_tickers.discard(ticker)
        logger.info(f"[BROADCASTER] Removed subscribed ticker: {ticker}")

    async def _broadcast_loop(self):
        """브로드캐스트 루프 (구독 기반)"""
        while self._is_running:
            try:
                # 브로드캐스트할 종목: 구독된 종목만
                tickers_to_broadcast = self._subscribed_tickers.copy()

                if not tickers_to_broadcast:
                    # 구독자가 없으면 기본 종목만 브로드캐스트
                    tickers_to_broadcast = self.DEFAULT_TICKERS

                if not tickers_to_broadcast:
                    await asyncio.sleep(self.interval_seconds)
                    continue

                # Kiwoom API에서 가격 조회
                price_updates = await self._fetch_prices_from_kiwoom(tickers_to_broadcast)

                # 브로드캐스트
                for ticker, data in price_updates.items():
                    await connection_manager.broadcast(
                        {
                            "type": "price_update",
                            "ticker": ticker,
                            "data": data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        topic=f"price:{ticker}",
                    )

                logger.info(f"[BROADCASTER] Broadcasted {len(price_updates)} tickers")

            except Exception as e:
                logger.error(f"[BROADCASTER] Error: {e}")

            await asyncio.sleep(self.interval_seconds)
```

#### 개선 방안 B: Kiwoom 브리지 ELW 지원

```python
# src/websocket/server.py

def subscribe(self, client_id: str, topic: str) -> None:
    # ...
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ELW 지원: ticker.isdigit() 체크 제거
        # 대신 길이와 형식으로 체크
        if len(ticker) >= 6:  # 6자리 이상 (일반 주식, ELW 모두 포함)
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
                logger.info(f"[WS BRIDGE] Added ticker: {ticker} (ELW 가능)")
            else:
                # 브리지 없으면 폴링 fallback
                price_broadcaster.add_subscribed_ticker(ticker)
```

### 3.2 VCP 스캐너 전 종목 확장

```python
# services/vcp_scanner/main.py

class ScanRequest(BaseModel):
    """스캔 요청 모델"""
    market: str = "ALL"  # KOSPI, KOSDAQ, ALL
    top_n: int = 30
    exclude_elw: bool = True  # ELW 제외 여부
    min_market_cap: Optional[int] = None  # 최소 시가총액
    max_tickers: int = 100  # 최대 스캔 종목 수

@router.post("/scan")
async def trigger_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    VCP 스캔 트리거

    - 전체 종목 스캔 지원
    - ELW 필터링 옵션
    - 시가총액 필터링
    """
    analyzer = get_analyzer()

    # 종목 리스트 가져오기
    async with get_db_session() as db:
        # market 필터링
        if request.market == "ALL":
            markets = ["KOSPI", "KOSDAQ"]
        else:
            markets = [request.market]

        # 쿼리 빌딩
        query = (
            select(Stock)
            .where(Stock.market.in_(markets))
            .where(Stock.listing_status == "Y")  # 상장 종목만
        )

        # ELW 제외
        if request.exclude_elw:
            # ticker가 6자리 숫자인 것만 (ELW 제외)
            query = query.where(Stock.ticker.regexp_match("^[0-9]{6}$"))

        # 시가총액 필터
        if request.min_market_cap:
            query = query.where(Stock.market_cap >= request.min_market_cap)

        # 최대 종목 수 제한
        query = query.order_by(Stock.market_cap.desc()).limit(request.max_tickers)

        result = await db.execute(query)
        stocks = result.scalars().all()

    # VCP 분석 (병렬 처리)
    tasks = [
        analyzer.analyze(stock.ticker, stock.name)
        for stock in stocks
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 유효한 결과만 필터링
    valid_results = [
        r for r in results
        if r and isinstance(r, VCPResult) and r.pattern_detected
    ]

    # 점수순 정렬
    valid_results.sort(key=lambda x: x.total_score, reverse=True)

    # 상위 N개 반환
    top_results = valid_results[:request.top_n]

    # DB 저장
    await save_signals(top_results)

    return {"results": [r.to_dict() for r in top_results]}
```

### 3.3 폴링 Fallback API

```python
# services/api_gateway/routes/stocks.py

@router.get("/realtime-prices")
async def get_realtime_prices_polling(
    tickers: str = Query(..., description="콤마로 구분된 종목코드"),
    include_elw: bool = Query(True, description="ELW 포함 여부"),
):
    """
    실시간 가격 조회 (폴링 방식)

    WebSocket 미지원 종목(ELW, K-OTC)을 위한 폴링 엔드포인트
    """
    from src.kiwoom.rest_api import get_kiwoom_api

    ticker_list = tickers.split(",")

    # ELW 필터링
    if not include_elw:
        ticker_list = [t for t in ticker_list if t.isdigit()]

    api = await get_kiwoom_api()
    if not api:
        raise HTTPException(status_code=503, detail="Kiwoom API not available")

    # 토큰 발급
    await api.issue_token()

    # 가격 조회
    prices = {}
    for ticker in ticker_list:
        try:
            # 일봉 데이터 조회 (최신 종가)
            daily_prices = await api.get_daily_prices(ticker, days=1)

            if daily_prices and len(daily_prices) > 0:
                latest = daily_prices[0]
                prices[ticker] = {
                    "price": latest.get("price", 0),
                    "change": latest.get("change", 0),
                    "change_rate": (latest.get("change", 0) /
                                  (latest.get("price", 1) - latest.get("change", 0)) * 100)
                                   if latest.get("price") else 0,
                    "volume": latest.get("volume", 0),
                    "timestamp": latest.get("date", datetime.now().isoformat()),
                    "is_realtime": False,  # 폴링 데이터임
                }
        except Exception as e:
            logger.error(f"Failed to fetch price for {ticker}: {e}")
            prices[ticker] = None

    return {"prices": prices}
```

### 3.4 ELW 종목 실시간 지원

```python
# src/websocket/kiwoom_bridge.py

class KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket 브리지

    ELW 종목 지원을 위한 확장
    """

    async def add_ticker(self, ticker: str) -> bool:
        """
        종목 추가 (ELW 지원)

        Args:
            ticker: 종목코드 (6자리, ELW 포함)

        Returns:
            성공 여부
        """
        if ticker in self._subscribed_tickers:
            return True

        # ELW 체크 및 처리
        is_elw = not ticker.isdigit()

        if is_elw:
            # ELW 종목 처리
            logger.info(f"[WS BRIDGE] Adding ELW ticker: {ticker}")

            # ELW는 별도 TR 또는 일봉 데이터로 대체
            elw_code = self._convert_elw_code(ticker)
            await self._subscribe_elw(elw_code)
        else:
            # 일반 종목
            await self._subscribe_stock(ticker)

        self._subscribed_tickers.add(ticker)
        return True

    def _convert_elw_code(self, ticker: str) -> str:
        """
        ELW 종목코드 변환

        Kiwoom에서 ELW는 별도 코드 체계 사용
        """
        # ELW 코드 변환 로직
        # 예: 0015N0 -> 15N0 또는 Kiwoom ELW 코드
        if "N" in ticker.upper():
            return ticker.replace("N", "N")  # Kiwoom 포맷
        return ticker

    async def _subscribe_elw(self, elw_code: str) -> None:
        """
        ELW 종목 구독

        ELW는 실시간 지원이 제한적이므로 폴링으로 대체
        """
        # ELW 전용 폴링 태스크 생성
        from tasks.elw_tasks import elw_polling_task
        elw_polling_task.delay(elw_code)

        logger.info(f"[WS BRIDGE] ELW polling started for: {elw_code}")
```

### 3.5 캐싱 계층 도입

```python
# src/websocket/cache_layer.py

class RedisPriceCache:
    """
    실시간 가격 캐시 계층

    WebSocket 미지원 종목을 위한 캐싱
    """

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.cache_ttl = 10  # 10초 캐시

    async def get_price(self, ticker: str) -> Optional[dict]:
        """캐시된 가격 조회"""
        key = f"price:{ticker}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_price(self, ticker: str, price_data: dict) -> None:
        """가격 캐시 저장"""
        key = f"price:{ticker}"
        await self.redis.setex(
            key,
            self.cache_ttl,
            json.dumps(price_data)
        )

    async def get_prices_batch(self, tickers: List[str]) -> dict:
        """일괄 조회"""
        keys = [f"price:{t}" for t in tickers]
        cached = await self.redis.mget(keys)

        result = {}
        for ticker, data in zip(tickers, cached):
            if data:
                result[ticker] = json.loads(data)

        return result
```

---

## 4. 아키텍처 개선

### 4.1 계층별 데이터 소스

```
┌─────────────────────────────────────────────────────────────┐
│                     프론트엔트                                │
├─────────────────────────────────────────────────────────────┤
│  useRealtimePrices()                                         │
│  ├── WebSocket 구독 (KOSPI 대형주)                         │
│  └── 폴링 Fallback (ELW, 소형주)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  API Gateway (/api/kr)                        │
├─────────────────────────────────────────────────────────────┤
│  GET /realtime-prices?tickers=XXX&include_elw=true         │
│  └── Kiwoom REST API 폴링                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              WebSocket Server (/ws)                           │
├─────────────────────────────────────────────────────────────┤
│  KiwoomWebSocketBridge                                       │
│  ├── KOSPI/KOSDAQ 지수 (001, 201)                          │
│  ├── 일반 주식 (6자리 숫자)                                │
│  └── ELW (폴링으로 대체)                                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 데이터 전략

| 종목 유형 | 실시간 방법 | 폴링 주기 | 캐시 |
|-----------|---------------|-----------|------|
| KOSPI 대형주 | WebSocket | - | Redis 10초 |
| KOSPI 중/소형주 | WebSocket | - | Redis 10초 |
| KOSDAQ | WebSocket | - | Redis 10초 |
| ELW | 폴링 | 10~30초 | Redis 30초 |
| K-OTC | 폴링 | 30~60초 | Redis 60초 |

---

## 5. 단계별 구현 계획

### 5.1 1단계: 프론트엔드 폴링 Fallback (1주일)

**목표**: ELW 종목에 대해 실시간 가격 표시

**작업**:
1. `RealtimePriceCard` 컴포넌트에 폴링 로직 추가
2. `/api/kr/realtime-prices` 폴링 엔드포인트 구현
3. ELW 종목에 대해 "폴링 업데이트" 뱃지 표시

**산출물**:
- `frontend/components/RealtimePriceCard.tsx` 수정
- `services/api_gateway/routes/stocks.py` 폴링 엔드포인트 추가

### 5.2 2단계: 백엔드 구독 기반 브로드캐스트 (1주일)

**목표**: 클라이언트가 구독하는 모든 종목 브로드캐스트

**작업**:
1. `DynamicPriceBroadcaster` 구현
2. `subscribe()` 시 `_subscribed_tickers`에 추가
3. `unsubscribe()` 시 제거

**산출물**:
- `src/websocket/server.py` 수정

### 5.3 3단계: VCP 스캐너 전 종목 확장 (2주일)

**목표**: KOSPI/KOSDAQ 전 종목 스캔

**작업**:
1. `/scan` 엔드포인트에 ELW 필터링 옵션 추가
2. 시가총액 기반 필터링
3. 최대 종목 수 제한 (성능 이슈)

**산출물**:
- `services/vcp_scanner/main.py` 수정
- VCP 스캔 태스크 최적화

### 5.4 4단계: ELW 실시간 지원 (3주일)

**목표**: Kiwoom WebSocket ELW 지원

**작업**:
1. Kiwoom ELW TR 코드 확인
2. ELW 전용 WebSocket 메시지 처리
3. ELW 폴링 태스크 구현 (실시간 지원 전까지)

**산출물**:
- `src/websocket/kiwoom_bridge.py` ELW 지원
- `tasks/elw_tasks.py` ELW 폴링 태스크

### 5.5 5단계: 캐싱 계층 도입 (2주일)

**목표**: 성능 개선 및 부하 감소

**작업**:
1. Redis 가격 캐시 구현
2. WebSocket 미지원 종목 캐시 조회
3. 캐시 무효화 정책 구현

**산출물**:
- `src/websocket/cache_layer.py` 구현
- 캐시 태스크 스케줄링

---

## 6. 기술적 제약사항

### 6.1 Kiwoom API 제약

| 항목 | 제약 | 해결 방안 |
|------|------|-----------|
| 실시간 데이터 종목 수 | 제한 있음 | 구독 기반 동적 관리 |
| ELW 실시간 | 미확실 | 폴링으로 대체 후 확인 |
| API 호출 빈도 | 제한 있음 | 캐싱으로 부하 감소 |
| 동시 연결 수 | 제한 있음 | 연결 풀링 |

### 6.2 시스템 리소스

| 리소스 | 현재 | 개선 후 |
|--------|------|--------|
| WebSocket 연결 | 1개 (공유) | 다중 연결 지원 |
| 브로드캐스트 종목 | 6개 (고정) | 최대 100개 (동적) |
| 폴링 API 호출 | 없음 | ELW 종목에 한해 10초 주기 |

### 6.3 성능 목표

| 지표 | 현재 | 목표 |
|------|------|------|
| 실시간 지원 종목 수 | 6종 | 500종 이상 |
| ELW 데이터 지연 | N/A | 10~30초 |
| WebSocket 메시지 지연 | 5초 | 5초 이내 |
| API 응답 시간 | N/A | 1초 이내 |

---

## 7. 테스트 계획

### 7.1 단위 테스트

| 항목 | 테스트 방법 | 기대 결과 |
|------|-------------|----------|
| 폴링 Fallback | ELW 종목 가격 조회 | 데이터 반환 |
| 구독 기반 브로드캐스트 | 100종목 구독 시도 | 모든 종목 브로드캐스트 |
| ELW 필터링 | ELW 제외 스캔 | ELW 제외됨 |
| 캐시 조회 | Redis 캐시 히트 | 캐시된 데이터 반환 |

### 7.2 통합 테스트

1. **KOSPI 대형주 실시간**: 삼성전자, SK하이닉스 등 실시간 업데이트 확인
2. **ELW 폴링**: ELW 종목 10초 간격 폴링 업데이트 확인
3. **대량 구독**: 100종목 동시 구독 시 브로드캐스트 확인
4. **VCP 전체 스캔**: KOSPI/KOSDAQ 전체 스캔 완료 확인

---

## 8. 롤백 계획

### 8.1 롤백 기준

- WebSocket 연결 불안정
- API 응답 시간 5초 초과
- 서버 리소스 사용량 80% 이상

### 8.2 롤백 절차

1. 동적 브로드캐스터 → 기존 고정 브로드캐스터
2. ELW 폴링 중단
3. ELW 필터링 해제

---

## 9. 참고 자료

### 9.1 KRX 종목 코드

- KOSPI 주식: 6자리 숫자
- KOSDAQ 주식: 6자리 숫자
- ELW: 6자리 + 1자리 알파벳 (예: 0015N0)
- K-OTC: 10자리 숫자

### 9.2 Kiwoom API

- 실시간 데이터: `0B` TR (체결)
- 일봉 데이터: `OPTNKF` TR (주식 일봉)
- ELW 데이터: 별도 TR (확인 필요)

---

*보고서 종료*
