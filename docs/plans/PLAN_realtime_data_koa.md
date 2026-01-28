# 키움증권 KOA 실시간 데이터 연동

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

한국 주식의 **진짜 실시간 데이터**를 키움증권 KOA(Kiwoom Open API)를 통해 연동합니다.

### 현재 문제
- `pykrx`는 일별 데이터만 제공 (실시간 X)
- DB 데이터는 항상 하루 전 데이터
- Mock 데이터는 랜덤 값으로 부정확함

### 목표
- 키움 KOA를 통한 실시간 체결가/호가 수신
- WebSocket을 통해 프론트엔드에 실시간 전송
- 장 중 실시간 가격 업데이트

---

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  키움 KOA       │ ──▶ │  KOA Bridge     │ ──▶ │  Redis Pub/Sub  │
│  (Kiwoom.exe)   │      │  (Python)       │      │  (Event Bus)    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                         │
                                                         ▼
                                                  ┌─────────────────┐
                                                  │  WebSocket      │
                                                  │  Broadcaster    │
                                                  └─────────────────┘
                                                         │
                                                         ▼
                                                  ┌─────────────────┐
                                                  │   프론트엔드     │
                                                  │  (실시간 업데이트)│
                                                  └─────────────────┘
```

---

## Dependencies

- 키움증권 계좌 (HTS 계좌)
- 키움 OpenAPI+ 설치 (Kiwoom.exe)
- Python `pywin32` (Windows COM 연동)

---

## Phase Breakdown

### Phase 1: KOA 브리지 구조 설계
**Goal**: 키움 KOA와 Python 간 통신 브리지 설계

**Test Strategy:**
- Mock KOA 인터페이스로 테스트
- 브리지 통신 프로토콜 검증

**Tasks:**
- [ ] KOA COM 인터페이스 분석 (Kiwoom.py 참고)
- [ ] Python → KOA 명령 구조 설계
- [ ] KOA → Python 이벤트 핸들러 설계
- [ ] Mock KOA 서버 구현 (테스트용)

**Quality Gate:**
- [ ] Mock KOA 서버와 Python 브리지 통신 성공
- [ ] 이벤트 핸들러 정상 동작 확인
- [ ] 유닛 테스트 통과 (≥80%)

**Coverage Target:** 85%

---

### Phase 2: 실시간 데이터 수신기 구현
**Goal**: 키움 KOA에서 실시간 체결가 수신

**Test Strategy:**
- Mock 실시간 데이터 스트림 생성
- 수신 데이터 파싱/검증 테스트

**Tasks:**
- [ ] KOA 실시간 시세 요청 (SetRealReg)
- [ ] 체결가 데이터 수신 핸들러 (OnReceiveRealData)
- [ ] 호가 데이터 수신 핸들러 (OnReceiveMTRealData)
- [ ] 데이터 포맷 변환 (KOA → 내부 포맷)

**Quality Gate:**
- [ ] Mock KOA로 실시간 데이터 수신 성공
- [ ] 데이터 파싱 정확도 100%
- [ ] 수신 로그 정상 기록

**Coverage Target:** 90%

---

### Phase 3: Redis Pub/Sub 연동
**Goal**: 수신한 실시간 데이터를 Redis에 발행

**Test Strategy:**
- Redis Pub/Sub 통합 테스트
- 데이터 발행/구독 검증

**Tasks:**
- [ ] Redis Pub Producer 구현
- [ ] 채널 구조 설계 (`realtime:price:{ticker}`)
- [ ] 데이터 직렬화/역직렬화
- [ ] 발행 실패 시 재시도 로직

**Quality Gate:**
- [ ] Redis에 실시간 데이터 발행 성공
- [ ] 구독자가 데이터 정상 수신
- [ ] 발행 지연 <100ms

**Coverage Target:** 85%

---

### Phase 4: WebSocket 브로드캐스트 연동
**Goal**: Redis 데이터를 WebSocket으로 전송

**Test Strategy:**
- End-to-End 실시간 데이터 흐름 테스트
- WebSocket 메시지 검증

**Tasks:**
- [ ] Redis Consumer 구현
- [ ] WebSocket 브로드캐스터 연동
- [ ] 기존 price_provider와 통합
- [ ] 실시간 데이터 우선순위 로직 (KOA > DB > Mock)

**Quality Gate:**
- [ ] KOA → Redis → WebSocket → 프론트엔드 흐름 완성
- [ ] 실시간 데이터 지연 <500ms
- [ ] 기존 기능 회귀 없음

**Coverage Target:** 80%

---

### Phase 5: 프론트엔드 실시간 업데이트
**Goal**: 프론트엔드에서 진짜 실시간 데이터 표시

**Test Strategy:**
- Playwright E2E 테스트
- 실시간 업데이트 UI 검증

**Tasks:**
- [ ] 실시간 데이터 UI 컴포넌트 개선
- [ ] 체결가 등락 색상 애니메이션
- [ ] 호가창 UI (선택 사항)
- [ ] 장 운영 시간 표시

**Quality Gate:**
- [ ] 실시간 가격 업데이트 눈으로 확인
- [ ] 등락 색상 정확히 표시
- [ ] E2E 테스트 통과

**Coverage Target:** 70% (UI)

---

### Phase 6: 에러 처리 및 안정성
**Goal**: KOA 연결 끊김/재연결 처리

**Test Strategy:**
- 장애 시나리오 시뮬레이션
- 재연결 로직 검증

**Tasks:**
- [ ] KOA 연결 상태 모니터링
- [ ] 자동 재연결 로직
- [ ] 장 종료 후 처리
- [ ] 폴백 데이터 로직 (KOA 실패 시 DB 사용)

**Quality Gate:**
- [ ] 연결 끊김 시 자동 재연결
- [ ] 장 종료 후 정상 처리
- [ ] 폴백 데이터 정상 작동

**Coverage Target:** 85%

---

### Phase 7: 배포 및 모니터링
**Goal**: 프로덕션 배포 및 운영

**Test Strategy:**
- 프로덕션 환경 테스트
- 모니터링 대시보드 검증

**Tasks:**
- [ ] Windows 서버에 Kiwoom.exe 배포
- [ ] KOA Bridge 서비스로 실행
- [ ] 로그 수집 및 모니터링
- [ ] 장애 알림 설정

**Quality Gate:**
- [ ] 프로덕션에서 실시간 데이터 정상 수신
- [ ] 모니터링 대시보드 정상 작동
- [ ] 장애 시 알림 정상 발송

**Coverage Target:** N/A

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| 키움 API 변경 | Medium | High | 공식 문서 확인, 추상화 레이어 |
| Windows 의존성 | High | Medium | Docker에서 별도 서비스로 운영 |
| 연동 끊김 | Medium | High | 폴백 로직, 재연결 자동화 |
| COM 인터페이스 불안정 | Low | Medium | 예외 처리, 로깅 강화 |

---

## Rollback Strategy

- **Phase 1-2**: 기존 Mock/DB 데이터 그대로 사용
- **Phase 3-4**: Redis Pub/Sub 비활성화
- **Phase 5**: 기존 UI 그대로 사용
- **전체**: 기존 `price_provider.py`로 롤백

---

## Progress Tracking

| Phase | Status | Last Updated | Notes |
|-------|--------|--------------|-------|
| Phase 1 | ⏳ Pending | - | - |
| Phase 2 | ⏳ Pending | - | - |
| Phase 3 | ⏳ Pending | - | - |
| Phase 4 | ⏳ Pending | - | - |
| Phase 5 | ⏳ Pending | - | - |
| Phase 6 | ⏳ Pending | - | - |
| Phase 7 | ⏳ Pending | - | - |

---

## Notes & Learnings

*(진행하면서 기록)*

---

## References

- 키움증권 OpenAPI+ 가이드: https://www.kiwoom.com/hz/default.jsp
- KOA Developer 문서: KoA 설치 폴더 참조
