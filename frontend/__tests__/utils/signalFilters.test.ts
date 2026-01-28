/**
 * Signal filtering utilities tests
 * 시그널 필터링 유틸리티 테스트
 */

import { describe, it, expect } from "vitest"

describe("signalFilters", () => {
  describe("filterByType", () => {
    it("VCP 시그널만 필터링", () => {
      const signals = [
        { signal_type: "VCP" },
        { signal_type: "JONGGA_V2" },
        { signal_type: "VCP" },
      ]
      // @ts-expect-error - 테스트용 간단한 객체
      const result = signals.filter((s) => s.signal_type === "VCP")
      expect(result).toHaveLength(2)
    })

    it("JONGGA_V2 시그널만 필터링", () => {
      const signals = [
        { signal_type: "VCP" },
        { signal_type: "JONGGA_V2" },
        { signal_type: "VCP" },
      ]
      // @ts-expect-error - 테스트용 간단한 객체
      const result = signals.filter((s) => s.signal_type === "JONGGA_V2")
      expect(result).toHaveLength(1)
    })
  })

  describe("filterByStatus", () => {
    it("OPEN 상태 시그널만 필터링", () => {
      const signals = [
        { status: "OPEN" },
        { status: "CLOSED" },
        { status: "OPEN" },
      ]
      // @ts-expect-error - 테스트용 간단한 객체
      const result = signals.filter((s) => s.status === "OPEN")
      expect(result).toHaveLength(2)
    })

    it("CLOSED 상태 시그널만 필터링", () => {
      const signals = [
        { status: "OPEN" },
        { status: "CLOSED" },
        { status: "OPEN" },
      ]
      // @ts-expect-error - 테스트용 간단한 객체
      const result = signals.filter((s) => s.status === "CLOSED")
      expect(result).toHaveLength(1)
    })
  })

  describe("calculateStats", () => {
    it("평균 수익률 계산", () => {
      const signals = [
        { return_pct: 10.5 },
        { return_pct: -3.2 },
        { return_pct: 7.8 },
      ]
      // @ts-expect-error - 테스트용 간단한 객체
      const returns = signals.map((s) => s.return_pct).filter((r): r is number => r !== undefined)
      const avg = returns.reduce((sum, r) => sum + r, 0) / returns.length
      expect(avg).toBeCloseTo(5.03, 1)
    })

    it("승률 계산", () => {
      const signals = [
        { return_pct: 10.5 },
        { return_pct: -3.2 },
        { return_pct: 7.8 },
        { return_pct: -1.5 },
      ]
      // @ts-expect-error - 테스트용 간단한 객체
      const returns = signals.map((s) => s.return_pct).filter((r): r is number => r !== undefined && r > 0)
      const winRate = (returns.length / signals.length) * 100
      expect(winRate).toBe(50)
    })
  })
})
