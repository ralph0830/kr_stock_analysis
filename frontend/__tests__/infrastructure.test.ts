/**
 * 테스트 인프라 검증 테스트
 * Mock 데이터 팩토리와 헬퍼 함수가 올바르게 동작하는지 확인
 */

import { describe, it, expect } from "vitest"
import {
  mockPriceData,
  mockRisingPriceData,
  mockFallingPriceData,
  mockSidewaysPriceData,
  mockEmptyPriceData,
  mockFlowData,
  mockForeignBuyingFlowData,
  mockInstBuyingFlowData,
  mockDoubleBuyingFlowData,
  mockEmptyFlowData,
  mockStockChartResponse,
  mockStockFlowResponse,
  mockKiwoomChartResponse,
} from "./mocks/chartMocks"
import {
  createRandomPrice,
  createRandomVolume,
  createDateRange,
  expectValidPriceData,
  expectValidFlowData,
} from "./utils/testHelpers.tsx"

describe("Chart Mocks - PriceData", () => {
  it("mockPriceData가 지정된 일수만큼 데이터를 생성한다", () => {
    const data = mockPriceData(30)
    expect(data).toHaveLength(30)
  })

  it("mockPriceData가 유효한 PriceData 형식을 반환한다", () => {
    const data = mockPriceData(10)
    data.forEach(item => expectValidPriceData(item))
  })

  it("mockPriceData가 볼린저밴드를 포함한다", () => {
    const data = mockPriceData(10)
    data.forEach(item => {
      expect(item).toHaveProperty("upper_band")
      expect(item).toHaveProperty("lower_band")
      expect(item).toHaveProperty("middle_band")
      expect(item.upper_band).toBeGreaterThan(item.middle_band)
      expect(item.lower_band).toBeLessThan(item.middle_band)
    })
  })

  it("mockRisingPriceData가 상승 추세 데이터를 생성한다", () => {
    const data = mockRisingPriceData(10)
    expect(data[0].close).toBeLessThan(data[data.length - 1].close)
  })

  it("mockFallingPriceData가 하락 추세 데이터를 생성한다", () => {
    const data = mockFallingPriceData(10)
    expect(data[0].close).toBeGreaterThan(data[data.length - 1].close)
  })

  it("mockSidewaysPriceData가 횡보 데이터를 생성한다", () => {
    const data = mockSidewaysPriceData(10)
    const range = Math.max(...data.map(d => d.close)) - Math.min(...data.map(d => d.close))
    expect(range).toBeLessThan(2000) // ±1000원 범위
  })

  it("mockEmptyPriceData가 빈 배열을 반환한다", () => {
    const data = mockEmptyPriceData()
    expect(data).toEqual([])
  })
})

describe("Chart Mocks - FlowData", () => {
  it("mockFlowData가 지정된 일수만큼 데이터를 생성한다", () => {
    const data = mockFlowData(20)
    expect(data).toHaveLength(20)
  })

  it("mockFlowData가 유효한 FlowData 형식을 반환한다", () => {
    const data = mockFlowData(10)
    data.forEach(item => expectValidFlowData(item))
  })

  it("mockForeignBuyingFlowData가 외국인 순매수 우위 데이터를 생성한다", () => {
    const data = mockForeignBuyingFlowData(10)
    data.forEach(item => {
      expect(item.foreign_net).toBeGreaterThan(0)
    })
  })

  it("mockInstBuyingFlowData가 기관 순매수 우위 데이터를 생성한다", () => {
    const data = mockInstBuyingFlowData(10)
    data.forEach(item => {
      expect(item.inst_net).toBeGreaterThan(0)
    })
  })

  it("mockDoubleBuyingFlowData가 이중 매수 데이터를 생성한다", () => {
    const data = mockDoubleBuyingFlowData(10)
    data.forEach(item => {
      expect(item.foreign_net).toBeGreaterThan(0)
      expect(item.inst_net).toBeGreaterThan(0)
    })
  })

  it("mockEmptyFlowData가 빈 배열을 반환한다", () => {
    const data = mockEmptyFlowData()
    expect(data).toEqual([])
  })
})

describe("Chart Mocks - API Responses", () => {
  it("mockStockChartResponse가 유효한 API 응답 형식을 반환한다", () => {
    const response = mockStockChartResponse("005930", 30)
    expect(response).toHaveProperty("ticker", "005930")
    expect(response).toHaveProperty("period", "30d")
    expect(response).toHaveProperty("data")
    expect(response).toHaveProperty("total_points", 30)
    expect(response.data).toHaveLength(30)
  })

  it("mockStockFlowResponse가 유효한 수급 API 응답 형식을 반환한다", () => {
    const response = mockStockFlowResponse("005930", 20)
    expect(response).toHaveProperty("ticker", "005930")
    expect(response).toHaveProperty("period_days", 20)
    expect(response).toHaveProperty("data")
    expect(response).toHaveProperty("smartmoney_score")
    expect(response).toHaveProperty("total_points", 20)
    expect(response.smartmoney_score).toBeGreaterThanOrEqual(0)
    expect(response.smartmoney_score).toBeLessThanOrEqual(100)
  })

  it("mockKiwoomChartResponse가 역순 데이터를 반환한다", () => {
    const response = mockKiwoomChartResponse("005930", 10)
    expect(response.data).toHaveLength(10)
    // Kiwoom는 YYYYMMDD 형식
    expect(response.data[0].date).toMatch(/^\d{8}$/)
  })
})

describe("Test Helpers", () => {
  it("createRandomPrice가 지정된 범위 내 가격을 생성한다", () => {
    const price = createRandomPrice(80000, 2000)
    expect(price).toBeGreaterThanOrEqual(79000)
    expect(price).toBeLessThanOrEqual(81000)
  })

  it("createRandomVolume이 지정된 범위 내 거래량을 생성한다", () => {
    const volume = createRandomVolume(10000000, 5000000)
    expect(volume).toBeGreaterThanOrEqual(7500000)
    expect(volume).toBeLessThanOrEqual(12500000)
  })

  it("createDateRange가 지정된 일수만큼 날짜를 생성한다", () => {
    const dates = createDateRange(5)
    expect(dates).toHaveLength(5)
    dates.forEach(date => {
      expect(date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    })
  })

  it("createDateRange가 오름차순 정렬된 날짜를 반환한다", () => {
    const dates = createDateRange(5)
    for (let i = 1; i < dates.length; i++) {
      expect(new Date(dates[i]).getTime()).toBeGreaterThan(new Date(dates[i - 1]).getTime())
    }
  })
})
