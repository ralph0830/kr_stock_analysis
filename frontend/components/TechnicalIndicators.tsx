/**
 * 기술적 지표 컴포넌트
 * RSI, MACD, 볼린저 밴드, 52주 신고가/신저가를 표시합니다.
 */
"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { apiClient } from "@/lib/api-client"
import type { IStockChart } from "@/types"
import { calculateTechnicalIndicators, calculateRSI, calculateMACD, calculateBollingerBands, calculate52WeekHighLow } from "@/lib/utils/technicalIndicators"
import { formatPrice } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react"

interface TechnicalIndicatorsProps {
  ticker: string
}

export function TechnicalIndicators({ ticker }: TechnicalIndicatorsProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [chartData, setChartData] = useState<IStockChart | null>(null)

  // 차트 데이터 조회
  useEffect(() => {
    async function fetchChartData() {
      setLoading(true)
      setError(null)

      try {
        const data = await apiClient.getStockChart(ticker, "1y")
        setChartData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "차트 데이터 조회 실패")
      } finally {
        setLoading(false)
      }
    }

    fetchChartData()
  }, [ticker])

  // 기술적 지표 계산
  const indicators = useMemo(() => {
    if (!chartData || chartData.data.length === 0) return null

    // 종가 배열 추출 (최신 순)
    const prices = chartData.data.map((d) => d.close).reverse()

    return calculateTechnicalIndicators(prices)
  }, [chartData])

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
  if (!indicators || !chartData || chartData.data.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-96">
          <p className="text-gray-500">기술적 지표를 계산할 데이터가 부족합니다.</p>
        </CardContent>
      </Card>
    )
  }

  // RSI 해석
  const getRSIInterpretation = (rsi: number) => {
    if (rsi >= 70) return { text: "과매수", color: "text-red-600" }
    if (rsi <= 30) return { text: "과매도", color: "text-blue-600" }
    return { text: "중립", color: "text-gray-600" }
  }

  const rsiInterpretation = getRSIInterpretation(indicators.rsi)

  // MACD 해석
  const getMACDInterpretation = (macd: number, signal: number, histogram: number) => {
    if (histogram > 0) return { text: "상승 추세", color: "text-red-600", icon: TrendingUp }
    if (histogram < 0) return { text: "하락 추세", color: "text-blue-600", icon: TrendingDown }
    return { text: "중립", color: "text-gray-600", icon: Minus }
  }

  const macdInterpretation = getMACDInterpretation(
    indicators.macd.macd,
    indicators.macd.signal,
    indicators.macd.histogram
  )

  const MACDIcon = macdInterpretation.icon

  return (
    <Card>
      <CardHeader>
        <CardTitle>기술적 지표</CardTitle>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* RSI */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">RSI (Relative Strength Index)</h3>
              <Badge variant="outline">14일</Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">RSI 값</span>
                <span className="text-xl font-bold">{indicators.rsi.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">해석</span>
                <span className={`text-sm font-semibold ${rsiInterpretation.color}`}>
                  {rsiInterpretation.text}
                </span>
              </div>
              {/* RSI 바 그래프 */}
              <div className="mt-3">
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 via-gray-500 to-red-500"
                    style={{ width: "100%" }}
                  />
                </div>
                <div className="relative">
                  <div
                    className="absolute top-0 w-1 h-3 bg-black dark:bg-white"
                    style={{ left: `${indicators.rsi}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>30</span>
                  <span>70</span>
                  <span>100</span>
                </div>
              </div>
            </div>
          </div>

          {/* MACD */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">MACD</h3>
              <Badge variant="outline">12/26/9</Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">MACD 라인</span>
                <span className="text-lg font-semibold">{indicators.macd.macd.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Signal 라인</span>
                <span className="text-lg font-semibold">{indicators.macd.signal.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Histogram</span>
                <span
                  className={`text-lg font-semibold ${
                    indicators.macd.histogram > 0 ? "text-red-600" : indicators.macd.histogram < 0 ? "text-blue-600" : ""
                  }`}
                >
                  {indicators.macd.histogram.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-2 pt-2 border-t">
                <MACDIcon className="w-4 h-4" />
                <span className={`text-sm font-semibold ${macdInterpretation.color}`}>
                  {macdInterpretation.text}
                </span>
              </div>
            </div>
          </div>

          {/* 볼린저 밴드 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">볼린저 밴드</h3>
              <Badge variant="outline">20일 ±2σ</Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">상단 밴드</span>
                <span className="text-lg font-semibold text-red-600">
                  {formatPrice(indicators.bollingerBands.upper)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">중간 밴드 (SMA)</span>
                <span className="text-lg font-semibold">
                  {formatPrice(indicators.bollingerBands.middle)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">하단 밴드</span>
                <span className="text-lg font-semibold text-blue-600">
                  {formatPrice(indicators.bollingerBands.lower)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">밴드 폭</span>
                <span className="text-sm font-semibold">
                  {formatPrice(indicators.bollingerBands.bandwidth)}
                </span>
              </div>
            </div>
          </div>

          {/* 52주 신고가/신저가 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">52주 신고가/신저가</h3>
              <Badge variant="outline">1년</Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-red-500" />
                  <span className="text-sm text-gray-600 dark:text-gray-400">신고가</span>
                </div>
                <span className="text-lg font-semibold text-red-600">
                  {formatPrice(indicators.fiftyTwoWeek.high)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-500" />
                  <span className="text-sm text-gray-600 dark:text-gray-400">신저가</span>
                </div>
                <span className="text-lg font-semibold text-blue-600">
                  {formatPrice(indicators.fiftyTwoWeek.low)}
                </span>
              </div>
              {chartData.data.length > 0 && (
                <div className="pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">현재가</span>
                    <span className="text-sm font-semibold">
                      {formatPrice(chartData.data[chartData.data.length - 1].close)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 지표 설명 */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <h4 className="font-semibold mb-2 text-sm">📊 기술적 지표 안내</h4>
          <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
            <li>• <strong>RSI 70 이상</strong>: 과매수 구간, 하락 가능성</li>
            <li>• <strong>RSI 30 이하</strong>: 과매도 구간, 반등 가능성</li>
            <li>• <strong>MACD Histogram &gt; 0</strong>: 상승 추세 (골든크로스)</li>
            <li>• <strong>MACD Histogram &lt; 0</strong>: 하락 추세 (데드크로스)</li>
            <li>• <strong>볼린저 밴드</strong>: 가격 변동성 측정, 밴드 축소 후 돌파 시 큰 움직임</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
