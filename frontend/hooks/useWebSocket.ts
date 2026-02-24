/**
 * WebSocket React Hook
 * 실시간 데이터 연동을 위한 커스텀 훅
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { Signal } from "@/types";
import type { IDaytradingSignal } from "@/types";
import {
  WebSocketClient,
  ConnectionState,
  WSMessage,
  PriceUpdateMessage,
  IndexUpdateMessage,
  MarketGateUpdateMessage,
  SignalUpdateMessage,
  createWebSocketClient,
  getWebSocketUrl,
} from "@/lib/websocket";
import { useToast } from "@/hooks/use-toast";

// 실시간 가격 데이터 상태
export interface RealtimePrice {
  ticker: string;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  timestamp: string;
}

// 실시간 지수 데이터 상태
export interface RealtimeIndex {
  code: string;  // 001: KOSPI, 201: KOSDAQ
  name: string;  // KOSPI, KOSDAQ
  index: number;
  change: number;
  change_rate: number;
  volume: number;
  timestamp: string;
}

// Market Gate 데이터 상태
export interface MarketGateData {
  status: "RED" | "YELLOW" | "GREEN";
  level: number;
  kospi: number | null;
  kospi_change_pct: number | null;
  kosdaq: number | null;
  kosdaq_change_pct: number | null;
  timestamp: string;
}

// 에러 타입 (QA 개선: 502 Bad Gateway 추가)
export type WebSocketErrorType =
  | "connection_refused"
  | "forbidden"
  | "bad_gateway"     // 502 에러
  | "service_unavailable" // 503 에러
  | "network"
  | "timeout"
  | "unknown";

// 에러 정보 (QA 개선: 상세한 사용자 메시지)
export interface WebSocketError {
  type: WebSocketErrorType;
  message: string;
  statusCode?: number; // HTTP 상태 코드 (502, 503 등)
  retryable: boolean;
  userMessage: string; // 사용자에게 표시할 메시지
  timestamp?: string;  // 에러 발생 시간
}

// Hook 옵션
export interface UseWebSocketOptions {
  autoConnect?: boolean; // 자동 연결 여부
  initialTopics?: string[]; // 초기 구독 토픽
  onPriceUpdate?: (price: RealtimePrice) => void; // 가격 업데이트 콜백
  onIndexUpdate?: (index: RealtimeIndex) => void; // 지수 업데이트 콜백
  onMarketGateUpdate?: (data: MarketGateData) => void; // Market Gate 업데이트 콜백
  onConnected?: (clientId: string) => void; // 연결 성공 콜백
  onDisconnected?: () => void; // 연결 종료 콜백
  onError?: (error?: WebSocketError) => void; // 에러 콜백
}

/**
 * WebSocket 커스텀 훅
 *
 * Usage:
 * ```tsx
 * const { connected, subscribe, unsubscribe } = useWebSocket({
 *   autoConnect: true,
 *   initialTopics: ["price:005930"],
 *   onPriceUpdate: (price) => console.log("Price update:", price),
 * });
 * ```
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    autoConnect = true,
    initialTopics = [],
    onPriceUpdate,
    onIndexUpdate,
    onMarketGateUpdate,
    onConnected,
    onDisconnected,
    onError,
  } = options;

  // WebSocket 클라이언트 ref (재렌더링 방지)
  const clientRef = useRef<WebSocketClient | null>(null);

  // 연결 상태
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");

  // 클라이언트 ID
  const [clientId, setClientId] = useState<string | null>(null);

  // Phase 4: 재연결 횟수와 마지막 에러 정보
  const [reconnectCount, setReconnectCount] = useState<number>(0);
  const [lastError, setLastError] = useState<WebSocketError | null>(null);
  const [maxReconnectReached, setMaxReconnectReached] = useState<boolean>(false);

  // 실시간 가격 데이터 (종목별)
  const [prices, setPrices] = useState<Map<string, RealtimePrice>>(new Map());

  // 실시간 지수 데이터 (KOSPI/KOSDAQ)
  const [indices, setIndices] = useState<Map<string, RealtimeIndex>>(new Map());

  // 컴포넌트 마운트 시 클라이언트 초기화
  useEffect(() => {
    // WebSocket URL (공통 유틸리티 사용)
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || getWebSocketUrl();

    // 디버깅용 URL 로깅 (개발 환경 전용)
    if (process.env.NODE_ENV === "development") {
      console.log("[useWebSocket] Getting client for:", wsUrl);
    }

    // 클라이언트 생성 (싱글톤)
    clientRef.current = createWebSocketClient(wsUrl);

    // 연결 상태 동기화 (이미 연결된 경우)
    if (clientRef.current.connectionState === "connected") {
      setConnectionState("connected");
    }

    // 메시지 수신 처리
    const unsubscribeMessage = clientRef.current.onMessage((message: WSMessage) => {
      // 가격 업데이트
      if (message.type === "price_update") {
        const priceMsg = message as PriceUpdateMessage;
        const realtimePrice: RealtimePrice = {
          ticker: priceMsg.ticker,
          price: priceMsg.data.price,
          change: priceMsg.data.change,
          change_rate: priceMsg.data.change_rate,
          volume: priceMsg.data.volume,
          timestamp: priceMsg.timestamp,
        };

        // 가격 데이터 업데이트
        setPrices((prev) => {
          const next = new Map(prev);
          next.set(priceMsg.ticker, realtimePrice);
          return next;
        });

        // 콜백 호출
        if (onPriceUpdate) {
          onPriceUpdate(realtimePrice);
        }
      }

      // 지수 업데이트
      if (message.type === "index_update") {
        const indexMsg = message as IndexUpdateMessage;
        const realtimeIndex: RealtimeIndex = {
          code: indexMsg.code,
          name: indexMsg.name,
          index: indexMsg.data.index,
          change: indexMsg.data.change,
          change_rate: indexMsg.data.change_rate,
          volume: indexMsg.data.volume,
          timestamp: indexMsg.timestamp,
        };

        // 지수 데이터 업데이트
        setIndices((prev) => {
          const next = new Map(prev);
          next.set(indexMsg.name.toLowerCase(), realtimeIndex);
          return next;
        });

        // 콜백 호출
        if (onIndexUpdate) {
          onIndexUpdate(realtimeIndex);
        }
      }

      // Market Gate 업데이트
      if (message.type === "market_gate_update") {
        const gateMsg = message as MarketGateUpdateMessage;
        const marketGateData: MarketGateData = {
          status: gateMsg.data.status,
          level: gateMsg.data.level,
          kospi: gateMsg.data.kospi,
          kospi_change_pct: gateMsg.data.kospi_change_pct,
          kosdaq: gateMsg.data.kosdaq,
          kosdaq_change_pct: gateMsg.data.kosdaq_change_pct,
          timestamp: gateMsg.timestamp,
        };

        // 커스텀 이벤트 디스패치 (다른 컴포넌트에서도 수신 가능)
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("market-gate-update", { detail: gateMsg.data }));
        }

        // 콜백 호출
        if (onMarketGateUpdate) {
          onMarketGateUpdate(marketGateData);
        }
      }

      // 연결 확인
      if (message.type === "connected") {
        setClientId(message.client_id || null);
        if (onConnected && message.client_id) {
          onConnected(message.client_id);
        }
      }
    });

    // 연결 상태 변경 처리
    const unsubscribeStateChange = clientRef.current.onStateChange((state: ConnectionState) => {
      setConnectionState(state);

      // Phase 4: 재연결 횟수 추적
      if (clientRef.current) {
        setReconnectCount(clientRef.current.reconnectCount);

        // 최대 재연결 시도 초과 확인
        if (clientRef.current.reconnectCount >= 10) {
          setMaxReconnectReached(true);
        }
      }

      // 콜백 호출
      if (state === "connected") {
        // 연결 성공 시 에러 초기화
        setLastError(null);
        setMaxReconnectReached(false);
        // 연결 성공은 connected 메시지에서 처리
      } else if (state === "disconnected") {
        setClientId(null);
        // 연결 종료 시 502/503 에러 판별 (재연결 시도 횟수로 유추)
        const isBadGateway = reconnectCount >= 3; // 3회 이상 실패는 서버 문제일 가능성 높음

        const errorObj: WebSocketError = {
          type: isBadGateway ? "bad_gateway" : "connection_refused",
          message: isBadGateway
            ? "WebSocket 502 Bad Gateway - 백엔드 서비스 응답 없음"
            : "WebSocket 연결이 종료되었습니다",
          statusCode: isBadGateway ? 502 : undefined,
          retryable: true,
          userMessage: isBadGateway
            ? "실시간 서비스에 연결할 수 없습니다. 백엔드 서비스 상태를 확인해주세요."
            : "실시간 연결이 끊어졌습니다. 재연결을 시도합니다.",
          timestamp: new Date().toISOString(),
        };
        setLastError(errorObj);
        if (onDisconnected) {
          onDisconnected();
        }
      } else if (state === "error") {
        // 에러 타입 결정 (502 Bad Gateway 우선 처리)
        const errorObj: WebSocketError = {
          type: reconnectCount >= 3 ? "bad_gateway" : "forbidden",
          message: reconnectCount >= 3
            ? "WebSocket 502 Bad Gateway - Nginx Proxy Manager 또는 백엔드 서비스 문제"
            : "WebSocket 연결 에러 - CORS 또는 권한 문제",
          statusCode: reconnectCount >= 3 ? 502 : undefined,
          retryable: reconnectCount >= 3, // 502는 재시도 의미 있음
          userMessage: reconnectCount >= 3
            ? "실시간 서비스에 연결할 수 없습니다 (502 Bad Gateway). 서버 상태를 확인해주세요."
            : "실시간 기능을 사용할 수 없습니다 (서버 설정 필요)",
          timestamp: new Date().toISOString(),
        };
        setLastError(errorObj);
        if (onError) {
          onError(errorObj);
        }
      } else if (state === "connecting") {
        // 연결 시도 중
        setLastError(null);
        setMaxReconnectReached(false);
      }
    });

    // 자동 연결 (이미 연결되어 있지 않은 경우만)
    if (autoConnect && clientRef.current.connectionState === "disconnected") {
      clientRef.current.connect(initialTopics);
    }

    // 클린업 (연결 끊지 않고 콜백만 정리)
    return () => {
      unsubscribeMessage();
      unsubscribeStateChange();
      // 싱글톤이므로 연결을 끊지 않음 (다른 컴포넌트 사용 중일 수 있음)
    };
  }, []); // 빈 의존성 배열: 마운트 시 한 번만 실행

  /**
   * 토픽 구독
   */
  const subscribe = useCallback((topic: string) => {
    if (clientRef.current) {
      clientRef.current.subscribe(topic);
    }
  }, []);

  /**
   * 토픽 구독 취소
   */
  const unsubscribe = useCallback((topic: string) => {
    if (clientRef.current) {
      clientRef.current.unsubscribe(topic);
    }
  }, []);

  /**
   * 핑 전송
   */
  const ping = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.ping();
    }
  }, []);

  /**
   * 수동 연결
   */
  const connect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.connect();
    }
  }, []);

  /**
   * 재연결 시도 (재연결 상태 리셋 후 연결)
   */
  const reconnect = useCallback(() => {
    if (clientRef.current) {
      // 재연결 상태 리셋
      clientRef.current.resetReconnectState();
      // 연결 시도
      clientRef.current.connect();
    }
  }, []);

  /**
   * 연결 종료
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }
  }, []);

  /**
   * 특정 종목의 실시간 가격 조회
   */
  const getPrice = useCallback(
    (ticker: string): RealtimePrice | undefined => {
      return prices.get(ticker);
    },
    [prices]
  );

  /**
   * 특정 지수의 실시간 데이터 조회
   */
  const getIndex = useCallback(
    (name: string): RealtimeIndex | undefined => {
      return indices.get(name.toLowerCase());
    },
    [indices]
  );

  // 연결 상태 플래그
  const connected = connectionState === "connected";
  const connecting = connectionState === "connecting";
  const disconnected = connectionState === "disconnected";
  const error = connectionState === "error";

  return {
    // 연결 상태
    connectionState,
    connected,
    connecting,
    disconnected,
    error,
    clientId,

    // Phase 4: 재연결 정보
    reconnectCount,
    lastError,
    maxReconnectReached,

    // 실시간 가격 데이터
    prices: Object.fromEntries(prices), // Map → Plain Object 변환
    getPrice,

    // 실시간 지수 데이터
    indices: Object.fromEntries(indices), // Map → Plain Object 변환
    getIndex,

    // 메서드
    subscribe,
    unsubscribe,
    ping,
    connect,
    disconnect,
    reconnect,
  };
}

/**
 * 실시간 가격 데이터만 사용하는 간단한 훅
 *
 * WebSocket 연결 실패 시 API 폴링으로 자동 전환됩니다.
 *
 * Usage:
 * ```tsx
 * const { prices, getPrice, connected, error, dataSource } = useRealtimePrices(["005930", "000660"]);
 * ```
 */
export function useRealtimePrices(tickers: string[]) {
  const [prices, setPrices] = useState<Map<string, RealtimePrice>>(new Map());
  const [usePolling, setUsePolling] = useState(false); // WebSocket 실패 시 폴링 사용
  const [loading, setLoading] = useState(false);

  const { connected, subscribe, unsubscribe, error, connecting, reconnect } = useWebSocket({
    autoConnect: true,
    onPriceUpdate: (price) => {
      setPrices((prev) => {
        const next = new Map(prev);
        next.set(price.ticker, price);
        return next;
      });
    },
  });

  // 가격 데이터 fetch 함수 (폴링용)
  const fetchPrices = useCallback(async (): Promise<void> => {
    if (tickers.length === 0) return;

    setLoading(true);
    try {
      const priceData = await apiClient.getRealtimePrices(tickers);

      setPrices((prev) => {
        const next = new Map(prev);
        // API 응답 데이터를 RealtimePrice 형식으로 변환
        Object.entries(priceData).forEach(([ticker, data]) => {
          next.set(ticker, {
            ticker,
            price: data.price,
            change: data.change,
            change_rate: data.change_percent,
            volume: data.volume,
            timestamp: data.timestamp || new Date().toISOString(),
          });
        });
        return next;
      });
    } catch (err) {
      if (process.env.NODE_ENV === "development") {
        console.error("[useRealtimePrices] Failed to fetch prices:", err);
      }
    } finally {
      setLoading(false);
    }
  }, [tickers]);

  // 종목들 자동 구독 (연결 상태 확인 후 구독)
  useEffect(() => {
    // 연결되지 않았으면 대기
    if (!connected) {
      if (process.env.NODE_ENV === "development") {
        console.log(`[useRealtimePrices] Waiting for connection...`);
      }
      return;
    }

    // 연결된 경우에만 구독
    tickers.forEach((ticker) => {
      if (process.env.NODE_ENV === "development") {
        console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
      }
      subscribe(`price:${ticker}`);
    });

    // WebSocket 연결 성공 시 폴링 중지
    setUsePolling(false);

    return () => {
      tickers.forEach((ticker) => {
        unsubscribe(`price:${ticker}`);
      });
    };
  }, [tickers.join(","), subscribe, unsubscribe, connected]);

  // 초기 데이터 로드
  useEffect(() => {
    if (prices.size === 0 && !connected) {
      fetchPrices();
    }
  }, [prices.size, connected, fetchPrices]);

  // WebSocket 연결 실패 시 주기적 API 폴링 폴백
  useEffect(() => {
    if (usePolling) {
      const interval = setInterval(() => {
        if (process.env.NODE_ENV === "development") {
          console.log("[useRealtimePrices] Polling API (WebSocket unavailable)");
        }
        fetchPrices();
      }, 15000); // 15초마다 폴링

      return () => clearInterval(interval);
    }
  }, [usePolling, fetchPrices]);

  // WebSocket 연결 실패 감지 시 폴링 모드 전환
  useEffect(() => {
    // 연결 시도 후 5초 동안 연결되지 않으면 폴링 모드 전환
    if (!connected && !connecting && prices.size === 0) {
      const timer = setTimeout(() => {
        if (!connected && !usePolling) {
          setUsePolling(true);
          if (process.env.NODE_ENV === "development") {
            console.log("[useRealtimePrices] WebSocket not available, switching to polling mode");
          }
        }
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [connected, connecting, prices.size, usePolling]);

  /**
   * 특정 종목의 실시간 가격 조회
   */
  const getPrice = useCallback(
    (ticker: string): RealtimePrice | undefined => {
      return prices.get(ticker);
    },
    [prices]
  );

  return {
    prices: Object.fromEntries(prices),
    getPrice,
    connected,
    error,
    connecting,
    loading,
    usePolling,
    reconnect,
    fetchPrices,
  };
}

/**
 * 실시간 지수 데이터만 사용하는 간단한 훅
 *
 * Usage:
 * ```tsx
 * const { indices, getIndex, kospi, kosdaq, connected } = useMarketIndices();
 * ```
 */
export function useMarketIndices() {
  const [indices, setIndices] = useState<Map<string, RealtimeIndex>>(new Map());

  const { connected, subscribe, unsubscribe, error, connecting } = useWebSocket({
    autoConnect: true,
    onIndexUpdate: (index) => {
      setIndices((prev) => {
        const next = new Map(prev);
        next.set(index.name.toLowerCase(), index);
        return next;
      });
    },
  });

  // KOSPI/KOSDAQ 자동 구독
  useEffect(() => {
    if (connected) {
      // market:kospi, market:kosdaq 토픽 구독
      subscribe("market:kospi");
      subscribe("market:kosdaq");
    }

    return () => {
      unsubscribe("market:kospi");
      unsubscribe("market:kosdaq");
    };
  }, [connected, subscribe, unsubscribe]);

  /**
   * 특정 지수의 실시간 데이터 조회
   */
  const getIndex = useCallback(
    (name: string): RealtimeIndex | undefined => {
      return indices.get(name.toLowerCase());
    },
    [indices]
  );

  // 편의 getter
  const kospi = getIndex("kospi");
  const kosdaq = getIndex("kosdaq");

  return {
    indices: Object.fromEntries(indices),
    getIndex,
    kospi,
    kosdaq,
    connected,
    error,
    connecting,
  };
}

/**
 * Market Gate 실시간 업데이트 Hook
 *
 * WebSocket을 통해 Market Gate 상태를 실시간으로 수신합니다.
 * WebSocket 연결 실패 시 API 폴링으로 폴백합니다.
 *
 * Usage:
 * ```tsx
 * const { marketGate, isRealtime, connected, loading, error, refetch } = useMarketGate();
 * ```
 */
export function useMarketGate() {
  const [marketGate, setMarketGate] = useState<MarketGateData | null>(null);
  const [isRealtime, setIsRealtime] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [usePolling, setUsePolling] = useState(false); // WebSocket 실패 시 폴링 사용

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
    onMarketGateUpdate: (data: MarketGateData) => {
      setMarketGate(data);
      setIsRealtime(true);
      setLastUpdate(new Date(data.timestamp));
      setError(null); // 데이터 수신 시 에러.clear
      if (process.env.NODE_ENV === "development") {
        console.log("[useMarketGate] Received update:", data);
      }
    },
  });

  // Market Gate 데이터 fetch 함수 (공통)
  const fetchMarketGate = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getMarketGate();

      // API 응답 데이터 변환 (undefined → null 변환)
      const data: MarketGateData = {
        status: response.status,
        level: response.level,
        kospi: response.kospi_close ?? null,
        kospi_change_pct: response.kospi_change_pct ?? null,
        kosdaq: response.kosdaq_close ?? null,
        kosdaq_change_pct: response.kosdaq_change_pct ?? null,
        timestamp: response.updated_at || new Date().toISOString(),
      };

      setMarketGate(data);
      setLastUpdate(new Date(data.timestamp));
      setError(null);
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);
      if (process.env.NODE_ENV === "development") {
        console.error("[useMarketGate] Failed to fetch data:", errorObj);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // market-gate 토픽 자동 구독
  useEffect(() => {
    if (connected) {
      subscribe("market-gate");
      setUsePolling(false); // WebSocket 연결 성공 시 폴링 중지
      if (process.env.NODE_ENV === "development") {
        console.log("[useMarketGate] Subscribed to market-gate topic");
      }
    }
  }, [connected, subscribe]);

  // 초기 데이터 로드
  useEffect(() => {
    if (!marketGate && !error) {
      fetchMarketGate();
    }
  }, [marketGate, error, fetchMarketGate]);

  // WebSocket 연결 실패 시 주기적 API 폴링 폴백
  useEffect(() => {
    if (usePolling) {
      const interval = setInterval(() => {
        if (process.env.NODE_ENV === "development") {
          console.log("[useMarketGate] Polling API (WebSocket unavailable)");
        }
        fetchMarketGate();
      }, 10000); // 10초마다 폴링

      return () => clearInterval(interval);
    }
  }, [usePolling, fetchMarketGate]);

  // WebSocket 연결 실패 감지 시 폴링 모드 전환
  useEffect(() => {
    // 연결 시도 후 5초 동안 연결되지 않으면 폴링 모드 전환
    if (!connected && !loading && !marketGate) {
      const timer = setTimeout(() => {
        if (!connected && !marketGate) {
          setUsePolling(true);
          if (process.env.NODE_ENV === "development") {
            console.log("[useMarketGate] WebSocket not available, switching to polling mode");
          }
        }
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [connected, loading, marketGate]);

  return {
    marketGate,
    isRealtime,
    connected,
    lastUpdate,
    loading,
    error,
    refetch: fetchMarketGate, // 수동 재시도 함수
  };
}

/**
 * VCP 시그널 실시간 구독 Hook
 *
 * WebSocket을 통해 VCP 시그널 업데이트를 실시간으로 수신합니다.
 * 백엔드에서 signal:vcp 토픽으로 브로드캐스트하는 시그널 데이터를
 * 수신하면 자동으로 store의 signals 상태를 업데이트합니다.
 *
 * Usage:
 * ```tsx
 * const { signals, connected, isRealtime, lastUpdate } = useSignals();
 * ```
 */
export function useSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [isRealtime, setIsRealtime] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
    // 다른 컴포넌트의 콜백과 충돌하지 않도록 내부적으로만 처리
    onPriceUpdate: undefined,
    onIndexUpdate: undefined,
    onMarketGateUpdate: undefined,
  });

  // WebSocket 메시지 리스너를 통해 시그널 업데이트 수신
  useEffect(() => {
    if (!connected) {
      return;
    }

    // 메시지 리스너 등록을 위해 WebSocket 클라이언트에 직접 접근
    const wsUrl = getWebSocketUrl();
    const client = createWebSocketClient(wsUrl);

    // 메시지 핸들러
    const unsubscribeMessage = client.onMessage((message: WSMessage) => {
      if (message.type === "signal_update") {
        const signalMsg = message as SignalUpdateMessage;
        // VCP 시그널인지 확인 (checks 필드가 없으면 VCP)
        const data = signalMsg.data as any;
        if (data.signals && data.signals.length > 0) {
          // VCP 시그널 (checks 필드가 없는 것으로 확인)
          const vcpSignals = data.signals as Signal[];
          if (process.env.NODE_ENV === "development") {
            console.log("[useSignals] Received signal update:", vcpSignals.length, "signals");
          }
          setSignals(vcpSignals);
          setIsRealtime(true);
          setLastUpdate(new Date(data.timestamp));
        }
      }
    });

    // signal:vcp 토픽 구독
    if (process.env.NODE_ENV === "development") {
      console.log("[useSignals] Subscribing to signal:vcp topic");
    }
    subscribe("signal:vcp");

    return () => {
      unsubscribeMessage();
    };
  }, [connected, subscribe]);

  // 초기 데이터 로드 (fallback)
  useEffect(() => {
    if (signals.length === 0 && !isRealtime) {
      // API에서 초기 데이터 로드
      apiClient.getSignals()
        .then((initialSignals) => {
          if (process.env.NODE_ENV === "development") {
            console.log("[useSignals] Loaded initial signals:", initialSignals.length);
          }
          setSignals(initialSignals);
        })
        .catch((error) => {
          console.error("[useSignals] Failed to load initial signals:", error);
        });
    }
  }, [signals.length, isRealtime]);

  return {
    signals,
    setSignals,
    isRealtime,
    connected,
    lastUpdate,
  };
}

/**
 * Daytrading 시그널 실시간 구독 Hook
 *
 * WebSocket을 통해 Daytrading 시그널 업데이트를 실시간으로 수신합니다.
 * 백엔드에서 signal:daytrading 토픽으로 브로드캐스트하는 시그널 데이터를
 * 수신하면 자동으로 store의 signals 상태를 업데이트합니다.
 *
 * Usage:
 * ```tsx
 * const { signals, connected, isRealtime, lastUpdate } = useDaytradingSignals();
 * ```
 */
export function useDaytradingSignals() {
  const [signals, setSignals] = useState<IDaytradingSignal[]>([]);
  const [isRealtime, setIsRealtime] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
    // 다른 컴포넌트의 콜백과 충돌하지 않도록 내부적으로만 처리
    onPriceUpdate: undefined,
    onIndexUpdate: undefined,
    onMarketGateUpdate: undefined,
  });

  // WebSocket 메시지 리스너를 통해 시그널 업데이트 수신
  useEffect(() => {
    if (!connected) {
      return;
    }

    // 메시지 리스너 등록을 위해 WebSocket 클라이언트에 직접 접근
    const wsUrl = getWebSocketUrl();
    const client = createWebSocketClient(wsUrl);

    // 메시지 핸들러
    const unsubscribeMessage = client.onMessage((message: WSMessage) => {
      if (message.type === "signal_update") {
        const signalMsg = message as SignalUpdateMessage;
        // daytrading_signals인지 확인 (데이터 구조로 구분)
        const data = signalMsg.data;
        // Daytrading 시그널인지 확인 (checks 필드 존재 여부)
        const firstSignal = data.signals?.[0];
        const isDaytradingSignal = firstSignal && "checks" in firstSignal && Array.isArray(firstSignal.checks);

        if (isDaytradingSignal) {
          // Daytrading 시그널 타입으로 캐스팅
          const daytradingSignals = data.signals as IDaytradingSignal[];
          if (process.env.NODE_ENV === "development") {
            console.log("[useDaytradingSignals] Received daytrading signal update:", daytradingSignals.length, "signals");
          }
          setSignals(daytradingSignals);
          setIsRealtime(true);
          setLastUpdate(new Date(data.timestamp));
        }
      }
    });

    // signal:daytrading 토픽 구독
    if (process.env.NODE_ENV === "development") {
      console.log("[useDaytradingSignals] Subscribing to signal:daytrading topic");
    }
    subscribe("signal:daytrading");

    return () => {
      unsubscribeMessage();
    };
  }, [connected, subscribe]);

  // 초기 데이터 로드 (fallback)
  useEffect(() => {
    if (signals.length === 0 && !isRealtime) {
      // API에서 초기 데이터 로드
      apiClient.getDaytradingSignals()
        .then((response) => {
          // API 응답 구조: {signals: [], count: number, generated_at: string}
          const signalsData = response.signals || [];
          if (process.env.NODE_ENV === "development") {
            console.log("[useDaytradingSignals] Loaded initial signals:", signalsData.length);
          }
          setSignals(signalsData);
        })
        .catch((error) => {
          console.error("[useDaytradingSignals] Failed to load initial signals:", error);
        });
    }
  }, [signals.length, isRealtime]);

  return {
    signals,
    setSignals,
    isRealtime,
    connected,
    lastUpdate,
  };
}
