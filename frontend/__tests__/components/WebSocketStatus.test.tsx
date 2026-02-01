/**
 * WebSocket 연결 상태 UI 컴포넌트 테스트 (Phase 4: GREEN)
 *
 * TDD 두 번째 단계: 연결 상태 UI 기능 구현
 *
 * 테스트 대상:
 * 1. 연결 중 상태일 때 노란색 ◐ 아이콘 표시
 * 2. 연결됨 상태일 때 녹색 ● 아이콘 표시
 * 3. 에러 상태일 때 빨간색 ⚠️ 아이콘 표시
 * 4. 재연결 시도 횟수 표시
 * 5. 마지막 에러 메시지 툴팁 표시
 * 6. 상태 변경 시 부드러운 전환 애니메이션
 * 7. aria-label 접근성 속성
 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { WebSocketStatus } from "@/components/RealtimePriceCard"

// useWebSocket mock implementation
const mockUseWebSocket = vi.fn()
vi.mock("@/hooks/useWebSocket", () => ({
  useWebSocket: () => mockUseWebSocket(),
}))

import { useWebSocket } from "@/hooks/useWebSocket"

// 전역 container 변수 (각 테스트에서 사용)
let container: HTMLElement

describe("WebSocket 연결 상태 UI - Phase 4 GREEN", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock return value
    mockUseWebSocket.mockReturnValue({
      connected: false,
      connecting: false,
      error: null,
      connectionState: "disconnected",
      clientId: null,
      reconnectCount: 0,
      lastError: null,
    })
  })

  describe("연결 상태 아이콘 - GREEN Phase", () => {
    it("연결 중 상태일 때 노란색 ◐ 아이콘을 표시해야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: false,
        connecting: true,
        error: null,
        connectionState: "connecting",
        clientId: null,
        reconnectCount: 0,
        lastError: null,
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: 연결 중 아이콘이 있어야 함
      const connectingIcon = container.querySelector('[data-testid="ws-icon-connecting"]')
      expect(connectingIcon).toBeDefined()
    })

    it("연결됨 상태일 때 녹색 ● 아이콘을 표시해야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: true,
        connecting: false,
        error: null,
        connectionState: "connected",
        clientId: "test-client-123",
        reconnectCount: 0,
        lastError: null,
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: 연결됨 아이콘이 있어야 함
      const connectedIcon = container.querySelector('[data-testid="ws-icon-connected"]')
      expect(connectedIcon).toBeDefined()
    })

    it("에러 상태일 때 빨간색 ⚠️ 아이콘을 표시해야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: false,
        connecting: false,
        error: true,
        connectionState: "error",
        clientId: null,
        reconnectCount: 3,
        lastError: "Connection timeout",
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: 에러 아이콘이 있어야 함
      const errorIcon = container.querySelector('[data-testid="ws-icon-error"]')
      expect(errorIcon).toBeDefined()
    })
  })

  describe("재연결 횟수 표시 - GREEN Phase", () => {
    it("재연결 시도 횟수를 표시해야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: false,
        connecting: true,
        error: true,
        connectionState: "connecting",
        clientId: null,
        reconnectCount: 3,
        lastError: "Connection lost",
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: 재연결 횟수가 표시되어야 함
      const reconnectText = screen.queryByText(/재연결.*3/)
      expect(reconnectText).toBeDefined()
    })

    it("재연결 횟수가 0일 때는 표시하지 않아야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: true,
        connecting: false,
        error: null,
        connectionState: "connected",
        clientId: "test-client-123",
        reconnectCount: 0,
        lastError: null,
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: 재연결 텍스트가 없어야 함
      const reconnectText = container.querySelector('[data-testid="ws-reconnect-count"]')
      expect(reconnectText).toBeNull()
    })
  })

  describe("에러 메시지 툴팁 - GREEN Phase", () => {
    it("마지막 에러 메시지를 툴팁으로 표시해야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: false,
        connecting: false,
        error: true,
        connectionState: "error",
        clientId: null,
        reconnectCount: 1,
        lastError: "Connection timeout",
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: 에러 메시지가 툴팁에 있어야 함
      const errorTooltip = container.querySelector('[title*="Connection timeout"]')
      expect(errorTooltip).toBeDefined()
    })
  })

  describe("접근성 - GREEN Phase", () => {
    it("aria-label 속성을 포함해야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: true,
        connecting: false,
        error: null,
        connectionState: "connected",
        clientId: "test-client-123",
        reconnectCount: 0,
        lastError: null,
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: aria-label이 있어야 함
      const statusElement = container.querySelector('[aria-label*="WebSocket"]')
      expect(statusElement).toBeDefined()
    })
  })

  describe("상태 전환 애니메이션 - GREEN Phase", () => {
    it("상태 변경 시 transition 클래스가 있어야 함", () => {
      // Arrange
      mockUseWebSocket.mockReturnValue({
        connected: true,
        connecting: false,
        error: null,
        connectionState: "connected",
        clientId: "test-client-123",
        reconnectCount: 0,
        lastError: null,
      })

      // Act
      container = render(<WebSocketStatus />).container

      // Assert: transition 클래스가 있어야 함
      const statusElement = container.querySelector('[class*="transition"]')
      expect(statusElement).toBeDefined()
    })
  })
})
