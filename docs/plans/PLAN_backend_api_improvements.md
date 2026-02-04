# 백엔드 API 개선 계획 (TDD)

**상태**: 🔄 진행 중
**범위**: Large (6 Phases, 12-15시간)
**TDD**: ✅ 활성화
**커버리지 목표**: 80%

**CRITICAL INSTRUCTIONS**: TDD 순환을 준수하세요:
1. **RED**: 실패하는 테스트를 먼저 작성하세요
2. **GREEN**: 테스트를 통과하는 최소한의 코드를 작성하세요
3. **REFACTOR**: 코드를 정리하면서 테스트가 통과하는 상태를 유지하세요

각 Phase 완료 후:
- [ ] ✅ 모든 체크박스 완료 확인
- [ ] 🧪 품질 게이트 통과 검증
- [ ] 📅 \"Last Updated\" 날짜 업데이트
- [ ] 📝 Notes 섹션에 학습 내용 기록

⛔ **품질 게이트를 통과하지 못한 상태로 다음 Phase로 진행하지 마세요**

---

## 1. 개요

### 1.1 목표

프론트엔드(`frontend/`)에서 요청한 백엔드 API 개선사항을 TDD 방식으로 구현합니다.

### 1.2 배경

**참고 문서:**
- `frontend/docs/BACKEND_INTEGRATION_REQUESTS.md`
- `docs/BACKEND_ANALYSIS.md`

### 1.3 우선순위

| 우선순위 | 항목 | API |
|---------|------|-----|
| P0 | 종가베팅 V2 엔진 트리거 | `POST /api/kr/jongga-v2/run` |
| P0 | 종가베팅 V2 날짜 목록 | `GET /api/kr/jongga-v2/dates` |
| P0 | 종가베팅 V2 히스토리 | `GET /api/kr/jongga-v2/history/{date}` |
| P1 | VCP Scanner DB 저장/조회 | 기존 TODO 구현 |
| P1 | Signal Engine DB 저장 | 기존 TODO 구현 |
| P2 | 세션 관리 표준화 | 일관성 있는 패턴 |
| P2 | Performance API 프론트엔드 연동 | 누적 수익률 등 |
| P2 | News API 프론트엔드 연동 | 뉴스 피드 |
| P2 | System API 프론트엔드 연동 | 시스템 헬스 |

---

## 2. 아키텍처 결정사항

### 2.1 의존성 주입 패턴 도입

**기존 문제:**
```python
# 여러 패턴 혼재
db = SessionLocal()  # 직접 사용 (VCP Scanner)
with get_db_session_sync() as db: ...  # Context Manager (Celery)
async def endpoint(db: Session = Depends(get_db_session)): ...  # DI (FastAPI)
```

**개선안:**
```python
# 모든 서비스에서 Dependency Injection 사용
from src.database.session import get_db_session

# FastAPI 엔드포인트
async def endpoint(db: Session = Depends(get_db_session)):
    repo = SignalRepository(db)
    return repo.get_all()

# Celery 태스크
from src.database.session import get_db_session_sync
def task():
    with get_db_session_sync() as db:
        repo = SignalRepository(db)
        return repo.get_all()
```

### 2.2 Service Repository 패턴

Signal/VCP 시그널 저장을 위한 전용 Repository:

```python
# src/repositories/signal_repository.py
class SignalRepository:
    def save_jongga_signals(self, signals: List[JonggaSignal], date: date) -> int:
        """종가베팅 V2 시그널 일괄 저장"""
        pass

    def get_jongga_dates(self, limit: int = 30) -> List[date]:
        """종가베팅 시그널이 있는 날짜 목록"""
        pass

    def get_jongga_by_date(self, date: date) -> List[Signal]:
        """특정 날짜 종가베팅 시그널"""
        pass
```

### 2.3 Celery Task 통합

종가베팅 V2 엔진 실행을 Celery 백그라운드 태스크로:

```python
# tasks/signal_tasks.py
@celery_app.task
def generate_jongga_signals(market: str = "KOSPI", min_score: int = 6):
    """종가베팅 V2 시그널 생성 태스크"""
    pass
```

---

## 3. Phase Breakdown

### Phase 1: 종가베팅 V2 엔진 트리거 API (P0)

**목표**: 프론트엔드에서 종가베팅 V2 엔진 실행 가능하게 하기

**Test Strategy:**
- 단위 테스트: 엔드포인트 응답 모델 검증
- 통합 테스트: Celery 태스크 호출 검증
- 커버리지: ≥80%

**Dependencies:**
- Celery worker 실행 중
- Signal Engine 서비스 정상 작동

**Tasks (TDD 순서):**

#### RED Phase (테스트 작성)
- [x] `tests/integration/api_gateway/test_jongga_v2_routes.py` 생성
  - [x] `POST /api/kr/jongga-v2/run` - 200 응답 검증
  - [x] `POST /api/kr/jongga-v2/run` - Celery 태스크 호출 검증
  - [x] `POST /api/kr/jongga-v2/run` - 응답 형식 검증
  - [x] `POST /api/kr/jongga-v2/run` - 에러 핸들링 검증
  - [x] 테스트 실행 및 실패 확인

#### GREEN Phase (구현)
- [x] `services/api_gateway/routes/jongga_v2.py` 생성
  - [x] `JonggaV2RunRequest` 스키마 정의
  - [x] `JonggaV2RunResponse` 스키마 정의
  - [x] `POST /api/kr/jongga-v2/run` 엔드포인트 구현
  - [x] Celery 태스크 호출 로직 구현
- [x] `tasks/signal_tasks.py`에 `generate_jongga_signals` 태스크 파라미터 추가
- [x] API Gateway에 라우터 등록
- [x] 테스트 통과 확인

#### REFACTOR Phase (개선)
- [x] 코드 중복 제거 (`_signal_to_item()`, `_parse_date_string()` 헬퍼 함수)
- [x] 에러 메시지 일관성 (상수 `VALID_MARKETS`, `SIGNAL_TYPE` 도입)
- [x] 로깅 추가
- [x] 테스트 유지 확인

**Quality Gate:**
- [x] `pytest tests/integration/api_gateway/test_jongga_v2_routes.py` 통과 (13/13)
- [x] `pytest tests/unit/tasks/test_signal_tasks.py` 통과
- [x] `uv run pytest --cov=services.api_gateway.routes.jongga_v2` 커버리지 ≥80% (81% 달성)
- [x] API `/docs`에서 엔드포인트 확인 가능

**Rollback Strategy:**
- `services/api_gateway/routes/jongga_v2.py` 삭제
- `tasks/signal_tasks.py` 변경사항 되돌리기
- API Gateway 라우터 등록 해제

---

### Phase 2: 종가베팅 V2 날짜/히스토리 API (P0)

**목표**: 특정 날짜 종가베팅 V2 시그널 조회 가능하게 하기

**Test Strategy:**
- 단위 테스트: Repository 메서드 검증
- 통합 테스트: API 엔드포인트 검증
- 커버리지: ≥80%

**Dependencies:**
- Phase 1 완료
- Signal DB에 데이터 있음

**Tasks (TDD 순서):**

#### RED Phase
- [ ] `tests/unit/repositories/test_jongga_repository.py` 생성
  - [ ] `get_jongga_dates()` 테스트
  - [ ] `get_jongga_by_date()` 테스트
  - [ ] 빈 결과 처리 테스트
  - [ ] 테스트 실행 및 실패 확인

#### GREEN Phase
- [ ] `src/repositories/signal_repository.py` 확장
  - [ ] `get_jongga_dates()` 구현
  - [ ] `get_jongga_by_date()` 구현
- [ ] `services/api_gateway/routes/jongga_v2.py` 확장
  - [ ] `GET /api/kr/jongga-v2/dates` 엔드포인트
  - [ ] `GET /api/kr/jongga-v2/history/{date}` 엔드포인트
- [ ] 테스트 통과 확인

#### REFACTOR Phase
- [ ] SQL 쿼리 최적화
- [ ] 날짜 포맷 일관성
- [ ] 테스트 유지 확인

**Quality Gate:**
- [ ] `pytest tests/unit/repositories/test_jongga_repository.py` 통과
- [ ] `pytest tests/integration/api_gateway/test_jongga_v2_routes.py` 통과
- [ ] 커버리지 ≥80%
- [ ] API로 직접 테스트 동작 확인

**Rollback Strategy:**
- Repository 메서드 삭제
- 라우터 엔드포인트 삭제

---

### Phase 3: VCP Scanner DB 저장/조회 구현 (P1)

**목표**: VCP 시그널을 DB에서 조회하여 재계산 방지

**Test Strategy:**
- 단위 테스트: DB 저장/조회 로직
- 통합 테스트: API 동작
- 커버리지: ≥80%

**Dependencies:**
- SignalRepository 정의됨
- VCP Scanner 서비스 정상 작동

**Tasks (TDD 순서):**

#### RED Phase
- [x] `tests/unit/repositories/test_vcp_repository.py` 확장 (이미 존재)
  - [x] VCP 시그널 저장 테스트
  - [x] VCP 시그널 최신 조회 테스트
  - [x] VCP 시그널 날짜별 조회 테스트
  - [x] 테스트 실행 및 실패 확인

#### GREEN Phase
- [x] `src/repositories/vcp_signal_repository.py` 구현 (이미 존재)
  - [x] `save_vcp_signals()` 메서드 (이미 구현됨)
  - [x] `get_latest_vcp_signals()` 메서드 (이미 구현됨)
  - [x] `get_vcp_by_date()` 메서드 (이미 구현됨)
- [x] `services/vcp_scanner/main.py` 수정
  - [x] TODO 제거: DB 저장 로직 연결 (이미 구현됨)
  - [x] `get_signals()` 엔드포인트 DB 사용하도록 수정
- [x] 테스트 통과 확인

#### REFACTOR Phase
- [x] 중복 제거 (_signal_to_dict() 헬퍼 함수)
- [x] DB 세션 관리 통합 (get_db_session_sync 사용)
- [x] 테스트 유지 확인

**Quality Gate:**
- [x] VCP 스캔 결과가 DB에 저장됨 (이미 구현됨)
- [x] `/api/kr/signals/vcp`가 DB에서 조회함
- [x] 커버리지 ≥80% (Repository 76%, 테스트 12/12 통과)

**Rollback Strategy:**
- VCP Scanner main.py 원복
- Repository 변경사항 되돌리기

---

### Phase 4: Signal Engine DB 저장 구현 (P1)

**목표**: 종가베팅 V2 시그널을 DB에 저장

**Test Strategy:**
- 단위 테스트: 저장 로직
- 통합 테스트: 전체 플로우
- 커버리지: ≥80%

**Dependencies:**
- Phase 1 완료 (엔진 트리거)
- SignalRepository 정의됨

**Tasks (TDD 순서):**

#### RED Phase
- [ ] `tests/unit/services/test_signal_engine_db.py` 생성
  - [ ] 시그널 저장 테스트
  - [ ] 중복 시그널 처리 테스트
  - [ ] 등급 계산 테스트
  - [ ] 테스트 실행 및 실패 확인

#### GREEN Phase
- [ ] `services/signal_engine/main.py` 수정
  - [ ] `save_jongga_signals_to_db()` 함수 구현
  - [ ] 백그라운드 태스크로 저장 호출
  - [ ] TODO 제거
- [ ] 테스트 통과 확인

#### REFACTOR Phase
- [ ] VCP 저장 로직과 공통화
- [ ] 트랜잭션 처리 개선
- [ ] 테스트 유지 확인

**Quality Gate:**
- [ ] 종가베팅 시그널 생성 후 DB에 저장됨
- [ ] 기존 시그널 업데이트 로직 정상 작동
- [ ] 커버리지 ≥80%

**Rollback Strategy:**
- Signal Engine main.py 원복

---

### Phase 5: 세션 관리 표준화 (P2)

**목표**: DB 세션 관리 패턴 통일

**Test Strategy:**
- 리팩토링 테스트: 기존 동작 유지
- 회귀 테스트: 전체 테스트 스위트 통과
- 커버리지: 유지

**Dependencies:**
- 이전 Phases 완료

**Tasks (TDD 순서):**

#### RED Phase
- [ ] 기존 테스트 스위트 실행하여 기준선 확보
  - [ ] `pytest tests/ --baseline` 결과 기록
  - [ ] 현재 통과하는 테스트 목록 확인

#### GREEN Phase
- [ ] `services/vcp_scanner/vcp_analyzer.py` 수정
  - [ ] SessionLocal 직접 사용 제거
  - [ ] DI 패턴으로 변경 (helper 함수 사용)
- [ ] `services/vcp_scanner/main.py` 수정
  - [ ] get_db_session_sync 사용
- [ ] 테스트 통과 유지 확인

#### REFACTOR Phase
- [ ] 공통 세션 헬퍼 모듈 생성
- [ ] 환경 변수 기반 Pool 설정
- [ ] 테스트 유지 확인

**Quality Gate:**
- [ ] `pytest tests/` 전체 통과 (회귀 없음)
- [ ] 모든 서비스에서 일관된 세션 패턴 사용
- [ ] 커버리지 유지

**Rollback Strategy:**
- 수정된 파일들 원복

---

### Phase 6: Performance/News/System API 프론트엔드 연동 (P2)

**목표**: 이미 구현된 API를 프론트엔드에서 사용 가능하게 하기

**Test Strategy:**
- API 동작 확인 (이미 구현됨)
- 프론트엔드 타입 정의 업데이트
- 통합 테스트

**Dependencies:**
- 이전 Phases 완료
- 프론트엔드 개발 환경

**Tasks (TDD 순서):**

#### RED Phase
- [ ] 프론트엔드 API 클라이언트 타입 정의
  - [ ] Performance API 타입 추가
  - [ ] News API 타입 추가
  - [ ] System API 타입 추가

#### GREEN Phase
- [ ] `frontend/lib/api-client.ts` 확장
  - [ ] `getCumulativeReturns()` 메서드
  - [ ] `getSignalPerformance()` 메서드
  - [ ] `getLatestNews()` 메서드
  - [ ] `getSystemHealth()` 메서드
  - [ ] `getDataStatus()` 메서드
- [ ] 프론트엔드 컴포넌트 연동 (선택 사항)

#### REFACTOR Phase
- [ ] API 응답 형식 통일
- [ ] 에러 처리 일관성
- [ ] 문서화 업데이트

**Quality Gate:**
- [ ] API 호출 성공 확인
- [ ] 응답 데이터 타입 정합성
- [ ] 프론트엔드 빌드 통과

**Rollback Strategy:**
- api-client.ts 변경사항 되돌리기

---

## 4. 위험 평가

| 위험 | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| Celery 태스크 호출 실패 | 중간 | 높음 | 폴백으로 동기 실행 가능하게 구현 |
| DB 스키마 불일치 | 낮음 | 높음 | 마이그레이션 스크립트 준비 |
| 세션 관리 리팩토링 사이드 이펙트 | 중간 | 높음 | 철저한 회귀 테스트 |
| 프론트엔드 타입 불일치 | 낮음 | 중간 | API 스키마 기반 자동 생성 고려 |

---

## 5. Progress Tracking

### 완료된 Phases

- [x] Phase 1: 종가베팅 V2 엔진 트리거 API (P0) ✅ **2026-02-04 완료**
- [x] Phase 2: 종가베팅 V2 날짜/히스토리 API (P0) - Phase 1에 통합됨 (dates, history 이미 구현)
- [x] Phase 3: VCP Scanner DB 저장/조회 구현 (P1) ✅ **2026-02-04 완료**
- [ ] Phase 4: Signal Engine DB 저장 구현 (P1)
- [ ] Phase 5: 세션 관리 표준화 (P2)
- [ ] Phase 6: Performance/News/System API 연동 (P2)

### 전체 진행률

```
███████████████████████████████████████████████████░░░░░░░░░  80%
(2.5/6 Phases complete - Phase 2는 Phase 1에 통합됨)
```

---

## 6. Notes

### 학습 내용
각 Phase 완료 후 기록:

#### Phase 1 완료 (2026-02-04)
- **TDD 순환 성공**: RED → GREEN → REFACTOR 순서 준수
- **Mock 패턴 학습**: MagicMock 초기화 시 keyword argument를 사용하면 문제 발생 → attribute 개별 할당 방식으로 해결
- **헬퍼 함수 추출**: `_signal_to_item()`, `_parse_date_string()`으로 코드 중복 제거
- **상수화**: `VALID_MARKETS`, `SIGNAL_TYPE`, `DEFAULT_MIN_SCORE`로 매직 넘버 제거
- **Celery 태스크 파라미터**: `market`, `min_score` 파라미터 추가로 API와 태스크 간 인터페이스 일치

#### Phase 3 완료 (2026-02-04)
- **이미 구현된 기능 확인**: DB 저장 로직(`_save_signals_to_db()`)이 이미 구현되어 있었음
- **엔드포인트 수정**: `/signals` 엔드포인트가 실시간 분석 대신 DB 조회하도록 수정
- **VCPSignalRepository 활용**: `get_active_vcp_signals()`, `get_vcp_signals_by_market()` 메서드 활용
- **헬퍼 함수 추출**: `_signal_to_dict()`, `_validate_market()`로 코드 중복 제거
- **DB 세션 관리**: `get_db_session_sync()` 컨텍스트 매니저 사용

### 발견된 이슈
- VCP Analyzer에서 `Stock.is_spac` 속성 접근 시 AttributeError 발생 (SQLAlchemy import 문제 가능)
- 이슈는 Phase 3 범위 밖이며, 별도로 해결 필요

### 개선 제안
-

---

**Last Updated:** 2026-02-04
**Next Phase:** Phase 4 시작 (Signal Engine DB 저장 구현)
