/**
 * 단타 추천 페이지
 * Daytrading Scanner를 통한 실시간 단타 매수 신호 제공
 */
"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import Link from "next/link"
import { useDaytradingStore } from "@/store/daytradingStore"
import { useDaytradingSignals, useRealtimePrices } from "@/hooks/useWebSocket"
import { DaytradingSignalTable } from "@/components/DaytradingSignalTable"
import { ThemeToggle } from "@/components/ThemeToggle"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Zap, RefreshCw, Filter, ArrowLeft, Wifi, WifiOff, AlertCircle } from "lucide-react"

export default function CustomRecommendationPage() {
  const {
    signals: storeSignals,
    loading,
    error,
    filters,
    fetchDaytradingSignals,
    scanDaytradingMarket,
    setFilters,
    resetFilters,
  } = useDaytradingStore()

  // WebSocket 실시간 시그널 구독
  const {
    signals: wsSignals,
    isRealtime,
    connected: wsConnected,
    lastUpdate: wsLastUpdate,
  } = useDaytradingSignals()

  const [scanning, setScanning] = useState(false)
  const [wsRetryCount, setWsRetryCount] = useState(0)

  // 실시간 데이터와 스토어 데이터 병합 (실시간 우선)
  const signals = useMemo(() => {
    return wsSignals.length > 0 ? wsSignals : storeSignals
  }, [wsSignals, storeSignals])

  // 실시간 가격 구독 (시그널 목록의 ticker들) - signals 정의 후 실행
  const tickerList = useMemo(() => signals.map((s) => s.ticker), [signals])
  const {
    prices: realtimePrices,
    getPrice,
    connected: priceConnected,
    error: priceError,
  } = useRealtimePrices(tickerList)

  // WebSocket 연결 실패 카운트
  useEffect(() => {
    if (!wsConnected && wsSignals.length === 0) {
      setWsRetryCount((prev) => prev + 1)
    } else if (wsConnected) {
      setWsRetryCount(0)
    }
  }, [wsConnected, wsSignals.length])

  // 초기 데이터 로드 (실시간 연결 전에만)
  useEffect(() => {
    if (!isRealtime && storeSignals.length === 0) {
      fetchDaytradingSignals()
    }
  }, [fetchDaytradingSignals, isRealtime, storeSignals.length])

  // 스캔 핸들러
  const handleScan = async () => {
    setScanning(true)
    try {
      await scanDaytradingMarket({
        market: filters.market === "ALL" ? undefined : filters.market,
        limit: filters.limit,
      })
    } finally {
      setScanning(false)
    }
  }

  // 새로고침 핸들러
  const handleRefresh = () => {
    fetchDaytradingSignals()
  }

  // 에러 복구 핸들러
  const handleRetry = () => {
    setWsRetryCount(0)
    fetchDaytradingSignals()
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Zap className="w-6 h-6 text-yellow-500" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                ⚡ 단타 추천
              </h1>
              {/* 실시간 연결 상태 표시 개선 */}
              {wsConnected ? (
                <Badge variant="outline" className="text-green-600 border-green-600 dark:text-green-400 dark:border-green-400">
                  <Wifi className="w-3 h-3 mr-1" />
                  시그널 실시간
                </Badge>
              ) : (
                <Badge variant="outline" className="text-gray-500 border-gray-400 dark:text-gray-400 dark:border-gray-600">
                  <WifiOff className="w-3 h-3 mr-1" />
                  {wsRetryCount > 0 ? `재연결 중 (${wsRetryCount})` : "연결 안됨"}
                </Badge>
              )}
              {priceConnected && (
                <Badge variant="outline" className="text-green-600 border-green-600 dark:text-green-400 dark:border-green-400">
                  <Wifi className="w-3 h-3 mr-1" />
                  가격 실시간
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Link
                href="/dashboard"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
              >
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  대시보드
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 필터 패널 */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Filter className="w-5 h-5" />
                  필터
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* 시장 선택 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">시장</label>
                  <Select
                    value={filters.market}
                    onValueChange={(value: "ALL" | "KOSPI" | "KOSDAQ") =>
                      setFilters({ market: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">전체</SelectItem>
                      <SelectItem value="KOSPI">KOSPI</SelectItem>
                      <SelectItem value="KOSDAQ">KOSDAQ</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* 최소 점수 필터 */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">최소 점수</label>
                    <Badge variant="secondary">{filters.minScore}점</Badge>
                  </div>
                  <Slider
                    min={0}
                    max={105}
                    step={5}
                    value={[filters.minScore]}
                    onValueChange={([value]) => setFilters({ minScore: value })}
                    className="py-4"
                  />
                </div>

                {/* 개수 제한 */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">표시 개수</label>
                    <Badge variant="secondary">{filters.limit}</Badge>
                  </div>
                  <Slider
                    min={10}
                    max={100}
                    step={10}
                    value={[filters.limit]}
                    onValueChange={([value]) => setFilters({ limit: value })}
                    className="py-4"
                  />
                </div>

                {/* 버튼 그룹 */}
                <div className="space-y-2 pt-2">
                  <Button
                    onClick={handleRefresh}
                    variant="outline"
                    className="w-full"
                    disabled={loading}
                    aria-label="시그널 새로고침"
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                    새로고침
                  </Button>
                  <Button
                    onClick={handleScan}
                    className="w-full"
                    disabled={scanning}
                    aria-label={scanning ? "시장 스캔 중" : "시장 스캔 실행"}
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${scanning ? "animate-spin" : ""}`} />
                    {scanning ? "스캔 중..." : "시장 스캔"}
                  </Button>
                  <Button
                    onClick={resetFilters}
                    variant="ghost"
                    className="w-full"
                    aria-label="필터 초기화"
                  >
                    필터 초기화
                  </Button>
                </div>

                {/* 결과 요약 */}
                <div className="pt-4 border-t">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    총 <span className="font-semibold">{signals.length}</span>개 시그널
                    {isRealtime && wsLastUpdate && (
                      <span className="ml-2 text-green-600 dark:text-green-400 flex items-center gap-1">
                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        실시간
                      </span>
                    )}
                  </p>
                  {/* WebSocket 연결 실패 시 안내 */}
                  {!wsConnected && signals.length === 0 && (
                    <p className="text-xs text-gray-500 mt-2">
                      실시간 연결이 안됩니다. 새로고침하거나 시장 스캔을 실행하세요.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 안내 카드 */}
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">단타 추천이란?</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
                <p>7가지 체크리스트를 기반으로 당일 매수 후 익일 일봉 기준으로 매도하는 단타 매매 기회를 제공합니다.</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li>거래량 폭증</li>
                  <li>모멘텀 돌파</li>
                  <li>박스권 탈출</li>
                  <li>5일선 위</li>
                  <li>기관 매수</li>
                  <li>낙폭 과대</li>
                  <li>외국인 순매수</li>
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* 시그널 목록 */}
          <div className="lg:col-span-3">
            {/* 에러 상태 표시 개선 (재시도 버튼 추가) */}
            {error && (
              <Card className="mb-4 border-red-200 bg-red-50 dark:bg-red-900/20">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                      <p className="text-red-600 dark:text-red-400">{error}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRetry}
                      className="text-red-600 border-red-300 hover:bg-red-100 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-900/30"
                    >
                      <RefreshCw className="w-4 h-4 mr-1" />
                      재시도
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <DaytradingSignalTable
              signals={signals}
              loading={loading}
              isRealtime={isRealtime}
              lastUpdate={wsLastUpdate}
              onScan={handleScan}
              scanning={scanning}
              realtimePrices={realtimePrices}
              priceConnected={priceConnected}
              getPrice={getPrice}
            />
          </div>
        </div>
      </div>
    </main>
  )
}
