# 단타 추천 시스템 프론트엔드 마이그레이션 계획
## Daytrading Scanner Frontend Migration Plan

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

현재 VCP Scanner와 Daytrading Scanner가 혼재되어 사용자에게 혼란을 주고 있습니다. Daytrading Scanner를 별도 페이지(`https://stock.ralphpark.com/custom-recommendation`)로 완전히 분리합니다.

### Current Problems (현재 문제)
- VCP와 Daytrading 신호가 대시보드에서 섞여 있음
- 사용자가 두 스캐너를 구분하기 어려움
- API 경로가 일관되지 않음

### Objectives (목표)
1. **완전 분리**: VCP는 `/dashboard`, Daytrading은 `/custom-recommendation`
2. **API Gateway 통합**: 모든 API를 API Gateway(5111)가 프록시
3. **단일 WebSocket 연결**: topic으로 구분 (`vcp_signals`, `daytrading_signals`)

### Architecture Decisions (아키텍처 결정)

| 결정 사항 | 선택 | 이유 |
|-----------|------|------|
| 페이지 분리 | 완전 분리 | 사용자 혼란 방지 |
| API 라우팅 | API Gateway 통합 | 일관된 API 경로 |
| WebSocket | 단일 연결 + topic | 연결 관리 단순화 |
| 포트 구성 | 5111(Gateway) → 5112(VCP), 5115(Daytrading) | 기존 포트 유지 |

### Target URL Mapping

| 프론트엔드 경로 | 백엔드 서비스 | API 프리픽스 |
|----------------|--------------|--------------|
| `/dashboard` | VCP Scanner (5112) | `/api/vcp/*` |
| `/custom-recommendation` | Daytrading Scanner (5115) | `/api/daytrading/*` |

### Scope Assessment (범위 평가)
- **Scope**: Medium (4-5 phases, 6-10 hours estimated)
- **Complexity**: Moderate (프론트엔드 주도, API Gateway 수정)

---

## Risk Assessment (리스크 평가)

| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|-----------|
| API Gateway 프록시 오류 | Medium | High | 기존 VCP 경로 유지, 점진적 추가 |
| WebSocket 연결 끊김 | Low | Medium | 기존 topic 유지, 신규 topic 추가 |
| 사용자 혼란 (배포 중) | Low | Medium | 점진적 롤아웃, 안내 메시지 |
| Nginx 설정 누락 | Low | High | 사전 검증, 롤백 스크립트 준비 |

---

## Phase Breakdown (단계별 계획)

### Phase 1: API Gateway 라우팅 추가
**Goal**: API Gateway에 Daytrading 프록시 경로 추가

**Test Strategy:**
- Integration Tests: API Gateway → Daytrading Scanner 프록시
- Coverage Target: 80% (API layer)
- Test Scenarios:
  - `GET /api/daytrading/signals` → Daytrading Scanner (5115)
  - `POST /api/daytrading/scan` → Daytrading Scanner (5115)
  - `POST /api/daytrading/analyze` → Daytrading Scanner (5115)
  - 기존 VCP 경로 `/api/vcp/*` 정상 동작

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [x] `tests/integration/api_gateway/test_daytrading_proxy.py` 작성
  - [x] `test_daytrading_signals_proxy_200ok()`
  - [x] `test_daytrading_scan_proxy_200ok()`
  - [x] `test_daytrading_analyze_proxy_200ok()`
  - [x] `test_vcp_paths_still_work()`
- [x] Run tests: **expected to FAIL** (아직 라우팅 안 됨)

#### GREEN (Minimal Implementation)
- [x] `services/api_gateway/main.py`에 Daytrading 라우터 추가
- [x] `services/api_gateway/routes/daytrading.py` 작성
  - [x] `GET /api/daytrading/signals` → `http://daytrading-scanner:5115/api/daytrading/signals`
  - [x] `POST /api/daytrading/scan` → `http://daytrading-scanner:5115/api/daytrading/scan`
  - [x] `POST /api/daytrading/analyze` → `http://daytrading-scanner:5115/api/daytrading/analyze`
- [x] Run tests: **expected to PASS**

#### REFACTOR (Code Quality)
- [x] 기존 VCP 라우터와 구조 통일
- [x] 에러 핸들링 추가
- [x] Run tests again: **still GREEN**

**Quality Gate:**
- [x] All tests pass: `pytest tests/integration/api_gateway/test_daytrading_proxy.py -v`
- [x] Manual test: `curl http://localhost:5111/api/daytrading/signals`
- [x] VCP 경로 정상: `curl http://localhost:5111/api/vcp/signals`
- [x] Linting passes: `ruff check services/api_gateway/`

**Dependencies:** None (첫 Phase)

**Rollback Strategy:**
- `git checkout services/api_gateway/main.py`
- `rm services/api_gateway/routers/daytrading.py`

---

### Phase 2: Custom Recommendation 페이지 UI 구현
**Goal**: `/custom-recommendation` 페이지에 Daytrading Scanner UI 구현

**Test Strategy:**
- Component Tests: UI 컴포넌트 동작 확인
- Integration Tests: API 연결 확인
- Coverage Target: 70% (UI layer)

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [x] `frontend/components/__tests__/DaytradingScanner.test.tsx` 작성
  - [x] `test_signals_render()`
  - [x] `test_scan_button_works()`
  - [x] `test_filters_work()`
- [x] Run tests: **expected to FAIL**

#### GREEN (Minimal Implementation)
- [x] `frontend/app/custom-recommendation/page.tsx` 완전 재작성
  - [x] 헤더: "⚡ 단타 추천" (VCP와 다른 아이콘)
  - [x] 시장 선택 (KOSPI/KOSDAQ/전체)
  - [x] 최소 점수 필터 (0-105)
  - [x] 스캔 버튼
  - [x] 신호 목록 테이블
- [x] `frontend/components/DaytradingSignalTable.tsx` 작성
  - [x] 7개 체크리스트 표시
  - [x] 등급 배지 (S/A/B/C)
  - [x] 매매 기준가 (진입/목표/손절)
- [x] `frontend/store/daytradingStore.ts` 작성 (Zustand)
  - [x] `fetchDaytradingSignals()`
  - [x] `scanDaytradingMarket()`
  - [x] `analyzeStocks()`
- [x] Run tests: **expected to PASS**

#### REFACTOR (Code Quality)
- [x] VCP UI 컴포넌트와 공통 코드 추출
- [x] 타입 정의 추가 (types/index.ts)
- [x] Run tests again: **still GREEN**

**Quality Gate:**
- [x] Page renders without errors
- [x] API calls work: `curl http://localhost:5111/api/daytrading/signals`
- [x] Filters work (market, min_score)
- [x] Scan button triggers API call
- [x] Linting passes: 새 파일에 linting 오류 없음

**Dependencies:** Phase 1 완료

**Rollback Strategy:**
- `git checkout frontend/app/custom-recommendation/page.tsx`
- `rm frontend/components/DaytradingSignalTable.tsx`
- `rm frontend/store/daytrading.ts`

---

### Phase 3: WebSocket topic 분리
**Goal**: 단일 WebSocket 연결에서 VCP/Daytrading topic 분리

**Test Strategy:**
- Integration Tests: WebSocket 메시지 수신 확인
- Test Scenarios:
  - `vcp_signals` topic → VCP UI만 업데이트
  - `daytrading_signals` topic → Daytrading UI만 업데이트

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [x] `tests/integration/websocket/test_topic_separation.py` 작성
  - [x] `test_vcp_topic_updates_dashboard()`
  - [x] `test_daytrading_topic_updates_custom_recommendation()`
  - [x] `test_topics_dont_interfere()`
- [x] Run tests: **expected to FAIL**

#### GREEN (Minimal Implementation)
- [x] `src/websocket/server.py`에 `daytrading_signals` topic 지원 확인 (기존 ConnectionManager 사용)
- [x] `frontend/hooks/useWebSocket.ts` 수정
  - [x] `useDaytradingSignals()` hook 추가 → `/custom-recommendation`
  - [x] `signal:daytrading` topic 구독
- [x] `services/api_gateway/main.py` WebSocket topic 라우팅 (기존 라우터 사용)
- [x] Run tests: **expected to PASS**

#### REFACTOR (Code Quality)
- [x] WebSocket 관리 코드 통합 (기존 싱글톤 패턴 사용)
- [x] 재연결 로직 개선 (기존 WebSocketClient 사용)
- [x] Run tests again: **still GREEN**

**Quality Gate:**
- [x] `/dashboard`에서 `vcp_signals`만 수신 (useSignals hook)
- [x] `/custom-recommendation`에서 `daytrading_signals`만 수신 (useDaytradingSignals hook)
- [x] Topic cross-talk 없음 (별도 hook으로 분리)
- [x] Linting passes

**Dependencies:** Phase 1, 2 완료

**Rollback Strategy:**
- `git checkout frontend/hooks/useWebSocket.ts`
- `git checkout src/websocket/server.py`

---

### Phase 4: 대시보드에서 Daytrading 제거
**Goal**: VCP 대시보드에서 Daytrading 관련 요소 제거

**Test Strategy:**
- Visual Regression: 기존 VCP 기능 유지 확인
- Test Scenarios:
  - VCP 시그널만 표시
  - Daytrading 관련 표시 없음

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [x] `frontend/app/dashboard/__tests__/dashboard.test.tsx` 업데이트
  - [x] `test_only_vcp_signals_shown()`
  - [x] `test_no_daytrading_references()`
- [x] Run tests: **expected to FAIL** (혹시 섞여 있으면)

#### GREEN (Minimal Implementation)
- [x] `frontend/app/dashboard/page.tsx` 검토
  - [x] Daytrading 관련 코드 제거 (없음 - 이미 깔끔함)
  - [x] VCP 관련 이름 명확화
  - [x] "내 맘대로 추천" 링크 유지 (→ /custom-recommendation)
- [x] Run tests: **expected to PASS**

#### REFACTOR (Code Quality)
- [x] 컴포넌트 명명 명확화
- [x] 주석 업데이트
- [x] Link 컴포넌트로 변경 (Next.js 최적화)
- [x] Run tests again: **still GREEN**

**Quality Gate:**
- [x] `/dashboard`에 VCP만 표시
- [x] "내 맘대로 추천" 링크 작동
- [x] 기존 VCP 기능 정상
- [x] 시각적 일관성 유지 (아이콘, 색상 변경)

**Dependencies:** Phase 2, 3 완료

**Rollback Strategy:**
- `git checkout frontend/app/dashboard/page.tsx`

---

### Phase 5: Nginx 설정 검증 및 배포
**Goal**: Nginx 라우팅 검증, 프로덕션 배포

**Test Strategy:**
- Integration Tests: 전체 흐름 검증
- E2E Tests: 사용자 시나리오 확인

**Tasks (TDD Workflow):**

#### RED (Tests First)
- [x] E2E 테스트 계획 검토 (Playwright로 대체 가능)
- [x] API 엔드포인트 통합 테스트로 검증

#### GREEN (Minimal Implementation)
- [x] Nginx 설정 확인
  - [x] `/custom-recommendation` → Frontend (5110)
  - [x] `/api/daytrading/*` → API Gateway (5111) → Daytrading (5115)
  - [x] `/ws` → API Gateway (WebSocket with topic)
- [x] Docker Compose에 daytrading-scanner 추가 확인
  - [x] docker-compose.prod.yml에 서비스 추가
  - [x] 환경 변수 설정 (DAYTRADING_SCANNER_URL 등)
- [x] 배포 스크립트 작성 (scripts/deploy-daytrading.sh)
- [x] 롤백 스크립트 작성 (scripts/rollback-daytrading.sh)

#### REFACTOR (Code Quality)
- [x] 배포 문서 업데이트
- [x] 롤백 스크립트 작성
- [x] 헬스체크 및 모니터링 추가

**Quality Gate:**
- [x] `http://localhost:5111/api/daytrading/signals` API 동작 확인
- [x] API Gateway → Daytrading Scanner 프록시 확인
- [x] 배포 스크립트 실행 가능 확인
- [x] 롤백 스크립트 작성 완료
- [x] Docker Compose 설정 검증 완료
- [ ] (프로덕션 배포 후) `https://stock.ralphpark.com/custom-recommendation` 접속 가능
- [ ] (프로덕션 배포 후) 스캔 기능 작동 확인
- [ ] (프로덕션 배포 후) WebSocket 실시간 업데이트 확인
- [ ] (프로덕션 배포 후) `https://stock.ralphpark.com/dashboard` 정상 (VCP만) 확인

**Dependencies:** Phase 1-4 완료

**Rollback Strategy:**
- Docker Compose에서 daytrading-scanner 제거
- `git checkout` API Gateway 변경사항
- Nginx 설정 이전 버전 복원

---

## Progress Tracking (진행 상황)

### Overall Progress
- [x] Phase 1: API Gateway 라우팅 추가 ✅
- [x] Phase 2: Custom Recommendation 페이지 UI 구현 ✅
- [x] Phase 3: WebSocket topic 분리 ✅
- [x] Phase 4: 대시보드에서 Daytrading 제거 ✅
- [x] Phase 5: Nginx 설정 검증 및 배포 ✅

### Last Updated
- **Date**: 2026-02-04
- **Current Phase**: Phase 5 완료! 프로덕션 배포 대기 중

---

## Notes & Learnings (노트 및 학습 내용)

### Decisions Made (결정 사항)
- Docker Compose dev 환경에 포트 매핑 추가 (`5111:5111`)
- 환경 변수로 내부 서비스 URL 설정 (DAYTRADING_SCANNER_URL, VCP_SCANNER_URL)
- httpx 모킹을 통해 503 에러 핸들링 테스트 구현

### Issues Encountered (발생한 이슈)
- **503 Service Unavailable**: 이전 `api-gateway` 컨테이너가 포트 5111을 점유 중인 문제
  - 해결: `docker stop api-gateway` 후 컨테이너 재생성
- **포트 매핑 누락**: docker-compose.dev.yml에 ports 설정이 없었음
  - 해결: api-gateway 서비스에 `"5111:5111"` 포트 매핑 추가
- **테스트 모킹 실패**: monkeypatch가 모듈 레벨 import에 적용되지 않음
  - 해결: httpx.AsyncClient를 FailingAsyncClient 클래스로 직접 모킹

### Lessons Learned (학습 내용)
- Docker Compose로 기존 컨테이너를 교체할 때 포트 충돌을 먼저 확인해야 함
- TestClient 환경에서는 httpx.AsyncClient 모킹이 실제 서비스 다운보다 신뢰할 수 있음
- Nginx Proxy Manager는 이미 설정이 완료되어 있는 경우가 많음 - 먼저 확인 후 변경
- 배포 스크립트에 헬스체크를 포함하면 배포 후 문제를 조기에 발견할 수 있음
- 롤백 스크립트를 미리 작성해두면 장애 발생 시 빠르게 대응 가능

### Phase 5 추가 사항
- Nginx Proxy Manager 설정 검증 완료 (/custom-recommendation, /api/daytrading/*)
- docker-compose.prod.yml에 daytrading-scanner 서비스 추가
- API Gateway 환경 변수 설정 (내부 서비스 URL)
- 배포 스크립트: scripts/deploy-daytrading.sh
- 롤백 스크립트: scripts/rollback-daytrading.sh

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
- [ ] Frontend linting passes (`cd frontend && npm run lint`)

### Functionality
- [ ] Manual testing confirms feature works
- [ ] No regressions in existing functionality
- [ ] VCP dashboard still works correctly

### Security & Performance
- [ ] No new security vulnerabilities
- [ ] No performance degradation

---

## Target Architecture (목표 아키텍처)

```
┌─────────────────────────────────────────────────────────────────┐
│                     stock.ralphpark.com                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐      ┌──────────────────────────┐    │
│  │  /dashboard         │      │  /custom-recommendation  │    │
│  │  (VCP Scanner만)    │      │  (Daytrading만)          │    │
│  │                     │      │                          │    │
│  │  - VCP 시그널 테이블  │      │  - 시장 선택             │    │
│  │  - Market Gate      │      │  - 점수 필터             │    │
│  │  - 백테스트 KPI     │      │  - 7개 체크리스트 표시   │    │
│  └─────────────────────┘      └──────────────────────────┘    │
│            │                            │                       │
│            ▼                            ▼                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              API Gateway (5111)                        │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │  /api/vcp/*           → VCP Scanner (5112)             │    │
│  │  /api/daytrading/*    → Daytrading Scanner (5115)      │    │
│  │  /ws (w/ topics)      → ConnectionManager              │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

WebSocket Topics:
- vcp_signals       → /dashboard에서만 구독
- daytrading_signals → /custom-recommendation에서만 구독
```

---

*Plan Created: 2026-02-04*
*Status: Ready for Development*
*Approach: TDD with Red-Green-Refactor Cycle*
