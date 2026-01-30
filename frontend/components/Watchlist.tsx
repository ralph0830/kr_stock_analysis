/**
 * 관심종목(Watchlist) 컴포넌트
 * localStorage를 활용한 관심종목 관리
 */

"use client";

import { useState, useEffect } from "react";
import { useStore } from "@/store";
import { formatPrice, formatPercent, cn } from "@/lib/utils";
import { useRealtimePrices } from "@/hooks/useWebSocket";

interface WatchlistItem {
  ticker: string;
  name: string;
  addedAt: string;
}

const WATCHLIST_STORAGE_KEY = "ralph_stock_watchlist";

export function Watchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);

  // 관심종목 로드
  useEffect(() => {
    const stored = localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (stored) {
      try {
        setWatchlist(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse watchlist:", e);
      }
    }
  }, []);

  // 관심종목 저장
  const saveWatchlist = (items: WatchlistItem[]) => {
    setWatchlist(items);
    localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(items));
  };

  // 관심종목 추가
  const addToWatchlist = (ticker: string, name: string) => {
    const exists = watchlist.some((item) => item.ticker === ticker);
    if (!exists) {
      saveWatchlist([
        ...watchlist,
        { ticker, name, addedAt: new Date().toISOString() },
      ]);
    }
  };

  // 관심종목 제거
  const removeFromWatchlist = (ticker: string) => {
    saveWatchlist(watchlist.filter((item) => item.ticker !== ticker));
  };

  // 현재 시그널에서 관심종목 추가 가능 여부 확인
  const { signals } = useStore();
  const availableToAdd = signals.filter(
    (signal) => !watchlist.some((item) => item.ticker === signal.ticker)
  );

  // 실시간 가격 조회
  const tickers = watchlist.map((item) => item.ticker);
  const { prices, getPrice, connected } = useRealtimePrices(tickers);

  if (watchlist.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          ⭐ 관심종목
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-center py-4">
          관심종목이 없습니다.
        </p>
        {availableToAdd.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              시그널 종목에서 추가:
            </p>
            <div className="flex flex-wrap gap-2">
              {availableToAdd.slice(0, 5).map((signal) => (
                <button
                  key={signal.ticker}
                  onClick={() => addToWatchlist(signal.ticker, signal.name)}
                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm hover:bg-blue-200 dark:hover:bg-blue-800 transition"
                >
                  + {signal.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      {/* 헤더 */}
      <div
        className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          ⭐ 관심종목 ({watchlist.length})
        </h3>
        <button className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          {isExpanded ? "▼" : "▶"}
        </button>
      </div>

      {/* 관심종목 목록 */}
      {isExpanded && (
        <div className="p-4">
          <div className="space-y-3">
            {watchlist.map((item) => {
              const realtimePrice = getPrice(item.ticker);
              return (
                <div
                  key={item.ticker}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {item.name}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {item.ticker}
                      </span>
                    </div>
                    {connected && realtimePrice ? (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-sm text-gray-900 dark:text-gray-100">
                          {formatPrice(realtimePrice.price)}
                        </span>
                        <span
                          className={cn(
                            "text-xs px-2 py-0.5 rounded",
                            realtimePrice.change_rate >= 0
                              ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                              : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                          )}
                        >
                          {formatPercent(realtimePrice.change_rate)}
                        </span>
                      </div>
                    ) : (
                      <p className="text-xs text-gray-500 mt-1">데이터 대기 중...</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={`/chart?t=${item.ticker}`}
                      className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 transition"
                      title="차트 보기"
                    >
                      📊
                    </a>
                    <button
                      onClick={() => removeFromWatchlist(item.ticker)}
                      className="p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition"
                      title="제거"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 종목 추가 */}
          {availableToAdd.length > 0 && (
            <details className="mt-4">
              <summary className="text-sm text-blue-600 dark:text-blue-400 cursor-pointer hover:underline">
                + 종목 추가
              </summary>
              <div className="mt-2 flex flex-wrap gap-2">
                {availableToAdd.slice(0, 10).map((signal) => (
                  <button
                    key={signal.ticker}
                    onClick={() => addToWatchlist(signal.ticker, signal.name)}
                    className="px-3 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-full text-sm hover:bg-gray-300 dark:hover:bg-gray-500 transition"
                  >
                    {signal.name}
                  </button>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
