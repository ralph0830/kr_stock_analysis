/**
 * AI 분석 요약 컴포넌트
 * 종목의 AI 감성 분석 결과를 표시
 */
"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api-client"
import type { IAIAnalysis } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Brain, RefreshCw, TrendingUp, TrendingDown, Minus, Loader2 } from "lucide-react"

interface AIAnalysisSummaryProps {
  ticker: string
  stockName?: string
}

export function AIAnalysisSummary({ ticker, stockName }: AIAnalysisSummaryProps) {
  const [analysis, setAnalysis] = useState<IAIAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiClient.getAISummary(ticker)
      setAnalysis(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI 분석 조회 실패")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalysis()
  }, [ticker])

  // 감성 색상 계산
  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
      case "negative":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
      case "neutral":
        return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300"
      default:
        return "bg-gray-50 text-gray-400 dark:bg-gray-800/50 dark:text-gray-500"
    }
  }

  const getSentimentIcon = (sentiment?: string) => {
    switch (sentiment) {
      case "positive":
        return <TrendingUp className="w-5 h-5" />
      case "negative":
        return <TrendingDown className="w-5 h-5" />
      case "neutral":
        return <Minus className="w-5 h-5" />
      default:
        return <Brain className="w-5 h-5" />
    }
  }

  const getRecommendationColor = (rec?: string) => {
    switch (rec) {
      case "BUY":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
      case "SELL":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
      case "OVERWEIGHT":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
      case "UNDERWEIGHT":
        return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300"
      case "HOLD":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300"
    }
  }

  const getRecommendationLabel = (rec?: string) => {
    switch (rec) {
      case "BUY": return "매수"
      case "SELL": return "매도"
      case "OVERWEIGHT": return "과대평가"
      case "UNDERWEIGHT": return "저평가"
      case "HOLD": return "확보"
      default: return "-"
    }
  }

  // 로딩 상태
  if (loading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-600" />
            AI 분석
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
        </CardContent>
      </Card>
    )
  }

  // 에러 상태
  if (error) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-600" />
            AI 분석
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchAnalysis}
            className="h-8"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            재시도
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 dark:text-gray-400">{error}</p>
        </CardContent>
      </Card>
    )
  }

  // 데이터 없음
  if (!analysis || !analysis.sentiment) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Brain className="w-5 h-5 text-gray-400" />
            AI 분석
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => apiClient.triggerAIAnalysis(ticker).then(fetchAnalysis)}
            className="h-8"
          >
            분석 시작
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            아직 AI 분석이 없습니다. 분석을 시작해보세요.
          </p>
        </CardContent>
      </Card>
    )
  }

  // 감성 점수 계산 (-1.0 ~ 1.0)
  const score = analysis.score ?? 0
  const scorePercent = ((score + 1) / 2) * 100 // 0 ~ 100 변환
  const isPositive = score > 0
  const isNeutral = Math.abs(score) < 0.1

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          AI 분석
          {analysis.analysis_date && (
            <span className="text-xs font-normal text-gray-500 ml-2">
              ({new Date(analysis.analysis_date).toLocaleDateString("ko-KR")} 기준)
            </span>
          )}
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchAnalysis}
          className="h-8 text-gray-500 hover:text-gray-700"
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 감성 상태 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-full ${getSentimentColor(analysis.sentiment)}`}>
              {getSentimentIcon(analysis.sentiment)}
            </div>
            <span className="font-medium">
              {analysis.sentiment === "positive" && "긍정"}
              {analysis.sentiment === "negative" && "부정"}
              {analysis.sentiment === "neutral" && "중립"}
            </span>
          </div>
          <Badge className={getRecommendationColor(analysis.recommendation)}>
            {getRecommendationLabel(analysis.recommendation)}
          </Badge>
        </div>

        {/* 감성 점수 바 */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 dark:text-gray-400">감성 점수</span>
            <span className={`font-medium ${isPositive ? "text-green-600" : isNeutral ? "text-gray-600" : "text-red-600"}`}>
              {score > 0 ? "+" : ""}{score.toFixed(2)}
            </span>
          </div>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                isPositive
                  ? "bg-gradient-to-r from-green-400 to-green-600"
                  : isNeutral
                  ? "bg-gradient-to-r from-gray-400 to-gray-500"
                  : "bg-gradient-to-r from-red-400 to-red-600"
              }`}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>

        {/* 요약 텍스트 */}
        {analysis.summary && (
          <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {analysis.summary}
            </p>
          </div>
        )}

        {/* 키워드 태그 */}
        {analysis.keywords && analysis.keywords.length > 0 && (
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">주요 키워드</p>
            <div className="flex flex-wrap gap-1">
              {analysis.keywords.map((keyword, idx) => (
                <Badge
                  key={idx}
                  variant="secondary"
                  className="text-xs"
                >
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
