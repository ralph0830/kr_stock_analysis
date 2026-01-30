# PART 05-2: Closing Bet V2 (종가베팅 페이지)

> **파일**: `frontend/src/app/dashboard/kr/closing-bet/page.tsx`
> **전체 문서**: `docs/archive_originals/PART_05_02_closing_bet.md` (400줄)

---

## 개요

Closing Bet V2 시그널 대시보드:
- S/A/B 등급별 시그널
- 날짜 선택
- 네이버 금융 차트 연동
- 12점 만점 상세 점수/체크리스트

---

## 인터페이스

```typescript
interface ScoreDetail {
    news: number;        // 0-3점
    volume: number;      // 0-3점
    chart: number;       // 0-2점
    candle: number;      // 0-1점
    consolidation: number; // 0-1점
    supply: number;      // 0-2점
    total: number;       // 0-12점
}

interface Signal {
    stock_code: string;
    stock_name: string;
    grade: string;       // 'S', 'A', 'B', 'C'
    score: ScoreDetail;
    current_price: number;
    entry_price: number;
    stop_price: number;
    target_price: number;
}
```

---

## 네이버 차트 위젯

```tsx
// 네이버 금융 차트 이미지
https://ssl.pstatic.net/imgfinance/chart/item/candle/day/{symbol}.png

// 인터랙티브 차트
https://m.stock.naver.com/domestic/stock/{symbol}/chart
```

---

## 차트 모달

- ESC 키 닫기
- 전체 화면 배경 클릭 닫기
