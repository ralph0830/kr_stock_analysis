# 프론트엔드 개선 방안
**전체 종목 실시간 가격 지원**

작성 일자: 2026-02-03
목표: VCP 스캔 결과로 선별된 모든 종목의 실시간 가격 표시

---

## 1. 현재 문제점

### 1.1 데이터 불일치

```
VCP 시그널 종목 (API에서 반환):
├── 0015N0 (아로마티카) - ELW
├── 493330 (지에프아이) - ELW
└── 217590 (티엠씨) - ELW

브로드캐스터 지원 종목:
├── 005930 (삼성전자) ✅
├── 000660 (SK하이닉스) ✅
├── 035420 (NAVER) ✅
├── 005380 (현대차) ✅
├── 028260 (삼성물산) ✅
└── 000020 (동화약품) ✅
```

**문제**: 시그널 종목이 브로드캐스터 지원 종목과 완전히 다릅니다.

### 1.2 UI 현황

```
┌─────────────────────────────────────┐
│ 아로마티카 (0015N0)                  │
│ [연결됨]                             │
│                                     │
│      데이터 대기 중...               │
│                                     │
│ (가격이 영원토 표시되지 않음)        │
└─────────────────────────────────────┘
```

---

## 2. 설계 원칙

### 2.1 핵심 원칙

1. **전체 종목 지원**: KOSPI, KOSDAQ, ELW, K-OTC 모든 종목의 가격 표시
2. **그레이스풀 데그레이션**: 실시간 → 폴링 → 캐시 순으로 데이터 소스 선택
3. **투명한 데이터 소스**: 사용자에게 어떤 방식으로 데이터를 가져오는지 표시
4. **성능 고려**: 불필요한 요청 최소화, 캐싱 활용

### 2.2 데이터 전략

| 종목 유형 | 1순위 | 2순위 | 3순위 |
|-----------|-------|-------|-------|
| KOSPI 대형주 | WebSocket | 캐시 | 폴링 |
| KOSPI 중소형주 | WebSocket | 캐시 | 폴링 |
| KOSDAQ | WebSocket | 캐시 | 폴링 |
| ELW | 폴링 | 캐시 | - |
| K-OTC | 폴링 | 캐시 | - |

---

## 3. 컴포넌트 개선

### 3.1 RealtimePriceCard 개선

**파일**: `frontend/components/RealtimePriceCard.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { useRealtimePrices } from "@/hooks/useWebSocket";
import { apiClient } from "@/lib/api-client";
import { formatPrice, formatPercent, cn } from "@/lib/utils";

interface RealtimePriceCardProps {
  ticker: string;
  name: string;
}

// 데이터 소스 타입
type DataSourceType = "realtime" | "polling" | "cached" | "none";

// 종목 분류 (실시간 지원 여부)
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "ELW" | "OTC" | "UNKNOWN";
  realtimeSupported: boolean;
} {
  // K-OTC: 10자리
  if (ticker.length === 10) {
    return { category: "OTC", realtimeSupported: false };
  }

  // ELW: 알파벳 포함
  if (/[A-Za-z]/.test(ticker)) {
    return { category: "ELW", realtimeSupported: false };
  }

  // KOSPI/KOSDAQ 구분 (0으로 시작하면 KOSPI)
  if (ticker.startsWith("0") || ticker.startsWith("00") || ticker.startsWith("000")) {
    return { category: "KOSPI", realtimeSupported: true };
  }

  return { category: "KOSDAQ", realtimeSupported: true };
}

export function RealtimePriceCard({ ticker, name }: RealtimePriceCardProps) {
  const { prices, getPrice, connected, error } = useRealtimePrices([ticker]);
  const realtimePrice = getPrice(ticker);
  const { category, realtimeSupported } = getTickerCategory(ticker);

  // 폴링 데이터 상태
  const [pollingPrice, setPollingPrice] = useState<any>(null);
  const [dataSource, setDataSource] = useState<DataSourceType>("none");
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // WebSocket 데이터가 있으면 사용
  if (realtimePrice) {
    return <PriceDisplay
      ticker={ticker}
      name={name}
      price={realtimePrice}
      dataSource="realtime"
      connected={connected}
    />;
  }

  // 폴링 Fallback
  useEffect(() => {
    // WebSocket이 지원하면 폴링 안 함
    if (realtimeSupported && connected) {
      return;
    }

    // 폴링 시작
    setPollingPrice(null);
    setDataSource("polling");

    const fetchPollingPrice = async () => {
      try {
        const prices = await apiClient.getRealtimePrices([ticker], {
          include_elw: true,  // ELW 포함
        });

        if (prices[ticker]) {
          setPollingPrice(prices[ticker]);
          setLastUpdate(new Date(prices[ticker].timestamp));
        }
      } catch (e) {
        console.error(`[Polling] Failed to fetch price for ${ticker}:`, e);
      }
    };

    // 즉시 실행
    fetchPollingPrice();

    // 주기적 폴링
    const interval = setInterval(fetchPollingPrice, 15000);  // 15초

    return () => clearInterval(interval);
  }, [ticker, realtimeSupported, connected, realtimePrice]);

  // 표시할 데이터
  const displayPrice = realtimePrice || pollingPrice;

  // 에러 상태
  if (error) {
    return <ErrorState ticker={ticker} name={name} error={error} />;
  }

  // 로딩 상태
  if (!displayPrice) {
    return <LoadingState ticker={ticker} name={name} />;
  }

  // 데이터 소스 뱃지 컴포넌트
  function DataSourceBadge() {
    if (dataSource === "realtime") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          실시간
        </span>
      );
    }

    if (dataSource === "polling") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
          폴링 {category}
        </span>
      );
    }

    return null;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg hover:shadow-xl transition-all">
      {/* 종목 정보 헤더 */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {ticker} • {category}
          </p>
        </div>
        <DataSourceBadge />
      </div>

      {/* 가격 정보 */}
      <div className="mb-4">
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            {formatPrice(displayPrice.price)}
          </span>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm font-medium",
                displayPrice.change > 0
                  ? "text-red-600 dark:text-red-400"
                  : displayPrice.change < 0
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-600"
              )}
            >
              {displayPrice.change > 0 ? "+" : ""}
              {formatPrice(displayPrice.change)}
            </span>
            <span
              className={cn(
                "text-sm font-medium",
                displayPrice.change_rate > 0
                  ? "text-red-600 dark:text-red-400"
                  : displayPrice.change_rate < 0
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-600"
              )}
            >
              ({formatPercent(displayPrice.change_rate)})
            </span>
          </div>
        </div>
      </div>

      {/* 추가 정보 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400">거래량</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {displayPrice.volume?.toLocaleString() || "-"}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">업데이트</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {lastUpdate
              ? lastUpdate.toLocaleTimeString("ko-KR")
              : "-"}
          </p>
        </div>
      </div>

      {/* 데이터 소스 안내 */}
      {dataSource === "polling" && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {realtimeSupported
              ? "현재 실시간 연결이 없습니다. 15초마다 업데이트됩니다."
              : `${category} 종목은 폴링으로 업데이트됩니다.`}
          </p>
        </div>
      )}

      {/* 변동 바 */}
      <div className="mt-4 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-300",
            displayPrice.change_rate > 0
              ? "bg-red-500 dark:bg-red-400"
              : displayPrice.change_rate < 0
              ? "bg-blue-500 dark:bg-blue-400"
              : "bg-gray-400"
          )}
          style={{
            width: `${Math.min(Math.abs(displayPrice.change_rate) * 10, 100)}%`,
          }}
        />
      </div>
    </div>
  );
}

// 로딩 상태 컴포넌트
function LoadingState({ ticker, name }: { ticker: string; name: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
        </div>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
          로딩 중...
        </span>
      </div>
      <div className="flex items-center justify-center py-8">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    </div>
  );
}

// 에러 상태 컴포넌트
function ErrorState({ ticker, name, error }: { ticker: string; name: string; error?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
        </div>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
          연결 실패
        </span>
      </div>
      <div className="text-center py-4">
        <p className="text-red-500 dark:text-red-400 text-sm">
          데이터를 불러오지 못했습니다
        </p>
        <p className="text-gray-500 dark:text-gray-400 text-xs mt-2">
          {error || "서버 상태를 확인해주세요"}
        </p>
      </div>
    </div>
  );
}

// 가격 표시 컴포넌트
function PriceDisplay({
  ticker,
  name,
  price,
  dataSource,
  connected,
}: {
  ticker: string;
  name: string;
  price: any;
  dataSource: DataSourceType;
  connected: boolean;
}) {
  const isPositive = price.change > 0;
  const isNegative = price.change < 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg hover:shadow-xl transition-all">
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
        </div>
        <DataSourceBadge
          source={dataSource}
          connected={connected}
        />
      </div>

      {/* 가격 */}
      <div className="mb-4">
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            {formatPrice(price.price)}
          </span>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm font-medium",
                isPositive ? "text-red-600" : isNegative ? "text-blue-600" : "text-gray-600"
              )}
            >
              {isPositive ? "+" : ""}{formatPrice(price.change)}
            </span>
            <span
              className={cn(
                "text-sm font-medium",
                isPositive ? "text-red-600" : isNegative ? "text-blue-600" : "text-gray-600"
              )}
            >
              ({formatPercent(price.change_rate)})
            </span>
          </div>
        </div>
      </div>

      {/* 추가 정보 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500">거래량</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {price.volume?.toLocaleString() || "-"}
          </p>
        </div>
        <div>
          <p className="text-gray-500">업데이트</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {price.timestamp ? new Date(price.timestamp).toLocaleTimeString("ko-KR") : "-"}
          </p>
        </div>
      </div>

      {/* 변동 바 */}
      <div className="mt-4 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-300",
            isPositive ? "bg-red-500" : isNegative ? "bg-blue-500" : "bg-gray-400"
          )}
          style={{ width: `${Math.min(Math.abs(price.change_rate) * 10, 100)}%` }}
        />
      </div>
    </div>
  );
}

// 데이터 소스 뱃지
function DataSourceBadge({ source, connected }: { source: DataSourceType; connected?: boolean }) {
  if (source === "realtime" && connected) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
        실시간
      </span>
    );
  }

  if (source === "polling") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
        <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
        폴링
      </span>
    );
  }

  return null;
}
```

---

## 4. API 클라이언트 개선

**파일**: `frontend/lib/api-client.ts`

```typescript
/**
 * 실시간 가격 조회 (폴링 방식)
 * WebSocket 미지원 종목(ELW, K-OTC)을 위한 폴링 API
 */
async getRealtimePricesPolling(
  tickers: string[],
  options?: {
    include_elw?: boolean;
    cache_ttl?: number;
  }
): Promise<Record<string, StockPrice>> {
  const params: any = {
    tickers: tickers.join(","),
    include_elw: options?.include_elw ?? true,
    cache_ttl: options?.cache_ttl ?? 10,  // 10초 캐시
  };

  const response = await this.apiClient.get<{
    prices: Record<string, StockPrice>;
  }>(`/api/kr/realtime-prices`, { params });

  return response.data.prices;
}

// 기존 메서드에 별칭 추가
async getRealtimePrices(
  tickers: string[]
): Promise<Record<string, StockPrice>> {
  // WebSocket 연결 확인
  const wsConnected = this.checkWebSocketConnection();

  if (wsConnected) {
    // WebSocket이면 메시지로 요청 (기존 방식)
    return this._getRealtimePricesViaWebSocket(tickers);
  } else {
    // WebSocket 연결 안 되면 폴링으로 대체
    return this.getRealtimePricesPolling(tickers, { include_elw: true });
  }
}

private checkWebSocketConnection(): boolean {
  // WebSocket 연결 상태 확인
  // (구현 필요)
  return false;
}

private _getRealtimePricesViaWebSocket(
  tickers: string[]
): Promise<Record<string, StockPrice>> {
  // WebSocket 메시지 전송 방식
  // (구현 필요)
  return Promise.resolve({});
}
```

---

## 5. 훅 개선

**파일**: `frontend/hooks/useWebSocket.ts`

```typescript
/**
 * 실시간 가격 데이터만 사용하는 훅
 *
 * 개선사항:
 * - 폴링 Fallback 지원
 * - 전체 종목 지원 (KOSPI, KOSDAQ, ELW)
 * - 데이터 소스 표시
 */
export function useRealtimePrices(tickers: string[]) {
  const [prices, setPrices] = useState<Map<string, RealtimePrice>>(new Map());
  const [pollingPrices, setPollingPrices] = useState<Map<string, RealtimePrice>>(new Map());

  const { connected, subscribe, unsubscribe, error, connecting } = useWebSocket({
    autoConnect: true,
    onPriceUpdate: (price) => {
      setPrices((prev) => {
        const next = new Map(prev);
        next.set(price.ticker, price);
        return next;
      });
    },
  });

  // WebSocket 구독 (실시간 지원 종목만)
  const realtimeSupportedTickers = tickers.filter(t =>
    !isELW(t) && !isOTC(t)
  );

  useEffect(() => {
    if (connected) {
      realtimeSupportedTickers.forEach((ticker) => {
        console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
        subscribe(`price:${ticker}`);
      });
    }

    return () => {
      realtimeSupportedTickers.forEach((ticker) => {
        unsubscribe(`price:${ticker}`);
      });
    };
  }, [realtimeSupportedTickers.join(","), subscribe, unsubscribe, connected]);

  // 폴링 Fallback (WebSocket 미지원 종목)
  useEffect(() => {
    // 실시간 지원 종목은 폴링 안 함
    const pollingTargets = tickers.filter(t =>
      !realtimeSupportedTickers.includes(t)
    );

    if (pollingTargets.length === 0) return;

    const fetchPollingPrices = async () => {
      try {
        const prices = await apiClient.getRealtimePricesPolling(pollingTargets, {
          include_elw: true,
        });

        setPollingPrices((prev) => {
          const next = new Map(prev);
          Object.entries(prices).forEach(([ticker, price]) => {
            next.set(ticker, {
              ticker: price.ticker,
              price: price.price,
              change: price.change,
              change_rate: price.change_rate,
              volume: price.volume,
              timestamp: price.timestamp,
              is_polling: true,  // 폴링 데이터 표시
            } as RealtimePrice);
          });
          return next;
        });
      } catch (e) {
        console.error("[useRealtimePrices] Polling failed:", e);
      }
    };

    // 즉시 실행
    fetchPollingPrices();

    // 주기적 폴링
    const interval = setInterval(fetchPollingPrices, 15000);

    return () => clearInterval(interval);
  }, [pollingTargets.join(",")]);

  // 병합 데이터 (실시간 + 폴링)
  const combinedPrices = new Map([
    ...prices,
    ...pollingPrices,
  ]);

  const getPrice = useCallback(
    (ticker: string): RealtimePrice | undefined => {
      return combinedPrices.get(ticker);
    },
    [combinedPrices]
  );

  return {
    prices: Object.fromEntries(combinedPrices),
    getPrice,
    connected,
    error,
    connecting,
  };
}

// 헬퍼 함수
function isELW(ticker: string): boolean {
  // 알파벳이 포함되어 있으면 ELW
  return /[A-Za-z]/.test(ticker);
}

function isOTC(ticker: string): boolean {
  // 10자리면 K-OTC
  return ticker.length === 10;
}
```

---

## 6. 랜딩 페이지 개선

**파일**: `frontend/app/page.tsx`

```typescript
"use client";

import { useEffect, useMemo, useState } from "react";
import { useStore } from "@/store";
import { useMarketGate } from "@/hooks/useWebSocket";
import { RealtimePriceGrid, WebSocketStatus } from "@/components/RealtimePriceCard";
import { Watchlist } from "@/components/Watchlist";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function HomePage() {
  const [showDashboard, setShowDashboard] = useState(false);
  const [excludeELW, setExcludeELW] = useState(true);  // ELW 필터
  const [marketFilter, setMarketFilter] = useState<"ALL" | "KOSPI" | "KOSDAQ">("ALL");

  const {
    signals,
    loadingSignals,
    fetchSignals,
  } = useStore();

  // Market Gate 실시간 WebSocket Hook 사용
  const { marketGate, isRealtime, connected, lastUpdate } = useMarketGate();

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // 시그널 필터링
  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      // ELW 필터링
      if (excludeELW && isELW(signal.ticker)) {
        return false;
      }
      // 시장 필터링
      if (marketFilter !== "ALL" && signal.market !== marketFilter) {
        return false;
      }
      return true;
    });
  }, [signals, excludeELW, marketFilter]);

  // 실시간 가격 모니터링할 종목 목록 (필터링된 시그널)
  const realtimeTickers = useMemo(() => {
    return filteredSignals.slice(0, 6).map((signal) => ({
      ticker: signal.ticker,
      name: signal.name,
    }));
  }, [filteredSignals]);

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                📊 Ralph Stock 대시보드
              </h1>
              <WebSocketStatus />
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <button
                onClick={() => setShowDashboard(!showDashboard)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
              >
                {showDashboard ? "간단 보기" : "전체 보기"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* 필터 컨트롤 */}
        <section className="mb-6">
          <div className="flex flex-wrap gap-4 items-center bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="flex items-center gap-2">
              <label htmlFor="market-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                시장:
              </label>
              <select
                id="market-filter"
                value={marketFilter}
                onChange={(e) => setMarketFilter(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="ALL">전체</option>
                <option value="KOSPI">KOSPI</option>
                <option value="KOSDAQ">KOSDAQ</option>
              </select>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={excludeELW}
                onChange={(e) => setExcludeELW(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                ELW 제외
              </span>
            </label>

            <div className="ml-auto text-sm text-gray-500 dark:text-gray-400">
              총 {filteredSignals.length}개 시그널
            </div>
          </div>
        </section>

        {/* Market Gate 상태 섹션 */}
        <section>
          {/* 기존 Market Gate 표시 */}
          {/* ... */}
        </section>

        {/* 실시간 가격 모니터링 */}
        {realtimeTickers.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              실시간 가격 모니터링
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({realtimeTickers.length}종목)
              </span>
            </h2>
            <RealtimePriceGrid stocks={realtimeTickers} />
          </section>
        )}

        {/* VCP Signals */}
        {!showDashboard && filteredSignals.length > 0 && (
          <section>
            {/* 기존 시그널 테이블 */}
          </section>
        )}

        {/* 안내 메시지 */}
        {filteredSignals.length === 0 && !loadingSignals && (
          <section className="text-center py-16">
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              현재 활성화된 시그널이 없습니다.
            </p>
            {excludeELW && signals.length > 0 && (
              <button
                onClick={() => setExcludeELW(false)}
                className="text-blue-600 hover:text-blue-800 underline"
              >
                ELW 포함하여 다시 검색
              </button>
            )}
          </section>
        )}
      </div>
    </main>
  );
}

function isELW(ticker: string): boolean {
  return /[A-Za-z]/.test(ticker);
}
```

---

## 7. 타입 정의 추가

**파일**: `frontend/types/index.ts`

```typescript
/**
 * 실시간 가격 데이터
 */
export interface RealtimePrice {
  ticker: string;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  timestamp: string;
  is_polling?: boolean;  // 폴링 여부
}

/**
 * 데이터 소스 정보
 */
export interface DataSource {
  type: "realtime" | "polling" | "cached";
  latency?: number;  // 데이터 지연 (ms)
  last_update: string;
}

/**
 * 종목 분류 정보
 */
export interface TickerCategory {
  ticker: string;
  category: "KOSPI" | "KOSDAQ" | "ELW" | "OTC";
  realtime_supported: boolean;
}

/**
 * 종목 필터 옵션
 */
export interface TickerFilterOptions {
  market?: "ALL" | "KOSPI" | "KOSDAQ";
  exclude_elw?: boolean;
  min_market_cap?: number;
  max_tickers?: number;
}
```

---

## 8. 유틸리티 개선 사항

### 8.1 로딩 스켈레톤

```typescript
// 그리디어 로딩: 실시간 데이터 먼저 표시
// 폴링 데이터가 도착하면 업데이트

const [initialPrices, setInitialPrices] = useState<Record<string, RealtimePrice>>({});

// 페이지 로드 시 빠른 폴링으로 초기 데이터 로드
useEffect(() => {
  const loadInitialPrices = async () => {
    const prices = await apiClient.getRealtimePricesPolling(
      realtimeTickers.map(s => s.ticker),
      { include_elw: true }
    );
    setInitialPrices(prices);
  };

  loadInitialPrices();
}, [realtimeTickers]);
```

### 8.2 에러 복구

```typescript
// 폴링 실패 시 재시도 로직
const fetchWithRetry = async (ticker: string, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const prices = await apiClient.getRealtimePricesPolling([ticker], {
        include_elw: true,
      });
      return prices[ticker];
    } catch (e) {
      if (i === retries - 1) {
        console.error(`[Polling] Failed after ${retries} attempts for ${ticker}:`, e);
        return null;
      }
      // 지연 후 재시도
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};
```

### 8.3 접근성 개선

```typescript
// aria-live를 사용한 스크린 리더더 지원
<div
  role="status"
  aria-live="polite"
  aria-label={`${name} (${ticker}) 가격 정보`}
>
  <p>현재가: {formatPrice(displayPrice.price)}원</p>
  <p>전일대비: {formatPercent(displayPrice.change_rate)}</p>
  {dataSource === "polling" && (
    <p aria-label="데이터 업데이트 방법">
      15초마다 폴링으로 업데이트됩니다
    </p>
  )}
</div>
```

---

## 9. 테스트 가이드

### 9.1 KOSPI 대형주 테스트

1. 삼성전자(005930) 카드 확인
2. "실시간" 뱃지 표시
3. 가격 실시간 업데이트 확인

### 9.2 ELW 종목 테스트

1. 아로마티카(0015N0) 카드 확인
2. "폴링 ELW" 뱃지 표시
3. 15초마다 가격 업데이트 확인

### 9.3 필터링 테스트

1. ELW 제외 체크박스
2. 시장 필터 (KOSPI/KOSDAQ/전체)
3. 필터 적용 후 종목 수 확인

---

## 10. 완료 상태 (Implementation Status)

### 10.1 Phase 1: WebSocket 구독 버그 수정 ✅

**완료일자**: 2026-02-03

**관련 보고서**: `realtime_price_issue_analysis_20260203.md`

**문제**: `useRealtimePrices` 훅이 WebSocket 연결 상태를 확인하지 않고 구독을 시도하여, 연결되지 않은 상태에서 구독 요청이 대기열에만 추가되고 실제 전송이 이루어지지 않음.

**해결**: `useMarketGate`와 동일한 패턴으로 `connected` 상태 확인 추가

**수정 파일**: `frontend/hooks/useWebSocket.ts:395-414`

```typescript
// 수정 전: 연결 상태 확인 없음
useEffect(() => {
  tickers.forEach((ticker) => {
    subscribe(`price:${ticker}`);
  });
  // ...
}, [tickers.join(","), subscribe, unsubscribe]); // ❌ connected 없음

// 수정 후: 연결 상태 확인 추가
useEffect(() => {
  if (!connected) {  // ✅ 연결 상태 확인
    console.log(`[useRealtimePrices] Waiting for connection...`);
    return;
  }

  tickers.forEach((ticker) => {
    console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
    subscribe(`price:${ticker}`);
  });
  // ...
}, [tickers.join(","), subscribe, unsubscribe, connected]); // ✅ connected 추가
```

### 10.2 검증 방법

**브라우저 Console 확인**:
```bash
# 1. http://localhost:5110 또는 https://stock.ralphpark.com/ 접속
# 2. Console에 다음 로그 순서 확인:
[useRealtimePrices] Waiting for connection...
[useRealtimePrices] Subscribing to price:005930
```

**서버 구독자 확인**:
```bash
curl http://localhost:5111/ws/stats | jq '.subscriptions'

# 기대 결과:
{
  "price:005930": 1,  # ← 0이 아니어야 함
  "price:000660": 1,
  "market-gate": 1
}
```

### 10.3 진행 중/예정 (TODO)

| 항목 | 상태 | 우선순위 |
|------|------|----------|
| ELW/K-OTC 폴링 Fallback | 예정 | 높음 |
| 데이터 소스 뱃지 UI | 예정 | 중간 |
| 필터링 컨트롤 (ELW 제외) | 예정 | 중간 |
| 초기 로딩 스켈레톤 | 예정 | 낮음 |
| 접근성 개선 (aria-live) | 예정 | 낮음 |

---

*프론트엔드 개선 방안 종료*

*마지막 수정: 2026-02-03*
