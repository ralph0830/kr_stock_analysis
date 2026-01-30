# 종가베팅 V2 시스템 전체 구현 계획

**상태**: ✅ 완료 (Phase 1-3)
**범위**: Large (5 Phases)

> **전체 문서**: `docs/archive_originals/PLAN_jonggav2_full_implementation.md` (316줄)

---

## 개요

종가베팅 V2 시스템 4가지 핵심 기능:
- Phase 1: 뉴스 점수 연동 (Gemini API) ✅
- Phase 2: 차트 점수 개선 (VCP 패턴) ✅
- Phase 3: 시그널 생성 자동화 ✅
- Phase 4: Market Gate 섹터 시각화 (백엔드) ⏳
- Phase 5: Market Gate 섹터 시각화 (프론트) ⏳

---

## 완료된 Phases

### Phase 1: 뉴스 점수 연동
- Gemini API 감성 분석
- news_score (0-3점)
- 예외 처리 및 폴백

### Phase 2: 차트 점수 개선
- VCP 패턴 감지
- 52주 고가 근접 확인
- chart_score (0-2점)

### Phase 3: 시그널 생성 자동화
- 전체 종목 대량 시그널 생성
- DB 저장 기능
- 6점 이상 필터링

---

## 점수 체계

| 항목 | 점수 | 설명 |
|------|------|------|
| News | 0-3 | Gemini 감성 분석 |
| Volume | 0-3 | 거래대금 기준 |
| Chart | 0-2 | VCP + 52주 고가 |
| Candle | 0-1 | 상승 캔들 |
| Period | 0-1 | 풀백 기간 |
| Flow | 0-2 | 외국인/기관 수급 |
| **합계** | **0-12** | S(10+) / A(8+) / B(6+) |
