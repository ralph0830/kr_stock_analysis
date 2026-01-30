# PART 05-1: KR Market Overview (메인 대시보드)

> **파일**: `frontend/src/app/dashboard/kr/page.tsx`
> **전체 문서**: `docs/archive_originals/PART_05_01_kr_overview.md` (374줄)

---

## 개요

KR Market Overview 페이지 기능:
- Market Gate: 시장 상태 점수 (원형 프로그레스)
- 섹터 지표: KOSPI 200 섹터별 bullish/bearish
- KPI 카드: 오늘 시그널, VCP/Closing Bet 성과
- 시장 지수: KOSPI/KOSDAQ 실시간

---

## 인터페이스

```typescript
interface BacktestStats {
    status: string;
    count: number;
    win_rate: number;
    avg_return: number;
    profit_factor?: number;
}
```

---

## 유틸리티 함수

### `getGateColor()` - 게이트 점수 색상
```typescript
// 70+ → green, 40+ → yellow, else → red
```

### `getSectorColor()` - 섹터 신호 색상
```typescript
// bullish → green, bearish → red, neutral → yellow
```

---

## Market Gate 섹션

- 원형 프로그레스 바 (SVG)
- 게이트 점수 (0-100)
- 섹터 그리드 (KOSPI 200 섹터)
