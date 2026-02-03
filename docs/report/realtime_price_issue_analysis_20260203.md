# 실시간 가격 모니터링 기능 분석 보고서

**분석 일자**: 2026-02-03
**분석 대상**: 랜딩페이지 실시간 가격 모니터링 기능
**심각도**: 높음 (핵심 기능 미작동)

---

## 1. 실행 요약 (Executive Summary)

### 1.1 문제 개요
랜딩페이지(`https://stock.ralphpark.com/`)의 실시간 가격 모니터링 기능이 정상 작동하지 않습니다. 가격 데이터가 표시되지 않고 "데이터 대기 중..." 메시지가 지속됩니다.

### 1.2 핵심 발견
| 항목 | 상태 | 설명 |
|------|------|------|
| WebSocket 연결 | ✅ 정상 | 1개 연결 유지 중 |
| 가격 데이터 브로드캐스트 | ✅ 정상 | 서버에서 6개 종목 가격 브로드캐스트 중 |
| price 토픽 구독자 | ❌ **0명** | 구독자가 없어 메시지 전송 불가 |
| market-gate 토픱 구독자 | ✅ 1명 | Market Gate는 정상 작동 |

### 1.3 근본 원인
`useRealtimePrices` 훅에서 **WebSocket 연결 상태를 확인하지 않고 구독을 시도**하여, 연결되지 않은 상태에서 구독 요청이 대기열에만 추가되고 실제 전송이 이루어지지 않습니다.

### 1.4 영향 범위
- 랜딩페이지 실시간 가격 모니터링 기능 전체
- 사용자 경험: 핵심 기능인 실시간 가격 확인 불가

---

## 2. 문제 상세 분석

### 2.1 사용자 관점에서의 문제

#### 2.1.1 UI 표시 상태
```
┌─────────────────────────────────────┐
│ 삼성전자                  [연결됨]   │
│ 005930                              │
│                                     │
│      데이터 대기 중...               │
└─────────────────────────────────────┘
```

#### 2.1.2 기대 동작
- 실시간 가격이 표시되어야 함
- 변동률, 거래량, 업데이트 시간이 표시되어야 함

#### 2.1.3 실제 동작
- "데이터 대기 중..." 메시지 지속
- WebSocket 연결 상태는 "연결됨"으로 표시됨
- 가격 데이터는 수신되지 않음

### 2.2 기술적 분석

#### 2.2.1 프론트엔드 아키텍처

```
page.tsx (랜딩페이지)
│
├── useMarketGate() Hook
│   └── subscribe("market-gate") ✅ 작동
│
├── RealtimePriceCard 컴포넌트
│   └── useRealtimePrices([ticker]) Hook
│       └── subscribe(`price:${ticker}`) ❌ 실패
│
└── Watchlist 컴포넌트
```

#### 2.2.2 WebSocket 싱글톤 패턴

모든 훅이 하나의 `WebSocketClient` 인스턴스를 공유합니다:

```typescript
// lib/websocket.ts
let _wsClient: WebSocketClient | null = null;

export function createWebSocketClient(url: string): WebSocketClient {
  if (!_wsClient) {
    _wsClient = new WebSocketClient(url);
  }
  return _wsClient;
}
```

이로 인해 발생하는 문제:
- 각 훅이 독립적으로 `useEffect` 실행
- 연결 상태 공유 복잡성
- 구독 타이밍 경합

#### 2.2.3 구독 처리 흐름

**정상 작동하는 useMarketGate**:
```typescript
// hooks/useWebSocket.ts:500-525
export function useMarketGate() {
  const { connected, subscribe } = useWebSocket({...});

  useEffect(() => {
    if (connected) {  // ✅ 연결 상태 확인
      subscribe("market-gate");
      console.log("[useMarketGate] Subscribed to market-gate topic");
    }
    return () => {};
  }, [connected, subscribe]);  // ✅ connected를 의존성으로 사용
}
```

**문제가 발생하는 useRealtimePrices**:
```typescript
// hooks/useWebSocket.ts:381-408
export function useRealtimePrices(tickers: string[]) {
  const { connected, subscribe, unsubscribe } = useWebSocket({...});

  useEffect(() => {
    // ❌ 연결 상태 확인 없음
    tickers.forEach((ticker) => {
      console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
      subscribe(`price:${ticker}`);
    });

    return () => {
      tickers.forEach((ticker) => {
        unsubscribe(`price:${ticker}`);
      });
    };
  }, [tickers.join(","), subscribe, unsubscribe]);  // ❌ connected가 의존성에 없음
}
```

#### 2.2.4 WebSocketClient.subscribe() 내부 동작

```typescript
// lib/websocket.ts:248-274
subscribe(topic: string): void {
  // 이미 구독 중이면 무시
  if (this._subscriptions.has(topic)) {
    return;
  }

  // 연결되지 않았으면 대기열에만 추가
  if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
    console.log("[WebSocket] Queueing subscription for:", topic);
    this._pendingSubscriptions.add(topic);  // 대기열에만 추가

    // WebSocket이 닫혀있으면 재연결 시도
    if (this.ws?.readyState === WebSocket.CLOSED) {
      this.connect(Array.from(this._subscriptions), true);
    }
    return;  // ⚠️ 여기서 반환 - 실제 구독 메시지 전송 안 함
  }

  // 실제 메시지 전송
  const message = { type: "subscribe", topic: topic };
  this.ws.send(JSON.stringify(message));
  this._subscriptions.add(topic);
}
```

### 2.3 백엔드 분석

#### 2.3.1 WebSocket 엔드포인트 구조

```python
# src/websocket/routes.py:32-98
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    subscribe: Optional[str] = Query(None),  # URL 파라미터
):
    client_id = str(uuid.uuid4())
    await websocket.accept()

    # ConnectionManager에 등록
    connection_manager.active_connections[client_id] = websocket

    # 초기 구독 처리 (URL 파라미터)
    if subscribe:
        topics = subscribe.split(",")
        for topic in topics:
            topic = topic.strip()
            if topic:
                connection_manager.subscribe(client_id, topic)
                await websocket.send_json({
                    "type": "subscribed",
                    "topic": topic,
                })

    # 환영 메시지
    await websocket.send_json({
        "type": "connected",
        "client_id": client_id,
    })

    # 메시지 수신 루프
    while True:
        data = await websocket.receive_json()
        message_type = data.get("type")

        if message_type == "subscribe":
            topic = data.get("topic")
            if topic:
                connection_manager.subscribe(client_id, topic)
```

#### 2.3.2 ConnectionManager 구독 처리

```python
# src/websocket/server.py:144-177
def subscribe(self, client_id: str, topic: str) -> None:
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    self.subscriptions[topic].add(client_id)
    logger.info(f"Client {client_id} subscribed to {topic}")

    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]
        if ticker.isdigit() and len(ticker) == 6:
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
```

#### 2.3.3 브로드캐스트 메서드

```python
# src/websocket/server.py:116-143
async def broadcast(self, message: dict, topic: Optional[str] = None) -> None:
    if topic:
        recipients = self.subscriptions.get(topic, set())
        print(f"[BROADCAST] Topic={topic}, subscribers={len(recipients)}")
    else:
        recipients = set(self.active_connections.keys())

    sent_count = 0
    for client_id in recipients:
        if client_id in self.active_connections:
            await self.send_personal_message(message, client_id)
            sent_count += 1

    if sent_count > 0:
        print(f"[BROADCAST] Sent to {sent_count} recipients")
    else:
        print(f"[BROADCAST] No recipients found to send to")
```

### 2.4 서버 로그 분석

#### 2.4.1 정상 작동 로그 (market-gate)

```
[WebSocket] Connection attempt from 172.25.0.1:53020
[WebSocket] Connection accepted for {client_id}
[WebSocket] Client {client_id} registered with manager
Client {client_id} subscribed to market-gate
[WebSocket] Welcome message sent to {client_id}
```

#### 2.4.2 가격 브로드캐스트 로그

```
[BROADCAST] Topic=price:005930, subscribers=0  ← 구독자 0명
[BROADCAST] No recipients found to send to
[WS BRIDGE] Broadcasting price update for 005930: 157900.0
[WS BRIDGE] ✅ Broadcasted price update for 005930: 157900.0

[BROADCAST] Topic=price:000660, subscribers=0  ← 구독자 0명
[BROADCAST] No recipients found to send to
[WS BRIDGE] Broadcasting price update for 000660: 873000.0
[WS BRIDGE] ✅ Broadcasted price update for 000660: 873000.0
```

#### 2.4.3 WebSocket 통계 확인

```bash
$ curl http://localhost:5111/ws/stats
{
  "active_connections": 1,
  "subscriptions": {
    "price:005930": 0,      ← 0명
    "price:000660": 0,      ← 0명
    "signals": 0,
    "market-gate": 1        ← 1명 ✅
  },
  "bridge_running": true,
  "broadcaster_running": true
}
```

---

## 3. 근본 원인 (Root Cause)

### 3.1 직접 원인

**`price:*` 토픽 구독자가 0명**입니다. 따라서:
- 서버는 가격 데이터를 브로드캐스트하려고 시도
- 하지만 구독자가 없어서 전송할 대상이 없음
- 클라이언트는 가격 업데이트를 받지 못함

### 3.2 간접 원인

#### 3.2.1 프론트엔드 구독 타이밍 문제

`useRealtimePrices` 훅이 **연결 상태를 확인하지 않고** 구독을 시도합니다.

**문제 시나리오**:
1. 페이지 로드 시 `useMarketGate()`가 먼저 마운트
2. WebSocket 연결 시작 (`connecting` 상태)
3. `useRealtimePrices()`가 마운트되지만 `connected`는 아직 `false`
4. `useEffect`가 실행되어 `subscribe()` 호출
5. `WebSocketClient.subscribe()`에서 연결 안 된 상태 확인
6. 대기열(`_pendingSubscriptions`)에만 추가
7. 연결 완료 후 `_flushPendingSubscriptions()`가 호출되어야 하는데...

#### 3.2.2 대기열 처리 문제

```typescript
// lib/websocket.ts:_flushPendingSubscriptions
private _flushPendingSubscriptions(): void {
  for (const topic of this._pendingSubscriptions) {
    if (!this._subscriptions.has(topic)) {
      this.subscribe(topic);  // 재귀 호출
    }
  }
  this._pendingSubscriptions.clear();
}
```

잠재적 문제:
- 대기열 처리 시점이 `onopen` 핸들러
- 하지만 다른 훅에서 이미 구독을 처리했을 수 있음
- `this._subscriptions.has(topic)` 체크로 인해 중복 구독 방지

#### 3.2.3 여러 훅의 경합

`useWebSocket` 훅을 사용하는 모든 곳:
- `useMarketGate()` → `market-gate` 구독 ✅
- `useRealtimePrices()` → `price:*` 구독 ❌
- `useMarketIndices()` → `market:kospi`, `market:kosdaq` 구독 ❓

각 훅이 **독립적으로** `useEffect`를 실행하므로 타이밍 경합이 발생할 수 있습니다.

### 3.3 기여 원인

#### 3.3.1 백엔드 중복 로그

```python
# routes.py:109-113
logger.debug(f"[WebSocket] Received from {client_id}: {message_type}")
# ... (중간 코드 없음)
logger.debug(f"[WebSocket] Received from {client_id}: {message_type}")  # 중복
```

#### 3.3.2 로그 레벨 설정

구독 처리 로그가 `logger.info()`로 설정되어 있지만 실제로는 출력되지 않습니다:
```python
logger.info(f"Client {client_id} subscribed to {topic}")
```

이 로그가 서버 로그에 없는 것으로 보아, `connection_manager.subscribe()`가 실제로 호출되지 않거나 로거 설정에 문제가 있을 수 있습니다.

---

## 4. 영향 분석 (Impact Analysis)

### 4.1 기능적 영향

| 기능 | 영향 | 심각도 |
|------|------|--------|
| 실시간 가격 모니터링 | 완전 작동 안 함 | 높음 |
| Market Gate 상태 | 정상 작동 | 없음 |
| WebSocket 연결 | 정상 작동 | 없음 |
| VCP 시그널 표시 | 정상 작동 | 없음 |

### 4.2 사용자 경험 영향

1. **신뢰도 하락**: 메인 화면에서 핵심 기능이 작동하지 않음
2. **혼동**: "연결됨" 상태인데 데이터가 안 옴
3. **기대치 불일치**: 실시간이라고 표시되어 있지만 실시간 데이터 없음

### 4.3 비즈니스 영향

- 사용자가 실시간 시장 데이터를 확인할 수 없음
- 서비스 신뢰도에 부정적 영향
- 대시보드로서의 가치 하락

---

## 5. 개선 제안 (Recommendations)

### 5.1 우선순위 1: 프론트엔드 수정 (높음)

#### 5.1.1 useRealtimePrices에 연결 확인 추가

**파일**: `frontend/hooks/useWebSocket.ts`

**수정 전**:
```typescript
export function useRealtimePrices(tickers: string[]) {
  const { connected, subscribe, unsubscribe } = useWebSocket({...});

  useEffect(() => {
    tickers.forEach((ticker) => {
      subscribe(`price:${ticker}`);
    });
    return () => {
      tickers.forEach((ticker) => {
        unsubscribe(`price:${ticker}`);
      });
    };
  }, [tickers.join(","), subscribe, unsubscribe]);  // ❌ connected 없음
}
```

**수정 후**:
```typescript
export function useRealtimePrices(tickers: string[]) {
  const { connected, subscribe, unsubscribe, connecting } = useWebSocket({...});

  useEffect(() => {
    // ✅ 연결 상태 확인
    if (!connected) {
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
  }, [tickers.join(","), subscribe, unsubscribe, connected]);  // ✅ connected 추가

  // ... 나머지 코드
}
```

#### 5.1.2 useMarketIndices도 동일하게 수정

```typescript
export function useMarketIndices() {
  const { connected, subscribe, unsubscribe } = useWebSocket({...});

  useEffect(() => {
    // ✅ 연결 상태 확인
    if (!connected) return;

    subscribe("market:kospi");
    subscribe("market:kosdaq");

    return () => {
      unsubscribe("market:kospi");
      unsubscribe("market:kosdaq");
    };
  }, [connected, subscribe, unsubscribe]);  // 이미 connected 포함됨
}
```

### 5.2 우선순위 2: 디버깅 강화 (중간)

#### 5.2.1 WebSocketClient 구독 상태 로그 추가

**파일**: `frontend/lib/websocket.ts`

```typescript
subscribe(topic: string): void {
  console.log(`[WebSocketClient] subscribe() called for topic: ${topic}`);
  console.log(`[WebSocketClient] Current state:`, {
    connected: this.ws?.readyState === WebSocket.OPEN,
    alreadySubscribed: this._subscriptions.has(topic),
    pendingSubscriptions: Array.from(this._pendingSubscriptions),
  });

  if (this._subscriptions.has(topic)) {
    console.log(`[WebSocketClient] Already subscribed to ${topic}, skipping`);
    return;
  }

  if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
    console.log(`[WebSocketClient] Not connected, queueing subscription for: ${topic}`);
    this._pendingSubscriptions.add(topic);
    // ...
  }

  // 실제 메시지 전송
  console.log(`[WebSocketClient] Sending subscribe message for: ${topic}`);
  this.ws.send(JSON.stringify({ type: "subscribe", topic }));
  this._subscriptions.add(topic);
}
```

#### 5.2.2 브라우저 Console 가이드라인 추가

개발자가 문제를 진단할 수 있도록 Console에 명확한 메시지 출력:

```
[WebSocket] 🔄 Connecting to ws://localhost:5111/ws
[WebSocket] ✅ Connected to ws://localhost:5111/ws
[WebSocket] 📨 Flushing 3 pending subscriptions...
[WebSocket]   → price:005930
[WebSocket]   → price:000660
[WebSocket]   → market-gate
```

### 5.3 우선순위 3: 백엔드 개선 (낮음)

#### 5.3.1 중복 로그 제거

**파일**: `src/websocket/routes.py`

```python
# 109-113행: 중복 로그 제거
logger.debug(f"[WebSocket] Received from {client_id}: {message_type}")
# 아래 중복된 코드 삭제
```

#### 5.3.2 구독 처리 로그 강화

```python
def subscribe(self, client_id: str, topic: str) -> None:
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    # 기존 구독자 수 기록
    before_count = len(self.subscriptions[topic])

    self.subscriptions[topic].add(client_id)

    # 상세 로그
    logger.info(
        f"[SUBSCRIBE] Client {client_id[:8]}... → topic: {topic} "
        f"(before: {before_count}, after: {len(self.subscriptions[topic])})"
    )
```

### 5.4 우선순위 4: 테스트 커버리지 (낮음)

#### 5.4.1 WebSocket 연결 테스트

```typescript
// __tests__/hooks/useRealtimePrices.test.ts
describe("useRealtimePrices", () => {
  it("should subscribe to price topics only when connected", async () => {
    const { result } = renderHook(() => useRealtimePrices(["005930"]), {
      wrapper: WebSocketProvider,
    });

    // 연결 전에는 구독하지 않음
    expect(mockSubscribe).not.toHaveBeenCalled();

    // 연결 후 구독
    act(() => {
      mockWsConnected();
    });

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith("price:005930");
    });
  });
});
```

---

## 6. 검증 계획 (Verification Plan)

### 6.1 단위 테스트

| 항목 | 테스트 방법 | 기대 결과 |
|------|------------|----------|
| 연결 상태 확인 | `connected=false`일 때 구독 안 함 | 대기열에 추가 |
| 연결 후 구독 | `connected=true`가 되면 구독 | `subscribe()` 호출 |
| 중복 구독 방지 | 같은 토픽 재구독 시도 | 무시됨 |

### 6.2 통합 테스트

#### 6.2.1 브라우저 테스트

1. https://stock.ralphpark.com/ 접속
2. 개발자 도구 Console 열기
3. 다음 로그 확인:
   ```
   [useWebSocket] Getting client for: ws://...
   [WebSocket] Connected to ws://...
   [useMarketGate] Subscribed to market-gate topic
   [useRealtimePrices] Subscribing to price:005930
   [WebSocketClient] Sending subscribe message for: price:005930
   ```

4. 네트워크 탭 → WS → 메시지 확인:
   ```json
   {"type":"subscribe","topic":"price:005930"}
   ```

5. 가격 업데이트 수신 확인:
   ```json
   {"type":"price_update","ticker":"005930","data":{...}}
   ```

#### 6.2.2 서버 로그 확인

```bash
# 서버 로그 모니터링
docker logs api-gateway -f | grep -E "SUBSCRIBE|BROADCAST|price:"

# 기대 출력:
# [SUBSCRIBE] Client abc12345... → topic: price:005930 (before: 0, after: 1)
# [BROADCAST] Topic=price:005930, subscribers=1
# [BROADCAST] Sent to 1 recipients
```

### 6.3 API 엔드포인트 확인

```bash
# 구독 상태 확인
curl http://localhost:5111/ws/stats | jq '.subscriptions'

# 기대 결과:
{
  "price:005930": 1,  # ← 1명 이상이어야 함
  "price:000660": 1,
  "market-gate": 1
}
```

---

## 7. 롤백 계획 (Rollback Plan)

### 7.1 롤백 기준

- 실시간 가격이 여전히 표시되지 않음
- WebSocket 연결이 실패함
- Market Gate 기능이 중단됨

### 7.2 롤백 절차

1. Git 이전 커밋으로 복귀
2. Docker 컨테이너 재시작
3. 정상 동작 확인

### 7.3 롤백 후 계획

- 근본 원인 재분석
- 대안 수립 (폴링 방식 등)
- 점진적 롤아웃

---

## 8. 참고 자료 (References)

### 8.1 관련 파일

| 경로 | 설명 |
|------|------|
| `frontend/app/page.tsx` | 랜딩페이지 |
| `frontend/components/RealtimePriceCard.tsx` | 실시간 가격 카드 |
| `frontend/hooks/useWebSocket.ts` | WebSocket 훅 |
| `frontend/lib/websocket.ts` | WebSocket 클라이언트 |
| `src/websocket/routes.py` | WebSocket 라우터 |
| `src/websocket/server.py` | WebSocket 서버 |

### 8.2 관련 문서

- `CLAUDE.md` - 프로젝트 설정 및 개발 가이드
- `docs/api/API_GUIDE.md` - API 엔드포인트 문서
- `docs/SERVICE_MODULARIZATION.md` - 서비스 모듈화 가이드

### 8.3 유사 이슈

- `docs/report/frontend_vcp_issue_final.md` - VCP 관련 프론트엔드 이슈

---

## 9. 변경 이력 (Changelog)

| 일자 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-03 | 1.0 | 초기 분석 보고서 작성 |

---

## 10. 승인 (Approval)

| 역할 | 이름 | 일자 | 서명 |
|------|------|------|------|
| 분석자 | Claude (AI) | 2026-02-03 | - |
| 검토자 | - | - | - |
| 승인자 | - | - | - |

---

*보고서 종료*
