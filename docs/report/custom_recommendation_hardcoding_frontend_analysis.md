# custom-recommendation 페이지 프론트엔드 하드코딩 분석 보고서

**분석 일자:** 2026-02-06
**대상 URL:** https://stock.ralphpark.com/custom-recommendation
**분석 범위:** 프론트엔드 코드 하드코딩 확인

---

## 1. 요약

custom-recommendation 페이지의 **프론트엔드 코드에 하드코딩된 종목 데이터는 없습니다.**

모든 데이터는 API 호출과 WebSocket을 통해 동적으로 로드됩니다.

---

## 2. 분석 결과

### 2.1 페이지 컴포넌트 (`page.tsx`)

**파일:** `/frontend/app/custom-recommendation/page.tsx`

**분석 결과:** ✅ 하드코딩 없음

- 모든 데이터는 `useDaytradingStore()`와 `useDaytradingSignals()` hook을 통해 가져옴
- `signals` 상태는 API와 WebSocket에서 동적으로 로드됨
- 페이지에 하드코딩된 종목 코드나 이름 없음

```typescript
// 실시간 데이터와 스토어 데이터 병합 (실시간 우선)
const signals = useMemo(() => {
  return wsSignals.length > 0 ? wsSignals : storeSignals
}, [wsSignals, storeSignals])
```

### 2.2 Store (`daytradingStore.ts`)

**파일:** `/frontend/store/daytradingStore.ts`

**분석 결과:** ✅ 하드코딩 없음

- `fetchDaytradingSignals()`: API 호출 (`/api/daytrading/signals`)
- `scanDaytradingMarket()`: 스캔 API 호출 (`/api/daytrading/scan`)
- `analyzeStocks()`: 분석 API 호출 (`/api/daytrading/analyze`)
- 하드코딩된 데이터 없음

```typescript
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

### 2.3 API 클라이언트 (`api-client.ts`)

**파일:** `/frontend/lib/api-client.ts`

**분석 결과:** ✅ 하드코딩 없음

```typescript
// 단타 시그널 조회
async getDaytradingSignals(params?: {
  min_score?: number;
  market?: "KOSPI" | "KOSDAQ";
  limit?: number;
}): Promise<IDaytradingSignalsResponse> {
  const response = await api.get<IDaytradingSignalsResponse>("/api/daytrading/signals", { params });
  return response.data;
}
```

### 2.4 WebSocket Hook (`useWebSocket.ts`)

**파일:** `/frontend/hooks/useWebSocket.ts`

**분석 결과:** ✅ 하드코딩 없음

- `useDaytradingSignals()`: `signal:daytrading` 토픽 구독
- `useRealtimePrices()`: `price:{ticker}` 토픽 구독
- 모든 데이터는 WebSocket 메시지로 수신

---

## 3. 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    custom-recommendation 페이지                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. 초기 로드                                                      │
│     useDaytradingStore.fetchDaytradingSignals()                   │
│           ↓                                                       │
│     GET /api/daytrading/signals                                   │
│           ↓                                                       │
│     API Gateway → Daytrading Scanner (5115)                       │
│           ↓                                                       │
│     DB 조회 (daytrading_signals 테이블)                           │
│                                                                   │
│  2. 실시간 업데이트                                                │
│     useDaytradingSignals()                                       │
│           ↓                                                       │
│     WebSocket 연결 (wss://stock.ralphpark.com/ws)                │
│           ↓                                                       │
│     signal:daytrading 토픽 구독                                   │
│                                                                   │
│  3. 실시간 가격                                                    │
│     useRealtimePrices(tickerList)                                 │
│           ↓                                                       │
│     price:{ticker} 토픽 구독 (005930, 000270, ...)               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 결론

| 항목 | 상태 | 설명 |
|------|------|------|
| 페이지 컴포넌트 | ✅ 하드코딩 없음 | API/WebSocket 통해 동적 로드 |
| Store | ✅ 하드코딩 없음 | API 호출만 수행 |
| API 클라이언트 | ✅ 하드코딩 없음 | 백엔드 API만 호출 |
| WebSocket Hook | ✅ 하드코딩 없음 | 토픽 구독만 수행 |

**프론트엔드는 완전히 동적으로 작동하며, 하드코딩된 데이터가 없습니다.**

---

## 5. 참고 파일

| 파일 | 경로 |
|------|------|
| 페이지 컴포넌트 | `/home/ralph/work/python/kr_stock_analysis/frontend/app/custom-recommendation/page.tsx` |
| Store | `/home/ralph/work/python/kr_stock_analysis/frontend/store/daytradingStore.ts` |
| API 클라이언트 | `/home/ralph/work/python/kr_stock_analysis/frontend/lib/api-client.ts` |
| WebSocket Hook | `/home/ralph/work/python/kr_stock_analysis/frontend/hooks/useWebSocket.ts` |
