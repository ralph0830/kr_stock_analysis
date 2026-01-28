/**
 * 시스템 상태 Zustand Store
 * 시스템 헬스 및 데이터 상태 관리
 */
import { create } from "zustand"
import type { ISystemHealth, IDataStatus } from "@/types"
import { apiClient } from "@/lib/api-client"

interface ISystemState {
  // 상태
  systemHealth: ISystemHealth | null
  dataStatus: IDataStatus | null
  loading: boolean
  error: string | null
  lastFetch: number | null  // 마지막 폴링 시간

  // 액션
  fetchSystemHealth: () => Promise<void>
  fetchDataStatus: () => Promise<void>
  refreshAll: () => Promise<void>
  startPolling: (interval?: number) => void
  stopPolling: () => void
}

export const useSystemStore = create<ISystemState>((set, get) => {
  let pollingInterval: NodeJS.Timeout | null = null

  return {
    // 초기 상태
    systemHealth: null,
    dataStatus: null,
    loading: false,
    error: null,
    lastFetch: null,

    // 시스템 헬스 조회
    fetchSystemHealth: async () => {
      try {
        const health = await apiClient.getSystemHealth()
        set({ systemHealth: health, lastFetch: Date.now() })
      } catch (error) {
        console.error("시스템 헬스 조회 실패:", error)
      }
    },

    // 데이터 상태 조회
    fetchDataStatus: async () => {
      try {
        const status = await apiClient.getDataStatus()
        set({ dataStatus: status })
      } catch (error) {
        console.error("데이터 상태 조회 실패:", error)
      }
    },

    // 전체 새로고침
    refreshAll: async () => {
      set({ loading: true })
      await Promise.all([
        get().fetchSystemHealth(),
        get().fetchDataStatus(),
      ])
      set({ loading: false })
    },

    // 주기적 폴링 시작
    startPolling: (interval: number = 30000) => {
      // 기존 폴링 정지
      if (pollingInterval) {
        get().stopPolling()
      }

      // 즉시 한 번 실행
      get().refreshAll()

      // 주기적 실행
      pollingInterval = setInterval(() => {
        get().refreshAll()
      }, interval)

      console.log(`시스템 상태 폴링 시작 (${interval / 1000}초 간격)`)
    },

    // 폴링 정지
    stopPolling: () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
        pollingInterval = null
        console.log("시스템 상태 폴링 정지")
      }
    },
  }
})
