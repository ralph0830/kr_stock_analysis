# VCP 시그널 실시간 업데이트 백엔드 구현 요청

**전달 일자**: 2026-02-03
**작성자**: Claude Code (Frontend)
**관련 문서**: `docs/report/vcp_realtime_update_analysis_20260203.md`

---

## 1. 개요

### 1.1 목적

VCP 시그널이 생성/업데이트될 때 프론트엔드로 실시간 푸시 알림을 보내는 기능 구현 요청

### 1.2 현재 상태

| 항목 | 상태 | 설명 |
|------|------|------|
| 프론트엔드 | ✅ 완료 | `signal_update` 메시지 수신 준비됨 |
| 백엔드 | 🔴 필요 | SignalBroadcaster 구현 필요 |
| VCP Scanner | 🔴 필요 | 브로드캐스트 호출 추가 필요 |

---

## 2. 프론트엔드 완료 사항

### 2.1 구현 완료

| 파일 | 수정 내용 |
|------|-----------|
| `frontend/types/index.ts` | `signal_update` 메시지 타입 추가 |
| `frontend/lib/websocket.ts` | `SignalUpdateMessage` export 추가 |
| `frontend/store/index.ts` | `setSignals()` 액션 추가 |
| `frontend/hooks/useWebSocket.ts` | `useSignals()` Hook 구현 |
| `frontend/app/dashboard/kr/vcp/page.tsx` | 실시간 업데이트 연결 |

### 2.2 WebSocket 메시지 형식

프론트엔드가 기대하는 메시지 형식:

```json
{
  "type": "signal_update",
  "data": {
    "signals": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "signal_type": "VCP",
        "score": 10,
        "grade": "S",
        "entry_price": 75000,
        "target_price": 82000,
        "stop_loss": 72000,
        "position_size": 1000,
        "reasons": ["수축률 0.4", "외국인 수급 개선"],
        "created_at": "2026-02-03T09:30:00"
      }
    ],
    "count": 1,
    "timestamp": "2026-02-03T09:30:00.123456"
  }
}
```

### 2.3 프론트엔드 구독 토픽

- **토픽**: `signal:vcp`
- **구독 방법**: WebSocket 메시지 `{"type": "subscribe", "topic": "signal:vcp"}`

---

## 3. 백엔드 구현 가이드

### 3.1 SignalBroadcaster 구현

**파일**: `src/websocket/server.py`

```python
class SignalBroadcaster:
    """
    VCP 시그널 실시간 브로드캐스터

    PriceBroadcaster와 동일한 패턴으로 구현
    """

    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
        self._running = False

    async def broadcast_signal_update(self, signals: List[Dict[str, Any]]) -> None:
        """
        시그널 업데이트 브로드캐스트

        Args:
            signals: 업데이트된 시그널 리스트
        """
        from datetime import datetime, timezone

        message = {
            "type": "signal_update",
            "data": {
                "signals": signals,
                "count": len(signals),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        # signal:vcp 토픽으로 브로드캐스트
        await self._connection_manager.broadcast(
            message,
            topic="signal:vcp"
        )

    async def start(self) -> None:
        """브로드캐스터 시작"""
        self._running = True
        logger.info("SignalBroadcaster started")

    async def stop(self) -> None:
        """브로드캐스터 중지"""
        self._running = False
        logger.info("SignalBroadcaster stopped")

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._running
```

### 3.2 전역 인스턴스 생성

**파일**: `src/websocket/server.py`

```python
# 전역 인스턴스 (price_broadcaster와 동일한 패턴)
signal_broadcaster = SignalBroadcaster(connection_manager)
```

### 3.3 VCP Scanner에서 브로드캐스트 호출

**파일**: `services/vcp_scanner/main.py`

`save_vcp_signals_to_db()` 함수 수정:

```python
def save_vcp_signals_to_db(
    results: List[Any],
    signal_date: Optional[date] = None
) -> int:
    """
    VCP 스캔 결과를 DB에 저장 후 WebSocket 브로드캐스트
    """
    # ... 기존 DB 저장 로직 ...

    db.commit()
    logging.info(f"VCP 시그널 {saved_count}개 DB 저장 완료")

    # ========== 추가: WebSocket 브로드캐스트 ==========
    try:
        import asyncio
        from src.websocket.server import signal_broadcaster

        # 비동기 브로드캐스트 실행
        signal_dicts = [r.to_dict() for r in results]

        def run_broadcast():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    signal_broadcaster.broadcast_signal_update(signal_dicts)
                )
            finally:
                loop.close()

        # 백그라운드에서 실행 (DB 트랜잭션 방해 방지)
        import threading
        thread = threading.Thread(target=run_broadcast, daemon=True)
        thread.start()

        logging.info(f"VCP 시그널 {len(signal_dicts)}개 WebSocket 브로드캐스트 완료")
    except Exception as e:
        logging.warning(f"WebSocket 브로드캐스트 실패: {e}")
    # ===================================================

    return saved_count
```

### 3.4 API Gateway 시작 시 브로드캐스터 시작

**파일**: `services/api_gateway/main.py`

```python
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    # ... 기존 시작 로직 ...

    # SignalBroadcaster 시작
    from src.websocket.server import signal_broadcaster
    await signal_broadcaster.start()
    logger.info("SignalBroadcaster started")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    # SignalBroadcaster 중지
    from src.websocket.server import signal_broadcaster
    await signal_broadcaster.stop()
    logger.info("SignalBroadcaster stopped")

    # ... 기존 종료 로직 ...
```

---

## 4. 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VCP 실시간 업데이트 데이터 흐름                       │
└─────────────────────────────────────────────────────────────────────────┘

1. Celery Beat (매일 정해진 시간) 또는 수동 스캔 요청
   ↓
2. VCP Scanner Service (POST /scan)
   ↓
3. analyzer.scan_market()로 시장 스캔
   ↓
4. save_vcp_signals_to_db()로 DB 저장
   ↓
5. ✅ signal_broadcaster.broadcast_signal_update() 호출
   ↓
6. ConnectionManager.broadcast("signal:vcp", message)
   ↓
7. ✅ 프론트엔드 WebSocket 클라이언트 수신
   ↓
8. ✅ useSignals() Hook이 signals 상태 업데이트
   ↓
9. ✅ UI 자동 갱신
```

---

## 5. 테스트 시나리오

### 5.1 수동 스캔 테스트

```bash
# VCP 스캔 요청
curl -X POST http://localhost:5112/scan \
  -H "Content-Type: application/json" \
  -d '{"market": "KOSPI", "top_n": 5, "min_score": 7}'

# 예상 결과:
# 1. DB에 시그널 저장
# 2. WebSocket으로 signal_update 메시지 브로드캐스트
# 3. 프론트엔드 VCP 페이지에서 실시간 업데이트 확인
```

### 5.2 WebSocket 구독 확인

```javascript
// 브라우저 콘솔에서 실행
const ws = new WebSocket("ws://localhost:5111/ws");

ws.onopen = () => {
  // signal:vcp 토픽 구독
  ws.send(JSON.stringify({ type: "subscribe", topic: "signal:vcp" }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log("Received:", message);

  // 기대 형식:
  // {
  //   "type": "signal_update",
  //   "data": {
  //     "signals": [...],
  //     "count": N,
  //     "timestamp": "..."
  //   }
  // }
};
```

---

## 6. 검증 체크리스트

백엔드 구현 후 다음 항목 확인:

- [ ] `SignalBroadcaster` 클래스 구현 완료
- [ ] `signal_broadcaster` 전역 인스턴스 생성
- [ ] VCP Scanner `save_vcp_signals_to_db()`에 브로드캐스트 호출 추가
- [ ] API Gateway 시작/종료 시 브로드캐스터 시작/중지
- [ ] WebSocket `/ws/stats` 엔드포인트에서 `signal:vcp` 구독 확인
- [ ] 수동 스캔 시 프론트엔드 실시간 업데이트 확인

---

## 7. 참조: PriceBroadcaster 기존 구현

**파일**: `src/websocket/server.py`

```python
class PriceBroadcaster:
    """종목 가격 실시간 브로드캐스터 (참조용)"""

    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
        self._active_tickers: Set[str] = set()
        self._running = False

    async def broadcast_price_update(
        self, ticker: str, price_data: dict
    ) -> None:
        """가격 업데이트 브로드캐스트"""
        message = {
            "type": "price_update",
            "ticker": ticker,
            "data": price_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._connection_manager.broadcast(f"price:{ticker}", message)

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running
```

---

## 8. 우선순위

| 순위 | 작업 | 파일 | 심각도 |
|------|------|------|--------|
| 1 | `SignalBroadcaster` 클래스 구현 | `src/websocket/server.py` | 높음 |
| 2 | VCP Scanner 브로드캐스트 호출 | `services/vcp_scanner/main.py` | 높음 |
| 3 | API Gateway 시작/종료 로직 | `services/api_gateway/main.py` | 중간 |

---

## 9. 연락처

질문 사항 있으면 프론트엔드 팀에 문의 바랍니다.

---

*전달일: 2026-02-03*
*버전: 1.0*
