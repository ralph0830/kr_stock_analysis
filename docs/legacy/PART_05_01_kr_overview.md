# PART 05-1: KR Market Overview (메인 대시보드)

> **파일**: `frontend/src/app/dashboard/kr/page.tsx`
> **용도**: 한국 주식 시장 개요 대시보드 페이지
> **프레임워크**: Next.js 14 App Router, React

---

## 개요

KR Market Overview 페이지는 다음을 표시합니다:

- **Market Gate**: 시장 상태 점수 (원형 프로그레스)
- **섹터 지표**: KOSPI 200 섹터별bullish/bearish 상태
- **KPI 카드**: 오늘 시그널, VCP/Closing Bet 성과
- **시장 지수**: KOSPI/KOSDAQ 실시간

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
const [gateData, setGateData] = useState<KRMarketGate | null>(null);
const [signalsData, setSignalsData] = useState<KRSignalsResponse | null>(null);
const [backtestData, setBacktestData] = useState<BacktestSummary | null>(null);
const [loading, setLoading] = useState(true);
const [lastUpdated, setLastUpdated] = useState<string>('');
```

---

## 데이터 로드

```typescript
const loadData = async () => {
    setLoading(true);
    try {
        // Load core data
        const [gate, signals] = await Promise.all([
            krAPI.getMarketGate(),
            krAPI.getSignals(),
        ]);
        setGateData(gate);
        setSignalsData(signals);

        // Load Backtest Summary
        const btRes = await fetch('/api/kr/backtest-summary');
        if (btRes.ok) {
            setBacktestData(await btRes.json());
        }

        setLastUpdated(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }));
    } catch (error) {
        console.error('Failed to load KR Market data:', error);
    } finally {
        setLoading(false);
    }
};
```

---

## 유틸리티 함수

### `getGateColor()` - 게이트 점수 색상

```typescript
const getGateColor = (score: number) => {
    if (score >= 70) return 'text-green-500';
    if (score >= 40) return 'text-yellow-500';
    return 'text-red-500';
};
```

### `getSectorColor()` - 섹터 신호 색상

```typescript
const getSectorColor = (signal: string) => {
    if (signal === 'bullish') return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (signal === 'bearish') return 'bg-red-500/20 text-red-400 border-red-500/30';
    return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
};
```

---

## Market Gate 섹션

### 게이트 점수 카드 (원형 프로그레스)

```tsx
<div className="lg:col-span-1 p-6 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group">
    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-rose-500">
        <i className="fas fa-chart-line text-4xl"></i>
    </div>
    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
        KR Market Gate
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
    </h3>
    <div className="flex flex-col items-center justify-center py-2">
        <div className="relative w-32 h-32 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90">
                <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/5" />
                <circle
                    cx="64" cy="64" r="58"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="transparent"
                    strokeDasharray="364.4"
                    strokeDashoffset={364.4 - (364.4 * (gateData?.score ?? 0) / 100)}
                    className={`${getGateColor(gateData?.score ?? 0)} transition-all duration-1000 ease-out`}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-3xl font-black ${getGateColor(gateData?.score ?? 0)}`}>
                    {loading ? '--' : gateData?.score ?? '--'}
                </span>
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Score</span>
            </div>
        </div>
        <div className="mt-4 px-4 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-bold text-gray-400">
            {loading ? 'Analyzing...' : gateData?.label ?? 'N/A'}
        </div>
    </div>
</div>
```

### 섹터 그리드

```tsx
<div className="lg:col-span-3 p-6 rounded-2xl bg-[#1c1c1e] border border-white/10">
    <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-gray-400">KOSPI 200 Sector Index</h3>
        <div className="flex items-center gap-4 text-[10px] font-bold text-gray-500 uppercase tracking-tighter">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span> Bullish</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500"></span> Neutral</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> Bearish</span>
        </div>
    </div>
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse border border-white/5"></div>
            ))
        ) : (
            gateData?.sectors?.map((sector) => (
                <div
                    key={sector.name}
                    className={`p-3 rounded-xl border ${getSectorColor(sector.signal)} transition-all hover:scale-105`}
                >
                    <div className="text-xs font-bold truncate">{sector.name}</div>
                    <div className={`text-lg font-black ${sector.change_pct >= 0 ? 'text-rose-400' : 'text-blue-400'}`}>
                        {sector.change_pct >= 0 ? '+' : ''}{sector.change_pct.toFixed(2)}%
                    </div>
                </div>
            ))
        )}
    </div>
</div>
```

---

## KPI 카드

### 1. 오늘 시그널

```tsx
<div className="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-rose-500/30 transition-all">
    <div className="absolute top-0 right-0 w-20 h-20 bg-rose-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2"></div>
    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Today's Signals</div>
    <div className="text-3xl font-black text-white group-hover:text-rose-400 transition-colors">
        {loading ? '--' : signalsData?.signals?.length ?? 0}
    </div>
    <div className="mt-2 text-xs text-gray-500">VCP + 외국인 순매수</div>
</div>
```

### 2. VCP 전략 성과

```tsx
<div className="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-amber-500/30 transition-all">
    <div className="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2"></div>
    <div className="flex justify-between items-start">
        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">VCP Strategy</div>
        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 text-[10px] font-bold border border-amber-500/20">Win Rate</span>
    </div>
    <div className="flex items-baseline gap-2">
        <span className="text-3xl font-black text-white group-hover:text-amber-400 transition-colors">
            {loading ? '--' : backtestData?.vcp?.win_rate ?? 0}<span className="text-base text-gray-600">%</span>
        </span>
        <span className={`text-xs font-bold ${(backtestData?.vcp?.avg_return ?? 0) > 0 ? 'text-red-400' : 'text-blue-400'}`}>
            Avg. {(backtestData?.vcp?.avg_return ?? 0) > 0 ? '+' : ''}{backtestData?.vcp?.avg_return}%
        </span>
    </div>
    <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
        <span>{renderTradeCount(backtestData?.vcp?.count ?? 0)}</span>
        {backtestData?.vcp?.status === 'OK' && <i className="fas fa-check-circle text-emerald-500"></i>}
    </div>
</div>
```

### 3. Closing Bet 성과

```tsx
<div className="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-emerald-500/30 transition-all">
    <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2"></div>
    <div className="flex justify-between items-start">
        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Closing Bet</div>
        {backtestData?.closing_bet?.status === 'Accumulating' ? (
            <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[10px] font-bold border border-amber-500/20 animate-pulse">
                <i className="fas fa-hourglass-half mr-1"></i>축적 중
            </span>
        ) : (
            <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 text-[10px] font-bold border border-emerald-500/20">Win Rate</span>
        )}
    </div>
    {backtestData?.closing_bet?.status === 'Accumulating' ? (
        <div className="py-4">
            <div className="text-2xl font-black text-amber-400 mb-1">
                <i className="fas fa-database mr-2"></i>데이터 축적 중
            </div>
            <div className="text-xs text-gray-500">
                {backtestData?.closing_bet?.message || '최소 2일 데이터 필요'}
            </div>
        </div>
    ) : (
        <>
            <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black text-white group-hover:text-emerald-400 transition-colors">
                    {loading ? '--' : backtestData?.closing_bet?.win_rate ?? 0}<span className="text-base text-gray-600">%</span>
                </span>
                <span className={`text-xs font-bold ${(backtestData?.closing_bet?.avg_return ?? 0) > 0 ? 'text-red-400' : 'text-blue-400'}`}>
                    Avg. {(backtestData?.closing_bet?.avg_return ?? 0) > 0 ? '+' : ''}{backtestData?.closing_bet?.avg_return}%
                </span>
            </div>
            <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
                <span>{renderTradeCount(backtestData?.closing_bet?.count ?? 0)}</span>
                {backtestData?.closing_bet?.status === 'OK' && <i className="fas fa-check-circle text-emerald-500"></i>}
            </div>
        </>
    )}
</div>
```

### 4. 리프레시 버튼

```tsx
<button
    onClick={loadData}
    disabled={loading}
    className="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 flex flex-col justify-center items-center gap-2 cursor-pointer hover:bg-white/5 transition-all group disabled:opacity-50"
>
    <div className={`w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-white group-hover:rotate-180 transition-transform duration-500 ${loading ? 'animate-spin' : ''}`}>
        <i className="fas fa-sync-alt"></i>
    </div>
    <div className="text-center">
        <div className="text-sm font-bold text-white">Refresh Data</div>
        <div className="text-[10px] text-gray-500">Last: {lastUpdated || '-'}</div>
    </div>
</button>
```

---

## 시장 지수 섹션

```tsx
<section>
    <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span className="w-1 h-5 bg-rose-500 rounded-full"></span>
            Market Indices
        </h3>
        <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">KOSPI / KOSDAQ</span>
    </div>
    <div className="grid grid-cols-2 gap-4">
        <div className="p-4 rounded-2xl bg-[#1c1c1e] border border-white/10">
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1">KOSPI</div>
            <div className="flex items-end gap-2">
                <span className="text-xl font-black text-white">
                    {loading ? '--' : gateData?.kospi_close?.toLocaleString() ?? '--'}
                </span>
                {gateData && (
                    <span className={`text-xs font-bold mb-0.5 ${gateData.kospi_change_pct >= 0 ? 'text-rose-400' : 'text-blue-400'}`}>
                        <i className={`fas fa-caret-${gateData.kospi_change_pct >= 0 ? 'up' : 'down'} mr-0.5`}></i>
                        {gateData.kospi_change_pct >= 0 ? '+' : ''}{gateData.kospi_change_pct?.toFixed(2)}%
                    </span>
                )}
            </div>
        </div>
        <div className="p-4 rounded-2xl bg-[#1c1c1e] border border-white/10">
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1">KOSDAQ</div>
            <div className="flex items-end gap-2">
                <span className="text-xl font-black text-white">
                    {loading ? '--' : gateData?.kosdaq_close?.toLocaleString() ?? '--'}
                </span>
                {gateData && (
                    <span className={`text-xs font-bold mb-0.5 ${gateData.kosdaq_change_pct >= 0 ? 'text-rose-400' : 'text-blue-400'}`}>
                        <i className={`fas fa-caret-${gateData.kosdaq_change_pct >= 0 ? 'up' : 'down'} mr-0.5`}></i>
                        {gateData.kosdaq_change_pct >= 0 ? '+' : ''}{gateData.kosdaq_change_pct?.toFixed(2)}%
                    </span>
                )}
            </div>
        </div>
    </div>
</section>
```

---

## API 호출

```typescript
// lib/api.ts
export const krAPI = {
    getMarketGate: (): Promise<KRMarketGate> =>
        fetch('/api/kr/market-gate').then(r => r.json()),

    getSignals: (): Promise<KRSignalsResponse> =>
        fetch('/api/kr/signals').then(r => r.json()),
};
```

---

## 타입 정의

```typescript
// types/kr.ts
export interface KRMarketGate {
    score: number;
    label: string;
    kospi_close: number;
    kospi_change_pct: number;
    kosdaq_close: number;
    kosdaq_change_pct: number;
    sectors: Array<{
        name: string;
        signal: 'bullish' | 'neutral' | 'bearish';
        change_pct: number;
    }>;
}

export interface KRSignalsResponse {
    signals: Array<{
        ticker: string;
        name: string;
        market: string;
        // ...
    }>;
    generated_at: string;
}
```
