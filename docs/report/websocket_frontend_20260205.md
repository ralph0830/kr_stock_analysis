# WebSocket 프론트엔드 구현 분석 보고서

**작성일:** 2026-02-05
**범위:** 메인 대시보드(VCP) vs 단타 추천(Daytrading) WebSocket 프론트엔드 비교

---

## 1. 개요

메인 대시보드와 단타 추천 페이지의 WebSocket 프론트엔드 사용 방식을 분석하고 불일치 사항을 확인합니다.

---

## 2. WebSocket 클라이언트 구조

### 2.1 코어 파일

| 파일 | 설명 |
|------|------|
| `lib/websocket.ts` | WebSocketClient 클래스, 메시지 타입 정의 |
| `hooks/useWebSocket.ts` | 메인 WebSocket Hook |
| `hooks/useRealtimePrices.ts` | 실시간 가격 Hook |
| `hooks/useMarketGate.ts` | Market Gate Hook |
| `store/useSignalsStore.ts` | VCP 시그널 Store |

### 2.2 메시지 타입 정의

```typescript
// lib/websocket.ts
export type WSMessage =
  | PriceUpdateMessage
  | IndexUpdateMessage
  | MarketGateUpdateMessage
  | SignalUpdateMessage
  | ConnectedMessage
  | PingMessage
  | PongMessage;

export interface PriceUpdateMessage {
  type: "price_update";
  ticker: string;
  data: {
    price: number;
    change: number;
    change_rate: number;
    volume: number;
  };
  timestamp: string;
}

export interface SignalUpdateMessage {
  type: "signal_update";
  data: {
    signal_type: string;  // "VCP" | "DAYTRADING"
    signals: any[];
    count: number;
    timestamp: string;
  };
}
```

---

## 3. 메인 대시보드 WebSocket 사용

### 3.1 useSignals Hook (VCP)

```typescript
// hooks/useWebSocket.ts
export function useSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [isRealtime, setIsRealtime] = useState(false);

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
  });

  useEffect(() => {
    if (!connected) return;

    const client = createWebSocketClient(wsUrl);

    // 메시지 수신
    client.onMessage((message: WSMessage) => {
      if (message.type === "signal_update") {
        setSignals(signalMsg.data.signals);
        setIsRealtime(true);
      }
    });

    // signal:vcp 토픽 구독 ✅
    subscribe("signal:vcp");
  }, [connected, subscribe]);

  // 초기 데이터 로드 (fallback)
  useEffect(() => {
    if (signals.length === 0 && !isRealtime) {
      apiClient.getSignals().then(setSignals);
    }
  }, [signals.length, isRealtime]);

  return { signals, isRealtime, connected };
}
```

### 3.2 토픽 구독 현황

| Hook | 구독 토픽 | 상태 |
|------|----------|------|
| `useRealtimePrices` | `price:{ticker}` | ✅ 작동 |
| `useMarketGate` | `market-gate` | ✅ 작동 |
| `useSignals` | `signal:vcp` | ✅ 작동 |
| `useDaytradingSignals` | `signal:daytrading` | ⚠️ 백엔드 미구현 |

---

## 4. 단타 추천 WebSocket 사용

### 4.1 useDaytradingSignals Hook

```typescript
// hooks/useWebSocket.ts (현재 구현)
export function useDaytradingSignals() {
  const [signals, setSignals] = useState<IDaytradingSignal[]>([]);
  const [isRealtime, setIsRealtime] = useState(false);

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
  });

  useEffect(() => {
    if (!connected) return;

    const client = createWebSocketClient(wsUrl);

    // 메시지 수신
    client.onMessage((message: WSMessage) => {
      if (message.type === "signal_update") {
        const data = signalMsg.data as any;
        // checks 필드로 단타 시그널 확인
        if (data.signals && data.signals.length > 0 && "checks" in data.signals[0]) {
          setSignals(data.signals);
          setIsRealtime(true);
        }
      }
    });

    // signal:daytrading 토픽 구독
    subscribe("signal:daytrading");  // ⚠️ 백엔드에서 방송 없음
  }, [connected, subscribe]);

  // 초기 데이터 로드 (API 폴링 fallback)
  useEffect(() => {
    if (signals.length === 0 && !isRealtime) {
      apiClient.getDaytradingSignals()
        .then((response) => {
          setSignals(response.data.signals);  // ⚠️ 버그: data.data.signals
        })
        .catch((error) => {
          console.error("[useDaytradingSignals] Failed:", error);
        });
    }
  }, [signals.length, isRealtime]);

  return { signals, isRealtime, connected };
}
```

### 4.2 단타 추천 페이지에서의 사용

```typescript
// app/custom-recommendation/page.tsx
export default function CustomRecommendationPage() {
  const {
    signals: storeSignals,
    loading,
    fetchDaytradingSignals,
  } = useDaytradingStore();

  // WebSocket 실시간 시그널 구독
  const {
    signals: wsSignals,
    isRealtime,
    connected: wsConnected,
  } = useDaytradingSignals();

  // 실시간 데이터와 스토어 데이터 병합
  const signals = useMemo(() => {
    return wsSignals.length > 0 ? wsSignals : storeSignals;
  }, [wsSignals, storeSignals]);

  // ...
}
```

---

## 5. 불일치 사항 분석

### 5.1 API 응답 구조 접근 차이

| Hook | API 호출 | 데이터 접근 | 상태 |
|------|----------|-----------|------|
| `useSignals` | `apiClient.getSignals()` | 직접 사용 | ✅ 작동 |
| `useDaytradingSignals` | `apiClient.getDaytradingSignals()` | `response.data.signals` | ❌ 버그 |

**문제 코드:**
```typescript
// 현재 (버그)
apiClient.getDaytradingSignals()
  .then((response) => {
    setSignals(response.data.signals);  // ❌ response.data.data.signals여야 함
  })

// 수정 필요
apiClient.getDaytradingSignals()
  .then((response) => {
    setSignals(response.data.data.signals);  // ✅ 수정
  })
```

**API 응답 구조:**
```json
{
  "success": true,
  "data": {
    "signals": [...],  // ← 여기에 있음
    "count": 2
  }
}
```

### 5.2 토픽 구독 불일치

| 구분 | 메인 대시보드 | 단타 추천 | 비고 |
|------|-------------|----------|------|
| 토픽 이름 | `signal:vcp` | `signal:daytrading` | 명명 규칙 다름 |
| 백엔드 브로드캐스트 | `SignalBroadcaster` ✅ | 없음 ❌ | 미구현 |
| 프론트엔드 구독 | `subscribe("signal:vcp")` | `subscribe("signal:daytrading")` | 프론트엔드만 정의 |
| 실시간 업데이트 | ✅ 작동 | ❌ API 폴링만 작동 | 의존性问题 |

### 5.3 데이터 타입 불일치

```typescript
// 메인 대시보드 - Signal
interface Signal {
  ticker: string;
  name: string;
  signal_type: string;  // "VCP" | "JONGGA_V2"
  score: number | ScoreDetail;
  grade: string;
  created_at: string;
}

// 단타 추천 - IDaytradingSignal
interface IDaytradingSignal {
  ticker: string;
  name: string;
  market: "KOSPI" | "KOSDAQ";
  total_score: number;  // ⚠️ 다름
  grade: "S" | "A" | "B" | "C";
  checks: IDaytradingCheck[];  // ⚠️ 추가 필드
  signal_type: DaytradingSignalType;  // "STRONG_BUY" | "BUY" | "WATCH"
  detected_at?: string;  // ⚠️ 다름
}
```

---

## 6. 메인 대시보드 기준 표준화 방안

### 6.1 토픽 네이밍 통일

| 현재 (단타) | 표준 (메인) | 변경 범위 |
|-------------|------------|----------|
| `signal:daytrading` | `signal:daytrading` | 유지 (의미 명확) |
| `signal:vcp` | `signal:vcp` | 유지 |

### 6.2 데이터 구조 통일

```typescript
// 통합 제안
export interface ISignalBase {
  ticker: string;
  name: string;
  market: string;
  score: number;  // ✅ VCP는 score, Daytrading도 total_score → score
  grade: "S" | "A" | "B" | "C";
  signal_type: SignalType;
  created_at: string;  // ✅ VCP는 created_at, Daytrading도 detected_at → created_at
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;
}

export interface IVCPSignal extends ISignalBase {
  signal_type: "VCP" | "JONGGA_V2";
  contraction_ratio?: number;
  foreign_5d?: number;
  inst_5d?: number;
}

export interface IDaytradingSignal extends ISignalBase {
  signal_type: "STRONG_BUY" | "BUY" | "WATCH";
  checks: IDaytradingCheck[];  // 단타 전용 필드
}
```

### 6.3 Hook 통일 패턴

```typescript
// 통합 패턴
export function useSignals(signalType: "vcp" | "daytrading") {
  const [signals, setSignals] = useState<ISignalBase[]>([]);
  const [isRealtime, setIsRealtime] = useState(false);

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
  });

  useEffect(() => {
    if (!connected) return;

    const client = createWebSocketClient(wsUrl);

    client.onMessage((message: WSMessage) => {
      if (message.type === "signal_update") {
        const data = message.data as any;
        // signal_type으로 구분
        if (data.signal_type?.toLowerCase() === signalType) {
          setSignals(data.signals);
          setIsRealtime(true);
        }
      }
    });

    // 토픽 구독
    subscribe(`signal:${signalType}`);
  }, [connected, subscribe, signalType]);

  return { signals, isRealtime, connected };
}
```

---

## 7. 현재 버그 수정

### 7.1 API 응답 접근 수정

**파일:** `hooks/useWebSocket.ts`

```typescript
// 수정 전 (버그)
apiClient.getDaytradingSignals()
  .then((response) => {
    setSignals(response.data.signals);  // ❌
  })

// 수정 후
apiClient.getDaytradingSignals()
  .then((response) => {
    setSignals(response.data.data.signals);  // ✅
  })
```

**동일한 버그가 있는 위치:**
1. `hooks/useWebSocket.ts:842` - `useDaytradingSignals` 초기 데이터 로드
2. `store/daytradingStore.ts:58` - `fetchDaytradingSignals`
3. `store/daytradingStore.ts:80` - `scanDaytradingMarket`
4. `store/daytradingStore.ts:99` - `analyzeStocks`

### 7.2 수정 필요 파일 목록

| 파일 | 라인 | 수정 내용 |
|------|------|----------|
| `hooks/useWebSocket.ts` | 842 | `response.data.signals` → `response.data.data.signals` |
| `store/daytradingStore.ts` | 58, 80, 99 | 동일하게 수정 |

---

## 8. 통합 우선순위

### Phase 1: API 응답 접근 수정 (긴급)

- [ ] `response.data.signals` → `response.data.data.signals` 수정 (4곳)
- [ ] 단타 시그널 정상 표시 확인

**작업량:** 30분

### Phase 2: 백엔드 브로드캐스트 구현

- [ ] `DaytradingSignalBroadcaster` 구현 (별도 백엔드 보고서 참조)
- [ ] WebSocket 실시간 업데이트 확인

**작업량:** 2-3시간 (백엔드)

### Phase 3: 타입 정의 통일

- [ ] `ISignalBase` 인터페이스 정의
- [ ] `IVCPSignal`, `IDaytradingSignal` 확장
- [ ] 공통 Hook `useSignals(signalType)` 구현

**작업량:** 2-3시간

---

## 9. 결론

### 주요 발견

1. **API 응답 접근 버그**: `response.data.signals` → `response.data.data.signals` 수정 필요 (4곳)
2. **단타 WebSocket 백엔드 미구현**: `signal:daytrading` 토픽 방송 기능 없음
3. **데이터 타입 불일치**: 필드명, 구조가 VCP와 다름

### 개선 방향

1. **필드명 통일**: `total_score` → `score`, `detected_at` → `created_at`
2. **타입 계층 구조**: 베이스 인터페이스 + 시그널 타입별 확장
3. **Hook 패턴 통일**: `useSignals(signalType)`으로 단일화

**총 작업량 예상:** 5-7시간 (백엔드 + 프론트엔드)
