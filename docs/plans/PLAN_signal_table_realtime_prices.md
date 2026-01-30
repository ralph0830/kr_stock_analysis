# PLAN: 시그널 테이블 실시간 가격 통합

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

시그널 테이블에 실시간 가격 데이터를 통합하여 사용자가 현재가, 전일비, 등락률을 실시간으로 확인할 수 있도록 합니다.

### Objectives
- [ ] 시그널 테이블에 실시간 가격 컬럼 추가
- [ ] WebSocket을 통한 실시간 가격 업데이트
- [ ] 상위 5개 시그널 종목에 대한 실시간 가격 표시

### Scope
- **Size**: Small (단일 컴포넌트 수정)
- **Estimated Time**: 1-2시간
- **TDD**: 필요 최소 (UI 로직 중심)

---

## Architecture Decisions

### 1. 실시간 가격 데이터 소스
- **Decision**: 기존 `useRealtimePrices` hook 활용
- **Rationale**: 이미 WebSocket 연동 및 가격 업데이트 로직이 구현됨

### 2. 컬럼 구성
- **결정가**: 현재가, 전일비, 등락률 3개 컬럼 추가
- **위치**: 진입가 앞에 배치 (가장 중요한 정보)

### 3. 데이터 처리
- **결정**: 실시간 가격이 없으면 "-" 또는 "로딩 중" 표시
- **Rationale**: WebSocket 연결 지연 시 UI 깨짐 방지

---

## Phase Breakdown

### Phase 1: 시그널 테이블에 실시간 가격 Hook 연결

**Goal**: 시그널 테이블에서 실시간 가격 데이터 조회 가능

**Tasks**:
- [ ] `useRealtimePrices` hook으로 시그널 종목들 실시간 가격 조회
- [ ] 시그널 종목 ticker 리스트 추출
- [ ] 실시간 가격 데이터 상태 관리

**Quality Gate**:
- [ ] Hook이 시그널 종목들의 가격을 정상적으로 조회
- [ ] WebSocket 연결 상태 확인 가능

**Dependencies**: 없음

---

### Phase 2: 시그널 테이블 컬럼 추가

**Goal**: 테이블에 현재가, 전일비, 등락률 컬럼 추가

**Tasks**:
- [ ] TableHead에 컬럼 헤더 추가
- [ ] TableCell에 실시간 가격 데이터 렌더링
- [ ] 가격 데이터 없을 때 fallback 표시

**Quality Gate**:
- [ ] 컬럼이 정상적으로 표시됨
- [ ] 가격 데이터 업데이트 시 화면 갱신됨

**Dependencies**: Phase 1 완료

---

### Phase 3: 스타일링 및 UX 개선

**Goal**: 실시간 가격 표시 UX 개선

**Tasks**:
- [ ] 등락률에 따른 색상 적용 (상승: 빨간색, 하락: 파란색)
- [ ] 가격 업데이트 애니메이션 효과
- [ ] 로딩 상태 표시

**Quality Gate**:
- [ ] 색상이 등락률에 따라 올바르게 적용됨
- [ ] 애니메이션이 자연스럽게 작동함

**Dependencies**: Phase 2 완료

---

## Quality Gate Checklist

### Build & Compilation
- [ ] 프로젝트 빌드 성공 (`npm run build`)
- [ ] TypeScript 타입 체크 통과 (`npx tsc --noEmit`)
- [ ] ESLint 통과 (`npm run lint`)

### Functionality
- [ ] 시그널 테이블에 실시간 가격 표시됨
- [ ] WebSocket 연결 시 가격 업데이트됨
- [ ] 등락률 색상 올바르게 적용됨

### Edge Cases
- [ ] WebSocket 연결 실패 시 graceful degradation
- [ ] 시그널 없는 경우 빈 상태 정상 표시
- [ ] 가격 데이터 없는 경우 "-" 표시

---

## Risk Assessment

| Risk | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| WebSocket 연결 실패 | Medium | Low | 연결 실패 시 "-" 표시, 에러 메시지 |
| 가격 데이터 지연 | Low | Low | 로딩 상태 표시 |
| 실시간 업데이트 성능 | Low | Low | React 최적화 (useMemo) |

---

## Rollback Strategy

**Phase 1/2**: 커밋 되돌리기 (`git revert`)
**Phase 3**: CSS 제거, 기본 테이블 스타일로 복귀

---

## Progress Tracking

**Last Updated**: 2026-01-30 ✅ 완료

### Phase Status
- [x] Phase 1: Hook 연결
- [x] Phase 2: 컬럼 추가
- [x] Phase 3: 스타일링

---

## Notes & Learnings

_(작업 진행 중 학습한 내용 기록)_
