/**
 * 실시간 가격 표시 카드 컴포넌트
 */
"use client";

import { useEffect } from "react";
import { useRealtimePrices, useWebSocket } from "@/hooks/useWebSocket";
import { formatPrice, formatPercent, formatNumber, cn } from "@/lib/utils";

interface RealtimePriceCardProps {
  ticker: string;
  name: string;
}

export function RealtimePriceCard({ ticker, name }: RealtimePriceCardProps) {
  const { prices, getPrice, connected, error, connecting } = useRealtimePrices([ticker]);

  const realtimePrice = getPrice(ticker);

  // 에러 상태
  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
          </div>
          <div className="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
            연결 실패
          </div>
        </div>
        <div className="text-center py-4">
          <p className="text-red-500 dark:text-red-400 text-sm">
            WebSocket 연결 실패
          </p>
          <p className="text-gray-500 dark:text-gray-400 text-xs mt-2">
            서버가 실행 중인지 확인하세요
          </p>
        </div>
      </div>
    );
  }

  // 연결 중 또는 데이터 없음
  if (!realtimePrice) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
          </div>
          <div
            className={cn(
              "px-2 py-1 rounded text-xs font-medium",
              connected
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : connecting
                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
            )}
          >
            {connected ? "연결됨" : connecting ? "연결 중..." : "대기 중"}
          </div>
        </div>
        <div className="text-center py-4">
          <p className="text-gray-500 dark:text-gray-400">
            {connecting ? "연결 중..." : "데이터 대기 중..."}
          </p>
        </div>
      </div>
    );
  }

  const isPositive = realtimePrice.change > 0;
  const isNegative = realtimePrice.change < 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg transition-all hover:shadow-xl">
      {/* 종목 정보 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
        </div>
        <div
          className={cn(
            "px-2 py-1 rounded text-xs font-medium",
            connected
              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
              : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
          )}
        >
          {connected ? "실시간" : "연결 안됨"}
        </div>
      </div>

      {/* 가격 정보 */}
      <div className="mb-4">
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            {formatPrice(realtimePrice.price)}
          </span>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm font-medium",
                isPositive
                  ? "text-red-600 dark:text-red-400"
                  : isNegative
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-600 dark:text-gray-400"
              )}
            >
              {isPositive ? "+" : ""}
              {formatPrice(realtimePrice.change)}
            </span>
            <span
              className={cn(
                "text-sm font-medium",
                isPositive
                  ? "text-red-600 dark:text-red-400"
                  : isNegative
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-600 dark:text-gray-400"
              )}
            >
              ({isPositive ? "+" : ""}
              {formatPercent(realtimePrice.change_rate)})
            </span>
          </div>
        </div>
      </div>

      {/* 추가 정보 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400 mb-1">거래량</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {formatNumber(realtimePrice.volume)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400 mb-1">업데이트</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {new Date(realtimePrice.timestamp).toLocaleTimeString("ko-KR")}
          </p>
        </div>
      </div>

      {/* 변동량 표시 바 */}
      <div className="mt-4 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-300",
            isPositive
              ? "bg-red-500 dark:bg-red-400"
              : isNegative
              ? "bg-blue-500 dark:bg-blue-400"
              : "bg-gray-400 dark:bg-gray-500"
          )}
          style={{
            width: `${Math.min(Math.abs(realtimePrice.change_rate) * 10, 100)}%`,
          }}
        />
      </div>
    </div>
  );
}

/**
 * 실시간 가격 그리드 컴포넌트
 */
export function RealtimePriceGrid({
  stocks,
}: {
  stocks: Array<{ ticker: string; name: string }>;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {stocks.map((stock) => (
        <RealtimePriceCard
          key={stock.ticker}
          ticker={stock.ticker}
          name={stock.name}
        />
      ))}
    </div>
  );
}

/**
 * WebSocket 연결 상태 표시 컴포넌트
 */
export function WebSocketStatus() {
  const { connected, connecting, error, clientId } = useWebSocket({});

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "w-3 h-3 rounded-full",
          connected
            ? "bg-green-500 animate-pulse"
            : connecting
            ? "bg-yellow-500 animate-pulse"
            : error
            ? "bg-red-500"
            : "bg-gray-400"
        )}
      />
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {connected ? "실시간 연결됨" : connecting ? "연결 중..." : "연결 안됨"}
      </span>
      {clientId && (
        <span className="text-xs text-gray-500 dark:text-gray-500">
          (ID: {clientId.slice(0, 8)}...)
        </span>
      )}
    </div>
  );
}
