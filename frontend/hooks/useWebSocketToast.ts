/**
 * WebSocket 연결 상태를 Toast 알림으로 표시하는 Hook
 *
 * 연결 실패, 재연결 시도, 연결 성공 등을 사용자에게 알립니다.
 */

import { useEffect, useRef } from "react";
import { useToast } from "./use-toast";

interface UseWebSocketToastOptions {
  connected: boolean;
  connecting: boolean;
  error: boolean;
  maxReconnectReached?: boolean;
  reconnectCount?: number;
  lastError?: {
    type: string;
    userMessage: string;
  } | null;
}

/**
 * WebSocket 연결 상태 변화를 Toast 알림으로 표시합니다.
 *
 * @param options - WebSocket 연결 상태
 */
export function useWebSocketToast({
  connected,
  connecting,
  error,
  maxReconnectReached = false,
  reconnectCount = 0,
  lastError,
}: UseWebSocketToastOptions) {
  const { toast } = useToast();

  console.log('[useWebSocketToast] Called with:', { connected, connecting, error });

  // 이전 상태 추적 (ref로 관리하여 재렌더링 방지)
  const prevConnectedRef = useRef(connected);
  const prevMaxReachedRef = useRef(maxReconnectReached);
  const toastShownRef = useRef(false);

  useEffect(() => {
    console.log('[useWebSocketToast] useEffect - State:', { connected, wasConnected: prevConnectedRef.current });

    // 연결 성공 (이전에 연결되지 않았다가 연결된 경우)
    if (connected && !prevConnectedRef.current) {
      console.log('[useWebSocketToast] Showing connected toast');
      toast({
        title: "실시간 연결 성공",
        description: "실시간 데이터 업데이트가 시작되었습니다.",
      });
    }

    // 최대 재연결 시도 도달 (한 번만 표시)
    if (maxReconnectReached && !prevMaxReachedRef.current && !toastShownRef.current) {
      console.log('[useWebSocketToast] Showing max reconnect toast');
      toast({
        title: "실시간 연결 실패",
        description: lastError?.userMessage || "서버 연결에 실패했습니다. 폴링 모드로 전환됩니다.",
        variant: "destructive",
      });
      toastShownRef.current = true;
    }

    // 상태 ref 업데이트
    prevConnectedRef.current = connected;
    prevMaxReachedRef.current = maxReconnectReached;
  }, [connected, maxReconnectReached, lastError, toast]);
}
