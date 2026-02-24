# API Gateway 모듈화 계획

**작성일**: 2026-02-06
**작성자**: Backend Architect Agent
**상태**: Phase 1 - 계획 수립 완료

---

## 개요

현재 `services/api_gateway/main.py`는 **2,050줄**의 단일 파일로 구성되어 있어 유지보수 및 테스트 커버리지 향상에 어려움이 있습니다. 본 문서는 API Gateway를 체계적으로 모듈화하여 **테스트 커버리지 55% → 70%** 달성하기 위한 리팩토링 계획을 제시합니다.

---

## 현재 상태 분석

### 파일 구조
```
services/api_gateway/
├── main.py (2,050줄) ⚠️ 문제 파일
├── schemas.py (515줄)
├── service_registry.py (250줄)
├── dashboard.py (280줄)
├── routes/
│   ├── ai.py (314줄)
│   ├── api_keys.py (253줄)
│   ├── backtest.py (193줄)
│   ├── chatbot.py (278줛)
│   ├── daytrading.py (295줄)
│   ├── jongga_v2.py (441줄)
│   ├── news.py (299줄)
│   ├── performance.py (306줄)
│   ├── signals.py (272줄)
│   ├── stocks.py (326줄)
│   ├── system.py (641줄)
│   └── triggers.py (569줄)
└── utils/ (비어있음)
```

### main.py 코드 구성 분석

| 구성 요소 | 라인 수 | 비율 | 설명 |
|----------|---------|------|------|
| Imports & Setup | 1-140 | 6.8% | 환경 변수, 모듈 import, 설정 |
| Lifespan Manager | 142-380 | 11.7% | 앱 시작/종료 로직 |
| App Configuration | 382-573 | 9.4% | FastAPI 앱 설정, 미들웨어 |
| Health Endpoints | 579-669 | 4.3% | `/health`, `/`, `/api/health` |
| Metrics Endpoints | 676-782 | 5.2% | `/metrics`, `/api/metrics` |
| KR Market Routes | 788-1239 | 22.1% | 시그널, 마켓게이트, 종가베팅 |
| Stock Detail Routes | 1245-1902 | 32.1% | 종목 상세, 차트, 수급, 시그널 |
| Realtime Prices | 1441-1592 | 7.5% | 실시간 가격 조회 |
| Error Handlers | 1908-1954 | 2.2% | 예외 처리 |
| Internal Endpoints | 1960-2039 | 3.9% | 내부 서비스 통신 |
| Main Entry | 2041-2050 | 0.4% | uvicorn 실행 |

**문제점:**
1. **2,050줄 단일 파일**: 너무 커서 이해하고 테스트하기 어려움
2. **비즈니스 로직 혼재**: 라우트 핸들러 안에 데이터 처리 로직이 포함
3. **Hardcoded 로직**: 등급 계산, 점수 변환 등 별도 서비스 계층 없음
4. **의존성 주입 부족**: DB 세션, 레포지토리 직접 생성
5. **테스트 어려움**: 거대한 함수와 사이드 이펙트로 테스트 작성 어려움

---

## 모듈화 전략: Layered Architecture

### 아키텍처 원칙

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  (FastAPI Routes - Request/Response, Validation only)    │
├─────────────────────────────────────────────────────────┤
│                      Business Layer                      │
│         (Services - Business Logic, Transformations)     │
├─────────────────────────────────────────────────────────┤
│                     Data Access Layer                    │
│         (Repositories - DB Queries, ORM Operations)      │
└─────────────────────────────────────────────────────────┘
```

### 모듈화 목표

1. **Route Handlers**: Request 수신/검증만 담당 (~50줄)
2. **Service Layer**: 비즈니스 로직 분리 (재사용 가능, 테스트 가능)
3. **Dependency Injection**: FastAPI Depends 활용
4. **Single Responsibility**: 각 모듈은 하나의 명확한 책임

---

## 상세 모듈화 계획

### Phase 1: 핵심 서비스 계층 추출 (우선순위: 🔴 높음)

**목표**: main.py에서 비즈니스 로직을 서비스로 분리

#### 1.1 Health & Metrics Service
**파일**: `services/api_gateway/services/health_service.py`

**책임**:
- 시스템 헬스 체크
- 메트릭 수집 및 내보내기
- 서비스 상태 모니터링

**인터페이스**:
```python
class HealthService:
    async def get_system_health(self) -> SystemHealthResponse
    async def get_service_status(self, service_name: str) -> ServiceStatusItem
    def get_metrics(self, metric_type: Optional[str] = None) -> MetricsResponse
    def reset_metrics(self) -> dict
```

**main.py에서 분리할 로직**:
- `/health`, `/api/health` 엔드포인트
- `/metrics`, `/api/metrics` 엔드포인트
- 메트릭 레지스트리 관련 로직

---

#### 1.2 Market Data Service
**파일**: `services/api_gateway/services/market_service.py`

**책임**:
- VCP 시그넌 조회 및 변환
- Market Gate 상태 조회
- 종가베팅 V2 시그널 프록시
- 섹터 데이터 계산

**인터페이스**:
```python
class MarketService:
    async def get_vcp_signals(self, limit: int = 20) -> List[SignalResponse]
    async def get_market_gate_status(self) -> MarketGateStatus
    async def get_jongga_v2_latest(self) -> List[SignalResponse]
    async def analyze_jongga_v2(self, request: dict) -> dict
    def calculate_sector_status(self, change_pct: float) -> str
    def calculate_sector_score(self, change_pct: float) -> float
    def calculate_signal_grade(self, total_score: float) -> str
    def calculate_target_price(self, entry_price: float, grade: str) -> float
```

**main.py에서 분리할 로직**:
- `/api/kr/signals` (lines 788-905)
- `/api/kr/market-gate` (lines 907-1013)
- `/api/kr/backtest-kpi` (lines 1015-1101)
- `/api/kr/jongga-v2/latest` (lines 1103-1168)
- `/api/kr/jongga-v2/analyze` (lines 1170-1239)
- 등급 계산 로직 (lines 841-871)
- 섹터 상태/점수 계산 (lines 936-961)

---

#### 1.3 Stock Detail Service
**파일**: `services/api_gateway/services/stock_service.py`

**책임**:
- 종목 상세 정보 조회
- 차트 데이터 조회
- 수급 데이터 조회
- 시그널 히스토리 조회
- SmartMoney 점수 계산

**인터페이스**:
```python
class StockService:
    async def get_stock_detail(self, ticker: str) -> StockDetailResponse
    async def get_stock_chart(self, ticker: str, period: str) -> StockChartResponse
    async def get_stock_flow(self, ticker: str, days: int) -> StockFlowResponse
    async def get_stock_signals(self, ticker: str, limit: int) -> SignalHistoryResponse
    def calculate_smartmoney_score(self, flow_data: List[FlowDataPoint]) -> float
    def calculate_price_change(self, current: float, previous: float) -> tuple
```

**main.py에서 분리할 로직**:
- `/api/kr/stocks/{ticker}` (lines 1245-1297)
- `/api/kr/stocks/{ticker}/chart` (lines 1360-1434)
- `/api/kr/stocks/{ticker}/flow` (lines 1620-1749)
- `/api/kr/stocks/{ticker}/signals` (lines 1751-1902)
- SmartMoney 점수 계산 (lines 1703-1719)

---

#### 1.4 Realtime Price Service
**파일**: `services/api_gateway/services/price_service.py`

**책임**:
- 실시간 가격 일괄 조회
- 가격 캐시 관리
- 브로드캐스터 연동

**인터페이스**:
```python
class PriceService:
    async def get_realtime_prices(self, tickers: List[str]) -> dict
    async def get_realtime_price(self, ticker: str) -> Optional[dict]
    def calculate_price_change(self, daily_price: DailyPrice) -> tuple
```

**main.py에서 분리할 로직**:
- `/api/kr/realtime-prices` POST (lines 1441-1507)
- `/api/kr/realtime-prices` GET (lines 1509-1592)
- 등락률 계산 로직 (lines 1482-1487, 1567-1572)

---

#### 1.5 Internal Service
**파일**: `services/api_gateway/services/internal_service.py`

**책임**:
- 내부 서비스 간 통신
- 실시간 가격 캐시 조회

**인터페이스**:
```python
class InternalService:
    async def get_realtime_prices_internal(self, tickers: List[str]) -> dict
    async def get_realtime_price_internal(self, ticker: str) -> dict
```

**main.py에서 분리할 로직**:
- `/internal/prices` (lines 1960-2002)
- `/internal/price/{ticker}` (lines 2004-2039)

---

### Phase 2: Lifespan Manager 모듈화 (우선순위: 🟡 중간)

**목표**: 앱 시작/종료 로직을 전담 모듈로 분리

**파일**: `services/api_gateway/lifespan.py`

**책임**:
- Kiwoom REST API 연동
- WebSocket 브로드캐스터 시작/종료
- 하트비트 관리자 시작/종료
- Redis Pub/Sub 시작/종료
- Daytrading Price Broadcaster 시작/종료

**인터페이스**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup 로직
    yield
    # Shutdown 로직
```

**main.py에서 분리할 로직**:
- 전체 `lifespan` 함수 (lines 142-380)

**세부 하위 모듈**:
```python
async def setup_kiwoom_integration(app: FastAPI)
async def setup_price_broadcaster()
async def setup_signal_broadcaster()
async def setup_daytrading_broadcaster()
async def setup_heartbeat_manager()
async def setup_redis_subscriber()

async def teardown_kiwoom_integration()
async def teardown_broadcasters()
async def teardown_subscribers()
```

---

### Phase 3: Application Configuration 모듈화 (우선순위: 🟢 낮음)

**목표**: FastAPI 앱 설정을 별도 파일로 분리

**파일**: `services/api_gateway/app.py`

**책임**:
- FastAPI 앱 인스턴스 생성
- CORS 미들웨어 설정
- Custom 미들웨어 등록
- 라우터 등록
- OpenAPI 설정

**인터페이스**:
```python
def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스 생성 및 설정"""
    app = FastAPI(...)
    setup_cors(app)
    setup_middleware(app)
    setup_routers(app)
    setup_exception_handlers(app)
    return app
```

**main.py에서 분리할 로직**:
- FastAPI 앱 생성 (lines 382-472)
- CORS 설정 (lines 478-504)
- 미들웨어 설정 (lines 506-516)
- 라우터 등록 (lines 522-573)
- 예외 핸들러 (lines 1908-1954)

---

### Phase 4: 의존성 주입 체계 구축

**목표**: FastAPI Depends 활용하여 테스트 가능성 향상

**파일**: `services/api_gateway/dependencies.py`

**책임**:
- DB 세션 의존성
- 서비스 인스턴스 의존성
- 레포지토리 의존성

**인터페이스**:
```python
def get_db_session() -> Generator[Session, None, None]
def get_health_service() -> HealthService
def get_market_service() -> MarketService
def get_stock_service() -> StockService
def get_price_service() -> PriceService
def get_internal_service() -> InternalService
```

---

## 새로운 파일 구조

```
services/api_gateway/
├── main.py (~200줄) ✅ 간결한 진입점
├── app.py (~150줄) ✅ 앱 설정
├── lifespan.py (~250줄) ✅ 라이프사이클 관리
├── dependencies.py (~100줄) ✅ 의존성 주입
├── schemas.py (515줄) ✅ 그대로 유지
├── service_registry.py (250줄) ✅ 그대로 유지
├── dashboard.py (280줄) ✅ 그대로 유지
│
├── services/                    # 🆕 비즈니스 로직 계층
│   ├── __init__.py
│   ├── health_service.py (~150줄)
│   ├── market_service.py (~300줄)
│   ├── stock_service.py (~250줄)
│   ├── price_service.py (~150줄)
│   └── internal_service.py (~100줄)
│
├── routes/                      # ✅ 기존 라우터 유지
│   ├── ai.py (314줄)
│   ├── api_keys.py (253줄)
│   ├── backtest.py (193줄)
│   ├── chatbot.py (278줄)
│   ├── daytrading.py (295줄)
│   ├── jongga_v2.py (441줄)
│   ├── news.py (299줄)
│   ├── performance.py (306줄)
│   ├── signals.py (272줄)
│   ├── stocks.py (326줄)
│   ├── system.py (641줄)
│   └── triggers.py (569줄)
│
├── utils/                       # 🆕 유틸리티 모듈
│   ├── __init__.py
│   ├── grade_calculator.py      # 등급 계산
│   ├── score_calculator.py      # 점수 계산
│   └── price_calculator.py      # 가격 계산
│
└── tests/                       # ✅ 테스트 확장
    ├── test_services/           # 🆕 서비스 계층 테스트
    │   ├── test_health_service.py
    │   ├── test_market_service.py
    │   ├── test_stock_service.py
    │   ├── test_price_service.py
    │   └── test_internal_service.py
    ├── test_utils/              # 🆕 유틸리티 테스트
    │   ├── test_grade_calculator.py
    │   ├── test_score_calculator.py
    │   └── test_price_calculator.py
    ├── test_api.py              # ✅ 기존 API 테스트
    ├── test_service_registry.py
    └── conftest.py
```

**코드 라인 수 비교**:
- **현재**: main.py 2,050줄
- **개선 후**: main.py 200줄 + services 950줄 + app 150줄 + lifespan 250줄 + dependencies 100줄 = 1,650줄
- **순수 추가**: -400줄 (코드 감소 + 구조화)

---

## 구현 순서

### Week 1: 기반 작업
1. **디렉토리 구조 생성**
   ```bash
   mkdir -p services/api_gateway/services
   mkdir -p services/api_gateway/utils
   mkdir -p tests/unit/services
   mkdir -p tests/unit/utils
   touch services/api_gateway/services/__init__.py
   touch services/api_gateway/utils/__init__.py
   ```

2. **유틸리티 모듈 추출** (가장 단순한 작업부터)
   - `grade_calculator.py`: 등급 계산 로직
   - `score_calculator.py`: 점수 계산 로직
   - `price_calculator.py`: 가격/등락률 계산 로직

3. **테스트 작성** (TDD 방식)
   - 각 유틸리티 함수에 대한 단위 테스트 작성
   - 목표 커버리지: 90%+

### Week 2: 서비스 계층 구현
1. **HealthService 구현**
   - `services/health_service.py` 작성
   - 테스트 작성
   - main.py에서 HealthService 사용하도록 리팩토링

2. **PriceService 구현**
   - `services/price_service.py` 작성
   - 테스트 작성
   - main.py에서 PriceService 사용하도록 리팩토링

3. **InternalService 구현**
   - 가장 단순한 서비스로 먼저 구현

### Week 3: 핵심 비즈니스 로직
1. **MarketService 구현**
   - VCP 시그널 변환 로직 분리
   - Market Gate 상태 계산 분리
   - 종가베팅 V2 프록시 로직 분리
   - 테스트 작성 (Mock 활용)

2. **StockService 구현**
   - 종목 상세 조회 로직 분리
   - 차트 데이터 조회 로직 분리
   - 수급 데이터 및 SmartMoney 계산 분리
   - 시그널 히스토리 조회 로직 분리
   - 테스트 작성

### Week 4: 통합 및 최적화
1. **의존성 주입 체계 구축**
   - `dependencies.py` 작성
   - 모든 서비스를 FastAPI Depends로 주입

2. **Lifespan 모듈화**
   - `lifespan.py`로 분리
   - 하위 함수들로 세분화

3. **App Configuration 모듈화**
   - `app.py`로 분리
   - create_app() 패턴 적용

4. **main.py 간소화**
   - 진입점만 남기기
   - create_app() 호출

### Week 5: 테스트 커버리지 향상
1. **서비스 계층 테스트 확장**
   - Mock Repository 활용
   - 경계 케이스 테스트
   - 통합 테스트 추가

2. **API 통합 테스트 개선**
   - TestClient 활용
   - E2E 시나리오 테스트

3. **커버리지 측정 및 개선**
   - 목표: 70% 달성
   - 누락된 부분 테스트 추가

---

## 테스트 전략

### 단위 테스트 (Unit Tests)
**대상**: Service Layer, Utils

```python
# 예시: tests/unit/services/test_market_service.py
import pytest
from unittest.mock import Mock, patch
from services.api_gateway.services.market_service import MarketService

@pytest.fixture
def market_service(db_session):
    return MarketService(db_session)

@pytest.fixture
def mock_registry():
    with patch('services.api_gateway.services.market_service.get_registry') as mock:
        yield mock

async def test_get_vcp_signals_success(market_service, mock_registry):
    """VCP 시그널 조회 성공 테스트"""
    # Given
    mock_vcp_scanner = {'url': 'http://localhost:5112'}
    mock_registry.return_value.get_service.return_value = mock_vcp_scanner

    mock_response = Mock()
    mock_response.json.return_value = {
        "signals": [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "total_score": 85,
                "current_price": 80000,
                "analysis_date": "2026-02-06"
            }
        ]
    }

    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.raise_for_status = Mock()
        mock_get.return_value.json.return_value = mock_response.json()

        # When
        signals = await market_service.get_vcp_signals(limit=10)

        # Then
        assert len(signals) == 1
        assert signals[0].ticker == "005930"
        assert signals[0].grade == "A"  # 85점 → A등급

async def test_calculate_signal_grade():
    """등급 계산 로직 테스트"""
    # Given
    from services.api_gateway.utils.grade_calculator import calculate_signal_grade

    # When & Then
    assert calculate_signal_grade(85) == "A"
    assert calculate_signal_grade(95) == "S"
    assert calculate_signal_grade(65) == "B"
    assert calculate_signal_grade(45) == "C"
```

### 통합 테스트 (Integration Tests)
**대상**: API Endpoints

```python
# 예시: tests/integration/test_market_api.py
import pytest
from httpx import AsyncClient
from services.api_gateway.main import app

@pytest.mark.asyncio
async def test_get_vcp_signals_api():
    """VCP 시그널 API 엔드포인트 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/kr/signals?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
```

### 테스트 커버리지 목표

| 모듈 | 현재 커버리지 | 목표 커버리지 | 테스트 수 |
|------|--------------|--------------|----------|
| Utils (신규) | 0% | 90%+ | 20+ |
| Services (신규) | 0% | 85%+ | 40+ |
| Routes (기존) | 55% | 75%+ | 30+ |
| **전체** | **55%** | **70%** | **90+** |

---

## 성공 지표

### 정량적 지표
1. **코드 라인 수**: main.py 2,050줄 → 200줄 (90% 감소)
2. **테스트 커버리지**: 55% → 70% (15% 증가)
3. **테스트 수**: 622개 → 700+개 (80+개 추가)
4. **순환 복잡도**: main.py 50+ → 10 이하
5. **함수 평균 길이**: 50줄+ → 20줄 이하

### 정성적 지표
1. **가독성**: 각 모듈의 목적이 명확하게 식별 가능
2. **테스트 가능성**: Mock 없이 단위 테스트 작성 가능
3. **재사용성**: 서비스 계층이 다른 컨텍스트에서 재사용 가능
4. **유지보수성**: 새로운 기능 추가 시 영향 범위 최소화
5. **확장성**: 새로운 엔드포인트 추가가 용이

---

## 리스크 및 완화 계획

### 리스크 1: 리팩토링 중 기능 회귀
**완화**:
- 각 Phase마다 통합 테스트 실행
- Feature Branch 전략 활용
- 점진적 리팩토링 (한 번에 하나의 서비스만)

### 리스크 2: 과도한 설계로 인한 지연
**완화**:
- YAGNI 원칙 준수 (현재 필요한 것만 구현)
- MVP 서비스부터 시작 (HealthService → PriceService → MarketService)
- 주간 리뷰 및 범위 조정

### 리스크 3: 기존 라우터와의 호환성
**완화**:
- API 스펙 변경 없음 (내부 구조만 변경)
- 통합 테스트로 기존 동작 보장
- 점진적 마이그레이션 (일부 엔드포인트만 서비스 사용)

### 리스크 4: 테스트 작성 시간 부족
**완화**:
- TDD 방식 적용 (구현 전 테스트 작성)
- Mock 적극 활용 (DB 외부 의존성 제거)
- pytest fixture 재사용

---

## 다음 단계 (Action Items)

### 즉시 시작 (Week 1 Day 1-2)
1. ✅ `docs/backend/API_GATEWAY_MODULARIZATION_PLAN.md` 문서 작성 완료
2. 🔄 `docs/backend/` 디렉토리 구조 확립
3. ⏳ `services/api_gateway/services/` 디렉토리 생성
4. ⏳ `services/api_gateway/utils/` 디렉토리 생성

### Week 1 Day 3-5: 유틸리티 추출
1. ⏳ `grade_calculator.py` 구현 및 테스트
2. ⏳ `score_calculator.py` 구현 및 테스트
3. ⏳ `price_calculator.py` 구현 및 테스트
4. ⏳ 커버리지 측정 (목표: 90%+)

### Week 2: HealthService & PriceService
1. ⏳ `health_service.py` 구현
2. ⏳ `price_service.py` 구현
3. ⏳ main.py 리팩토링 (Health/Price 엔드포인트)
4. ⏳ 통합 테스트 업데이트

---

## 참고 자료

### 기존 문서
- `docs/api/API_GUIDE.md` - API 엔드포인트 명세
- `docs/OPEN_ARCHITECTURE.md` - 마이크로서비스 구조
- `docs/SERVICE_MODULARIZATION.md` - 서비스 모듈화 가이드

### Best Practices
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Layered Architecture in Python](https://realpython.com/python-application-layouts/)
- [Testing FastAPI Applications](https://fastapi.tiangolo.com/tutorial/testing/)

---

**문서 버전**: 1.0
**마지막 수정**: 2026-02-06
**승인자**: Backend Architect Team
