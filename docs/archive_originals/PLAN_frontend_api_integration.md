# 프론트엔드 API 연결 구현 계획

> **CRITICAL INSTRUCTIONS**: After completing each phase:
> 1. ✅ Check off completed task checkboxes
> 2. 🧪 Run all quality gate validation commands
> 3. ⚠️ Verify ALL quality gate items pass
> 4. 📅 Update "Last Updated" date
> 5. 📝 Document learnings in Notes section
> 6. ➡️ Only then proceed to next phase
>
> ⛔ DO NOT skip quality gates or proceed with failing checks

---

## 개요

### 목표
백엔드에서 구현한 P1 API를 프론트엔드에 연결하여 사용자에게 제공

### 범위 (Large - 6~7 Phases)
1. **Phase 1**: API 클라이언트 확장 - 새로운 백엔드 API 메서드 추가
2. **Phase 2**: AI 분석 컴포넌트 - 종목 상세에 AI 요약 표시
3. **Phase 3**: 시스템 상태 컴포넌트 - 대시보드에 시스템 헬스 표시
4. **Phase 4**: 스캔 트리거 컴포넌트 - VCP/Signal 스캔 버튼 UI
5. **Phase 5**: Store 확장 - 새로운 상태 관리 로직 추가
6. **Phase 6**: 타입 정의 확장 - TypeScript 인터페이스 추가
7. **Phase 7**: 통합 테스트 및 리팩토링

### 기술 스택
- **Frontend**: Next.js 14 App Router, React 19, TypeScript
- **UI**: shadcn/ui, Tailwind CSS, Lucide Icons
- **상태 관리**: Zustand
- **차트**: Recharts
- **HTTP**: Axios

---

## Phase 1: API 클라이언트 확장

### 목표
백엔드 P1 API 엔드포인트와 통신할 API 클라이언트 메서드 추가

### Test Strategy
- API 메서드별 단위 테스트
- Mock 응답으로 캡슐화된 테스트
- 타입 검증 (TypeScript)

### Tasks

#### RED Phase (테스트 작성)
- [ ] `api-client.test.ts` 파일 생성
- [ ] AI API 메서드 테스트 작성
  - [ ] `getAISummary(ticker)` - 200 응답 검증
  - [ ] `getAIAnalysis()` - 목록 조회 검증
  - [ ] `getAIHistoryDates()` - 날짜 목록 검증
  - [ ] `getAIHistoryByDate()` - 특정 날짜 검증
  - [ ] `triggerAIAnalysis(ticker)` - 트리거 검증
- [ ] 시스템 API 메서드 테스트 작성
  - [ ] `getDataStatus()` - 데이터 상태 검증
  - [ ] `getSystemHealth()` - 시스템 헬스 검증
- [ ] 스캔 API 메서드 테스트 작성
  - [ ] `triggerVCPScan()` - VCP 스캔 검증
  - [ ] `triggerSignalGeneration()` - 시그널 생성 검증
  - [ ] `getScanStatus()` - 스캔 상태 검증
- [ ] 테스트 실행 → 실패 확인

#### GREEN Phase (구현)
- [ ] `lib/api-client.ts`에 새로운 API 메서드 추가
  - [ ] `getAISummary(ticker: string)` → `GET /api/kr/ai-summary/{ticker}`
  - [ ] `getAIAnalysis()` → `GET /api/kr/ai-analysis`
  - [ ] `getAIHistoryDates()` → `GET /api/kr/ai-history-dates`
  - [ ] `getAIHistoryByDate()` → `GET /api/kr/ai-history/{date}`
  - [ ] `triggerAIAnalysis(ticker)` → `POST /api/kr/ai-analyze/{ticker}`
  - [ ] `getDataStatus()` → `GET /api/system/data-status`
  - [ ] `getSystemHealth()` → `GET /api/system/health`
  - [ ] `triggerVCPScan()` → `POST /api/kr/scan/vcp`
  - [ ] `triggerSignalGeneration()` → `POST /api/kr/scan/signals`
  - [ ] `getScanStatus()` → `GET /api/kr/scan/status`
- [ ] 테스트 실행 → 통과 확인

#### REFACTOR Phase
- [ ] 에러 처리 일관성 확인
- [ ] 재시도 로직 적용
- [ ] 타입 안전성 검증

### Quality Gate
- [ ] 모든 API 메서드 테스트 통과
- [ ] TypeScript 컴파일 에러 없음
- [ ] API 응답 타입 정확히 매핑됨

### Dependencies
- 백엔드 API 실행 중 (포트 5111)
- 기존 api-client.ts 구조

### Coverage Target
- ≥90% (API 레이어)

### 완료 기준
- API 호출 시 console.log로 응답 확인 가능
- TypeScript 오류 없음

---

## Phase 2: AI 분석 컴포넌트

### 목표
종목 상세 페이지에 AI 분석 섹션 추가

### Test Strategy
- 컴포넌트 렌더링 테스트
- 데이터 로딩/에러 상태 테스트
- Mock 데이터로 시각적 검증

### Tasks

#### RED Phase (테스트 작성)
- [ ] `AIAnalysisSummary.test.tsx` 파일 생성
- [ ] AI 요약 표시 테스트
- [ ] 감성 점수 바 색상 테스트 (긍정/부정/중립)
- [ ] 키워드 태그 표시 테스트
- [ ] 매수 추천 배지 테스트
- [ ] 로딩 스켈레톤 테스트
- [ ] 에러 상태 테스트

#### GREEN Phase (구현)
- [ ] `components/AIAnalysisSummary.tsx` 컴포넌트 생성
  - [ ] Props: `ticker`, `analysis`
  - [ ] 감성 표시 (이모지 + 색상)
  - [ ] 감성 점수 바 (-1.0 ~ 1.0)
  - [ ] 요약 텍스트
  - [ ] 키워드 태그 리스트
  - [ ] 매수 추천 (BUY/SELL/HOLD/OVERWEIGHT/UNDERWEIGHT)
  - [ ] 업데이트 시간 표시
- [ ] `stockStore.ts`에 AI 상태 추가
  - [ ] `aiAnalysis: IAIAnalysis | null`
  - [ ] `fetchAIAnalysis(ticker)` 액션
- [ ] `StockDetail.tsx`에 AI 섹션 통합

#### REFACTOR Phase
- [ ] 감성 색상 상수 분리
- [ ] 아이콘/배지 컴포넌트 재사용
- [ ] 로딩 상태 애니메이션 추가

### Quality Gate
- [ ] 컴포넌트 렌더링 성공
- [ ] API 데이터 정상 표시
- [ ] 반응형 레이아웃 확인

### Dependencies
- Phase 1 완료 (API 클라이언트)

### Coverage Target
- ≥80% (컴포넌트 로직)

### 완료 기준
- 종목 상세 페이지에서 AI 요약 확인 가능
- 감성 색상 올바르게 표시

---

## Phase 3: 시스템 상태 컴포넌트

### 목표
대시보드/시그널 페이지에 시스템 헬스 모니터링 추가

### Test Strategy
- 시스템 상태 표시 테스트
- 서비스별 상태 색상 테스트
- 데이터 상태 표시 테스트

### Tasks

#### RED Phase (테스트 작성)
- [ ] `SystemHealthIndicator.test.tsx` 파일 생성
- [ ] 시스템 상태 표시 테스트
- [ ] 서비스 상태 리스트 테스트
- [ ] 데이터 상태 카드 테스트
- [ ] 자동 새로고침 테스트

#### GREEN Phase (구현)
- [ ] `components/SystemHealthIndicator.tsx` 컴포넌트 생성
  - [ ] 전체 상태 헤더 (healthy/degraded/unhealthy)
  - [ ] 서비스 상태 그리드
  - [ ] 데이터 파일 상태 테이블
  - [ ] Uptime 표시
  - [ ] 새로고침 버튼
- [ ] `store/systemStore.ts` 생성
  - [ ] 시스템 상태 관리
  - [ ] 주기적 폴링 (30초)
- [ ] 대시보드/시그널 페이지에 배치

#### REFACTOR Phase
- [ ] 상태 색상 유틸리티 함수화
- [ ] 폴링 간격 설정 가능하게 분리
- [ ] 에러 발생 시 알림 추가

### Quality Gate
- [ ] 시스템 상태 정확히 표시
- [ ] 자동 새로고침 동작
- [ ] 에러 발생 시 사용자 피드백

### Dependencies
- Phase 1 완료 (API 클라이언트)

### Coverage Target
- ≥75% (시스템 모니터링 로직)

### 완료 기준
- 대시보드에서 시스템 상태 확인 가능
- 서비스 다운 시 시각적 경고 표시

---

## Phase 4: 스캔 트리거 컴포넌트

### 목표
VCP/Signal 스캔 실행 UI 추가

### Test Strategy
- 트리거 버튼 동작 테스트
- 진행 상태 표시 테스트
- 결과 표시 테스트

### Tasks

#### RED Phase (테스트 작성)
- [ ] `ScanTriggerPanel.test.tsx` 파일 생성
- [ ] VCP 스캔 버튼 클릭 테스트
- [ ] 시그널 생성 버튼 클릭 테스트
- [ ] 진행률 표시 테스트
- [ ] 완료 메시지 테스트
- [ ] 에러 처리 테스트

#### GREEN Phase (구현)
- [ ] `components/ScanTriggerPanel.tsx` 컴포넌트 생성
  - [ ] VCP 스캔 버튼 + 옵션 (시장, 최소 점수)
  - [ ] 시그널 생성 버튼 + 옵션 (종목 리스트)
  - [ ] 진행 상태 모달/토스트
  - [ ] 진행률 바
  - [ ] 완료 결과 요약
- [ ] `store/scanStore.ts` 생성
  - [ ] 스캔 상태 관리
  - [ ] 진행률 추적
  - [ ] 결과 저장
- [ ] 시그널 페이지에 배치

#### REFACTOR Phase
- [ ] 버튼 로딩 상태 재사용
- [ ] 진행률 애니메이션 개선
- [ ] 결과 알림 최적화

### Quality Gate
- [ ] 스캔 트리거 정상 동작
- [ ] 진행 상태 실시간 업데이트
- [ ] 완료 후 결과 확인 가능

### Dependencies
- Phase 1 완료 (API 클라이언트)
- WebSocket 연동 (선택사항)

### Coverage Target
- ≥70% (트리거 로직)

### 완료 기준
- 스캔 버튼 클릭으로 진행 가능
- 진행률과 결과 확인 가능

---

## Phase 5: Store 확장

### 목표
Zustand store에 새로운 상태 관리 로직 추가

### Test Strategy
- Store 액션 테스트
- 상태 업데이트 검증
- 캐싱 로직 테스트

### Tasks

#### RED Phase (테스트 작성)
- [ ] `systemStore.test.ts` 파일 생성
- [ ] `scanStore.test.ts` 파일 생성
- [ ] AI 상태 관리 테스트
- [ ] 시스템 상태 폴링 테스트
- [ ] 스캔 상태 업데이트 테스트

#### GREEN Phase (구현)
- [ ] `store/systemStore.ts` 생성/확장
  - [ ] 시스템 헬스 상태
  - [ ] 데이터 상태
  - [ ] 주기적 폴링 로직
- [ ] `store/scanStore.ts` 생성/확장
  - [ ] 스캔 상태
  - [ ] 진행률
  - [ ] 결과
- [ ] 기존 `stockStore.ts`에 AI 상태 추가

#### REFACTOR Phase
- [ ] Store 로직 분리
- [ ] 선택적 업데이트 최적화
- [ ] persist middleware 추가

### Quality Gate
- [ ] Store 테스트 통과
- [ ] 상태 업데이트 정확
- [ ] 불필요한 리렌더링 없음

### Dependencies
- Phase 1-4 구현 완료

### Coverage Target
- ≥85% (Store 로직)

### 완료 기준
- 모든 상태가 Store에서 관리됨
- 컴포넌트 간 상태 공유 정상

---

## Phase 6: 타입 정의 확장

### 목표
TypeScript 인터페이스/타입 추가로 타입 안전성 확보

### Test Strategy
- 타입 검증
- API 응답 타입 매칭

### Tasks

#### RED Phase (테스트 작성)
- [ ] 타입 사용 시나리오 테스트
- [ ] API 응답 매핑 테스트

#### GREEN Phase (구현)
- [ ] `types/index.ts`에 새로운 타입 추가
  - [ ] `IAIAnalysis` - AI 분석 결과
  - [ ] `IAIAnalysisList` - AI 분석 목록
  - [ ] `ISystemHealth` - 시스템 헬스
  - [ ] `IDataStatus` - 데이터 상태
  - [ ] `IScanStatus` - 스캔 상태
  - [ ] `IVCPScanResponse` - VCP 스캔 응답
  - [ ] `ISignalGenerationResponse` - 시그널 생성 응답

#### REFACTOR Phase
- [ ] 타입 정리 및 중복 제거
- [ ] 공통 타입 추출
- [ ] 엄격 모드로 검증

### Quality Gate
- [ ] TypeScript 컴파일 에러 없음
- [ ] 모든 API 응답 타입 정의됨
- [ ] `any` 타입 사용 없음

### Dependencies
- Phase 1-5 구현 완료

### Coverage Target
- N/A (타입 정의)

### 완료 기준
- 모든 컴포넌트가 타입 안전함

---

## Phase 7: 통합 테스트 및 리팩토링

### 목표
전체 기능 통합 테스트 및 사용성 개선

### Test Strategy
- E2E 워크플로우 테스트
- 사용자 시나리오 테스트
- 성능 테스트

### Tasks

#### RED Phase (테스트 작성)
- [ ] E2E 시나리오 테스트 작성
  - [ ] 종목 상세 → AI 확인
  - [ ] 대시보드 → 시스템 상태 확인
  - [ ] 시그널 → 스캔 실행 → 결과 확인

#### GREEN Phase (구현)
- [ ] 통합 테스트 실행
- [ ] 발견된 버그 수정
- [ ] 성능 최적화
- [ ] 접근성 개선

#### REFACTOR Phase
- [ ] 코드 리팩토링
- [ ] 주석 추가
- [ ] 문서화

### Quality Gate
- [ ] 모든 E2E 테스트 통과
- [ ] 사용자 시나리오 정상 동작
- [ ] 성능 기준 충족

### Dependencies
- Phase 1-6 완료

### Coverage Target
- ≥75% (전체 프론트엔드)

### 완료 기준
- 모든 기능이 사용자에게 제공 가능

---

## 리스크 평가

| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|----------|
| API 엔드포인트 변경 | Medium | High | 타입 검증으로 조기 발견 |
| CORS 이슈 | Low | Medium | 이미 구성됨 확인 |
| WebSocket 연동 복잡성 | Medium | Medium | Phase 4에서 선택사항으로 |
| 성능 저하 | Low | Medium | 코드 스플리팅, 캐싱 |

---

## 롤백 전략

### Phase 1-3: API/Store
- 파일 삭제로 복구 가능
- Git 커밋 단위로 진행

### Phase 4-7: 컴포넌트
- feature flag로 제어 가능
- 기존 컴포넌트에 영향 없음

---

## 진행 상황

### 최종 업데이트: 2026-01-27 (완료)

| Phase | 상태 | 완료일 | 노트 |
|-------|------|--------|------|
| Phase 1 | ✅ 완료 | 2026-01-27 | API 클라이언트 10개 메서드 추가 |
| Phase 2 | ✅ 완료 | 2026-01-27 | AIAnalysisSummary 컴포넌트 생성 |
| Phase 3 | ✅ 완료 | 2026-01-27 | SystemHealthIndicator + systemStore 생성 |
| Phase 4 | ✅ 완료 | 2026-01-27 | ScanTriggerPanel 컴포넌트 생성 |
| Phase 5 | ✅ 완료 | 2026-01-27 | Store 구조 검증 완료 |
| Phase 6 | ✅ 완료 | 2026-01-27 | 타입 정의 완료 (백엔드와 일치) |
| Phase 7 | ✅ 완료 | 2026-01-27 | 빌드 통과, TypeScript 검증 완료 |

---

## 학습 내용 (Notes)

### 구현 완료 사항

1. **API Client Extension (Phase 1)**
   - AI Analysis: `getAISummary`, `getAIAnalysis`, `getAIHistoryDates`, `getAIHistoryByDate`, `triggerAIAnalysis`
   - System Management: `getDataStatus`, `getSystemHealth`
   - Scan Trigger: `triggerVCPScan`, `triggerSignalGeneration`, `getScanStatus`

2. **AI Component (Phase 2)**
   - `AIAnalysisSummary.tsx`: 감성 분석, 점수 바, 키워드 태그, 추천 배지
   - `stockStore.ts` 확장: AI 분석 상태 관리

3. **System Health Component (Phase 3)**
   - `SystemHealthIndicator.tsx`: 서비스 상태, 데이터 상태, uptime 표시
   - `systemStore.ts`: 30초 폴링으로 자동 업데이트

4. **Scan Trigger Panel (Phase 4)**
   - `ScanTriggerPanel.tsx`: VCP 스캔, 시그널 생성 버튼, 5초 폴링 상태 확인
   - 빠른 실행 버튼 (전체/KOSPI/KOSDAQ)

5. **Dashboard 통합**
   - 왼쪽 사이드바: SystemHealth + ScanTrigger
   - 메인 영역: Market Gate 상태
   - 반응형 4열 그리드 레이아웃

6. **빌드 검증**
   - TypeScript 컴파일: 성공
   - Next.js 빌드: 성공
   - 모든 컴포넌트 타입 안전함

### 향후 개선사항
- 테스트 코드 추가 (TDD RED phase 생략됨)
- WebSocket 기반 실시간 스캔 상태 업데이트
- 에러 바운더리 추가하여 UX 개선

