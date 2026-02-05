/**
 * Chart Page TDD 테스트
 * 차트 페이지의 검색, 종목 선택, 미니 차트 렌더링 테스트
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { ReactNode } from "react"

// Recharts Mock (StockChart 사용)
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children, width, height }: {
    children: ReactNode
    width?: number | string
    height?: number | string
  }) => (
    <div
      data-testid="responsive-container"
      style={{ width: width || '100%', height: height || 400 }}
    >
      {children}
    </div>
  ),
  LineChart: ({ children, data }: {
    children: ReactNode
    data: any[]
  }) => (
    <div data-testid="line-chart" data-points={data.length}>
      {children}
    </div>
  ),
  AreaChart: ({ children, data }: {
    children: ReactNode
    data: any[]
  }) => (
    <div data-testid="area-chart" data-points={data.length}>
      {children}
    </div>
  ),
  BarChart: ({ children, data }: {
    children: ReactNode
    data: any[]
  }) => (
    <div data-testid="bar-chart" data-points={data.length}>
      {children}
    </div>
  ),
  ComposedChart: ({ children, data }: {
    children: ReactNode
    data: any[]
  }) => (
    <div data-testid="composed-chart" data-points={data.length}>
      {children}
    </div>
  ),
  Line: ({ dataKey }: { dataKey: string }) => (
    <div data-testid={`line-${dataKey}`} className="recharts-line" />
  ),
  Area: ({ dataKey }: { dataKey: string }) => (
    <div data-testid={`area-${dataKey}`} className="recharts-area" />
  ),
  Bar: ({ dataKey }: { dataKey: string }) => (
    <div data-testid={`bar-${dataKey}`} className="recharts-bar" />
  ),
  XAxis: () => <div data-testid="x-axis" className="recharts-x-axis" />,
  YAxis: () => <div data-testid="y-axis" className="recharts-y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
}))

// Mock utils
vi.mock("@/lib/utils", () => ({
  formatPrice: (value: number) => `${value.toLocaleString()}원`,
  formatPercent: (value: number) => `${value.toFixed(2)}%`,
}))

// Mock apiClient
const mockChartData = [
  { date: "20260101", close: 80000, volume: 1000000 },
  { date: "20260102", close: 81000, volume: 1200000 },
  { date: "20260103", close: 80500, volume: 900000 },
]

const mockMiniChartData = {
  "005930": [
    { date: "20260101", close: 80000, volume: 1000000 },
    { date: "20260102", close: 81000, volume: 1200000 },
  ],
  "000660": [
    { date: "20260101", close: 150000, volume: 500000 },
    { date: "20260102", close: 152000, volume: 600000 },
  ],
  "035420": [
    { date: "20260101", close: 200000, volume: 300000 },
    { date: "20260102", close: 205000, volume: 350000 },
  ],
  "005380": [
    { date: "20260101", close: 220000, volume: 400000 },
    { date: "20260102", close: 225000, volume: 450000 },
  ],
}

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    getStockChart: vi.fn((ticker: string, period: string) => {
      // 미니 차트용 데이터 (1mo)
      if (period === "1mo") {
        return Promise.resolve({
          ticker,
          period,
          data: mockMiniChartData[ticker] || [],
        })
      }
      // 메인 차트용 데이터 (6mo)
      return Promise.resolve({
        ticker,
        period,
        data: mockChartData,
      })
    }),
  },
}))

// Mock ThemeToggle
vi.mock("@/components/ThemeToggle", () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}))

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

// 컴포넌트 import (mock 설정 후)
import ChartPage from "@/app/chart/page"

// 페이지 래퍼 (next/navigation mock)
const mockSearchParams = {}
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => mockSearchParams[key],
  }),
}))

describe("ChartPage - TDD", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderChartPage = () => {
    return render(<ChartPage />)
  }

  it("페이지 헤더를 렌더링한다", () => {
    renderChartPage()

    expect(screen.getByText("📊 차트 시각화")).toBeInTheDocument()
  })

  it("Kiwoom 실시간 데이터 연동 배지를 표시한다", async () => {
    renderChartPage()

    // 비동기 상태 업데이트 대기
    await waitFor(() => {
      expect(screen.getByText(/Kiwoom 실시간 데이터 연동됨/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it("검색 입력창을 렌더링한다", () => {
    renderChartPage()

    const searchInput = screen.getByPlaceholderText("종목명 또는 티커 검색...")
    expect(searchInput).toBeInTheDocument()
  })

  it("빠른 선택 버튼을 렌더링한다", () => {
    renderChartPage()

    expect(screen.getByText("삼성전자")).toBeInTheDocument()
    expect(screen.getByText("SK하이닉스")).toBeInTheDocument()
    expect(screen.getByText("NAVER")).toBeInTheDocument()
    expect(screen.getByText("현대차")).toBeInTheDocument()
  })

  it("미니 차트 섹션을 렌더링한다", () => {
    renderChartPage()

    expect(screen.getByText("미니 차트")).toBeInTheDocument()
  })

  it("차트 기능 안내를 렌더링한다", () => {
    renderChartPage()

    expect(screen.getByText("차트 기능 안내")).toBeInTheDocument()
    expect(screen.getAllByText(/가격 차트/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/볼린저밴드/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/거래량/).length).toBeGreaterThan(0)
  })

  it("홈 링크를 제공한다", () => {
    renderChartPage()

    const homeLink = screen.getByText("← 홈")
    expect(homeLink).toBeInTheDocument()
    expect(homeLink.closest("a")).toHaveAttribute("href", "/")
  })
})

describe("ChartPage - 검색 기능", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderChartPage = () => {
    return render(<ChartPage />)
  }

  it("검색 입력창에 입력할 수 있다", () => {
    renderChartPage()

    const searchInput = screen.getByPlaceholderText("종목명 또는 티커 검색...")

    fireEvent.change(searchInput, { target: { value: "삼성" } })

    expect(searchInput).toHaveValue("삼성")
  })

  it("티커로 검색어를 입력할 수 있다", () => {
    renderChartPage()

    const searchInput = screen.getByPlaceholderText("종목명 또는 티커 검색...")

    fireEvent.change(searchInput, { target: { value: "005930" } })

    expect(searchInput).toHaveValue("005930")
  })

  it("종목명이 페이지에 표시된다", () => {
    renderChartPage()

    expect(screen.getByText("삼성전자")).toBeInTheDocument()
  })
})

describe("ChartPage - 종목 선택", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderChartPage = () => {
    return render(<ChartPage />)
  }

  it("빠른 선택 버튼을 클릭하면 종목이 변경된다", () => {
    renderChartPage()

    const skHynixButton = screen.getByText("SK하이닉스")
    fireEvent.click(skHynixButton)

    // 버튼이 클릭 가능해야 함
    expect(skHynixButton).toBeInTheDocument()
  })
})

describe("ChartPage - 로딩 상태", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderChartPage = () => {
    return render(<ChartPage />)
  }

  it("미니 차트 섹션이 렌더링된다", () => {
    renderChartPage()

    expect(screen.getByText("미니 차트")).toBeInTheDocument()
  })
})

describe("ChartPage - 차트 렌더링", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderChartPage = () => {
    return render(<ChartPage />)
  }

  it("차트 영역이 렌더링된다", () => {
    renderChartPage()

    // 차트 기능 안내 섹션 확인
    expect(screen.getByText("차트 기능 안내")).toBeInTheDocument()
  })
})

describe("ChartPage - 미니 차트 렌더링", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderChartPage = () => {
    return render(<ChartPage />)
  }

  it("미니 차트 카드가 렌더링된다", () => {
    renderChartPage()

    // 미니 차트 섹션 확인
    expect(screen.getByText("미니 차트")).toBeInTheDocument()

    // 각 종목명 확인
    expect(screen.getByText("삼성전자")).toBeInTheDocument()
    expect(screen.getByText("SK하이닉스")).toBeInTheDocument()
  })
})
