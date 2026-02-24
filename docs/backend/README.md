# Backend Architecture Documentation

**Ralph Stock Analysis System - Backend Architecture**

---

## 문서 개요

本 디렉토리 (`/docs/backend/`)는 한국 주식 분석 시스템의 백엔드 아키텍처에 대한 공식 문서 저장소입니다. 모든 백엔드 설계, API 명세, 데이터베이스 스키마 변경은 이곳에 먼저 문서화되어야 합니다.

> **Backend Architect Agent의 Golden Rule**: `/docs/backend`는 단일 진실의 원천(Single Source of Truth)입니다. 어떠한 코드 변경도 사전에 이 문서를 반영해야 합니다.

---

## 문서 구조

```
docs/backend/
├── README.md                          # 본 파일 - 백엔드 문서 개요
├── API_GATEWAY_MODULARIZATION_PLAN.md # API Gateway 리팩토링 계획 ⭐
├── ARCHITECTURE_ANALYSIS_20260206.md  # 초기 아키텍처 분석
│
├── api-specs/                         # API 명세서
│   ├── api-gateway-routes.md          # API Gateway 엔드포인트 명세 ⭐
│   ├── service-layer-spec.md          # 서비스 계층 명세 (예정)
│   └── response-models.md             # 공통 응답 모델 (예정)
│
├── schemas/                           # 데이터베이스 스키마
│   ├── database-schema.md             # 전체 DB 스키마 (예정)
│   ├── stock-table.md                 # stocks 테이블 (예정)
│   ├── signal-table.md                # signals 테이블 (예정)
│   └── daily-price-table.md           # daily_prices 테이블 (TimescaleDB) (예정)
│
├── security/                          # 보안 설계
│   ├── authentication.md              # 인증 흐름 (예정)
│   ├── authorization.md               # 권한 부여 (예정)
│   └── audit-logging.md               # 감사 로깅 (예정)
│
└── guides/                           # 구현 가이드
    ├── testing-guide.md               # 테스트 작성 가이드 (예정)
    ├── error-handling.md              # 에러 처리 패턴 (예정)
    └── deployment.md                  # 배포 절차 (예정)
```

---

## 주요 문서

### 1. API Gateway 모듈화 계획 ⭐
**파일**: `API_GATEWAY_MODULARIZATION_PLAN.md`

**목차**:
- 현재 상태 분석 (main.py 2,050줄)
- 모듈화 전략 (Layered Architecture)
- 상세 모듈화 계획 (Phase 1-4)
- 새로운 파일 구조
- 구현 순서 (5주 계획)
- 테스트 전략
- 성공 지표

**핵심 내용**:
```
현재: main.py 2,050줄 (단일 파일)
목표: main.py 200줄 + Service Layer 950줄 + App 150줄

아키텍처:
Presentation Layer (FastAPI Routes)
      ↓
Business Layer (Services)
      ↓
Data Access Layer (Repositories)
```

---

### 2. API Gateway Routes Specification
**파일**: `api-specs/api-gateway-routes.md`

**목차**:
- Health Check & Metrics (5개 엔드포인트)
- Market Data (5개 엔드포인트)
- Stock Detail (4개 엔드포인트)
- Realtime Prices (2개 엔드포인트)
- Internal (2개 엔드포인트)
- 모듈별 라우터 구성

**핵심 엔드포인트**:
```
Health Check:
- GET /health
- GET /metrics

Market Data:
- GET /api/kr/signals
- GET /api/kr/market-gate
- GET /api/kr/jongga-v2/latest

Stock Detail:
- GET /api/kr/stocks/{ticker}
- GET /api/kr/stocks/{ticker}/chart
- GET /api/kr/stocks/{ticker}/flow
```

---

## 백엔드 아키텍처 원칙

### 1. 신뢰성 (Reliability) 최우선
- **데이터 무결성**: ACID 트랜잭션 준수
- **장애 격리**: Circuit Breaker 패턴
- **그레이스풀 데그레이션**: 서비스 일부 장애 시 전체 장애 방지
- **재시도 전략**: Exponential Backoff

### 2. Repository Pattern 준수
모든 데이터베이스 접근은 Repository를 통해야 합니다:

```python
# ✅ 올바른 예
from src.repositories.stock_repository import StockRepository
from src.database.session import get_db_session

async def get_stock(ticker: str):
    async with get_db_session() as db:
        repo = StockRepository(db)
        return await repo.get_by_ticker(ticker)

# ❌ 잘못된 예
from src.database.models import Stock

async def get_stock(ticker: str):
    async with get_db_session() as db:
        return db.query(Stock).filter(Stock.ticker == ticker).first()
```

### 3. 계층 분리 (Separation of Concerns)

```
┌─────────────────────────────────────┐
│   Presentation Layer (Routes)       │
│   - Request 수신/검증               │
│   - Response 반환                   │
│   - 비즈니스 로직 없음              │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Business Layer (Services)         │
│   - 비즈니스 로직 수행              │
│   - 데이터 변환                     │
│   - 외부 API 호출                   │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Data Access Layer (Repositories)  │
│   - DB 쿼리 수행                   │
│   - ORM 매핑                       │
│   - 트랜잭션 관리                  │
└─────────────────────────────────────┘
```

### 4. 의존성 주입 (Dependency Injection)
FastAPI Depends를 활용한 테스트 가능한 코드:

```python
from fastapi import Depends

async def get_stock_detail(
    ticker: str,
    service: StockService = Depends(get_stock_service)
):
    return await service.get_stock_detail(ticker)
```

### 5. 포트 포워딩 일관성
모든 서비스는 `511x` 포트 범위 사용:

| 포트 | 서비스 | 설명 |
|------|--------|------|
| 5110 | Frontend | Next.js UI |
| 5111 | API Gateway | Main Gateway |
| 5112 | VCP Scanner | Pattern Detection |
| 5113 | Signal Engine | Signal Generation |
| 5114 | Chatbot | AI Chatbot |
| 5115 | Daytrading Scanner | Daytrading Signals |

---

## 데이터베이스 아키텍처

### 데이터베이스 목록
- **PostgreSQL 15+**: 주요 데이터 저장소
- **TimescaleDB Extension**: 시계열 데이터 최적화 (daily_prices, institutional_flows)
- **Redis 7+**: 캐시 및 메시지 브로커

### 주요 테이블

| 테이블명 | 설명 | Extension |
|----------|------|-----------|
| `stocks` | 종목 기본 정보 | - |
| `signals` | VCP/종가베팅 시그널 | - |
| `daily_prices` | 일봉 OHLCV 데이터 | TimescaleDB (hypertable) |
| `institutional_flows` | 기관 수급 데이터 | TimescaleDB (hypertable) |
| `market_status` | Market Gate 상태 | - |
| `ai_analyses` | AI 분석 결과 | - |
| `backtest_results` | 백테스트 결과 | - |

### TimescaleDB Hypertable 설정
```sql
-- daily_prices 테이블을 hypertable로 변환
SELECT create_hypertable('daily_prices', 'date');

-- institutional_flows 테이블을 hypertable로 변환
SELECT create_hypertable('institutional_flows', 'date');

-- 30일보다 오래된 데이터 자동 삭제 (선택)
SELECT add_retention_policy('daily_prices', INTERVAL '30 days');
```

---

## API 설계 원칙

### 1. RESTful URL 구조
```
{api-version}/{market}/{resource}/{id}/{sub-resource}

예시:
- /api/kr/signals
- /api/kr/stocks/005930
- /api/kr/stocks/005930/chart
- /api/kr/stocks/005930/flow
```

### 2. HTTP 메서드 사용
- `GET`: 리소스 조회 (멱등성)
- `POST`: 리소스 생성 또는 복잡한 조회
- `PUT`: 리소스 전체 업데이트 (멱등성)
- `PATCH`: 리소스 부분 업데이트
- `DELETE`: 리소스 삭제 (멱등성)

### 3. 상태 코드 활용
- `200 OK`: 정상 응답
- `201 Created`: 리소스 생성 성공
- `400 Bad Request`: 잘못된 요청
- `404 Not Found`: 리소스 없음
- `422 Unprocessable Entity`: 검증 실패
- `500 Internal Server Error`: 서버 에러
- `503 Service Unavailable`: 서비스 임시 unavailable

### 4. 응답 형식 표준화
```json
// 성공 응답
{
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}

// 에러 응답
{
  "status": "error",
  "code": 404,
  "detail": "Stock not found: 005930",
  "path": "/api/kr/stocks/005930"
}
```

---

## 테스트 전략

### 테스트 피라미드
```
        /\
       /E2E\        10% (통합 테스트)
      /------\
     /  Integration 30% (서비스 계층 테스트)
    /------------\
   /   Unit Tests \   60% (단위 테스트)
  /----------------\
```

### 테스트 커버리지 목표
| 레이어 | 현재 | 목표 |
|-------|------|------|
| Routes | 55% | 75% |
| Services (신규) | 0% | 85% |
| Repositories | 65% | 80% |
| Utils (신규) | 0% | 90% |
| **전체** | **55%** | **70%** |

### 테스트 작성 가이드

#### 단위 테스트 (Unit Tests)
```python
# tests/unit/services/test_market_service.py
import pytest
from unittest.mock import Mock, patch

class TestMarketService:
    @pytest.mark.asyncio
    async def test_get_vcp_signals_success(self):
        # Given
        service = MarketService(mock_db)
        mock_registry.get_service.return_value = {
            'url': 'http://localhost:5112'
        }

        # When
        signals = await service.get_vcp_signals(limit=10)

        # Then
        assert len(signals) <= 10
        assert all(s.grade in ['S', 'A', 'B', 'C'] for s in signals)
```

#### 통합 테스트 (Integration Tests)
```python
# tests/integration/test_market_api.py
import pytest
from httpx import AsyncClient
from services.api_gateway.main import app

@pytest.mark.asyncio
async def test_get_vcp_signals_api():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/kr/signals?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

---

## 보안 가이드라인

### 1. 인증 및 인가
- 현재: 인증 없음 (내부용)
- 향후 계획: JWT 기반 인증

### 2. 데이터 검증
```python
from pydantic import BaseModel, Field, validator

class StockRequest(BaseModel):
    ticker: str = Field(..., min_length=6, max_length=6)
    period: str = Field(default="6mo")

    @validator('ticker')
    def validate_ticker(cls, v):
        if not v.isdigit():
            raise ValueError('Ticker must be 6 digits')
        return v
```

### 3. SQL Injection 방지
```python
# ✅ 올바른 예 (Parameterized Query)
db.execute(
    select(Stock).where(Stock.ticker == ticker)
)

# ❌ 잘못된 예 (String Concatenation)
db.execute(f"SELECT * FROM stocks WHERE ticker = '{ticker}'")
```

### 4. Rate Limiting
| 엔드포인트 그룹 | 제한 | 기간 |
|----------------|------|------|
| Health/Metrics | 제한 없음 | - |
| Market Data | 100 요청 | 1분 |
| Stock Detail | 60 요청 | 1분 |
| Realtime Prices | 30 요청 | 1분 |

---

## 배포 절차

### 1. Docker Compose Profiles
```bash
# 개발 환경
make dev

# 운영 환경
make prod

# 테스트 환경
make test
```

### 2. 환경 변수 필수 항목
```bash
# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://...

# Kiwoom REST API (선택)
KIWOOM_APP_KEY=...
KIWOOM_SECRET_KEY=...

# Services
VCP_SCANNER_URL=http://localhost:5112
SIGNAL_ENGINE_URL=http://localhost:5113
```

### 3. Health Check
```bash
# 서비스 시작 후 헬스 체크
curl http://localhost:5111/health

# 예상 응답
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "2.0.0"
}
```

---

## 문서화 규칙

### 1. API 명세 작성
모든 신규 API는 `/docs/backend/api-specs/`에 문서화되어야 합니다.

### 2. 스키마 변경 문서화
데이터베이스 스키마 변경 시 `/docs/backend/schemas/`에 업데이트합니다.

### 3. 아키텍처 변경 보고
주요 아키텍처 변경 시 `/docs/backend/ARCHITECTURE_ANALYSIS_YYYYMMDD.md`를 작성합니다.

### 4. 주기적 검토
- **주간**: Backend Architect Team이 문서 최신성 확인
- **월간**: 전체 문서 검토 및 갱신
- **분기별**: 아키텍처 원칙 재검토

---

## 관련 문서

### 프로젝트 레벨
- [CLAUDE.md](../../CLAUDE.md) - 프로젝트 개요
- [DOCKER_COMPOSE.md](../../DOCKER_COMPOSE.md) - Docker 설정
- [OPEN_ARCHITECTURE.md](../../OPEN_ARCHITECTURE.md) - 마이크로서비스 구조

### API 레벨
- [API_GUIDE.md](../../api/API_GUIDE.md) - 전체 API 가이드
- [CHART_SYSTEM.md](../../api/CHART_SYSTEM.md) - 차트 시스템
- [WEBSOCKET.md](../../WEBSOCKET.md) - WebSocket 설정

### 테스트
- [TESTING.md](../../TESTING.md) - 테스트 가이드

---

## 다음 단계 (Action Items)

### 즉시 실행 (Week 1)
1. ✅ `docs/backend/README.md` 작성 완료
2. ✅ `docs/backend/API_GATEWAY_MODULARIZATION_PLAN.md` 작성 완료
3. ✅ `docs/backend/api-specs/api-gateway-routes.md` 작성 완료
4. ⏳ `docs/backend/schemas/` 디렉토리 생성
5. ⏳ `docs/backend/guides/` 디렉토리 생성

### Week 2-3: API Gateway 모듈화
1. ⏳ `services/api_gateway/services/` 디렉토리 생성
2. ⏳ 유틸리티 모듈 추출 (grade_calculator, score_calculator, price_calculator)
3. ⏳ 서비스 계층 구현 (HealthService, MarketService, StockService, PriceService)
4. ⏳ 테스트 작성 (목표 커버리지: 70%)

### Week 4-5: 통합 및 최적화
1. ⏳ 의존성 주입 체계 구축
2. ⏳ Lifespan Manager 모듈화
3. ⏳ App Configuration 모듈화
4. ⏳ main.py 간소화 (2,050줄 → 200줄)

---

## 연락처

**Backend Architect Team**
- 이메일: backend-team@krstock.example.com
- Slack: #backend-architecture
- GitHub: @ralph-stock/backend-team

---

**문서 버전**: 1.0
**마지막 수정**: 2026-02-06
**유지보수자**: Backend Architect Agent
