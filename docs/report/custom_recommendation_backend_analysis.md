# custom-recommendation 페이지 백엔드/연동 분석 보고서

**분석 일자:** 2026-02-06  
**대상 URL:** https://stock.ralphpark.com/custom-recommendation  
**분석 범위:** API Gateway, Daytrading Scanner, WebSocket

---

## 1. 요약

custom-recommendation 페이지의 백엔드는 **API Gateway**와 **Daytrading Scanner** 마이크로서비스로 구성되어 있습니다.

**핵심 서비스:**
- **API Gateway** (Port 5111): 라우팅 및 프록시
- **Daytrading Scanner** (Port 5115): 단타 시그널 생성 및 DB 조회
- **WebSocket Manager** (API Gateway 내): 실시간 메시징

---

## 2. 아키텍처

### 2.1 서비스 구성

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  (Next.js: https://stock.ralphpark.com)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (5111)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ /api/daytrading/signals → Daytrading Scanner (5115)     │  │
│  │ /api/daytrading/scan   → Daytrading Scanner (5115)      │  │
│  │ /api/daytrading/analyze → Daytrading Scanner (5115)     │  │
│  │ /ws (WebSocket)          → WebSocket Manager             │  │
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
│  │   - 점수 기반 정렬                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ POST /api/daytrading/scan                                │  │
│  │   - TODO: 현재 Mock 데이터 반환                          │  │
│  │   - Phase 4에서 실제 데이터 조회 구현 예정               │  │
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

### 2.2 라우팅 구성

**API Gateway 라우터** (`/services/api_gateway/routes/daytrading.py`)
```python
router = APIRouter(
    prefix="/api/daytrading",
    tags=["daytrading"],
)

@router.get("/signals")
async def get_daytrading_signals(
    min_score: int = 0,
    market: Optional[str] = None,
    limit: int = 50
)

@router.post("/scan")
async def scan_daytrading_market(request: dict)

@router.post("/analyze")
async def analyze_daytrading_stocks(request: dict)
```

**Daytrading Scanner 엔드포인트** (`/services/daytrading_scanner/main.py`)
```python
@app.get("/api/daytrading/signals")
async def get_signals(...)

@app.post("/api/daytrading/scan")
async def scan_market(request: ScanRequest)

@app.post("/api/daytrading/analyze")
async def analyze_stocks(request: AnalyzeRequest)
```

---

## 3. 데이터 소스 분석

### 3.1 GET /api/daytrading/signals

**데이터 소스:** PostgreSQL DB (`daytrading_signals` 테이블)

**쿼리 로직** (`/services/daytrading_scanner/main.py:199-224`)
```python
with get_db_session_sync() as db:
    repo = DaytradingSignalRepository(db)
    
    if min_score > 0 and market:
        db_signals = (
            db.query(repo.model)
            .filter_by(status="OPEN", market=market)
            .filter(repo.model.score >= min_score)
            .order_by(repo.model.score.desc())
            .limit(limit)
            .all()
        )
    elif min_score > 0:
        db_signals = repo.get_by_min_score(min_score, limit)
    elif market:
        db_signals = repo.get_by_market(market, limit)
    else:
        db_signals = repo.get_active_signals(limit)
```

**데이터 변환**
```python
# DB 모델 → API 모델 변환
for db_signal in db_signals:
    checks_list = []
    if db_signal.checks:
        for check_data in db_signal.checks:
            checks_list.append(DaytradingCheck(
                name=check_data.get("name", ""),
                status=check_data.get("status", "failed"),
                points=check_data.get("points", 0)
            ))
    
    # 점수 기반 signal_type 결정
    if db_signal.score >= 80:
        signal_type = "STRONG_BUY"
    elif db_signal.score >= 60:
        signal_type = "BUY"
    else:
        signal_type = "WATCH"
```

### 3.2 POST /api/daytrading/scan

**데이터 소스:** **현재 Mock 데이터**

**코드** (`/services/daytrading_scanner/main.py:137-162`)
```python
candidates = [
    CandidateDataWithScore(
        ticker="005930",
        name="삼성전자",
        price=75000,
        change_rate=2.5,
        volume=20000000,
        avg_volume=10000000,
        volume_ratio=2.0,
        score=90,
        grade="S"
    ),
    CandidateDataWithScore(
        ticker="000270",
        name="기아",
        price=120000,
        change_rate=1.8,
        volume=15000000,
        avg_volume=8000000,
        volume_ratio=1.88,
        score=75,
        grade="A"
    ),
]
```

**중요:** 시장 스캔 기능은 **아직 실제 데이터를 사용하지 않습니다**. 
- TODO 주석: `# TODO: Phase 4에서 실제 데이터 조회 구현`

### 3.3 캐싱 레이어

API Gateway에서 Redis 기반 캐싱 구현:

```python
# /services/api_gateway/routes/daytrading.py:43-46
async def _get_cache_key(min_score: int, market: Optional[str], limit: int, format: str = "list") -> str:
    market_part = market.lower() if market else "all"
    return f"daytrading:signals:{min_score}:{market_part}:{limit}:{format}"
```

- 캐시 TTL: 5분 (300초)
- 스캔 실행 후 캐시 무효화

---

## 4. WebSocket 연동 분석

### 4.1 WebSocket 엔드포인트

**URL:** `wss://stock.ralphpark.com/ws`  
**실제 포워딩:** `ws://api-gateway:5111/ws` → `ws://localhost:5111/ws`

### 4.2 토픽 구독

**프론트엔드 구독 토픽:**
- `signal:daytrading` - 단타 시그널 업데이트

**구독 로그 확인:**
```
[log] [useDaytradingSignals] Subscribing to signal:daytrading topic
```

### 4.3 WebSocket 메시지 포맷

**Signal Update Message**
```typescript
{
  type: "signal_update",
  data: {
    signals: IDaytradingSignal[],
    timestamp: string
  }
}
```

### 4.4 백엔드 브로드캐스트 구현 확인 필요

**발견된 사항:**
- 프론트엔드에서 `signal:daytrading` 토픽 구독은 정상 수행
- 하지만 백엔드에서 실제로 이 토픽으로 메시지를 브로드캐스트하는 코드를 확인하지 못함

**확인 필요한 파일:**
- `/services/api_gateway/websocket_manager.py` (또는 유사한 WebSocket 관리 모듈)

---

## 5. 점수 계산 로직 분석

### 5.1 7개 체크리스트

**파일:** `/services/daytrading_scanner/models/scoring.py`

| 체크리스트 | 점수 | 계산 함수 | 조건 |
|-----------|------|----------|------|
| 거래량 폭증 | 15점 | `calculate_volume_spike_score()` | 거래량 비율 2배 이상 |
| 모멘텀 돌파 | 15점 | `calculate_momentum_breakout_score()` | 신고가 갱신 또는 고가 +2% 돌파 |
| 박스권 탈출 | 15점 | `calculate_box_breakout_score()` | 박스 상단 돌파 |
| 5일선 위 | 15점 | `calculate_ma5_above_score()` | 현재가 > MA5 |
| 기관 매수 | 15점 | `calculate_institution_buy_score()` | 순매수 100억 원 이상 |
| 낙폭 과대 | 15점 | `calculate_oversold_bounce_score()` | 전일 음락 1%+ 당일 반등 |
| 섹터 모멘텀 | 15점 | `calculate_sector_momentum_score()` | 섹터 상위 20% |

### 5.2 등급 부여

```python
# /services/daytrading_scanner/models/scoring.py:339-357
def get_grade_from_score(total_score: int) -> str:
    if total_score >= 90:
        return "S"
    elif total_score >= 75:
        return "A"
    elif total_score >= 60:
        return "B"
    else:
        return "C"
```

---

## 6. API Gateway 캐싱 및 서비스 레지스트리

### 6.1 서비스 레지스트리

**파일:** `/services/api_gateway/service_registry.py`

```python
daytrading_url = os.getenv("DAYTRADING_SCANNER_URL", "http://localhost:5115")
self.register(ServiceInfo(
    name="daytrading-scanner",
    url=daytrading_url,
    health_check_url=f"{daytrading_url}/health"
))
```

### 6.2 헬스 체크

**시스템 헬스 엔드포인트** (`/services/api_gateway/routes/system.py:384-400`)
```python
daytrading_service = registry.get_service("daytrading-scanner")
if daytrading_service:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{daytrading_service['url']}/health")
        # Health Check 결과 반환
```

---

## 7. 환경 변수 설정

### 7.1 API Gateway

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DAYTRADING_SCANNER_URL` | `http://localhost:5115` | Daytrading Scanner URL |
| `REDIS_URL` | - | 캐싱을 위한 Redis URL |

### 7.2 Daytrading Scanner

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | - | PostgreSQL 연결 URL |

---

## 8. 문제점 및 개선사항

### 8.1 확인된 문제점

| 항목 | 문제 | 심각도 |
|------|------|--------|
| 시장 스캔 Mock 데이터 | 실제 데이터 대신 Mock 반환 | 🔴 높음 |
| WebSocket 브로드캐스트 | 시그널 업데이트 브로드캐스트 구현 미확인 | 🟡 중간 |
| 실시간 가격 연동 | WebSocket 가격 업데이트 미사용 | 🟡 중간 |

### 8.2 개선 제안

1. **시장 스캔 실제 데이터 구현**
   - 현재 Mock 데이터인 `/api/daytrading/scan` 엔드포인트
   - 실제 종목 스캔 로직 구현 필요 (Phase 4 예정)

2. **WebSocket 브로드캐스트 구현**
   - 시그널 생성/업데이트 시 `signal:daytrading` 토픽으로 브로드캐스트
   - 프론트엔드에서 실시간 시그널 업데이트 표시

3. **실시간 가격 연동**
   - 프론트엔드의 `useRealtimePrices` Hook 활용
   - 종목별 현재가 실시간 표시

---

## 9. 결론

custom-recommendation 페이지의 백엔드는 **기본적인 기능이 구현**되어 있습니다:

- **DB 조회:** ✅ PostgreSQL에서 시그널 정상 조회
- **API 라우팅:** ✅ API Gateway → Daytrading Scanner 포워딩 정상
- **캐싱:** ✅ Redis 기반 캐싱 구현됨
- **WebSocket 연결:** ✅ 연결 및 토픽 구독 정상

**단, 다음 기능은 추가 구현이 필요합니다:**
- 시장 스캔 실제 데이터 구현 (현재 Mock)
- WebSocket 시그널 브로드캐스트 (백엔드에서 전송 코드 확인 필요)
- 실시간 가격 연동 (프론트엔드 Hook 활용)

---

## 10. 참고 파일

| 파일 | 경로 |
|------|------|
| API Gateway 메인 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/main.py` |
| Daytrading 라우터 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/routes/daytrading.py` |
| Daytrading Scanner | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/main.py` |
| 점수 계산 로직 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/models/scoring.py` |
| 서비스 레지스트리 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/service_registry.py` |
| 시스템 헬스 체크 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/routes/system.py` |
