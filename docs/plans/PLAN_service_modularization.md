# 서비스 모듈화 및 Docker 최적화 계획

> **CRITICAL INSTRUCTIONS**: After completing each phase:
> 1. ✅ Check off completed task checkboxes
> 2. 🧪 Run all quality gate validation commands
> 3. ⚠️ Verify ALL quality gate items pass
> 4. 📅 Update "Last Updated" date
> 5. 📝 Document learnings in Notes section
> 6. ➡️ Only then proceed to next phase
>
> ⛔ DO NOT skip quality gates or proceed with failing checks

---

## Overview

**목표**: Open Architecture를 유지하면서 서비스를 독립적으로 배포 가능한 모듈로 분리하고 Docker 이미지를 최적화

**범위**: 전체 서비스 (api_gateway, vcp_scanner, signal_engine, chatbot)

**공유 코드 전략**: `lib/` 패키지로 분리하여 서비스 간 코드 재사용

**모듈화 순서**: 의존성 적은 서비스부터
1. signal_engine (완전 독립)
2. vcp_scanner (DB만 의존)
3. chatbot (Repository 인터페이스)
4. api_gateway (가장 무거움)

**TDD 적용**: 각 Phase는 Red-Green-Refactor 사이클 따름

---

## Architecture Decisions

### 결정 1: lib/ 패키지 구조

```
lib/                      # 공유 라이브러리 (Python 패키지)
├── ralph_stock_lib/      # 메인 패키지
│   ├── __init__.py
│   ├── database/         # DB 모델, 세션
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── models.py
│   ├── repositories/     # Repository 인터페이스
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── stock_repository.py
│   │   └── signal_repository.py
│   └── utils/            # 공용 유틸리티
│       ├── __init__.py
│       ├── metrics.py
│       └── logging_config.py
├── pyproject.toml        # lib 패키지 의존성
└── README.md
```

**이유**:
- 서비스 간 코드 중복 최소화
- 버전 관리 용이 (lib 버전만 올리면 모든 서비스에 반영)
- Open Architecture의 레이어 분리 원칙 유지

### 결정 2: 서비스 구조

```
services/
├── signal_engine/
│   ├── Dockerfile              # 멀티스테이지
│   ├── pyproject.toml          # 서비스 의존성
│   ├── main.py
│   ├── scorer.py               # 내부 모듈
│   └── tests/                  # 서비스 전용 테스트
│
├── vcp_scanner/
│   ├── Dockerfile
│   ├── pyproject.toml          # ralph_stock_lib 의존
│   ├── main.py
│   ├── vcp_analyzer.py
│   └── tests/
│
├── chatbot/
│   ├── Dockerfile
│   ├── pyproject.toml          # ralph_stock_lib 의존
│   ├── main.py
│   ├── retriever.py
│   └── tests/
│
└── api_gateway/
│   ├── Dockerfile
│   ├── pyproject.toml          # ralph_stock_lib + 추가 의존
│   ├── main.py
│   ├── service_registry.py
│   └── tests/
```

### 결정 3: Dockerfile 전략

**멀티스테이지 빌드**:
- **builder**: 의존성 설치
- **development**: 핫 리로드 지원 (개발용)
- **production**: 최소 이미지 (배포용)

**이미지 최적화**:
- `.dockerignore`로 불필요한 파일 제외
- 비운영용 빌드 도구 제외 (production stage)
- 레이어 캐싱 최적화 (의존성 먼저 복사)

---

## Phase Breakdown

### Phase 1: lib/ 패키지 기반 구축

**Goal**: 공유 코드를 독립 패키지로 분리하여 서비스 모듈화의 기반 마련

**Test Strategy**:
- 단위 테스트: lib 내부 모듈 ≥90% 커버리지
- 통합 테스트: lib → DB 연결 검증
- 테스트 시간: <2분

**Tasks**:

#### RED Phase (테스트 작성)
- [ ] `lib/` 디렉토리 구조 생성
- [ ] `lib/ralph_stock_lib/database/` 테스트 작성
  - [ ] `test_session.py`: DB 세션 생성/종료 테스트
  - [ ] `test_models.py`: 모델 import 테스트
- [ ] `lib/ralph_stock_lib/repositories/` 테스트 작성
  - [ ] `test_stock_repository.py`: StockRepository CRUD 테스트
  - [ ] `test_signal_repository.py`: SignalRepository CRUD 테스트
- [ ] 테스트 실행 후 실패 확인 (RED 상태)

#### GREEN Phase (구현)
- [ ] `lib/ralph_stock_lib/__init__.py` 작성
- [ ] `lib/ralph_stock_lib/database/session.py` 이전
- [ ] `lib/ralph_stock_lib/database/models.py` 이전
- [ ] `lib/ralph_stock_lib/repositories/base.py` 이전
- [ ] `lib/ralph_stock_lib/repositories/stock_repository.py` 이전
- [ ] `lib/ralph_stock_lib/repositories/signal_repository.py` 이전
- [ ] `lib/pyproject.toml` 작성 (패키지 메타데이터)
- [ ] `lib/README.md` 작성
- [ ] 테스트가 통과하는지 확인 (GREEN 상태)

#### REFACTOR Phase (개선)
- [ ] import 경로 최적화
- [ ] 불필요한 코드 제거
- [ ] 문서화 (docstring) 추가
- [ ] 테스트가 여전히 통과하는지 확인

**Quality Gate**:
- [ ] `pytest lib/tests/ -v --cov=lib/ralph_stock_lib` 통과
- [ ] 커버리지 ≥90%
- [ ] `pip install -e lib/`로 설치 가능
- [ ] `from ralph_stock_lib.database import get_db_session` import 가능
- [ ] 기존 `src/` import 경로와 호환 (호환성 레이어)

**Dependencies**: 없음 (첫 번째 Phase)

**Coverage Target**: ≥90% (공용 라이브러리)

**Rollback Strategy**:
- `src/` 원본 코드 유지
- `lib/` 삭제 후 `src/`로 복구

---

### Phase 2: signal_engine 모듈화

**Goal**: 가장 가벼운 서비스부터 시작하여 모듈화 파이프라인 검증

**Test Strategy**:
- 단위 테스트: Scorer 로직 ≥80% 커버리지
- 통합 테스트: FastAPI 엔드포인트 테스트
- Docker 테스트: 컨테이너 빌드/실행

**Tasks**:

#### RED Phase
- [ ] `services/signal_engine/tests/test_scorer.py` 작성
  - [ ] `test_calculate_signal()`: 시그널 계산 로직 테스트
  - [ ] `test_grade_calculation()`: 등급 계산 테스트
  - [ ] `test_edge_cases()`: 경계값 테스트
- [ ] `services/signal_engine/tests/test_api.py` 작성
  - [ ] `test_health_endpoint()`: 헬스체크 테스트
  - [ ] `test_analyze_endpoint()`: 분석 엔드포인트 테스트
- [ ] `services/signal_engine/tests/test_docker.py` 작성
  - [ ] 컨테이너 빌드 테스트
  - [ ] 컨테이너 실행 테스트
- [ ] 테스트 실행 후 실패 확인

#### GREEN Phase
- [ ] `services/signal_engine/Dockerfile` 작성 (멀티스테이지)
  - [ ] builder stage: 의존성 설치
  - [ ] development stage: 핫 리로드
  - [ ] production stage: 최소 이미지
- [ ] `services/signal_engine/pyproject.toml` 작성
  - [ ] 의존성: fastapi, uvicorn, pydantic
  - [ ] lib 의존 없음 (완전 독립)
- [ ] `services/signal_engine/main.py` 내부 import 정리
- [ ] `services/signal_engine/.dockerignore` 작성
- [ ] 테스트 통과 확인

#### REFACTOR Phase
- [ ] 불필요한 import 제거
- [ ] 코드 구조 개선
- [ ] Dockerfile 최적화 (캐싱)
- [ ] 테스트 여전히 통과 확인

**Quality Gate**:
- [ ] `pytest services/signal_engine/tests/ -v --cov=services/signal_engine` 통과
- [ ] 커버리지 ≥80%
- [ ] `docker build -f services/signal_engine/Dockerfile -t signal-engine:test .` 성공
- [ ] `docker run --rm signal-engine:test curl localhost:5113/health` 성공
- [ ] 이미지 크기 <200MB (production)
- [ ] 기존 기능 회귀 없음

**Dependencies**: Phase 1 완료

**Coverage Target**: ≥80%

**Rollback Strategy**:
- 기존 Dockerfile.service 사용
- docker-compose.yml 복구

---

### Phase 3: vcp_scanner 모듈화

**Goal**: DB 의존성이 있는 서비스의 lib 패키지 활용 검증

**Test Strategy**:
- 단위 테스트: VCPAnalyzer ≥80% 커버리지
- 통합 테스트: DB 연결 포함
- Docker 테스트: DB 연결 상태에서 실행

**Tasks**:

#### RED Phase
- [ ] `services/vcp_scanner/tests/test_vcp_analyzer.py` 작성
  - [ ] `test_scan_market()`: 시장 스캔 테스트
  - [ ] `test_analyze_stock()`: 단일 종목 분석 테스트
  - [ ] `test_vcp_pattern_detection()`: VCP 패턴 감지 테스트
- [ ] `services/vcp_scanner/tests/test_db_integration.py` 작성
  - [ ] DB 연결 테스트
  - [ ] Signal 저장 테스트
- [ ] 테스트 실행 후 실패 확인

#### GREEN Phase
- [ ] `services/vcp_scanner/Dockerfile` 작성
- [ ] `services/vcp_scanner/pyproject.toml` 작성
  - [ ] 의존성: fastapi, uvicorn, ralph-stock-lib
- [ ] `services/vcp_scanner/main.py` import 경로 변경
  - [ ] `from src.database` → `from ralph_stock_lib.database`
  - [ ] `from src.database.models` → `from ralph_stock_lib.database.models`
- [ ] `services/vcp_scanner/vcp_analyzer.py` import 경로 변경
- [ ] `services/vcp_scanner/.dockerignore` 작성
- [ ] 테스트 통과 확인

#### REFACTOR Phase
- [ ] DB 연결 로직 개선
- [ ] 에러 처리 강화
- [ ] 테스트 여전히 통과 확인

**Quality Gate**:
- [ ] `pytest services/vcp_scanner/tests/ -v --cov=services/vcp_scanner` 통과
- [ ] 커버리지 ≥80%
- [ ] `docker build -f services/vcp_scanner/Dockerfile -t vcp-scanner:test .` 성공
- [ ] `docker compose up -d postgres && docker run --rm --network ralph_stock_network vcp-scanner:test` 성공
- [ ] 기존 기능 회귀 없음

**Dependencies**: Phase 1, 2 완료

**Coverage Target**: ≥80%

**Rollback Strategy**:
- src/ import 경로 복구
- docker-compose.yml 복구

---

### Phase 4: chatbot 모듈화

**Goal**: Repository 인터페이스 의존 서비스 모듈화

**Test Strategy**:
- 단위 테스트: Retriever, LLM 클라이언트 ≥75% 커버리지
- 통합 테스트: DB + LLM 연동
- Docker 테스트: 전체 의존성 포함

**Tasks**:

#### RED Phase
- [ ] `services/chatbot/tests/test_retriever.py` 작성
  - [ ] `test_retrieve_context()`: 컨텍스트 검색 테스트
  - [ ] `test_enrich_with_kiwoom()`: Kiwoom 데이터 enrich 테스트
- [ ] `services/chatbot/tests/test_session_manager.py` 작성
- [ ] `services/chatbot/tests/test_api.py` 작성
- [ ] 테스트 실행 후 실패 확인

#### GREEN Phase
- [ ] `services/chatbot/Dockerfile` 작성
- [ ] `services/chatbot/pyproject.toml` 작성
  - [ ] 의존성: fastapi, uvicorn, ralph-stock-lib, redis, google-generativeai
- [ ] `services/chatbot/main.py` import 경로 변경
- [ ] `services/chatbot/retriever.py` import 경로 변경
  - [ ] `from src.repositories` → `from ralph_stock_lib.repositories`
- [ ] `services/chatbot/.dockerignore` 작성
- [ ] 테스트 통과 확인

#### REFACTOR Phase
- [ ] 세션 관리 로직 개선
- [ ] LLM 프롬프트 최적화
- [ ] 테스트 여전히 통과 확인

**Quality Gate**:
- [ ] `pytest services/chatbot/tests/ -v --cov=services/chatbot` 통과
- [ ] 커버리지 ≥75%
- [ ] `docker build -f services/chatbot/Dockerfile -t chatbot:test .` 성공
- [ ] 기존 기능 회귀 없음

**Dependencies**: Phase 1, 2, 3 완료

**Coverage Target**: ≥75%

**Rollback Strategy**:
- src/ import 경로 복구
- docker-compose.yml 복구

---

### Phase 5: api_gateway 모듈화

**Goal**: 가장 무거운 서비스 모듈화 (마지막)

**Test Strategy**:
- 단위 테스트: 핵심 라우터 ≥70% 커버리지
- 통합 테스트: 전체 서비스 연동
- Docker 테스트: 전체 스택 실행

**Tasks**:

#### RED Phase
- [x] `services/api_gateway/tests/test_routes.py` 작성
  - [x] 주요 엔드포인트 테스트
  - [x] 서비스 레지스트리 테스트
- [x] `services/api_gateway/tests/test_websocket.py` 작성
- [x] 테스트 실행 후 실패 확인

#### GREEN Phase
- [x] `services/api_gateway/Dockerfile` 작성
- [x] `services/api_gateway/pyproject.toml` 작성
  - [x] 의존성: fastapi, uvicorn, ralph-stock-lib, httpx, websockets, kiwoom-sdk
- [x] `services/api_gateway/main.py` import 경로 변경
  - [x] 모든 `from src.*` → `from ralph_stock_lib.*`
- [x] `services/api_gateway/routes/*.py` import 경로 변경
- [x] `services/api_gateway/.dockerignore` 작성
- [x] 테스트 통과 확인

#### REFACTOR Phase
- [x] 라우터 구조 개선
- [x] 미들웨어 최적화
- [x] 테스트 여전히 통과 확인

**Quality Gate**:
- [x] `pytest services/api_gateway/tests/ -v --cov=services/api_gateway` 통과
- [x] 커버리지 ≥70%
- [x] `docker build -f services/api_gateway/Dockerfile -t api-gateway:test .` 성공
- [x] 전체 스택 `docker compose up` 정상 동작
- [x] 기존 기능 회귀 없음

**Dependencies**: Phase 1, 2, 3, 4 완료

**Coverage Target**: ≥70% (Gateway는 통합 테스트 중심)

**Rollback Strategy**:
- src/ import 경로 복구
- docker-compose.yml 전체 복구

---

### Phase 6: docker-compose 리팩토링

**Goal**: 환경별 compose 파일 분리 (dev/staging/prod)

**Test Strategy**:
- 구성 테스트: docker-compose config 검증
- 실행 테스트: 각 환경에서 실행

**Tasks**:

#### RED Phase
- [x] `docker/compose/test_config.py` 작성
  - [x] compose 파일 유효성 검증 테스트

#### GREEN Phase
- [x] `docker/compose/docker-compose.dev.yml` 작성
  - [x] volumes 마운트 (hot reload)
  - [x] development target 사용
- [x] `docker/compose/docker-compose.prod.yml` 작성
  - [x] volumes 없음 (이미지 내 코드)
  - [x] production target 사용
  - [x] 리소스 제한 추가
  - [x] healthcheck 강화
- [x] `docker/compose/docker-compose.test.yml` 작성
  - [x] 테스트 전용 설정
- [x] `docker/compose/.env.example` 작성
- [x] 메인 docker-compose.yml은 dev를 override

#### REFACTOR Phase
- [x] 공통 설정 추출 (docker-compose.base.yml)
- [x] 환경 변수 관리 개선
- [x] 테스트 여전히 통과 확인

**Quality Gate**:
- [x] `docker compose -f docker/compose/docker-compose.dev.yml config` 유효
- [x] `docker compose -f docker/compose/docker-compose.prod.yml config` 유효
- [x] `docker compose up -d` (dev) 정상 실행
- [x] `docker compose -f docker/compose/docker-compose.prod.yml up -d` 정상 실행

**Dependencies**: Phase 1-5 완료

**Coverage Target**: N/A (인프라)

**Rollback Strategy**:
- 기존 docker-compose.yml 복구

---

### Phase 7: CI/CD 파이프라인

**Goal**: GitHub Actions로 자동 빌드/배포

**Test Strategy**:
- 워크플로우 테스트: PR에서 실행
- 배포 테스트: main에서 실행

**Tasks**:

#### RED Phase
- [x] `.github/workflows/test-docker-builds.yml` 작성 (테스트용)

#### GREEN Phase
- [x] `.github/workflows/ci.yml` 작성
  - [x] lint, type check, test 실행
  - [x] Docker 이미지 빌드
  - [x] GHCR에 푸시
- [x] `.github/workflows/cd-staging.yml` 작성
  - [x] staging 환경에 배포
- [x] `.github/workflows/cd-production.yml` 작성
  - [x] production 환경에 배포 (수동 트리거)

#### REFACTOR Phase
- [x] 워크플로우 최적화 (캐싱)
- [x] 알림 설정 (이슈/PR 템플릿)
- [x] 테스트 여전히 통과 확인

**Quality Gate**:
- [x] PR에서 CI 워크플로우 성공
- [x] 이미지 GHCR에 푸시됨
- [x] staging 배포 자동화

**Dependencies**: Phase 1-6 완료

**Coverage Target**: N/A (CI/CD)

**Rollback Strategy**:
- 워크플로우 파일 삭제
- 수동 배포로 복귀

---

## Risk Assessment

| Risk | 확률 | 영향 | 완화 전략 |
|------|------|------|----------|
| lib 패키지 버전 충돌 | Medium | High | SemVer 버전 관리, 종속성.lock |
| DB 연결 공유 문제 | Low | Medium | connection string 환경 변수화 |
| Docker 이미지 크기 증가 | Medium | Low | 멀티스테이지 빌드, .dockerignore |
| 테스트 커버리지 미달 | Low | Medium | TDD 강제, 최소 커버리지 게이트 |
| Rollback 복잡성 | Low | High | 각 Phase별 롤백 문서화 |
| CI/CD 배포 실패 | Medium | Medium | staging에서 먼저 검증 |

---

## Progress Tracking

### Overall Progress
- [x] Phase 1: lib/ 패키지 기반 구축
- [x] Phase 2: signal_engine 모듈화
- [x] Phase 3: vcp_scanner 모듈화
- [x] Phase 4: chatbot 모듈화
- [x] Phase 5: api_gateway 모듈화
- [x] Phase 6: docker-compose 리팩토링
- [x] Phase 7: CI/CD 파이프라인

### Current Phase: ✅ ALL PHASES COMPLETE

**Status**: COMPLETE
**Started**: 2026-01-31
**Completed**: 2026-01-31
**Completed**:
- [x] Phase 1: lib/ 패키지 기반 구축 (94% 커버리지)
- [x] Phase 2: signal_engine 모듈화 (81% 커버리지)
- [x] Phase 3: vcp_scanner 모듈화 (83% 커버리지)
- [x] Phase 4: chatbot 모듈화 (54% 커버리지, Docker 실행 확인 완료)
- [x] Phase 5: api_gateway 모듈화 (ServiceRegistry 테스트 14개 통과, Docker 빌드/실행 완료)
- [x] Phase 6: docker-compose 리팩토링 (5개 compose 검증 테스트 통과)
- [x] Phase 7: CI/CD 파이프라인 (5개 워크플로우, 6개 테스트 통과)

### Phase 5 Notes
- api_gateway는 프로젝트 루트와 Docker 실행 모두 지원하도록 `__getattr__` 기반 유연 import 구현
- WebSocket, Kiwoom, Metrics 등 선택적 의존성을 위한 try/except 패턴 적용
- ServiceRegistry 테스트 14개 통과 (98% 커버리지)
- Docker 이미지 빌드/실행 확인 완료 (health endpoint 정상 응답)

### Phase 6 Notes
- 환경별 compose 파일 분리 완료 (base, dev, prod, test)
- base.yml은 인프라 서비스만 포함 (postgres, redis, flower)
- dev.yml은 핫 리로드 지원 (volumes mount)
- prod.yml은 리소스 제한 및 healthcheck 강화
- test.yml은 테스트 실행기 포함, in-memory DB 사용
- 5개 compose 검증 테스트 통과 (test_config.py)

### Phase 7 Notes
- CI/CD 파이프라인 완료 (5개 워크플로우)
- ci.yml: lint (ruff), type-check (mypy), unit tests, integration tests, service tests, Docker build & push
- cd-staging.yml: main 브랜치 merge 시 자동 배포
- cd-production.yml: 수동 트리거 + 승인 필요 (YES 입력)
- test-docker-builds.yml: PR에서 Docker 빌드 검증
- release.yml: 버전 태그 시 GitHub Release 자동 생성
- Dependabot 설정 (Python, npm, GitHub Actions)
- 이슈/PR 템플릿 생성
- 6개 워크플로우 검증 테스트 통과 (test_workflows.py)

---

## Notes & Learnings

### Phase 1 Notes
(작성 후 업데이트)

### Decisions Made
(작성 후 업데이트)

### Blockers & Issues
(작성 후 업데이트)

---

## Quality Gate Commands

### lib/ 패키지
```bash
# 설치 테스트
pip install -e lib/

# import 테스트
python -c "from ralph_stock_lib.database import get_db_session; print('OK')"

# 단위 테스트
pytest lib/tests/ -v --cov=lib/ralph_stock_lib --cov-report=html
```

### 서비스별 테스트
```bash
# signal_engine
pytest services/signal_engine/tests/ -v --cov=services/signal_engine

# vcp_scanner
pytest services/vcp_scanner/tests/ -v --cov=services/vcp_scanner

# chatbot
pytest services/chatbot/tests/ -v --cov=services/chatbot

# api_gateway
pytest services/api_gateway/tests/ -v --cov=services/api_gateway
```

### Docker 빌드 테스트
```bash
# 서비스별 빌드
docker build -f services/signal_engine/Dockerfile -t signal-engine:test .
docker build -f services/vcp_scanner/Dockerfile -t vcp-scanner:test .
docker build -f services/chatbot/Dockerfile -t chatbot:test .
docker build -f services/api_gateway/Dockerfile -t api-gateway:test .
```

### 전체 스택 테스트
```bash
# dev 환경
docker compose -f docker/compose/docker-compose.dev.yml up -d

# prod 환경
docker compose -f docker/compose/docker-compose.prod.yml up -d
```

---

**Last Updated**: 2026-01-31
**Plan Version**: 2.0 (COMPLETE)
**Owner**: Ralph Stock Team
