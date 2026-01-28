# KR Stock - TODO List

> **마지막 업데이트**: 2026-01-28

## 📊 상태 요약

| 우선순위 | 상태 | 진행률 |
|----------|------|--------|
| **P0** (핵심 기능) | ✅ 완료 | 3/3 |
| **P1** (누락 API) | ✅ 완료 | 3/3 |
| **P2** (추가 기능) | 🔄 진행 중 | 1/3 |
| **P3** (품질 향상) | ⏳ 예정 | 0/3 |

> **완료된 작업 상세**: `docs/migration/TODO_ARCHIVE.md` 참조

---

## 🟢 P2 - 추가 기능

### P2-1: Chatbot API
- [ ] **`services/chatbot/main.py`** - FastAPI Chatbot Service
  - [ ] `GET /health` - 서비스 상태
  - [ ] `POST /chat` - 채팅 요청
  - [ ] `GET /context` - 대화 맥락 조회
- [ ] **`src/analysis/chatbot.py`**
  - [ ] RAG 기반 질의응답
  - [ ] 종목 추천 로직
  - [ ] 대화 기록 저장
- [ ] **`services/api_gateway/routes/chatbot.py`**
  - [ ] `POST /api/kr/chatbot` - 챗봇 질의
  - [ ] `GET /api/kr/chatbot/welcome` - 웰컴 메시지
  - [ ] `GET/POST/DELETE /api/kr/chatbot/memory` - 메모리 관리
  - [ ] `GET/DELETE /api/kr/chatbot/history` - 히스토리
- **위치**: `services/chatbot/`, `src/analysis/`, `services/api_gateway/routes/`
- **의존**: LLM API (Gemini/GPT)
- **추정 시간**: 6시간

### P2-2: CLI 진입점 ✅
- [x] **`run.py`** - Rich 기반 CLI 메뉴 인터페이스
  - [x] VCP 스캔, 시그널 생성, 조회
  - [x] Market Gate, AI 분석, 시스템 헬스
  - [x] 백테스트 KPI
- [x] **`requirements.txt`** - rich==13.7.0 추가
- **완료일**: 2026-01-28

### P2-3: 누적 수익률 API
- [ ] **`services/api_gateway/routes/performance.py`**
  - [ ] `GET /api/kr/performance/cumulative` - 누적 수익률
  - [ ] `GET /api/kr/performance/by-signal` - 시그널별 성과
  - [ ] `GET /api/kr/performance/by-period` - 기간별 성과
- [ ] **`src/repositories/performance_repository.py`**
  - [ ] `calculate_cumulative_return()` - 누적 수익률 계산
  - [ ] `calculate_win_rate()` - 승률 계산
  - [ ] `calculate_sharpe_ratio()` - 샤프 비율
- **위치**: `services/api_gateway/routes/`, `src/repositories/`
- **의존**: Signal 데이터 충분
- **추정 시간**: 3시간

---

## 🔵 P3 - 품질 향상

### P3-1: 테스트 커버리지 향상
- [ ] **단위 테스트 추가**
  - [ ] `src/config/` 설정 모듈 테스트
  - [ ] `src/repositories/backtest_repository.py` 테스트
  - [ ] `services/ai_analyzer/` 테스트
- [ ] **통합 테스트 추가**
  - [ ] 백테스트 API 통합 테스트
  - [ ] AI 분석 API 통합 테스트
  - [ ] SSE 스트리밍 테스트
- [ ] **목표**: 전체 커버리지 80% 이상
- **추정 시간**: 4시간

### P3-2: API 문서화
- [ ] **OpenAPI 스펙 완성**
  - [ ] 모든 엔드포인트 설명 추가
  - [ ] 예제 응답 추가
  - [ ] 에러 케이스 문서화
- [ ] **`docs/api/`** - API 가이드
  - [ ] `getting-started.md`
  - [ ] `endpoints.md`
  - [ ] `examples.md`
- **추정 시간**: 2시간

### P3-3: 코드 품질 개선
- [ ] **린트/포맷**
  - [ ] `ruff check .` 통과
  - [ ] `ruff format .` 적용
- [ ] **타입 검사**
  - [ ] `mypy src/` 통과
  - [ ] 타입 힌트 추가
- [ ] **코드 복잡도**
  - [ ] cyclomatic complexity 확인
  - [ ] 리팩토링
- **추정 시간**: 3시간

---

## 📊 마일스톤

### Milestone 1: 핵심 기능 완성 ✅
- [x] Open Architecture 마이그레이션 (7/7 Phases)
- [x] P0-1: Config 설정 복원
- [x] P0-2: 백테스트 결과 모델 및 API
- [x] P0-3: 종목 상세 API (백엔드 완료)

### Milestone 2: 누락 API 구현 ✅
- [x] P1-1: AI 분석 API
- [x] P1-2: 시스템 관리 API
- [x] P1-3: VCP/Signal 트리거 API

### Milestone 3: 추가 기능 🔄
- [ ] P2-1: Chatbot API
- [x] P2-2: CLI 진입점
- [ ] P2-3: 누적 수익률 API

### Milestone 4: 품질 향상 ⏳
- [ ] P3-1: 테스트 커버리지 향상
- [ ] P3-2: API 문서화
- [ ] P3-3: 코드 품질 개선

---

## 🔗 관련 문서

- [PROGRESS.md](./PROGRESS.md) - 전체 진행 상황
- [CLAUDE.md](./CLAUDE.md) - 프로젝트 개요 및 아키텍처
- [docs/plans/PLAN_open_architecture_migration.md](./docs/plans/PLAN_open_architecture_migration.md) - 마이그레이션 상세 계획
- [docs/migration/TODO_ARCHIVE.md](./docs/migration/TODO_ARCHIVE.md) - 완료된 P0/P1 작업 내역
