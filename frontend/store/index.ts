/**
 * Zustand Store
 */

import { create } from "zustand";
import type { Signal, MarketGateStatus, StockPrice, ISignalFilters, ISortConfig, IBacktestKPI } from "@/types";
import { apiClient } from "@/lib/api-client";
import { applyFiltersAndSort } from "@/lib/signalFilters";

interface AppState {
  // 시그널 상태
  signals: Signal[];
  loadingSignals: boolean;
  signalsError: string | null;

  // Market Gate 상태
  marketGate: MarketGateStatus | null;
  loadingMarketGate: boolean;
  marketGateError: string | null;

  // 백테스트 KPI 상태
  backtestKPI: IBacktestKPI | null;
  loadingBacktestKPI: boolean;
  backtestKPIError: string | null;

  // 실시간 가격 상태
  prices: Record<string, StockPrice>;
  pricesError: string | null;

  // 필터/정렬 상태
  filters: ISignalFilters;
  sortConfig: ISortConfig;

  // 액션
  fetchSignals: () => Promise<void>;
  fetchMarketGate: () => Promise<void>;
  fetchBacktestKPI: () => Promise<void>;
  fetchPrices: (tickers: string[]) => Promise<void>;

  // 필터 액션
  setFilters: (filters: Partial<ISignalFilters>) => void;
  resetFilters: () => void;
  setSortBy: (sortBy: ISortConfig["sortBy"]) => void;
  toggleSortOrder: () => void;

  // 필터링된 시그널 getter
  getFilteredSignals: () => Signal[];
}

export const useStore = create<AppState>((set, get) => ({
  // 초기 상태
  signals: [],
  loadingSignals: false,
  signalsError: null,

  marketGate: null,
  loadingMarketGate: false,
  marketGateError: null,

  backtestKPI: null,
  loadingBacktestKPI: false,
  backtestKPIError: null,

  prices: {},
  pricesError: null,

  // 필터/정렬 초기 상태
  filters: {
    grades: [],
    minScore: 0,
    maxScore: 12,
    signalType: "all",
  },
  sortConfig: {
    sortBy: "score",
    order: "desc",
  },

  // 시그널 조회
  fetchSignals: async () => {
    set({ loadingSignals: true, signalsError: null });
    try {
      const signals = await apiClient.getSignals();
      set({ signals, loadingSignals: false });
    } catch (error) {
      set({
        loadingSignals: false,
        signalsError: error instanceof Error ? error.message : "시그널 조회 실패",
      });
    }
  },

  // Market Gate 조회
  fetchMarketGate: async () => {
    set({ loadingMarketGate: true, marketGateError: null });
    try {
      const marketGate = await apiClient.getMarketGate();
      set({ marketGate, loadingMarketGate: false });
    } catch (error) {
      set({
        loadingMarketGate: false,
        marketGateError: error instanceof Error ? error.message : "Market Gate 조회 실패",
      });
    }
  },

  // 백테스트 KPI 조회
  fetchBacktestKPI: async () => {
    set({ loadingBacktestKPI: true, backtestKPIError: null });
    try {
      const backtestKPI = await apiClient.getBacktestKPI();
      set({ backtestKPI, loadingBacktestKPI: false });
    } catch (error) {
      set({
        loadingBacktestKPI: false,
        backtestKPIError: error instanceof Error ? error.message : "백테스트 KPI 조회 실패",
      });
    }
  },

  // 실시간 가격 조회
  fetchPrices: async (tickers: string[]) => {
    set({ pricesError: null });
    try {
      const prices = await apiClient.getRealtimePrices(tickers);
      set({ prices });
    } catch (error) {
      set({
        pricesError: error instanceof Error ? error.message : "가격 조회 실패",
      });
    }
  },

  // 필터 설정
  setFilters: (newFilters: Partial<ISignalFilters>) => {
    set({ filters: { ...get().filters, ...newFilters } });
  },

  // 필터 초기화
  resetFilters: () => {
    set({
      filters: {
        grades: [],
        minScore: 0,
        maxScore: 12,
        signalType: "all",
      },
    });
  },

  // 정렬 기준 설정
  setSortBy: (sortBy: ISortConfig["sortBy"]) => {
    set({ sortConfig: { ...get().sortConfig, sortBy } });
  },

  // 정렬 순서 토글
  toggleSortOrder: () => {
    set({
      sortConfig: {
        ...get().sortConfig,
        order: get().sortConfig.order === "asc" ? "desc" : "asc",
      },
    });
  },

  // 필터링된 시그널 반환
  getFilteredSignals: () => {
    const { signals, filters, sortConfig } = get();
    return applyFiltersAndSort(signals, filters, sortConfig);
  },
}));
