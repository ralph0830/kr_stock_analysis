/**
 * 수급 차트 컴포넌트
 * 외국인/기관 순매수 흐름을 시각화합니다.
 */
"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { apiClient } from "@/lib/api-client"
import type { IFlowHistory } from "@/types"
import { transformFlowData, calculateFlowColor } from "@/lib/utils/flowData"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"

interface FlowChartProps {
  ticker: string
}

export function FlowChart({ ticker }: FlowChartProps) {
  const [period, setPeriod] = useState<number>(20)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flowData, setFlowData] = useState<IFlowHistory | null>(null)

  // 수급 데이터 조회
  useEffect(() => {
    async function fetchFlow() {
      setLoading(true)
      setError(null)

      try {
        const data = await apiClient.getStockFlow(ticker, period)
        setFlowData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "수급 데이터 조회 실패")
      } finally {
        setLoading(false)
      }
    }

    fetchFlow()
  }, [ticker, period])

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
  if (!flowData || flowData.data.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-96">
          <p className="text-gray-500">수급 데이터가 없습니다.</p>
        </CardContent>
      </Card>
    )
  }

  // 차트 데이터 변환
  const chartData = transformFlowData(flowData.data)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>수급 흐름 (SmartMoney)</CardTitle>
          <Badge variant="outline" className="text-lg">
            점수: {flowData.smartmoney_score.toFixed(1)}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        {/* 기간 선택 */}
        <div className="mb-6 flex gap-2">
          <Button
            variant={period === 5 ? "default" : "outline"}
            size="sm"
            onClick={() => setPeriod(5)}
          >
            5일
          </Button>
          <Button
            variant={period === 20 ? "default" : "outline"}
            size="sm"
            onClick={() => setPeriod(20)}
          >
            20일
          </Button>
          <Button
            variant={period === 60 ? "default" : "outline"}
            size="sm"
            onClick={() => setPeriod(60)}
          >
            60일
          </Button>
        </div>

        {/* Bar 차트 */}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value)
                  return `${date.getMonth() + 1}/${date.getDate()}`
                }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  if (Math.abs(value) >= 10000) {
                    return `${(value / 10000).toFixed(0)}만`
                  }
                  return value
                }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload
                    return (
                      <div className="bg-white dark:bg-gray-800 p-3 rounded shadow border border-gray-200 dark:border-gray-700">
                        <p className="text-sm font-medium mb-2">{data.date}</p>
                        <p className="text-sm" style={{ color: "#ef4444" }}>
                          외국인: {data.foreign_net.toLocaleString()}주
                        </p>
                        <p className="text-sm" style={{ color: "#3b82f6" }}>
                          기관: {data.inst_net.toLocaleString()}주
                        </p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend />
              <Bar
                dataKey="foreign_net"
                name="외국인"
                fill="#ef4444"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="inst_net"
                name="기관"
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* SmartMoney 점수 설명 */}
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            <strong>SmartMoney 점수</strong>: 외국인 순매수 40% + 기관 순매수 30% 가중 계산
          </p>
          <p className="text-xs text-gray-500 mt-1">
            * 점수가 높을수록 외국인/기관의 순매수 비중이 큽니다.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

