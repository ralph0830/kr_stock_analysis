/**
 * 차트 데이터 Mock 생성기
 * TDD Red Phase: 먼저 실패하는 테스트를 위한 Mock 데이터 팩토리
 */

// 타입을 직접 정의하여 import 의존성 제거
export interface PriceData {
  date: string
  close: number
  volume: number
  upper_band: number
  lower_band: number
  middle_band: number
}

export interface IFlowDataPoint {
  date: string
  foreign_net: number
  inst_net: number
  foreign_net_amount?: number
  inst_net_amount?: number
  supply_demand_score?: number
}

/**
 * 기본 가격 데이터 생성
 */
export function mockPriceData(days: number = 30, startPrice: number = 80000): PriceData[] {
  const data: PriceData[] = []
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days + 1)

  for (let i = 0; i < days; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i)

    const change = (Math.random() - 0.5) * 0.04
    const price = startPrice * (1 + change * i * 0.1)
    const upperBand = price * 1.02
    const lowerBand = price * 0.98
    const middleBand = price

    data.push({
      date: date.toISOString().split('T')[0],
      close: Math.round(price),
      volume: Math.round(Math.random() * 10000000 + 5000000),
      upper_band: Math.round(upperBand),
      lower_band: Math.round(lowerBand),
      middle_band: Math.round(middleBand),
    })

    startPrice = price
  }

  return data
}

/**
 * 상승 추세 가격 데이터
 */
export function mockRisingPriceData(days: number = 30): PriceData[] {
  return mockPriceData(days, 70000).map((item, index) => ({
    ...item,
    close: Math.round(70000 * (1 + index * 0.005)),
  }))
}

/**
 * 하락 추세 가격 데이터
 */
export function mockFallingPriceData(days: number = 30): PriceData[] {
  return mockPriceData(days, 90000).map((item, index) => ({
    ...item,
    close: Math.round(90000 * (1 - index * 0.003)),
  }))
}

/**
 * 횡보 가격 데이터
 */
export function mockSidewaysPriceData(days: number = 30): PriceData[] {
  return mockPriceData(days, 80000).map((item) => ({
    ...item,
    close: 80000 + Math.round((Math.random() - 0.5) * 1000),
  }))
}

/**
 * 빈 차트 데이터
 */
export function mockEmptyPriceData(): PriceData[] {
  return []
}

/**
 * 기본 수급 데이터 생성
 */
export function mockFlowData(days: number = 20): IFlowDataPoint[] {
  const data: IFlowDataPoint[] = []
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days + 1)

  for (let i = 0; i < days; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i)

    const foreignNet = Math.round((Math.random() - 0.4) * 2000000)
    const instNet = Math.round((Math.random() - 0.4) * 1500000)

    data.push({
      date: date.toISOString().split('T')[0],
      foreign_net: foreignNet,
      inst_net: instNet,
      foreign_net_amount: foreignNet * 10000,
      inst_net_amount: instNet * 10000,
      supply_demand_score: 50 + (foreignNet + instNet) / 100000,
    })
  }

  return data
}

/**
 * 외국인 순매수 우위
 */
export function mockForeignBuyingFlowData(days: number = 20): IFlowDataPoint[] {
  const data = mockFlowData(days)
  return data.map((item) => ({
    ...item,
    foreign_net: Math.abs(item.foreign_net) + 500000,
    inst_net: item.inst_net,
  }))
}

/**
 * 기관 순매수 우위
 */
export function mockInstBuyingFlowData(days: number = 20): IFlowDataPoint[] {
  const data = mockFlowData(days)
  return data.map((item) => ({
    ...item,
    foreign_net: item.foreign_net,
    inst_net: Math.abs(item.inst_net) + 300000,
  }))
}

/**
 * 이중 매수
 */
export function mockDoubleBuyingFlowData(days: number = 20): IFlowDataPoint[] {
  const data = mockFlowData(days)
  return data.map((item) => ({
    ...item,
    foreign_net: Math.abs(item.foreign_net) + 500000,
    inst_net: Math.abs(item.inst_net) + 300000,
  }))
}

/**
 * 빈 수급 데이터
 */
export function mockEmptyFlowData(): IFlowDataPoint[] {
  return []
}

/**
 * API 응답 Mock
 */
export function mockStockChartResponse(ticker: string = "005930", days: number = 30) {
  return {
    ticker,
    period: `${days}d`,
    data: mockPriceData(days),
    total_points: days,
  }
}

/**
 * 수급 API 응답 Mock
 */
export function mockStockFlowResponse(ticker: string = "005930", days: number = 20) {
  const flowData = mockFlowData(days)
  let smartmoneyScore = 50.0

  if (flowData.length > 0) {
    const avgForeign = flowData.reduce((sum, d) => sum + d.foreign_net, 0) / flowData.length
    const avgInst = flowData.reduce((sum, d) => sum + d.inst_net, 0) / flowData.length
    const foreignScore = Math.min(100, Math.max(0, 50 + (avgForeign / 100000) * 10))
    const instScore = Math.min(100, Math.max(0, 50 + (avgInst / 100000) * 10))
    smartmoneyScore = (foreignScore * 0.4) + (instScore * 0.3) + 30
  }

  return {
    ticker,
    period_days: days,
    data: flowData,
    smartmoney_score: Math.round(smartmoneyScore * 10) / 10,
    total_points: days,
  }
}

/**
 * Kiwoom 차트 API 응답 Mock (역순)
 */
export function mockKiwoomChartResponse(ticker: string = "005930", days: number = 30) {
  const priceData = mockPriceData(days).reverse()

  return {
    ticker,
    period_days: days,
    data: priceData.map((item) => ({
      date: item.date.replace(/-/g, ''),
      price: item.close,
      volume: item.volume,
    })),
    total_points: days,
  }
}
