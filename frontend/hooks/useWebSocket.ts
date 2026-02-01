/**
 * WebSocket React Hook
 * 실시간 데이터 연동을 위한 커스텀 훅
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
  WebSocketClient,
  ConnectionState,
  WSMessage,
  PriceUpdateMessage,
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

// Hook 옵션
export interface UseWebSocketOptions {
  autoConnect?: boolean; // 자동 연결 여부
  initialTopics?: string[]; // 초기 구독 토픽
  onPriceUpdate?: (price: RealtimePrice) => void; // 가격 업데이트 콜백
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

  // 컴포넌트 마운트 시 클라이언트 초기화
  useEffect(() => {
    // WebSocket URL (환경 변수 또는 상대 경로)
    // HTTPS 접속 시 상대 경로 사용 (NPM 프록시 통해 /ws로 접근 → wss://)
    // HTTP 개발 접속 시 직접 연결 (ws://)
    const defaultUrl = typeof window !== "undefined"
      ? (() => {
          const protocol = window.location.protocol;
          const hostname = window.location.hostname;

          // HTTPS 접속: 상대 경로 사용 (브라우저가 wss:// 현재호스트/ws 사용)
          if (protocol === "https:") {
            return `${protocol.replace("http", "ws")}//${hostname}/ws`;
          }

          // HTTP 개발 접속: 직접 연결
          const isDirectAccess = hostname === "localhost" ||
                               hostname === "127.0.0.1" ||
                               /^\d+\.\d+\.\d+\.\d+$/.test(hostname);
          if (isDirectAccess) {
            return `ws://${hostname}:5111/ws`;
          }

          // 도메인 접속 (HTTP): 상대 경로
          return `ws://${hostname}/ws`;
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

  // 종목들 자동 구독
  useEffect(() => {
    if (connected) {
      tickers.forEach((ticker) => {
        subscribe(`price:${ticker}`);
      });
    }

    return () => {
      tickers.forEach((ticker) => {
        unsubscribe(`price:${ticker}`);
      });
    };
  }, [connected, tickers.join(","), subscribe, unsubscribe]);

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
