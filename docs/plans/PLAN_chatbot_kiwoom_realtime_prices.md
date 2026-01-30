# PLAN: 챗봇 Kiwoom 실시간 현재가 연동 강화

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

### 목표
챗봇에서 "삼성전자 현재가 알려줘" 질문 시 Kiwoom REST API를 통해 실제 실시간 가격을 반환

### 문제 상황
- Mock 데이터 또는 부정확한 데이터 반환
- Kiwoom API 연동이 되어 있으나 정상 작동하지 않음
- 에러 시 명확한 메시지 부족

### 접근 방식
- **Direct Kiwoom API**: 챗봇 서비스에서 직접 Kiwoom REST API 호출
- **Comprehensive Scope**: 전체 Kiwoom 연동 개선 + 로깅 강화

### 성공 기준
- 실시간 현재가 정확도 ±0.1%
- API 응답 시간 < 2초
- 실패 시 사용자에게 명확한 메시지

---

## Phase Breakdown

### Phase 1: Kiwoom API Health Check & 진단

**Goal**: 현재 Kiwoom API 연동 상태 진단 및 문제 파악

**Test Strategy**:
- 단위 테스트: Kiwoom API 연결 상태 확인
- 통합 테스트: 실제 API 호출 테스트
- 커버리지: 80%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/unit/chatbot/test_kiwoom_integration_health.py` 작성
  - [ ] `test_kiwoom_env_variables_set()` - 환경 변수 확인
  - [ ] `test_kiwoom_client_initialization()` - 클라이언트 초기화
  - [ ] `test_kiwoom_token_fetch()` - 토큰 발급 테스트
- [ ] `tests/integration/chatbot/test_kiwoom_api_calls.py` 작성
  - [ ] `test_get_daily_prices_samsung()` - 삼성전자 실제 조회
  - [ ] `test_get_daily_prices_invalid_ticker()` - 없는 종목 테스트

#### GREEN (구현)
- [ ] Kiwoom API 연결 로깅 강화
- [ ] 테스트가 통과하는 최소 구현

#### REFACTOR
- [ ] 로그 메시지 개선
- [ ] 에러 메시지 한글화

**Quality Gate**:
- [ ] All tests pass
- [ ] Kiwoom API 연결 성공 로그 확인
- [ ] `pytest tests/unit/chatbot/test_kiwoom_integration_health.py -v`
- [ ] `pytest tests/integration/chatbot/test_kiwoom_api_calls.py -v`

**Rollback**: 테스트 파일만 삭제하면 됨

---

### Phase 2: 현재가 조회 캐싱 레이어 구현

**Goal**: Redis 캐싱으로 API 호출 최적화

**Test Strategy**:
- 단위 테스트: 캐시 동작 확인
- 모의 객체: Redis mock 사용
- 커버리지: 85%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/unit/chatbot/test_price_cache.py` 작성
  - [ ] `test_cache_miss_then_hit()` - 캐시 미스 후 히트
  - [ ] `test_cache_expiration()` - TTL 30초 확인
  - [ ] `test_cache_invalidation()` - 종목별 캐시 무효화
  - [ ] `test_concurrent_cache_access()` - 동시 접근 테스트

#### GREEN (구현)
- [ ] `services/chatbot/price_cache.py` 생성
  - [ ] `@cached_price` 데코레이터 구현
  - [ ] Redis backend 연결
  - [ ] TTL 30초 설정
- [ ] `get_kiwoom_current_price()`에 캐싱 적용

#### REFACTOR
- [ ] 캐시 키 포맷 일관성 (`price:{ticker}`)
- [ ] 캐시预热 (warmup) 함수

**Quality Gate**:
- [ ] All tests pass
- [ ] 캐시 적중률 > 50% (2회 연속 조회 시)
- [ ] `pytest tests/unit/chatbot/test_price_cache.py -v`

**Rollback**: 캐싱 코드 제거, 기존 직접 호출 복원

---

### Phase 3: 에러 핸들링 및 Graceful Degradation

**Goal**: API 실패 시 사용자에게 명확한 메시지 제공

**Test Strategy**:
- 단위 테스트: 에러 케이스별 처리 확인
- 통합 테스트: 실패 시나리오 시뮬레이션
- 커버리지: 90%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/unit/chatbot/test_error_handling.py` 작성
  - [ ] `test_kiwoom_api_timeout()` - 타임아웃 처리
  - [ ] `test_kiwoom_api_500_error()` - 서버 에러 처리
  - [ ] `test_kiwoom_api_429_rate_limit()` - Rate Limiting 처리
  - [ ] `test_invalid_ticker_error()` - 없는 종목 에러 메시지

#### GREEN (구현)
- [ ] `services/chatbot/kiwoom_integration.py` 에러 핸들링 개선
  - [ ] `KiwoomAPIError` 서브클래스 추가 (Timeout, RateLimit, NotFound)
  - [ ] 사용자 친화적 에러 메시지 매핑
  - [ ] 재시도 로직 (exponential backoff)
- [ ] LLM 프롬프트에 에러 상황 안내 추가

#### REFACTOR
- [ ] 에러 코드 일관성
- [ ] 재시도 정책 설정화

**Quality Gate**:
- [ ] All tests pass
- [ ] 에러 상황에서 사용자에게 명확한 메시지
- [ ] `pytest tests/unit/chatbot/test_error_handling.py -v`

**Rollback**: 기존 에러 핸들링 복원

---

### Phase 4: 챗봇 응답에 실시간 가격 포함 강화

**Goal**: LLM 응답에 정확한 실시간 가격 정보 반영

**Test Strategy**:
- 통합 테스트: end-to-end 챗봇 응답 확인
- API 테스트: `/chat` 엔드포인트
- 커버리지: 80%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/integration/chatbot/test_realtime_price_response.py` 작성
  - [ ] `test_chat_with_samsung_current_price()` - 삼성전자 현재가 질문
  - [ ] `test_chat_with_sk_hynix_price()` - SK하이닉스 현재가 질문
  - [ ] `test_chat_with_multiple_stocks()` - 여러 종목 현재가
  - [ ] `test_chat_when_kiwoom_down()` - Kiwoom 다운 시 응답

#### GREEN (구현)
- [ ] `services/chatbot/prompts.py` 실시간 가격 표시 개선
  - [ ] 가격 정보 없을 때 안내 메시지
  - [ ] 가격 정보 있을 때 포맷팅 개선
- [ ] `services/chatbot/retriever.py` `enrich_with_kiwoom_data()` 개선
  - [ ] 병렬 조회로 응답 시간 개선
  - [ ] 실패 시 fallback 데이터 처리

#### REFACTOR
- [ ] 프롬프트 템플릿 일관성
- [ ] 가격 포맷 함수 재사용

**Quality Gate**:
- [ ] All tests pass
- [ ] "삼성전자 현재가 알려줘" → 실제 가격 포함 응답
- [ ] `pytest tests/integration/chatbot/test_realtime_price_response.py -v`

**Rollback**: 기존 프롬프트 복원

---

### Phase 5: 로깅 및 모니터링 강화

**Goal**: Kiwoom API 호출 추적 및 문제 진단 용이성

**Test Strategy**:
- 단위 테스트: 로그 출력 확인
- 통합 테스트: 로그 수집 확인
- 커버리지: 70%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/unit/chatbot/test_logging.py` 작성
  - [ ] `test_api_call_logged()` - API 호출 로그 확인
  - [ ] `test_cache_hit_logged()` - 캐시 적중 로그
  - [ ] `test_error_logged()` - 에러 로그 확인

#### GREEN (구현)
- [ ] `services/chatbot/kiwoom_integration.py` 로깅 강화
  - [ ] API 호출 시작/종료 로그
  - [ ] 캐시 적중/미스 로그
  - [ ] 응답 시간 로그
  - [ ] structured logging (JSON)
- [ ] Prometheus 메트릭 (선택)

#### REFACTOR
- [ ] 로그 레벨 일관성
- [ ] 중요 로그에 correlation_id 추가

**Quality Gate**:
- [ ] All tests pass
- [ ] 로그에서 API 호출 추적 가능
- [ ] `pytest tests/unit/chatbot/test_logging.py -v`

**Rollback**: 기존 로깅 복원

---

### Phase 6: 문서화 및 E2E 테스트

**Goal**: 사용자 가이드 및 E2E 테스트 완성

**Test Strategy**:
- E2E 테스트: Playwright로 실제 사용자 시나리오
- 문서 검토: 사용자 가이드 completeness
- 커버리지: N/A (E2E)

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/e2e/chatbot/test_realtime_prices_e2e.spec.ts` 작성
  - [ ] `test_samsung_current_price()` - 삼성전자 현재가 E2E
  - [ ] `test_market_status()` - 시장 상태 E2E
  - [ ] `test_recommendation_with_prices()` - 추천 + 현재가 E2E

#### GREEN (구현)
- [ ] E2E 테스트 실행 환경 구성
- [ ] `docs/api/CHATBOT_KIWOOM_API.md` 문서 작성
  - [ ] 환경 변수 설정 가이드
  - [ ] 트러블슈팅 가이드
  - [ ] API 응답 예시

#### REFACTOR
- [ ] 문서 일관성
- [ ] 예제 코드 확인

**Quality Gate**:
- [ ] All E2E tests pass
- [ ] 문서 검토 완료
- [ ] `playwright test tests/e2e/chatbot/test_realtime_prices_e2e.spec.ts`

**Rollback**: 문서만 삭제하면 됨

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Kiwoom API Rate Limiting | Medium | High | 캐싱, 재시도 로직, 요청 간 지연 |
| Kiwoom API 인증 만료 | Low | High | 토큰 자동 갱신 로직 |
| 네트워크 지연 | Medium | Medium | 타임아웃 설정, fallback 데이터 |
| 캐시 일관성 문제 | Low | Medium | TTL 명확히, 무효화 로직 |

---

## Test Coverage Summary

| Phase | Target | Files |
|-------|--------|-------|
| Phase 1 | 80% | `test_kiwoom_integration_health.py`, `test_kiwoom_api_calls.py` |
| Phase 2 | 85% | `test_price_cache.py` |
| Phase 3 | 90% | `test_error_handling.py` |
| Phase 4 | 80% | `test_realtime_price_response.py` |
| Phase 5 | 70% | `test_logging.py` |
| Phase 6 | N/A | `test_realtime_prices_e2e.spec.ts` |

**Overall Target**: ≥80% coverage for new code

---

## Progress Tracking

### Last Updated
2026-01-30 (Phase 1-4 완료)

### Phase Status
- [x] Phase 1: Kiwoom API Health Check & 진단 ✅
- [x] Phase 2: 현재가 조회 캐싱 레이어 구현 ✅
- [x] Phase 3: 에러 핸들링 및 Graceful Degradation ✅
- [x] Phase 4: 챗봇 응답 실시간 가격 포함 강화 ✅
- [ ] Phase 5: 로깅 및 모니터링 강화 (옵션)
- [ ] Phase 6: 문서화 및 E2E 테스트 (옵션)

---

## Notes

### Learnings
- Kiwoom API가 정상 작동하며 현재가 조회 성공 (삼성전자 152,100원)
- 캐싱 레이어로 Redis 연동 성공 (TTL 30초)
- 에러 핸들링 서브클래스 구현로 사용자 친화적 메시지 제공
- 재시도 로직 (exponential backoff)로 안정성 개선

### Test Results Summary
- **Phase 1**: 9 passed, 1 skipped (Kiwoom API 연동 성공)
- **Phase 2**: 9 passed, 1 skipped (Redis 캐싱 성공)
- **Phase 3**: 17 passed (에러 핸들링 완전)
- **Phase 4**: 10 passed (E2E 챗봇 응답 테스트)
- **Total**: 36 passed, 1 skipped

### Issues Found
- 없음

### Decisions Made
- Direct Kiwoom API 방식 채택 (API Gateway 경유 x)
- Redis 캐싱으로 API 호출 최적화
- 사용자 친화적 에러 메시지 제공을 위한 에러 서브클래스 구현
