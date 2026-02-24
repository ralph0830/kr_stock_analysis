# custom-recommendation 페이지 실시간 가격 연동 검증 보고서

**분석 일자:** 2026-02-06 (인프라 재시작 후 재검증)
**대상 URL:** https://stock.ralphpark.com/custom-recommendation  
**분석 도구:** Playwright (headless browser)

---

## 1. 요약

custom-recommendation 페이지의 실시간 가격 연동을 **인프라 재시작 후 재검증**한 결과:
- **프론트엔드 코드**: 완전히 구현됨 ✅
- **WebSocket 연결**: 정상 작동 ✅
- **백엔드 브로드캐스터**: 코드는 구현되었으나 **실제 동작하지 않음** ⚠️
- **시그널 수신**: 프론트엔드에서 시그널을 수신하지 못함 (0개 표시) ❌

---

## 2. 검증 결과 (인프라 재시작 후)

### 2.1 프론트엔드 상태 (완료 ✅)

| 항목 | 상태 | 설명 |
|------|------|------|
| WebSocket 연결 | ✅ | `wss://stock.ralphpark.com/ws` 정상 연결 |
| `useDaytradingSignals` | ✅ | signal:daytrading 토픽 구독 시도 |
| `useRealtimePrices` Hook | ✅ | 페이지에서 사용 중 (라인 48-55) |
| UI 배지 표시 | ✅ | "시그널 실시간", "가격 실시간" 배지 표시됨 |
| 실시간 배지 표시 | ✅ | "가격 실시간" 배지 표시됨 |

**프론트엔드 구현 코드:**
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

### 2.2 백엔드 상태 (부분 완료 ⚠️)

| 항목 | 상태 | 설명 |
|------|------|------|
| `DaytradingPriceBroadcaster` | ⚠️ | 코드는 구현됨, 시작 로그 없음 |
| `broadcast_price_update()` | ✅ | 브로드캐스트 함수 구현됨 |
| 종목 추가 로직 | ⚠️ | 코드는 있으나 실행되지 않음 |
| `signal:daytrading` 브로드캐스트 | ❌ | **메시지 전송 안 됨** |

---

## 3. Playwright 캡처 로그 (인프라 재시작 후)

### 3.1 페이지 로드 시 로그

```
[log] [useWebSocket] Getting client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] Created new client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: disconnected → connecting
[log] [WebSocket] Connected to wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: connecting → connected
[log] [WebSocket] Ping timer started (interval: 30000 ms)
[log] [WebSocket] Client ID: 496ec6b3-9f75-4b51-9ed8-1907a6969bcb
[log] [useDaytradingSignals] Subscribing to signal:daytrading topic
[log] [useDaytradingSignals] Loaded initial signals: 0
```

**관찰:**
- WebSocket 연결 성공
- `signal:daytrading` 토픽 구독 시도
- **하지만 시그널 0개 표시** (`Loaded initial signals: 0`)
- **`[useRealtimePrices] Subscribing to price:005930` 로그 없음**

### 3.2 서버 로그 확인

```bash
# API Gateway 로그에서 DaytradingPriceBroadcaster 시작 로그 검색
docker compose logs api-gateway --tail 3000 | grep -E "Daytrading Price Broadcaster"
# 결과: 없음

# signal:daytrading 브로드캐스트 로그 검색
docker compose logs api-gateway --tail 500 | grep -E "signal:daytrading|Broadcasted.*daytrading"
# 결과: 없음
```

**관찰:**
- `DaytradingPriceBroadcaster` 시작 로그 없음
- `signal:daytrading` 토픽으로 메시지 전송 없음
- **Market Gate WebSocket Bridge는 정상 작동 중** (다른 종목 가격 브로드캐스트 있음)

---

## 4. 문제점 분석 (인프라 재시작 후)

### 4.1 핵심 문제: DaytradingPriceBroadcaster 시작 안 됨

**위치:** `/services/api_gateway/main.py:296-303`

**현상:**
- API Gateway 시작 시 `DaytradingPriceBroadcaster`를 시작하는 코드가 있음
- 하지만 서버 로그에 `"📡 Starting Daytrading Price Broadcaster..."` 메시지 없음
- `✅ Daytrading Price Broadcaster started` 메시지도 없음

**원인 추정:**
1. API Gateway가 비정상 종료 후 재시작될 때 DaytradingPriceBroadcaster가 시작되지 않음
2. 또는 WebSocket 연결 매니저 초기화 전에 브로드캐스터 시작을 시도하여 실패

### 4.2 문제 2: signal:daytrading 브로드캐스트 없음

**현상:**
- 프론트엔드에서 `signal:daytrading` 토픽을 구독
- 하지만 서버에서 해당 토픽으로 메시지를 전송하지 않음
- `broadcast_daytrading_signals()` 함수가 호출되지 않음

**원인:**
- Daytrading 시그널이 생성/업데이트될 때 `broadcast_daytrading_signals()`를 호출하는 코드가 없음
- VCP 시그널과 달리 Daytrading 시그널은 WebSocket으로 실시간 브로드캐스트하지 않음

### 4.3 문제 3: 프론트엔드에서 시그널 0개 표시

**현상:**
- API는 정상 응답 (`{"success":true, "data":{"signals":[...]}}`)
- 하지만 프론트엔드에서 `useDaytradingSignals`가 시그널을 수신하지 못함
- 페이지에 "총 0개 시그널"로 표시됨

**원인:**
- `useDaytradingSignals`는 WebSocket `signal:daytrading` 토픽에서만 시그널을 받음
- 초기 데이터는 API에서 직접 가져오지만, `wsSignals.length > 0 ? wsSignals : storeSignals` 로직에서 `wsSignals`가 0개라서 `storeSignals`를 사용해야 함
- 하지만 `storeSignals`도 비어있음 (초기 로드 실패)

---

## 5. 해결 방안

### 5.1 해결 1: DaytradingPriceBroadcaster 시작 확인

**파일:** `/services/api_gateway/main.py`

**확인 필요:**
```python
# startup 이벤트에서 DaytradingPriceBroadcaster 시작 부분 확인
# 라인 296-303
print("📡 Starting Daytrading Price Broadcaster...")
from services.daytrading_scanner.price_broadcaster import get_daytrading_price_broadcaster
global daytrading_price_broadcaster
daytrading_price_broadcaster = get_daytrading_price_broadcaster()
daytrading_price_broadcaster.set_connection_manager(connection_manager)
await daytrading_price_broadcaster.start()
print("✅ Daytrading Price Broadcaster started")
```

**수정 필요:**
- WebSocket 연결 매니저가 초기화된 후 브로드캐스터 시작 순서 보장
- 예외 처리 추가하여 시작 실패 시 로그 출력

### 5.2 해결 2: API Gateway 라우터에서 종목 추가 확인

**파일:** `/services/api_gateway/routes/daytrading.py`

**이미 구현됨 (라인 155-167):**
```python
# Daytrading 시그널 종목들을 daytrading_price_broadcaster에 추가
signal_tickers = [s.get("ticker") for s in signals_data if s.get("ticker")]
if signal_tickers:
    try:
        from services.api_gateway.main import daytrading_price_broadcaster
        if daytrading_price_broadcaster:
            for ticker in signal_tickers:
                daytrading_price_broadcaster.add_ticker(ticker)
            logger.info(f"Added daytrading signal tickers to price broadcaster: {signal_tickers}")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to add tickers to price broadcaster: {e}")
```

**확인 필요:**
- `daytrading_price_broadcaster`가 `None`인지 확인
- 로그 레벨 때문에 `logger.info()`가 출력되지 않는지 확인

### 5.3 해결 3: Daytrading 시그널 브로드캐스트 추가

**파일:** `/services/daytrading_scanner/main.py` 또는 `/services/api_gateway/routes/daytrading.py`

**추가 필요:**
```python
# 시그널 스캔 완료 후 WebSocket으로 브로드캐스트
from services.daytrading_scanner.broadcaster import broadcast_daytrading_signals

await broadcast_daytrading_signals(signals, connection_manager)
```

---

## 6. 결론

| 구성 요소 | 상태 | 비고 |
|----------|------|------|
| 프론트엔드 구현 | ✅ 완료 | `useRealtimePrices` Hook 사용 중 |
| WebSocket 연결 | ✅ 완료 | 연결 및 토픽 구독 정상 |
| 백엔드 브로드캐스터 코드 | ✅ 완료 | `DaytradingPriceBroadcaster` 구현됨 |
| 브로드캐스터 실행 | ❌ 미작동 | **시작 로그 없음** |
| 종목 추가 로직 | ⚠️ | 코드는 있으나 실행 안 됨 |
| 시그널 브로드캐스트 | ❌ 미구현 | `signal:daytrading` 메시지 없음 |

**최종 상태:**
- 프론트엔드는 100% 준비됨
- 백엔드 코드는 구현되어 있으나 **실제 실행되지 않음**
- **DaytradingPriceBroadcaster 시작 및 signal:daytrading 브로드캐스트 구현 필요**

---

## 7. 참고 파일

| 파일 | 경로 |
|------|------|
| 프론트엔드 페이지 | `/home/ralph/work/python/kr_stock_analysis/frontend/app/custom-recommendation/page.tsx` |
| 시그널 테이블 | `/home/ralph/work/python/kr_stock_analysis/frontend/components/DaytradingSignalTable.tsx` |
| WebSocket Hook | `/home/ralph/work/python/kr_stock_analysis/frontend/hooks/useWebSocket.ts` |
| 가격 브로드캐스터 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/price_broadcaster.py` |
| 브로드캐스터 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/broadcaster.py` |
| API Gateway 메인 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/main.py` |
| Daytrading 라우터 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/routes/daytrading.py` |
| Daytrading Scanner | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/main.py` |

---

## 8. 검증 일지

| 일자 | 검증 내용 | 결과 |
|------|----------|------|
| 2026-02-06 초기 | 프론트엔드 코드 검증 | ✅ 구현 완료 |
| 2026-02-06 초기 | 백엔드 브로드캐스터 코드 검증 | ✅ 구현 완료 |
| 2026-02-06 재시작 후 | 인프라 재시작 후 재검증 | ⚠️ 브로드캐스터 미작동 |
| 2026-02-06 12:44 | 서버 로그 확인 | ❌ 시작 로그 없음 |
| 2026-02-06 12:44 | signal:daytrading 브로드캐스트 확인 | ❌ 메시지 없음 |
