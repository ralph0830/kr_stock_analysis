/**
 * 차트 페이지용 실시간 가격 표시 컴포넌트
 *
 * 기능:
 * - 실시간 가격 표시 (WebSocket 우선, 폴링 폴백)
 * - 가격 변동 시 색상 애니메이션 (빨강 ↔ 파랑)
 * - WebSocket 연결 상태 인디케이터
 * - 반응형 레이아웃 (모바일/태블릿/데스크톱)
 *
 * @author Frontend Architect
 * @date 2026-02-07
 */
"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useWebSocket, RealtimePrice } from "@/hooks/useWebSocket";
import { formatPrice, formatPercent, formatNumber, cn } from "@/lib/utils";

/**
 * 종목 정보 인터페이스
 */
export interface IStockInfo {
  ticker: string;
  name: string;
}

/**
 * 컴포넌트 Props 인터페이스
 */
export interface IChartRealtimePriceProps {
  /** 표시할 종목 목록 */
  stocks: IStockInfo[];
  /** 현재 선택된 종목 티커 */
  selectedTicker?: string;
  /** 선택된 종목 변경 콜백 */
  onStockSelect?: (ticker: string) => void;
  /** 컴팩트 모드 (미니 차트 그리드용) */
  compact?: boolean;
}

/**
 * 애니메이션 상태 타입
 */
type AnimationState = "up" | "down" | "neutral";

/**
 * 가격 방향 (상승/하락/보합)
 */
type PriceDirection = "up" | "down" | "neutral";

/**
 * 개별 종목 실시간 가격 컴포넌트
 */
interface StockPriceItemProps {
  stock: IStockInfo;
  priceData: RealtimePrice | undefined;
  connected: boolean;
  isSelected: boolean;
  onSelect: () => void;
  compact: boolean;
}

function StockPriceItem({
  stock,
  priceData,
  connected,
  isSelected,
  onSelect,
  compact,
}: StockPriceItemProps) {
  // 애니메이션 상태
  const [animationState, setAnimationState] = useState<AnimationState>("neutral");

  // 이전 가격 저장 (변동 감지용)
  const prevPriceRef = useState<number | null>(null);

  // 가격 변동 감지 및 애니메이션 트리거
  useEffect(() => {
    if (priceData && prevPriceRef[0] !== null) {
      if (priceData.price > prevPriceRef[0]) {
        setAnimationState("up");
      } else if (priceData.price < prevPriceRef[0]) {
        setAnimationState("down");
      }
    }
    prevPriceRef[1](priceData?.price ?? null);

    // 애니메이션 초기화 (1.5초 후)
    const timer = setTimeout(() => {
      setAnimationState("neutral");
    }, 1500);

    return () => clearTimeout(timer);
  }, [priceData?.price]);

  // 가격 방향 계산
  const direction: PriceDirection = useMemo(() => {
    if (!priceData || priceData.change === 0) return "neutral";
    return priceData.change > 0 ? "up" : "down";
  }, [priceData]);

  // 색상 클래스 계산
  const colorClass = useMemo(() => {
    switch (direction) {
      case "up":
        return "text-red-600 dark:text-red-400";
      case "down":
        return "text-blue-600 dark:text-blue-400";
      default:
        return "text-gray-600 dark:text-gray-400";
    }
  }, [direction]);

  // 배경색 클래스 (애니메이션 포함)
  const bgClass = useMemo(() => {
    const baseClass = isSelected
      ? "bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700"
      : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700";

    const animationClass =
      animationState === "up"
        ? "bg-red-50 dark:bg-red-900/20"
        : animationState === "down"
        ? "bg-blue-50 dark:bg-blue-900/20"
        : "";

    return cn(baseClass, animationClass, "transition-colors duration-300");
  }, [isSelected, animationState]);

  // 데이터 소스 뱃지
  const DataSourceBadge = () => {
    if (connected && priceData) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" aria-hidden="true" />
          실시간
        </span>
      );
    }
    return null;
  };

  // 데이터 없음 상태
  if (!priceData) {
    return (
      <button
        onClick={onSelect}
        className={cn(
          "w-full p-3 rounded-lg border text-left transition-all hover:shadow-md",
          bgClass
        )}
        disabled
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">{stock.name}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{stock.ticker}</p>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">대기 중</span>
        </div>
      </button>
    );
  }

  // 컴팩트 모드 (미니 차트 그리드용)
  if (compact) {
    return (
      <button
        onClick={onSelect}
        className={cn(
          "w-full p-3 rounded-lg border text-left transition-all hover:shadow-md",
          bgClass
        )}
        aria-label={`${stock.name} (${stock.ticker}) 현재가 ${formatPrice(priceData.price)}`}
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {stock.name}
          </span>
          <DataSourceBadge />
        </div>
        <div className="flex items-baseline gap-2">
          <span className={cn("text-lg font-bold", colorClass)}>
            {formatPrice(priceData.price)}
          </span>
          <span className={cn("text-xs font-medium", colorClass)}>
            {direction === "up" && "+"}
            {formatPercent(priceData.change_rate)}
          </span>
        </div>
      </button>
    );
  }

  // 표준 모드
  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full p-4 rounded-lg border text-left transition-all hover:shadow-lg",
        bgClass
      )}
      aria-label={`${stock.name} (${stock.ticker}) 현재가 ${formatPrice(priceData.price)}, 전일대비 ${priceData.change > 0 ? "+" : ""}${formatPrice(priceData.change)}`}
    >
      {/* 종목 정보 헤더 */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {stock.name}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">{stock.ticker}</p>
        </div>
        <DataSourceBadge />
      </div>

      {/* 가격 정보 */}
      <div className="flex items-baseline gap-3 mb-2">
        <span className={cn("text-2xl font-bold", colorClass)}>
          {formatPrice(priceData.price)}
        </span>
        <div className="flex items-center gap-2">
          <span className={cn("text-sm font-medium", colorClass)}>
            {direction === "up" && "+"}
            {formatPrice(priceData.change)}
          </span>
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded font-medium",
              direction === "up"
                ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                : direction === "down"
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
            )}
          >
            {direction === "up" && "+"}
            {formatPercent(priceData.change_rate)}
          </span>
        </div>
      </div>

      {/* 추가 정보 (거래량) */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>거래량: {formatNumber(priceData.volume)}주</span>
        <span className="text-xs">
          {new Date(priceData.timestamp).toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </span>
      </div>

      {/* 변동량 표시 바 */}
      <div className="mt-3 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-500 ease-out",
            direction === "up"
              ? "bg-red-500 dark:bg-red-400"
              : direction === "down"
              ? "bg-blue-500 dark:bg-blue-400"
              : "bg-gray-400 dark:bg-gray-500"
          )}
          style={{
            width: `${Math.min(Math.abs(priceData.change_rate) * 10, 100)}%`,
          }}
          aria-hidden="true"
        />
      </div>
    </button>
  );
}

/**
 * 차트 페이지용 실시간 가격 그리드 컴포넌트
 *
 * @example
 * ```tsx
 * <ChartRealtimePrice
 *   stocks={[
 *     { ticker: "005930", name: "삼성전자" },
 *     { ticker: "000020", name: "동서" },
 *   ]}
 *   selectedTicker="005930"
 *   onStockSelect={(ticker) => setSelectedTicker(ticker)}
 *   compact={false}
 * />
 * ```
 */
export function ChartRealtimePrice({
  stocks,
  selectedTicker,
  onStockSelect,
  compact = false,
}: IChartRealtimePriceProps) {
  const { getPrice, connected, connecting, subscribe, unsubscribe, clientId } = useWebSocket({
    autoConnect: true,
  });

  // WebSocket 토픽 구독 (stocks 배열 변경 시 자동 구독/해제)
  useEffect(() => {
    // 연결되지 않았거나 clientId가 없으면 대기
    if (!connected || !clientId) {
      if (process.env.NODE_ENV === "development") {
        console.log("[ChartRealtimePrice] Waiting for WebSocket connection...", { connected, clientId });
      }
      return;
    }

    // 연결 안정화를 위해 약간의 딜레이 후 구독
    const subscriptionTimer = setTimeout(() => {
      // 모든 종목 토픽 구독
      const topics = stocks.map((stock) => `price:${stock.ticker}`);
      topics.forEach((topic) => {
        if (process.env.NODE_ENV === "development") {
          console.log(`[ChartRealtimePrice] Subscribing to ${topic} (clientId: ${clientId})`);
        }
        subscribe(topic);
      });
    }, 500); // 500ms 딜레이로 연결 안정화 대기

    // cleanup: 타이머 및 구독 해제
    return () => {
      clearTimeout(subscriptionTimer);
      const topics = stocks.map((stock) => `price:${stock.ticker}`);
      topics.forEach((topic) => {
        if (process.env.NODE_ENV === "development") {
          console.log(`[ChartRealtimePrice] Unsubscribing from ${topic}`);
        }
        unsubscribe(topic);
      });
    };
  }, [stocks.map((s) => s.ticker).join(","), connected, clientId, subscribe, unsubscribe]);

  // WebSocket 연결 상태 표시
  const ConnectionStatus = () => {
    if (connecting) {
      return (
        <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" aria-hidden="true" />
          <span>연결 중...</span>
        </div>
      );
    }
    if (connected) {
      return (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" aria-hidden="true" />
          <span>실시간 연결됨</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <span className="w-2 h-2 bg-gray-400 rounded-full" aria-hidden="true" />
        <span>폴링 모드</span>
      </div>
    );
  };

  // 그리드 레이아웃 (반응형)
  const gridClass = cn(
    "grid gap-3",
    compact
      ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
      : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
  );

  return (
    <section
      className="space-y-4"
      aria-label="실시간 주식 가격"
    >
      {/* 연결 상태 헤더 */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          실시간 가격
        </h2>
        <ConnectionStatus />
      </div>

      {/* 가격 그리드 */}
      <div className={gridClass} role="list">
        {stocks.map((stock) => (
          <StockPriceItem
            key={stock.ticker}
            stock={stock}
            priceData={getPrice(stock.ticker)}
            connected={connected}
            isSelected={stock.ticker === selectedTicker}
            onSelect={() => onStockSelect?.(stock.ticker)}
            compact={compact}
          />
        ))}
      </div>

      {/* 접근성 안내 (스크린 리더용) */}
      <p className="sr-only">
        실시간 주식 가격 정보입니다. 현재 {connected ? "WebSocket 실시간 연결" : "폴링"} 상태입니다.
        가격 업데이트 시 색상이 변화하여 시각적으로 표시됩니다.
      </p>
    </section>
  );
}

/**
 * 단일 종목 실시간 가격 헤더 컴포넌트
 * (차트 상단에 크게 표시하는 용도)
 */
export interface IChartRealtimePriceHeaderProps {
  ticker: string;
  name: string;
}

export function ChartRealtimePriceHeader({
  ticker,
  name,
}: IChartRealtimePriceHeaderProps) {
  const { getPrice, connected, connecting, subscribe, unsubscribe, clientId } = useWebSocket({
    autoConnect: true,
  });

  // 단일 종목 토픽 구독
  useEffect(() => {
    // 연결되지 않았거나 clientId가 없으면 대기
    if (!connected || !clientId) {
      if (process.env.NODE_ENV === "development") {
        console.log("[ChartRealtimePriceHeader] Waiting for WebSocket connection...", { connected, clientId });
      }
      return;
    }

    // 연결 안정화를 위해 약간의 딜레이 후 구독
    const subscriptionTimer = setTimeout(() => {
      const topic = `price:${ticker}`;
      if (process.env.NODE_ENV === "development") {
        console.log(`[ChartRealtimePriceHeader] Subscribing to ${topic} (clientId: ${clientId})`);
      }
      subscribe(topic);
    }, 500);

    return () => {
      clearTimeout(subscriptionTimer);
      const topic = `price:${ticker}`;
      if (process.env.NODE_ENV === "development") {
        console.log(`[ChartRealtimePriceHeader] Unsubscribing from ${topic}`);
      }
      unsubscribe(topic);
    };
  }, [ticker, connected, clientId, subscribe, unsubscribe]);

  const priceData = getPrice(ticker);

  // 애니메이션 상태
  const [animationState, setAnimationState] = useState<AnimationState>("neutral");

  // 가격 변동 감지
  useEffect(() => {
    if (priceData) {
      if (priceData.change > 0) {
        setAnimationState("up");
      } else if (priceData.change < 0) {
        setAnimationState("down");
      } else {
        setAnimationState("neutral");
      }

      // 애니메이션 초기화
      const timer = setTimeout(() => {
        setAnimationState("neutral");
      }, 1500);

      return () => clearTimeout(timer);
    }
  }, [priceData?.price, priceData?.change]);

  // 색상 계산
  const direction: PriceDirection = priceData && priceData.change > 0 ? "up" : priceData && priceData.change < 0 ? "down" : "neutral";

  const colorClass = {
    up: "text-red-600 dark:text-red-400",
    down: "text-blue-600 dark:text-blue-400",
    neutral: "text-gray-900 dark:text-gray-100",
  }[direction];

  const bgAnimationClass = {
    up: "bg-red-50 dark:bg-red-900/10",
    down: "bg-blue-50 dark:bg-blue-900/10",
    neutral: "",
  }[animationState];

  return (
    <header
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md transition-colors duration-300",
        bgAnimationClass
      )}
    >
      {/* 종목 정보 + 연결 상태 */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            {name}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{ticker}</p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" aria-hidden="true" />
              실시간
            </span>
          ) : connecting ? (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" aria-hidden="true" />
              연결 중
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
              <span className="w-2 h-2 bg-gray-400 rounded-full" aria-hidden="true" />
              폴링
            </span>
          )}
        </div>
      </div>

      {/* 가격 정보 (대형 표시) */}
      {priceData ? (
        <>
          <div className="flex items-baseline gap-4 mb-4">
            <span className={cn("text-4xl font-bold", colorClass)}>
              {formatPrice(priceData.price)}
            </span>
            <div className="flex items-center gap-3">
              <span className={cn("text-xl font-semibold", colorClass)}>
                {direction === "up" && "+"}
                {formatPrice(priceData.change)}
              </span>
              <span
                className={cn(
                  "text-lg px-3 py-1 rounded-lg font-medium",
                  direction === "up"
                    ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                    : direction === "down"
                    ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                )}
              >
                {direction === "up" && "+"}
                {formatPercent(priceData.change_rate)}
              </span>
            </div>
          </div>

          {/* 추가 정보 */}
          <div className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400">
            <div>
              <span className="mr-2">거래량:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {formatNumber(priceData.volume)}주
              </span>
            </div>
            <div>
              <span className="mr-2">업데이트:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {new Date(priceData.timestamp).toLocaleTimeString("ko-KR", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            </div>
          </div>
        </>
      ) : (
        <div className="py-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            {connecting ? "실시간 데이터를 불러오는 중..." : "데이터를 가져올 수 없습니다."}
          </p>
        </div>
      )}
    </header>
  );
}

export default ChartRealtimePrice;
