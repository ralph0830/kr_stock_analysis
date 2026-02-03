# VCP 시그널 실시간 업데이트 아키텍처 분석 보고서

**분석 일자**: 2026-02-03
**분석자**: Claude Code QA
**범위**: 프론트엔드/백엔드 전체 아키텍처

---

## 1. 요약

### 1.1 문제 정의

VCP 시그널이 실시간으로 변동되어야 하지만, 현재 시스템에서는 시그널 업데이트가 실시간으로 전달되지 않음

### 1.2 핵심 원인

| 원인 | 위치 | 설명 |
|------|------|------|
| **WebSocket 브로드캐스터 없음** | 백엔드 | Signal 전용 브로드캐스터가 존재하지 않음 |
| **VCP 스캐너 연결 부재** | VCP 서비스 | DB 저장 후 WebSocket 알림 없음 |
| **프론트엔드 Hook 없음** | 프론트엔드 | `useSignals()` Hook이 존재하지 않음 |
| **메시지 타입 미정의** | 타입 정의 | `signal_update` 메시지 타입 없음 |

---

## 2. 백엔드 분석

### 2.1 현재 WebSocket 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WebSocket Server                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     ConnectionManager                          │  │
│  │  - active_connections: Dict[client_id, WebSocket]             │  │
│  │  - subscriptions: Dict[topic, Set[client_id]]                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     PriceBroadcaster                          │  │
│  │  - _active_tickers: Set[str]                                  │  │
│  │  - broadcast_price_update(ticker, price_data)                 │  │
│  │  - start() / stop() / is_running()                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    HeartbeatManager                           │  │
│  │  - 30초 간격 ping/pong                                         │  │
│  │  - 연결 상태 모니터링                                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 VCP Scanner 서비스 분석

**파일**: `services/vcp_scanner/main.py`

#### 2.2.1 VCP 스캔 엔드포인트

```python
@app.post("/scan", response_model=ScanResponse)
async def scan_vcp_patterns(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    VCP 패턴 스캔 실행

    Flow:
    1. analyzer.scan_market()로 시장 스캔
    2. save_vcp_signals_to_db()로 DB 저장
    3. 결과 반환
    """
    analyzer = get_analyzer()
    results = await analyzer.scan_market(
        market=request.market,
        top_n=request.top_n,
        min_score=request.min_score
    )

    # DB 저장
    saved_count = save_vcp_signals_to_db(results)

    return ScanResponse(
        results=[r.to_dict() for r in results],
        count=len(results),
        scanned_at=datetime.now().isoformat(),
        saved=saved_count > 0,
    )
    # ⚠️ WebSocket 브로드캐스트 없음!
```

#### 2.2.2 DB 저장 함수

```python
def save_vcp_signals_to_db(results: List[Any], signal_date: Optional[date] = None) -> int:
    """
    VCP 스캔 결과를 DB에 저장

    Flow:
    1. 기존 VCP 시그널 삭제 (DELETE)
    2. 새 시그널 INSERT (Signal 레코드)
    3. commit

    ⚠️ 저장 후 WebSocket 알림 없음
    """
    # ... DB 저장 로직 ...
    db.commit()
    logging.info(f"VCP 시그널 {saved_count}개 DB 저장 완료")
    # ⚠️ 여기서 WebSocket 브로드캐스트 필요!
    return saved_count
```

### 2.3 API Gateway 시그널 라우터 분석

**파일**: `services/api_gateway/routes/signals.py`

#### 2.3.1 시그널 조회 엔드포인트

```python
@router.get("/vcp", response_model=VCPSignalsResponse)
def get_active_vcp_signals(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db_session),
) -> VCPSignalsResponse:
    """
    활성 VCP 시그널 상위 10개 조회

    ⚠️ REST API만 제공, WebSocket 푸시 없음
    """
    vcp_repo = VCPSignalRepository(session)
    signals = vcp_repo.get_active_vcp_signals(limit=limit, market=market)

    return VCPSignalsResponse(
        signals=signal_items,
        count=len(signal_items),
        generated_at=generated_at,
    )
```

**문제점**: REST API로만 제공되며, 실시간 업데이트를 위한 WebSocket 푸시 메커니즘 없음

### 2.4 WebSocket Routes 분석

**파일**: `src/websocket/routes.py`

#### 2.4.1 현재 지원 토픽

| 토픽 패턴 | 용도 | 브로드캐스터 |
|-----------|------|-------------|
| `price:{ticker}` | 종목 가격 업데이트 | `price_broadcaster` ✅ |
| `index:*` | 지수 업데이트 | `index_broadcaster` ✅ (구현됨) |
| `market_gate` | 마켓 게이트 | `market_gate_broadcaster` ✅ (구현됨) |
| `signal:*` | **시그널 업데이트** | ❌ **없음** |

#### 2.4.2 WebSocket 메시지 핸들러

```python
# 현재 메시지 타입별 처리
if message_type == "subscribe":
    topic = data.get("topic")
    connection_manager.subscribe(client_id, topic)
    # ✅ 토픽 구독은 가능하지만...

elif message_type == "unsubscribe":
    topic = data.get("topic")
    connection_manager.unsubscribe(client_id, topic)

elif message_type == "ping":
    await websocket.send_json({"type": "pong"})
```

**문제점**: `signal:*` 토픽을 구독하더라도, 이를 브로드캐스팅하는 컴포넌트가 없음

---

## 3. 프론트엔드 분석

### 3.1 시그널 Store 분석

**파일**: `frontend/store/index.ts` (라인 80-91)

```typescript
fetchSignals: async () => {
  set({ loadingSignals: true, signalsError: null });
  try {
    const signals = await apiClient.getSignals();
    set({ signals, loadingSignals: false });
  } catch (error) {
    set({
      loadingSignals: false,
      signalsError: error instanceof Error ? error.message : "시그널 조회 실패",
    });
  }
},
```

**문제점**:
- 페이지 로드 시 한 번만 호출됨
- 실시간 업데이트를 받는 메커니즘 없음
- WebSocket을 통한 시그널 업데이트 수신 로직 없음

### 3.2 WebSocket 메시지 타입 분석

**파일**: `frontend/types/index.ts` (라인 83-92)

```typescript
export type WSMessageType =
  | "connected"
  | "subscribed"
  | "unsubscribed"
  | "price_update"       // ✅ 가격 업데이트
  | "index_update"       // ✅ 지수 업데이트
  | "market_gate_update" // ✅ 마켓 게이트 업데이트
  | "error"
  | "ping"
  | "pong";
// ❌ "signal_update" 타입 없음!
```

### 3.3 WebSocket Hooks 분석

**파일**: `frontend/hooks/useWebSocket.ts`

| Hook | 용도 | 상태 |
|------|------|------|
| `useRealtimePrices()` | 실시간 가격 구독 | ✅ 구현됨 |
| `useMarketGate()` | 마켓 게이트 구독 | ✅ 구현됨 |
| `useSignals()` | **시그널 구독** | ❌ **없음** |

### 3.4 메인 페이지 시그널 표시

**파일**: `frontend/app/page.tsx` (라인 198-249)

```typescript
{/* VCP Signals (간단 버전) */}
{!showDashboard && signals.length > 0 && (
  <section>
    <h2>활성 VCP 시그널 ({signals.length}개)</h2>
    {/* ... 시그널 테이블 ... */}
  </section>
)}
```

**문제점**:
- `signals` 상태는 페이지 로드 시 한 번만 설정됨
- 실시간 업데이트로 인한 재랜더링 로직 없음

---

## 4. 데이터 흐름 분석

### 4.1 현재 데이터 흐름 (비실시간)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         현재 VCP 시그널 데이터 흐름                       │
└─────────────────────────────────────────────────────────────────────────┘

1. Celery Beat (매일 정해진 시간)
   ↓
2. VCP Scan Task 실행
   ↓
3. VCP Scanner Service (POST /scan)
   ↓
4. DB에 시그널 저장 (DELETE + INSERT)
   ↓
5. ❌ WebSocket 브로드캐스트 없음
   ↓
6. ❌ 프론트엔드는 새로고침해야 업데이트 확인
```

### 4.2 가격 데이터 흐름 (실시간 - 비교)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         실시간 가격 데이터 흐름 (참조)                     │
└─────────────────────────────────────────────────────────────────────────┘

1. Kiwoom WebSocket (실시간 체결)
   ↓
2. KiwoomWebSocketBridge._on_receive_real_data()
   ↓
3. price_broadcaster.broadcast_price_update(ticker, data)
   ↓
4. ConnectionManager.broadcast("price:005930", message)
   ↓
5. ✅ 프론트엔드 WebSocket 클라이언트 수신
   ↓
6. ✅ useRealtimePrices Hook이 상태 업데이트
   ↓
7. ✅ UI 자동 갱신
```

---

## 5. 아키텍처 개선 방안

### 5.1 백엔드: SignalBroadcaster 구현

**파일**: `src/websocket/server.py` (신규)

```python
class SignalBroadcaster:
    """
    VCP 시그널 실시간 브로드캐스터

    PriceBroadcaster와 동일한 패턴으로 구현
    """

    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def broadcast_signal_update(self, signals: List[Dict]):
        """
        시그널 업데이트 브로드캐스트

        Args:
            signals: 업데이트된 시그널 리스트
        """
        message = {
            "type": "signal_update",
            "data": {
                "signals": signals,
                "count": len(signals),
                "timestamp": datetime.now().isoformat(),
            }
        }

        # signal:vcp 토픽으로 브로드캐스트
        await self._connection_manager.broadcast("signal:vcp", message)

    async def start(self):
        """브로드캐스터 시작"""
        self._running = True

    async def stop(self):
        """브로드캐스터 중지"""
        self._running = False

    def is_running(self) -> bool:
        return self._running
```

### 5.2 VCP Scanner Service: 저장 후 브로드캐스트

**파일**: `services/vcp_scanner/main.py` (수정 필요)

```python
def save_vcp_signals_to_db(results: List[Any], signal_date: Optional[date] = None) -> int:
    """
    VCP 스캔 결과를 DB에 저장 후 WebSocket 브로드캐스트
    """
    # ... 기존 DB 저장 로직 ...

    # ✅ 추가: WebSocket 브로드캐스트
    try:
        import asyncio
        from src.websocket.server import signal_broadcaster

        # 비동기 브로드캐스트
        signal_dicts = [r.to_dict() for r in results]
        asyncio.create_task(
            signal_broadcaster.broadcast_signal_update(signal_dicts)
        )
        logging.info(f"VCP 시그널 {len(signal_dicts)}개 WebSocket 브로드캐스트 완료")
    except Exception as e:
        logging.warning(f"WebSocket 브로드캐스트 실패: {e}")

    return saved_count
```

### 5.3 프론트엔드: WebSocket 메시지 타입 추가

**파일**: `frontend/types/index.ts`

```typescript
export type WSMessageType =
  | "connected"
  | "subscribed"
  | "unsubscribed"
  | "price_update"
  | "index_update"
  | "market_gate_update"
  | "signal_update"       // ✅ 추가
  | "error"
  | "ping"
  | "pong";

export interface SignalUpdateMessage {
  type: "signal_update";
  data: {
    signals: Signal[];
    count: number;
    timestamp: string;
  };
}
```

### 5.4 프론트엔드: useSignals Hook 구현

**파일**: `frontend/hooks/useWebSocket.ts` (신규)

```typescript
/**
 * VCP 시그널 실시간 구독 Hook
 */
export function useSignals() {
  const { subscribe, addMessageListener, removeMessageListener } = useWebSocket();
  const setSignals = useStore((state) => state.setSignals);

  useEffect(() => {
    // signal:vcp 토픽 구독
    const unsubscribe = subscribe("signal:vcp");

    // 메시지 리스너 등록
    const handleSignalUpdate = (message: WSMessage) => {
      if (message.type === "signal_update") {
        setSignals(message.data.signals);
      }
    };

    addMessageListener(handleSignalUpdate);

    return () => {
      unsubscribe();
      removeMessageListener(handleSignalUpdate);
    };
  }, [subscribe, addMessageListener, removeMessageListener, setSignals]);
}
```

### 5.5 프론트엔드: 메인 페이지에서 Hook 사용

**파일**: `frontend/app/page.tsx`

```typescript
// ✅ 추가
import { useSignals } from "@/hooks/useWebSocket";

export default function HomePage() {
  // ✅ 시그널 실시간 구독
  useSignals();  // 시그널 업데이트 자동 수신

  // ... 기존 코드 ...
}
```

---

## 6. 구현 우선순위

### Phase 1: 백엔드 브로드캐스터 구현 (높음)

| 작업 | 파일 | 우선순위 |
|------|------|----------|
| `SignalBroadcaster` 클래스 구현 | `src/websocket/server.py` | 높음 |
| `signal_broadcaster` 인스턴스 생성 | `src/websocket/server.py` | 높음 |
| VCP Scanner 브로드캐스트 호출 | `services/vcp_scanner/main.py` | 높음 |

### Phase 2: 프론트엔드 Hook 구현 (높음)

| 작업 | 파일 | 우선순위 |
|------|------|----------|
| `signal_update` 메시지 타입 추가 | `frontend/types/index.ts` | 높음 |
| `useSignals()` Hook 구현 | `frontend/hooks/useWebSocket.ts` | 높음 |
| 메인 페이지 Hook 사용 | `frontend/app/page.tsx` | 중간 |

### Phase 3: 테스트 및 검증 (중간)

| 작업 | 설명 |
|------|------|
| 단위 테스트 | SignalBroadcaster 테스트 |
| 통합 테스트 | VCP Scanner → WebSocket → 프론트엔드 흐름 |
| E2E 테스트 | Playwright로 실시간 업데이트 확인 |

---

## 7. 요약

### 7.1 현재 상태

| 항목 | 상태 | 설명 |
|------|------|------|
| VCP 시그널 생성 | ✅ 작동 | Celery Beat로 정기 실행 |
| DB 저장 | ✅ 작동 | Signal 테이블에 저장됨 |
| REST API 조회 | ✅ 작동 | `/api/kr/signals`로 조회 가능 |
| WebSocket 브로드캐스트 | ❌ **없음** | 실시간 푸시 메커니즘 부재 |
| 프론트엔드 실시간 수신 | ❌ **없음** | 새로고침해야 업데이트 확인 |

### 7.2 근본 원인

1. **백엔드**: VCP Scanner가 DB 저장 후 WebSocket 브로드캐스트를 하지 않음
2. **백엔드**: Signal 전용 브로드캐스터(`SignalBroadcaster`)가 없음
3. **프론트엔드**: `signal_update` 메시지 타입이 정의되지 않음
4. **프론트엔드**: 시그널 실시간 구독 Hook(`useSignals`)이 없음

### 7.3 해결 방안

1. **SignalBroadcaster 구현**: `PriceBroadcaster`와 동일한 패턴으로 구현
2. **VCP Scanner 연결**: DB 저장 후 `signal_broadcaster.broadcast_signal_update()` 호출
3. **프론트엔드 타입 추가**: `signal_update` 메시지 타입 정의
4. **프론트엔드 Hook 구현**: `useSignals()` Hook으로 실시간 구독

---

## 8. 참조: 정상 작동하는 가격 실시간 흐름

### 8.1 가격 브로드캐스터 구현

**파일**: `src/websocket/server.py`

```python
class PriceBroadcaster:
    """종목 가격 실시간 브로드캐스터"""

    async def broadcast_price_update(self, ticker: str, price_data: dict):
        """가격 업데이트 브로드캐스트"""
        message = {
            "type": "price_update",
            "ticker": ticker,
            "data": price_data,
        }
        await self._connection_manager.broadcast(f"price:{ticker}", message)
```

### 8.2 프론트엔드 가격 Hook

**파일**: `frontend/hooks/useWebSocket.ts`

```typescript
export function useRealtimePrices(tickers: string[]) {
  const { subscribe, addMessageListener, removeMessageListener } = useWebSocket();
  const updatePrice = useStore((state) => state.updateRealtimePrice);

  useEffect(() => {
    // 토픽 구독
    const unsubscribes = tickers.map((ticker) =>
      subscribe(`price:${ticker}`)
    );

    // 메시지 리스너
    const handlePriceUpdate = (message: WSMessage) => {
      if (message.type === "price_update") {
        updatePrice(message.ticker, message.data);
      }
    };

    addMessageListener(handlePriceUpdate);

    return () => {
      unsubscribes.forEach((unsub) => unsub());
      removeMessageListener(handlePriceUpdate);
    };
  }, [tickers, subscribe, addMessageListener, removeMessageListener, updatePrice]);
}
```

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
