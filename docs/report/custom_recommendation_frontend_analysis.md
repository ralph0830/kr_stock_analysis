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
- 필터링 (시장, 최소 점수, 표시 개수)
- 시장 스캔 기능 (백엔드 스캔 트리거)

---

## 2. 기술 아키텍처

### 2.1 주요 컴포넌트

| 파일 | 경로 | 설명 |
|------|------|------|
| 페이지 컴포넌트 | `/frontend/app/custom-recommendation/page.tsx` | 메인 페이지 |
| 시그널 테이블 | `/frontend/components/DaytradingSignalTable.tsx` | 시그널 목록 표시 |
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
│           │                                 ▼                    │
│  ┌────────┴─────────────┐      ┌─────────────────────────────┐  │
│  │ useDaytradingSignals │◄─────┤   API Gateway               │  │
│  │ (WebSocket Hook)     │      │   /api/daytrading/signals   │  │
│  └────────┬─────────────┘      └─────────────────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────┐                                        │
│  │ DaytradingSignalTable │ (UI 렌더링)                          │
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
      // 외부 도메인: NPM 리버스 프록시 경로 사용
      return `${wsProtocol}//${hostname}/ws`;
    })()
  : "ws://localhost:5111/ws";
```

**2) 연결 상태 관리**
- `connectionState`: "disconnected" | "connecting" | "connected" | "error"
- `clientId`: 연결 시 서버에서 할당
- `reconnectCount`: 재연결 시도 횟수 (최대 10회)

**3) 실제 연결 로그 (Playwright 캡처)**
```
[log] [useWebSocket] Getting client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] Created new client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: disconnected → connecting
[log] [WebSocket] Connected to wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: connecting → connected
[log] [WebSocket] Ping timer started (interval: 30000 ms)
[log] [WebSocket] Client ID: 03131e6b-8c20-496b-ac25-c3efa4d3ee34
```

### 3.2 실시간 시그널 구독

**토픽 구독**
```typescript
// /frontend/hooks/useWebSocket.ts:847-851
// signal:daytrading 토픽 구독
subscribe("signal:daytrading");
```

**메시지 핸들러**
```typescript
// /frontend/hooks/useWebSocket.ts:830-844
const unsubscribeMessage = client.onMessage((message: WSMessage) => {
  if (message.type === "signal_update") {
    const signalMsg = message as SignalUpdateMessage;
    const data = signalMsg.data as any;
    // Daytrading 시그널 (checks 필드가 있는지 확인)
    if (data.signals && data.signals.length > 0 && "checks" in data.signals[0]) {
      setSignals(data.signals);
      setIsRealtime(true);
      setLastUpdate(new Date(data.timestamp));
    }
  }
});
```

### 3.3 실시간 가격 연동 (현재 미사용)

`useRealtimePrices` Hook이 존재하며 종목별 실시간 가격 구독을 지원하지만, **custom-recommendation 페이지에서는 사용되지 않습니다.**

```typescript
// /frontend/hooks/useWebSocket.ts:444-500
// 종목들 자동 구독 (연결 상태 확인 후 구독)
tickers.forEach((ticker) => {
  subscribe(`price:${ticker}`);
});
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
[log] [useDaytradingSignals] Loaded initial signals: 3
```

### 4.2 시장 스캔 기능

**API 엔드포인트**
```
POST /api/daytrading/scan
```

**요청 바디**
```typescript
{
  market?: "KOSPI" | "KOSDAQ",
  limit: number
}
```

### 4.3 API 클라이언트 설정

**BaseURL 동적 설정**
```typescript
// /frontend/lib/api-client.ts:45-67
const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const isLocal = hostname === "localhost" || hostname === "127.0.0.1";

    if (!isLocal) {
      // 외부 도메인: 현재 도메인 사용 (NPM 리버스 프록시)
      return `${protocol}//${hostname}`;
    }
    // 로컬 개발: 포트 5111 직접 연결
    return `${protocol}//${hostname}:5111`;
  }
  return "http://api-gateway:5111";  // SSR 환경
};
```

**재시도 정책**
- 5xx 에러 또는 네트워크 에러 시 최대 5회 재시도
- 지수 백오프 (1s, 2s, 4s, 5s 최대)

---

## 5. UI 구성 분석

### 5.1 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: ⚡ 단타 추천  [실시간]           [대시보드]             │
├──────────────────┬──────────────────────────────────────────────┤
│  필터 패널        │  시그널 목록                                  │
│  ─────────────    │  ┌────────────────────────────────────────┐ │
│  시장: 전체       │  │ 삼성전자 (005930)                      │ │
│  최소 점수: 60    │  │ S 등급 | 강력 매수 | 90점              │ │
│  표시 개수: 50    │  │ [체크리스트 7개 표시]                   │ │
│  ─────────────    │  │ 진입: 75,000원 목표: 80,000원          │ │
│  [새로고침]       │  └────────────────────────────────────────┘ │
│  [시장 스캔]      │  ┌────────────────────────────────────────┐ │
│  [필터 초기화]    │  │ 기아 (000270)                           │ │
│  ─────────────    │  │ A 등급 | 매수 | 75점                    │ │
│  총 3개 시그널    │  │ [체크리스트 7개 표시]                   │ │
│  ─────────────    │  │ 진입: 120,000원 목표: 128,000원        │ │
│  [단타 추천이란?] │  └────────────────────────────────────────┘ │
│                   │  ┌────────────────────────────────────────┐ │
│                   │  │ LG전자 (066570)                        │ │
│                   │  │ C 등급 | 45점                          │ │
│                   │  └────────────────────────────────────────┘ │
└──────────────────┴──────────────────────────────────────────────┘
```

### 5.2 데이터 표시

**실제로 표시된 종목 (3개)**
1. **삼성전자 (005930)** - S 등급, 90점
2. **기아 (000270)** - A 등급, 75점
3. **LG전자 (066570)** - C 등급, 45점

**체크리스트 항목 (7개)**
- 거래량 폭증 (15점)
- 모멘텀 돌파 (15점)
- 박스권 탈출 (15점)
- 5일선 위 (15점)
- 기관 매수 (15점)
- 낙폭 과대 (15점)
- 섹터 모멘텀 (15점)

---

## 6. 발견한 사항

### 6.1 정상 작동 기능

| 항목 | 상태 | 설명 |
|------|------|------|
| WebSocket 연결 | ✅ | `wss://stock.ralphpark.com/ws` 정상 연결 |
| API 호출 | ✅ | `/api/daytrading/signals` 정상 응답 |
| 초기 데이터 로드 | ✅ | 3개 시그널 정상 표시 |
| 실시간 상태 표시 | ✅ | "실시간" 배지 표시됨 |
| Ping/Pong | ✅ | 30초 간격 정상 동작 |

### 6.2 개선 가능 사항

| 항목 | 현황 | 개선 제안 |
|------|------|----------|
| 실시간 가격 연동 | ❌ 미사용 | 종목별 실시간 가격 업데이트 기능 추가 |
| WebSocket 시그널 업데이트 | ⚠️ 미확인 | 실시간 시그널 업데이트 메시지 수신 미확인 |
| 데이터 자동 갱신 | ⚠️ 수동 | "새로고침" 버튼 클릭 시에만 갱신 |

### 6.3 잠재적 문제점

1. **실시간 가격 연동 미구현**
   - `useRealtimePrices` Hook이 존재하지만 페이지에서 사용하지 않음
   - 현재가 정보가 표시되지 않음 (매매 기준가만 표시)

2. **WebSocket 시그널 업데이트 미확인**
   - `signal:daytrading` 토픽 구독은 수행됨
   - 하지만 실제로 백엔드에서 시그널 업데이트 브로드캐스트가 있는지 확인 필요

3. **Market Gate 데이터 수신 확인**
   - 콘솔에서 Market Gate 업데이트가 수신됨: 
     ```
     [log] [useMarketGate] Received update: {status: RED, level: 0, kospi: 4981.88, ...}
     ```
   - 이는 WebSocket이 정상 작동함을 증명

---

## 7. 결론

custom-recommendation 페이지는 **기본적인 실시간 연동 기능이 정상 작동**합니다.

- WebSocket 연결: ✅ 정상
- API 호출: ✅ 정상
- 데이터 표시: ✅ 정상 (3개 시그널)

**다만, 실시간 가격 연동 기능은 구현되어 있지 않으며**, 단타 시그널 자체의 실시간 업데이트는 백엔드에서 브로드캐스트할 경우에만 작동합니다.

---

## 8. 참고 파일

| 파일 | 경로 |
|------|------|
| 페이지 컴포넌트 | `/home/ralph/work/python/kr_stock_analysis/frontend/app/custom-recommendation/page.tsx` |
| WebSocket Hook | `/home/ralph/work/python/kr_stock_analysis/frontend/hooks/useWebSocket.ts` |
| API 클라이언트 | `/home/ralph/work/python/kr_stock_analysis/frontend/lib/api-client.ts` |
| 상태 관리 | `/home/ralph/work/python/kr_stock_analysis/frontend/store/daytradingStore.ts` |
| 시그널 테이블 | `/home/ralph/work/python/kr_stock_analysis/frontend/components/DaytradingSignalTable.tsx` |
