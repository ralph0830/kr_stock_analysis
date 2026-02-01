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
 *
 * Phase 4: 연결 상태 UI 개선
 * - 연결 상태 아이콘: ● (연결됨), ◐ (연결 중), ⚠️ (에러)
 * - 재연결 횟수 표시
 * - 에러 메시지 툴팁
 * - 접근성 (aria-label)
 * - 부드러운 전환 애니메이션
 */
export function WebSocketStatus() {
  const { connected, connecting, error, clientId, reconnectCount, lastError, connectionState } = useWebSocket({});

  // Phase 4: 상태별 아이콘과 색상 매핑
  const getStatusConfig = () => {
    if (connected) {
      return {
        icon: "●",
        colorClass: "bg-green-500",
        text: "실시간 연결됨",
        ariaLabel: "WebSocket 연결됨",
      };
    }
    if (connecting) {
      return {
        icon: "◐",
        colorClass: "bg-yellow-500 animate-pulse",
        text: "연결 중...",
        ariaLabel: "WebSocket 연결 중",
      };
    }
    if (error) {
      return {
        icon: "⚠️",
        colorClass: "bg-red-500",
        text: "연결 실패",
        ariaLabel: "WebSocket 연결 오류",
      };
    }
    return {
      icon: "○",
      colorClass: "bg-gray-400",
      text: "대기 중",
      ariaLabel: "WebSocket 대기 중",
    };
  };

  const statusConfig = getStatusConfig();

  // Phase 4: 에러 메시지 생성 (툴팁용)
  const getErrorMessage = () => {
    if (lastError) return lastError;
    if (error) return "연결 오류가 발생했습니다";
    return null;
  };

  const errorMessage = getErrorMessage();
  const hasReconnect = reconnectCount > 0;

  return (
    <div
      className="flex items-center gap-2 transition-all duration-300"
      data-testid={`ws-status-${connectionState}`}
      aria-label={statusConfig.ariaLabel}
    >
      {/* Phase 4: 상태 아이콘 */}
      <span
        className={cn(
          "text-sm transition-all duration-300",
          error && "animate-pulse"
        )}
        data-testid={
          connected ? "ws-icon-connected" :
          connecting ? "ws-icon-connecting" :
          error ? "ws-icon-error" :
          "ws-icon-disconnected"
        }
      >
        {statusConfig.icon}
      </span>

      {/* 상태 텍스트 */}
      <span className="text-sm text-gray-600 dark:text-gray-400 transition-all duration-300">
        {statusConfig.text}
      </span>

      {/* Phase 4: 재연결 횟수 표시 */}
      {hasReconnect && (
        <span
          className="text-xs text-yellow-600 dark:text-yellow-400 font-medium transition-all duration-300"
          data-testid="ws-reconnect-count"
          title={`재연결 시도: ${reconnectCount}회`}
        >
          (재연결 {reconnectCount})
        </span>
      )}

      {/* Phase 4: 에러 메시지 툴팁 */}
      {errorMessage && (
        <span
          className="text-xs text-red-500 dark:text-red-400 cursor-help underline decoration-dotted"
          title={errorMessage}
          data-testid="ws-error-message"
        >
          {errorMessage.length > 20 ? errorMessage.substring(0, 20) + "..." : errorMessage}
        </span>
      )}

      {/* 클라이언트 ID (있는 경우만) */}
      {clientId && (
        <span className="text-xs text-gray-500 dark:text-gray-500 transition-all duration-300">
          (ID: {clientId.slice(0, 8)}...)
        </span>
      )}
    </div>
  );
}
