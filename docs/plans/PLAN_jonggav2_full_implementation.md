# 종가베팅 V2 시스템 전체 구현 계획

> 4가지 핵심 기능의 TDD 기반 구현

**생성일:** 2026-01-28
**범위:** Large (5 Phases, 15-25 hours)
**TDD:** 테스트 우선 (Red-Green-Refactor)

---

## 🚨 CRITICAL INSTRUCTIONS

각 Phase 완료 후:
1. ✅ 완료된 작업 체크박스 확인
2. 🧪 품질 게이트 검증 명령어 실행
3. ⚠️ **모든** 품질 게이트 항목 통과 확인
4. 📅 "Last Updated" 날짜 업데이트
5. 📝 Notes 섹션에 학습 내용 기록
6. ➡️ **그 후에만** 다음 Phase 진행

⛔ 실패하는 테스트가 있거나 품질 게이트를 통과하지 못하면 다음 Phase로 진행하지 마세요.

---

## 📋 개요

### 목표
종가베팅 V2 시스템의 4가지 핵심 기능 구현
- Phase 1: 뉴스 점수 연동 (Gemini API)
- Phase 2: 차트 점수 개선 (VCP 패턴)
- Phase 3: 시그널 생성 자동화
- Phase 4: Market Gate 섹터 시각화 (백엔드)
- Phase 5: Market Gate 섹터 시각화 (프론트엔드 + E2E)

### 현재 상태
- ✅ Phase 1-3: 서비스 실행, API 통합, Frontend UI 완료
- ✅ DB 데이터 수집 완료 (Kiwoom API, 80개 데이터)
- ✅ 거래대금 점수 기준 수정 완료
- ✅ flow_score 구현 완료

---

## Phase 1: 뉴스 점수 연동 (Gemini API)

### Goal
Gemini API를 사용한 뉴스 감성 분석으로 news_score 계산 (0-3점)

### Test Strategy
- Unit Test: NewsCollector Mock → Gemini API Mock
- Integration Test: 실제 Gemini API 호출 (API Key 있을 때)
- Coverage Target: ≥80% for news scoring logic

### Tasks (TDD 순서)

#### RED (테스트 작성)
- [x] `_calculate_news_score()` 테스트 작성
  - [x] 뉴스 3개 이상 긍정: 3점
  - [x] 뉴스 2개 긍정: 2점
  - [x] 뉴스 1개 긍정: 1점
  - [x] 뉴스 없음: 0점
  - [x] API 실패 시: 0점 (폴백)

#### GREEN (구현)
- [x] NewsScorer.calculate_daily_score() 구현
  - [x] Gemini API 호출 로직
  - [x] 감성 분석 결과 점수화
  - [x] 예외 처리 및 폴백 로직 추가

#### REFACTOR (코드 개선)
- [x] 예외 처리로 에러 핸들링 개선
- [x] Mock 분석기 폴백 구현

### Quality Gate
- [x] 테스트 15개 전체 통과
- [x] NewsScorer 100% 커버리지
- [x] SignalScorer 통합 테스트 통과
- [x] Mock 분석기로 API 없이 테스트 가능

### Files
- `src/analysis/news_scorer.py` (수정됨: 예외 처리 추가)
- `services/signal_engine/scorer.py` (_calculate_news_score)
- `tests/unit/analysis/test_news_scorer.py` (新增)

---

## Phase 2: 차트 점수 개선 (VCP 패턴)

### Goal
VCP 패턴 감지 및 52주 고가 근접 확인으로 chart_score 계산 (0-2점)

### Test Strategy
- Unit Test: VCPAnalyzer Mock
- Integration Test: 실제 daily_prices 데이터 사용
- Coverage Target: ≥80% for chart analysis logic

### Tasks (TDD 순서)

#### RED (테스트 작성)
- [x] `_calculate_chart_score()` 테스트 작성 (이미 존재)
  - [x] VCP + 52주 고가 근접: 2점
  - [x] VCP만: 1점
  - [x] 52주 고가만: 1점
  - [x] 둘 다 아님: 0점

#### GREEN (구현)
- [x] VCPAnalyzer.detect_vcp_pattern() 구현 완료
  - [x] 볼린저밴드 수축비 계산
  - [x] 거래량 감소 패턴 확인
- [x] VCPAnalyzer.is_near_52w_high() 구현 완료
  - [x] 최근 52일 최고가 확인
  - [x] 95% 근접 기준

#### REFACTOR (코드 개선)
- [x] VCPAnalyzer 단위 테스트 10개 추가
- [x] 볼린저밴드 계산 함수 테스트 추가

### Quality Gate
- [x] VCPAnalyzer 단위 테스트 10개 통과
- [x] SignalScorer 차트 점수 테스트 5개 통과
- [x] 볼린저밴드 계산 정확성 검증

### Files
- `src/analysis/vcp_analyzer_improved.py` (기존 구현 유지)
- `services/signal_engine/scorer.py` (_calculate_chart_score)
- `tests/unit/analysis/test_vcp_analyzer.py` (新增)

---

## Phase 3: 시그널 생성 자동화

### Goal
전체 종목 대량 시그널 생성 및 DB 저장 기능 구현

### Test Strategy
- Unit Test: SignalRepository Mock
- Integration Test: 실제 DB 저장 확인
- Coverage Target: ≥80% for signal generation logic

### Tasks (TDD 순서)

#### RED (테스트 작성)
- [x] SignalGenerator.generate_all_signals() 테스트
  - [x] 전체 종목 시그널 생성
  - [x] 점수 필터링 (6점 이상)
  - [x] 파라미터 전달 확인
- [x] analyze_single_stock 테스트
  - [x] 단일 종목 분석 성공
  - [x] 데이터 없음 처리
  - [x] 예외 상황 처리

#### GREEN (구현)
- [x] SignalGenerator Celery 태스크 구현 완료
  - [x] SignalScorer.calculate() 호출
  - [x] 점수 필터링 (6점 이상)
  - [x] 등급순 정렬
- [x] analyze_single_stock 태스크 구현 완료

#### REFACTOR (코드 개선)
- [x] signal.score.total 접근 개선
- [x] 예외 처리 강화

### Quality Gate
- [x] 테스트 6개 전체 통과
- [x] 실제 SignalScorer로 테스트 통과

### Files
- `tasks/signal_tasks.py` (기존 구현 유지, 개선됨)
- `services/signal_engine/main.py` (기존 엔드포인트)
- `tests/unit/tasks/test_signal_tasks.py` (新增)

---

## Phase 4: Market Gate 섹터 시각화 (백엔드)

### Goal
섹터별 종가베팅 V2 점수 집계 API 구현

### Test Strategy
- Unit Test: SectorScoreCalculator Mock
- Integration Test: 실제 DB 데이터로 섹터 점수 계산
- Coverage Target: ≥80% for sector aggregation logic

### Tasks (TDD 순서)

#### RED (테스트 작성)
- [ ] SectorScoreCalculator.calculate_sector_scores() 테스트
  - [ ] 섹터별 평균 점수 계산
  - [ ] 섹터별 최고 점수 종목
  - [ ] 섹터별 종목 수
- [ ] API `/api/kr/market-gate/sectors` 테스트
  - [ ] GET 요청 응답 구조
  - [ ] 섹터별 데이터 포맷

#### GREEN (구현)
- [ ] SectorScoreCalculator 클래스 구현
  - [ ] 섹터별 종목 그룹화
  - [ ] 종가베팅 V2 점수 집계
- [ ] API Gateway 라우트 추가
  - [ ] `/api/kr/market-gate/sectors` 엔드포인트

#### REFACTOR (코드 개선)
- [ ] 섹터 분류 로직 개선
- [ ] 캐싱 전략 추가

### Quality Gate
- [ ] 테스트 3개 이상 통과
- [ ] API 응답 200 OK 확인
- [ ] 실제 섹터별 점수 계산 확인

### Files
- `src/analysis/sector_analyzer.py` (新增)
- `services/api_gateway/routes/market_gate.py` (新增)
- `tests/unit/analysis/test_sector_analyzer.py`

---

## Phase 5: Market Gate 섹터 시각화 (프론트엔드 + E2E)

### Goal
섹터별 점수 시각화 컴포넌트 및 E2E 테스트

### Test Strategy
- Component Test: React 컴포넌트 단위 테스트
- Integration Test: API 연동 테스트
- E2E Test: Playwright로 웹상 동작 확인
- Coverage Target: Integration tests preferred for UI

### Tasks (TDD 순서)

#### RED (테스트 작성)
- [ ] MarketGateSectors 컴포넌트 테스트
  - [ ] 섹터 카드 렌더링
  - [ ] 클릭 이벤트
- [ ] API 연동 테스트
  - [ ] `/api/kr/market-gate/sectors` 호출
  - [ ] 데이터 표시 확인

#### GREEN (구현)
- [ ] MarketGateSectors.tsx 컴포넌트
  - [ ] 섹터별 카드 UI
  - [ ] 그리드 레이아웃
  - [ ] 클릭 핸들러
- [ ] 페이지 추가
  - [ ] `/market-gate` 라우트

#### REFACTOR (코드 개선)
- [ ] UI/UX 개선
- [ ] 로딩 상태 표시

#### E2E 테스트
- [ ] Playwright 테스트
  - [ ] 페이지 접속 확인
  - [ ] 섹터 카드 표시 확인
  - [ ] 클릭 동작 확인

### Quality Gate
- [ ] 컴포넌트 테스트 통과
- [ ] 프론트엔드 빌드 성공: `npm run build`
- [ ] Linting 통과: `npm run lint`
- [ ] **E2E 테스트 통과** (Playwright)
- [ ] **웹상 동작 확인** (http://localhost:5110/market-gate)

### Files
- `frontend/components/MarketGateSectors.tsx` (新增)
- `frontend/app/market-gate/page.tsx` (新增)
- `tests/e2e/test_market_gate.spec.ts` (新增)

---

## 📊 Risk Assessment

| Risk | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| Gemini API Key 없음 | Medium | Medium | Mock 데이터 폴백 |
| VCP 패턴 복잡도 | High | High | 단순화된 알고리즘 시작 |
| DB 데이터 부족 | Medium | Medium | 기존 80개 데이터 활용 |
| 프론트엔드 CORS | Low | Low | API Gateway 설정 |
| Playwright 설치 | Low | Medium | Docker로 실행 |

---

## 진행 상황

| Phase | 상태 | 완료일 | Notes |
|-------|------|--------|-------|
| Phase 1 | ✅ Complete | 2026-01-28 | 뉴스 점수 연동 (15개 테스트 통과) |
| Phase 2 | ✅ Complete | 2026-01-28 | 차트 점수 개선 (15개 테스트 통과) |
| Phase 3 | ✅ Complete | 2026-01-28 | 시그널 생성 자동화 (6개 테스트 통과) |
| Phase 4 | ⏳ Pending | - | Market Gate 백엔드 |
| Phase 5 | ⏳ Pending | - | Market Gate 프론트엔드 + E2E |

---

**Last Updated:** 2026-01-28
**다음 작업:** Phase 4 시작

## 📝 Notes

### 2026-01-28
- 계획서 생성 완료
- 사용자 승인 완료
- **Phase 1 완료**: 뉴스 점수 연동
  - NewsScorer 단위 테스트 12개 작성
  - SignalScorer 통합 테스트 3개 작성
  - NewsScorer.calculate_daily_score()에 예외 처리 추가
  - 100% 커버리지 달성
  - Mock 분석기로 API Key 없어도 테스트 가능
- **Phase 2 완료**: 차트 점수 개선 (VCP 패턴)
  - VCPAnalyzer 단위 테스트 10개 작성
  - 볼린저밴드 계산 테스트 2개 작성
  - SignalScorer 차트 점수 테스트 5개 기존
  - 총 15개 테스트 통과
- **Phase 3 완료**: 시그널 생성 자동화
  - signal_tasks.py 단위 테스트 6개 작성
  - 점수 필터링 로직 개선 (hasattr 체크 추가)
  - 실제 SignalScorer로 통합 테스트 완료
