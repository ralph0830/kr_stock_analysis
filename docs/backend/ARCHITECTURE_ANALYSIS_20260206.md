# Backend Architecture Analysis Report

**작성일**: 2026-02-06
**작성자**: Backend Architect Agent
**버전**: 1.0.0

---

## 목차

1. [개요](#1-개요)
2. [마이크로서비스 구조 분석](#2-마이크로서비스-구조-분석)
3. [Repository 패턴 분석](#3-repository-패턴-분석)
4. [데이터베이스 아키텍처](#4-데이터베이스-아키텍처)
5. [통신 패턴](#5-통신-패턴)
6. [현황 요약](#6-현황-요약)
7. [개선 필요 사항](#7-개선-필요-사항)
8. [우선순위별 실행 계획](#8-우선순위별-실행-계획)

---

## 1. 개요

### 1.1 시스템 개요

Ralph Stock Analysis System은 **FastAPI 기반 마이크로서비스 아키텍처**로 구현된 한국 주식 분석 플랫폼입니다.

**주요 특징:**
- **마이크로서비스**: 5개 독립 서비스 (API Gateway, VCP Scanner, Signal Engine, Chatbot, Daytrading Scanner)
- **데이터베이스**: PostgreSQL + TimescaleDB (시계열 데이터 최적화)
- **메시징**: Redis Pub/Sub + Celery (백그라운드 태스크)
- **실시간 통신**: WebSocket (실시간 가격, 시그널 업데이트)

### 1.2 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| **API Framework** | FastAPI | Latest |
| **ORM** | SQLAlchemy | 2.0+ |
| **Database** | PostgreSQL + TimescaleDB | 15+ |
| **Cache/Message Broker** | Redis | 7+ |
| **Task Queue** | Celery | 5+ |
| **Real-time** | WebSocket | - |
| **Python Version** | Python | 3.12+ |

---

## 2. 마이크로서비스 구조 분석

### 2.1 서비스 목록

| 서비스 | 포트 | 책임 | 상태 |
|--------|------|------|------|
| **API Gateway** | 5111 | 모든 요청의 단일 진입점, 라우팅, CORS | ✅ 운영중 |
| **VCP Scanner** | 5112 | 볼린저밴드 수축 패턴 탐지 | ✅ 운영중 |
| **Signal Engine** | 5113 | 종가베팅 V2 시그널 생성 (12점 스코어링) | ✅ 운영중 |
| **Chatbot** | 5114 | AI 챗봇 (Gemini + RAG) | ✅ 운영중 |
| **Daytrading Scanner** | 5115 | 단타 매수 신호 스캔 | ✅ 운영중 |

### 2.2 서비스 상세 분석

#### 2.2.1 API Gateway (Port 5111)

**파일**: `services/api_gateway/main.py`

**책임:**
- CORS 처리
- 요청 라우팅 (프록시 패턴)
- WebSocket 엔드포인트 (`/ws`)
- 인증/인가 (예정)
- 메트릭 수집 (`/metrics`)

**라우팅 구조:**
```python
# 프록시 패턴: VCP Scanner → API Gateway
@app.get("/api/kr/signals")
async def get_kr_signals():
    # http://localhost:5112/signals로 프록시
    pass

# 직접 DB 조회: Market Gate
@app.get("/api/kr/market-gate")
async def get_kr_market_gate():
    # DB 직접 조회
    pass
```

**의존성:**
- `service_registry`: 서비스 디스커버리
- `httpx`: 비동기 HTTP 클라이언트
- `websocket.server`: WebSocket 연결 관리

**문제점:**
1. **단일 파일 과도함**: 2,050줄 → 여러 파일로 분리 필요
2. **레거시 호환 코드**: Flask 라우팅 호환용 중복 엔드포인트
3. **직접 DB 조회**: 일부 엔드포인트에서 Repository 패턴 미사용

#### 2.2.2 VCP Scanner (Port 5112)

**파일**: `services/vcp_scanner/main.py`

**책임:**
- VCP 패턴 탐지
- SmartMoney 수급 분석 (외국인/기관)
- DB 저장 (자동 갱신)
- WebSocket 브로드캐스트

**엔드포인트:**
```python
GET  /signals              # 활성 VCP 시그널 조회
POST /scan                 # VCP 패턴 스캔 실행
GET  /analyze/{ticker}     # 단일 종목 VCP 분석
GET  /health               # 헬스 체크
```

**분석기 구조:**
```python
class VCPAnalyzer:
    async def scan_market(market, top_n, min_score):
        # 1. 종목 스캔
        # 2. VCP 점수 계산
        # 3. SmartMoney 점수 계산
        # 4. 종합 점수 산출
        pass
```

**문제점:**
1. **Import 플렉시빌리티**: Docker/로컬 실행을 위한 복잡한 import 로직
2. **DB 세션 관리**: `get_db_session_sync()` 사용 시 혼재

#### 2.2.3 Signal Engine (Port 5113)

**파일**: `services/signal_engine/main.py`

**책임:**
- 종가베팅 V2 시그널 생성
- 12점 스코어링 시스템
- 등급 산출 (S/A/B/C)

**스코어링 구조:**
```python
ScoreDetail:
- news: 3점        # 뉴스 감성 분석
- volume: 3점      # 거래대금 급증
- chart: 2점       # 차트 패턴
- candle: 1점      # 캔들 패턴
- period: 1점      # 기간 조정
- flow: 2점        # 수급 흐름
---
총점: 0-12점
등급: S(11-12), A(9-10), B(7-8), C(6이하)
```

**문제점:**
1. **직접 DB 접근**: Repository 패턴 미사용
2. **하드코딩된 로직**: 일부 매직 넘버 존재

#### 2.2.4 Daytrading Scanner (Port 5115)

**파일**: `services/daytrading_scanner/main.py`

**책임:**
- 장중 단타 매수 신호 스캔
- 7개 체크리스트 점수 (총 105점)
- 실시간 가격 연동

**체크리스트:**
1. 거래량 폭증 (15점)
2. 모멘텀 돌파 (15점)
3. 박스권 탈출 (15점)
4. 5일선 위 (15점)
5. 기관 매수 (15점)
6. 낙폭 과대 (15점)
7. 섹터 모멘텀 (15점)

**문제점:**
1. **복잡한 점수 로직**: `scoring.py` 500+ 줄
2. **실시간 가격 의존**: Kiwoom REST API 연동 복잡

---

## 3. Repository 패턴 분석

### 3.1 구조

```
src/repositories/
├── __init__.py
├── base.py                      # BaseRepository (Generic)
├── stock_repository.py          # StockRepository
├── signal_repository.py         # SignalRepository
├── daily_price_repository.py    # DailyPriceRepository
├── vcp_signal_repository.py     # VCPSignalRepository
├── daytrading_signal_repository.py
├── market_repository.py         # MarketRepository
├── performance_repository.py    # PerformanceRepository
├── backtest_repository.py       # BacktestRepository
└── ai_analysis_repository.py    # AIAnalysisRepository
```

### 3.2 BaseRepository

**파일**: `src/repositories/base.py`

```python
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    # CRUD 기본 메서드
    def create(self, **kwargs) -> ModelType
    def get_by_id(self, id: int) -> Optional[ModelType]
    def get_all(self, skip, limit, **filters) -> List[ModelType]
    def update(self, id, **kwargs) -> Optional[ModelType]
    def delete(self, id) -> bool
    def count(self, **filters) -> int
    def exists(self, **filters) -> bool
```

**장점:**
- **Generic 타입**: 타입 안전성 확보
- **공통 CRUD**: 코드 중복 최소화
- **필터 지원**: 동적 쿼리 빌더

### 3.3 StockRepository

**파일**: `src/repositories/stock_repository.py`

**주요 메서드:**
```python
class StockRepository(BaseRepository[Stock]):
    def get_by_ticker(self, ticker: str) -> Optional[Stock]
    def list_all(self, market, sector, limit) -> List[Stock]
    def search(self, keyword, limit) -> List[Stock]
    def create_if_not_exists(self, **kwargs) -> Stock
    def get_institutional_flow(self, ticker, days) -> List[InstitutionalFlow]
```

**사용 예:**
```python
# FastAPI Dependency Injection
@app.get("/api/kr/stocks/{ticker}")
async def get_stock_detail(ticker: str, db: Session = Depends(get_db_session)):
    stock_repo = StockRepository(db)
    stock = stock_repo.get_by_ticker(ticker)
    return stock

# Celery Task (동기 세션)
@celery_app.task
def update_stock_market_cap():
    with get_db_session_sync() as db:
        stock_repo = StockRepository(db)
        stocks = stock_repo.list_all()
        # ...
```

### 3.4 문제점

1. **일관성 없는 사용**:
   - 일부 서비스에서 Repository 패턴 미사용 (Signal Engine)
   - 직접 SQLAlchemy 쿼리 사용

2. **세션 관리 혼재**:
   - `get_db_session()` (FastAPI DI)
   - `get_db_session_sync()` (Celery)
   - 직접 `SessionLocal()` 호출

3. **트랜잭션 처리 부족**:
   - 명시적 트랜잭션 경계 부재
   - 롤백 로직 불명확

---

## 4. 데이터베이스 아키텍처

### 4.1 스키마 구조

```
PostgreSQL (Port: 5433)
├── stocks                    # 종목 기본 정보
├── signals                   # VCP/종가베팅 시그널
├── daily_prices              # 일봉 데이터 (TimescaleDB)
├── institutional_flows       # 기관 수급 (TimescaleDB)
├── market_status             # Market Gate 상태
├── daytrading_signals        # 단타 매수 신호
├── ai_analyses               # AI 분석 결과
└── backtest_results          # 백테스트 결과
```

### 4.2 TimescaleDB 하이퍼테이블

**시계열 데이터 최적화:**
```sql
-- 일봉 데이터
SELECT create_hypertable('daily_prices', 'date', if_not_exists => TRUE);

-- 기관 수급 데이터
SELECT create_hypertable('institutional_flows', 'date', if_not_exists => TRUE);
```

**장점:**
- 파티셔닝 자동화 (날짜 기반)
- 쿼리 성능 최적화 (시계열 함수)
- 압축 자동 지원

### 4.3 세션 관리

**파일**: `src/database/session.py`

```python
# Engine 설정
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # 커넥션 유효성 검사
    future=True,         # SQLAlchemy 2.0
)

# FastAPI 용 (Dependency Injection)
def get_db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Celery 용 (Context Manager)
def get_db_session_sync():
    @contextmanager
    def _session_context():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    return _session_context()
```

**커넥션 풀 설정:**
- `pool_size=20`: 기본 커넥션 수
- `max_overflow=10`: 최대 추가 커넥션
- `pool_pre_ping=True`: 유효성 검사 (MySQL 연결 끊김 방지)

---

## 5. 통신 패턴

### 5.1 REST API (동기)

**프록시 패턴:**
```
Frontend → API Gateway → VCP Scanner
                     → Signal Engine
                     → Chatbot
```

**장점:**
- 서비스 디커플링
- 독립 배포 가능
- 기술 스택 유연성

**단점:**
- 네트워크 지연
- 에러 전파 복잡

### 5.2 WebSocket (비동기)

**실시간 브로드캐스트:**
```python
# 가격 업데이트
await connection_manager.broadcast({
    "type": "price_update",
    "ticker": "005930",
    "data": {"price": 82400, "change": +300}
}, topic=f"price:{ticker}")

# 시그널 업데이트
await signal_broadcaster.broadcast_signal_update(
    results, signal_type="VCP"
)
```

**토픽 기반 구독:**
- `price:{ticker}`: 종목별 가격
- `market:{name}`: 지수 (KOSPI/KOSDAQ)
- `signals`: VCP/종가베팅 시그널

### 5.3 Redis Pub/Sub (비동기)

**Celery → WebSocket:**
```python
# Celery Task에서 결과 발행
redis_client.publish("signals", json.dumps(signal_data))

# API Gateway에서 수신 → 브로드캐스트
async def redis_subscriber():
    sub = redis_client.pubsub()
    await sub.subscribe("signals")
    async for message in sub.listen():
        await connection_manager.broadcast(message["data"])
```

---

## 6. 현황 요약

### 6.1 장점

1. **명확한 서비스 분리**: 5개 마이크로서비스 독립 운영
2. **Repository 패턴**: 데이터 접근 계층 추상화
3. **TimescaleDB 활용**: 시계열 데이터 최적화
4. **실시간 통신**: WebSocket + Redis Pub/Sub
5. **컨테이너화**: Docker Compose로 쉬운 배포

### 6.2 단점

1. **코드 중복**: 각 서비스에 유사한 에러 처리, 로깅
2. **일관성 부족**: Repository 패턴 사용 불균형
3. **테스트 부족**: 통합 테스트 커버리지 낮음
4. **문서화 부족**: API 스펙, 아키텍처 문서 부족
5. **트랜잭션 관리**: 명시적 트랜잭션 경계 부족

---

## 7. 개선 필요 사항

### 7.1 아키텍처

#### [P1] API Gateway 리팩토링

**현재 문제:**
- `main.py` 2,050줄 (단일 파일)
- 레거시 호환 코드 중복

**개선안:**
```
services/api_gateway/
├── main.py                    # 앱 초기화 (200줄 이내)
├── routes/                    # 라우터 모듈화
│   ├── __init__.py
│   ├── signals.py
│   ├── stocks.py
│   ├── market.py
│   └── daytrading.py
├── dependencies.py            # DI 설정
├── middleware/                # 미들웨어 분리
│   ├── auth.py
│   ├── logging.py
│   └── error_handler.py
└── utils/                     # 유틸리티
    ├── response.py
    └── validation.py
```

#### [P1] 공통 라이브러리 추출

**현재 문제:**
- 각 서비스에 중복된 에러 처리, 로깅, 검증 로직

**개선안:**
```
src/shared/
├── exceptions.py              # 공통 예외
├── logging.py                 # 로깅 설정
├── validators.py              # Pydantic 검증기
├── response.py                # 표준 응답 모델
└── middleware.py              # 공통 미들웨어
```

### 7.2 데이터베이스

#### [P2] 트랜잭션 관리 개선

**현재 문제:**
- 명시적 트랜잭션 경계 부족
- 롤백 로직 불명확

**개선안:**
```python
# 데코레이터 기반 트랜잭션 관리
from functools import wraps

def transactional(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        db = kwargs.get('db')
        try:
            result = await func(*args, **kwargs)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
    return wrapper

# 사용
@transactional
async def create_signal(db: Session, signal_data: dict):
    # ...
    pass
```

#### [P2] 쿼리 최적화

**현재 문제:**
- N+1 쿼리 문제
- 인덱스 미사용

**개선안:**
```python
# Eager Loading
from sqlalchemy.orm import selectinload

query = select(Signal).options(
    selectinload(Signal.stock)  # JOIN 미리 로드
).where(Signal.status == "OPEN")
```

### 7.3 API 설계

#### [P2] 표준 응답 모델

**현재 문제:**
- 응답 형식 불일치

**개선안:**
```python
# 표준 응답 모델
class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# 사용
@app.get("/api/kr/signals")
async def get_signals():
    try:
        signals = await signal_service.get_active_signals()
        return APIResponse(success=True, data=signals)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INTERNAL_ERROR", message=str(e))
        )
```

### 7.4 테스트

#### [P3] 통합 테스트 강화

**현재 문제:**
- 단위 테스트만 존재
- API 통합 테스트 부족

**개선안:**
```python
# tests/integration/test_api_gateway.py
@pytest.mark.asyncio
async def test_get_signals_proxy():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/kr/signals?limit=10")

    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10
```

### 7.5 모니터링

#### [P3] 분산 추적 (Distributed Tracing)

**현재 문제:**
- 서비스 간 요청 추적 불가

**개선안:**
```python
# OpenTelemetry 통합
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@app.get("/api/kr/signals")
async def get_signals():
    with tracer.start_as_current_span("vcp_scanner_proxy"):
        # VCP Scanner 호출
        pass
```

---

## 8. 우선순위별 실행 계획

### Phase 1: 기반 강화 (1-2주)

**목표:** 코드 일관성 확보, 중복 제거

| 작업 | 우선순위 | 난이도 | 소요 시간 |
|------|----------|--------|-----------|
| API Gateway 리팩토링 | P1 | 중 | 3일 |
| 공통 라이브러리 추출 | P1 | 하 | 2일 |
| Repository 패턴 일관성 | P1 | 하 | 2일 |
| 문서화 (API 스펙) | P1 | 하 | 2일 |

**산출물:**
- 리팩토링된 API Gateway
- `src/shared/` 패키지
- `/docs/backend/api-specs/` API 문서

### Phase 2: 데이터 무결성 (1주)

**목표:** 트랜잭션 관리, 쿼리 최적화

| 작업 | 우선순위 | 난이도 | 소요 시간 |
|------|----------|--------|-----------|
| 트랜잭션 데코레이터 | P2 | 중 | 2일 |
| N+1 쿼리 해결 | P2 | 중 | 2일 |
| 인덱스 최적화 | P2 | 하 | 1일 |

**산출물:**
- 트랜잭션 관리 라이브러리
- 쿼리 최적화 보고서
- 인덱스 스크립트

### Phase 3: 테스트 및 모니터링 (1주)

**목표:** 테스트 커버리지, 분산 추적

| 작업 | 우선순위 | 난이도 | 소요 시간 |
|------|----------|--------|-----------|
| 통합 테스트 작성 | P3 | 중 | 3일 |
| OpenTelemetry 통합 | P3 | 중 | 2일 |

**산출물:**
- 통합 테스트 스위트
- 분산 추적 시스템

---

## 부록

### A. 포트 번호 체계

| 포트 | 서비스 | 설명 |
|------|--------|------|
| 5110 | Frontend | Next.js |
| 5111 | API Gateway | 메인 API |
| 5112 | VCP Scanner | VCP 패턴 스캔 |
| 5113 | Signal Engine | 종가베팅 V2 |
| 5114 | Chatbot | AI 챗봇 |
| 5115 | Daytrading Scanner | 단타 스캔 |
| 5433 | PostgreSQL | 데이터베이스 |
| 6380 | Redis | 캐시/메시지 브로커 |
| 5555 | Flower | Celery 모니터링 |

### B. 환경 변수

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ralph_stock

# Redis
REDIS_URL=redis://localhost:6380/0

# Celery
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Services
VCP_SCANNER_URL=http://localhost:5112
SIGNAL_ENGINE_URL=http://localhost:5113
CHATBOT_SERVICE_URL=http://localhost:5114

# Kiwoom REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true
```

### C. 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| Open Architecture | `/docs/OPEN_ARCHITECTURE.md` | 시스템 아키텍처 |
| API Guide | `/docs/api/API_GUIDE.md` | API 엔드포인트 |
| Docker Compose | `/docs/DOCKER_COMPOSE.md` | 배포 가이드 |
| WebSocket | `/docs/WEBSOCKET.md` | WebSocket 설정 |

---

**문서 종료**
