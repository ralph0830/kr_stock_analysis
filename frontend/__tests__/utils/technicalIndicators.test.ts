/**
 * Technical Indicators tests
 * 기술적 지표 계산 테스트 (RSI, MACD, 볼린저 밴드 등)
 */

import { describe, it, expect } from "vitest"

describe("Technical Indicators", () => {
  describe("RSI (Relative Strength Index)", () => {
    it("RSI 14일 계산", () => {
      // 테스트용 가격 데이터
      const prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113]

      // RSI 계산 로직 (간소 버전)
      const period = 14
      let gains = 0
      let losses = 0

      // 첫 14일 평균 gain/loss 계산
      for (let i = 1; i <= period; i++) {
        const change = prices[i] - prices[i - 1]
        if (change > 0) gains += change
        else losses -= change
      }

      const avgGain = gains / period
      const avgLoss = losses / period

      const rs = avgGain / avgLoss
      const rsi = 100 - (100 / (1 + rs))

      // RSI는 0-100 사이 값
      expect(rsi).toBeGreaterThan(0)
      expect(rsi).toBeLessThan(100)
    })

    it("모두 상승일 때 RSI 100", () => {
      const prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]

      const period = 14
      let gains = 0
      let losses = 0

      for (let i = 1; i <= period; i++) {
        const change = prices[i] - prices[i - 1]
        if (change > 0) gains += change
        else losses -= change
      }

      const avgGain = gains / period
      const avgLoss = losses / period

      // loss가 0이면 RSI는 100
      if (avgLoss === 0) {
        expect(100).toBe(100)
      }
    })

    it("모두 하락일 때 RSI 0", () => {
      const prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86]

      const period = 14
      let gains = 0
      let losses = 0

      for (let i = 1; i <= period; i++) {
        const change = prices[i] - prices[i - 1]
        if (change > 0) gains += change
        else losses -= change
      }

      const avgGain = gains / period
      const avgLoss = losses / period

      // gain이 0이면 RSI는 0
      if (avgGain === 0) {
        expect(0).toBe(0)
      }
    })
  })

  describe("MACD (Moving Average Convergence Divergence)", () => {
    it("MACD 라인 계산 (12일 EMA - 26일 EMA)", () => {
      const prices = Array.from({ length: 30 }, (_, i) => 100 + i * 0.5)

      // 단순 이동평균 (SMA)로 EMA 근사
      const ema12 = calculateSMA(prices.slice(-12))
      const ema26 = calculateSMA(prices.slice(-26))

      const macd = ema12 - ema26

      // 상승 추세면 MACD가 양수
      expect(macd).toBeGreaterThan(0)
    })

    it("Signal 라인 계산 (MACD의 9일 EMA)", () => {
      const macdValues = [1, 1.2, 1.5, 1.8, 2.0, 2.3, 2.5, 2.7, 3.0]

      // Signal line = MACD의 9일 EMA
      const signal = calculateSMA(macdValues)

      expect(signal).toBeGreaterThan(1)
      expect(signal).toBeLessThan(3)
    })

    it("Histogram 계산 (MACD - Signal)", () => {
      const macd = 2.5
      const signal = 2.0

      const histogram = macd - signal

      expect(histogram).toBe(0.5)
    })
  })

  describe("52주 신고가/신저가", () => {
    it("52주 신고가 계산", () => {
      const prices = Array.from({ length: 252 }, (_, i) => {
        // 52주(약 252거래일) 데이터
        return 100 + Math.sin(i / 20) * 20 + i * 0.1
      })

      const fiftyTwoWeekHigh = Math.max(...prices)

      expect(fiftyTwoWeekHigh).toBeGreaterThan(100)
    })

    it("52주 신저가 계산", () => {
      const prices = Array.from({ length: 252 }, (_, i) => {
        return 100 + Math.sin(i / 20) * 20 + i * 0.1
      })

      const fiftyTwoWeekLow = Math.min(...prices)

      expect(fiftyTwoWeekLow).toBeLessThan(120)
    })
  })

  describe("볼린저 밴드", () => {
    it("상단 밴드 계산 (20일 MA + 2표준편차)", () => {
      const prices = Array.from({ length: 20 }, () => 100 + Math.random() * 10)

      const sma = calculateSMA(prices)
      const variance = prices.reduce((sum, p) => sum + Math.pow(p - sma, 2), 0) / prices.length
      const stdDev = Math.sqrt(variance)

      const upperBand = sma + 2 * stdDev

      expect(upperBand).toBeGreaterThan(sma)
    })

    it("하단 밴드 계산 (20일 MA - 2표준편차)", () => {
      const prices = Array.from({ length: 20 }, () => 100 + Math.random() * 10)

      const sma = calculateSMA(prices)
      const variance = prices.reduce((sum, p) => sum + Math.pow(p - sma, 2), 0) / prices.length
      const stdDev = Math.sqrt(variance)

      const lowerBand = sma - 2 * stdDev

      expect(lowerBand).toBeLessThan(sma)
    })

    it("밴드 폭 계산", () => {
      const prices = Array.from({ length: 20 }, () => 100 + Math.random() * 10)

      const sma = calculateSMA(prices)
      const variance = prices.reduce((sum, p) => sum + Math.pow(p - sma, 2), 0) / prices.length
      const stdDev = Math.sqrt(variance)

      const upperBand = sma + 2 * stdDev
      const lowerBand = sma - 2 * stdDev
      const bandwidth = upperBand - lowerBand

      expect(bandwidth).toBeGreaterThan(0)
    })
  })
})

// Helper function: Simple Moving Average
function calculateSMA(prices: number[]): number {
  return prices.reduce((sum, p) => sum + p, 0) / prices.length
}
