# PART 04-4: VCP 프론트엔드 페이지

> **파일**: `frontend/src/app/dashboard/kr/vcp/page.tsx`
> **용도**: VCP 시그널 대시보드 페이지 (Next.js 14 App Router)
> **의존**: krAPI, KRSignal, KRAIAnalysis

---

## 개요

VCP Pattern Scanner 페이지는 다음을 표시합니다:

- **VCP 시그널 목록**: 실시간 업데이트
- **AI 추천**: GPT + Gemini 이중 검증
- **실시간 가격**: 60초 간격 폴링
- **수급 데이터**: 외국인/기관 5일 순매수

---

## 인터페이스 정의

```typescript
interface BacktestStats {
    status: string;
    count: number;
    win_rate: number;
    avg_return: number;
    profit_factor?: number;
    message?: string;
}

interface BacktestSummary {
    vcp: BacktestStats;
    closing_bet: BacktestStats;
}
```

---

## 상태 관리

```typescript
const [signals, setSignals] = useState<KRSignal[]>([]);
const [aiData, setAiData] = useState<KRAIAnalysis | null>(null);
const [loading, setLoading] = useState(true);
const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
const [lastUpdated, setLastUpdated] = useState<string>('');
const [signalDate, setSignalDate] = useState<string>('');
```

---

## 데이터 로드

```typescript
useEffect(() => {
    loadSignals();
}, []);

const loadSignals = async () => {
    setLoading(true);
    try {
        const [signalsRes, aiRes] = await Promise.all([
            krAPI.getSignals(),
            krAPI.getAIAnalysis(),
        ]);
        setSignals(signalsRes.signals || []);
        setAiData(aiRes);
        // Extract signal date from generated_at
        const genAt = (signalsRes as any).generated_at;
        if (genAt) {
            const d = new Date(genAt);
            setSignalDate(d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }));
        }
        setLastUpdated(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
    } catch (error) {
        console.error('Failed to load signals:', error);
    } finally {
        setLoading(false);
    }
};
```

---

## 실시간 가격 업데이트

```typescript
// Real-time price updates (every 60s)
useEffect(() => {
    if (loading || signals.length === 0) return;

    const updatePrices = async () => {
        try {
            const tickers = signals.map(s => s.ticker);
            if (tickers.length === 0) return;

            const res = await fetch('/api/kr/realtime-prices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers })
            });
            const prices = await res.json();

            if (Object.keys(prices).length > 0) {
                setSignals(prev => prev.map(s => {
                    if (prices[s.ticker]) {
                        const current = prices[s.ticker];
                        const entry = s.entry_price || 0;
                        let ret = s.return_pct || 0;
                        if (entry > 0) {
                            ret = ((current - entry) / entry) * 100;
                        }
                        return { ...s, current_price: current, return_pct: ret };
                    }
                    return s;
                }));
                setLastUpdated(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
            }
        } catch (e) {
            console.error('Price update failed:', e);
        }
    };

    const interval = setInterval(updatePrices, 60000);
    return () => clearInterval(interval);
}, [signals.length, loading]);
```

---

## 유틸리티 함수

### `formatFlow()` - 수급 포맷

```typescript
const formatFlow = (value: number | undefined) => {
    if (value === undefined || value === null) return '-';
    const absValue = Math.abs(value);
    if (absValue >= 100000000) {
        return `${(value / 100000000).toFixed(1)}억`;
    } else if (absValue >= 10000) {
        return `${(value / 10000).toFixed(0)}만`;
    }
    return value.toLocaleString();
};
```

### `getAIBadge()` - AI 추천 뱃지

```typescript
const getAIBadge = (ticker: string, model: 'gpt' | 'gemini') => {
    if (!aiData) return null;
    const stock = aiData.signals?.find((s) => s.ticker === ticker);
    if (!stock) return null;

    const rec = model === 'gpt' ? stock.gpt_recommendation : stock.gemini_recommendation;
    if (!rec) return <span className="text-gray-500 text-[10px]">-</span>;

    const action = rec.action?.toUpperCase();
    let bgClass = 'bg-yellow-500/20 text-yellow-400';
    let icon = '■';
    let label = '관망';

    if (action === 'BUY') {
        bgClass = 'bg-green-500/20 text-green-400';
        icon = '▲';
        label = '매수';
    } else if (action === 'SELL') {
        bgClass = 'bg-red-500/20 text-red-400';
        icon = '▼';
        label = '매도';
    }

    return (
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${bgClass} border border-current/30`} title={rec.reason}>
            {icon} {label}
        </span>
    );
};
```

---

## 헤더 섹션

```tsx
<div>
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-xs text-blue-400 font-medium mb-4">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping"></span>
        VCP Pattern Scanner
    </div>
    <h2 className="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
        VCP <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">Signals</span>
    </h2>
    <p className="text-gray-400 text-lg">Volatility Contraction Pattern + 기관/외국인 수급</p>
</div>
```

---

## 컨트롤 섹션

```tsx
<div className="flex items-center justify-between">
    <div className="flex items-center gap-3">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="w-1 h-5 bg-blue-500 rounded-full"></span>
            Live VCP Signals
        </h3>
        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs font-bold rounded-full">
            {signals.length}
        </span>
    </div>

    <button
        onClick={loadSignals}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold rounded-xl transition-all flex items-center gap-2 disabled:opacity-50"
    >
        <i className={`fas fa-sync-alt ${loading ? 'animate-spin' : ''}`}></i>
        Refresh
    </button>
</div>
```

---

## 시그널 테이블

### 컬럼 구조

| 컬럼 | 설명 | 타입 |
|-----|------|------|
| Stock | 종목명/티커/시장 | string |
| Date | 시그널 날짜 | date |
| 외국인 5D | 5일 순매수 | number (억/만) |
| 기관 5D | 5일 순매수 | number (억/만) |
| Score | VCP 점수 | number |
| Cont. | 수축률 | number |
| Entry | 진입가 | number (원) |
| Current | 현재가 | number (원) |
| Return | 수익률 | number (%) |
| GPT | GPT 추천 | badge |
| Gemini | Gemini 추천 | badge |

### 행 렌더링

```tsx
{signals.map((signal, idx) => (
    <tr
        key={`${signal.ticker}-${idx}`}
        onClick={() => setSelectedTicker(signal.ticker)}
        className={`hover:bg-white/5 transition-colors cursor-pointer ${selectedTicker === signal.ticker ? 'bg-white/10' : ''}`}
    >
        {/* Stock */}
        <td className="px-4 py-3">
            <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center text-white font-bold text-sm">
                    {signal.name?.charAt(0) || signal.ticker?.charAt(0) || '?'}
                </div>
                <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                        <span className="text-white font-bold">{signal.name || signal.ticker}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${signal.market === 'KOSPI' ? 'bg-blue-500/20 text-blue-400' : 'bg-pink-500/20 text-pink-400'}`}>
                            {signal.market}
                        </span>
                    </div>
                    <span className="text-[10px] text-gray-500 font-mono">{signal.ticker}</span>
                </div>
            </div>
        </td>

        {/* Date */}
        <td className="px-4 py-3 text-gray-400 text-xs">
            {signal.signal_date || signalDate || '-'}
        </td>

        {/* 외국인 5D */}
        <td className={`px-4 py-3 text-right font-mono text-xs ${signal.foreign_5d > 0 ? 'text-green-400' : 'text-red-400'}`}>
            <div className="flex items-center justify-end gap-1">
                {signal.foreign_5d > 0 ? <i className="fas fa-arrow-up text-[8px]"></i> : signal.foreign_5d < 0 ? <i className="fas fa-arrow-down text-[8px]"></i> : null}
                {formatFlow(signal.foreign_5d)}
            </div>
        </td>

        {/* 기관 5D */}
        <td className={`px-4 py-3 text-right font-mono text-xs ${signal.inst_5d > 0 ? 'text-green-400' : 'text-red-400'}`}>
            <div className="flex items-center justify-end gap-1">
                {signal.inst_5d > 0 ? <i className="fas fa-arrow-up text-[8px]"></i> : signal.inst_5d < 0 ? <i className="fas fa-arrow-down text-[8px]"></i> : null}
                {formatFlow(signal.inst_5d)}
            </div>
        </td>

        {/* Score */}
        <td className="px-4 py-3 text-center">
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                {signal.score ? Math.round(signal.score) : '-'}
            </span>
        </td>

        {/* Cont. (수축률) */}
        <td className={`px-4 py-3 text-center font-mono text-xs ${signal.contraction_ratio && signal.contraction_ratio <= 0.6 ? 'text-emerald-400' : 'text-purple-400'}`}>
            {signal.contraction_ratio?.toFixed(2) ?? '-'}
        </td>

        {/* Entry */}
        <td className="px-4 py-3 text-right font-mono text-xs text-gray-400">
            ₩{signal.entry_price?.toLocaleString() ?? '-'}
        </td>

        {/* Current */}
        <td className="px-4 py-3 text-right font-mono text-xs text-white">
            ₩{signal.current_price?.toLocaleString() ?? '-'}
        </td>

        {/* Return */}
        <td className={`px-4 py-3 text-right font-mono text-xs font-bold ${signal.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {signal.return_pct !== undefined ? `${signal.return_pct >= 0 ? '+' : ''}${signal.return_pct.toFixed(1)}%` : '-'}
        </td>

        {/* GPT */}
        <td className="px-4 py-3 text-center">
            {getAIBadge(signal.ticker, 'gpt')}
        </td>

        {/* Gemini */}
        <td className="px-4 py-3 text-center">
            {getAIBadge(signal.ticker, 'gemini')}
        </td>
    </tr>
))}
```

---

## 로딩/빈 상태

```tsx
{/* Loading */}
{loading ? (
    <tr>
        <td colSpan={11} className="p-8 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-2xl text-blue-500/50 mb-3"></i>
            <p className="text-xs">Loading signals...</p>
        </td>
    </tr>
) : signals.length === 0 ? (
    /* Empty */
    <tr>
        <td colSpan={11} className="p-8 text-center text-gray-500">
            <i className="fas fa-inbox text-2xl opacity-30 mb-3"></i>
            <p className="text-xs">오늘 시그널이 없습니다</p>
        </td>
    </tr>
) : (
    /* Signals */
    signals.map(...)
)}
```

---

## API 호출

```typescript
// lib/api.ts
export const krAPI = {
    getSignals: (): Promise<KRSignalsResponse> =>
        fetch('/api/kr/signals').then(r => r.json()),

    getAIAnalysis: (): Promise<KRAIAnalysis> =>
        fetch('/api/kr/ai-analysis').then(r => r.json()),
};
```

---

## 타입 정의

```typescript
// types/kr.ts
export interface KRSignal {
    ticker: string;
    name: string;
    market: 'KOSPI' | 'KOSDAQ';
    signal_date?: string;
    foreign_5d: number;
    inst_5d: number;
    score?: number;
    contraction_ratio?: number;
    entry_price?: number;
    current_price?: number;
    return_pct?: number;
}

export interface KRAIAnalysis {
    signals: Array<{
        ticker: string;
        gpt_recommendation?: {
            action: 'BUY' | 'SELL' | 'HOLD';
            reason: string;
        };
        gemini_recommendation?: {
            action: 'BUY' | 'SELL' | 'HOLD';
            reason: string;
        };
    }>;
}
```
