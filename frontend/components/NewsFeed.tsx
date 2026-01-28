/**
 * 뉴스 피드 컴포넌트
 * 최근 뉴스 목록과 감성 분석 결과, 키워드를 표시합니다.
 */
"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { apiClient } from "@/lib/api-client"
import type { INewsFeed } from "@/types"
import { filterRecentNews, calculateSentimentScore, getSentimentLabel, getSentimentColor, extractKeywords } from "@/lib/utils/newsFilters"
import { Newspaper, TrendingUp, TrendingDown, Minus, ExternalLink } from "lucide-react"

interface NewsFeedProps {
  ticker: string
}

// Mock 뉴스 데이터 (실제 API가 없을 때 사용)
const mockNewsData: INewsFeed = {
  ticker: "005930",
  total_news: 3,
  avg_sentiment: 0.35,
  sentiment_label: "중립",
  news: [
    {
      id: "1",
      ticker: "005930",
      title: "삼성전자, 신규 파운드리 반도체 수주 물량 증가",
      content: "삼성전자가 최근 신규 파운드리에 납품할 반도체 수주 물량을 늘렸습니다...",
      date: new Date().toISOString(),
      source: "연합뉴스",
      url: "https://example.com/news1",
      sentiment_score: 0.6,
      keywords: ["삼성전자", "반도체", "수주"],
    },
    {
      id: "2",
      ticker: "005930",
      title: "삼성전자, 4분기 실적 시장 기대치 상회",
      content: "삼성전자의 4분기 실적이 시장의 기대치를 상회했습니다...",
      date: new Date(Date.now() - 86400000).toISOString(), // 1일 전
      source: "헤럴드경제",
      url: "https://example.com/news2",
      sentiment_score: 0.3,
      keywords: ["삼성전자", "실적", "시장"],
    },
    {
      id: "3",
      ticker: "005930",
      title: "반도체 업황 둔화, 삼성전자 주가 약보",
      content: "글로벌 반도체 업황 둔화로 삼성전자 주가가 약세를 보이고 있습니다...",
      date: new Date(Date.now() - 172800000).toISOString(), // 2일 전
      source: "Korea Times",
      url: "https://example.com/news3",
      sentiment_score: -0.2,
      keywords: ["반도체", "업황", "주가"],
    },
  ],
}

export function NewsFeed({ ticker }: NewsFeedProps) {
  const [period, setPeriod] = useState<7 | 30>(7)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newsData, setNewsData] = useState<INewsFeed | null>(null)

  // 뉴스 데이터 조회
  useEffect(() => {
    async function fetchNews() {
      setLoading(true)
      setError(null)

      try {
        // 실제 API가 구현되기 전까지 mock 데이터 사용
        // const data = await apiClient.getStockNews(ticker, period)
        // setNewsData(data)

        // Mock 데이터 사용 (실제 API 구현 시 주석 해제)
        await new Promise((resolve) => setTimeout(resolve, 500)) // 로딩 시뮬레이션
        setNewsData(mockNewsData)
      } catch (err) {
        setError(err instanceof Error ? err.message : "뉴스 조회 실패")
      } finally {
        setLoading(false)
      }
    }

    fetchNews()
  }, [ticker, period])

  // 기간별 필터링된 뉴스
  const filteredNews = newsData
    ? filterRecentNews(newsData.news, period)
    : []

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
  if (!newsData || filteredNews.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>관련 뉴스</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-80">
          <div className="text-center">
            <Newspaper className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p className="text-gray-500">최근 {period}일간 뉴스가 없습니다.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // 전체 평균 감성 점수 계산
  const avgSentiment = calculateSentimentScore(
    filteredNews.map((n) => n.sentiment_score || 0)
  )
  const sentimentLabel = getSentimentLabel(avgSentiment)
  const sentimentColor = getSentimentColor(sentimentLabel)

  // 감성 아이콘
  const SentimentIcon = avgSentiment >= 0.5 ? TrendingUp : avgSentiment <= -0.5 ? TrendingDown : Minus

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>관련 뉴스</CardTitle>
          <div className="flex items-center gap-3">
            {/* 기간 선택 */}
            <div className="flex gap-1">
              <Button
                variant={period === 7 ? "default" : "outline"}
                size="sm"
                onClick={() => setPeriod(7)}
              >
                7일
              </Button>
              <Button
                variant={period === 30 ? "default" : "outline"}
                size="sm"
                onClick={() => setPeriod(30)}
              >
                30일
              </Button>
            </div>

            {/* 평균 감성 점수 */}
            {filteredNews.length > 0 && (
              <div className="flex items-center gap-2">
                <SentimentIcon className={`w-5 h-5 ${sentimentColor}`} />
                <span className={`text-sm font-semibold ${sentimentColor}`}>
                  {sentimentLabel}
                </span>
                <Badge variant="outline" className="text-sm">
                  {avgSentiment.toFixed(2)}
                </Badge>
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* 뉴스 목록 */}
        <div className="space-y-4">
          {filteredNews.map((news) => {
            const itemSentiment = getSentimentLabel(news.sentiment_score || 0)
            const itemColor = getSentimentColor(itemSentiment)
            const ItemIcon = news.sentiment_score && news.sentiment_score >= 0.5
              ? TrendingUp
              : news.sentiment_score && news.sentiment_score <= -0.5
              ? TrendingDown
              : Minus

            return (
              <div
                key={news.id}
                className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                {/* 뉴스 헤더 */}
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-base flex-1 pr-4">
                    {news.title}
                  </h3>
                  {news.url && (
                    <a
                      href={news.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>

                {/* 감성 점수 및 날짜 */}
                <div className="flex items-center gap-3 mb-2 text-sm">
                  <div className="flex items-center gap-1">
                    <ItemIcon className={`w-4 h-4 ${itemColor}`} />
                    <span className={`font-medium ${itemColor}`}>
                      {itemSentiment}
                    </span>
                    {news.sentiment_score !== undefined && (
                      <span className="text-gray-500">
                        ({news.sentiment_score.toFixed(2)})
                      </span>
                    )}
                  </div>
                  <span className="text-gray-400">|</span>
                  <span className="text-gray-500">
                    {new Date(news.date).toLocaleDateString("ko-KR")}
                  </span>
                  {news.source && (
                    <>
                      <span className="text-gray-400">|</span>
                      <span className="text-gray-500">{news.source}</span>
                    </>
                  )}
                </div>

                {/* 키워드 태그 */}
                {news.keywords && news.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {news.keywords.map((keyword, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* 뉴스 요약 */}
                {news.summary && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                    {news.summary}
                  </p>
                )}

                {/* 뉴스 내용 (요약이 없을 때만 표시) */}
                {!news.summary && news.content && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                    {news.content}
                  </p>
                )}
              </div>
            )}
          )}
        </div>

        {/* 요약 정보 */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-600 dark:text-gray-400">총 뉴스</p>
                <p className="text-lg font-semibold">{filteredNews.length}개</p>
              </div>
              <div>
                <p className="text-gray-600 dark:text-gray-400">기간</p>
                <p className="text-lg font-semibold">최근 {period}일</p>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              * 감성 분석은 AI 기반으로 자동 계산됩니다.
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
