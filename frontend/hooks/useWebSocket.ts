/**
 * WebSocket React Hook
 * 실시간 데이터 연동을 위한 커스텀 훅
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { Signal } from "@/types";
import {
  WebSocketClient,
  ConnectionState,
  WSMessage,
  PriceUpdateMessage,
  IndexUpdateMessage,
  MarketGateUpdateMessage,
  SignalUpdateMessage,
  createWebSocketClient,
} from "@/lib/websocket";

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

// Hook 옵션
export interface UseWebSocketOptions {
  autoConnect?: boolean; // 자동 연결 여부
  initialTopics?: string[]; // 초기 구독 토픽
  onPriceUpdate?: (price: RealtimePrice) => void; // 가격 업데이트 콜백
  onIndexUpdate?: (index: RealtimeIndex) => void; // 지수 업데이트 콜백
  onMarketGateUpdate?: (data: MarketGateData) => void; // Market Gate 업데이트 콜백
  onConnected?: (clientId: string) => void; // 연결 성공 콜백
  onDisconnected?: () => void; // 연결 종료 콜백
  onError?: (error?: string) => void; // 에러 콜백 (Phase 4: error message 추가)
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

  // Phase 4: 재연결 횟수와 마지막 에러 메시지
  const [reconnectCount, setReconnectCount] = useState<number>(0);
  const [lastError, setLastError] = useState<string | null>(null);

  // 실시간 가격 데이터 (종목별)
  const [prices, setPrices] = useState<Map<string, RealtimePrice>>(new Map());

  // 실시간 지수 데이터 (KOSPI/KOSDAQ)
  const [indices, setIndices] = useState<Map<string, RealtimeIndex>>(new Map());

  // 컴포넌트 마운트 시 클라이언트 초기화
  useEffect(() => {
    // WebSocket URL (환경 변수 또는 현재 도메인 기반)
    const defaultUrl = typeof window !== "undefined"
      ? (() => {
          const protocol = window.location.protocol;
          const hostname = window.location.hostname;

          // 로컬 개발 환경: 포트 5111 직접 연결
          const isLocal = hostname === "localhost" || hostname === "127.0.0.1";

          // HTTP → ws, HTTPS → wss
          const wsProtocol = protocol.replace("http", "ws");

          if (isLocal) {
            // 로컬 개발: ws://localhost:5111/ws
            return `${wsProtocol}//${hostname}:5111/ws`;
          }

          // 외부 도메인 (예: stock.ralphpark.com, ralphpark.com)
          // NPM 리버스 프록시 경로 사용: /ws → 5111 포트로 포워딩
          // SSL 종료는 NPM에서 처리되므로 포트 번호 불필요
          return `${wsProtocol}//${hostname}/ws`;
        })()
      : "ws://localhost:5111/ws";
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultUrl;

    // 디버깅용 URL 로깅
    console.log("[useWebSocket] Getting client for:", wsUrl);

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
      }

      // 콜백 호출
      if (state === "connected") {
        // 연결 성공 시 에러 초기화
        setLastError(null);
        // 연결 성공은 connected 메시지에서 처리
      } else if (state === "disconnected") {
        setClientId(null);
        setLastError("연결이 종료되었습니다");
        if (onDisconnected) {
          onDisconnected();
        }
      } else if (state === "error") {
        setLastError("연결 오류가 발생했습니다");
        if (onError) {
          onError("연결 오류");
        }
      } else if (state === "connecting") {
        // 연결 시도 중
        setLastError(null);
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
  };
}

/**
 * 실시간 가격 데이터만 사용하는 간단한 훅
 *
 * Usage:
 * ```tsx
 * const { prices, getPrice, connected, error } = useRealtimePrices(["005930", "000660"]);
 * ```
 */
export function useRealtimePrices(tickers: string[]) {
  const [prices, setPrices] = useState<Map<string, RealtimePrice>>(new Map());

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

  // 종목들 자동 구독 (연결 상태 확인 후 구독)
  useEffect(() => {
    // 연결되지 않았으면 대기
    if (!connected) {
      console.log(`[useRealtimePrices] Waiting for connection...`);
      return;
    }

    // 연결된 경우에만 구독
    tickers.forEach((ticker) => {
      console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
      subscribe(`price:${ticker}`);
    });

    return () => {
      tickers.forEach((ticker) => {
        unsubscribe(`price:${ticker}`);
      });
    };
  }, [tickers.join(","), subscribe, unsubscribe, connected]);

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
 *
 * Usage:
 * ```tsx
 * const { marketGate, isRealtime, connected, error } = useMarketGate();
 * ```
 */
export function useMarketGate() {
  const [marketGate, setMarketGate] = useState<MarketGateData | null>(null);
  const [isRealtime, setIsRealtime] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const { connected, subscribe } = useWebSocket({
    autoConnect: true,
    onMarketGateUpdate: (data: MarketGateData) => {
      setMarketGate(data);
      setIsRealtime(true);
      setLastUpdate(new Date(data.timestamp));
      console.log("[useMarketGate] Received update:", data);
    },
  });

  // market-gate 토픽 자동 구독
  useEffect(() => {
    if (connected) {
      subscribe("market-gate");
      console.log("[useMarketGate] Subscribed to market-gate topic");
    }

    return () => {
      // NOTE: 구독 취소는 연결 종료 시 자동으로 처리됨
    };
  }, [connected, subscribe]);

  // 초기 데이터 로드 (fallback)
  useEffect(() => {
    if (!marketGate) {
      // API에서 초기 데이터 로드
      fetch("/api/kr/market-gate")
        .then((res) => res.json())
        .then((data) => {
          setMarketGate({
            status: data.status,
            level: data.level,
            kospi: data.kospi_close,
            kospi_change_pct: data.kospi_change_pct,
            kosdaq: data.kosdaq_close,
            kosdaq_change_pct: data.kosdaq_change_pct,
            timestamp: data.updated_at,
          });
          if (data.updated_at) {
            setLastUpdate(new Date(data.updated_at));
          }
        })
        .catch((error) => {
          console.error("[useMarketGate] Failed to load initial data:", error);
        });
    }
  }, [marketGate]);

  return {
    marketGate,
    isRealtime,
    connected,
    lastUpdate,
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
    const wsUrl = typeof window !== "undefined"
      ? (() => {
          const protocol = window.location.protocol;
          const hostname = window.location.hostname;
          const isLocal = hostname === "localhost" || hostname === "127.0.0.1";
          const wsProtocol = protocol.replace("http", "ws");
          return isLocal
            ? `${wsProtocol}//${hostname}:5111/ws`
            : `${wsProtocol}//${hostname}/ws`;
        })()
      : "ws://localhost:5111/ws";

    const client = createWebSocketClient(wsUrl);

    // 메시지 핸들러
    const unsubscribeMessage = client.onMessage((message: WSMessage) => {
      if (message.type === "signal_update") {
        const signalMsg = message as SignalUpdateMessage;
        console.log("[useSignals] Received signal update:", signalMsg.data.count, "signals");
        setSignals(signalMsg.data.signals);
        setIsRealtime(true);
        setLastUpdate(new Date(signalMsg.data.timestamp));
      }
    });

    // signal:vcp 토픽 구독
    console.log("[useSignals] Subscribing to signal:vcp topic");
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
          console.log("[useSignals] Loaded initial signals:", initialSignals.length);
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
