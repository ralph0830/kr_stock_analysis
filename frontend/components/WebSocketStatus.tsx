/**
 * WebSocket 연결 상태 컴포넌트
 *
 * 실시간 연결 상태를 사용자에게 명확하게 표시합니다.
 */

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Wifi, WifiOff, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface WebSocketStatusProps {
  connected: boolean;
  connecting: boolean;
  error: boolean;
  reconnectCount?: number;
  maxReconnectReached?: boolean;
  usePolling?: boolean;
  onReconnect?: () => void;
  className?: string;
  showLabel?: boolean;
}

/**
 * WebSocket 연결 상태 표시 컴포넌트
 *
 * @param connected - 연결 상태
 * @param connecting - 연결 중 상태
 * @param error - 에러 상태
 * @param reconnectCount - 재연결 시도 횟수
 * @param maxReconnectReached - 최대 재연결 도달 여부
 * @param usePolling - 폴링 모드 사용 여부
 * @param onReconnect - 재연결 핸들러
 * @param className - 추가 스타일 클래스
 * @param showLabel - 라벨 표시 여부
 */
export function WebSocketStatus({
  connected,
  connecting,
  error,
  reconnectCount = 0,
  maxReconnectReached = false,
  usePolling = false,
  onReconnect,
  className,
  showLabel = true,
}: WebSocketStatusProps) {
  // 연결 상태에 따른 표시
  const getStatusInfo = () => {
    if (connected) {
      return {
        icon: <Wifi className="h-4 w-4" />,
        text: "실시간 연결됨",
        variant: "default" as const,
        bgClass: "bg-green-500",
      };
    }
    if (connecting) {
      return {
        icon: <Loader2 className="h-4 w-4 animate-spin" />,
        text: reconnectCount > 0 ? `재연결 중... (${reconnectCount}/10)` : "연결 중...",
        variant: "secondary" as const,
        bgClass: "bg-yellow-500 animate-pulse",
      };
    }
    if (usePolling) {
      return {
        icon: <RefreshCw className="h-4 w-4 animate-spin" />,
        text: "폴링 모드 (15초)",
        variant: "outline" as const,
        bgClass: "bg-blue-500",
      };
    }
    if (maxReconnectReached || error) {
      return {
        icon: <WifiOff className="h-4 w-4" />,
        text: "연결 실패",
        variant: "destructive" as const,
        bgClass: "bg-red-500",
      };
    }
    return {
      icon: <WifiOff className="h-4 w-4" />,
      text: "연결 대기 중",
      variant: "outline" as const,
        bgClass: "bg-gray-500",
    };
  };

  const statusInfo = getStatusInfo();

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* 연결 상태 인디케이터 */}
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "w-2 h-2 rounded-full transition-colors",
            statusInfo.bgClass
          )}
        />
        {showLabel && (
          <span className="text-sm text-muted-foreground">{statusInfo.text}</span>
        )}
        {statusInfo.icon}
      </div>

      {/* 최대 재연결 도달 시 재연결 버튼 표시 */}
      {(maxReconnectReached || error) && onReconnect && (
        <Button
          size="sm"
          variant="outline"
          onClick={onReconnect}
          className="h-7 px-2 text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          재연결
        </Button>
      )}

      {/* 폴링 모드 표시 */}
      {usePolling && (
        <Badge variant="outline" className="text-xs">
          API 폴링
        </Badge>
      )}
    </div>
  );
}

/**
 * 간단한 연결 상태 아이콘만 표시하는 컴포넌트
 */
export function WebSocketStatusIcon({
  connected,
  connecting,
  className,
}: {
  connected: boolean;
  connecting?: boolean;
  className?: string;
}) {
  const bgClass = connected
    ? "bg-green-500"
    : connecting
    ? "bg-yellow-500 animate-pulse"
    : "bg-red-500";

  return (
    <div
      className={cn(
        "w-2 h-2 rounded-full transition-colors",
        bgClass,
        className
      )
      }
      title={connected ? "실시간 연결됨" : "연결 안됨"}
    />
  );
}
