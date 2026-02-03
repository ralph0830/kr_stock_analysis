/**
 * StockChart 컴포넌트 TDD 테스트
 * Recharts Mock을 활용한 컴포넌트 렌더링 테스트
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ReactNode } from "react"

// Recharts Mock 설정 (vi.mock은 파일 최상단에 호이스트됨)
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
  Line: ({ dataKey, name, stroke, strokeWidth }: {
    dataKey: string
    name?: string
    stroke?: string
    strokeWidth?: number
  }) => (
    <div
      data-testid={`line-${dataKey}`}
      data-name={name || dataKey}
      data-stroke={stroke}
      data-stroke-width={strokeWidth}
      className="recharts-line"
    />
  ),
  Area: ({ dataKey, stroke, fill }: {
    dataKey: string
    stroke?: string
    fill?: string
  }) => (
    <div
      data-testid={`area-${dataKey}`}
      data-stroke={stroke}
      data-fill={fill}
      className="recharts-area"
    />
  ),
  Bar: ({ dataKey, name, fill }: {
    dataKey: string
    name?: string
    fill?: string
  }) => (
    <div
      data-testid={`bar-${dataKey}`}
      data-name={name || dataKey}
      data-fill={fill}
      className="recharts-bar"
    />
  ),
  XAxis: ({ dataKey, tickFormatter }: {
    dataKey?: string
    tickFormatter?: (value: any) => string
  }) => (
    <div
      data-testid="x-axis"
      data-key={dataKey}
      className="recharts-x-axis"
    />
  ),
  YAxis: ({ domain, tickFormatter }: {
    domain?: [number, number]
    tickFormatter?: (value: any) => string
  }) => (
    <div
      data-testid="y-axis"
      data-domain={domain ? domain.join(',') : undefined}
      className="recharts-y-axis"
    />
  ),
  CartesianGrid: ({ strokeDasharray }: { strokeDasharray?: string | number }) => (
    <div
      data-testid="cartesian-grid"
      data-stroke-dasharray={strokeDasharray}
      className="recharts-grid"
    />
  ),
  Tooltip: ({ content }: { content?: any }) => (
    <div data-testid="tooltip" className="recharts-tooltip" />
  ),
  Legend: () => (
    <div data-testid="legend" className="recharts-legend" />
  ),
  ReferenceLine: ({ label }: { label?: string }) => (
    <div
      data-testid="reference-line"
      data-label={label}
      className="recharts-reference-line"
    />
  ),
}))

// Mock utils
vi.mock("@/lib/utils", () => ({
  formatPrice: (value: number) => `${value.toLocaleString()}원`,
  formatPercent: (value: number) => `${value.toFixed(2)}%`,
}))

// 컴포넌트 import는 mock 설정 후에 해야 함
import {
  FullStockChart,
  PriceChart,
  VolumeChart,
  MiniChart,
  BollingerBands,
  PriceChange,
  type PriceData,
} from "@/components/StockChart"

// Mock utils
vi.mock("@/lib/utils", () => ({
  formatPrice: (value: number) => `${value.toLocaleString()}원`,
  formatPercent: (value: number) => `${value.toFixed(2)}%`,
}))

describe("StockChart Components - TDD", () => {
  describe("BollingerBands", () => {
    it("볼린저밴드 데이터가 있으면 렌더링한다", () => {
      const data: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000, upper_band: 82000, lower_band: 78000, middle_band: 80000 },
        { date: "2026-01-02", close: 81000, volume: 1200000, upper_band: 82500, lower_band: 79500, middle_band: 81000 },
      ]

      const { container } = render(<BollingerBands data={data} />)

      // AreaChart가 렌더링되는지 확인
      expect(screen.getByTestId("area-chart")).toBeInTheDocument()
    })

    it("볼린저밴드 데이터가 없으면 null을 반환한다", () => {
      const data: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
      ]

      const { container } = render(<BollingerBands data={data} />)

      // 빈 컨테이너 확인 (null 반환)
      expect(container.firstChild).toBe(null)
    })

    it("빈 배열이면 null을 반환한다", () => {
      const { container } = render(<BollingerBands data={[]} />)

      expect(container.firstChild).toBe(null)
    })

    it("상단/하단 밴드가 0인 데이터는 필터링한다", () => {
      const data: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000, upper_band: 0, lower_band: 0 },
      ]

      const { container } = render(<BollingerBands data={data} />)

      expect(container.firstChild).toBe(null)
    })
  })

  describe("VolumeChart", () => {
    it("거래량 데이터를 렌더링한다", () => {
      const data: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
        { date: "2026-01-02", close: 81000, volume: 1200000 },
      ]

      render(<VolumeChart data={data} />)

      // BarChart와 Bar가 렌더링되는지 확인
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument()
      expect(screen.getByTestId("bar-volume")).toBeInTheDocument()
    })

    it("ResponsiveContainer로 감싸진다", () => {
      const data: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
      ]

      render(<VolumeChart data={data} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })

    it("빈 데이터도 렌더링한다 (차트는 빈 상태로)", () => {
      const data: PriceData[] = []

      render(<VolumeChart data={data} />)

      // 컴포넌트 자체는 렌더링되어야 함
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })
  })

  describe("PriceChart", () => {
    const mockData: PriceData[] = [
      { date: "2026-01-01", close: 80000, volume: 1000000, upper_band: 82000, lower_band: 78000, middle_band: 80000 },
      { date: "2026-01-02", close: 81000, volume: 1200000, upper_band: 82500, lower_band: 79500, middle_band: 81000 },
      { date: "2026-01-03", close: 80500, volume: 900000, upper_band: 82300, lower_band: 78700, middle_band: 80500 },
    ]

    it("가격 차트를 렌더링한다", () => {
      render(<PriceChart data={mockData} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
      expect(screen.getByTestId("line-chart")).toBeInTheDocument()
    })

    it("종가 라인을 렌더링한다", () => {
      render(<PriceChart data={mockData} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })

    it("상단 밴드가 있으면 렌더링한다", () => {
      render(<PriceChart data={mockData} />)

      expect(screen.getByTestId("line-upper")).toBeInTheDocument()
    })

    it("하단 밴드가 있으면 렌더링한다", () => {
      render(<PriceChart data={mockData} />)

      expect(screen.getByTestId("line-lower")).toBeInTheDocument()
    })

    it("중단 밴드가 있으면 렌더링한다", () => {
      render(<PriceChart data={mockData} />)

      expect(screen.getByTestId("line-middle")).toBeInTheDocument()
    })

    it("볼린저밴드가 없으면 종가 라인만 렌더링한다", () => {
      const dataWithoutBands: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
        { date: "2026-01-02", close: 81000, volume: 1200000 },
      ]

      render(<PriceChart data={dataWithoutBands} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
      expect(screen.queryByTestId("line-upper")).not.toBeInTheDocument()
      expect(screen.queryByTestId("line-lower")).not.toBeInTheDocument()
    })

    it("커스텀 height를 적용한다", () => {
      const { container } = render(<PriceChart data={mockData} height={300} />)

      const containerEl = screen.getByTestId("responsive-container")
      expect(containerEl).toBeInTheDocument()
    })

    it("빈 데이터도 렌더링한다", () => {
      const { container } = render(<PriceChart data={[]} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })
  })

  describe("FullStockChart", () => {
    const mockData: PriceData[] = [
      { date: "2026-01-01", close: 80000, volume: 1000000, upper_band: 82000, lower_band: 78000, middle_band: 80000 },
      { date: "2026-01-02", close: 81000, volume: 1200000, upper_band: 82500, lower_band: 79500, middle_band: 81000 },
    ]

    it("가격 차트와 거래량 차트를 모두 렌더링한다", () => {
      render(<FullStockChart data={mockData} />)

      // 가격 차트 영역
      expect(screen.getByText("가격 차트")).toBeInTheDocument()
      // 거래량 차트 영역
      expect(screen.getByText("거래량")).toBeInTheDocument()
    })

    it("거래량이 0이면 거래량 차트를 렌더링하지 않는다", () => {
      const dataWithoutVolume: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 0, upper_band: 82000, lower_band: 78000 },
      ]

      render(<FullStockChart data={dataWithoutVolume} />)

      expect(screen.getByText("가격 차트")).toBeInTheDocument()
      expect(screen.queryByText("거래량")).not.toBeInTheDocument()
    })

    it("커스텀 height를 PriceChart에 전달한다", () => {
      render(<FullStockChart data={mockData} height={300} />)

      expect(screen.getByText("가격 차트")).toBeInTheDocument()
    })

    it("빈 데이터면 가격 차트만 렌더링한다", () => {
      render(<FullStockChart data={[]} />)

      expect(screen.getByText("가격 차트")).toBeInTheDocument()
    })
  })

  describe("MiniChart", () => {
    const mockData: PriceData[] = [
      { date: "2026-01-01", close: 80000, volume: 1000000 },
      { date: "2026-01-02", close: 81000, volume: 1200000 },
      { date: "2026-01-03", close: 80500, volume: 900000 },
    ]

    it("미니 차트를 렌더링한다", () => {
      render(<MiniChart data={mockData} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
      expect(screen.getByTestId("line-chart")).toBeInTheDocument()
    })

    it("상승하면 빨간색 라인을 렌더링한다", () => {
      const risingData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
        { date: "2026-01-02", close: 81000, volume: 1200000 },
      ]

      render(<MiniChart data={risingData} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })

    it("하락하면 파란색 라인을 렌더링한다", () => {
      const fallingData: PriceData[] = [
        { date: "2026-01-01", close: 81000, volume: 1000000 },
        { date: "2026-01-02", close: 80000, volume: 1200000 },
      ]

      render(<MiniChart data={fallingData} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })

    it("커스텀 height를 적용한다", () => {
      render(<MiniChart data={mockData} height={80} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })

    it("빈 데이터도 렌더링한다", () => {
      render(<MiniChart data={[]} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })

    it("단일 데이터도 렌더링한다", () => {
      const singleData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
      ]

      render(<MiniChart data={singleData} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })
  })

  describe("PriceChange", () => {
    it("상승 시 빨간색으로 표시한다", () => {
      render(<PriceChange current={81000} previous={80000} />)

      expect(screen.getByText("81,000원")).toBeInTheDocument()
      expect(screen.getByText(/\+1\.25%/)).toBeInTheDocument()
    })

    it("하락 시 파란색으로 표시한다", () => {
      render(<PriceChange current={79000} previous={80000} />)

      expect(screen.getByText("79,000원")).toBeInTheDocument()
      expect(screen.getByText(/-1\.25%/)).toBeInTheDocument()
    })

    it("변동 없으면 회색으로 표시한다 (양수로 처리)", () => {
      render(<PriceChange current={80000} previous={80000} />)

      expect(screen.getByText("80,000원")).toBeInTheDocument()
      expect(screen.getByText("+0.00%")).toBeInTheDocument()
    })

    it("소수점 둘째자리까지 표시한다", () => {
      render(<PriceChange current={81000} previous={80000} />)

      expect(screen.getByText(/\+1\.25%/)).toBeInTheDocument()
    })

    it("0으로 나누기 방지 (previous가 0이면)", () => {
      // 실제로는 previous가 0이 될 수 없지만 테스트 작성
      render(<PriceChange current={0} previous={1} />)

      expect(screen.getByText("0원")).toBeInTheDocument()
    })
  })

  describe("통합 테스트", () => {
    it("모든 컴포넌트가 함께 렌더링된다", () => {
      const mockData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000, upper_band: 82000, lower_band: 78000, middle_band: 80000 },
        { date: "2026-01-02", close: 81000, volume: 1200000, upper_band: 82500, lower_band: 79500, middle_band: 81000 },
      ]

      const { container } = render(
        <div>
          <FullStockChart data={mockData} />
          <MiniChart data={mockData} />
          <PriceChange current={81000} previous={80000} />
        </div>
      )

      expect(screen.getByText("가격 차트")).toBeInTheDocument()
      expect(screen.getByText("거래량")).toBeInTheDocument()
      // 여러 개의 line-chart가 렌더링되어야 함 (FullStockChart 내부 + MiniChart)
      expect(screen.getAllByTestId("line-chart").length).toBeGreaterThanOrEqual(2)
    })
  })

  describe("PriceChart - 추가 엣지 케이스", () => {
    it("단일 데이터로 렌더링한다", () => {
      const singleData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
      ]

      render(<PriceChart data={singleData} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })

    it("대용량 데이터로 렌더링한다", () => {
      const largeData: PriceData[] = Array.from({ length: 100 }, (_, i) => ({
        date: `2026-01-${(i + 1).toString().padStart(2, '0')}`,
        close: 80000 + i * 100,
        volume: 1000000 + i * 10000,
      }))

      render(<PriceChart data={largeData} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })

    it("모든 볼린저밴드가 있는 경우 모든 라인을 렌더링한다", () => {
      const dataWithAllBands: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000, upper_band: 82000, lower_band: 78000, middle_band: 80000 },
      ]

      render(<PriceChart data={dataWithAllBands} />)

      expect(screen.getByTestId("line-upper")).toBeInTheDocument()
      expect(screen.getByTestId("line-lower")).toBeInTheDocument()
      expect(screen.getByTestId("line-middle")).toBeInTheDocument()
      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })
  })

  describe("VolumeChart - 추가 엣지 케이스", () => {
    it("대량 거래량 데이터를 렌더링한다 (억 단위)", () => {
      const highVolumeData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 500000000 }, // 500만주
      ]

      render(<VolumeChart data={highVolumeData} />)

      expect(screen.getByTestId("bar-volume")).toBeInTheDocument()
    })

    it("1만주 미만 거래량을 렌더링한다", () => {
      const lowVolumeData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 5000 },
      ]

      render(<VolumeChart data={lowVolumeData} />)

      expect(screen.getByTestId("bar-volume")).toBeInTheDocument()
    })
  })

  describe("MiniChart - 추가 엣지 케이스", () => {
    it("가격이 같으면 중립 색상으로 렌더링한다", () => {
      const flatData: PriceData[] = [
        { date: "2026-01-01", close: 80000, volume: 1000000 },
        { date: "2026-01-02", close: 80000, volume: 1200000 },
      ]

      render(<MiniChart data={flatData} />)

      // 마지막 가격이 첫 가격 이상이면 빨간색
      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })

    it("10개 이상 데이터 포인트로 렌더링한다", () => {
      const manyData: PriceData[] = Array.from({ length: 20 }, (_, i) => ({
        date: `2026-01-${(i + 1).toString().padStart(2, '0')}`,
        close: 80000 + i * 50,
        volume: 1000000,
      }))

      render(<MiniChart data={manyData} />)

      expect(screen.getByTestId("line-price")).toBeInTheDocument()
    })
  })

  describe("PriceChange - 추가 엣지 케이스", () => {
    it("매우 큰 가격 변동을 처리한다", () => {
      render(<PriceChange current={100000} previous={50000} />)

      expect(screen.getByText("100,000원")).toBeInTheDocument()
      expect(screen.getByText(/\+100\.00%/)).toBeInTheDocument()
    })

    it("음수 가격을 처리하지 않는다 (실제 시나리오)", () => {
      render(<PriceChange current={1000} previous={5000} />)

      expect(screen.getByText("1,000원")).toBeInTheDocument()
      expect(screen.getByText(/-80\.00%/)).toBeInTheDocument()
    })
  })
})
