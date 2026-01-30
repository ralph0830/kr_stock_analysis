# Ralph Stock - TODO List

> **마지막 업데이트**: 2026-01-29

## 📊 상태 요약

| 우선순위 | 상태 | 진행률 |
|----------|------|--------|
| **P0** (핵심 기능) | ✅ 완료 | 3/3 |
| **P1** (누락 API) | ✅ 완료 | 3/3 |
| **P2** (추가 기능) | ✅ 완료 | 3/3 |
| **P3** (품질 향상) | ✅ 완료 | 3/3 |
| **P4** (운영 개선) | ✅ 완료 | 4/4 |
| **P5** (성능 최적화) | ✅ 완료 | 4/4 |
| **P6** (보안 강화) | ✅ 완료 | 3/3 |
| **P7** (프론트엔드 고도화) | ✅ 완료 | 4/4 |

> **완료된 작업 상세**: `docs/migration/TODO_ARCHIVE.md` 참조

---

## 🟢 P2 - 추가 기능

### P2-1: Chatbot API ✅
- [x] **`services/chatbot/main.py`** - FastAPI Chatbot Service
  - [x] `GET /health` - 서비스 상태
  - [x] `POST /chat` - 채팅 요청
  - [x] `GET /context` - 대화 맥락 조회
- [x] **`services/chatbot/retriever.py`** - RAG 기반 지식 검색
  - [x] 종목/시그널/뉴스 검색
  - [x] Kiwoom API 실시간 가격 연동
- [x] **`services/chatbot/llm_client.py`** - Gemini LLM 연동
  - [x] 답변 생성 (실시간 분석 기반)
- [x] **`services/chatbot/recommender.py`** - 종목 추천 로직
  - [x] VCP/종가베팅 기반 추천
  - [x] 등급별 포지션 사이즈
- [x] **`services/chatbot/session_manager.py`** - 대화 기록 저장 (Redis)
- [x] **`services/api_gateway/routes/chatbot.py`**
  - [x] `POST /api/kr/chatbot/chat` - 챗봇 질의
  - [x] `GET /api/kr/chatbot/health` - 헬스 체크
  - [x] `GET /api/kr/chatbot/recommendations` - 종목 추천
  - [x] `GET/DELETE /api/kr/chatbot/session/{id}` - 세션 관리
- [x] **`frontend/components/ChatbotWidget.tsx`** - React 챗봇 컴포넌트
- [x] **테스트**: 77개 테스트 통과 (Unit + Integration)
- **완료일**: 2026-01-28

### P2-2: CLI 진입점 ✅
- [x] **`run.py`** - Rich 기반 CLI 메뉴 인터페이스
  - [x] VCP 스캔, 시그널 생성, 조회
  - [x] Market Gate, AI 분석, 시스템 헬스
  - [x] 백테스트 KPI
- [x] **`requirements.txt`** - rich==13.7.0 추가
- **완료일**: 2026-01-28

### P2-3: 누적 수익률 API ✅
- [x] **`services/api_gateway/routes/performance.py`**
  - [x] `GET /api/kr/performance/cumulative` - 누적 수익률
  - [x] `GET /api/kr/performance/by-signal` - 시그널별 성과
  - [x] `GET /api/kr/performance/by-period` - 기간별 성과
  - [x] `GET /api/kr/performance/top-performers` - 최고 성과 종목
  - [x] `GET /api/kr/performance/sharpe-ratio` - 샤프 비율
- [x] **`src/repositories/performance_repository.py`**
  - [x] `calculate_cumulative_return()` - 누적 수익률 계산
  - [x] `calculate_signal_performance()` - 승률, 평균 수익률
  - [x] `calculate_sharpe_ratio()` - 샤프 비율
  - [x] `get_performance_by_period()` - 기간별 성과
  - [x] `get_top_performers()` - 최고 성과 종목
- [x] **테스트**: 10개 테스트 통과
- **완료일**: 2026-01-28

---

## 🔵 P3 - 품질 향상

### P3-1: 테스트 커버리지 향상 ✅
- [x] **단위 테스트 추가**
  - [x] `tests/unit/repositories/test_ai_analysis_repository.py` - 9개 테스트
  - [x] `tests/unit/repositories/test_signal_repository_extended.py` - 14개 테스트
  - [x] `tests/unit/tasks/test_collection_tasks.py` - 8개 테스트
  - [x] `tests/unit/utils/test_httpx_circuit_breaker.py` - 13개 테스트
  - [x] `tests/unit/repositories/test_performance_repository.py` - 10개 테스트 (P2-3)
- [x] **커버리지 향상**
  - 전체: 76% (66% → 10% ↑)
  - ai_analysis_repository: 98%
  - signal_repository: 98%
  - collection_tasks: 88%
- **완료일**: 2026-01-28

### P3-2: API 문서화 ✅
- [x] **OpenAPI 스펙 완성**
  - [x] 모든 엔드포인트 설명 추가 (37개)
  - [x] 예제 응답 추가
  - [x] 에러 케이스 문서화
- [x] **`docs/api/API_GUIDE.md`** - 전체 API 가이드
  - [x] 시작하기 섹션
  - [x] 엔드포인트별 상세 설명
  - [x] 요청/응답 예시
  - [x] 에러 처리 가이드
- [x] **`docs/postman/KR_Stock_API_Collection.json`**
  - [x] 40개 API 요청 컬렉션
  - [x] 변수 설정 (baseUrl, ticker)
  - [x] 예제 데이터 포함
- **완료일**: 2026-01-28

### P3-3: 코드 품질 개선 ✅
- [x] **린트/포맷**
  - [x] `ruff check services/api_gateway/` 통과
  - [x] `ruff check . --fix` 적용
- [x] **수정 사항**
  - [x] unused imports 제거
  - [x] unused variables 제거
  - [x] 중복 정의 제거
  - [x] datetime import 누락 수정
- [x] **services/api_gateway/** - ruff 오류 0개 상태
- **완료일**: 2026-01-28

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

### Milestone 3: 추가 기능 ✅
- [x] P2-1: Chatbot API
- [x] P2-2: CLI 진입점
- [x] P2-3: 누적 수익률 API

### Milestone 4: 품질 향상 ✅
- [x] P3-1: 테스트 커버리지 향상
- [x] P3-2: API 문서화
- [x] P3-3: 코드 품질 개선

---

## 🔮 향후 계획 (P4 이상)

### P4: 운영 개선 ✅
- [x] Docker Compose production 설정
- [x] 로그 수집 구조화 (JSON 형식)
- [x] 헬스체크 개선
- [x] Graceful Shutdown 구현
- **완료일**: 2026-01-28

### P5: 성능 최적화 ✅
- [x] **데이터베이스 쿼리 튜닝**
  - [x] Slow Query 로그 설정 (log_min_duration_statement = 1000)
  - [x] 인덱스 최적화 확인 (daily_prices, signals 인덱스 확인)
  - [x] N+1 쿼리 해결 (Repository 패턴 사용)
- [x] **Redis 캐시 전략 확장**
  - [x] 캐시 TTL 최적화 (CacheTTL 클래스: PRICE=300, SIGNAL=900, MARKET=60)
  - [x] 캐시 warm-up 기능 (CacheClient.warm_up)
  - [x] 캐시 적중률 모니터링 (GET /api/system/cache/metrics)
- [x] **API 응답 시간 모니터링**
  - [x] 요청 추적 ID (RequestIDMiddleware, X-Request-ID 헤더)
  - [x] P95/P99 지표 수집 (Histogram.get_percentile)
  - [x] 느린 엔드포인트 식별 (GET /api/system/metrics/slow)
- [x] **비동기 처리 최적화**
  - [x] Celery 태스크 병렬화 (group/chord 활용)
  - [x] 워커 수 동적 조정 (--autoscale=8,2)
  - [x] 태스크 우선순위 큐 (TaskPriority: HIGH=9, MEDIUM=5, LOW=1)
- **완료일**: 2026-01-30

### P6: 보안 강화 ✅
- [x] **API Key 인증 구현**
  - [x] APIKey 모델 (src/database/models_api_key.py)
  - [x] APIKeyAuthMiddleware (X-API-Key 헤더 검증)
  - [x] API Key 관리 라우터 (발급/조회/삭제/활성화)
- [x] **Rate Limiting 적용**
  - [x] Sliding Window 방식 (RateLimiter)
  - [x] IP별/Key별 제한 (RateLimitMiddleware)
  - [x] 엔드포인트별 제한 (endpoint_limits)
- [x] **입력 검증 강화**
  - [x] SQL Injection 탐지 (detect_sql_injection)
  - [x] XSS 탐지 (detect_xss)
  - [x] 문자열 정제 (sanitize_string)
- **완료일**: 2026-01-30

### P7: 프론트엔드 고도화 ✅
- [x] **`frontend/components/ThemeToggle.tsx`** - 다크 모드 토글 컴포넌트
  - [x] 라이트/다크 모드 전환
  - [x] localStorage에 테마 설정 저장
  - [x] 시스템 선호도 감지
- [x] **`frontend/app/chatbot/page.tsx`** - 챗봇 전용 페이지
  - [x] AI 주식 챗봇 UI
  - [x] 챗봇 위젯 통합
- [x] **모든 페이지 테마 토글 버튼 추가**
  - [x] 홈 (`/`)
  - [x] 대시보드 (`/dashboard`)
  - [x] 시그널 (`/signals`)
  - [x] 차트 (`/chart`)
  - [x] 종목 상세 (`/stock/[ticker]`)
- [x] **`frontend/app/layout.tsx`** - 루트 레이아웃 다크 모드 스타일
- [x] **접속 테스트 완료** (Playwright 헤드리스 모드)
- **완료일**: 2026-01-29

---

## 🔮 향후 계획 (P8 이상)

## 🔗 관련 문서

- [PROGRESS.md](./PROGRESS.md) - 전체 진행 상황
- [CLAUDE.md](./CLAUDE.md) - 프로젝트 개요 및 아키텍처
- [docs/plans/PLAN_open_architecture_migration.md](./docs/plans/PLAN_open_architecture_migration.md) - 마이그레이션 상세 계획
- [docs/migration/TODO_ARCHIVE.md](./docs/migration/TODO_ARCHIVE.md) - 완료된 P0/P1 작업 내역
- [docs/api/API_GUIDE.md](./docs/api/API_GUIDE.md) - API 가이드 문서
