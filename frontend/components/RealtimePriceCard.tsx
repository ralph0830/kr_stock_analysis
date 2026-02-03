/**
 * 실시간 가격 표시 카드 컴포넌트
 *
 * Phase 5 개선사항:
 * - 데이터 소스 표시 (WebSocket vs 폴링)
 * - 폴링 Fallback 지원
 */
"use client";

import { useEffect, useState, useMemo } from "react";
import { useRealtimePrices, useWebSocket, RealtimePrice } from "@/hooks/useWebSocket";
import { formatPrice, formatPercent, formatNumber, cn } from "@/lib/utils";
import { apiClient } from "@/lib/api-client";

interface RealtimePriceCardProps {
  ticker: string;
  name: string;
}

// 데이터 소스 타입
type DataSourceType = "realtime" | "polling" | "none";

/**
 * 종목 코드 분류 (KOSPI/KOSDAQ/OTC)
 */
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "OTC" | "UNKNOWN";
  realtimeSupported: boolean;
} {
  // K-OTC: 10자리
  if (ticker.length === 10) {
    return { category: "OTC", realtimeSupported: false };
  }

  // KOSPI/KOSDAQ 구분 (0으로 시작하면 KOSPI)
  if (ticker.startsWith("0") || ticker.startsWith("00") || ticker.startsWith("000")) {
    return { category: "KOSPI", realtimeSupported: true };
  }

  return { category: "KOSDAQ", realtimeSupported: true };
}

/**
 * 타임스탬프 포맷 함수 (유효성 검증 포함)
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return "-";
    }
    return date.toLocaleTimeString("ko-KR");
  } catch {
    return "-";
  }
}

export function RealtimePriceCard({ ticker, name }: RealtimePriceCardProps) {
  const { prices, getPrice, connected, error, connecting } = useRealtimePrices([ticker]);
  const realtimePrice = getPrice(ticker);

  // 종목 분류
  const { category, realtimeSupported } = useMemo(() => getTickerCategory(ticker), [ticker]);

  // 폴링 데이터 상태
  const [pollingPrice, setPollingPrice] = useState<RealtimePrice | null>(null);
  const [dataSource, setDataSource] = useState<DataSourceType>("none");
  const [isPolling, setIsPolling] = useState(false);

  // WebSocket 데이터가 있으면 실시간으로 표시
  useEffect(() => {
    if (realtimePrice) {
      setDataSource("realtime");
    } else if (pollingPrice) {
      setDataSource("polling");
    } else {
      setDataSource("none");
    }
  }, [realtimePrice, pollingPrice]);

  // 폴링 Fallback: WebSocket 데이터가 없거나 연결되지 않은 경우 폴링 시도
  useEffect(() => {
    // WebSocket 연결되고 데이터가 있으면 폴링 스킵
    if (connected && realtimePrice) {
      return;
    }

    let mounted = true;
    setIsPolling(true);

    const fetchPollingPrice = async () => {
      try {
        const prices = await apiClient.getRealtimePrices([ticker]);
        if (mounted && prices[ticker]) {
          const priceData = prices[ticker];
          setPollingPrice({
            ticker: priceData.ticker,
            price: priceData.price,
            change: priceData.change,
            change_rate: priceData.change_percent,
            volume: priceData.volume,
            timestamp: priceData.timestamp || new Date().toISOString(),
          });
          setDataSource("polling");
        }
      } catch (e) {
        console.error(`[RealtimePriceCard] Polling failed for ${ticker}:`, e);
      } finally {
        if (mounted) {
          setIsPolling(false);
        }
      }
    };

    // 즉시 실행
    fetchPollingPrice();

    // 주기적 폴링 (15초 간격)
    const interval = setInterval(fetchPollingPrice, 15000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [ticker, connected, realtimePrice]);

  // 표시할 데이터 (WebSocket 우선, 폴링 Fallback)
  const displayPrice = realtimePrice || pollingPrice;

  // 변동량 계산 (displayPrice 기준)
  const isPositive = (displayPrice?.change ?? 0) > 0;
  const isNegative = (displayPrice?.change ?? 0) < 0;
  const DataSourceBadge = () => {
    if (dataSource === "realtime" && connected) {
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
          <span className={cn("w-2 h-2 rounded-full", isPolling ? "bg-yellow-500 animate-pulse" : "bg-yellow-500")}></span>
          폴링 {category}
        </span>
      );
    }

    // 연결 중 상태
    if (connecting) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
          연결 중
        </span>
      );
    }

    // 대기 중
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
        <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
        대기 중
      </span>
    );
  };

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
  if (!displayPrice) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
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
        <div className="text-center py-4">
          <p className="text-gray-500 dark:text-gray-400">
            {isPolling ? "폴링 중..." : connecting ? "연결 중..." : "데이터 대기 중..."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg transition-all hover:shadow-xl">
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
                isPositive
                  ? "text-red-600 dark:text-red-400"
                  : isNegative
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-600 dark:text-gray-400"
              )}
            >
              {isPositive ? "+" : ""}
              {formatPrice(displayPrice.change)}
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
              {formatPercent(displayPrice.change_rate)})
            </span>
          </div>
        </div>
      </div>

      {/* 추가 정보 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400 mb-1">거래량</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {formatNumber(displayPrice.volume)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400 mb-1">업데이트</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {formatTimestamp(displayPrice.timestamp)}
          </p>
        </div>
      </div>

      {/* 폴링 데이터 소스 안내 */}
      {dataSource === "polling" && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            현재 실시간 연결이 없습니다. 15초마다 업데이트됩니다.
          </p>
        </div>
      )}

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
            width: `${Math.min(Math.abs(displayPrice.change_rate) * 10, 100)}%`,
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
