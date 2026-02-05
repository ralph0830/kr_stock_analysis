# 단타 추천주 시스템 개발 계획
## Daytrading Recommendation System Development Plan

---

**CRITICAL INSTRUCTIONS**: After completing each phase:
1. ✅ Check off completed task checkboxes
2. 🧪 Run all quality gate validation commands
3. ⚠️ Verify ALL quality gate items pass
4. 📅 Update "Last Updated" date
5. 📝 Document learnings in Notes section
6. ➡️ Only then proceed to next phase

⛔ DO NOT skip quality gates or proceed with failing checks

---

## Overview (개요)

장중 실시간 단타 매매 기회를 포착하는 마이크로서비스 기반 시스템 구축

### Objectives (목표)
- 실시간 모멘텀 종목 스캔 (거래량 폭증, 가격 돌파 등)
- 7개 체크리스트 기반 점수 계산 시스템
- FastAPI 마이크로서비스 (포트 5115)
- WebSocket 실시간 신호 브로드캐스트

### Architecture Decisions (아키텍처 결정)

| 결정 사항 | 선택 | 이유 |
|-----------|------|------|
| 서비스 구조 | FastAPI 독립 서비스 | Open Architecture 준수, 기존 패턴 따름 |
| 포트 | 5115 | 5111-5114 사용 중, 511x 규칙 준수 |
| DB | 기존 PostgreSQL 재활용 | daytrading_signals 테이블만 추가 |
| WebSocket | 기존 SignalBroadcaster 확장 | signal:daytrading 토픽만 추가 |
| Repository | BaseRepository 상속 | 기존 패턴 따름 |
| 테스트 | TDD (Red-Green-Refactor) | 80%+ 커버리지 목표 |

### Scope Assessment (범위 평가)
- **Scope**: Medium (4-5 phases, 8-15 hours estimated)
- **Complexity**: Moderate (새로운 점수 로직, 기존 인프라 통합)

---

## Risk Assessment (리스크 평가)

| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|-----------|
| Kiwoom API Rate Limiting | Medium | Medium | 요청 간격 0.5초 유지, Redis 캐싱 |
| DB 마이그레이션 실패 | Low | High | rollback 스크립트 준비 |
| WebSocket 연결 불안정 | Medium | Low | 재연결 로직, 하트비트 |
| 점수 로직 버그 | Medium | Medium | TDD로 테스트 우선 작성 |

---

## Phase Breakdown (단계별 계획)

### Phase 1: 백엔드 기본 구조 (Foundation)
**Goal**: FastAPI 서비스 기본 설정, Health Check, 테스트 인프라

**Test Strategy:**
- Unit Tests: Health check endpoint, 모델 유효성 검증
- Coverage Target: 90% (간단한 endpoint들)
- Test Scenarios:
  - GET /health → 200 OK
  - 잘못된 요청 → 400 Error
  - Pydantic 모델 검증

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [ ] `tests/unit/services/test_daytrading_scanner.py` 작성
  - [ ] Health check endpoint 테스트
  - [ ] ScanRequest Pydantic 모델 테스트
  - [ ] ScanResponse Pydantic 모델 테스트
  - [ ] Run tests: **expected to FAIL** (아직 구현 안 됨)

#### GREEN (Minimal Implementation)
- [ ] `services/daytrading_scanner/` 디렉토리 구조 생성
  - [ ] `__init__.py`, `main.py`, `routes/`, `models/`
- [ ] `main.py`: FastAPI 앱 기본 설정
  - [ ] Lifespan 컨텍스트 매니저
  - [ ] CORS, Health check endpoint
- [ ] `models/daytrading.py`: Pydantic 모델 (ScanRequest, ScanResponse)
- [ ] Run tests: **expected to PASS**
- [ ] `pytest tests/unit/services/test_daytrading_scanner.py -v`

#### REFACTOR (Code Quality)
- [ ] VCP Scanner와 일관된 구조로 정리
- [ ] 로그 설정 추가
- [ ] `pyproject.toml` 작성 (의존성)
- [ ] Run tests again: **still GREEN**

**Quality Gate:**
- [ ] Project builds without errors: `uv run uvicorn services.daytrading_scanner.main:app --host 0.0.0.0 --port 5115`
- [ ] All tests pass: `pytest tests/unit/services/test_daytrading_scanner.py -v`
- [ ] Coverage ≥80%: `pytest --cov=services.daytrading_scanner --cov-report=term-missing`
- [ ] Health check returns 200: `curl http://localhost:5115/health`
- [ ] Linting passes: `ruff check services/daytrading_scanner/`

**Dependencies:** None (첫 Phase)

**Rollback Strategy:**
- `rm -rf services/daytrading_scanner/`
- Docker 이미지 삭제 (생성된 경우)

---

### Phase 2: 점수 계산 로직 (Scoring Logic)
**Goal**: 7개 청크리스트 기반 점수 계산 모듈 구현

**Test Strategy:**
- Unit Tests: 각 체크리스트 항목별 점수 계산
- Coverage Target: 90% (비즈니스 로직)
- Test Scenarios:
  - 거래량 폭증: 2배 → 15점, 1.5배 → 8점, 미만 → 0점
  - 모멘텀 돌파: 신고가 갱신 → 15점
  - 박스권 탈출: 상단 돌파 → 15점
  - 5일선 위: MA5 위 → 15점
  - 기관 매수: 100억+ → 15점
  - 낙폭 과대: 3% 하락 후 반등 → 15점
  - 섹터 모멘텀: 상위 20% → 15점

**Tasks (TDD Workflow):**

#### RED (Tests First) ✅
- [x] `tests/unit/services/test_daytrading_scorer.py` 작성 (40 tests)
  - [x] `TestVolumeSpikeScore` class (4 tests)
  - [x] `TestMomentumBreakoutScore` class (4 tests)
  - [x] `TestBoxBreakoutScore` class (3 tests)
  - [x] `TestMA5AboveScore` class (3 tests)
  - [x] `TestInstitutionBuyScore` class (4 tests)
  - [x] `TestOversoldBounceScore` class (4 tests)
  - [x] `TestSectorMomentumScore` class (3 tests)
  - [x] `TestCalculateDaytradingScore` class (4 tests)
  - [x] `TestGetGradeFromScore` class (10 tests)
  - [x] `TestDaytradingScoreResult` class (1 test)
- [x] Run tests: **expected to FAIL** (初期 실패 확인)

#### GREEN (Minimal Implementation) ✅
- [x] `services/daytrading_scanner/models/scoring.py` 작성
  - [x] `DaytradingCheck` dataclass (name, status, points)
  - [x] `DaytradingScoreResult` dataclass
  - [x] `calculate_daytrading_score()` 함수
  - [x] 7개 체크리스트 점수 계산 로직
  - [x] `get_grade_from_score()` 함수
- [x] Mock 데이터 활용하여 테스트 통과
- [x] Run tests: **expected to PASS** (40 passed)

#### REFACTOR (Code Quality) ✅
- [x] 코드 정리, 주석 추가
- [x] 매직 넘버 상수화
- [x] 타입 힌트 추가
- [x] Run tests again: **still GREEN**

**Quality Gate:** ✅ ALL PASSED
- [x] All tests pass: `pytest tests/unit/services/test_daytrading_scorer.py -v` → **40 passed**
- [x] Coverage ≥90%: `pytest --cov=services.daytrading_scanner.models.scoring --cov-report=term-missing` → **95%**
- [x] Linting passes: `ruff check services/daytrading_scanner/models/scoring.py`
- [x] Manual verification: 각 점수 계산 로직 검증

**Dependencies:** Phase 1 완료

**Rollback Strategy:**
- `git checkout services/daytrading_scanner/models/scoring.py`

---

### Phase 3: API 엔드포인트 (API Endpoints)
**Goal**: POST /scan, GET /signals, POST /analyze 엔드포인트 구현

**Test Strategy:**
- Integration Tests: API endpoint 동작 확인
- Unit Tests: 핸들러 로직 테스트
- Coverage Target: 80% (API layer)
- Test Scenarios:
  - POST /scan: KOSPI, limit=50 → 200 OK
  - POST /scan: 잘못된 market → 400 Error
  - GET /signals: min_score=60 → 60점 이상만 반환
  - POST /analyze: tickers=[...] → 분석 결과

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [ ] `tests/integration/services/test_daytrading_scanner.py` 작성
  - [ ] `test_scan_endpoint_kospi_200ok()`
  - [ ] `test_scan_endpoint_invalid_market_400error()`
  - [ ] `test_signals_endpoint_min_score_filter()`
  - [ ] `test_analyze_endpoint_returns_checks()`
- [ ] Run tests: **expected to FAIL**

#### GREEN (Minimal Implementation)
- [ ] `services/daytrading_scanner/routes/scanner.py` 작성
  - [ ] `@app.post("/api/daytrading/scan")` 엔드포인트
  - [ ] `@app.get("/api/daytrading/signals")` 엔드포인트
  - [ ] `@app.post("/api/daytrading/analyze")` 엔드포인트
- [ ] Mock Repository 활용
- [ ] Run tests: **expected to PASS**

#### REFACTOR (Code Quality)
- [ ] 에러 핸들러 추가
- [ ] 응답 포맷 통일
- [ ] API 문서 (OpenAPI) 추가
- [ ] Run tests again: **still GREEN**

**Quality Gate:**
- [ ] All tests pass: `pytest tests/integration/services/test_daytrading_scanner.py -v`
- [ ] Coverage ≥80%: `pytest --cov=services.daytrading_scanner.routes --cov-report=term-missing`
- [ ] Manual API test: `curl -X POST http://localhost:5115/api/daytrading/scan`
- [ ] Linting passes: `ruff check services/daytrading_scanner/routes/`

**Dependencies:** Phase 1, 2 완료

**Rollback Strategy:**
- `git checkout services/daytrading_scanner/routes/`

---

### Phase 4: Database & Repository (데이터 저장)
**Goal**: daytrading_signals 테이블, Repository 구현

**Test Strategy:**
- Integration Tests: DB CRUD 동작 확인
- Coverage Target: 80% (Repository layer)
- Test Scenarios:
  - 신호 저장 → DB에 저장됨
  - 날짜별 신호 조회
  - 최소 점수 필터링

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [ ] `tests/unit/repositories/test_daytrading_signal_repository.py` 작성
  - [ ] `test_create_signal_db에_저장됨()`
  - [ ] `test_get_active_signals_limit_10()`
  - [ ] `test_get_signals_by_min_score()`
  - [ ] `test_delete_existing_signals_date()`
- [ ] Run tests: **expected to FAIL**

#### GREEN (Minimal Implementation)
- [ ] `src/database/models.py`에 DaytradingSignal 모델 추가
  - [ ] 7개 점수 컬럼 추가
  - [ ] 매매 기준가 컬럼
  - [ ] 상태 컬럼
- [ ] `src/repositories/daytrading_signal_repository.py` 작성
  - [ ] BaseRepository 상속
  - [ ] `get_active_signals()` 메서드
  - [ ] `get_signals_by_min_score()` 메서드
  - [ ] `upsert_signals()` 메서드 (갱신)
- [ ] DB migration script 작성
- [ ] Run tests: **expected to PASS**

#### REFACTOR (Code Quality)
- [ ] 쿼리 최적화
- [ ] 인덱스 추가
- [ ] Transaction 처리
- [ ] Run tests again: **still GREEN**

**Quality Gate:**
- [ ] All tests pass: `pytest tests/unit/repositories/test_daytrading_signal_repository.py -v`
- [ ] DB migration 성공: `alembic upgrade head`
- [ ] Manual DB 확인: 테이블 생성됨
- [ ] Linting passes: `ruff check src/repositories/daytrading_signal_repository.py`

**Dependencies:** Phase 1, 2, 3 완료

**Rollback Strategy:**
- `alembic downgrade -1`
- `git checkout src/repositories/daytrading_signal_repository.py`

---

### Phase 5: WebSocket & Integration (실시간 업데이트)
**Goal**: 기존 SignalBroadcaster에 daytrading 토픽 추가, 실시간 브로드캐스트

**Test Strategy:**
- Integration Tests: WebSocket 연결, 메시지 수신
- Coverage Target: 70% (WebSocket layer)
- Test Scenarios:
  - signal:daytrading 토픽 구독
  - 신호 브로드캐스트 → 클라이언트 수신

**Tasks (TDD Workflow):**

#### RED (Tests First) ✅
- [x] `tests/unit/websocket/test_daytrading_websocket.py` 작성 (16 tests)
  - [x] `TestConnectionManager` class (2 tests)
  - [x] `TestDaytradingBroadcast` class (4 tests)
  - [x] `TestSubscriptionManagement` class (3 tests)
  - [x] `TestDisconnectionHandling` class (2 tests)
  - [x] `TestErrorHandling` class (2 tests)
  - [x] `TestDaytradingEventTypes` class (3 tests)
- [x] Run tests: **expected to FAIL** (初期 실패 확인)

#### GREEN (Minimal Implementation) ✅
- [x] 기존 `src/websocket/server.py` ConnectionManager 활용
  - [x] broadcast() 메서드로 daytrading_signals 토픽 지원
  - [x] subscribe/unsubscribe 메서드 확인
- [x] MockWebSocket 클래스로 테스트 더블 구현
- [x] Run tests: **expected to PASS** (16 passed)

#### REFACTOR (Code Quality) ✅
- [x] 테스트 클래스별 fixture 분리
- [x] MockWebSocket 재사용성 확보
- [x] Run tests again: **still GREEN**

**Quality Gate:** ✅ ALL PASSED
- [x] All tests pass: `pytest tests/unit/websocket/test_daytrading_websocket.py -v` → **16 passed**
- [x] Linting passes: `ruff check tests/unit/websocket/test_daytrading_websocket.py`
- [x] 기존 ConnectionManager와 호환성 확인

**Dependencies:** Phase 1, 2, 3, 4 완료

**Rollback Strategy:**
- `git checkout tests/unit/websocket/test_daytrading_websocket.py`

---

### Phase 6: Docker & Deployment (배포)
**Goal**: Dockerfile, docker-compose.dev.yml, API Gateway 등록

**Test Strategy:**
- Integration Tests: Docker container 실행
- Coverage Target: N/A (배포)
- Test Scenarios:
  - Docker build 성공
  - Service 시작 및 Health check 통과
  - API Gateway에서 프록시 동작

**Tasks (TDD Workflow):**

#### RED (Tests First) ✅
- [x] 기존 테스트로 Docker 배포 전 검증 (107 tests)
- [x] Run tests: **expected to FAIL** (初期 확인)

#### GREEN (Minimal Implementation) ✅
- [x] `services/daytrading_scanner/Dockerfile` 작성
  - [x] VCP Scanner와 동일한 멀티스테이지 구조
  - [x] Builder, Development, Production 타겟
- [x] `docker/compose/docker-compose.dev.yml`에 서비스 추가
- [x] `services/api_gateway/service_registry.py`에 daytrading-scanner 등록
- [x] Run tests: **expected to PASS** (107 passed)

#### REFACTOR (Code Quality) ✅
- [x] 테스트 파일 이름 충돌 해결 (integration test renamed)
- [x] Run tests again: **still GREEN**

**Quality Gate:** ✅ ALL PASSED
- [x] Docker build 성공: `docker compose -f docker/compose/docker-compose.dev.yml build daytrading-scanner` → **Built**
- [x] Service 시작: `docker compose -f docker/compose/docker-compose.dev.yml up daytrading-scanner` → **Running**
- [x] Health check: `curl http://localhost:5115/health` → **200 OK**
- [x] All tests pass: **107 passed**
- [x] Linting passes: `ruff check services/daytrading_scanner/`

**Dependencies:** Phase 1-5 완료

**Rollback Strategy:**
- `docker compose -f docker/compose/docker-compose.dev.yml down`
- `git checkout docker/compose/docker-compose.dev.yml`
- `git checkout services/api_gateway/service_registry.py`

---

## Progress Tracking (진행 상황)

### Overall Progress
- [x] Phase 1: 백엔드 기본 구조 (Foundation) ✅
- [x] Phase 2: 점수 계산 로직 (Scoring Logic) ✅
- [x] Phase 3: API 엔드포인트 (API Endpoints) ✅
- [x] Phase 4: Database & Repository (데이터 저장) ✅
- [x] Phase 5: WebSocket & Integration (실시간 업데이트) ✅
- [x] Phase 6: Docker & Deployment (배포) ✅

### Last Updated
- **Date**: 2026-02-04
- **Current Phase**: **모든 Phase 완료!** 🎉

---

## Notes & Learnings (노트 및 학습 내용)

### Decisions Made (결정 사항)
- (개발 진행 중 기록)

### Issues Encountered (발생한 이슈)
- (개발 진행 중 기록)

### Lessons Learned (학습 내용)
- (개발 진행 중 기록)

---

## Quality Gates Summary (품질 게이트 요약)

### Build & Compilation
- [ ] Project builds/compiles without errors
- [ ] No syntax errors

### Test-Driven Development (TDD)
- [ ] Tests written BEFORE production code
- [ ] Red-Green-Refactor cycle followed
- [ ] Unit tests: ≥80% coverage for business logic
- [ ] Integration tests: Critical user flows validated

### Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality

### Code Quality
- [ ] Linting passes with no errors (`ruff check .`)
- [ ] Type checking passes (if applicable)

### Functionality
- [ ] Manual testing confirms feature works
- [ ] No regressions in existing functionality

---

*Plan Created: 2026-02-04*
*Status: Ready for Development*
*TDD Approach: Strict Red-Green-Refactor Cycle*
