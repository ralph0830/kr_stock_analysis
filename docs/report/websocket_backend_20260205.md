# WebSocket 백엔드 구현 분석 보고서

**작성일:** 2026-02-05
**범위:** 메인 대시보드(VCP) vs 단타 추천(Daytrading) WebSocket 백엔드 비교

---

## 1. 개요

메인 대시보드와 단타 추천 페이지가 공유하는 WebSocket 백엔드 인프라를 분석합니다.

**현재 상태:** 두 시스템이 **동일한 WebSocket 서버**를 사용함

---

## 2. WebSocket 서버 구조

### 2.1 핵심 컴포넌트

| 컴포넌트 | 파일 | 설명 |
|----------|------|------|
| `ConnectionManager` | `server.py` | 연결 관리, 토픽 구독/구독취소 |
| `PriceUpdateBroadcaster` | `server.py` | 실시간 가격 브로드캐스트 (5초 간격) |
| `SignalBroadcaster` | `server.py` | VCP 시그널 브로드캐스트 |
| `HeartbeatManager` | `server.py` | Ping/Pong Keep-Alive (30초 간격) |
| `RedisSubscriber` | `server.py` | Redis Pub/Sub 리스너 (Celery → WS) |

### 2.2 WebSocket 엔드포인트

```python
# src/websocket/routes.py
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    subscribe: Optional[str] = Query(None),  # 콤마로 구분된 토픽
)
```

**지원 토픽:**
| 토픽 패턴 | 설명 | 사용 시스템 |
|-----------|------|-------------|
| `price:{ticker}` | 종목 실시간 가격 | 메인, 단타 공용 |
| `market-gate` | Market Gate 상태 | 메인 대시보드 |
| `signal:vcp` | VCP 시그널 업데이트 | 메인 대시보드 |
| `signal:daytrading` | 단타 시그널 업데이트 | 단타 추천 (미구현) |
| `market:kospi` | KOSPI 지수 | 메인 대시보드 |
| `market:kosdaq` | KOSDAQ 지수 | 메인 대시보드 |

---

## 3. 메시지 프로토콜

### 3.1 클라이언트 → 서버

| 메시지 타입 | 필드 | 설명 |
|-------------|------|------|
| `subscribe` | `topic` | 토픽 구독 |
| `unsubscribe` | `topic` | 토픽 구독 취소 |
| `ping` | - | 핑 전송 |
| `pong` | - | 퐁 응답 |

### 3.2 서버 → 클라이언트

| 메시지 타입 | 데이터 구조 | 설명 |
|-------------|-------------|------|
| `connected` | `{client_id, message}` | 연결 성공 |
| `subscribed` | `{topic, message}` | 구독 완료 |
| `unsubscribed` | `{topic, message}` | 구독 취소 완료 |
| `price_update` | `{ticker, data, timestamp}` | 가격 업데이트 |
| `market_gate_update` | `{status, level, kospi, ...}` | Market Gate 업데이트 |
| `signal_update` | `{signal_type, signals, count}` | 시그널 업데이트 |
| `ping` | `{timestamp}` | 서버 핑 |
| `pong` | - | 서버 퐁 |

---

## 4. 브로드캐스터 구현

### 4.1 PriceUpdateBroadcaster (가격)

```python
class PriceUpdateBroadcaster:
    DEFAULT_TICKERS = {
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "035420",  # NAVER
        # ... 기본 종목
    }

    async def _broadcast_loop(self):
        # 5초마다 가격 브로드캐스트
        while self._is_running:
            price_updates = await self._fetch_prices_from_kiwoom(tickers)
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
```

**데이터 소스 우선순위:**
1. Kiwoom REST API (실시간) - `USE_KIWOOM_REST=true`
2. DB 폴링 (fallback)

### 4.2 SignalBroadcaster (시그널)

```python
class SignalBroadcaster:
    async def broadcast_signal_update(
        self,
        signals: list,
        signal_type: str = "VCP"
    ):
        message = {
            "type": "signal_update",
            "data": {
                "signal_type": signal_type,
                "signals": signal_dicts,
                "count": len(signal_dicts),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
        topic = f"signal:{signal_type.lower()}"
        await connection_manager.broadcast(message, topic=topic)
```

---

## 5. 단타 추천을 위한 필요한 추가 사항

### 5.1 현재 구현 상태

| 구분 | 메인 대시보드 (VCP) | 단타 추천 (Daytrading) | 비고 |
|------|---------------------|----------------------|------|
| 토픽 구독 | `signal:vcp` ✅ | `signal:daytrading` ❌ | **미구현** |
| 브로드캐스터 | `SignalBroadcaster` ✅ | 없음 ❌ | **미구현** |
| 실시간 업데이트 | VCP 스캔 시 브로드캐스트 | 없음 ❌ | **미구현** |

### 5.2 필요한 백엔드 변경

#### 5.2.1 DaytradingSignal 브로드캐스트 추가

```python
# src/websocket/server.py에 추가

class DaytradingSignalBroadcaster:
    """
    단타 시그널 실시간 브로드캐스터
    """

    def __init__(self):
        self._running = False

    async def broadcast_signal_update(self, signals: list) -> None:
        """단타 시그널 업데이트 브로드캐스트"""
        signal_dicts = []
        for sig in signals:
            if hasattr(sig, "to_dict"):
                signal_dicts.append(sig.to_dict())
            elif isinstance(sig, dict):
                signal_dicts.append(sig)

        message = {
            "type": "signal_update",
            "data": {
                "signal_type": "DAYTRADING",  # 단타 고유 타입
                "signals": signal_dicts,
                "count": len(signal_dicts),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        # signal:daytrading 토픽으로 브로드캐스트
        await connection_manager.broadcast(message, topic="signal:daytrading")

# 전역 인스턴스
daytrading_signal_broadcaster = DaytradingSignalBroadcaster()
```

#### 5.2.2 Daytrading Scanner 서비스와 연동

```python
# services/daytrading_scanner/main.py에 추가

from src.websocket.server import daytrading_signal_broadcaster

@router.post("/scan")
async def scan_market(request: DaytradingScanRequest):
    # 시장 스캔 실행
    signals = await daytrading_scorer.scan_market(request.market, request.limit)

    # WebSocket으로 브로드캐스트
    await daytrading_signal_broadcaster.broadcast_signal_update(signals)

    # 기존 캐시 무효화
    await _invalidate_daytrading_cache()

    return {"signals": signals, "count": len(signals)}
```

---

## 6. 프론트엔드-백엔드 연동 확인

### 6.1 메인 대시보드 (정상 작동)

```typescript
// 프론트엔드
export function useSignals() {
  const { connected, subscribe } = useWebSocket({...});

  useEffect(() => {
    if (connected) {
      subscribe("signal:vcp");  // ✅ 작동
    }
  }, [connected, subscribe]);

  // 메시지 수신
  client.onMessage((message: WSMessage) => {
    if (message.type === "signal_update") {
      setSignals(signalMsg.data.signals);
    }
  });
}
```

```python
# 백엔드
await signal_broadcaster.broadcast_signal_update(vcp_signals, signal_type="VCP")
# topic = "signal:vcp" ✅
```

### 6.2 단타 추천 (미구현)

```typescript
// 프론트엔드
export function useDaytradingSignals() {
  useEffect(() => {
    if (connected) {
      subscribe("signal:daytrading");  // ❌ 백엔드에서 방송 없음
    }
  }, [connected, subscribe]);
}
```

```python
# 백엔드 - 해당 코드 없음 ❌
# await daytrading_signal_broadcaster.broadcast_signal_update(...)
```

---

## 7. 문제점 및 개선 방안

### 7.1 현재 문제점

1. **단타 시그널 브로드캐스터 미구현**
   - Daytrading Scanner가 시그널을 생성해도 WebSocket으로 전송되지 않음
   - 프론트엔드는 API 폴링으로만 데이터를 가져옴

2. **토픽 구조 불일치**
   - VCP: `signal:vcp` ✅
   - Daytrading: `signal:daytrading` (프론트엔드만 정의, 백엔드 미구현)

3. **데이터 구조 차이**
   - VCP 시그널: `Signal` 모델 기반
   - Daytrading 시그널: `DaytradingSignal` 모델 기반 (체크리스트 포함)

### 7.2 개선 방안

#### 7.2.1 DaytradingSignalBroadcaster 구현

**파일:** `src/websocket/server.py`

```python
class DaytradingSignalBroadcaster:
    """단타 시그널 실시간 브로드캐스터"""

    async def broadcast_signal_update(self, signals: list) -> None:
        signal_dicts = [_convert_to_dict(s) for s in signals]

        message = {
            "type": "signal_update",
            "data": {
                "signal_type": "DAYTRADING",
                "signals": signal_dicts,
                "count": len(signal_dicts),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        await connection_manager.broadcast(message, topic="signal:daytrading")

daytrading_signal_broadcaster = DaytradingSignalBroadcaster()
```

#### 7.2.2 Daytrading Scanner 연동

**파일:** `services/daytrading_scanner/main.py`

```python
from src.websocket.server import daytrading_signal_broadcaster

@router.post("/scan")
async def scan_market(request: DaytradingScanRequest):
    signals = await scanner.scan(request.market, request.limit)

    # WebSocket 브로드캐스트
    await daytrading_signal_broadcaster.broadcast_signal_update(signals)

    return {"success": True, "signals": signals}
```

---

## 8. 통합 일정

### Phase 1: 브로드캐스터 구현 (긴급)

- [ ] `DaytradingSignalBroadcaster` 클래스 구현
- [ ] Daytrading Scanner 서비스에 브로드캐스트 호출 추가

**작업량:** 2-3시간

### Phase 2: 테스트

- [ ] WebSocket 메시지 수신 확인
- [ ] 프론트엔드 실시간 업데이트 확인

**작업량:** 1-2시간

---

## 9. 결론

메인 대시보드는 WebSocket 실시간 업데이트가 정상 작동하지만, 단타 추천은 백엔드 브로드캐스터가 미구현되어 API 폴링에 의존하고 있습니다.

**필요 작업:**
1. `DaytradingSignalBroadcaster` 구현
2. Daytrading Scanner 스캔 완료 시 WebSocket 브로드캐스트 호출 추가
3. 통합 테스트

**총 작업량 예상:** 3-5시간
