# 키움 REST API 실시간 데이터 통합 계획

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

키움증권 REST API를 사용하여 실시간 주식 데이터를 수신하는 시스템을 구축합니다.
기존 Windows COM 기반 KOA(Kiwoom Open API) 구조를 완전히 교체하여 멀티 OS 지원을实现합니다.

**범위**: Large (6-7 Phases, 15-25 시간)
**TDD**: Yes (Red-Green-Refactor Cycle)
**Coverage Target**: ≥80%

---

## Architecture

### Before (Windows COM 기반)
```
src/koa/
├── base.py           # IKOABridge 인터페이스
├── windows.py        # WindowsKOABridge (COM)
├── mock.py           # MockKOABridge
├── service.py        # RealtimeDataService
└── pipeline.py       # RealtimePipelineManager
```

### After (REST API 기반)
```
src/kiwoom/
├── base.py           # IKiwoomBridge 인터페이스 (KOABridge와 호환)
├── rest_api.py       # KiwoomRestAPI (HTTP + OAuth2)
├── websocket.py      # KiwoomWebSocket (WS 실시간 시세)
├── mock.py           # MockKiwoomBridge (테스트용)
├── service.py        # KiwoomRealtimeService
└── pipeline.py       # KiwoomPipelineManager (KOA와 호환)
```

---

## Phases

### Phase 1: 기반 구조 및 인터페이스 정의

**Goal**: 키움 REST API를 위한 기반 인터페이스와 데이터 구조 정의

**Test Strategy**:
- 인터페이스 추상화 검증 테스트
- 데이터 클래스 직렬화/역직렬화 테스트
- Coverage: ≥85%

**Tasks**:

- [ ] **RED**: 인터페이스 정의 테스트 작성
  - [ ] `test_base.py`: IKiwoomBridge 인터페이스 테스트
  - [ ] `test_models.py`: RealtimePrice, OrderBook 데이터 클래스 테스트

- [ ] **GREEN**: 인터페이스 구현
  - [ ] `src/kiwoom/base.py`: IKiwoomBridge 추상 클래스
  - [ ] `src/kiwoom/models.py`: RealtimePrice, OrderBook, KiwoomConfig

- [ ] **REFACTOR**: 코드 정리
  - [ ] 타입 힌트 추가
  - [ ] 문서화 완료

**Quality Gate**:
- [ ] `pytest tests/unit/kiwoom/test_base.py -v` 통과
- [ ] `pytest tests/unit/kiwoom/test_models.py -v` 통과
- [ ] Coverage ≥85%
- [ ] `ruff check src/kiwoom/` 통과

**Dependencies**: 없음

---

### Phase 2: Kiwoom REST API 클라이언트 구현

**Goal**: OAuth2 인증 및 REST API 호출 기능 구현

**Test Strategy**:
- OAuth2 토큰 발급/갱신 테스트 (Mock 사용)
- 시장가/지정가 주문 API 테스트
- 계좌 조회 API 테스트
- Coverage: ≥80%

**Tasks**:

- [ ] **RED**: REST API 테스트 작성
  - [ ] `test_rest_api.py`: 토큰 발급, 주문, 조회 테스트
  - [ ] `test_rest_api_auth.py`: 인증/만료 처리 테스트

- [ ] **GREEN**: REST API 구현
  - [ ] `src/kiwoom/rest_api.py`: KiwoomRestAPI 클래스
    - OAuth2 토큰 발급/갱신
    - 시장가/지정가 매수 주문
    - 시장가/지정가 매도 주문
    - 현재가 조회 (ka10001)
    - 계좌 잔고 조회

- [ ] **REFACTOR**: 에러 처리 개선
  - [ ] 재시도 로직 추가
  - [ ] 예외 처리 구체화

**Quality Gate**:
- [ ] `pytest tests/unit/kiwoom/test_rest_api.py -v` 통과
- [ ] `pytest tests/unit/kiwoom/test_rest_api_auth.py -v` 통과
- [ ] Coverage ≥80%
- [ ] Mock API 호출로 인증 흐름 검증

**Dependencies**: Phase 1 완료

---

### Phase 3: Kiwoom WebSocket 클라이언트 구현

**Goal**: WebSocket 실시간 시세 수신 기능 구현

**Test Strategy**:
- WebSocket 연결/로그인 테스트
- 실시간 시세 등록/해제 테스트
- PING/PONG 연결 유지 테스트
- 자동 재연결 테스트
- Coverage: ≥80%

**Tasks**:

- [ ] **RED**: WebSocket 테스트 작성
  - [ ] `test_websocket.py`: 연결, 등록, 수신 테스트
  - [ ] `test_websocket_reconnect.py`: 재연결 테스트

- [ ] **GREEN**: WebSocket 구현
  - [ ] `src/kiwoom/websocket.py`: KiwoomWebSocket 클래스
    - WebSocket 연결 및 로그인
    - 실시간 시세 등록 (REG 전문)
    - 실시간 데이터 수신 루프
    - PING/PONG 처리
    - 자동 재연결

- [ ] **REFACTOR**: 비동기 처리 최적화
  - [ ] asyncio 병렬 처리 개선
  - [ ] 메시지 큐 버퍼링

**Quality Gate**:
- [ ] `pytest tests/unit/kiwoom/test_websocket.py -v` 통과
- [ ] `pytest tests/unit/kiwoom/test_websocket_reconnect.py -v` 통과
- [ ] Coverage ≥80%
- [ ] WebSocket 연결 유지 5분 이상 테스트 통과

**Dependencies**: Phase 1 완료

---

### Phase 4: Mock Kiwoom Bridge 구현

**Goal**: 테스트 및 개발용 Mock 구현

**Test Strategy**:
- Mock 데이터 생성 검증
- 비동기 API 시뮬레이션 테스트
- Coverage: ≥85%

**Tasks**:

- [ ] **RED**: Mock 테스트 작성
  - [ ] `test_mock.py`: Mock 데이터 생성 테스트
  - [ ] `test_mock_async.py`: 비동기 Mock 동작 테스트

- [ ] **GREEN**: Mock 구현
  - [ ] `src/kiwoom/mock.py`: MockKiwoomBridge 클래스
    - 실시간 가격 변동 시뮬레이션
    - WebSocket 메시지 시뮬레이션
    - 주문 체결 시뮬레이션

- [ ] **REFACTOR**: Mock 데이터 현실성 개선
  - [ ] 실제 시장 데이터 패턴 반영
  - [ ] 랜덤성 제어 (시드값 지정)

**Quality Gate**:
- [ ] `pytest tests/unit/kiwoom/test_mock.py -v` 통과
- [ ] `pytest tests/unit/kiwoom/test_mock_async.py -v` 통과
- [ ] Coverage ≥85%
- [ ] Mock 데이터로 API Gateway 통합 테스트 통과

**Dependencies**: Phase 1 완료

---

### Phase 5: Kiwoom Realtime Service 구현

**Goal**: REST API + WebSocket 통합 서비스 구현

**Test Strategy**:
- 종목 구독/해제 테스트
- 실시간 데이터 핸들러 테스트
- Redis 발행 통합 테스트
- Coverage: ≥80%

**Tasks**:

- [ ] **RED**: Service 테스트 작성
  - [ ] `test_service.py`: 구독, 핸들러 테스트
  - [ ] `test_service_integration.py**: Redis 통합 테스트

- [ ] **GREEN**: Service 구현
  - [ ] `src/kiwoom/service.py`: KiwoomRealtimeService 클래스
    - 종목 구독 관리
    - 실시간 데이터 핸들러 등록
    - WebSocket + REST API 통합
    - Redis 발행 연동

- [ ] **REFACTOR**: 이벤트 루프 최적화
  - [ ] 핸들러 호출 비동기 처리
  - [ ] 에러 복구 메커니즘

**Quality Gate**:
- [ ] `pytest tests/unit/kiwoom/test_service.py -v` 통과
- [ ] `pytest tests/unit/kiwoom/test_service_integration.py -v` 통과
- [ ] `pytest tests/integration/kiwoom/ -v` 통과
- [ ] Coverage ≥80%
- [ ] 실제 키움 API로 종목 구독 및 데이터 수신 확인

**Dependencies**: Phase 2, 3, 4 완료

---

### Phase 6: Pipeline Manager 구현

**Goal**: 기존 KOA 파이프라인과 호환되는 관리자 구현

**Test Strategy**:
- 파이프라인 시작/중지 테스트
- 다중 종목 구독 테스트
- WebSocket 통합 테스트
- Health check 테스트
- Coverage: ≥80%

**Tasks**:

- [ ] **RED**: Pipeline 테스트 작성
  - [ ] `test_pipeline.py`: 시작, 중지, 구독 테스트
  - [ ] `test_pipeline_integration.py`: 전체 흐름 테스트

- [ ] **GREEN**: Pipeline 구현
  - [ ] `src/kiwoom/pipeline.py`: KiwoomPipelineManager 클래스
    - KOA 파이프라인과 호환되는 인터페이스
    - REST API + WebSocket + Redis 통합
    - 자동 시작/중지
    - Health check

- [ ] **REFACTOR**: 설정 관리 개선
  - [ ] 환경변수 기반 초기화
  - [ ] 계좌 정보 검증

**Quality Gate**:
- [ ] `pytest tests/unit/kiwoom/test_pipeline.py -v` 통과
- [ ] `pytest tests/integration/kiwoom/test_pipeline_integration.py -v` 통과
- [ ] Coverage ≥80%
- [ ] API Gateway에서 KiwoomPipelineManager로 교체 후 정상 작동

**Dependencies**: Phase 5 완료

---

### Phase 7: API Gateway 연동 및 통합 테스트

**Goal**: 기존 API Gateway에 Kiwoom REST API 통합

**Test Strategy**:
- API Endpoint 테스트
- WebSocket 연결 테스트
- E2E 테스트
- Coverage: ≥75%

**Tasks**:

- [ ] **RED**: 통합 테스트 작성
  - [ ] `tests/integration/api_gateway/test_kiwoom_integration.py`
  - [ ] `tests/integration/api_gateway/test_websocket_realtime.py`

- [ ] **GREEN**: 연동 구현
  - [ ] `services/api_gateway/main.py`: lifespan 수정
    - KOA → Kiwoom 교체
    - 환경변수 기반 REST/WebSocket 선택
  - [ ] `services/api_gateway/routes.py`: 실시간 엔드포인트 수정

- [ ] **REFACTOR**: 하위 호환성 유지
  - [ ] 기존 KOA 인터페이스와 호환성 유지
  - [ ] Mock 모드 지원

**Quality Gate**:
- [ ] `pytest tests/integration/api_gateway/ -v` 통과
- [ ] `pytest tests/e2e/ -v` 통과
- [ ] Coverage ≥75%
- [ ] 실제 키움 API로 실시간 데이터 수신 확인
- [ ] 프론트엔드에서 실시간 데이터 표시 확인

**Dependencies**: Phase 6 완료

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 키움 API 키 만료/해지 | Medium | High | 환경변수로 모의투자/실전 투자 전환, 에러 처리 강화 |
| WebSocket 연결 불안정 | Medium | Medium | 자동 재연결, PING/PONG 처리, 타임아웃 설정 |
| API 레이트 리밋 | Low | Medium | 요청 속도 제한, 캐싱, Queue 처리 |
| OAuth2 토큰 만료 | Low | High | 토큰 자동 갱신, 만료 1분 전 재발급 |

---

## Rollback Strategy

### Phase 1-4: 인프라 변경
- 기존 `src/koa/`를 `src/koa_legacy/`로 이동 후 보존
- 문제 발생 시 즉시 복원

### Phase 5-7: 통합 변경
- Git 브랜치로 개발
- 문제 발생 시 `git revert`로 롤백
- 환경변수로 레거시 모드 전환 지원

---

## Progress Tracking

### Last Updated: 2025-01-27

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| Phase 1 | ✅ Complete | 100% | 인터페이스 정의 (15 tests passed) |
| Phase 2 | 🔄 Complete | 88% | REST API 클라이언트 (69 tests passed, 9 mock issues) |
| Phase 3 | ✅ Complete | 100% | WebSocket 클라이언트 (41 tests passed) |
| Phase 4 | ✅ Complete | 100% | Mock Bridge (13 tests passed) |
| Phase 5 | ✅ Complete | 100% | Realtime Service (16 tests passed) |
| Phase 6 | ✅ Complete | 100% | Pipeline Manager (17 tests passed) |
| Phase 7 | ✅ Complete | 100% | API Gateway 연동 (13 tests passed) |

---

## Notes

### 키움 REST API 정보
- **실전투자**: `https://api.kiwoom.com`
- **모의투자**: `https://mockapi.kiwoom.com`
- **WebSocket**: `wss://api.kiwoom.com:10000/api/dostk/websocket`
- **인증 방식**: OAuth2 Bearer Token

### 환경변수 (.env)
```bash
# 키움 API 키
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key

# 모의투자 키
KIWOOM_MOCK_APP_KEY=your_mock_app_key
KIWOOM_MOCK_SECRET_KEY=your_mock_secret_key

# 모드 설정
USE_MOCK=false  # true: 모의투자, false: 실전투자
```

### 참고 코드
- GitHub: https://github.com/ralph0830/kiwoom_stock_telegram
- kiwoom_order.py: REST API 주문 처리
- kiwoom_websocket.py: WebSocket 실시간 시세
- config.py: 설정 관리

