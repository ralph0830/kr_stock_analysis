# Implementation Plan: 종목 상세 페이지 기능 확장

**Status**: ✅ 완료 (5/5 Phases)
**기간**: 2026-01-26 ~ 2026-01-28

> **전체 문서**: `docs/archive_originals/PLAN_stock_detail_page.md` (1002줄)

---

## 개요

종목 상세 페이지 (`/stock/[ticker]`)에 다음 기능 추가:
- 수급 차트 (외국인/기관 흐름)
- 시그널 히스토리 및 성과
- 수익률 분석
- 기술적 지표 (RSI, MACD)
- 관련 뉴스 및 감성 분석

---

## 완료된 Phases

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 수급 차트 컴포넌트 + API Backend | ✅ |
| 2 | 시그널 히스토리 및 성과 분석 | ✅ |
| 3 | 수익률 계산 및 차트 | ✅ |
| 4 | 기술적 지표 추가 (RSI, MACD) | ✅ |
| 5 | 관련 뉴스 및 감성 분석 | ✅ |

---

## 신규 API 엔드포인트

| Endpoint | Service | Cache TTL |
|----------|---------|-----------|
| `GET /api/kr/stocks/{ticker}/flow` | API Gateway | 5 min |
| `GET /api/kr/stocks/{ticker}/signals` | API Gateway | 15 min |
| `GET /api/kr/stocks/{ticker}/analysis` | Signal Engine | 30 min |
| `GET /api/kr/stocks/{ticker}/indicators` | VCP Scanner | 5 min |
| `GET /api/kr/stocks/{ticker}/news` | Signal Engine | 60 min |

---

## 기술적 결정사항

| 결정 | 근거 | Trade-off |
|------|------|-----------|
| 기존 서비스 확장 | Service Discovery 재사용 | 결합도 증가 가능성 |
| API Gateway 통합 라우팅 | 단일 진입점 | Gateway 병목 가능성 |
| Recharts 유지 | 기존 코드와 일관성 | D3.js 고급 기능 포기 |
| Server Components 우선 | Next.js 14 권장 패턴 | 실시간 갱신 제한적 |
