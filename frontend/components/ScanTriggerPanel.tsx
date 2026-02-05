/**
 * 스캔 트리거 패널 컴포넌트
 * VCP 스캔 및 시그널 생성을 트리거하고 상태를 표시
 */
"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api-client"
import type { IVCPScanResponse, ISignalGenerationResponse, IScanStatus } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Activity,
  Play,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  Radar,
  TrendingUp,
} from "lucide-react"

export function ScanTriggerPanel() {
  const [scanStatus, setScanStatus] = useState<IScanStatus | null>(null)
  const [vcpResult, setVcpResult] = useState<IVCPScanResponse | null>(null)
  const [signalResult, setSignalResult] = useState<ISignalGenerationResponse | null>(null)
  const [vcpLoading, setVcpLoading] = useState(false)
  const [signalLoading, setSignalLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 스캔 상태 폴링 (5초 간격)
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await apiClient.getScanStatus()
        setScanStatus(status)
      } catch (err) {
        console.error("스캔 상태 조회 실패:", err)
      }
    }

    // 초기 조회
    fetchStatus()

    // 주기적 폴링
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  // VCP 스캔 트리거
  const triggerVCPScan = async (options?: {
    market?: string
    min_score?: number
    min_grade?: string
  }) => {
    setVcpLoading(true)
    setVcpResult(null)
    setError(null)

    try {
      const result = await apiClient.triggerVCPScan(options)
      setVcpResult(result)

      // 완료된 경우 상태 갱신
      if (result.status === "completed") {
        setTimeout(() => {
          apiClient.getScanStatus().then(setScanStatus)
        }, 1000)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "VCP 스캔 실패")
    } finally {
      setVcpLoading(false)
    }
  }

  // 시그널 생성 트리거
  const triggerSignalGeneration = async (tickers?: string[]) => {
    setSignalLoading(true)
    setSignalResult(null)
    setError(null)

    try {
      const result = await apiClient.triggerSignalGeneration(tickers)
      setSignalResult(result)

      // 완료된 경우 상태 갱신
      if (result.status === "completed") {
        setTimeout(() => {
          apiClient.getScanStatus().then(setScanStatus)
        }, 1000)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "시그널 생성 실패")
    } finally {
      setSignalLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
      case "idle":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
      case "running":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
      case "error":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Loader2 className="w-4 h-4 animate-spin" />
      case "completed":
        return <CheckCircle className="w-4 h-4" />
      case "error":
        return <XCircle className="w-4 h-4" />
      default:
        return <Activity className="w-4 h-4" />
    }
  }

  // 현재 실행 중인 작업이 있는지 확인
  const isRunning =
    scanStatus?.vcp_scan_status === "running" ||
    scanStatus?.signal_generation_status === "running"

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Radar className="w-4 h-4 text-purple-600" />
          스캔 제어
        </CardTitle>
        {isRunning && (
          <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            실행 중
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* VCP 스캔 섹션 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">VCP 스캔</span>
            {scanStatus && (
              <Badge variant="outline" className={`text-xs ${getStatusColor(scanStatus.vcp_scan_status)}`}>
                {getStatusIcon(scanStatus.vcp_scan_status)}
                <span className="ml-1">
                  {scanStatus.vcp_scan_status === "running" && "실행 중"}
                  {scanStatus.vcp_scan_status === "completed" && "완료"}
                  {scanStatus.vcp_scan_status === "idle" && "대기"}
                  {scanStatus.vcp_scan_status === "error" && "에러"}
                </span>
              </Badge>
            )}
          </div>

          {/* VCP 결과 표시 */}
          {vcpResult && (
            <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs space-y-1">
              <div className="flex justify-between">
                <span>상태:</span>
                <span className={vcpResult.status === "completed" ? "text-green-600" : "text-blue-600"}>
                  {vcpResult.status === "started" && "시작됨"}
                  {vcpResult.status === "completed" && "완료"}
                  {vcpResult.status === "error" && "에러"}
                </span>
              </div>
              {vcpResult.found_signals > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>발견된 시그널:</span>
                  <span className="font-medium">{vcpResult.found_signals}개</span>
                </div>
              )}
            </div>
          )}

          {/* 빠른 실행 버튼 */}
          <div className="grid grid-cols-3 gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => triggerVCPScan()}
              disabled={vcpLoading || scanStatus?.vcp_scan_status === "running"}
              aria-label="VCP 전체 스캔 실행"
            >
              {vcpLoading ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Play className="w-3 h-3 mr-1" />
              )}
              전체
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => triggerVCPScan({ market: "KOSPI" })}
              disabled={vcpLoading || scanStatus?.vcp_scan_status === "running"}
              aria-label="KOSPI VCP 스캔 실행"
            >
              {vcpLoading ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Play className="w-3 h-3 mr-1" />
              )}
              KOSPI
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => triggerVCPScan({ market: "KOSDAQ" })}
              disabled={vcpLoading || scanStatus?.vcp_scan_status === "running"}
              aria-label="KOSDAQ VCP 스캔 실행"
            >
              {vcpLoading ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Play className="w-3 h-3 mr-1" />
              )}
              KOSDAQ
            </Button>
          </div>
        </div>

        {/* 구분선 */}
        <div className="border-t border-gray-200 dark:border-gray-700" />

        {/* 시그널 생성 섹션 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">시그널 생성</span>
            {scanStatus && (
              <Badge variant="outline" className={`text-xs ${getStatusColor(scanStatus.signal_generation_status)}`}>
                {getStatusIcon(scanStatus.signal_generation_status)}
                <span className="ml-1">
                  {scanStatus.signal_generation_status === "running" && "실행 중"}
                  {scanStatus.signal_generation_status === "completed" && "완료"}
                  {scanStatus.signal_generation_status === "idle" && "대기"}
                  {scanStatus.signal_generation_status === "error" && "에러"}
                </span>
              </Badge>
            )}
          </div>

          {/* 시그널 생성 결과 표시 */}
          {signalResult && (
            <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs space-y-1">
              <div className="flex justify-between">
                <span>상태:</span>
                <span className={signalResult.status === "completed" ? "text-green-600" : "text-blue-600"}>
                  {signalResult.status === "started" && "시작됨"}
                  {signalResult.status === "completed" && "완료"}
                  {signalResult.status === "error" && "에러"}
                </span>
              </div>
              {signalResult.generated_count > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>생성된 시그널:</span>
                  <span className="font-medium">{signalResult.generated_count}개</span>
                </div>
              )}
            </div>
          )}

          <Button
            variant="default"
            size="sm"
            className="w-full h-9 text-xs"
            onClick={() => triggerSignalGeneration()}
            disabled={signalLoading || scanStatus?.signal_generation_status === "running"}
            aria-label="시그널 생성 실행"
          >
            {signalLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <TrendingUp className="w-4 h-4 mr-2" />
            )}
            시그널 생성
          </Button>
        </div>

        {/* 에러 표시 */}
        {error && (
          <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {/* 마지막 실행 정보 */}
        {scanStatus && (scanStatus.last_vcp_scan || scanStatus.last_signal_generation) && (
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {scanStatus.last_vcp_scan && (
                <span>VCP: {new Date(scanStatus.last_vcp_scan).toLocaleString("ko-KR")}
                </span>
              )}
              {scanStatus.last_vcp_scan && scanStatus.last_signal_generation && " | "}
              {scanStatus.last_signal_generation && (
                <span>시그널: {new Date(scanStatus.last_signal_generation).toLocaleString("ko-KR")}
                </span>
              )}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
