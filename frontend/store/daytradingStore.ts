/**
 * Daytrading Scanner Zustand Store
 */
import { create } from "zustand"
import type {
  IDaytradingSignal,
  IDaytradingScanRequest,
  IDaytradingAnalyzeRequest,
} from "@/types"
import { apiClient } from "@/lib/api-client"
import { normalizeDaytradingSignals } from "./utils/daytradingNormalizer"

interface IDaytradingState {
  // 상태
  signals: IDaytradingSignal[]
  loading: boolean
  error: string | null
  filters: {
    minScore: number
    market: "ALL" | "KOSPI" | "KOSDAQ"
    limit: number
  }

  // 액션
  fetchDaytradingSignals: () => Promise<void>
  scanDaytradingMarket: (request?: IDaytradingScanRequest) => Promise<void>
  analyzeStocks: (request: IDaytradingAnalyzeRequest) => Promise<void>
  setFilters: (filters: Partial<IDaytradingState["filters"]>) => void
  resetFilters: () => void
  clearSignals: () => void
}

const DEFAULT_FILTERS = {
  minScore: 60,
  market: "ALL" as const,
  limit: 50,
}

export const useDaytradingStore = create<IDaytradingState>((set, get) => ({
  // 초기 상태
  signals: [],
  loading: false,
  error: null,
  filters: DEFAULT_FILTERS,

  // 단타 시그널 조회
  fetchDaytradingSignals: async () => {
    const { filters } = get()
    set({ loading: true, error: null })

    try {
      const response = await apiClient.getDaytradingSignals({
        min_score: filters.minScore,
        market: filters.market === "ALL" ? undefined : filters.market,
        limit: filters.limit,
      })

      // API 응답 구조: {success: true, data: {signals: [...], count: N}}
      const signals = response.data?.data?.signals ?? response.data?.signals ?? []

      set({
        signals,
        loading: false,
      })
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "단타 시그널 조회 실패",
      })
    }
  },

  // 단타 시장 스캔
  scanDaytradingMarket: async (request) => {
    set({ loading: true, error: null })

    try {
      const response = await apiClient.scanDaytradingMarket(request || {
        market: get().filters.market === "ALL" ? undefined : get().filters.market,
        limit: get().filters.limit,
      })

      // API 응답 구조: {success: true, data: {signals: [...], count: N}}
      const responseData = response.data?.data ?? response.data

      // 정규화 함수로 응답 데이터 변환
      const normalizedSignals = normalizeDaytradingSignals(responseData)

      set({
        signals: normalizedSignals,
        loading: false,
      })
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "단타 스캔 실패",
      })
    }
  },

  // 단타 종목 분석
  analyzeStocks: async (request) => {
    set({ loading: true, error: null })

    try {
      const response = await apiClient.analyzeDaytradingStocks(request)

      // API 응답 구조: {success: true, data: {signals: [...], count: N}}
      const responseData = response.data?.data ?? response.data

      // 정규화 함수로 응답 데이터 변환
      const normalizedSignals = normalizeDaytradingSignals(responseData)

      set({
        signals: normalizedSignals,
        loading: false,
      })
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "단타 분석 실패",
      })
    }
  },

  // 필터 설정
  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    }))
  },

  // 필터 초기화
  resetFilters: () => {
    set({ filters: DEFAULT_FILTERS })
  },

  // 시그널 초기화
  clearSignals: () => {
    set({ signals: [], error: null })
  },
}))
