# PART 05-2: Closing Bet V2 (종가베팅 페이지)

> **파일**: `frontend/src/app/dashboard/kr/closing-bet/page.tsx`
> **용도**: 종가베팅 V2 시그널 대시보드 페이지
> **프레임워크**: Next.js 14 App Router, React

---

## 개요

Closing Bet V2 페이지는 다음을 표시합니다:

- **시그널 목록**: S/A/B 등급별 종가베팅 시그널
- **날짜 선택**: 최신 또는 특정 날짜의 시그널
- **차트 모달**: 네이버 금융 차트 연동
- **점수/체크리스트**: 12점 만점 상세

---

## 인터페이스 정의

```typescript
interface ScoreDetail {
    news: number;
    volume: number;
    chart: number;
    candle: number;
    consolidation: number;
    supply: number;
    llm_reason: string;
    total: number;
}

interface ChecklistDetail {
    has_news: boolean;
    news_sources: string[];
    is_new_high: boolean;
    is_breakout: boolean;
    supply_positive: boolean;
    volume_surge: boolean;
}

interface NewsItem {
    title: string;
    source: string;
    published_at: string;
    url: string;
}

interface Signal {
    stock_code: string;
    stock_name: string;
    market: string;
    sector: string;
    grade: string; // 'S', 'A', 'B', 'C'
    score: ScoreDetail;
    checklist: ChecklistDetail;
    current_price: number;
    entry_price: number;
    stop_price: number;
    target_price: number;
    change_pct: number;
    trading_value: number;
    news_items?: NewsItem[];
}

interface ScreenerResult {
    date: string;
    total_candidates: number;
    filtered_count: number;
    signals: Signal[];
    updated_at: string;
}
```

---

## 네이버 차트 위젯

```tsx
function NaverChartWidget({ symbol }: { symbol: string }) {
    const [timestamp] = useState(() => Date.now());

    return (
        <div className="flex flex-col items-center justify-center p-8 bg-white h-full relative">
            <div className="w-full flex-1 flex items-center justify-center overflow-hidden">
                <img
                    src={`https://ssl.pstatic.net/imgfinance/chart/item/candle/day/${symbol}.png?sidcode=${timestamp}`}
                    alt="Chart"
                    className="max-w-full max-h-full object-contain"
                />
            </div>
            <a
                href={`https://m.stock.naver.com/domestic/stock/${symbol}/chart`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-6 px-6 py-3 bg-[#03c75a] hover:bg-[#00b24e] text-white font-bold rounded-xl transition-all shadow-lg hover:shadow-xl flex items-center gap-2"
            >
                <span>View Interactive Chart (Naver)</span>
                <i className="fas fa-external-link-alt"></i>
            </a>
            <p className="mt-4 text-xs text-gray-400">
                * Static chart image provided by Naver Finance. Click the button for real-time interactive analysis.
            </p>
        </div>
    );
}
```

---

## 차트 모달

```tsx
function ChartModal({ symbol, name, onClose }: { symbol: string, name: string, onClose: () => void }) {
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleEsc);
        return () => window.removeEventListener('keydown', handleEsc);
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 transition-opacity animate-in fade-in duration-200" onClick={onClose}>
            <div
                className="bg-[#1c1c1e] w-full max-w-4xl h-[80vh] rounded-2xl border border-white/10 shadow-2xl flex flex-col overflow-hidden relative animate-in zoom-in-95 duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/5 bg-[#1c1c1e]">
                    <div className="flex items-center gap-3">
                        <h3 className="text-xl font-bold text-white">{name}</h3>
                        <span className="text-sm font-mono text-gray-400">{symbol}</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <i className="fas fa-times text-xl"></i>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 bg-white relative">
                    <NaverChartWidget symbol={symbol} />
                </div>
            </div>
        </div>
    );
}
```

---

## 메인 컴포넌트

### 상태 관리

```typescript
export default function JonggaV2Page() {
    const [data, setData] = useState<ScreenerResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [dates, setDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('latest');

    // 차트 모달 상태
    const [chartModal, setChartModal] = useState<{ isOpen: boolean, symbol: string, name: string }>({
        isOpen: false, symbol: '', name: ''
    });
```

### 날짜 목록 로드

```typescript
useEffect(() => {
    fetch('/api/kr/jongga-v2/dates')
        .then((res) => res.json())
        .then((data) => {
            if (Array.isArray(data)) {
                setDates(data);
            }
        })
        .catch((err) => console.error('Failed to fetch dates:', err));
}, []);
```

### 데이터 로드

```typescript
useEffect(() => {
    setLoading(true);
    let url = '/api/kr/jongga-v2/latest';
    if (selectedDate !== 'latest') {
        url = `/api/kr/jongga-v2/history/${selectedDate}`;
    }

    fetch(url)
        .then((res) => res.json())
        .then((data) => {
            setData(data);
            setLoading(false);
        })
        .catch((err) => {
            console.error('Failed to fetch data:', err);
            setLoading(false);
            setData(null);
        });
}, [selectedDate]);
```

---

## 헤더 섹션

```tsx
<div>
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/5 text-xs text-indigo-400 font-medium mb-4">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping"></span>
        AI Powered Strategy
    </div>
    <h2 className="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
        Closing <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">Bet V2</span>
    </h2>
    <p className="text-gray-400 text-lg">
        Gemini 3.0 Analysis + Institutional Supply Trend
    </p>
</div>
```

---

## 컨트롤 & 통계

```tsx
<div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/5">
    <div className="flex gap-6">
        <StatBox label="Candidates" value={data?.total_candidates || 0} />
        <StatBox label="Signals" value={data?.filtered_count || 0} highlight />
        <DataStatusBox updatedAt={data?.updated_at} />
    </div>
```

---

## 날짜 선택기

```tsx
<div className="flex items-center gap-3">
    <button
        onClick={() => setSelectedDate('latest')}
        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
            selectedDate === 'latest'
                ? 'bg-indigo-500 text-white'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
        }`}
    >
        Latest
    </button>
    <select
        value={selectedDate}
        onChange={(e) => setSelectedDate(e.target.value)}
        className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm font-bold focus:outline-none focus:border-indigo-500"
    >
        {dates.map((date) => (
            <option key={date} value={date} className="bg-[#1c1c1e]">
                {date}
            </option>
        ))}
    </select>
</div>
```

---

## 등급별 뱃지 색상

```typescript
const getGradeBadge = (grade: string) => {
    const config = {
        S: { bg: 'bg-rose-500/20', text: 'text-rose-400', border: 'border-rose-500/30' },
        A: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' },
        B: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
        C: { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' },
    };
    const c = config[grade] || config.C;
    return `px-2 py-0.5 rounded text-xs font-bold ${c.bg} ${c.text} ${c.border}`;
};
```

---

## 시그널 카드

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    {data?.signals?.map((signal) => (
        <div
            key={signal.stock_code}
            className="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 hover:border-indigo-500/30 transition-all"
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 flex items-center justify-center text-white font-bold">
                        {signal.stock_name[0]}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-white font-bold">{signal.stock_name}</span>
                            <span className={getGradeBadge(signal.grade)}>{signal.grade}</span>
                        </div>
                        <span className="text-xs text-gray-500 font-mono">{signal.stock_code}</span>
                    </div>
                </div>
                <button
                    onClick={() => setChartModal({ isOpen: true, symbol: signal.stock_code, name: signal.stock_name })}
                    className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                >
                    <i className="fas fa-chart-line"></i>
                </button>
            </div>

            {/* Score */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Score</span>
                    <span className="text-xl font-black text-white">{signal.score.total}/12</span>
                </div>
                <div className="text-xs text-gray-500">
                    뉴스 {signal.score.news} • 수급 {signal.score.supply} • 차트 {signal.score.chart}
                </div>
            </div>

            {/* Prices */}
            <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-lg bg-white/5">
                    <div className="text-[10px] text-gray-500">진입</div>
                    <div className="text-sm font-bold text-white">{signal.entry_price.toLocaleString()}</div>
                </div>
                <div className="p-2 rounded-lg bg-white/5">
                    <div className="text-[10px] text-gray-500">목표</div>
                    <div className="text-sm font-bold text-emerald-400">{signal.target_price.toLocaleString()}</div>
                </div>
                <div className="p-2 rounded-lg bg-white/5">
                    <div className="text-[10px] text-gray-500">손절</div>
                    <div className="text-sm font-bold text-red-400">{signal.stop_price.toLocaleString()}</div>
                </div>
            </div>

            {/* Checklist */}
            <div className="mt-3 pt-3 border-t border-white/5">
                <div className="flex gap-2 flex-wrap">
                    {signal.checklist.has_news && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-green-500/10 text-green-400">뉴스 있음</span>
                    )}
                    {signal.checklist.supply_positive && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400">수급 양호</span>
                    )}
                    {signal.checklist.is_new_high && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400">신고가</span>
                    )}
                </div>
            </div>
        </div>
    ))}
</div>
```

---

## API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/kr/jongga-v2/latest` | 최신 시그널 |
| `GET /api/kr/jongga-v2/dates` | 가능한 날짜 목록 |
| `GET /api/kr/jongga-v2/history/{date}` | 특정 날짜 시그널 |

---

## 차트 모달 사용

```tsx
{/* 모달 트리거 */}
<button
    onClick={() => setChartModal({ isOpen: true, symbol: signal.stock_code, name: signal.stock_name })}
>
    <i className="fas fa-chart-line"></i>
</button>

{/* 모달 렌더링 */}
{chartModal.isOpen && (
    <ChartModal
        symbol={chartModal.symbol}
        name={chartModal.name}
        onClose={() => setChartModal({ isOpen: false, symbol: '', name: '' })}
    />
)}
```
