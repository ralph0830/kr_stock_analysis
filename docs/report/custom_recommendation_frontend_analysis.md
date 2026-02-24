# custom-recommendation 페이지 프론트엔드 분석 보고서

**분석 일자:** 2026-02-06  
**대상 URL:** https://stock.ralphpark.com/custom-recommendation  
**분석 도구:** Playwright (headless browser)

---

## 1. 요약

custom-recommendation 페이지는 **단타 매수 신호(Daytrading Signal)**를 제공하는 페이지로, **WebSocket을 통한 실시간 연동**과 **API를 통한 초기 데이터 로드** 방식을 혼합하여 사용합니다.

**핵심 기능:**
- 7가지 체크리스트 기반 단타 매수 신호 제공
- WebSocket 실시간 시그널 업데이트 구독 (`signal:daytrading` 토픽)
- **실시간 가격 연동 (구현 완료 ✅)** - `useRealtimePrices` Hook 사용
- 필터링 (시장, 최소 점수, 표시 개수)
- 시장 스캔 기능 (백엔드 스캔 트리거)

---

## 2. 기술 아키텍처

### 2.1 주요 컴포넌트

| 파일 | 경로 | 설명 |
|------|------|------|
| 페이지 컴포넌트 | `/frontend/app/custom-recommendation/page.tsx` | 메인 페이지 |
| 시그널 테이블 | `/frontend/components/DaytradingSignalTable.tsx` | 시그널 목록 표시 (실시간 가격 포함) |
| 상태 관리 | `/frontend/store/daytradingStore.ts` | Zustand 스토어 |
| WebSocket Hook | `/frontend/hooks/useWebSocket.ts` | WebSocket 연결 관리 |
| API 클라이언트 | `/frontend/lib/api-client.ts` | API 호출 |

### 2.2 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    custom-recommendation 페이지                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐      ┌─────────────────────────────┐  │
│  │ useDaytradingStore  │◄─────┤   apiClient                 │  │
│  │ (Zustand Store)     │      │   getDaytradingSignals()    │  │
│  └────────┬────────────┘      └─────────────┬───────────────┘  │
│           │                                 │                    │
│           ▼                                 ▼                    │
│  ┌─────────────────────┐      ┌─────────────────────────────┐  │
│  │ useDaytradingSignals │◄────┤   API Gateway               │  │
│  │ (WebSocket Hook)     │      │   /api/daytrading/signals   │  │
│  └────────┬─────────────┘      └─────────────────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────┐      ┌─────────────────────────────┐  │
│  │ useRealtimePrices   │◄────┤   WebSocket (price:{ticker}) │  │
│  │ (실시간 가격 Hook)    │      │   price:005930, price:000270│  │
│  └────────┬─────────────┘      └─────────────────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────┐                                        │
│  │ DaytradingSignalTable │ (UI 렌더링 + 실시간 가격)            │
│  └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. WebSocket 연동 분석

### 3.1 연결 프로세스

**1) WebSocket 연결 URL 동적 결정**
```typescript
// /frontend/hooks/useWebSocket.ts:132-153
const defaultUrl = typeof window !== "undefined"
  ? (() => {
      const protocol = window.location.protocol;
      const hostname = window.location.hostname;
      const isLocal = hostname === "localhost" || hostname === "127.0.0.1";
      const wsProtocol = protocol.replace("http", "ws");

      if (isLocal) {
        return `${wsProtocol}//${hostname}:5111/ws`;
      }
      return `${wsProtocol}//${hostname}/ws`;
    })()
  : "ws://localhost:5111/ws";
```

**2) 연결 상태 관리**
- `connectionState`: "disconnected" | "connecting" | "connected" | "error"
- `clientId`: 연결 시 서버에서 할당
- `reconnectCount`: 재연결 시도 횟수 (최대 10회)

**3) 실제 연결 로그 (2026-02-06 캡처)**
```
[log] [useWebSocket] Getting client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] Created new client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: disconnected → connecting
[log] [WebSocket] Connected to wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: connecting → connected
[log] [WebSocket] Ping timer started (interval: 30000 ms)
[log] [WebSocket] Client ID: e248711d-e037-4c2f-9d2f-726ad171caea
```

### 3.2 실시간 시그널 구독

**토픽 구독**
```typescript
// /frontend/hooks/useWebSocket.ts:847-851
subscribe("signal:daytrading");
```

**메시지 핸들러**
```typescript
// /frontend/hooks/useWebSocket.ts:830-844
const unsubscribeMessage = client.onMessage((message: WSMessage) => {
  if (message.type === "signal_update") {
    const signalMsg = message as SignalUpdateMessage;
    const data = signalMsg.data as any;
    if (data.signals && data.signals.length > 0 && "checks" in data.signals[0]) {
      setSignals(data.signals);
      setIsRealtime(true);
      setLastUpdate(new Date(data.timestamp));
    }
  }
});
```

### 3.3 실시간 가격 연동 (구현 완료 ✅)

**useRealtimePrices Hook 사용:**
```typescript
// /frontend/app/custom-recommendation/page.tsx:48-55
const tickerList = useMemo(() => signals.map((s) => s.ticker), [signals])
const {
  prices: realtimePrices,
  getPrice,
  connected: priceConnected,
  error: priceError,
} = useRealtimePrices(tickerList)
```

**종목별 자동 구독:**
```typescript
// /frontend/hooks/useWebSocket.ts:468-474
tickers.forEach((ticker) => {
  console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
  subscribe(`price:${ticker}`);
});
```

**실제 구독 로그:**
```
[log] [useRealtimePrices] Subscribing to price:005930
[log] [useRealtimePrices] Subscribing to price:000270
```

---

## 4. API 호출 분석

### 4.1 초기 데이터 로드

**API 엔드포인트**
```
GET /api/daytrading/signals?min_score=0&limit=50
```

**요청 코드**
```typescript
// /frontend/store/daytradingStore.ts:46-67
fetchDaytradingSignals: async () => {
  const { filters } = get()
  const response = await apiClient.getDaytradingSignals({
    min_score: filters.minScore,
    market: filters.market === "ALL" ? undefined : filters.market,
    limit: filters.limit,
  })
  set({ signals: response.data.signals, loading: false })
}
```

**실제 로그**
```
[log] [API Request] GET /api/daytrading/signals
[log] [API] baseURL: https://stock.ralphpark.com
```

### 4.2 시장 스캔 기능

**API 엔드포인트**
```
POST /api/daytrading/scan
```

### 4.3 API 클라이언트 설정

**BaseURL 동적 설정**
```typescript
const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const isLocal = hostname === "localhost" || hostname === "127.0.0.1";

    if (!isLocal) {
      return `${protocol}//${hostname}`;
    }
    return `${protocol}//${hostname}:5111`;
  }
  return "http://api-gateway:5111";
};
```

---

## 5. UI 구성 분석

### 5.1 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: ⚡ 단타 추천  [시그널 실시간] [가격 실시간] [대시보드]  │
├──────────────────┬──────────────────────────────────────────────┤
│  필터 패널        │  시그널 목록                                  │
│  ─────────────    │  ┌────────────────────────────────────────┐ │
│  시장: 전체       │  │ 삼성전자 (005930)                      │ │
│  최소 점수: 60    │  │ S 등급 | 강력 매수 | 90점              │ │
│  표시 개수: 50    │  │ [체크리스트 7개 표시]                   │ │
│  ─────────────    │  │ 진입: 75,000원 목표: 80,000원          │ │
│  [새로고침]       │  │ 현재가: 157,500원 (-1.13%) [실시간]    │ │
│  [시장 스캔]      │  └────────────────────────────────────────┘ │
│  [필터 초기화]    │  ┌────────────────────────────────────────┐ │
│  ─────────────    │  │ 기아 (000270)                           │ │
│  총 2개 시그널    │  │ A 등급 | 매수 | 75점                    │ │
│  ─────────────    │  │ [체크리스트 7개 표시]                   │ │
│  [단타 추천이란?] │  │ 현재가: 151,800원 (-2.82%) [실시간]    │ │
│                   │  └────────────────────────────────────────┘ │
└──────────────────┴──────────────────────────────────────────────┘
```

### 5.2 데이터 표시

**실제로 표시된 종목 (2개)**
1. **삼성전자 (005930)** - S 등급, 90점
2. **기아 (000270)** - A 등급, 75점

**현재가 표시:**
- 삼성전자: 157,500원 (-1.13%, -1,800원)
- 기아: 151,800원 (-2.82%, -4,400원)
- **실시간 배지 표시됨** ✅

---

## 6. 발견한 사항

### 6.1 정상 작동 기능

| 항목 | 상태 | 설명 |
|------|------|------|
| WebSocket 연결 | ✅ | `wss://stock.ralphpark.com/ws` 정상 연결 |
| API 호출 | ✅ | `/api/daytrading/signals` 정상 응답 |
| 초기 데이터 로드 | ✅ | 2개 시그널 정상 표시 |
| 실시간 상태 표시 | ✅ | "시그널 실시간", "가격 실시간" 배지 표시됨 |
| 가격 토픽 구독 | ✅ | `price:005930`, `price:000270` 구독 완료 |
| Ping/Pong | ✅ | 30초 간격 정상 동작 |

### 6.2 백엔드 연동 상태

| 항목 | 상태 | 설명 |
|------|------|------|
| 프론트엔드 구현 | ✅ 완료 | `useRealtimePrices` Hook 사용 중 |
| WebSocket 연결 | ✅ 완료 | 연결 및 토픽 구독 정상 |
| 백엔드 브로드캐스터 | ⚠️ 실행 중 | 하지만 종목이 추가되지 않음 |
| 가격 업데이트 수신 | ❌ 미구현 | 백엔드에서 종목 추가 로직 누락 |

---

## 7. 결론

custom-recommendation 페이지의 **프론트엔드 실시간 가격 연동은 완전히 구현**되어 있습니다.

- **WebSocket 연결:** ✅ 정상
- **API 호출:** ✅ 정상
- **데이터 표시:** ✅ 정상 (2개 시그널)
- **가격 토픽 구독:** ✅ 정상
- **UI 표시:** ✅ 정상 (현재가, 등락률, 실시간 배지)

**단, 백엔드에서 다음 기능이 필요합니다:**
1. Daytrading 시그널 종목을 `daytrading_price_broadcaster`에 추가하는 로직
2. API 응답에 `current_price` 필드 포함

---

## 8. 참고 파일

| 파일 | 경로 |
|------|------|
| 페이지 컴포넌트 | `/home/ralph/work/python/kr_stock_analysis/frontend/app/custom-recommendation/page.tsx` |
| 시그널 테이블 | `/home/ralph/work/python/kr_stock_analysis/frontend/components/DaytradingSignalTable.tsx` |
| WebSocket Hook | `/home/ralph/work/python/kr_stock_analysis/frontend/hooks/useWebSocket.ts` |
| API 클라이언트 | `/home/ralph/work/python/kr_stock_analysis/frontend/lib/api-client.ts` |
| 상태 관리 | `/home/ralph/work/python/kr_stock_analysis/frontend/store/daytradingStore.ts` |
