# Implementation Plan: Open Architecture Migration

**Status**: 🔄 In Progress
**Started**: 2026-01-23
**Last Updated**: 2026-01-23
**Estimated Completion**: 2026-04-23 (12 weeks)

---

**⚠️ CRITICAL INSTRUCTIONS**: After completing each phase:
1. ✅ Check off completed task checkboxes
2. 🧪 Run all quality gate validation commands
3. ⚠️ Verify ALL quality gate items pass
4. 📅 Update "Last Updated" date above
5. 📝 Document learnings in Notes section
6. ➡️ Only then proceed to next phase

⛔ **DO NOT skip quality gates or proceed with failing checks**

---

## 📋 Overview

### Feature Description
현재 Monolithic Flask 기반 한국 주식 AI 분석 시스템을 Open Architecture (Microservices + Event-Driven)로 재구성합니다. CSV/JSON 파일 기반 저장소를 PostgreSQL/TimescaleDB로 이전하고, Celery + Redis 기반 비동기 처리를 도입하여 확장 가능한 아키텍처를 구축합니다.

### Success Criteria
- [ ] PostgreSQL 데이터베이스로 성공적으로 마이그레이션 완료
- [ ] 모든 서비스가 독립적으로 배포 가능한 상태로 분리
- [ ] Celery 기반 백그라운드 작업이 정상 동작
- [ ] 이벤트 버스를 통한 서비스 간 통신 구현
- [ ] 기존 기능에 대한 회귀 없이 성능 개선 달성
- [ ] 프로덕션 환경에서 모니터링 시스템 운영

### User Impact
- **안정성**: 데이터베이스를 통한 데이터 무결성 보장
- **성능**: 비동기 처리로 API 응답 시간 단축
- **확장성**: 수폭 확장을 통한 트래픽 처리 능력 향상
- **신뢰성**: 서비스 분리로 장애 격리 및 빠른 복구

---

## 🏗️ Architecture Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **PostgreSQL + TimescaleDB** | 시계열 데이터 최적화, ACID 보장, 풍부한 생태계 | NoSQL 유연성 포기, 학습 곡선 |
| **Redis + Celery** | Python 친화적, 간단한 구현, 풍부한 기능 | Kafka의 대용량 처리 능력 포기 |
| **Docker Compose** | 개발/프로덕션 일관성, 간편한 배포 | Kubernetes의 복잡한 기능 포기 |
| **FastAPI (신규 서비스)** | 비동기 처리, 자동 문서, 높은 성능 | Flask 생태계와 호환성 고려 |
| **Redis Pub/Sub (이벤트 버스)** | 간단한 구현, 기존 Redis 활용 | RabbitMQ의 안정성/기능 포기 |
| **Prometheus + Grafana** | 표준 모니터링 스택, 풍부한 시각화 | 학습 곡선, 추가 인프라 |

---

## 📦 Dependencies

### Required Before Starting
- [ ] **Docker & Docker Compose**: 컨테이너 실행 환경
- [ ] **Python 3.11+**: 모든 서비스의 Python 버전
- [ ] **Node.js 20+**: Next.js Frontend
- [ ] **PostgreSQL 15+**: 데이터베이스 서버
- [ ] **Redis 7+**: 캐시 및 메시지 브로커

### External Dependencies
```
# Python Backend
fastapi==0.104.0
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
celery[redis]==5.3.4
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
timescaledb==2.13.0 (PostgreSQL extension)

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
httpx==0.25.2  # FastAPI 테스트용
pytest-mock==3.12.0

# Monitoring
prometheus-client==0.19.0

# 기존 의존성 유지
flask==3.0.0
pykrx==1.0.45
yfinance==0.2.32
pandas==2.1.3
google-generativeai==0.3.2
```

---

## 🧪 Test Strategy

### Testing Approach
**TDD Principle**: 모든 구현 전에 테스트를 먼저 작성하고, Red-Green-Refactor 사이클을 따릅니다.

### Test Pyramid for This Migration

| Test Type | Coverage Target | Purpose |
|-----------|-----------------|---------|
| **Unit Tests** | ≥85% | 비즈니스 로직, Repository, Service 계층 |
| **Integration Tests** | Critical paths | API 엔드포인트, DB 연동, 서비스 간 통신 |
| **E2E Tests** | Key user flows | 전체 시스템 동작 검증 |
| **Migration Tests** | 100% | 데이터 마이그레이션 정확성 |

### Test File Organization
```
tests/
├── unit/
│   ├── repositories/      # DB Repository 단위 테스트
│   ├── services/          # 비즈니스 로직 단위 테스트
│   ├── models/            # 데이터 모델 테스트
│   └── tasks/             # Celery Task 테스트
├── integration/
│   ├── api/               # API 통합 테스트
│   ├── database/          # DB 연동 테스트
│   └── services/          # 서비스 간 통신 테스트
├── e2e/
│   ├── vcp_flow/          # VCP 시그널 생성 플로우
│   └── closing_bet_flow/  # 종가베팅 생성 플로우
└── migration/
    └── data_migration/     # CSV→DB 마이그레이션 테스트
```

### Coverage Requirements by Phase
- **Phase 1 (DB)**: Repository ≥85%, Migration scripts 100%
- **Phase 2 (API)**: Endpoints ≥80%, Authentication ≥90%
- **Phase 3 (VCP)**: Scanner logic ≥85%, Integration ≥75%
- **Phase 4 (Signal)**: Generator ≥85%, Scorer ≥85%
- **Phase 5 (Celery)**: Tasks ≥80%, Integration ≥70%
- **Phase 6 (Events)**: Handlers ≥80%, Event bus ≥75%
- **Phase 7 (Cache)**: Cache layer ≥80%, Hit rate validation

### Test Naming Convention
```python
# Python (pytest)
def test_{feature}_{scenario}_{expected_result}():
    """Given {precondition}, when {action}, then {outcome}"""
    # Arrange
    # Act
    # Assert
```

### Coverage Commands
```bash
# Unit Tests with Coverage
pytest tests/unit/ --cov=src --cov-report=html --cov-report=term

# Integration Tests
pytest tests/integration/ --cov=src --cov-append --cov-report=html

# All Tests
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Coverage Report Open
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## 🚀 Implementation Phases

### Phase 1: Database Layer Introduction
**Goal**: CSV/JSON 기반 저장소를 PostgreSQL + TimescaleDB로 이전하고, 데이터 마이그레이션을 완료합니다.
**Estimated Time**: 12 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 1.1**: Repository 패턴 단위 테스트 작성
  - File(s): `tests/unit/repositories/test_stock_repository.py`, `tests/unit/repositories/test_signal_repository.py`
  - Expected: Tests FAIL (red) - Repository 클래스가 없음
  - Details:
    - `StockRepository.create()` - 종목 생성
    - `StockRepository.get_by_ticker()` - 종목 조회
    - `StockRepository.list_all()` - 전체 종목 목록
    - `SignalRepository.create()` - 시그널 생성
    - `SignalRepository.get_active()` - 활성 시그널 조회
    - `SignalRepository.update_status()` - 상태 업데이트

- [ ] **Test 1.2**: 데이터 마이그레이션 통합 테스트
  - File(s): `tests/migration/test_csv_to_db_migration.py`
  - Expected: Tests FAIL (red) - 마이그레이션 스크립트 없음
  - Details:
    - CSV 파일 → DB 레코드 변환 정확성
    - 중복 데이터 처리
    - 데이터 타입 변환 검증
    - Foreign Key 무결성

- [ ] **Test 1.3**: TimescaleDB 시계열 데이터 테스트
  - File(s): `tests/integration/database/test_timescaledb.py`
  - Expected: Tests FAIL (red) - TimescaleDB 미설정
  - Details:
    - 일봉 데이터 저장 및 조회
    - 시간 범위 쿼리 성능
    - 하이퍼테이블 자동 파티셔닝

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 1.4**: SQLAlchemy 스키마 정의
  - File(s): `src/database/models.py`, `src/database/schema.py`
  - Goal: Test 1.1 통과
  - Details:
    - Base 모델 클래스 (created_at, updated_at)
    - Stock 모델 (ticker, name, market, sector, ...)
    - Signal 모델 (type, status, score, entry_price, ...)
    - Trade 모델 (entry_time, exit_time, return_pct, ...)
    - InstitutionalFlow 모델 (date, foreign_net_buy, inst_net_buy, ...)
    - TimescaleDB 하이퍼테이블 (daily_prices, institutional_flows)

- [ ] **Task 1.5**: Repository 패턴 구현
  - File(s): `src/repositories/stock_repository.py`, `src/repositories/signal_repository.py`, `src/repositories/base.py`
  - Goal: Test 1.1 통과
  - Details:
    - SQLAlchemy Session 관리
    - CRUD 메서드 구현
    - 쿼리 빌더 패턴
    - 트랜잭션 처리

- [ ] **Task 1.6**: Alembic 마이그레이션 설정
  - File(s): `alembic.ini`, `src/database/migrations/versions/*.py`
  - Goal: DB 스키마 버전 관리
  - Details:
    - Alembic 초기화
    - 자동 마이그레이션 생성
    - 업그레이드/다운그레이드 스크립트

- [ ] **Task 1.7**: CSV → DB 마이그레이션 스크립트
  - File(s): `scripts/migrate_csv_to_db.py`
  - Goal: Test 1.2 통과
  - Details:
    - daily_prices.csv → TimescaleDB
    - all_institutional_trend_data.csv → TimescaleDB
    - korean_stocks_list.csv → PostgreSQL
    - signals_log.csv → PostgreSQL
    - 진행률 표시 및 에러 복구

- [ ] **Task 1.8**: Docker Compose 설정
  - File(s): `docker-compose.yml`, `Dockerfile`
  - Goal: 로컬 개발 환경 구성
  - Details:
    - PostgreSQL 15 + TimescaleDB extension
    - Redis 7
    - 네트워크 설정
    - 볼륨 마운트

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 1.9**: 코드 품질 개선
  - Files: Phase 1의 모든 코드
  - Goal: 테스트 유지하며 리팩토링
  - Checklist:
    - [ ] 중복 제거 (BaseRepository 추출)
    - [ ] 명명 규칙 통일 (snake_case)
    - [ ] 타입 힌트 추가 (Pydantic models)
    - [ ] 에러 처리 개선 (Custom exceptions)
    - [ ] 로깅 추가 (structlog)

#### Quality Gate ✋

**⚠️ STOP: Do NOT proceed to Phase 2 until ALL checks pass**

**TDD Compliance** (CRITICAL):
- [ ] **Red Phase**: Tests written FIRST and initially failed
- [ ] **Green Phase**: Production code written to make tests pass
- [ ] **Refactor Phase**: Code improved while tests still pass
- [ ] **Coverage Check**: ≥85% for repositories, 100% for migration scripts
  ```bash
  pytest tests/unit/repositories/ tests/migration/ --cov=src/database --cov=src/repositories --cov-report=html
  # HTML report should show ≥85% coverage
  ```

**Build & Tests**:
- [ ] **Build**: Docker Compose builds without errors (`docker-compose build`)
- [ ] **All Tests Pass**: 100% of tests passing
- [ ] **Test Performance**: Test suite < 5 minutes
- [ ] **No Flaky Tests**: Run 3 times, all pass consistently

**Code Quality**:
- [ ] **Linting**: `ruff check .` passes with no errors
- [ ] **Formatting**: `ruff format --check .` passes
- [ ] **Type Checking**: `mypy src/` passes
- [ ] **SQL**: `sqlfluff lint` passes (SQL 스타일)

**Database Validation**:
- [ ] **Schema**: Alembic upgrade successful (`alembic upgrade head`)
- [ ] **Migration**: All CSV data migrated correctly
  ```bash
  # Row count verification
  python -c "
  import pandas as pd
  csv_count = len(pd.read_csv('data/daily_prices.csv'))
  db_count = len(pd.read_sql('SELECT * FROM daily_prices', con=db_engine))
  assert csv_count == db_count, f'Mismatch: CSV={csv_count}, DB={db_count}'
  "
  ```
- [ ] **Constraints**: Foreign keys, unique constraints enforced
- [ ] **Indexes**: Required indexes created (analyze `EXPLAIN`)

**Security**:
- [ ] **Credentials**: DB passwords in environment variables only
- [ ] **Backups**: pg_dump backup script tested
- [ ] **Access**: User privileges minimal (principle of least privilege)

**Performance**:
- [ ] **Query Performance**: All queries < 100ms (use `EXPLAIN ANALYZE`)
- [ ] **Index Usage**: No sequential scans on large tables
- [ ] **Connection Pool**: SQLAlchemy pool configured (size=20)

**Documentation**:
- [ ] **Schema Documentation**: ERD diagram generated
- [ ] **Migration Guide**: How to migrate from CSV to DB
- [ ] **API Docs**: Repository methods documented with docstrings

**Validation Commands**:
```bash
# Build
docker-compose build

# Database Setup
docker-compose up -d postgres redis
alembic upgrade head

# Run Migration
python scripts/migrate_csv_to_db.py --dry-run
python scripts/migrate_csv_to_db.py

# Tests
pytest tests/unit/repositories/ tests/migration/ --cov=src/database --cov=src/repositories --cov-report=html

# Code Quality
ruff check .
ruff format --check .
mypy src/

# Database Validation
psql -U postgres -d kr_stock -c "SELECT COUNT(*) FROM daily_prices;"
psql -U postgres -d kr_stock -c "SELECT COUNT(*) FROM signals;"
```

**Manual Test Checklist**:
- [ ] CSV 데이터가 DB에 정확히 복사되었는지 확인
- [ ] 기존 Flask 앱이 DB에서 데이터를 읽을 수 있는지 확인
- [ ] DB 재시작 후 데이터가 유지되는지 확인
- [ ] 백업/복구 테스트 완료

---

### Phase 2: API Gateway Modularization
**Goal**: 단일 Flask 앱을 API Gateway 패턴으로 리팩토링하고, 라우팅 계층을 분리합니다.
**Estimated Time**: 10 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 2.1**: API Gateway 라우팅 테스트
  - File(s): `tests/integration/api/test_gateway_routing.py`
  - Expected: Tests FAIL (red) - Gateway 미구현
  - Details:
    - `/api/kr/signals` → VCP Scanner Service
    - `/api/kr/market-gate` → Market Analyzer Service
    - `/api/kr/jongga-v2/latest` → Signal Engine Service
    - `/api/kr/chatbot` → Chatbot Service
    - 인증/권한 검증
    - Rate limiting

- [ ] **Test 2.2**: 서비스 Discovery 테스트
  - File(s): `tests/unit/services/test_service_discovery.py`
  - Expected: Tests FAIL (red) - Service Discovery 미구현
  - Details:
    - 서비스 등록
    - 서비스 조회 (by name)
    - 헬스 체크
    - 로드 밸런싱 (round-robin)

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 2.3**: FastAPI API Gateway 구현
  - File(s): `services/api-gateway/main.py`, `services/api-gateway/routers/kr.py`, `services/api-gateway/routers/common.py`
  - Goal: Test 2.1 통과
  - Details:
    - FastAPI 애플리케이션
    - HTTP 클라이언트 (httpx)로 다른 서비스 호출
    - 요청/응답 변환 (DTO)
    - 에러 처리 및 재시 로직

- [ ] **Task 2.4**: Service Registry 구현
  - File(s): `services/api-gateway/service_registry.py`, `services/api-gateway/config.py`
  - Goal: Test 2.2 통과
  - Details:
    - 환경 변수 기반 서비스 주소 설정
    - 헬스 체크 엔드포인트 (`/health`)
    - Circuit Breaker 패턴 ( resilience library)
    - 요청 로깅 및 추적

- [ ] **Task 2.5**: 인증 미들웨어
  - File(s): `services/api-gateway/middleware/auth.py`
  - Goal: 보안 강화
  - Details:
    - JWT 토큰 검증 (선택사항)
    - API Key 인증
    - CORS 설정

- [ ] **Task 2.6**: 기존 Flask 라우팅 이전
  - File(s): `services/api-gateway/routers/kr.py` (from `app/routes/kr_market.py`)
  - Goal: 기존 API 호환성 유지
  - Details:
    - Blueprint → FastAPI Router 변환
    - 응답 포맷 일치
    - 버전 관리 (`/v1/`, `/v2/`)

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 2.7**: 코드 품질 개선
  - Files: Phase 2의 모든 코드
  - Checklist:
    - [ ] 의존성 주입 (DependencyInjector)
    - [ ] 환경 설정 분리 (Pydantic Settings)
    - [ ] 로깅 표준화 (JSON 포맷)
    - [ ] 에러 응답 표준화 (HTTPException)

#### Quality Gate ✋

**⚠️ STOP: Do NOT proceed to Phase 3 until ALL checks pass**

**TDD Compliance**:
- [ ] Red-Green-Refactor 사이클 준수
- [ ] Coverage ≥80% for API Gateway

**Build & Tests**:
```bash
# API Gateway Test
pytest tests/integration/api/ --cov=services/api-gateway

# Service Discovery Test
pytest tests/unit/services/ --cov=services/api-gateway

# Manual Test
docker-compose up api-gateway
curl http://localhost:8000/api/kr/signals  # Should proxy to VCP service
```

**Functionality**:
- [ ] 모든 기존 API endpoint가 정상 동작
- [ ] 서비스 장애 시 graceful degradation
- [ ] 응답 시간 < 200ms (proxy 오버헤드 < 50ms)

---

### Phase 3: VCP Scanner Service Separation
**Goal**: VCP 패턴 감지 로직을 독립 FastAPI 서비스로 분리합니다.
**Estimated Time**: 8 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 3.1**: VCP Scanner 서비스 API 테스트
  - File(s): `tests/integration/services/test_vcp_scanner_api.py`
  - Details:
    - `POST /scan` - VCP 스캔 요청
    - `GET /signals` - 결과 조회
    - `GET /signals/{id}` - 단일 시그널 조회
    - WebSocket으로 실시간 스캔 진행률

- [ ] **Test 3.2**: SmartMoneyScreener 로직 단위 테스트
  - File(s): `tests/unit/vcp/test_screener.py`
  - Details:
    - `detect_vcp_pattern()` - VCP 패턴 감지
    - `_calculate_score()` - 수급 점수 계산
    - `generate_signals()` - 시그널 생성

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 3.3**: FastAPI VCP Scanner 서비스
  - File(s): `services/vcp-scanner/main.py`, `services/vcp-scanner/scanner.py`
  - Details:
    - FastAPI 앱 구조
    - `screener.py` → `scanner.py`로 리팩토링
    - DB Repository 연동
    - WebSocket 진행률 스트리밍

- [ ] **Task 3.4**: Celery Task로 VCP 스캔 비동기화
  - File(s): `services/vcp-scanner/tasks.py`, `services/vcp-scanner/worker.py`
  - Details:
    - `@celery.task`로 VCP 스캔 래핑
    - 진행률 Redis pub/sub
    - 결과 DB 저장

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 3.5**: VCP 알고리즘 최적화
  - Details:
    - Vectorization (pandas/numpy)
    - 병렬 처리 (multiprocessing)
    - 캐싱 (Redis에 계산 결과)

#### Quality Gate ✋

**TDD Compliance**: Coverage ≥85% for VCP logic

**Validation**:
```bash
# Service Test
pytest tests/integration/services/test_vcp_scanner_api.py

# Unit Test
pytest tests/unit/vcp/ --cov=services/vcp-scanner

# Performance Test (100 stocks < 30s)
python scripts/benchmark_vcp_scan.py
```

---

### Phase 4: Signal Engine Service Separation
**Goal**: 종가베팅 V2 엔진을 독립 서비스로 분리하고, AI 분석을 비동기화합니다.
**Estimated Time**: 12 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 4.1**: Signal Engine API 테스트
  - File(s): `tests/integration/services/test_signal_engine_api.py`
  - Details:
    - `POST /generate` - 종가베팅 시그널 생성
    - `GET /signals/latest` - 최신 시그널 조회
    - `GET /signals/{date}` - 특정 날짜 시그널 조회

- [ ] **Test 4.2**: LLM Analyzer Mock 테스트
  - File(s): `tests/unit/ai/test_llm_analyzer.py`
  - Details:
    - Gemini API mock
    - 뉴스 감성 분석 로직
    - Rate limiting 로직

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 4.3**: FastAPI Signal Engine 서비스
  - File(s): `services/signal-engine/main.py`, `services/signal-engine/generator.py` (from `engine/generator.py`)
  - Details:
    - `engine/` → `services/signal-engine/`로 이전
    - DB Repository 연동
    - KRXCollector, EnhancedNewsCollector 이전

- [ ] **Task 4.4**: Celery Task로 AI 분석 비동기화
  - File(s): `services/signal-engine/tasks.py`
  - Details:
    - `analyze_with_ai()` Celery task
    - Rate limiting (Gemini API: 1 req/sec)
    - 재시시 로직 (exponential backoff)

- [ ] **Task 4.5**: LLM Analyzer 서비스 분리
  - File(s): `services/ai-analyzer/main.py`, `services/ai-analyzer/analyzer.py`
  - Details:
    - 독립 AI 분석 서비스
    - Gemini/GPT 클라이언트
    - API Key 관리 (Vault/환경변수)

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 4.6**: AI 분석 파이프라인 최적화
  - Details:
    - 배치 처리 (여러 종목 한 번에 분석)
    - 결과 캐싱 (Redis)
    - 실패 시 재시 큐

#### Quality Gate ✋

**TDD Compliance**: Coverage ≥85%

**Validation**:
```bash
# AI Analysis Test (with mock)
pytest tests/unit/ai/ --mock-gemini

# Integration Test
pytest tests/integration/services/test_signal_engine_api.py

# Rate Limiting Test
python scripts/test_gemini_rate_limit.py
```

---

### Phase 5: Celery Async Processing
**Goal**: 백그라운드 작업을 Celery로 비동기화하고, 작업 큐를 구성합니다.
**Estimated Time**: 12 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 5.1**: Celery Task 테스트
  - File(s): `tests/unit/tasks/test_celery_tasks.py`
  - Details:
    - VCP scan task
    - AI analysis task
    - Price update task
    - 에러 처리 및 재시

- [ ] **Test 5.2**: Celery Beat 스케줄 테스트
  - File(s): `tests/integration/celery/test_scheduled_tasks.py`
  - Details:
    - 매일 00:30 장 마감 후 데이터 수집
    - 매일 01:00 VCP 스캔
    - 매시간 실시간 가격 업데이트

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 5.3**: Celery 설정
  - File(s): `src/celery_app.py`, `src/celery_config.py`
  - Details:
    - Celery app 초기화
    - Redis broker 설정
    - Task 라우팅 (multiple queues)
    - Result backend 설정

- [ ] **Task 5.4**: Celery Tasks 구현
  - File(s): `src/tasks/vcp_tasks.py`, `src/tasks/data_tasks.py`, `src/tasks/ai_tasks.py`
  - Details:
    - `vcp_scan_task()` - VCP 전체 스캔
    - `collect_market_data_task()` - KRX/yfinance 데이터 수집
    - `analyze_with_ai_task()` - AI 분석
    - `update_prices_task()` - 실시간 가격 업데이트

- [ ] **Task 5.5**: Celery Beat 스케줄러
  - File(s): `src/scheduler.py`
  - Details:
    - `beat_schedule` 설정
    - 크론 표현식
    - Task 중복 방지 (lock)

- [ ] **Task 5.6**: Flower 모니터링
  - File(s): `docker-compose.yml` (flower service)
  - Details:
    - Celery Task 모니터링 UI
    - Worker 상태 확인
    - Task 성공/실패 추적

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 5.7**: Task 성능 최적화
  - Details:
    - Task chunking (대량 데이터 처리)
    - Worker별 전용 큐 (CPU vs I/O)
    - Task 타임아웃 설정

#### Quality Gate ✋

**TDD Compliance**: Coverage ≥80%

**Validation**:
```bash
# Celery Worker Test
celery -A src.celery_app worker --loglevel=info

# Beat Test
celery -A src.celery_app beat --loglevel=info

# Task Test
python scripts/test_celery_tasks.py
```

---

### Phase 6: Event Bus Implementation
**Goal**: Redis Pub/Sub 기반 이벤트 버스를 구현하여 서비스 간 느슨한 결합을 달성합니다.
**Estimated Time**: 14 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 6.1**: 이벤트 버스 테스트
  - File(s): `tests/unit/events/test_event_bus.py`
  - Details:
    - 이벤트 발행 (publish)
    - 이벤트 구독 (subscribe)
    - 이벤트 핸들러 등록
    - 직렬화/역직렬화

- [ ] **Test 6.2**: 이벤트 핸들러 통합 테스트
  - File(s): `tests/integration/events/test_event_handlers.py`
  - Details:
    - `MarketDataUpdated` → VCP Scanner 시작
    - `VCPSignalDetected` → AI Analyzer 시작
    - `AIAnalysisCompleted` → 시그널 업데이트

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 6.3**: 이벤트 버스 구현
  - File(s): `src/events/bus.py`, `src/events/base.py`
  - Details:
    - Redis Pub/Sub 래퍼
    - Pydantic 이벤트 모델
    - 이벤트 직렬화 (JSON)

- [ ] **Task 6.4**: 핵심 이벤트 정의
  - File(s): `src/events/events.py`
  - Details:
    - `MarketDataUpdated`
    - `VCPSignalDetected`
    - `SignalCreated`
    - `AIAnalysisCompleted`
    - `MarketStatusChanged`
    - `PriceUpdated`

- [ ] **Task 6.5**: 이벤트 핸들러 구현
  - File(s): `src/handlers/vcp_handler.py`, `src/handlers/signal_handler.py`
  - Details:
    - 이벤트 리스너
    - 비즈니스 로직 호출
    - 에러 처리

- [ ] **Task 6.6**: 서비스별 이벤트 통합
  - File(s): 각 서비스의 `main.py`
  - Details:
    - VCP Scanner: `VCPSignalDetected` 발행
    - AI Analyzer: `VCPSignalDetected` 구독 → `AIAnalysisCompleted` 발행
    - Chatbot: `SignalCreated` 구독 → 알림

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 6.7**: 이벤트 버스 추상화
  - Details:
    - Message Broker 인터페이스 (Redis ↔ RabbitMQ 전환 용이)
    - Dead Letter Queue
    - 이벤트 버전 관리

#### Quality Gate ✋

**TDD Compliance**: Coverage ≥80%

**Validation**:
```bash
# Event Bus Test
pytest tests/unit/events/ --cov=src/events

# Integration Test
python scripts/test_event_flow.py
```

---

### Phase 7: Caching & Optimization
**Goal**: Redis 캐싱 레이어를 도입하고, 시스템 전체 성능을 최적화합니다.
**Estimated Time**: 12 hours
**Status**: ⏳ Pending

#### Tasks

**🔴 RED: Write Failing Tests First**
- [ ] **Test 7.1**: 캐시 레이어 테스트
  - File(s): `tests/unit/cache/test_cache_layer.py`
  - Details:
    - Cache hit/miss
    - TTL 만료
    - Cache invalidation
    - 직렬화/역직렬화

- [ ] **Test 7.2**: 성능 벤치마크
  - File(s): `tests/performance/test_api_performance.py`
  - Details:
    - API 응답 시간 < 200ms
    - DB 쿼리 < 100ms
    - VCP 스캔 < 30s (100 종목)

**🟢 GREEN: Implement to Make Tests Pass**
- [ ] **Task 7.3**: 캐시 데코레이터 구현
  - File(s): `src/cache/decorators.py`, `src/cache/backend.py`
  - Details:
    - `@cache` 데코레이터
    - `@cache_async` 비동기 데코레이터
    - 키 생성 전략
    - TTL 설정

- [ ] **Task 7.4**: 자주 조회되는 데이터 캐싱
  - File(s): 각 Repository에 캐시 로직 추가
  - Details:
    - 종목 기본 정보 (TTL: 1시간)
    - 시그널 목록 (TTL: 5분)
    - 실시간 가격 (TTL: 1분)
    - Market Gate 상태 (TTL: 15분)

- [ ] **Task 7.5**: 데이터베이스 쿼리 최적화
  - File(s): `src/database/queries.py`, Alembic migration (indexes)
  - Details:
    - 인덱스 추가 (ticker, date, status)
    - 쿼리 최적화 (JOIN 제거, 서브쿼리 제거)
    - Connection Pool 튜닝

- [ ] **Task 7.6**: API 응답 최적화
  - File(s): 각 FastAPI 서비스
  - Details:
    - 응답 압축 (gzip)
    - 페이지네이션 (cursor-based)
    - 필드 선택 (GraphQL-like `fields` query param)

**🔵 REFACTOR: Clean Up Code**
- [ ] **Task 7.7**: 모니터링 및 메트릭
  - File(s): `src/monitoring/metrics.py`, `docker-compose.yml` (Prometheus, Grafana)
  - Details:
    - Prometheus exporter
    - Grafana 대시보드
    - 알림 규칙 (Alertmanager)

#### Quality Gate ✋

**TDD Compliance**: Coverage ≥80%

**Validation**:
```bash
# Cache Test
pytest tests/unit/cache/ --cov=src/cache

# Performance Test
python scripts/benchmark_api.py

# Load Test (locust)
locust -f tests/loadtests/locustfile.py
```

---

## ⚠️ Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **데이터 마이그레이션 누락** | Medium | High | 1) 마이그레이션 스크립트에 row count 검증 2) 더블 체크 메커니즘 (CSV vs DB) 3) 롤백 계획 (CSV 백업 유지) |
| **성능 저하 (DB 변환)** | Medium | Medium | 1) 인덱스 미리 생성 2) 쿼리 튜닝 (EXPLAIN ANALYZE) 3) 로드 테스트 (Locust) 4) 캐싱으로 부하 분산 |
| **Celery Worker 확장 문제** | Low | Medium | 1) Worker별 전용 큐 할당 (vcp, ai, price) 2) Flower 모니터링으로 상태 확인 3) 오토스케일링 (Kubernetes later) |
| **API 호환성 깨짐** | High | High | 1) 버전 관리 (/v1/, /v2/) 2) 기간 전환 (기존 Flask 병행 운영) 3) 통합 테스트 (E2E) 4) API 문서 자동화 (FastAPI) |
| **Redis 단일 장애점** | Low | High | 1) Redis Sentinel 고가용성 (Phase 8) 2) 페일오버 메커니즘 3) Redis 데이터持久化 (AOF) |
| **AI API Rate Limiting** | High | Medium | 1) Celery로 순차 처리 (1 req/sec) 2) 재시 로직 (exponential backoff) 3) Rate Limiter (Redis) 4) 예외 처리 및 알림 |
| **이벤트 버스 메시지 유실** | Medium | Medium | 1) Dead Letter Queue 2) 메시지 영속화 (Redis AOF) 3) 재시 큐 4) 모니터링 (메시지 처리량) |
| **Docker 볼륨 성능** | Low | Low | 1) named volumes 사용 2) 호스트 마운트 (개발 환경) 3) 볼륨 최적화 (trim) |

---

## 🔄 Rollback Strategy

### If Phase 1 Fails (Database Migration)
**Steps to revert**:
1. PostgreSQL 컨테이너 중지: `docker-compose down postgres`
2. 기존 CSV/JSON 파일 확인: `ls -la data/`
3. Flask app 설정 변경: `USE_DATABASE = False` (환경변수)
4. 기존 `screener.py`, `signal_tracker.py`의 CSV 읽기 로직 사용
5. 마이그레이션 스크립트 롤백: `python scripts/migrate_db_to_csv.py`

### If Phase 2 Fails (API Gateway)
**Steps to revert**:
1. FastAPI API Gateway 중지
2. 기존 Flask 앱 시작: `python flask_app.py`
3. Nginx 라우팅 변경: `/api/*` → Flask:5001 (FastAPI:8000 제거)
4. 기존 `app/routes/` 사용

### If Phase 3 Fails (VCP Scanner)
**Steps to revert**:
1. VCP Scanner 서비스 중지
2. API Gateway에서 로컬 `screener.py` 호출로 복귀
3. Celery Task를 동기 함수 호출로 변경

### If Phase 4 Fails (Signal Engine)
**Steps to revert**:
1. Signal Engine 서비스 중지
2. 기존 `engine/generator.py`를 API Gateway에서 직접 호출
3. AI 분석 동기화 (GPT/Gemini API 직접 호출)

### If Phase 5 Fails (Celery)
**Steps to revert**:
1. Celery Worker 중지
2. 기존 `scheduler.py` 사용 (cron + 직접 호출)
3. 동기 함수로 복귀

### If Phase 6 Fails (Event Bus)
**Steps to revert**:
1. 이벤트 버스 중지
2. 직접 함수 호출로 복귀 (HTTP REST API)
3. 각 서비스의 REST API 사용

### If Phase 7 Fails (Caching)
**Steps to revert**:
1. 캐시 데코레이터 제거 (no-op으로 교체)
2. 직접 DB 조회
3. Redis는 Celery용으로만 계속 사용

---

## 📊 Progress Tracking

### Completion Status
| Phase | Status | Progress | Time Spent |
|-------|--------|----------|------------|
| Phase 1: Database | ⏳ Pending | 0% | - |
| Phase 2: API Gateway | ⏳ Pending | 0% | - |
| Phase 3: VCP Scanner | ⏳ Pending | 0% | - |
| Phase 4: Signal Engine | ⏳ Pending | 0% | - |
| Phase 5: Celery Async | ⏳ Pending | 0% | - |
| Phase 6: Event Bus | ⏳ Pending | 0% | - |
| Phase 7: Caching | ⏳ Pending | 0% | - |

**Overall Progress**: 0% complete (0/7 phases)

### Timeline Tracking
| Phase | Estimated | Actual | Variance | Start Date | End Date |
|-------|-----------|--------|----------|------------|----------|
| Phase 1 | 12h | - | - | TBD | TBD |
| Phase 2 | 10h | - | - | TBD | TBD |
| Phase 3 | 8h | - | - | TBD | TBD |
| Phase 4 | 12h | - | - | TBD | TBD |
| Phase 5 | 12h | - | - | TBD | TBD |
| Phase 6 | 14h | - | - | TBD | TBD |
| Phase 7 | 12h | - | - | TBD | TBD |
| **Total** | **80h** | **-** | **-** | **-** | **-** |

---

## 📝 Notes & Learnings

### Implementation Notes
*Update as you progress through phases*

### Blockers Encountered
*Document any blocking issues and their resolutions*

### Improvements for Future Plans
*What would you do differently next time?*

---

## 📚 References

### Documentation
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/)
- [Celery User Guide](https://docs.celeryq.dev/)
- [TimescaleDB Docs](https://docs.timescale.com/)
- [Redis Pub/Sub](https://redis.io/docs/manual/pubsub/)

### Architecture Patterns
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Event-Driven Architecture](https://www.ibm.com/topics/event-driven-architecture)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)

### Tools
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [Pydantic Settings](https://docs.pydantic.com/latest/concepts/pydantic_settings/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)

---

## ✅ Final Checklist

**Before marking plan as COMPLETE**:
- [ ] All 7 phases completed with quality gates passed
- [ ] Full integration testing performed (E2E tests pass)
- [ ] Documentation updated (API docs, architecture diagram)
- [ ] Performance benchmarks meet targets (API < 200ms, VCP scan < 30s)
- [ ] Security review completed (no exposed credentials, proper access control)
- [ ] Monitoring operational (Prometheus + Grafana dashboards)
- [ ] Backup/restore tested (DB backup/restore verified)
- [ ] Rollback plan tested (each phase rollback verified)
- [ ] Stakeholders notified (team briefed on new architecture)
- [ ] Plan document archived for future reference

---

**Plan Status**: 🔄 In Progress
**Next Action**: Phase 1 - Database Layer Introduction
**Blocked By**: None
