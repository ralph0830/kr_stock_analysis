/**
 * 수급 데이터 변환 유틸리티 테스트
 */

import { describe, it, expect } from "vitest"
import { transformFlowData, calculateFlowColor, formatFlowAmount } from "@/lib/utils/flowData"

describe("Flow Data Utilities", () => {
  describe("transformFlowData", () => {
    it("API 응답을 차트 데이터로 변환한다", () => {
      // Given: API 응답 데이터가 있고
      const apiResponse = {
        ticker: "005930",
        period_days: 20,
        data: [
          {
            date: "2026-01-20",
            foreign_net: 1500000,
            inst_net: 800000,
          },
        ],
        smartmoney_score: 72.5,
        total_points: 1,
      }

      // When: 차트 데이터로 변환하면
      const chartData = transformFlowData(apiResponse.data)

      // Then: 차트용 형식으로 변환된다
      expect(chartData).toHaveLength(1)
      expect(chartData[0]).toHaveProperty("date", "2026-01-20")
      expect(chartData[0]).toHaveProperty("foreign_net", 1500000)
      expect(chartData[0]).toHaveProperty("inst_net", 800000)
    })

    it("데이터가 없을 때 빈 배열을 반환한다", () => {
      // Given: 빈 데이터가 있고
      const emptyData = []

      // When: 변환하면
      const chartData = transformFlowData(emptyData)

      // Then: 빈 배열을 반환한다
      expect(chartData).toEqual([])
    })
  })

  describe("calculateFlowColor", () => {
    it("순매수이면 빨간색을 반환한다", () => {
      // Given: 양수 값이 있고
      const netBuy = 1000000

      // When: 색상을 계산하면
      const color = calculateFlowColor(netBuy)

      // Then: 빨간색을 반환한다
      expect(color).toBe("#ef4444") // red-500
    })

    it("순매도이면 파란색을 반환한다", () => {
      // Given: 음수 값이 있고
      const netSell = -500000

      // When: 색상을 계산하면
      const color = calculateFlowColor(netSell)

      // Then: 파란색을 반환한다
      expect(color).toBe("#3b82f6") // blue-500
    })

    it("0이면 회색을 반환한다", () => {
      // Given: 0이 있고
      const zero = 0

      // When: 색상을 계산하면
      const color = calculateFlowColor(zero)

      // Then: 회색을 반환한다
      expect(color).toBe("#9ca3af") // gray-400
    })
  })

  describe("formatFlowAmount", () => {
    it("주수를 천 단위로 포맷팅한다", () => {
      // Given: 주수가 있고
      const shares = 1500000

      // When: 포맷팅하면
      const formatted = formatFlowAmount(shares)

      // Then: "150만주" 형식이 된다
      expect(formatted).toBe("150만주")
    })

    it("큰 수치를 만/억 단위로 포맷팅한다", () => {
      // Given: 큰 수치가 있고
      const largeAmount = 150000000

      // When: 포맷팅하면
      const formatted = formatFlowAmount(largeAmount)

      // Then: "1.5억주" 형식이 된다
      expect(formatted).toBe("1.5억주")
    })

    it("음수도 포맷팅한다", () => {
      // Given: 음수가 있고
      const negativeAmount = -500000

      // When: 포맷팅하면
      const formatted = formatFlowAmount(negativeAmount)

      // Then: "-50만주" 형식이 된다
      expect(formatted).toBe("-50만주")
    })
  })
})
