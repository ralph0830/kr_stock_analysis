/**
 * 종목 상세 Zustand Store
 */
import { create } from "zustand"
import type { IStockDetail, IStockChart, IChartPoint, IAIAnalysis } from "@/types"
import { apiClient } from "@/lib/api-client"

interface IStockState {
  // 상태
  selectedStock: IStockDetail | null
  chartData: IStockChart | null
  aiAnalysis: IAIAnalysis | null
  loading: boolean
  error: string | null

  // 액션
  fetchStockDetail: (ticker: string) => Promise<void>
  fetchStockChart: (ticker: string, period?: string) => Promise<void>
  fetchAIAnalysis: (ticker: string) => Promise<void>
  clearStock: () => void

  // 차트 데이터 변환 (StockChart 컴포넌트용)
  getChartDataForStockChart: () => IChartPoint[]
}

export const useStockStore = create<IStockState>((set, get) => ({
  // 초기 상태
  selectedStock: null,
  chartData: null,
  aiAnalysis: null,
  loading: false,
  error: null,

  // 종목 상세 조회
  fetchStockDetail: async (ticker: string) => {
    set({ loading: true, error: null })
    try {
      const stock = await apiClient.getStockDetail(ticker)
      set({ selectedStock: stock, loading: false })
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "종목 정보 조회 실패",
      })
    }
  },

  // 종목 차트 조회
  fetchStockChart: async (ticker: string, period: string = "6mo") => {
    set({ loading: true, error: null })
    try {
      const chart = await apiClient.getStockChart(ticker, period)
      set({ chartData: chart, loading: false })
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "차트 데이터 조회 실패",
      })
    }
  },

  // AI 분석 조회
  fetchAIAnalysis: async (ticker: string) => {
    try {
      const analysis = await apiClient.getAISummary(ticker)
      set({ aiAnalysis: analysis })
    } catch (error) {
      console.error("AI 분석 조회 실패:", error)
      // AI 분석 실패는 치명적이 아니므로 에러 상태로 설정하지 않음
    }
  },

  // 종목 정보 초기화
  clearStock: () => {
    set({
      selectedStock: null,
      chartData: null,
      aiAnalysis: null,
      loading: false,
      error: null,
    })
  },

  // 차트 데이터 변환 (StockChart 컴포넌트용)
  getChartDataForStockChart: () => {
    const { chartData } = get()
    if (!chartData) return []

    return chartData.data.map((point) => ({
      date: point.date,
      open: point.open,
      high: point.high,
      low: point.low,
      close: point.close,
      volume: point.volume,
    }))
  },
}))
