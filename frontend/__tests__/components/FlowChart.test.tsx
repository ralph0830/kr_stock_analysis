/**
 * FlowChart 컴포넌트 테스트
 * 수급 차트 시각화 컴포넌트 테스트
 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { FlowChart } from "@/components/FlowChart"

// Mock API client
import { apiClient } from "@/lib/api-client"

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    getStockFlow: vi.fn(),
  },
}))

// Mock Recharts 모듈
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ data, children }: { data: any[]; children: React.ReactNode }) => (
    <div data-testid="bar-chart" data-bars={data.length}>
      {children}
    </div>
  ),
  Bar: ({ dataKey, name }: { dataKey: string; name: string }) => (
    <div data-testid={`bar-${dataKey}`} data-name={name} className="recharts-bar-rect" />
  ),
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}))

// Mock UI components
vi.mock("@/components/ui/card", () => ({
  Card: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card">{children}</div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-content">{children}</div>
  ),
  CardHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-header">{children}</div>
  ),
  CardTitle: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-title">{children}</div>
  ),
}))

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => (
    <span data-testid="badge">{children}</span>
  ),
}))

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
  }: {
    children: React.ReactNode
    onClick?: () => void
  }) => (
    <button data-testid="button" onClick={onClick}>
      {children}
    </button>
  ),
}))

// Mock flowData utilities
vi.mock("@/lib/utils/flowData", () => ({
  transformFlowData: vi.fn((data) => data),
  calculateFlowColor: vi.fn(() => "#ef4444"),
}))

const mockTicker = "005930"
const mockFlowData = {
  ticker: mockTicker,
  period_days: 20,
  data: [
    {
      date: "2026-01-20",
      foreign_net: 1500000,
      inst_net: 800000,
      foreign_net_amount: 120000000000,
      inst_net_amount: 64000000000,
      supply_demand_score: 65.5,
    },
    {
      date: "2026-01-21",
      foreign_net: -500000,
      inst_net: 300000,
      foreign_net_amount: -40000000000,
      inst_net_amount: 24000000000,
      supply_demand_score: 55.0,
    },
  ],
  smartmoney_score: 72.5,
  total_points: 2,
}

describe("FlowChart Component", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 기본 mock 데이터 설정
    vi.mocked(apiClient.getStockFlow).mockResolvedValue(mockFlowData)
  })

  it("renders period selector tabs", async () => {
    render(<FlowChart ticker={mockTicker} />)

    await waitFor(() => {
      expect(screen.getByText("5일")).toBeInTheDocument()
      expect(screen.getByText("20일")).toBeInTheDocument()
      expect(screen.getByText("60일")).toBeInTheDocument()
    })
  })

  it("renders bar chart with flow data", async () => {
    render(<FlowChart ticker={mockTicker} />)

    await waitFor(() => {
      const chartContainer = screen.queryByTestId("bar-chart")
      expect(chartContainer).toBeInTheDocument()
    })
  })

  it("displays SmartMoney score", async () => {
    render(<FlowChart ticker={mockTicker} />)

    await waitFor(() => {
      expect(screen.getByText(/72\.5/)).toBeInTheDocument()
    })
  })

  it("shows empty state when no data", async () => {
    // 빈 데이터 반환 설정
    vi.mocked(apiClient.getStockFlow).mockResolvedValueOnce({
      ticker: mockTicker,
      period_days: 20,
      data: [],
      smartmoney_score: 0,
      total_points: 0,
    } as any)

    render(<FlowChart ticker={mockTicker} />)

    await waitFor(() => {
      expect(screen.getByText(/수급 데이터가 없습니다/)).toBeInTheDocument()
    })
  })

  it("changes period when tab is clicked", async () => {
    render(<FlowChart ticker={mockTicker} />)

    await waitFor(() => {
      expect(screen.getByText("60일")).toBeInTheDocument()
    })

    const tab60 = screen.getByText("60일")
    tab60.click()

    await waitFor(() => {
      expect(vi.mocked(apiClient.getStockFlow)).toHaveBeenCalled()
    })
  })

  it("displays foreign and institutional flow bars", async () => {
    render(<FlowChart ticker={mockTicker} />)

    await waitFor(() => {
      const foreignBar = screen.queryByTestId("bar-foreign_net")
      const instBar = screen.queryByTestId("bar-inst_net")

      expect(foreignBar).toBeInTheDocument()
      expect(instBar).toBeInTheDocument()
    })
  })
})
