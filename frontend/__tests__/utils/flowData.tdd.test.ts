/**
 * SmartMoney 점수 계산 테스트 (TDD)
 */
import { describe, it, expect } from "vitest"
import { calculateSmartMoneyScore } from "@/lib/utils/flowData"

describe("calculateSmartMoneyScore - TDD", () => {
  it("데이터가 없으면 기본값 50 반환", () => {
    const result = calculateSmartMoneyScore([])
    expect(result).toBe(50.0)
  })

  it("null이면 기본값 50 반환", () => {
    const result = calculateSmartMoneyScore(null as any)
    expect(result).toBe(50.0)
  })

  it("외국인만 대량 순매수 시 점수 상승", () => {
    const flowData = Array.from({ length: 5 }, () => ({
      date: "2026-01-01",
      foreign_net: 1000000, // +100만
      inst_net: 0,
    }))
    const result = calculateSmartMoneyScore(flowData)
    expect(result).toBeGreaterThan(50)
  })

  it("기관만 대량 순매수 시 점수 상승", () => {
    const flowData = Array.from({ length: 5 }, () => ({
      date: "2026-01-01",
      foreign_net: 0,
      inst_net: 1000000, // +100만
    }))
    const result = calculateSmartMoneyScore(flowData)
    expect(result).toBeGreaterThan(50)
  })

  it("이중 매수(외국인+기관 동시 순매수) 시 최고 점수", () => {
    const flowData = Array.from({ length: 5 }, () => ({
      date: "2026-01-01",
      foreign_net: 1000000,
      inst_net: 1000000,
    }))
    const result = calculateSmartMoneyScore(flowData)
    expect(result).toBeGreaterThan(70) // 높은 점수
  })

  it("외국인/기관 모두 순매도 시 점수 하락", () => {
    const flowData = Array.from({ length: 5 }, () => ({
      date: "2026-01-01",
      foreign_net: -1000000,
      inst_net: -1000000,
    }))
    const result = calculateSmartMoneyScore(flowData)
    expect(result).toBeLessThan(50) // 낮은 점수
  })

  it("최근 5일 데이터만 사용한다 (slice -5)", () => {
    // slice(-5)는 마지막 5개 요소를 가져옴
    const flowData = Array.from({ length: 10 }, (_, i) => ({
      date: `2026-01-${i.toString().padStart(2, '0')}`,
      foreign_net: i < 5 ? -1000000 : 1000000, // 앞부 5일 순매도, 뒤 5일 순매수
      inst_net: 0,
    }))
    const result = calculateSmartMoneyScore(flowData)
    // slice(-5)는 뒤 5개를 가져오므로 순매수 (1000000)
    expect(result).toBeGreaterThan(50)
  })

  it("점수 범위: 0~100 사이", () => {
    const flowData = Array.from({ length: 5 }, () => ({
      date: "2026-01-01",
      foreign_net: (Math.random() - 0.5) * 5000000,
      inst_net: (Math.random() - 0.5) * 5000000,
    }))
    const result = calculateSmartMoneyScore(flowData)
    expect(result).toBeGreaterThanOrEqual(0)
    expect(result).toBeLessThanOrEqual(100)
  })
})