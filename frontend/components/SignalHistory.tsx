/**
 * 시그널 히스토리 컴포넌트
 * 과거 VCP/종가베팅 시그널 내역을 표시합니다.
 */
"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { apiClient } from "@/lib/api-client"
import type { ISignalHistory, ISignalHistoryItem } from "@/types"
import { formatPrice, formatPercent } from "@/lib/utils"
import { TrendingUp, TrendingDown } from "lucide-react"

interface SignalHistoryProps {
  ticker: string
}

export function SignalHistory({ ticker }: SignalHistoryProps) {
  const [filter, setFilter] = useState<"all" | "VCP" | "JONGGA_V2">("all")
  const [statusFilter, setStatusFilter] = useState<"all" | "OPEN" | "CLOSED">("all")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signalData, setSignalData] = useState<ISignalHistory | null>(null)

  // 시그널 데이터 조회
  useEffect(() => {
    async function fetchSignals() {
      setLoading(true)
      setError(null)

      try {
        const data = await apiClient.getStockSignals(ticker, 50)
        setSignalData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "시그널 히스토리 조회 실패")
      } finally {
        setLoading(false)
      }
    }

    fetchSignals()
  }, [ticker])

  // 필터링된 시그널 목록
  const filteredSignals = signalData?.signals.filter((signal) => {
    if (filter !== "all" && signal.signal_type !== filter) return false
    if (statusFilter !== "all" && signal.status !== statusFilter) return false
    return true
  }) || []

  // 로딩 상태
  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-96">
          <p className="text-gray-500">로딩 중...</p>
        </CardContent>
      </Card>
    )
  }

  // 에러 상태
  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-96">
          <p className="text-red-500">에러: {error}</p>
        </CardContent>
      </Card>
    )
  }

  // 데이터 없음
  if (!signalData || signalData.signals.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-96">
          <p className="text-gray-500">시그널 히스토리가 없습니다.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>시그널 히스토리</CardTitle>
          <div className="flex gap-2">
            {signalData.avg_return_pct !== null && signalData.avg_return_pct !== undefined && (
              <Badge variant="outline" className="text-lg">
                평균 수익률: {formatPercent(signalData.avg_return_pct)}
              </Badge>
            )}
            {signalData.win_rate !== null && signalData.win_rate !== undefined && (
              <Badge variant="outline" className="text-lg">
                승률: {signalData.win_rate.toFixed(1)}%
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* 필터 UI */}
        <div className="mb-6 flex flex-wrap gap-2">
          <div className="flex gap-1">
            <Button
              variant={filter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter("all")}
            >
              전체
            </Button>
            <Button
              variant={filter === "VCP" ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter("VCP")}
            >
              VCP
            </Button>
            <Button
              variant={filter === "JONGGA_V2" ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter("JONGGA_V2")}
            >
              종가베팅 V2
            </Button>
          </div>
          <div className="flex gap-1">
            <Button
              variant={statusFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter("all")}
            >
              전체
            </Button>
            <Button
              variant={statusFilter === "OPEN" ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter("OPEN")}
            >
              진행중
            </Button>
            <Button
              variant={statusFilter === "CLOSED" ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter("CLOSED")}
            >
              종료
            </Button>
          </div>
        </div>

        {/* 시그널 테이블 */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4 font-semibold">날짜</th>
                <th className="text-left py-3 px-4 font-semibold">타입</th>
                <th className="text-left py-3 px-4 font-semibold">상태</th>
                <th className="text-right py-3 px-4 font-semibold">점수</th>
                <th className="text-right py-3 px-4 font-semibold">진입가</th>
                <th className="text-right py-3 px-4 font-semibold">청산가</th>
                <th className="text-right py-3 px-4 font-semibold">수익률</th>
              </tr>
            </thead>
            <tbody>
              {filteredSignals.map((signal) => (
                <tr key={signal.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="py-3 px-4 text-sm">
                    {new Date(signal.signal_date).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant="secondary">
                      {signal.signal_type === "VCP" ? "VCP" : "종가베팅 V2"}
                    </Badge>
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={signal.status === "OPEN" ? "default" : "outline"}>
                      {signal.status === "OPEN" ? "진행중" : "종료"}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span className="font-semibold">{signal.score?.toFixed(1) || "-"}</span>
                      {signal.grade && (
                        <Badge variant="outline" className="text-xs">
                          {signal.grade}
                        </Badge>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right text-sm">
                    {signal.entry_price ? formatPrice(signal.entry_price) : "-"}
                  </td>
                  <td className="py-3 px-4 text-right text-sm">
                    {signal.exit_price ? formatPrice(signal.exit_price) : "-"}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {signal.return_pct !== null && signal.return_pct !== undefined ? (
                      <div className="flex items-center justify-end gap-1">
                        {signal.return_pct > 0 ? (
                          <TrendingUp className="w-4 h-4 text-red-500" />
                        ) : signal.return_pct < 0 ? (
                          <TrendingDown className="w-4 h-4 text-blue-500" />
                        ) : null}
                        <span
                          className={`font-semibold ${
                            signal.return_pct > 0 ? "text-red-600" : signal.return_pct < 0 ? "text-blue-600" : ""
                          }`}
                        >
                          {formatPercent(signal.return_pct)}
                        </span>
                      </div>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 요약 정보 */}
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600 dark:text-gray-400">총 시그널</p>
              <p className="text-lg font-semibold">{signalData.total_signals}개</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">진행중</p>
              <p className="text-lg font-semibold text-green-600">{signalData.open_signals}개</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">종료</p>
              <p className="text-lg font-semibold">{signalData.closed_signals}개</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
