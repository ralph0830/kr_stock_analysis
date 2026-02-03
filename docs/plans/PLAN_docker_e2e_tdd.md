# Docker Full-Stack E2E Test Plan (TDD)

**CRITICAL INSTRUCTIONS**: After completing each phase:
1. ✅ Check off completed task checkboxes
2. 🧪 Run all quality gate validation commands
3. ⚠️ Verify ALL quality gate items pass
4. 📅 Update "Last Updated" date
5. 📝 Document learnings in Notes section
6. ➡️ Only then proceed to next phase

⛔ DO NOT skip quality gates or proceed with failing checks

---

## Overview

Docker Compose 기반 Full-Stack 통합 환경의 E2E 테스트 계획입니다. TDD 방식(Red-Green-Refactor)으로 모든 서비스와 프론트엔드 페이지가 정상 작동하는지 검증합니다.

**목표:**
- 모든 백엔드 서비스가 정상 응답하는지 확인
- 모든 프론트엔드 페이지가 렌더링되는지 확인
- 서비스 간 통신이 정상 작동하는지 확인

**범위:** Medium (4-5 phases, 4-8 hours total)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (5110)  →  API Gateway (5111)                    │
│       ↓                  ↓                                   │
│   Next.js          ┌──────────────────────────┐             │
│                   │  VCP Scanner (5112)      │             │
│                   │  Signal Engine (5113)    │             │
│                   │  Chatbot (5114)          │             │
│                   └──────────────────────────┘             │
│                         ↓                                   │
│                   PostgreSQL (5433)                         │
│                   Redis (6380)                              │
│                   Celery (Flower:5555)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### Phase 1: Service Health Check API Tests

**Goal:** 모든 백엔드 서비스의 health endpoint가 정상 응답하는지 확인

**Test Strategy:**
- HTTP health check 테스트
- 각 서비스의 `/health` 또는 루트 endpoint 검증
- Response JSON 구조 검증
- Expected status code: 200

**Tasks:**

- [ ] **RED Phase: 실패하는 테스트 작성**
  - [ ] `tests/e2e/test_service_health.py` 생성
  - [ ] API Gateway health check 테스트 작성 (예상: 실패)
  - [ ] VCP Scanner health check 테스트 작성
  - [ ] Signal Engine health check 테스트 작성
  - [ ] Chatbot health check 테스트 작성
  - [ ] PostgreSQL connection 테스트 작성
  - [ ] Redis connection 테스트 작성
  - [ ] Flower 접속 테스트 작성
  - [ ] `pytest tests/e2e/test_service_health.py` 실행해서 실패 확인

- [ ] **GREEN Phase: 서비스 실행 및 테스트 통과**
  - [ ] `docker compose --profile dev up -d` 실행
  - [ ] 모든 컨테이너가 실행되는지 확인 (`docker compose ps`)
  - [ ] `pytest tests/e2e/test_service_health.py -v` 실행
  - [ ] 실패한 테스트가 없는지 확인

- [ ] **REFACTOR Phase: 코드 개선**
  - [ ] 테스트 코드 리팩토링 (중복 제거)
  - [ ] 헬퍼 함수 추출
  - [ ] 테스트 다시 실행해서 계속 통과하는지 확인

**Quality Gate:**
- [ ] 모든 health check 테스트 통과
- [ ] 각 서비스가 JSON 응답 반환
- [ ] response time < 2초

**Dependencies:** Docker Compose 환경 구축 완료

**Coverage Target:** 100% (health endpoints)

---

### Phase 2: Frontend Page Load Tests

**Goal:** 모든 프론트엔드 페이지가 오류 없이 렌더링되는지 확인

**Test Strategy:**
- Playwright E2E 테스트
- 각 페이지 접속 후 렌더링 확인
- JavaScript 에러 없는지 확인
- Expected: 페이지 타이틀 및 주요 요소가 존재

**Tasks:**

- [ ] **RED Phase: 실패하는 테스트 작성**
  - [ ] `frontend/__tests__/e2e/page-load.spec.ts` 생성
  - [ ] 홈 페이지 (`/`) 로드 테스트 작성
  - [ ] 대시보드 (`/dashboard`) 로드 테스트 작성
  - [ ] KR 대시보드 (`/dashboard/kr`) 로드 테스트 작성
  - [ ] VCP 페이지 (`/dashboard/kr/vcp`) 로드 테스트 작성
  - [ ] 종가베팅 페이지 (`/dashboard/kr/closing-bet`) 로드 테스트 작성
  - [ ] 시그널 페이지 (`/signals`) 로드 테스트 작성
  - [ ] 차트 페이지 (`/chart`) 로드 테스트 작성
  - [ ] 챗봇 페이지 (`/chatbot`) 로드 테스트 작성
  - [ ] 종목 상세 (`/stock/005930`) 로드 테스트 작성
  - [ ] `playwright test` 실행해서 실패 확인

- [ ] **GREEN Phase: 페이지 구현 및 테스트 통과**
  - [ ] Frontend 컨테이너가 실행 중인지 확인
  - [ ] `playwright test` 실행
  - [ ] 실패한 페이지 수정 (Next.js 컴포넌트)
  - [ ] 모든 테스트 통과할 때까지 반복

- [ ] **REFACTOR Phase: 코드 개선**
  - [ ] 페이지 로드 시간 최적화
  - [ ] 공통 테스트 헬퍼 함수 추출
  - [ ] 테스트 다시 실행

**Quality Gate:**
- [ ] 모든 페이지가 3초 내에 로드
- [ ] JavaScript console 에러 없음
- [ ] 404 응답 없음
- [ ] 페이지 타이틀이 올바르게 표시

**Dependencies:** Phase 1 완료, Frontend 서비스 실행 중

**Coverage Target:** 100% (pages)

---

### Phase 3: API Integration Tests

**Goal:** 프론트엔드에서 백엔드 API를 호출하여 데이터가 정상 표시되는지 확인

**Test Strategy:**
- Playwright + MSW (Mock Service Worker) 또는 실제 API
- 주요 API endpoint 호출 테스트
- 데이터가 UI에 정상 렌더링되는지 확인

**Tasks:**

- [ ] **RED Phase: 실패하는 테스트 작성**
  - [ ] `frontend/__tests__/e2e/api-integration.spec.ts` 생성
  - [ ] 종목 목록 API 호출 테스트 작성
  - [ ] VCP 스캔 결과 API 호출 테스트 작성
  - [ ] 시그널 목록 API 호출 테스트 작성
  - [ ] 챗봇 응답 API 호출 테스트 작성
  - [ ] API 응답이 UI에 표시되는지 확인 테스트 작성
  - [ ] `playwright test` 실행해서 실패 확인

- [ ] **GREEN Phase: API 구현 및 테스트 통과**
  - [ ] 백엔드 API 엔드포인트 구현 (미완료 시)
  - [ ] 프론트엔드 API 호출 로직 구현
  - [ ] `playwright test` 실행
  - [ ] 모든 테스트 통과

- [ ] **REFACTOR Phase: 코드 개선**
  - [ ] API 에러 핸들링 개선
  - [ ] 로딩 상태 UI 개선
  - [ ] 테스트 재실행

**Quality Gate:**
- [ ] API 호출 시 response time < 5초
- [ ] 에러 발생 시 사용자에게 적절한 메시지 표시
- [ ] 데이터가 UI에 정확히 표시

**Dependencies:** Phase 1, 2 완료

**Coverage Target:** 80% (API integration)

---

### Phase 4: Service Integration Tests

**Goal:** 서비스 간 통신이 정상 작동하는지 확인 (Celery task, WebSocket 등)

**Test Strategy:**
- Celery task 실행 및 결과 확인
- WebSocket 연결 테스트 (구현 시)
- Flower 대시보드에서 task 확인

**Tasks:**

- [ ] **RED Phase: 실패하는 테스트 작성**
  - [ ] `tests/e2e/test_celery_tasks.py` 생성
  - [ ] Celery worker가 task를 처리하는지 테스트 작성
  - [ ] Celery beat가 스케줄대로 실행하는지 테스트 작성
  - [ ] Flower 대시보드에서 task를 확인하는지 테스트 작성
  - [ ] `pytest tests/e2e/test_celery_tasks.py` 실행해서 실패 확인

- [ ] **GREEN Phase: 통합 구현 및 테스트 통과**
  - [ ] Celery worker 실행 확인
  - [ ] Celery beat 실행 확인
  - [ ] Task 등록 및 실행
  - [ ] `pytest tests/e2e/test_celery_tasks.py` 실행
  - [ ] 모든 테스트 통과

- [ ] **REFACTOR Phase: 코드 개선**
  - [ ] Task 재시도 로직 개선
  - [ ] 모니터링 개선
  - [ ] 테스트 재실행

**Quality Gate:**
- [ ] Celery task가 성공적으로 완료
- [ ] Flower에서 task 상태 확인 가능
- [ ] 실패한 task의 로그가 기록됨

**Dependencies:** Phase 1 완료

**Coverage Target:** 70% (background tasks)

---

### Phase 5: Full E2E User Flow Tests

**Goal:** 실제 사용자 시나리오를 시뮬레이션하여 전체 흐름 검증

**Test Strategy:**
- Playwright E2E 테스트
- 사용자 시나리오: 종목 검색 → VCP 확인 → 시그널 확인 → 차트 확인

**Tasks:**

- [ ] **RED Phase: 실패하는 테스트 작성**
  - [ ] `frontend/__tests__/e2e/user-flow.spec.ts` 생성
  - [ ] 시나리오1: 홈 → 대시보드 → KR 종목 확인
  - [ ] 시나리오2: VCP 스캔 결과 확인 및 종목 선택
  - [ ] 시나리오3: 시그널 목록 확인 및 필터링
  - [ ] 시나리오4: 챗봇에 질문하고 응답 확인
  - [ ] `playwright test` 실행해서 실패 확인

- [ ] **GREEN Phase: 흐름 구현 및 테스트 통과**
  - [ ] 각 페이지 간 네비게이션 구현
  - [ ] 데이터 연결 구현
  - [ ] `playwright test` 실행
  - [ ] 모든 테스트 통과

- [ ] **REFACTOR Phase: UX 개선**
  - [ ] 페이지 전환 애니메이션 추가
  - [ ] 로딩 상태 피드백 개선
  - [ ] 테스트 재실행

**Quality Gate:**
- [ ] 모든 사용자 시나리오가 10초 내에 완료
- [ ] 중단 없는流畅한 경험
- [ ] 모든 네비게션이 정상 작동

**Dependencies:** Phase 1, 2, 3, 4 완료

**Coverage Target:** 90% (critical user paths)

---

## Test Files Structure

```
tests/e2e/
├── conftest.py                    # Pytest fixtures
├── test_service_health.py         # Phase 1
├── test_celery_tasks.py           # Phase 4
└── test_api_integration.py        # Phase 3

frontend/__tests__/e2e/
├── page-load.spec.ts              # Phase 2
├── api-integration.spec.ts        # Phase 3
└── user-flow.spec.ts              # Phase 5
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 서비스 간 네트워크 문제 | Medium | High | docker-compose.yml에서 network 확인 |
| 데이터베이스 초기화 실패 | Low | High | healthcheck 기다린 후 테스트 |
| 프론트엔드 빌드 실패 | Medium | Medium | Dockerfile 단계별 빌드 확인 |
| Celery worker가 task 처리 안 함 | Medium | Medium | Flower 대시보드로 상태 확인 |
| 포트 충돌 | Low | High | 다른 서비스 중지 후 테스트 |

---

## Rollback Strategy

**Phase 1-2:** 컨테이너 재시작 (`docker compose restart`)

**Phase 3-5:**
- Git으로 코드 롤백
- `docker compose down -v` 후 재시작
- DB 초기화 필요 시 `docker compose up -d --force-recreate`

---

## Progress Tracking

### Phase 1: Service Health Check API Tests
- [ ] RED Phase 완료
- [ ] GREEN Phase 완료
- [ ] REFACTOR Phase 완료
- [ ] Quality Gate 통과

### Phase 2: Frontend Page Load Tests
- [ ] RED Phase 완료
- [ ] GREEN Phase 완료
- [ ] REFACTOR Phase 완료
- [ ] Quality Gate 통과

### Phase 3: API Integration Tests
- [ ] RED Phase 완료
- [ ] GREEN Phase 완료
- [ ] REFACTOR Phase 완료
- [ ] Quality Gate 통과

### Phase 4: Service Integration Tests
- [ ] RED Phase 완료
- [ ] GREEN Phase 완료
- [ ] REFACTOR Phase 완료
- [ ] Quality Gate 통과

### Phase 5: Full E2E User Flow Tests
- [ ] RED Phase 완료
- [ ] GREEN Phase 완료
- [ ] REFACTOR Phase 완료
- [ ] Quality Gate 통과

---

## Last Updated

2026-02-01

---

## Notes

### Learnings
- Docker Compose의 volume 경로는 절대 경로를 사용해야 함
- extends와 override 파일의 volumes merge는 shallow copy됨
- Playwright 테스트는 frontend 컨테이너 내부에서 실행하는 것이 아니라 호스트에서 실행

### Issues Found
- None yet (테스트 진행 후 기록)
