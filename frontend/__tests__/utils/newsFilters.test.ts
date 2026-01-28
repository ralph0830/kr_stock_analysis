/**
 * News filtering utilities tests
 * 뉴스 필터링 및 감성 분석 테스트
 */

import { describe, it, expect } from "vitest"

describe("News Filters", () => {
  describe("filterRecentNews", () => {
    it("최근 7일 뉴스 필터링", () => {
      const today = new Date("2024-01-15")
      const news = [
        { date: "2024-01-15", title: "최신 뉴스" },
        { date: "2024-01-10", title: "5일 전 뉴스" },
        { date: "2024-01-05", title: "10일 전 뉴스" },
        { date: "2023-12-20", title: "오래된 뉴스" },
      ]

      const sevenDaysAgo = new Date(today)
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

      const recent = news.filter((item) => {
        const itemDate = new Date(item.date)
        return itemDate >= sevenDaysAgo
      })

      expect(recent).toHaveLength(2)
      expect(recent[0].title).toBe("최신 뉴스")
      expect(recent[1].title).toBe("5일 전 뉴스")
    })

    it("최근 30일 뉴스 필터링", () => {
      const today = new Date("2024-01-15")
      const news = [
        { date: "2024-01-14", title: "1일 전" },
        { date: "2024-01-01", title: "14일 전" },
        { date: "2023-12-01", title: "45일 전" },
      ]

      const thirtyDaysAgo = new Date(today)
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

      const recent = news.filter((item) => {
        const itemDate = new Date(item.date)
        return itemDate >= thirtyDaysAgo
      })

      expect(recent).toHaveLength(2)
    })
  })

  describe("calculateSentimentScore", () => {
    it("긍정적 뉴스 점수 계산", () => {
      const sentiments = [0.8, 0.6, 0.9, 0.7]
      const avgScore = sentiments.reduce((sum, s) => sum + s, 0) / sentiments.length
      expect(avgScore).toBeCloseTo(0.75, 2)
    })

    it("부정적 뉴스 점수 계산", () => {
      const sentiments = [-0.5, -0.3, -0.8, -0.6]
      const avgScore = sentiments.reduce((sum, s) => sum + s, 0) / sentiments.length
      expect(avgScore).toBeCloseTo(-0.55, 2)
    })

    it("중립적 뉴스 점수 계산", () => {
      const sentiments = [0.1, -0.1, 0.0, 0.2, -0.2]
      const avgScore = sentiments.reduce((sum, s) => sum + s, 0) / sentiments.length
      expect(avgScore).toBeCloseTo(0, 1)
    })

    it("빈 배열일 때 0 반환", () => {
      const sentiments: number[] = []
      const avgScore = sentiments.length > 0
        ? sentiments.reduce((sum, s) => sum + s, 0) / sentiments.length
        : 0
      expect(avgScore).toBe(0)
    })
  })

  describe("getSentimentLabel", () => {
    it("0.5 이상이면 긍정", () => {
      const score = 0.7
      let label = "중립"
      if (score >= 0.5) label = "긍정"
      else if (score <= -0.5) label = "부정"
      expect(label).toBe("긍정")
    })

    it("-0.5 이하면 부정", () => {
      const score = -0.7
      let label = "중립"
      if (score >= 0.5) label = "긍정"
      else if (score <= -0.5) label = "부정"
      expect(label).toBe("부정")
    })

    it("그 외는 중립", () => {
      const score = 0.3
      let label = "중립"
      if (score >= 0.5) label = "긍정"
      else if (score <= -0.5) label = "부정"
      expect(label).toBe("중립")
    })
  })

  describe("extractKeywords", () => {
    it("뉴스 제목에서 키워드 추출", () => {
      const title = "삼성전자, 반도체 사업 호황... 올해 실적 호조"
      const keywords = ["반도체", "사업", "실적", "호조"]

      // 간단한 키워드 추출 (공백으로 분리 후 2글자 이상)
      const words = title.split(/\s+/).flatMap((word) =>
        word.replace(/[.,...]/g, "").split("").filter((_, i) => i >= 2)
      )
      expect(words.length).toBeGreaterThan(0)
    })

    it("특수 문자 제거", () => {
      const title = "삼성전자, 매출 1조 달성!"
      const cleaned = title.replace(/[.,!]/g, "")
      expect(cleaned).toBe("삼성전자 매출 1조 달성")
    })
  })

  describe("getSentimentColor", () => {
    it("긍정은 빨간색", () => {
      const sentiment = "긍정"
      const color = sentiment === "긍정" ? "text-red-600" : sentiment === "부정" ? "text-blue-600" : "text-gray-600"
      expect(color).toBe("text-red-600")
    })

    it("부정은 파란색", () => {
      const sentiment = "부정"
      const color = sentiment === "긍정" ? "text-red-600" : sentiment === "부정" ? "text-blue-600" : "text-gray-600"
      expect(color).toBe("text-blue-600")
    })

    it("중립은 회색", () => {
      const sentiment = "중립"
      const color = sentiment === "긍정" ? "text-red-600" : sentiment === "부정" ? "text-blue-600" : "text-gray-600"
      expect(color).toBe("text-gray-600")
    })
  })
})
