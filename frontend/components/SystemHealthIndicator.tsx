/**
 * 시스템 상태 모니터링 컴포넌트
 * 데이터베이스, Redis, Celery, 외부 서비스 상태 표시
 */
"use client"

import { useEffect } from "react"
import { useSystemStore } from "@/store/systemStore"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Database,
  Server,
  Clock,
} from "lucide-react"
import { formatDistanceToNow } from "@/lib/utils"

export function SystemHealthIndicator() {
  const {
    systemHealth,
    dataStatus,
    loading,
    startPolling,
    stopPolling,
  } = useSystemStore()

  // 컴포넌트 마운트 시 폴링 시작
  useEffect(() => {
    startPolling(30000) // 30초 간격

    // 언마운트 시 폴링 정지
    return () => stopPolling()
  }, [startPolling, stopPolling])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
      case "up":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
      case "degraded":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
      case "unhealthy":
      case "down":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
      case "up":
      case "OK":
        return <CheckCircle className="w-4 h-4" />
      case "degraded":
        return <AlertTriangle className="w-4 h-4" />
      case "unhealthy":
      case "down":
      case "ERROR":
        return <XCircle className="w-4 h-4" />
      case "STALE":
        return <Clock className="w-4 h-4" />
      default:
        return <Activity className="w-4 h-4" />
    }
  }

  // 전체 상태 배지
  const getOverallStatus = () => {
    if (!systemHealth) return "unknown"
    return systemHealth.status
  }

  const getOverallColor = () => {
    const status = getOverallStatus()
    return getStatusColor(status)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity className="w-4 h-4" />
          시스템 상태
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => useSystemStore.getState().refreshAll()}
          className="h-7"
          disabled={loading}
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 전체 상태 */}
        <div className="flex items-center justify-between p-2 rounded-lg bg-gray-50 dark:bg-gray-800">
          <span className="text-sm font-medium">전체 상태</span>
          <Badge className={getOverallColor()}>
            {systemHealth?.status === "healthy" && "정상"}
            {systemHealth?.status === "degraded" && "경고"}
            {systemHealth?.status === "unhealthy" && "비정상"}
            {!systemHealth && "알 수 없음"}
          </Badge>
        </div>

        {/* 서비스 상태 */}
        {systemHealth && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">서비스 상태</p>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(systemHealth.services).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center justify-between p-2 rounded bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center gap-1">
                    <Server className="w-3 h-3 text-gray-400" />
                    <span className="text-xs truncate">{name}</span>
                  </div>
                  <Badge variant="outline" className={`text-xs ${getStatusColor(status)}`}>
                    {status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 데이터 파일 상태 */}
        {dataStatus && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">데이터 상태</p>
            <div className="space-y-1">
              {Object.entries(dataStatus.data_files).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center justify-between text-xs p-2 rounded bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                >
                  <span className="truncate">{name}</span>
                  <div className="flex items-center gap-1">
                    {getStatusIcon(status)}
                    <span className={getStatusColor(status)}>{status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Uptime */}
        {systemHealth?.uptime_seconds && (
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>가동 시간</span>
            <span>
              {formatDistanceToNow(new Date(Date.now() - systemHealth.uptime_seconds * 1000))}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
