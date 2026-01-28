# PLAN: API 문서화 및 코드 품질 개선 (P3-2, P3-3)

> **작업 기간**: 2026-01-28
> **범위**: Medium (4개 Phase, 예상 6-8시간)
> **목표**: OpenAPI 스펙 완성, API 가이드 작성, 코드 품질 개선

---

## 📋 개요

### 목적
1. **P3-2**: API 엔드포인트에 대한 상세 문서 작성
   - OpenAPI 스펙 보강 (요약, 설명, 예제 추가)
   - API 가이드 문서 작성 (`docs/api/`)
   - Postman Collection 내보내기

2. **P3-3**: 코드 품질 개선
   - ruff lint/format 통과
   - mypy 타입 검사 통과
   - 코드 복잡도 개선

### 대상 API 엔드포인트

| 태그 | 경로 | 설명 |
|------|------|------|
| `health` | `/health`, `/` | 헬스 체크 |
| `signals` | `/api/kr/signals`, `/api/kr/jongga-v2/*` | 시그널 조회 |
| `stocks` | `/api/kr/stocks/*` | 종목 상세, 차트, 수급, 시그널 |
| `market` | `/api/kr/market-gate` | Market Gate 상태 |
| `ai` | `/api/kr/ai-*` | AI 분석 |
| `chatbot` | `/api/kr/chatbot/*` | 챗봇 |
| `performance` | `/api/kr/performance/*` | 성과 지표 |
| `backtest` | `/api/kr/backtest/*` | 백테스트 |
| `triggers` | `/api/kr/scan/*` | 스캔 트리거 |
| `system` | `/api/system/*` | 시스템 관리 |
| `kiwoom` | `/api/kr/kiwoom/*` | 키움 연동 |

---

## 🎯 Phase 구조

### Phase 1: OpenAPI 스펙 보강
**목표**: FastAPI 자동 문서 개선

- 모든 엔드포인트에 `summary`, `description` 추가
- 요청/응답 예제 추가
- 태그 분류 정리
- 에러 케이스 문서화

### Phase 2: API 가이드 문서 작성
**목표**: 사용자용 API 가이드 작성

- `docs/api/getting-started.md` - 시작 가이드
- `docs/api/endpoints.md` - 엔드포인트 목록
- `docs/api/examples.md` - 사용 예시
- `docs/api/authentication.md` - 인증 가이드

### Phase 3: Postman Collection 생성
**목표**: Postman용 Collection 내보내기

- JSON 형식 Collection 생성
- 환경 변수 설정
- 예제 요청/응답 포함

### Phase 4: 코드 품질 개선 (P3-3)
**목표**: ruff/mypy 통과

- ruff check/format 실행 및 수정
- mypy 타입 검사 및 수정
- 코드 복잡도 점검

---

## 📝 Phase 1: OpenAPI 스펙 보강

### Goal
FastAPI의 자동 생성되는 OpenAPI 스펙(`openapi.json`)의 품질을 개선합니다.

### Tasks

#### 1.1 메인 엔드포인트 문서화
- [ ] `services/api_gateway/main.py` 엔드포인트 개선
  - [ ] `/health` - summary, description, examples 추가
  - [ ] `/` - 루트 엔드포인트 문서화
  - [ ] `/metrics`, `/api/metrics` - 메트릭 엔드포인트 문서화
  - [ ] `/api/kr/signals` - summary, description 개선
  - [ ] `/api/kr/market-gate` - Market Gate 상태 설명 추가
  - [ ] `/api/kr/backtest-kpi` - 백테스트 KPI 설명
  - [ ] `/api/kr/jongga-v2/*` - 종가베팅 V2 엔드포인트 문서화
  - [ ] `/api/kr/stocks/*` - 종목 관련 엔드포인트 정리

#### 1.2 라우터 파일 문서화
- [ ] `routes/ai.py` - AI 분석 엔드포인트
  - [ ] `GET /api/kr/ai-summary/{ticker}` - 종목 AI 요약
  - [ ] `GET /api/kr/ai-analysis` - 전체 AI 분석
  - [ ] `GET /api/kr/ai-history-dates` - 분석 가능 날짜
  - [ ] `GET /api/kr/ai-history/{date}` - 특정 날짜 분석
  - [ ] `POST /api/kr/ai-analyze/{ticker}` - AI 분석 트리거

- [ ] `routes/performance.py` - 성과 지표 엔드포인트
  - [ ] `GET /api/kr/performance/cumulative` - 누적 수익률
  - [ ] `GET /api/kr/performance/by-signal` - 시그널별 성과
  - [ ] `GET /api/kr/performance/by-period` - 기간별 성과
  - [ ] `GET /api/kr/performance/top-performers` - 최고 성과 종목
  - [ ] `GET /api/kr/performance/sharpe-ratio` - 샤프 비율

- [ ] `routes/stocks.py` - 종목 엔드포인트
- [ ] `routes/backtest.py` - 백테스트 엔드포인트
- [ ] `routes/chatbot.py` - 챗봇 엔드포인트
- [ ] `routes/triggers.py` - 스캔 트리거 엔드포인트
- [ ] `routes/system.py` - 시스템 관리 엔드포인트

#### 1.3 에러 응답 문서화
- [ ] 공통 에러 응답 모델 정의
- [ ] 400, 401, 404, 500, 503 응답 예제 추가

### Quality Gate
- [ ] `GET /docs` 접속 시 문서가 정상 표시되는지 확인
- [ ] 모든 엔드포인트에 summary/description 있는지 확인
- [ ] 예제 요청/응답이 포함되어 있는지 확인

### Dependencies
- FastAPI 앱이 실행 가능한 상태

---

## 📝 Phase 2: API 가이드 문서 작성

### Goal
사용자가 API를 쉽게 사용할 수 있도록 가이드 문서를 작성합니다.

### Tasks

#### 2.1 시작 가이드 작성
- [ ] `docs/api/getting-started.md` 생성
  - [ ] 서비스 시작 방법 (docker compose)
  - [ ] API 기본 URL (`http://localhost:5111`)
  - [ ] 인증 방법 (현재: 없음, 향후 예정)
  - [ ] 첫 요청 보내기 예시

#### 2.2 엔드포인트 목록 작성
- [ ] `docs/api/endpoints.md` 생성
  - [ ] 카테고리별 엔드포인트 목록
  - [ ] HTTP Method, 경로, 설명
  - [ ] 필수/선택 파라미터

#### 2.3 사용 예시 작성
- [ ] `docs/api/examples.md` 생성
  - [ ] 시그널 조회 예시
  - [ ] 종목 차트 조회 예시
  - [ ] 수급 데이터 조회 예시
  - [ ] AI 분석 요청 예시
  - [ ] curl, Python, JavaScript 예시

#### 2.4 인증 가이드 (옵션)
- [ ] `docs/api/authentication.md` 생성
  - [ ] 현재 인증 없음 안내
  - [ ] 향후 JWT 인증 계획

### Quality Gate
- [ ] 모든 마크다운 파일이 유효한지 확인
- [ ] 코드 블록에 syntax highlighting 적용
- [ ] curl 예시가 실행 가능한지 확인

### Dependencies
- Phase 1 완료

---

## 📝 Phase 3: Postman Collection 생성

### Goal
Postman에서 바로 import 할 수 있는 Collection을 생성합니다.

### Tasks

#### 3.1 Postman Collection 생성
- [ ] `docs/postman/KR_Stock_API.postman_collection.json` 생성
  - [ ] Collection 정보 (이름, 설명)
  - [ ] 환경 변수 (`base_url`, `ticker` 등)
  - [ ] 폴더 구조 (태그별 분류)

#### 3.2 요청 추가
- [ ] Health Check 폴더
- [ ] Signals 폴더
- [ ] Stocks 폴더
- [ ] AI Analysis 폴더
- [ ] Performance 폴더
- [ ] Backtest 폴더
- [ ] System 폴더

#### 3.3 예제 데이터 추가
- [ ] 각 요청에 예제 파라미터
- [ ] 예제 응답 저장
- [ ] 테스트 스크립트 추가 (선택)

### Quality Gate
- [ ] Postman에서 import 성공 확인
- [ ] 예제 요청이 실행 가능한지 확인

### Dependencies
- Phase 1 완료

---

## 📝 Phase 4: 코드 품질 개선 (P3-3)

### Goal
ruff lint/format와 mypy 타입 검사를 통과합니다.

### Tasks

#### 4.1 ruff lint 확인 및 수정
- [ ] `ruff check .` 실행
- [ ] 발견된 문제 수정
- [ ] 모든 경계 해결

#### 4.2 ruff format 적용
- [ ] `ruff format .` 실행
- [ ] 포맷팅 적용 확인

#### 4.3 mypy 타입 검사
- [ ] `mypy src/` 실행
- [ ] 타입 에러 수정
- [ ] 누락된 타입 힌트 추가

#### 4.4 코드 복잡도 점검
- [ ] cyclomatic complexity가 높은 함수 확인
- [ ] 복잡도가 높은 함수 리팩토링 (선택)

### Quality Gate
- [ ] `ruff check .` 통과 (에러 0)
- [ ] `ruff format .` 적용 완료
- [ ] `mypy src/` 주요 에러 해결
- [ ] 기존 테스트 통과 확인

### Dependencies
- Phase 1-3 완료

---

## 📊 Risk Assessment

| Risk | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| OpenAPI 스펙 작성 시간 초과 | Medium | Low | 우선순위 높은 엔드포인트만 먼저 작성 |
| 문서 업데이트 누락 | Medium | Low | 코드 변경 시 문서 업데이트 체크리스트 추가 |
| mypy 에러 과다 | High | Medium | 라이브러리 코드는 `# type: ignore` 사용 |

---

## 🔄 Rollback Strategy

### Phase 1-2 (문서화)
- 문서 파일만 추가/수정하므로 코드 롤백 불필요
- `git checkout`로 문서 파일만 되돌릴 수 있음

### Phase 4 (코드 품질)
- 변경 전 브랜치 생성: `git checkout -b p3-code-quality`
- 문제 발생 시 `git merge --abort` 후 수정 재개

---

## 📈 진행 상황

### 완료된 작업
- [x] P3-1: 테스트 커버리지 향상 (76%)

### 진행 중 작업
- [ ] Phase 1: OpenAPI 스펙 보강
- [ ] Phase 2: API 가이드 문서 작성
- [ ] Phase 3: Postman Collection 생성
- [ ] Phase 4: 코드 품질 개선

### Last Updated
2026-01-28

---

## 📝 Notes & Learnings

1. FastAPI는 자동으로 OpenAPI 문서를 생성하지만, `summary`와 `description`을 추가하면 가독성이 크게 향상됩니다.
2. Postman Collection을 JSON으로 내보내면 팀원 간 공유가 용이합니다.
3. ruff는 black/isort를 대체할 수 있는 빠른 Python lint/formatter입니다.
4. mypy는 순차적으로 적용하며, 라이브러리 코드는 `# type: ignore`를 활용합니다.
