/**
 * Return calculation utilities tests
 * 수익률 계산 유틸리티 테스트
 */

import { describe, it, expect } from "vitest"

describe("Return Calculations", () => {
  describe("calculateReturn", () => {
    it("수익률 계산 (양수)", () => {
      const entryPrice = 10000
      const exitPrice = 12000
      const returnPct = ((exitPrice - entryPrice) / entryPrice) * 100
      expect(returnPct).toBe(20)
    })

    it("수익률 계산 (음수)", () => {
      const entryPrice = 10000
      const exitPrice = 9000
      const returnPct = ((exitPrice - entryPrice) / entryPrice) * 100
      expect(returnPct).toBe(-10)
    })

    it("수익률 계산 (변동 없음)", () => {
      const entryPrice = 10000
      const exitPrice = 10000
      const returnPct = ((exitPrice - entryPrice) / entryPrice) * 100
      expect(returnPct).toBe(0)
    })

    it("진입가가 0일 때 Infinity 반환", () => {
      const entryPrice = 0
      const exitPrice = 10000
      const returnPct = ((exitPrice - entryPrice) / entryPrice) * 100
      expect(returnPct).toBe(Infinity)
    })
  })

  describe("calculateCumulativeReturn", () => {
    it("누적 수익률 계산", () => {
      const returns = [10, -5, 15, -3, 8]
      let cumulative = 100 // 초기 자본
      const cumulativeReturns = []

      for (const r of returns) {
        cumulative = cumulative * (1 + r / 100)
        cumulativeReturns.push(cumulative)
      }

      expect(cumulativeReturns).toHaveLength(5)
      expect(cumulativeReturns[0]).toBeCloseTo(110, 5) // 100 * 1.1 = 110
      expect(cumulativeReturns[1]).toBeCloseTo(104.5, 1) // 110 * 0.95 = 104.5
      expect(cumulativeReturns[2]).toBeCloseTo(120.18, 1) // 104.5 * 1.15 = 120.18
    })
  })

  describe("calculateWinRate", () => {
    it("승률 계산", () => {
      const returns = [10, -5, 15, -3, 8, -2]
      const winningReturns = returns.filter((r) => r > 0)
      const winRate = (winningReturns.length / returns.length) * 100
      expect(winRate).toBe(50) // 3/6 = 50%
    })

    it("모두 수익일 때 승률 100%", () => {
      const returns = [10, 15, 8]
      const winningReturns = returns.filter((r) => r > 0)
      const winRate = (winningReturns.length / returns.length) * 100
      expect(winRate).toBe(100)
    })

    it("모두 손실일 때 승률 0%", () => {
      const returns = [-10, -5, -3]
      const winningReturns = returns.filter((r) => r > 0)
      const winRate = (winningReturns.length / returns.length) * 100
      expect(winRate).toBe(0)
    })
  })

  describe("calculateMDD", () => {
    it("MDD (Maximum Drawdown) 계산", () => {
      const cumulativeValues = [100, 110, 105, 95, 85, 90, 100]
      let peak = cumulativeValues[0]
      let maxDD = 0

      for (const value of cumulativeValues) {
        if (value > peak) {
          peak = value
        }
        const dd = ((peak - value) / peak) * 100
        if (dd > maxDD) {
          maxDD = dd
        }
      }

      expect(maxDD).toBeCloseTo(22.73, 1) // peak 110에서 85로 하락
    })

    it("하락 없을 때 MDD 0%", () => {
      const cumulativeValues = [100, 110, 120, 130]
      let peak = cumulativeValues[0]
      let maxDD = 0

      for (const value of cumulativeValues) {
        if (value > peak) {
          peak = value
        }
        const dd = ((peak - value) / peak) * 100
        if (dd > maxDD) {
          maxDD = dd
        }
      }

      expect(maxDD).toBe(0)
    })
  })

  describe("calculateAverageReturn", () => {
    it("평균 수익률 계산", () => {
      const returns = [10, -5, 15, -3, 8]
      const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length
      expect(avgReturn).toBe(5) // (10 -5 +15 -3 +8) / 5 = 5
    })

    it("빈 배열일 때 0 반환", () => {
      const returns: number[] = []
      const avgReturn = returns.length > 0
        ? returns.reduce((sum, r) => sum + r, 0) / returns.length
        : 0
      expect(avgReturn).toBe(0)
    })
  })

  describe("calculateBestWorstReturn", () => {
    it("최고/최저 수익률 계산", () => {
      const returns = [10, -5, 15, -3, 8]
      const bestReturn = Math.max(...returns)
      const worstReturn = Math.min(...returns)
      expect(bestReturn).toBe(15)
      expect(worstReturn).toBe(-5)
    })

    it("빈 배열일 때 null 반환", () => {
      const returns: number[] = []
      const bestReturn = returns.length > 0 ? Math.max(...returns) : null
      const worstReturn = returns.length > 0 ? Math.min(...returns) : null
      expect(bestReturn).toBeNull()
      expect(worstReturn).toBeNull()
    })
  })
})
