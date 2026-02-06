/**
 * Daytrading Scanner 신호 테이블 컴포넌트
 * 7개 체크리스트, 등급 배지, 매매 기준가 표시
 * 실시간 가격 연동 지원
 */
"use client"

import { useState, useEffect, useMemo } from "react"
import { IDaytradingSignal } from "@/types"
import type { RealtimePrice } from "@/hooks/useWebSocket"
import { getGradeColor } from "@/lib/utils"
import {
  CHECK_LABELS,
  CHECK_DESCRIPTIONS,
  SIGNAL_TYPE_COLORS,
  SIGNAL_TYPE_LABELS,
} from "@/constants/daytrading"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/EmptyState"
import { Check, X, Zap, Search, TrendingUp, TrendingDown } from "lucide-react"

interface DaytradingSignalTableProps {
  signals: IDaytradingSignal[]
  loading?: boolean
  isRealtime?: boolean
  lastUpdate?: Date | null
  onScan?: () => void
  scanning?: boolean
  // 실시간 가격 관련 props
  realtimePrices?: Record<string, RealtimePrice>
  priceConnected?: boolean
  getPrice?: (ticker: string) => RealtimePrice | undefined
}

export function DaytradingSignalTable({
  signals,
  loading = false,
  isRealtime = false,
  lastUpdate = null,
  onScan,
  scanning = false,
  realtimePrices = {},
  priceConnected = false,
  getPrice,
}: DaytradingSignalTableProps) {
  // 가격 변경 하이라이트 상태 (Phase 3)
  const [flashTickers, setFlashTickers] = useState<Set<string>>(new Set())

  // 실시간 가격 변경 감지
  useEffect(() => {
    if (!priceConnected || !getPrice) return

    const interval = setInterval(() => {
      signals.forEach((signal) => {
        const realtimePrice = getPrice(signal.ticker)
        if (realtimePrice) {
          // 이전 가격과 비교하여 변경 감지 (localStorage에 임시 저장)
          const prevPrice = localStorage.getItem(`price_${signal.ticker}`)
          if (prevPrice && prevPrice !== realtimePrice.price.toString()) {
            // 플래시 효과 트리거
            setFlashTickers((prev) => new Set([...prev, signal.ticker]))
            setTimeout(() => {
              setFlashTickers((prev) => {
                const next = new Set(prev)
                next.delete(signal.ticker)
                return next
              })
            }, 1000) // 1초 후 플래시 제거
          }
          localStorage.setItem(`price_${signal.ticker}`, realtimePrice.price.toString())
        }
      })
    }, 1000) // 1초마다 체크

    return () => clearInterval(interval)
  }, [signals, getPrice, priceConnected])

  // 실시간 가격 데이터 병합 헬퍼
  const getSignalWithRealtimePrice = (signal: IDaytradingSignal) => {
    const realtimePrice = getPrice?.(signal.ticker)
    return {
      ...signal,
      current_price: realtimePrice?.price ?? signal.current_price,
      change: realtimePrice?.change,
      change_rate: realtimePrice?.change_rate,
      isRealtimePrice: !!realtimePrice && priceConnected,
    }
  }
  // 로딩 상태
  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Skeleton className="w-5 h-5" />
                  <Skeleton className="h-6 w-32" />
                </div>
                <div className="flex items-center gap-2">
                  <Skeleton className="h-6 w-16 rounded-full" />
                  <Skeleton className="h-6 w-20 rounded-full" />
                  <Skeleton className="h-6 w-12 rounded-full" />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-20 mb-2" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
                {[...Array(7)].map((_, j) => (
                  <Skeleton key={j} className="h-10 w-full" />
                ))}
              </div>
              <div className="flex gap-4">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // 빈 상태 UI (EmptyState 공통 컴포넌트 사용)
  if (signals.length === 0) {
    return (
      <Card>
        <CardContent className="p-8">
          <EmptyState
            icon={Search}
            title="표시할 시그널이 없습니다"
            description="현재 조건에 맞는 단타 매수 신호가 없습니다."
            actionText={onScan ? "시장 스캔 실행" : undefined}
            onAction={onScan}
            loading={scanning}
          />
        </CardContent>
      </Card>
    )
  }

  // 실시간 업데이트 시간 표시
  const formatLastUpdate = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)

    if (diffSec < 60) return "방금 전"
    if (diffMin < 60) return `${diffMin}분 전`
    return `${Math.floor(diffMin / 60)}시간 전`
  }

  return (
    <div className="space-y-4">
      {/* 실시간 상태 표시 */}
      {(isRealtime || lastUpdate) && (
        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-2">
          <span className="flex items-center gap-1">
            {isRealtime && (
              <>
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                실시간 업데이트 중
              </>
            )}
          </span>
          {lastUpdate && (
            <span>마지막 업데이트: {formatLastUpdate(lastUpdate)}</span>
          )}
        </div>
      )}

      {signals.map((signal) => {
        const enrichedSignal = getSignalWithRealtimePrice(signal)
        const isFlash = flashTickers.has(signal.ticker)
        const changeRate = enrichedSignal.change_rate ?? 0
        const isUp = changeRate > 0
        const isDown = changeRate < 0

        return (
          <Card
            key={signal.ticker}
            className={`transition-all duration-300 ${isFlash ? (isUp ? "bg-green-50 dark:bg-green-900/20" : "bg-red-50 dark:bg-red-900/20") : ""}`}
          >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Zap className="w-5 h-5 text-yellow-500" />
                    {signal.name}
                  </CardTitle>
                  <p className="text-sm text-gray-500">{signal.ticker}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={getGradeColor(signal.grade)}>
                  {signal.grade} 등급
                </Badge>
                <Badge
                  variant="outline"
                  className={SIGNAL_TYPE_COLORS[signal.signal_type]}
                >
                  {SIGNAL_TYPE_LABELS[signal.signal_type]}
                </Badge>
                <Badge variant="secondary">
                  {signal.total_score}점
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* 7개 체크리스트 */}
            <div className="mb-4">
              <h4 className="text-sm font-medium mb-2">체크리스트</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2" role="list" aria-label="단타 체크리스트 항목들">
                {signal.checks.map((check, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center gap-2 text-sm p-2 rounded ${
                      check.status === "passed"
                        ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                        : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                    }`}
                    role="listitem"
                    aria-label={`${CHECK_LABELS[check.name] || check.name}: ${check.status === "passed" ? "통과" : "미통과"}. ${CHECK_DESCRIPTIONS[check.name] || ""}`}
                  >
                    {check.status === "passed" ? (
                      <Check className="w-4 h-4" aria-hidden="true" />
                    ) : (
                      <X className="w-4 h-4" aria-hidden="true" />
                    )}
                    <span className="text-xs">{CHECK_LABELS[check.name] || check.name}</span>
                    <span className="ml-auto text-xs font-medium" aria-label={`${check.points}점`}>
                      +{check.points}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 매매 기준가 */}
            {(signal.entry_price || signal.target_price || signal.stop_loss) && (
              <div className="border-t pt-3">
                <h4 className="text-sm font-medium mb-2">매매 기준가</h4>
                <div className="flex gap-4 text-sm">
                  {signal.entry_price && (
                    <div>
                      <span className="text-gray-500">진입: </span>
                      <span className="font-medium">{signal.entry_price.toLocaleString()}원</span>
                    </div>
                  )}
                  {signal.target_price && (
                    <div>
                      <span className="text-gray-500">목표: </span>
                      <span className="font-medium text-green-600">{signal.target_price.toLocaleString()}원</span>
                    </div>
                  )}
                  {signal.stop_loss && (
                    <div>
                      <span className="text-gray-500">손절: </span>
                      <span className="font-medium text-red-600">{signal.stop_loss.toLocaleString()}원</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 매매 기준가 */}
            {(signal.entry_price || signal.target_price || signal.stop_loss) && (
              <div className="border-t pt-3">
                <h4 className="text-sm font-medium mb-2">매매 기준가</h4>
                <div className="flex gap-4 text-sm">
                  {signal.entry_price && (
                    <div>
                      <span className="text-gray-500">진입: </span>
                      <span className="font-medium">{signal.entry_price.toLocaleString()}원</span>
                    </div>
                  )}
                  {signal.target_price && (
                    <div>
                      <span className="text-gray-500">목표: </span>
                      <span className="font-medium text-green-600">{signal.target_price.toLocaleString()}원</span>
                    </div>
                  )}
                  {signal.stop_loss && (
                    <div>
                      <span className="text-gray-500">손절: </span>
                      <span className="font-medium text-red-600">{signal.stop_loss.toLocaleString()}원</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 실시간 현재가 */}
            <div className="mt-3 pt-3 border-t">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-medium">현재가</h4>
                  {enrichedSignal.isRealtimePrice && (
                    <span className="flex items-center gap-1 text-xs text-green-500">
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                      실시간
                    </span>
                  )}
                </div>
                {enrichedSignal.current_price && (
                  <div className="flex items-center gap-3">
                    <span className={`text-xl font-bold ${isUp ? "text-red-600" : isDown ? "text-blue-600" : "text-gray-900"}`}>
                      {enrichedSignal.current_price.toLocaleString()}원
                    </span>
                    {changeRate !== 0 && (
                      <span className={`flex items-center gap-1 text-sm ${isUp ? "text-red-600" : "text-blue-600"}`}>
                        {isUp ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                        {isUp ? "+" : ""}{changeRate.toFixed(2)}%
                      </span>
                    )}
                    {enrichedSignal.change !== undefined && (
                      <span className={`text-sm ${isUp ? "text-red-600" : "text-blue-600"}`}>
                        {isUp ? "+" : ""}{enrichedSignal.change.toLocaleString()}
                      </span>
                    )}
                  </div>
                )}
              </div>
              {/* 실시간 연결 안됨 시 안내 */}
              {!priceConnected && (
                <p className="text-xs text-gray-500 mt-1">
                  실시간 가격 연결 대기 중...
                </p>
              )}
            </div>
          </CardContent>
        </Card>
        )
      })}
    </div>
  )
}
