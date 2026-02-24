/**
 * 실시간 가격 표시 카드 컴포넌트
 *
 * Phase 5 개선사항:
 * - 데이터 소스 표시 (WebSocket vs 폴링)
 * - 중복 API 요청 방지 (부모로부터만 데이터 전달받음)
 * - 순수 표시 컴포넌트 (직접 API 호출하지 않음)
 */
"use client";

import { useMemo } from "react";
import { useState, useEffect, useCallback } from "react";
import { RealtimePrice } from "@/hooks/useWebSocket";
import { formatPrice, formatPercent, formatNumber, cn } from "@/lib/utils";
import { apiClient } from "@/lib/api-client";
import type { StockPrice } from "@/types";
import { useWebSocket } from "@/hooks/useWebSocket";

interface RealtimePriceCardProps {
  ticker: string;
  name: string;
  // 부모로부터 받은 데이터 (필수)
  priceData: RealtimePrice | null | undefined;
  connected: boolean;
  connecting?: boolean;
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

/**
 * 실시간 가격 카드 (순수 표시 컴포넌트)
 *
 * props로만 데이터를 받으며, 직접 API를 호출하지 않습니다.
 */
export function RealtimePriceCard({
  ticker,
  name,
  priceData,
  connected,
  connecting = false,
}: RealtimePriceCardProps) {
  // 종목 분류
  const { category } = useMemo(() => getTickerCategory(ticker), [ticker]);

  // 데이터 소스 판정
  const dataSource: DataSourceType = connected && priceData ? "realtime" : priceData ? "polling" : "none";

  // 표시할 데이터
  const displayPrice = priceData;

  // 변동량 계산
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
          <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
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

  // 데이터 없음 상태
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
            {connecting ? "연결 중..." : "데이터 대기 중..."}
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
 * 실시간 가격 그리드 컴포넌트 (폴링 로직 포함)
 *
 * 상위 컴포넌트에서 데이터를 받아 자식에게 전달하며,
 * WebSocket 연결이 없을 때 폴링을 수행합니다.
 */

// 폴링 간격 상수 (ms)
const POLLING_INTERVAL = 15000;

interface RealtimePriceGridProps {
  stocks: Array<{ ticker: string; name: string }>;
  getPrice: (ticker: string) => RealtimePrice | undefined;
  connected: boolean;
  connecting?: boolean;
}

export function RealtimePriceGrid({
  stocks,
  getPrice,
  connected,
  connecting = false,
}: RealtimePriceGridProps) {
  // 폴링 데이터 상태 (props로 받은 데이터가 없을 때만 사용)
  const [pollingPrices, setPollingPrices] = useState<Map<string, RealtimePrice>>(new Map());
  const [isPolling, setIsPolling] = useState(false);

  // WebSocket 연결되면 폴링 데이터 초기화
  useEffect(() => {
    if (connected) {
      setPollingPrices(new Map());
    }
  }, [connected]);

  // 폴링: WebSocket 연결이 없을 때만 수행
  useEffect(() => {
    // WebSocket 연결되면 폴링 중지
    if (connected) {
      return;
    }

    const fetchAllPrices = async () => {
      setIsPolling(true);
      try {
        const tickers = stocks.map((s) => s.ticker);
        const prices = await apiClient.getRealtimePrices(tickers);

        // StockPrice를 RealtimePrice로 변환
        const mappedPrices = new Map<string, RealtimePrice>();
        for (const [ticker, price] of Object.entries(prices)) {
          const stockPrice = price as StockPrice;
          mappedPrices.set(ticker, {
            ticker: stockPrice.ticker,
            price: stockPrice.price,
            change: stockPrice.change,
            change_rate: stockPrice.change_percent,
            volume: stockPrice.volume,
            timestamp: stockPrice.timestamp || new Date().toISOString(),
          });
        }
        setPollingPrices(mappedPrices);
      } catch (e) {
        console.error("[RealtimePriceGrid] Polling failed:", e);
      } finally {
        setIsPolling(false);
      }
    };

    // 즉시 실행
    fetchAllPrices();

    // 15초마다 폴링
    const interval = setInterval(fetchAllPrices, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, [stocks, connected]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {stocks.map((stock) => {
        // WebSocket 데이터 우선, 없으면 폴링 데이터
        const priceData = getPrice(stock.ticker) || pollingPrices.get(stock.ticker);

        return (
          <RealtimePriceCard
            key={stock.ticker}
            ticker={stock.ticker}
            name={stock.name}
            priceData={priceData}
            connected={connected}
            connecting={connecting}
          />
        );
      })}
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
  const getErrorMessage = (): string | null => {
    if (lastError) {
      return typeof lastError === "string" ? lastError : lastError.userMessage;
    }
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
