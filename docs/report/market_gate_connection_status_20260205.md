# Market Gate "연결대기" 상태 분석 보고서

**분석 일자:** 2026-02-05  
**분석 대상:** https://stock.ralphpark.com  
**분석 도구:** Playwright (브라우저 자동화, 콘솔 로그, 네트워크 분석)

---

## 1. 요약 (Executive Summary)

### 문제 현상
Market Gate 상태 옆에 "연결 대기"라고 표시되지만, 실제로는:
- **WebSocket 연결:** 정상 (connected)
- **Market Gate 데이터:** 정상 수신 (API 호출 성공)
- **KOSPI/KOSDAQ 데이터:** 정상 표시됨

### 원인
`isRealtime` 상태가 `false`로 유지되어 "연결 대기"로 표시됨. 이 상태는 **WebSocket 메시지를 통해 실시간 업데이트를 받을 때만 `true`**로 설정됨.

---

## 2. 상세 분석

### 2.1 페이지 탐색 결과

| 항목 | 상태 | 설명 |
|------|------|------|
| WebSocket 연결 | ✅ 정상 | `wss://stock.ralphpark.com/ws` 연결됨 |
| API 호출 | ✅ 정상 | `/api/kr/market-gate` 200 OK |
| 데이터 표시 | ✅ 정상 | RED 레벨 50, KOSPI/KOSDAQ 지수 표시됨 |
| 연결 상태 표시 | ⚠️ "연결 대기" | `isRealtime = false` |

### 2.2 콘솔 로그 분석

```log
[WebSocket] Connected to wss://stock.ralphpark.com/ws
[WebSocket] State change: connecting → connected
[WebSocket] Client ID: 6ba49e82-9fc6-4e30-9b16-f38c780d3f12
[useMarketGate] Subscribed to market-gate topic
```

**확인된 내용:**
- WebSocket 연결이 정상적으로 완료됨
- `market-gate` 토픽 구독 요청 전송됨
- 하지만 **Market Gate 업데이트 메시지 수신 로그 없음**

### 2.3 API 응답 분석

```json
{
  "status": "RED",
  "level": 50,
  "kospi_status": "약세",
  "kosdaq_status": "약세",
  "kospi_close": 5163.57,
  "kospi_change_pct": -3.86,
  "kosdaq_close": 1108.41,
  "kosdaq_change_pct": -3.57,
  "updated_at": "2026-02-05T13:17:35.444236"
}
```

API는 정상 응답을 반환함.

---

## 3. 원인 분석 (Root Cause)

### 3.1 프론트엔드 로직

`/home/ralph/work/python/kr_stock_analysis/frontend/hooks/useWebSocket.ts`

```typescript
export function useMarketGate() {
  const [isRealtime, setIsRealtime] = useState(false);  // 초기값: false

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
    onMarketGateUpdate: (data: MarketGateData) => {
      setMarketGate(data);
      setIsRealtime(true);  // WebSocket 메시지 수신 시에만 true로 설정됨!
      // ...
    },
  });

  // API 호출로 가져온 데이터는 isRealtime을 true로 설정하지 않음
  const fetchMarketGate = useCallback(async (): Promise<void> => {
    // ...
    const response = await apiClient.getMarketGate();
    setMarketGate(data);
    // isRealtime 설정 없음! → false로 유지됨
  }, []);
}
```

### 3.2 표시 로직

`/home/ralph/work/python/kr_stock_analysis/frontend/app/page.tsx`

```tsx
<span className={cn(/* ... */)}>
  {isRealtime ? "실시간" : "연결 대기"}  {/* isRealtime = false → "연결 대기" */}
</span>
```

### 3.3 WebSocket 메시지 흐름

```
[Celery Beat] 
  → update_market_gate 태스크 실행 (5분 간격)
  → _broadcast_market_gate_update() 호출
  → Redis Pub: "ws:broadcast:market-gate"
    → [Redis]
      → [WebSocket Server] Redis Sub에서 수신
        → broadcast("market-gate")로 클라이언트에게 전송
          → [Frontend] onMarketGateUpdate() 호출
            → setIsRealtime(true) 실행
```

**현재 상황:** 
- WebSocket 연결됨
- `market-gate` 토픽 구독함
- **하지만 서버에서 메시지가 전송되지 않음** → `isRealtime`이 `false`로 유지됨

---

## 4. 가능한 원인 (Hypothesis)

### 4.1 Celery Beat 미동작
- Celery Beat 스케줄러가 실행 중이 아닐 가능성
- `update-market-gate` 태스크가 5분 간격으로 실행되지 않을 가능성

### 4.2 Redis Pub/Sub 연결 문제
- WebSocket 서버의 Redis Pub/Sub 구독 연결이 끊어졌을 가능성
- `ws:broadcast:market-gate` 채널 메시지가 전달되지 않을 가능성

### 4.3 타이밍 문제
- 페이지 접속 시점에 Celery 태스크가 실행되지 않았을 가능성
- 마지막 업데이트: `2026-02-05T13:17:35` (분석 시간: 13:20)

---

## 5. 개선 방안

### 5.1 즉시 적용 가능한 개선 (UX 향상)

**문제:** API로 데이터를 가져왔어도 "연결 대기"로 표시됨

**해결:** API로 데이터를 가져온 경우 "최신 데이터"로 표시

```typescript
// 변경 전
<span>{isRealtime ? "실시간" : "연결 대기"}</span>

// 변경 제안
<span>
  {isRealtime 
    ? "실시간" 
    : marketGate 
      ? "최신 데이터"  // API로 가져온 데이터가 있으면 표시
      : "연결 대기"}
</span>
```

### 5.2 WebSocket 메시지 수신 확인 로그 추가

개발 환경에서 WebSocket 메시지 수신을 명확히 확인하기 위해:

```typescript
onMarketGateUpdate: (data: MarketGateData) => {
  console.log("[useMarketGate] Received WebSocket update:", data);
  setIsRealtime(true);
  // ...
}
```

### 5.3 Celery Beat 모니터링 강화

Flower 또는 모니터링 대시보드에서 Celery Beat 상태 확인:
- `update-market-gate` 태스크가 정기적으로 실행되는지 확인
- 태스크 실행 로그 확인

### 5.4 서버 사이드 Health Check 추가

```python
@app.get("/api/health/celery")
async def check_celery_health():
    """Celery Beat 상태 확인"""
    # 마지막 Market Gate 업데이트 시간 확인
    # Celery Beat가 활성화되어 있는지 확인
    return {
        "celery_beat_running": True/False,
        "last_market_gate_update": "timestamp",
    }
```

---

## 6. 결론

### 6.1 문제의 본질
"연결 대기"는 **기능적 문제가 아니라 표시 문제**입니다:
- 데이터는 정상적으로 표시됨
- WebSocket도 연결됨
- 단지 "실시간 WebSocket 업데이트를 받고 있지 않다는 상태"를 표시하는 것

### 6.2 사용자 경험
사용자 관점에서:
- "연결 대기" → 연결이 안 된 것으로 오해할 수 있음
- 실제로는 데이터가 정상 표시되고 있음
- **"최신 데이터" 또는 "API 업데이트"로 표시하는 것이 더 정확함**

### 6.3 우선순위

| 우선순위 | 항목 | 영향 |
|----------|------|------|
| 1 | UI 텍스트 수정 ("최신 데이터"로 변경) | 사용자 오해 방지 |
| 2 | Celery Beat 상태 확인 | 실시간 업데이트 복구 |
| 3 | 모니터링 강화 | 향후 문제 조기 감지 |

---

## 7. 첨부: 관련 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| Market Gate Hook | `frontend/hooks/useWebSocket.ts` | `useMarketGate()` 함수 (라인 574-685) |
| 메인 페이지 | `frontend/app/page.tsx` | Market Gate 상태 표시 (라인 88-107) |
| Celery 태스크 | `tasks/market_tasks.py` | `update_market_gate()` 함수 |
| Celery 스케줄 | `tasks/celery_app.py` | `beat_schedule` 설정 (라인 96-100) |
| WebSocket 서버 | `src/websocket/server.py` | Redis Pub/Sub 구독 (라인 920-980) |

---

## 8. 해결 확인 (2026-02-05 22:27)

### 8.1 API Gateway 재시작 후 상태

```bash
docker compose restart api-gateway
```

### 8.2 Redis Pub/Sub 정상 작동 확인

```log
api-gateway  | [REDIS SUB] Got message: pmessage, full: {...}
api-gateway  | [REDIS SUB] Processing pmessage: channel=ws:broadcast:market-gate
api-gateway  | [REDIS SUB] JSON parsed: market_gate_update
api-gateway  | [REDIS SUB] Broadcasting to market-gate...
api-gateway  | [BROADCAST] Topic=market-gate, subscribers=2
```

### 8.3 프론트엔드 수신 확인

```log
[log] [useMarketGate] Received update: {status: RED, level: 0, kospi: 5163.57, ...}
```

### 8.4 페이지 표시 상태

```
● 실시간 연결됨 (ID: 23d4a98d)
Market Gate 상태: 실시간
현재 상태: RED (레벨 0)
업데이트: 2026. 2. 5. 오후 1:27:35
```

---

## 9. 결론 (최종)

### 9.1 근본 원인

1. **API Gateway 서비스 헬스 상태:** Service Registry에서 Daytrading Scanner의 `is_healthy`가 `False`로 설정되어 503 에러 발생
2. **Redis Pub/Sub 구독자:** API Gateway 재시작 전 Redis Pub/Sub 구독 태스크가 정상 작동하지 않음

### 9.2 해결 방법

```bash
docker compose restart api-gateway
```

### 9.3 최종 상태

| 항목 | 재시작 전 | 재시작 후 |
|------|----------|----------|
| Daytrading API | 503 에러 | ✅ 정상 (2개 시그널) |
| Market Gate 상태 | "연결 대기" | ✅ "실시간 연결됨" |
| WebSocket | 연결됨 | ✅ 연결됨 + 메시지 수신 |
| Redis Pub/Sub | 비활성 | ✅ 활성 (subscribers=2) |

### 9.4 권장 사항

1. **서비스 헬스 체크 개선:** 주기적으로 Service Registry 헬스 상태를 갱신하는 메커니즘 구현
2. **Redis Pub/Sub 모니터링:** 구독 태스크 상태를 모니터링하고 실패 시 자동 재시작
3. **UI 텍스트 개선:** API로 데이터를 가져온 경우 "최신 데이터"로 표시하여 혼동 방지

---

**보고 작성자:** Claude Code (Full-Stack Integration Specialist)
**분석 방법:** Playwright 브라우저 자동화 + 코드 분석
**최종 수정:** 2026-02-05 22:28 (API Gateway 재시작 후 정상 작동 확인)
