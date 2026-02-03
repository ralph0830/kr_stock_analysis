# 프론트엔드 실시간 가격 모니터링 분석 보고서

**분석 일자**: 2026-02-03
**분석 유형**: 프론트엔드 검사 및 루트 원인 분석
**심각도**: 높음 (기능 미작동)

---

## 1. 실행 요약

### 1.1 문제 현상

https://stock.ralphpark.com/ 랜딩 페이지에서 **실시간 가격 모니터링 카드에 가격 데이터가 표시되지 않음**

| 항목 | 상태 |
|------|------|
| WebSocket 연결 | ✅ "실시간 연결됨" |
| Market Gate 데이터 | ✅ KOSPI/KOSDAQ 정상 표시 |
| 실시간 가격 카드 | ❌ "데이터 대기 중..." |

### 1.2 핵심 발견

**ELW 종목 구독 불일치로 인한 데이터 미수신**

```
프론트엔드 구독 시도 종목 (ELW):
├── 0015N0 (아로마티카)
├── 493330 (지에프아이)
├── 217590 (티엠씨)
├── 0004V0 (엔비알모션)
├── 491000 (리브스메드)
└── 0120X0 (유진 챔피언중단기크레딧 X클래스)

백엔드 브로드캐스팅 종목 (KOSPI 대종목):
├── 005930 (삼성전자)
├── 000660 (SK하이닉스)
├── 035420 (NAVER)
└── 005380 (현대차)
```

### 1.3 근본 원인

1. **시그널 종목이 ELW** → VCP 스캐너가 ELW 종목에서 시그널 발생
2. **프론트엔드는 시그널 종목 구독 시도** → `useRealtimePrices()` 훅이 ELW 종목 구독
3. **백엔드는 ELW 구독 처리 안 함** → `ticker.isdigit()` 체크로 ELW 차단
4. **결과: 구독자 0명, 데이터 미수신**

---

## 2. 상세 분석

### 2.1 프론트엔드 검증

#### 브라우저 콘솔 로그

```
[WebSocket] Connected to wss://stock.ralphpark.com/ws
[WebSocket] Client ID: a9ec4b85-6ea4-49ff-95be-01b02da89fd2
[useRealtimePrices] Subscribing to price:0015N0
[useRealtimePrices] Subscribing to price:493330
[useRealtimePrices] Subscribing to price:217590
[useRealtimePrices] Subscribing to price:0004V0
[useRealtimePrices] Subscribing to price:491000
[useRealtimePrices] Subscribing to price:0120X0
[useMarketGate] Subscribed to market-gate topic
```

**검증 결과**:
- ✅ WebSocket 연결 성공
- ✅ `connected` 상태로 전환
- ✅ ELW 종목 구독 요청 전송

#### 페이지 표시 상태

```
실시간 가격 모니터링
┌─────────────────────┐
│ 아로마티카 0015N0   │
│ 연결됨              │
│ 데이터 대기 중...    │  ← 모든 카드가 동일 상태
└─────────────────────┘
```

### 2.2 백엔드 검증

#### WebSocket 통계 (`/ws/stats`)

```json
{
  "active_connections": 1,
  "subscriptions": {
    "price:005930": 0,    ← 구독자 0명
    "price:000660": 0,    ← 구독자 0명
    "market-gate": 7
  },
  "bridge_running": true,
  "bridge_tickers": [
    "035420", "217590", "491000", "005380",
    "000020", "028260", "005930", "000660", "493330"
  ],
  "broadcaster_running": true,
  "active_tickers": []
}
```

**분석**:
- `bridge_tickers`에 일부 ELW 종목 포함 (`217590`, `491000`, `493330`)
- 하지만 `subscriptions`에서 ELW 종목 누락 (`price:0015N0` 등 없음)
- `active_tickers`가 비어있음 → price_broadcaster에 등록된 종목 없음

#### 브로드캐스트 로그

```
[WS BRIDGE] Broadcasting price update for 000660: 890000.0
[BROADCAST] Topic=price:000660, subscribers=0
[BROADCAST] No recipients found to send to

[WS BRIDGE] Broadcasting price update for 005930: 159400.0
[BROADCAST] Topic=price:005930, subscribers=0
[BROADCAST] No recipients found to send to
```

**Kiwoom WebSocket Bridge는 작동 중**:
- 실시간 가격 수신 성공 (SK하이닉스 890,000원, 삼성전자 159,400원)
- 하지만 구독자가 0명이라 데이터 전송 안 됨

### 2.3 코드 분석

#### 프론트엔드 구독 로직

**파일**: `frontend/hooks/useWebSocket.ts:395-414`

```typescript
useEffect(() => {
  if (!connected) {
    console.log(`[useRealtimePrices] Waiting for connection...`);
    return;
  }

  // 연결된 경우에만 구독
  tickers.forEach((ticker) => {
    console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
    subscribe(`price:${ticker}`);  // ELW 종목 구독 시도
  });

  return () => {
    tickers.forEach((ticker) => {
      unsubscribe(`price:${ticker}`);
    });
  };
}, [tickers.join(","), subscribe, unsubscribe, connected]);
```

**분석**:
- ✅ `connected` 체크 후 구독 (정상 동작)
- ✅ 시그널 종목(ELW)을 정확히 구독 시도

#### 프론트엔드 WebSocket 클라이언트

**파일**: `frontend/lib/websocket.ts:248-274`

```typescript
subscribe(topic: string): void {
  if (this._subscriptions.has(topic)) {
    return;
  }

  if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
    console.log("[WebSocket] Queueing subscription for:", topic);
    this._pendingSubscriptions.add(topic);
    return;
  }

  const message = {
    type: "subscribe",
    topic: topic,
  };

  this.ws.send(JSON.stringify(message));  // 서버로 전송
  this._subscriptions.add(topic);
}
```

**분석**:
- ✅ WebSocket이 OPEN 상태일 때 메시지 전송
- ✅ 정상적으로 서버로 구독 요청 전송

#### 백엔드 구독 처리

**파일**: `src/websocket/server.py:144-177`

```python
def subscribe(self, client_id: str, topic: str) -> None:
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    self.subscriptions[topic].add(client_id)
    logger.info(f"Client {client_id} subscribed to {topic}")

    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ticker는 6자리 숫자여야 함  ← 문제!
        if ticker.isdigit() and len(ticker) == 6:
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
```

**ELW 종목 코드 형식**:
| 종목 | 코드 | `isdigit()` | 처리 여부 |
|------|------|-------------|-----------|
| 아로마티카 | `0015N0` | False ('N' 포함) | ❌ 차단 |
| 지에프아이 | `493330` | True | ✅ 통과 |
| 티엠씨 | `217590` | True | ✅ 통과 |
| 엔비알모션 | `0004V0` | False ('V' 포함) | ❌ 차단 |
| 리브스메드 | `491000` | True | ✅ 통과 |
| 유진챔피언 | `0120X0` | False ('X' 포함) | ❌ 차단 |

**문제**:
1. 알파벳 포함 ELW 종목(`0015N0`, `0004V0`, `0120X0`)은 `isdigit()` 체크로 차단
2. 숫자로만 구성된 ELW(`493330`, `217590`, `491000`)은 체크 통과하지만...
3. `bridge_tickers`에는 등록되었으나 **구독자 목록(`subscriptions`)에는 추가되지 않음**
4. Kiwoom WebSocket Bridge는 `active_tickers`에 있는 종목만 브로드캐스트

---

## 3. 근본 원인 (Root Cause)

### 3.1 직접 원인

**불일치**: 프론트엔드가 구독하는 종목과 백엔드가 브로드캐스트하는 종목이 다름

| 구분 | 종목 | 수신 여부 |
|------|------|----------|
| 프론트엔드 구독 | ELW (0015N0, 493330, ...) | ❌ |
| 백엔드 브로드캐스트 | KOSPI 대종목 (005930, 000660, ...) | ✅ (but 구독자 없음) |

### 3.2 시스템 설계 제약

1. **VCP 스캐너가 ELW 종목에서 시그널 발생**
2. **실시간 가격 시스템은 KOSPI 대종목 위주로 설계**
3. **ELW 종목에 대한 실시간 가격 데이터 소스 제약**

### 3.3 Kiwoom WebSocket Bridge 제약

**파일**: `src/websocket/kiwoom_bridge.py:99-115`

```python
async def _on_realtime_data(self, price: RealtimePrice) -> None:
    ticker = price.ticker

    # 구독 중인 종목인지 확인
    if ticker not in self._active_tickers:
        print(f"[WS BRIDGE] Ticker {ticker} not in active_tickers: {self._active_tickers}")
        return  # ← 구독 중이 아니면 브로드캐스트 안 함
```

**문제**:
- `ticker.isdigit()` 체크 때문에 ELW 종목이 `active_tickers`에 추가되지 않음
- Kiwoom WebSocket Bridge는 등록되지 않은 종목을 브로드캐스트하지 않음
- Kiwoom Pipeline에서 ELW 종목 데이터를 받아도 전송 안 됨

---

## 4. 영향 분석

### 4.1 기능적 영향

| 페이지 | 기능 | 상태 |
|--------|------|------|
| 랜딩 페이지 | 시그널 종목 실시간 가격 | ❌ 미작동 |
| /dashboard/kr | KOSPI 지수 | ✅ 정상 |
| Market Gate | KOSPI/KOSDAQ 지수 | ✅ 정상 |

### 4.2 사용자 경험

1. **데이터 없음**: "데이터 대기 중..." 메시지 지속
2. **혼동**: WebSocket이 "연결됨"인데 데이터 없음
3. **기대치 불일치**: "실시간" 표시인데 실시간 데이터 없음

### 4.3 비즈니스 영향

- 시그널 종목의 실시간 가격 확인 불가
- 사용자가 시그널 종목의 현재 가격을 알 수 없음
- 매매 결정에 필요한 실시간 정보 부족

---

## 5. 프론트엔드 개선 제안

### 5.1 우선순위 1: 데이터 소스 표시 (높음)

#### 구현 방안

```typescript
// RealtimePriceCard.tsx
interface RealtimePriceCardProps {
  ticker: string;
  name: string;
  dataSource?: "websocket" | "polling" | "cache";  // 데이터 소스 표시
}

export function RealtimePriceCard({ ticker, name, dataSource }: RealtimePriceCardProps) {
  const { prices, getPrice, connected } = useRealtimePrices([ticker]);
  const realtimePrice = getPrice(ticker);

  // 데이터 소스 뱃지
  const getDataSourceBadge = () => {
    if (dataSource === "websocket") return "실시간";
    if (dataSource === "polling") return "폴링 (15초)";
    if (dataSource === "cache") return "캐시";
    return connected ? "실시간" : "폴링";
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">{name}</h3>
          <p className="text-sm text-gray-500">{ticker}</p>
        </div>
        <div className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
          {getDataSourceBadge()}
        </div>
      </div>
      {/* ... */}
    </div>
  );
}
```

### 5.2 우선순위 2: ELW 종목 필터링 (중간)

#### 구현 방안

```typescript
// page.tsx
const [excludeELW, setExcludeELW] = useState(false);

const realtimeTickers = useMemo(() => {
  return signals
    .filter((signal) => {
      // ELW 제외 필터
      if (excludeELW && signal.ticker.length === 6 && !signal.ticker.match(/^\d+$/)) {
        return false;
      }
      return true;
    })
    .slice(0, 6)
    .map((signal) => ({
      ticker: signal.ticker,
      name: signal.name,
    }));
}, [signals, excludeELW]);
```

### 5.3 우선순위 3: 폴링 Fallback (중간)

#### 구현 방안

```typescript
// useRealtimePrices 훅에 폴링 fallback 추가
useEffect(() => {
  // WebSocket으로 데이터 받으면 스킵
  if (realtimePrice) return;

  // WebSocket 미지원 종목에 대해 폴링
  const fetchPollingPrice = async () => {
    try {
      const response = await fetch(`/api/kr/realtime-price?ticker=${ticker}`);
      const data = await response.json();
      setPollingPrice(data);
    } catch (error) {
      console.error("Polling fetch error:", error);
    }
  };

  fetchPollingPrice();
  const interval = setInterval(fetchPollingPrice, 15000);  // 15초 간격

  return () => clearInterval(interval);
}, [ticker, realtimePrice]);
```

### 5.4 우선순위 4: UI 개선 (낮음)

```typescript
// ELW 종목인 경우 안내 메시지 표시
const isELW = ticker.length === 6 && !ticker.match(/^\d+$/);

{isELW && !realtimePrice && (
  <div className="text-xs text-yellow-600 mt-2">
    ⚠️ ELW 종목은 실시간 지원이 제한됩니다
  </div>
)}
```

---

## 6. 테스트 계획

### 6.1 단위 테스트

```typescript
// utils.test.ts
describe("isELWTicker", () => {
  it("should return true for ELW tickers", () => {
    expect(isELWTicker("0015N0")).toBe(true);
    expect(isELWTicker("0004V0")).toBe(true);
  });

  it("should return false for regular tickers", () => {
    expect(isELWTicker("005930")).toBe(false);
    expect(isELWTicker("000660")).toBe(false);
  });
});
```

### 6.2 통합 테스트

1. ELW 종목 구독 시 폴링으로 fallback 동작 확인
2. 데이터 소스 뱃지 정확한 표시 확인
3. 필터링 UI 동작 확인

---

## 7. 권장 사항

### 7.1 단기 (즉시 실행)

**UI 개선**: 데이터 소스 뱃지와 ELW 안내 메시지 추가

- 사용자에게 현재 상태 명확히 전달
- "실시간 지원 안 함" 메시지로 혼동 방지

### 7.2 중기 (1-2주)

1. **폴링 Fallback 구현**: ELW 종목에 대해 15-30초 간격 폴링
2. **필터링 UI**: ELW 제외 옵션 제공

### 7.3 장기 (1개월 이상)

백엔드 ELW 지원과 연동하여 완전한 실시간 지원 구현

---

## 8. 완료 상태 (Implementation Status)

### 8.1 Phase 1: WebSocket 연결 상태 확인 수정 ✅

**완료일자**: 2026-02-03

**관련 보고서**: `realtime_price_issue_analysis_20260203.md`

**수정 파일**: `frontend/hooks/useWebSocket.ts:395-414`

**내용**: `useRealtimePrices` 훅에 `connected` 상태 확인 추가

```typescript
// 수정 완료된 코드 (2.3절 코드 분석 참조)
useEffect(() => {
  if (!connected) {  // ✅ 연결 상태 확인
    console.log(`[useRealtimePrices] Waiting for connection...`);
    return;
  }

  tickers.forEach((ticker) => {
    console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
    subscribe(`price:${ticker}`);
  });

  return () => {
    tickers.forEach((ticker) => {
      unsubscribe(`price:${ticker}`);
    });
  };
}, [tickers.join(","), subscribe, unsubscribe, connected]);
```

### 8.2 Phase 2: 데이터 소스 표시 및 폴링 Fallback ✅

**완료일자**: 2026-02-03

**수정 파일**: `frontend/components/RealtimePriceCard.tsx`

**구현 내용**:

| 항목 | 상태 | 설명 |
|------|------|------|
| ELW 종목 식별 | ✅ | `isELW()`, `getTickerCategory()` 함수 추가 |
| 데이터 소스 뱃지 | ✅ | 실시간(초록)/폴링(노랑)/연결 중(파랑)/대기 중(회색) |
| 폴링 Fallback | ✅ | `apiClient.getRealtimePrices()`로 15초 간격 폴링 |
| ELW 안내 메시지 | ✅ | ⚠️ ELW 종목은 실시간 지원 제한 안내 |

**추가된 헬퍼 함수**:
```typescript
// ELW 종목 여부 확인
function isELW(ticker: string): boolean {
  return ticker.length === 6 && /[A-Za-z]/.test(ticker);
}

// 종목 분류 (데이터 소스 결정용)
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "ELW" | "UNKNOWN";
  realtimeSupported: boolean;
} { /* ... */ }
```

### 8.3 진행 중/예정 (TODO)

| 우선순위 | 항목 | 상태 | 예정 완료일 |
|----------|------|------|-------------|
| 3 | 백엔드 ELW 지원 | 예정 | - |

### 8.4 검증 방법

**WebSocket 구독자 확인**:
```bash
curl http://localhost:5111/ws/stats | jq '.subscriptions'

# 기대 결과: KOSPI 대종목 구독자 1명 이상
{
  "price:005930": 1,  # ← 삼성전자 구독자 확인
  "price:000660": 1,  # ← SK하이닉스 구독자 확인
  "market-gate": 1
}
```

**브라우저 Console 확인**:
```
[useRealtimePrices] Waiting for connection...
[useRealtimePrices] Subscribing to price:005930
```

---

*보고서 종료*

*마지막 수정: 2026-02-03*
