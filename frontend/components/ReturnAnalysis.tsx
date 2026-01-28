/**
 * 수익률 분석 컴포넌트
 * 시그널별 수익률과 누적 수익률 차트, 승률 통계를 표시합니다.
 */
"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { apiClient } from "@/lib/api-client"
import type { ISignalHistory } from "@/types"
import { analyzeReturnFromSignals } from "@/lib/utils/returnCalculations"
import { formatPercent } from "@/lib/utils"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts"
import { TrendingUp, TrendingDown, Activity, Target, AlertTriangle } from "lucide-react"

interface ReturnAnalysisProps {
  ticker: string
}

export function ReturnAnalysis({ ticker }: ReturnAnalysisProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signalData, setSignalData] = useState<ISignalHistory | null>(null)

  // 시그널 데이터 조회
  useEffect(() => {
    async function fetchSignals() {
      setLoading(true)
      setError(null)

      try {
        const data = await apiClient.getStockSignals(ticker, 100)
        setSignalData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "시그널 데이터 조회 실패")
      } finally {
        setLoading(false)
      }
    }

    fetchSignals()
  }, [ticker])

  // 수익률 분석 계산
  const analysis = useMemo(() => {
    if (!signalData || signalData.signals.length === 0) return null
    return analyzeReturnFromSignals(signalData.signals)
  }, [signalData])

  // 누적 수익률 차트 데이터 변환
  const chartData = useMemo(() => {
    if (!analysis) return []

    return analysis.cumulativeReturns.map((value, index) => ({
      index: index + 1,
      value: value.toFixed(2),
      return: analysis.returns[index]?.toFixed(2) || "0",
    }))
  }, [analysis])

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

  // 데이터 없음 (CLOSED 시그널이 없는 경우)
  if (!analysis || analysis.closedSignals === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-96">
          <p className="text-gray-500">종료된 시그널이 없어 수익률을 계산할 수 없습니다.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>수익률 분석</CardTitle>
      </CardHeader>

      <CardContent>
        {/* 통계 카드 */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {/* 승률 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-4 h-4 text-blue-500" />
              <p className="text-sm text-gray-600 dark:text-gray-400">승률</p>
            </div>
            <p className="text-2xl font-bold">{analysis.winRate.toFixed(1)}%</p>
          </div>

          {/* 평균 수익률 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-green-500" />
              <p className="text-sm text-gray-600 dark:text-gray-400">평균 수익률</p>
            </div>
            <p
              className={`text-2xl font-bold ${
                analysis.avgReturn > 0 ? "text-red-600" : analysis.avgReturn < 0 ? "text-blue-600" : ""
              }`}
            >
              {formatPercent(analysis.avgReturn)}
            </p>
          </div>

          {/* 최고 수익률 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-red-500" />
              <p className="text-sm text-gray-600 dark:text-gray-400">최고 수익률</p>
            </div>
            <p className="text-2xl font-bold text-red-600">
              {analysis.bestReturn !== null ? formatPercent(analysis.bestReturn) : "-"}
            </p>
          </div>

          {/* 최저 수익률 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="w-4 h-4 text-blue-500" />
              <p className="text-sm text-gray-600 dark:text-gray-400">최저 수익률</p>
            </div>
            <p className="text-2xl font-bold text-blue-600">
              {analysis.worstReturn !== null ? formatPercent(analysis.worstReturn) : "-"}
            </p>
          </div>

          {/* MDD */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              <p className="text-sm text-gray-600 dark:text-gray-400">MDD</p>
            </div>
            <p className="text-2xl font-bold text-orange-600">{analysis.mdd.toFixed(2)}%</p>
          </div>
        </div>

        {/* 누적 수익률 차트 */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-4">누적 수익률 곡선</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="index"
                  label={{ value: "거래 횟수", position: "insideBottom", offset: -5 }}
                />
                <YAxis
                  label={{ value: "누적 자본", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload
                      return (
                        <div className="bg-white dark:bg-gray-800 p-3 rounded shadow border border-gray-200 dark:border-gray-700">
                          <p className="text-sm font-medium mb-1">거래 #{data.index}</p>
                          <p className="text-sm">누적: {data.value}</p>
                          <p className="text-sm">수익률: {data.return}%</p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Legend />
                <ReferenceLine y={100} stroke="#9ca3af" strokeDasharray="3 3" label="초기 자본" />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  name="누적 자본"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 요약 정보 */}
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600 dark:text-gray-400">총 시그널</p>
              <p className="text-lg font-semibold">{analysis.totalSignals}개</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">종료된 시그널</p>
              <p className="text-lg font-semibold">{analysis.closedSignals}개</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            * 분석은 종료된 시그널(CLOSED)의 수익률을 기준으로 계산됩니다.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
