# PART_04-07 구현 계획

> 종가베팅 V2 Scorer TODO 구현 및 Frontend UI 개선

**상태**: 진행 중
**범위**: Medium (4 Phases, 10-12 hours)

> **전체 문서**: `docs/archive_originals/PLAN_part04_07_implementation.md` (313줄)

---

## 개요

PART_04-07 참조 코드와 현재 프로젝트 간격을 분석하고, 누락된 기능을 Open Architecture를 유지하며 구현

---

## 범위

1. **P1-1**: SignalScorer TODO 항목 구현
   - 거래대금 점수 ✅
   - 차트 점수 (VCP) ✅
   - 캔들 점수 ⏳
   - 기간 점수 ⏳
   - 수급 점수 ⏳

2. **P1-2**: Frontend UI 개선
   - Market Gate 섹터 ⏳
   - 백테스트 KPI ⏳

3. **P2-1**: Chatbot API 구현 (선택) ⏳

---

## Architecture Decisions

- 마이크로서비스 구조 유지
- Repository 패턴 통해 데이터 접근
- SignalScorer에 Repository 주입
- Unit Tests: Repository Mock 사용
- Coverage: Business Logic ≥90%

---

## Phase 요약

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 거래대금 점수 계산 구현 | ✅ |
| 2 | 차트 패턴 점수 계산 구현 | ✅ |
| 3 | 캔들/기간/수급 점수 구현 | ⏳ |
| 4 | Frontend UI 개선 | ⏳ |
