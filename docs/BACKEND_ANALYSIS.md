# 백엔드 분석 보고서

**분석 일자:** 2026-02-04
**분석 범위:** 전체 백엔드 (마이크로서비스, 코어 모듈, 웹소켓, 태스크)

---

## 1. 개요

### 1.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│                        Port: 5110                               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    API Gateway (FastAPI)                        │
│                    Port: 5111                                   │
│  ┌──────────────┬──────────────┬──────────────┬─────────────┐  │
│  │   Routes     │   WebSocket  │   Service    │   Metrics    │  │
│  │ (12 modules) │   (1060줄)   │   Registry   │  Middleware  │  │
│  └──────────────┴──────────────┴──────────────┴─────────────┘  │
└─────┬───────────────┬───────────────┬────────────────────────────┘
      │               │               │
      ▼               ▼               ▼
┌───────────┐  ┌───────────┐  ┌─────────────┐
│ VCP       │  │ Signal    │  │  Chatbot    │
│ Scanner   │  │ Engine    │  │  (Gemini)   │
│ Port:5112 │  │ Port:5113 │  │  Port:5114  │
└───────────┘  └───────────┘  └─────────────┘
```

### 1.2 코드 베이스 규모

| 구분 | 파일 수 | 총 라인 |
|------|---------|---------|
| 전체 백엔드 | 65+ | 29,160 |
| 핵심 서비스 (상위 5) | 5 | 5,748 |
| 테스트 | 40+ | 2,000+ |

### 1.3 상위 파일 크기 순위

| 파일 | 라인 수 | 비고 |
|------|---------|------|
| `services/api_gateway/main.py` | 1,863 | 단일 책임 위반 |
| `src/kiwoom/rest_api.py` | 1,430 | Kiwoom REST API |
| `src/websocket/server.py` | 1,060 | WebSocket 서버 |
| `src/kiwoom/websocket.py` | 787 | Kiwoom WebSocket |
| `src/collectors/news_collector.py` | 715 | 뉴스 수집기 |

---

## 2. 마이크로서비스별 분석

### 2.1 API Gateway (`services/api_gateway/main.py`)

**파일 크기:** 1,863줄
**포트:** 5111

#### 장점

- Lifespan 컨텍스트 매니저로 startup/shutdown 관리
- Service Registry 패턴으로 서비스 검색
- 선택적 import (Docker/로컬 유연성)
- 통합 예외 처리

#### 문제점

**1) main.py가 너무 큼 (1,863줄)**

```python
# services/api_gateway/main.py:140-356
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 200줄이 넘는 startup 로직
    # - Kiwoom WebSocket 연결
    # - Price Broadcaster 시작
    # - Signal Broadcaster 시작
    # - Heartbeat Manager 시작
    # - Redis Pub/Sub 시작
```

→ **개선:** `StartupManager` 클래스로 분리

**2) 하드코딩된 종목 코드**

```python
# services/api_gateway/main.py:239
default_tickers = ["005930", "000660", "035420", "005380", "028260", "000020"]
```

→ **개선:** 환경 변수 또는 DB에서 조회

**3) 프록시 패턴 중복**

```python
# services/api_gateway/main.py:756-824 (VCP Scanner)
# services/api_gateway/main.py:1054-1087 (Signal Engine)
# 동일한 프록시 패턴이 반복됨
async with httpx.AsyncClient() as client:
    response = await client.get(f"{service['url']}/...")
```

→ **개선:** 공통 `proxy_request()` 헬퍼 함수

#### 개선 제안

1. **라우팅 모듈화**: `services/api_gateway/main.py` → 500줄 이하로 축소
2. **Startup 관리자**: `src/lifecycle/startup_manager.py` 신설
3. **프록시 추상화**: `src/proxy/service_proxy.py` 신설

---

### 2.2 VCP Scanner (`services/vcp_scanner/`)

**파일 크기:** 548줄 (core)
**포트:** 5112

#### 문제점

**1) 유연한 import 패턴 과다 사용**

```python
# services/vcp_scanner/vcp_analyzer.py:20-43
try:
    from ralph_stock_lib.database.session import SessionLocal
except ImportError:
    try:
        from src.database.session import SessionLocal
    except ImportError:
        # 런타임 import...
```

→ Docker/로컬 호환성을 위하지만, **의존성 주입이 더 깔끔함**

**2) DB 세션 관리 불일치**

```python
# services/vcp_scanner/main.py:204
db = SessionLocal()
try:
    # ...
finally:
    db.close()
```

→ **개선:** Repository 패턴 또는 Dependency Injection 사용

**3) TODO 미구현**

```python
# services/vcp_scanner/main.py:285
# TODO: Database에서 저장된 시그널 조회
# 현재는 실시간 분석 결과 반환
```

→ DB 쿼리가 구현되지 않아 매번 실시간 분석 실행

#### 개선 제안

1. **의존성 주입 도입**: `VCPAnalyzer(session_factory)` 패턴
2. **캐싱 계층**: 스캔 결과 Redis 캐싱 (TTL: 1시간)
3. **DB 조회 구현**: `SignalRepository` 활용

---

### 2.3 Signal Engine (`services/signal_engine/`)

**파일 크기:** 512줄 (core)
**포트:** 5113

#### 문제점

**1) Mock 데이터 의존**

```python
# services/signal_engine/main.py:102-108
# TODO: Database에서 저장된 시그널 조회
# 현재는 mock 데이터 생성
mock_signals = []
for ticker, name in [("005930", "삼성전자"), ("000660", "SK하이닉스")]:
```

→ **프로덕션 준비 미완료**

**2) 실제 종목 스캔 미구현**

```python
# services/signal_engine/main.py:136
# TODO: 실제 종목 스캔 로직
# 현재는 mock 데이터
mock_stocks = [("005930", "삼성전자", 80000), ...]
```

→ **VCP Scanner와 동일한 패턴 필요**

#### 개선 제안

1. **StockRepository 연동**: 전체 종목 스캔 로직
2. **배치 처리**: Celery Task로 스캔 분산
3. **DB 저장 구현**: `save_signals_to_db()` 함수

---

### 2.4 Chatbot (`services/chatbot/`)

**파일 크기:** 626줄 (main)
**포트:** 5114

#### 장점

- RAG (Retrieval Augmented Generation) 패턴 구현
- Session Manager로 Redis 세션 관리
- Kiwoom 실시간 데이터 연동

#### 문제점

**1) 레거시 함수 남음**

```python
# services/chatbot/main.py:503-581
def _generate_rag_reply(...):
    # Phase 3 함수 - Phase 4에서 LLM으로 교체 예정이라 주석
    # 하지만 여전히 코드에 존재
```

→ **삭제 필요**

**2) 종목명 조회 누락**

```python
# services/chatbot/main.py:427
"name": rec.get("name", rec.get("ticker", ""))  # 이름이 없으면 티커 사용
```

→ StockRepository를 사용해 이름 조회 필요

---

## 3. 공통 모듈 분석

### 3.1 Database Layer

**파일:** `src/database/session.py`

#### 장점

- TimescaleDB 하이퍼테이블 활용 (daily_prices, institutional_flows)
- 적절한 인덱스 구성
- Repository 패턴 사용

#### 문제점

**1) 세션 관리 세 가지 패턴 혼재**

```python
# 방식 1: Dependency Injection (FastAPI)
async def endpoint(db: Session = Depends(get_db_session)):
    ...

# 방식 2: Context Manager (Celery/스크립트)
with get_db_session_sync() as db:
    ...

# 방식 3: 직접 사용 (VCP Scanner) ❌
db = SessionLocal()
```

→ **표준화 필요**

**2) Pool 설정 고정**

```python
# src/database/session.py:23-31
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

→ 환경 변수로 설정 가능하게 변경

### 3.2 WebSocket

**파일:** `src/websocket/server.py` (1,060줄)

#### 장점

- 토픽 기반 구독 시스템
- ELW 종목 코드 지원
- 하트비트 관리자

#### 문제점

**1) 디버그 print() 문 과다**

```python
# src/websocket/server.py:127-142
print(f"[BROADCAST] Topic={topic}, subscribers={len(recipients)}")
print(f"[BROADCAST] No topic, broadcasting to all...")
```

→ logger로 교체 필요

**2) 복잡한 구독 로직**

```python
# src/websocket/server.py:170-218
def subscribe(self, client_id: str, topic: str):
    # 50줄이 넘는 조건부 로직
    # - KiwoomWebSocketBridge에 추가
    # - PriceBroadcaster에 추가
    # - 유효성 검증
```

→ **개선:** Strategy 패턴으로 데이터 소스 분리

### 3.3 Repository 패턴

#### 문제점

**1) 일관성 없는 인터페이스**

```python
# StockRepository
def get_by_ticker(self, ticker: str) -> Optional[Stock]:

# SignalRepository
def get_by_ticker(self, ticker: str, limit: int = 50) -> List[Signal]:
```

→ **GenericRepository** 베이스 클래스 도입 고려

**2) N+1 쿼리 가능성**

```python
# stock_repository.py (예시)
for stock in stocks:
    prices = stock.daily_prices  # Lazy loading
```

→ Eager Loading (`selectinload`) 검토 필요

---

## 4. 코드 품질 이슈

### 4.1 TODO 목록 (총 13건)

| 위치 | TODO | 우선순위 |
|------|------|----------|
| `api_gateway/main.py:1211` | 전일 대비 등락률 계산 | 중 |
| `api_gateway/main.py:1212` | 전일 대비 등락률 계산 | 중 |
| `signal_engine/main.py:102` | DB에서 저장된 시그널 조회 | **상** |
| `signal_engine/main.py:113` | DB에서 조회 시 생성 날짜 사용 | **상** |
| `signal_engine/main.py:136` | 실제 종목 스캔 로직 | **상** |
| `signal_engine/main.py:150` | 백그라운드 태스크로 DB 저장 | **상** |
| `vcp_scanner/main.py:285` | DB에서 저장된 시그널 조회 | **상** |
| `vcp_scanner/main.py:292` | DB에서 조회 시 저장 시간 사용 | **상** |
| `vcp_scanner/main.py:356` | 종목명 조회 (DB 또는 외부 API) | 중 |
| `news_collector.py:323` | 다음 뉴스 크롤링 구현 | 하 |
| `news_collector.py:338` | 연합뉴스 RSS 구현 | 하 |

### 4.2 하드코딩된 값

**1) 마법의 상수**

```python
# services/api_gateway/main.py:239
default_tickers = ["005930", "000660", "035420", "005380", "028260", "000020"]

# services/vcp_scanner/vcp_analyzer.py
FOREIGN_WEIGHT = 0.4  # 외국인 가중치
INST_WEIGHT = 0.3     # 기관 가중치

# 여러 곳에서 하드코딩된 시간 설정
timeout=10.0
sleep(1.0)
```

→ **개선:** `constants.py` 또는 환경 변수로 이동

### 4.3 예외 처리

**1) 너무 광범위한 except**

```python
# 여러 곳에서 발견
except Exception as e:
    logger.error(f"...: {e}")
    # 계속 실행
```

→ **개선:** 구체적 예외 타입 지정

---

## 5. 성능 이슈

### 5.1 잠재적 N+1 쿼리

```python
# services/api_gateway/main.py:1177-1215
# 종목 상세 조회 시 DailyPrice를 별도 쿼리
stock = stock_repo.get_by_ticker(ticker)  # Query 1
latest_price = db.execute(...)             # Query 2
```

→ **개선:** `joinedload()` 또는 별도 API 엔드포인트

### 5.2 캐싱 부재

| 데이터 | 현재 상태 | 제안 |
|--------|----------|------|
| VCP 스캔 결과 | 매번 실시간 계산 | Redis 캐시 (TTL: 1h) |
| 종목 기본 정보 | 매번 DB 조회 | Redis 캐시 (TTL: 24h) |
| Market Gate | 매번 DB 조회 | Redis 캐시 (TTL: 5min) |
| Kiwoom REST API | 매번 API 호출 | Redis 캐시 (TTL: 30s) |

### 5.3 동기 I/O

```python
# tasks/market_tasks.py:109-200
# Naver Finance API 호출이 동기 requests 사용
response = requests.get(kospi_url, headers=headers, timeout=10)
```

→ **개선:** `httpx.AsyncClient` 사용

---

## 6. 보안 이슈

### 6.1 환경 변수 관리

- ✅ `.env` 파일 사용 (gitignore 됨)
- ⚠️ 하드코딩된 기본값 존재

```python
# src/database/session.py:17-20
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/ralph_stock"  # 기본값 있음
)
```

### 6.2 API 키 노출 위험

```python
# services/chatbot/main.py:66-76
# GEMINI_API_KEY가 없으면 경고만 하고 계속 실행
if not gemini_key:
    logger.error("❌ GEMINI_API_KEY가 설정되지 않았습니다!")
    # 하지만 서비스는 계속 시작됨
```

→ **개선:** startup 실패 조건 추가

### 6.3 CORS 설정

```python
# services/api_gateway/main.py:450-467
allow_origins=[
    "http://localhost:5110",
    "https://ralphpark.com",
    ...
]
```

→ ✅ 양호 (특정 origin만 허용)

---

## 7. 우선순위별 개선 제안

### 🔴 P0 (즉시 개선)

| 항목 | 이유 | 예상 시간 |
|------|------|----------|
| Signal Engine DB 저장 구현 | 프로덕션 사용 불가 | 4시간 |
| VCP Scanner DB 조회 구현 | 불필요한 재계산 | 3시간 |
| 세션 관리 표준화 | 일관성 없음 | 2시간 |

### 🟡 P1 (주요 개선)

| 항목 | 이유 | 예상 시간 |
|------|------|----------|
| API Gateway 모듈 분리 | 유지보수 어려움 | 6시간 |
| Redis 캐싱 도입 | 성능 향상 | 4시간 |
| 하드코딩 값 환경변수화 | 설정 유연성 | 2시간 |
| print() → logger 교체 | 운영 환경 적합성 | 1시간 |

### 🟢 P2 (점진적 개선)

| 항목 | 이유 | 예상 시간 |
|------|------|----------|
| Generic Repository 도입 | 코드 중복 감소 | 4시간 |
| N+1 쿼리 해결 | 쿼리 성능 | 3시간 |
| 동기 I/O → 비동기 I/O | 응답 속도 | 4시간 |
| 테스트 커버리지 80%+ | 안정성 | 8시간 |

---

## 8. 리팩토링 로드맵

### Phase 1: 안정화 (1주)

```
Week 1:
├── Signal Engine DB 저장 구현
├── VCP Scanner DB 조회 구현
├── 세션 관리 표준화
└── 환경 변수 설정 재정비
```

### Phase 2: 성능 (1주)

```
Week 2:
├── Redis 캐싱 계층 도입
├── N+1 쿼리 해결
├── 동기 I/O → 비동기 I/O
└── 프록시 패턴 추상화
```

### Phase 3: 구조 개선 (2주)

```
Week 3-4:
├── API Gateway 모듈 분리
├── Generic Repository 도입
├── WebSocket 로직 정리
└── StartupManager 분리
```

### Phase 4: 품질 (1주)

```
Week 5:
├── print() → logger 교체
├── 테스트 커버리지 80%+
├── CI/CD 통합 테스트
└── 문서화
```

---

## 9. 요약

### 강점

1. ✅ 마이크로서비스 아키텍처 잘 구현됨
2. ✅ WebSocket 실시간 데이터 처리 완성도 높음
3. ✅ TimescaleDB 활용으로 시계열 데이터 최적화
4. ✅ RAG 기반 챗봇 구현

### 약점

1. ❌ Signal Engine이 mock 데이터에 의존
2. ❌ DB 세션 관리 패턴 불일치
3. ❌ 캐싱 전략 부재
4. ❌ 일부 큰 파일 (1,863줄) 유지보수 어려움

### 향후 방향

1. **단기**: 프로덕션 준비 (DB 저장/조회 구현)
2. **중기**: 성능 최적화 (캐싱, 쿼리 튜닝)
3. **장기**: 아키텍처 정리 (모듈 분리, 표준화)

---

*분석 완료: 2026-02-04*
*분석자: Claude Code*
