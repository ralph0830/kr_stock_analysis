# custom-recommendation 페이지 백엔드/연동 분석 보고서

**분석 일자:** 2026-02-06  
**대상 URL:** https://stock.ralphpark.com/custom-recommendation  
**분석 범위:** API Gateway, Daytrading Scanner, WebSocket, 실시간 가격 브로드캐스트

---

## 1. 요약

custom-recommendation 페이지의 백엔드는 **API Gateway**와 **Daytrading Scanner** 마이크로서비스로 구성되어 있습니다.

**핵심 서비스:**
- **API Gateway** (Port 5111): 라우팅 및 프록시
- **Daytrading Scanner** (Port 5115): 단타 시그널 생성 및 DB 조회
- **WebSocket Manager** (API Gateway 내): 실시간 메시징
- **DaytradingPriceBroadcaster**: 실시간 가격 브로드캐스트 (실행 중)

---

## 2. 아키텍처

### 2.1 서비스 구성

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  (Next.js: https://stock.ralphpark.com)                        │
│  - useRealtimePrices Hook 사용                                 │
│  - price:005930, price:000270 구독                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (5111)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ /api/daytrading/signals → Daytrading Scanner (5115)     │  │
│  │ /api/daytrading/scan   → Daytrading Scanner (5115)      │  │
│  │ /ws (WebSocket)          → WebSocket Manager             │  │
│  │ daytrading_price_broadcaster (실행 중)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Daytrading Scanner (5115)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ GET /api/daytrading/signals                              │  │
│  │   - DB에서 시그널 조회 (daytrading_signals 테이블)       │  │
│  │   - 필터링 (min_score, market, limit)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL DB                                │
│  - daytrading_signals 테이블                                   │
│  - stocks 테이블                                               │
│  - daily_prices 테이블 (TimescaleDB)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 실시간 가격 브로드캐스트 분석

### 3.1 DaytradingPriceBroadcaster

**파일:** `/services/daytrading_scanner/price_broadcaster.py`

**구현 상태:**
- 클래스 구현: ✅ 완료
- API Gateway에서 시작: ✅ 완료 (라인 296-303)
- ConnectionManager 설정: ✅ 완료
- 브로드캐스트 루프: ✅ 완료 (5초 간격)

**코드:**
```python
# /services/api_gateway/main.py:296-303
print("📡 Starting Daytrading Price Broadcaster...")
from services.daytrading_scanner.price_broadcaster import get_daytrading_price_broadcaster
global daytrading_price_broadcaster
daytrading_price_broadcaster = get_daytrading_price_broadcaster()
daytrading_price_broadcaster.set_connection_manager(connection_manager)
await daytrading_price_broadcaster.start()
print("✅ Daytrading Price Broadcaster started")
```

### 3.2 종목 추가 로직 (미구현 ❌)

**문제점:**
- `DaytradingPriceBroadcaster`는 실행 중이지만
- **종목을 추가하는 코드가 없습니다**

**VCP 시그널과의 비교:**
```python
# /services/api_gateway/main.py:882-886 (VCP 시그널)
# VCP 시그널 종목들을 price_broadcaster에 추가
if WEBSOCKET_AVAILABLE and price_broadcaster and signal_tickers:
    for ticker in signal_tickers:
        price_broadcaster.add_ticker(ticker)
    logger.info(f"Added VCP signal tickers to price_broadcaster: {signal_tickers}")
```

**Daytrading 시그널에는 해당 코드가 없습니다.**

### 3.3 브로드캐스트 함수

**파일:** `/services/daytrading_scanner/broadcaster.py`

```python
async def broadcast_price_update(
    ticker: str,
    price_data: Dict[str, Any],
    connection_manager,
) -> None:
    """종목 가격 업데이트 브로드캐스트"""
    
    message = {
        "type": "price_update",
        "ticker": ticker,
        "data": {
            "price": price_data.get("price"),
            "change": price_data.get("change"),
            "change_rate": price_data.get("change_rate"),
            "volume": price_data.get("volume", 0)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # 브로드캐스트 (price:{ticker} 토픽)
    topic = f"price:{ticker}"
    await connection_manager.broadcast(message, topic=topic)
```

---

## 4. API 응답 분석

### 4.1 GET /api/daytrading/signals

**실제 응답 예시:**
```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "total_score": 90,
        "grade": "S",
        "checks": [...],
        "signal_type": "STRONG_BUY",
        "entry_price": 75000,
        "target_price": 80000,
        "stop_loss": 72000,
        "reasons": ["거래량 폭증", "모멘텀 돌파", ...]
        // current_price 필드 없음!
      }
    ]
  }
}
```

### 4.2 Pydantic 모델 (필드 누락)

**파일:** `/services/daytrading_scanner/models/daytrading.py:99-111`

```python
class DaytradingSignal(BaseModel):
    ticker: str
    name: str
    market: str = "KOSPI"
    score: int
    grade: str = "C"
    checks: List[DaytradingCheck] = []
    signal_type: str = "WATCH"
    entry_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None
    reasons: List[str] = []
    # current_price 필드 없음!
```

---

## 5. 문제점 및 해결 방안

### 5.1 문제점 요약

| 항목 | 상태 | 설명 |
|------|------|------|
| 브로드캐스터 실행 | ✅ | API Gateway 시작 시 실행됨 |
| 종목 추가 로직 | ❌ | **누락됨** - 브로드캐스터에 종목이 추가되지 않음 |
| API 응답 가격 | ❌ | **필드 없음** - `current_price` 필드 누락 |
| 가격 데이터 조회 | ⚠️ | DB 조회 로직이 브로드캐스터에만 있음 |

### 5.2 해결 방안

**해결 1: API Gateway에서 종목 추가**

```python
# /services/api_gateway/routes/daytrading.py

@router.get("/signals")
async def get_daytrading_signals(...):
    # ... 기존 코드 ...
    
    # Daytrading 시그널 종목들을 daytrading_price_broadcaster에 추가
    from services.api_gateway.main import daytrading_price_broadcaster
    
    signal_tickers = [s["ticker"] for s in signals_data]
    if daytrading_price_broadcaster and signal_tickers:
        for ticker in signal_tickers:
            daytrading_price_broadcaster.add_ticker(ticker)
        logger.info(f"Added daytrading signal tickers to price broadcaster: {signal_tickers}")
```

**해결 2: Pydantic 모델에 필드 추가**

```python
# /services/daytrading_scanner/models/daytrading.py

class DaytradingSignal(BaseModel):
    # ... 기존 필드 ...
    current_price: Optional[int] = None  # 추가
```

**해결 3: DB에서 가격 조회**

```python
# /services/daytrading_scanner/main.py

# DB에서 최신 가격 조회
from src.repositories.stock_repository import StockRepository

with get_db_session_sync() as db:
    stock_repo = StockRepository(db)
    for db_signal in db_signals:
        latest_price = stock_repo.get_latest_price(db_signal.ticker)
        
        signals.append(DaytradingSignal(
            # ...
            current_price=latest_price.close_price if latest_price else None,
        ))
```

---

## 6. 결론

| 구성 요소 | 상태 | 비고 |
|----------|------|------|
| 브로드캐스터 구현 | ✅ 완료 | `DaytradingPriceBroadcaster` 구현됨 |
| 브로드캐스터 실행 | ✅ 완료 | API Gateway 시작 시 실행됨 |
| 종목 추가 로직 | ❌ 미구현 | **필요** |
| API 응답 가격 | ❌ 미구현 | **필요** |

**최종 상태:**
- 백엔드 인프라는 완전히 준비됨
- 브로드캐스터가 실행 중이지만 종목이 추가되지 않아 가격 업데이트가 전송되지 않음
- **종목 추가 로직과 API 응답 필드만 추가하면 실시간 가격 연동 완료**

---

## 7. 참고 파일

| 파일 | 경로 |
|------|------|
| API Gateway 메인 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/main.py` |
| Daytrading 라우터 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/routes/daytrading.py` |
| 가격 브로드캐스터 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/price_broadcaster.py` |
| 브로드캐스터 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/broadcaster.py` |
| Daytrading Scanner | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/main.py` |
| Pydantic 모델 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/models/daytrading.py` |
