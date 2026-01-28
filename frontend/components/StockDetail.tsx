/**
 * 종목 상세 컴포넌트
 * 종목 기본 정보, 차트, 관련 시그널 표시
 */
"use client"

import { useEffect, useMemo } from "react"
import { useStockStore } from "@/store/stockStore"
import { FullStockChart, type PriceData } from "@/components/StockChart"
import { FlowChart } from "@/components/FlowChart"
import { SignalHistory } from "@/components/SignalHistory"
import { ReturnAnalysis } from "@/components/ReturnAnalysis"
import { TechnicalIndicators } from "@/components/TechnicalIndicators"
import { NewsFeed } from "@/components/NewsFeed"
import { AIAnalysisSummary } from "@/components/AIAnalysisSummary"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatPrice, formatPercent, getMarketGateColor } from "@/lib/utils"
import { ArrowLeft, TrendingUp, TrendingDown } from "lucide-react"

interface StockDetailProps {
  ticker: string
}

export function StockDetail({ ticker }: StockDetailProps) {
  const { selectedStock, chartData, loading, error, fetchStockDetail, fetchStockChart, getChartDataForStockChart } =
    useStockStore()

  // 종목 데이터 로드
  useEffect(() => {
    fetchStockDetail(ticker)
    fetchStockChart(ticker, "6mo")
  }, [ticker, fetchStockDetail, fetchStockChart])

  // 차트 데이터 변환
  const chartDataForComponent = useMemo(() => {
    const data = getChartDataForStockChart()
    return data.map((point) => ({
      date: point.date,
      close: point.close,
      volume: point.volume,
    })) as PriceData[]
  }, [chartData, getChartDataForStockChart])

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-gray-500">로딩 중...</p>
      </div>
    )
  }

  // 에러 상태
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <p className="text-red-500">{error}</p>
        <Button onClick={() => window.history.back()}>뒤로 가기</Button>
      </div>
    )
  }

  // 데이터 없음
  if (!selectedStock) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <p className="text-gray-500">종목 정보를 찾을 수 없습니다.</p>
        <Button onClick={() => window.history.back()}>뒤로 가기</Button>
      </div>
    )
  }

  // 가격 변화 계산
  const priceChange = selectedStock.price_change || 0
  const priceChangePct = selectedStock.price_change_pct || 0
  const isPositive = priceChange >= 0

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => window.history.back()}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{selectedStock.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-lg text-gray-600">{selectedStock.ticker}</span>
            <Badge variant="outline">{selectedStock.market}</Badge>
            {selectedStock.sector && <Badge variant="secondary">{selectedStock.sector}</Badge>}
          </div>
        </div>
      </div>

      {/* 가격 정보 카드 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">현재가</p>
              <p className="text-3xl font-bold">
                {selectedStock.current_price ? formatPrice(selectedStock.current_price) : "-"}
              </p>
            </div>
            <div className="text-right">
              <div className="flex items-center justify-end gap-1">
                {isPositive ? (
                  <TrendingUp className="w-5 h-5 text-red-500" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-blue-500" />
                )}
                <span className={`text-xl font-semibold ${isPositive ? "text-red-600" : "text-blue-600"}`}>
                  {priceChange !== 0 ? formatPrice(priceChange) : "-"}
                </span>
              </div>
              {priceChangePct !== 0 && (
                <p className={`text-sm ${isPositive ? "text-red-600" : "text-blue-600"}`}>
                  {formatPercent(priceChangePct)}
                </p>
              )}
            </div>
          </div>
          {selectedStock.volume && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-gray-500">
                거래량: <span className="font-semibold">{selectedStock.volume.toLocaleString()}주</span>
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI 분석 요약 */}
      <AIAnalysisSummary ticker={ticker} stockName={selectedStock.name} />

      {/* 차트 */}
      {chartDataForComponent.length > 0 && (
        <FullStockChart data={chartDataForComponent} height={400} />
      )}

      {/* 수급 차트 */}
      <FlowChart ticker={ticker} />

      {/* 시그널 히스토리 */}
      <SignalHistory ticker={ticker} />

      {/* 수익률 분석 */}
      <ReturnAnalysis ticker={ticker} />

      {/* 기술적 지표 */}
      <TechnicalIndicators ticker={ticker} />

      {/* 관련 뉴스 */}
      <NewsFeed ticker={ticker} />

      {/* 기본 정보 */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">시장</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{selectedStock.market}</p>
          </CardContent>
        </Card>
        {selectedStock.sector && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">섹터</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-lg font-semibold">{selectedStock.sector}</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* 업데이트 정보 */}
      {selectedStock.updated_at && (
        <p className="text-sm text-gray-500 text-center">
          데이터 기준일: {new Date(selectedStock.updated_at).toLocaleDateString("ko-KR")}
        </p>
      )}
    </div>
  )
}
