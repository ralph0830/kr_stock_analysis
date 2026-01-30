# PART 04-4: VCP 프론트엔드 페이지

> **용도**: VCP 시그널 대시보드 페이지 (Next.js 14)
> **전체 문서**: `docs/archive_originals/PART_04_04_vcp_page.md` (410줄)

---

## 개요

VCP Pattern Scanner 페이지 기능:
- VCP 시그널 목록 (실시간 업데이트)
- AI 추천 (GPT + Gemini 이중 검증)
- 실시간 가격 (60초 간격 폴링)
- 수급 데이터 (외국인/기관 5일 순매수)

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

interface BacktestSummary {
    vcp: BacktestStats;
    closing_bet: BacktestStats;
}
```

---

## 유틸리티 함수

### `formatFlow()` - 수급 포맷
```typescript
// 100000000 → "10.0억"
// 10000 → "1만"
```

### `getAIBadge()` - AI 추천 뱃지
- 매수强力 / 매수 / 중립 / 매도

---

## 데이터 로드

```typescript
const [signals, setSignals] = useState<KRSignal[]>([]);
const [aiData, setAiData] = useState<KRAIAnalysis | null>([]);

// 실시간 가격 업데이트 (60초)
setInterval(updatePrices, 60000);
```
