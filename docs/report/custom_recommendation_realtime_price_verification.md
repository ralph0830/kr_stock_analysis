# custom-recommendation 페이지 실시간 가격 연동 검증 보고서

**분석 일자:** 2026-02-06  
**대상 URL:** https://stock.ralphpark.com/custom-recommendation  
**분석 도구:** Playwright (headless browser)

---

## 1. 요약

custom-recommendation 페이지의 실시간 가격 연동을 검증한 결과, **프론트엔드 코드는 완전히 구현**되어 있으나 **백엔드에서 종목 추가 로직이 누락**되어 있어 실제 가격 업데이트가 수신되지 않는 상태입니다.

---

## 2. 검증 결과

### 2.1 프론트엔드 상태 (완료 ✅)

| 항목 | 상태 | 설명 |
|------|------|------|
| WebSocket 연결 | ✅ | `wss://stock.ralphpark.com/ws` 정상 연결 |
| 가격 토픽 구독 | ✅ | `price:005930`, `price:000270` 정상 구독 |
| `useRealtimePrices` Hook | ✅ | 페이지에서 사용 중 (라인 48-55) |
| UI에 가격 표시 | ✅ | 현재가, 등락률, 등락금액 표시됨 |
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
| `DaytradingPriceBroadcaster` | ✅ | 구현 완료, 시작됨 |
| `broadcast_price_update()` | ✅ | 브로드캐스트 함수 구현됨 |
| 종목 추가 로직 | ❌ | **누락됨** |
| API 응답에 `current_price` | ❌ | **필드 없음** |

---

## 3. 문제점 분석

### 3.1 문제 1: 종목이 브로드캐스터에 추가되지 않음

**위치:** `/services/api_gateway/main.py`

**현상:**
- `daytrading_price_broadcaster`는 시작되지만 (라인 296-303)
- **종목을 추가하는 코드가 없습니다**

**VCP 시그널과의 비교:**
```python
# /services/api_gateway/main.py:882-886 (VCP 시그널)
# VCP 시그널 종목들을 price_broadcaster에 추가 (실시간 가격 브로드캐스트용)
if WEBSOCKET_AVAILABLE and price_broadcaster and signal_tickers:
    for ticker in signal_tickers:
        price_broadcaster.add_ticker(ticker)
```

**Daytrading 시그널에는 해당 코드가 없습니다.**

### 3.2 문제 2: API 응답에 `current_price` 필드 없음

**위치:** `/services/daytrading_scanner/main.py:289-301`

**현상:**
```python
# GET /api/daytrading/signals 응답
signals.append(DaytradingSignal(
    ticker=db_signal.ticker,
    name=db_signal.name,
    # ...
    entry_price=db_signal.entry_price,  # 있음
    target_price=db_signal.target_price, # 있음
    # current_price 필드 없음!  <-- 문제
))
```

**Pydantic 모델 (`/services/daytrading_scanner/models/daytrading.py:99-111`):**
```python
class DaytradingSignal(BaseModel):
    ticker: str
    name: str
    # ...
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None
    # current_price 필드 없음!  <-- 문제
```

### 3.3 문제 3: 프론트엔드가 API 응답 가격을 표시

**위치:** `/frontend/components/DaytradingSignalTable.tsx:301-338`

**현상:**
- 프론트엔드는 `current_price` 필드가 없으면 `entry_price`를 표시하지 않습니다
- 대신 `realtimePrices`에서 가격을 가져오지만, 백엔드에서 브로드캐스트가 없으므로 **실시간 업데이트가 되지 않습니다**

---

## 4. Playwright 캡처 로그

```
[log] [useWebSocket] Getting client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] Created new client for: wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: disconnected → connecting
[log] [WebSocket] Connected to wss://stock.ralphpark.com/ws
[log] [WebSocket] State change: connecting → connected
[log] [WebSocket] Ping timer started (interval: 30000 ms)
[log] [WebSocket] Client ID: e248711d-e037-4c2f-9d2f-726ad171caea
[log] [useDaytradingSignals] Subscribing to signal:daytrading topic
[log] [useRealtimePrices] Subscribing to price:005930
[log] [useRealtimePrices] Subscribing to price:000270
```

**관찰:**
- WebSocket 연결 성공
- 토픽 구독 성공
- **하지만 가격 업데이트 메시지 수신 없음**

---

## 5. 해결 방안

### 5.1 해결 1: API Gateway에서 종목 추가

**파일:** `/services/api_gateway/routes/daytrading.py`

**변경:** `/api/daytrading/signals` 엔드포인트 응답 후 종목 추가

```python
# Daytrading 시그널 종목들을 daytrading_price_broadcaster에 추가
from services.api_gateway.main import daytrading_price_broadcaster

signal_tickers = [s["ticker"] for s in signals_data]
if daytrading_price_broadcaster and signal_tickers:
    for ticker in signal_tickers:
        daytrading_price_broadcaster.add_ticker(ticker)
    logger.info(f"Added daytrading signal tickers to price broadcaster: {signal_tickers}")
```

### 5.2 해결 2: Pydantic 모델에 `current_price` 추가

**파일:** `/services/daytrading_scanner/models/daytrading.py`

```python
class DaytradingSignal(BaseModel):
    ticker: str
    name: str
    # ...
    current_price: Optional[int] = None  # 추가
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None
```

### 5.3 해결 3: DB에서 가격 조회

**파일:** `/services/daytrading_scanner/main.py`

```python
# DB에서 최신 가격 조회
from src.repositories.stock_repository import StockRepository

with get_db_session_sync() as db:
    stock_repo = StockRepository(db)
    for db_signal in db_signals:
        # 최신 일봉에서 가격 조회
        latest_price = stock_repo.get_latest_price(db_signal.ticker)
        
        signals.append(DaytradingSignal(
            # ...
            current_price=latest_price.close_price if latest_price else None,
            # ...
        ))
```

---

## 6. 결론

| 구성 요소 | 상태 | 비고 |
|----------|------|------|
| 프론트엔드 구현 | ✅ 완료 | `useRealtimePrices` Hook 사용 중 |
| WebSocket 연결 | ✅ 완료 | 연결 및 토픽 구독 정상 |
| 백엔드 브로드캐스터 | ✅ 완료 | `DaytradingPriceBroadcaster` 구현됨 |
| 종목 추가 로직 | ❌ 미구현 | **필요** |
| API 응답 가격 | ❌ 미구현 | **필요** |

**최종 상태:**
- 프론트엔드는 100% 준비됨
- 백엔드는 브로드캐스터가 실행 중이지만 종목이 추가되지 않음
- **종목 추가 로직과 API 응답에 `current_price` 필드 추가만으로 실시간 가격 연동 완료 가능**

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
| Pydantic 모델 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/models/daytrading.py` |
