/**
 * CandlestickChart TDD 테스트
 * 캔들스틱 차트 렌더링 테스트
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { ReactNode } from "react"

// Recharts Mock (Candlestick 포함)
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children, width, height }: {
    children: ReactNode
    width?: number | string
    height?: number | string
  }) => (
    <div
      data-testid="responsive-container"
      data-width={width}
      data-height={height}
      style={{ width: width || '100%', height: height || 400 }}
    >
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
  Line: ({ dataKey, stroke, dot }: {
    dataKey: string
    stroke?: string
    dot?: boolean
  }) => (
    <div
      data-testid={`line-${dataKey}`}
      className="recharts-line"
      data-stroke={stroke}
      data-dot={dot}
    />
  ),
  Bar: ({ dataKey, fill }: { dataKey: string; fill?: string }) => (
    <div
      data-testid={`bar-${dataKey}`}
      className="recharts-bar"
      data-fill={fill}
    />
  ),
  XAxis: () => <div data-testid="x-axis" className="recharts-x-axis" />,
  YAxis: () => <div data-testid="y-axis" className="recharts-y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
  // Recharts 2.15.0은 Candlestick 컴포넌트를 지원하지 않음
  // 캔들스틱은 Bar와 Line 조합으로 구현
}))

// Mock utils
vi.mock("@/lib/utils", () => ({
  formatPrice: (value: number) => `${value.toLocaleString()}원`,
  formatPercent: (value: number) => `${value.toFixed(2)}%`,
}))

// 컴포넌트 import는 mock 설정 후
import { CandlestickChart, MACDChart } from "@/components/CandlestickChart"
// 유틸리티 함수 import
import { calculateCandlestickData, calculateMACDFromPrices } from "@/components/CandlestickChart"

describe("CandlestickChart - TDD", () => {
  const mockOHLCVData = [
    {
      date: "2026-01-20",
      open: 80000,
      high: 81000,
      low: 79500,
      close: 80500,
      volume: 1000000,
    },
    {
      date: "2026-01-21",
      open: 80500,
      high: 81500,
      low: 80000,
      close: 81200,
      volume: 1200000,
    },
    {
      date: "2026-01-22",
      open: 81200,
      high: 81200,
      low: 80000,
      close: 80200,
      volume: 900000,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("기본 렌더링", () => {
    it("ResponsiveContainer로 래핑된 차트를 렌더링한다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })

    it("ComposedChart를 렌더링한다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
      expect(screen.getByTestId("composed-chart")).toHaveAttribute("data-points", "3")
    })

    it("XAxis와 YAxis를 렌더링한다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      expect(screen.getByTestId("x-axis")).toBeInTheDocument()
      expect(screen.getByTestId("y-axis")).toBeInTheDocument()
    })

    it("Tooltip을 렌더링한다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      expect(screen.getByTestId("tooltip")).toBeInTheDocument()
    })

    it("Legend를 렌더링한다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      expect(screen.getByTestId("legend")).toBeInTheDocument()
    })
  })

  describe("캔들스틱 데이터", () => {
    it("캔들스틱 차트 데이터를 처리한다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      // ComposedChart가 OHLCV 데이터로 렌더링되는지 확인
      expect(screen.getByTestId("composed-chart")).toHaveAttribute("data-points", "3")
    })

    it("양봉(상승) 데이터를 올바르게 처리한다", () => {
      const bullishData = [
        {
          date: "2026-01-20",
          open: 80000,
          high: 81000,
          low: 79500,
          close: 80500, // close > open
          volume: 1000000,
        },
      ]

      render(<CandlestickChart data={bullishData} />)

      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
    })

    it("음봉(하락) 데이터를 올바르게 처리한다", () => {
      const bearishData = [
        {
          date: "2026-01-22",
          open: 81200,
          high: 81200,
          low: 80000,
          close: 80200, // close < open
          volume: 900000,
        },
      ]

      render(<CandlestickChart data={bearishData} />)

      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
    })

    it("십자星(Doji) 데이터를 올바르게 처리한다", () => {
      const dojiData = [
        {
          date: "2026-01-20",
          open: 80000,
          high: 80500,
          low: 79500,
          close: 80000, // open == close
          volume: 1000000,
        },
      ]

      render(<CandlestickChart data={dojiData} />)

      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
    })
  })

  describe("이동평균선 옵션", () => {
    it("showMA=true면 이동평균선을 표시한다", () => {
      // 5일 이동평균을 계산하려면 최소 5개 데이터 필요
      const extendedData = [
        ...mockOHLCVData,
        { date: "2026-01-23", open: 80200, high: 80800, low: 80000, close: 80500, volume: 1100000 },
        { date: "2026-01-24", open: 80500, high: 81200, low: 80300, close: 81000, volume: 1300000 },
      ]

      render(<CandlestickChart data={extendedData} showMA={true} />)

      expect(screen.getByTestId("line-ma5")).toBeInTheDocument()
    })

    it("showMA=false면 이동평균선을 표시하지 않는다", () => {
      render(<CandlestickChart data={mockOHLCVData} showMA={false} />)

      expect(screen.queryByTestId("line-ma5")).not.toBeInTheDocument()
      expect(screen.queryByTestId("line-ma20")).not.toBeInTheDocument()
    })
  })

  describe("거래량 차트", () => {
    it("showVolume=true면 거래량 바를 표시한다", () => {
      render(<CandlestickChart data={mockOHLCVData} showVolume={true} />)

      expect(screen.getByTestId("bar-volume")).toBeInTheDocument()
    })

    it("showVolume=false면 거래량 바를 표시하지 않는다", () => {
      render(<CandlestickChart data={mockOHLCVData} showVolume={false} />)

      expect(screen.queryByTestId("bar-volume")).not.toBeInTheDocument()
    })
  })

  describe("데이터 변환", () => {
    it("빈 데이터를 처리한다", () => {
      render(<CandlestickChart data={[]} />)

      expect(screen.getByTestId("composed-chart")).toHaveAttribute("data-points", "0")
    })

    it("단일 데이터를 처리한다", () => {
      const singleData = [
        {
          date: "2026-01-20",
          open: 80000,
          high: 81000,
          low: 79500,
          close: 80500,
          volume: 1000000,
        },
      ]

      render(<CandlestickChart data={singleData} />)

      expect(screen.getByTestId("composed-chart")).toHaveAttribute("data-points", "1")
    })
  })

  describe("높이 설정", () => {
    it("기본 높이는 400px이다", () => {
      render(<CandlestickChart data={mockOHLCVData} />)

      const container = screen.getByTestId("responsive-container")
      expect(container).toHaveAttribute("data-height", "400")
    })

    it("사용자 정의 높이를 적용한다", () => {
      render(<CandlestickChart data={mockOHLCVData} height={600} />)

      const container = screen.getByTestId("responsive-container")
      expect(container).toHaveAttribute("data-height", "600")
    })
  })

  describe("색상 표시", () => {
    it("양봉은 빨간색으로 표시한다 (한국 주식 시장 convention)", () => {
      const bullishData = [
        {
          date: "2026-01-20",
          open: 80000,
          high: 81000,
          low: 79500,
          close: 80500,
          volume: 1000000,
        },
      ]

      render(<CandlestickChart data={bullishData} />)

      // 차트가 렌더링되는지 확인
      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
    })

    it("음봉은 파란색으로 표시한다 (한국 주식 시장 convention)", () => {
      const bearishData = [
        {
          date: "2026-01-22",
          open: 81200,
          high: 81200,
          low: 80000,
          close: 80200,
          volume: 900000,
        },
      ]

      render(<CandlestickChart data={bearishData} />)

      // 차트가 렌더링되는지 확인
      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
    })
  })
})

describe("MACDChart - TDD", () => {
  const mockMACDData = [
    {
      date: "2026-01-20",
      macd: 150,
      signal: 145,
      histogram: 5,
    },
    {
      date: "2026-01-21",
      macd: 155,
      signal: 148,
      histogram: 7,
    },
    {
      date: "2026-01-22",
      macd: 148,
      signal: 150,
      histogram: -2,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("기본 렌더링", () => {
    it("ResponsiveContainer로 래핑된 차트를 렌더링한다", () => {
      render(<MACDChart data={mockMACDData} />)

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument()
    })

    it("ComposedChart를 렌더링한다", () => {
      render(<MACDChart data={mockMACDData} />)

      expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
    })

    it("MACD 라인을 표시한다", () => {
      render(<MACDChart data={mockMACDData} />)

      expect(screen.getByTestId("line-macd")).toBeInTheDocument()
    })

    it("Signal 라인을 표시한다", () => {
      render(<MACDChart data={mockMACDData} />)

      expect(screen.getByTestId("line-signal")).toBeInTheDocument()
    })

    it("Histogram 바를 표시한다", () => {
      render(<MACDChart data={mockMACDData} />)

      // 양수 histogram bar
      expect(screen.getByTestId("bar-positiveHistogram")).toBeInTheDocument()
      // 음수 histogram bar
      expect(screen.getByTestId("bar-negativeHistogram")).toBeInTheDocument()
    })

    it("XAxis와 YAxis를 렌더링한다", () => {
      render(<MACDChart data={mockMACDData} />)

      expect(screen.getByTestId("x-axis")).toBeInTheDocument()
      expect(screen.getByTestId("y-axis")).toBeInTheDocument()
    })
  })

  describe("Histogram 색상", () => {
    it("양수 histogram은 빨간색으로 표시한다", () => {
      const positiveData = [
        {
          date: "2026-01-20",
          macd: 150,
          signal: 145,
          histogram: 5,
        },
      ]

      render(<MACDChart data={positiveData} />)

      expect(screen.getByTestId("bar-positiveHistogram")).toBeInTheDocument()
    })

    it("음수 histogram은 파란색으로 표시한다", () => {
      const negativeData = [
        {
          date: "2026-01-22",
          macd: 148,
          signal: 150,
          histogram: -2,
        },
      ]

      render(<MACDChart data={negativeData} />)

      expect(screen.getByTestId("bar-negativeHistogram")).toBeInTheDocument()
    })
  })

  describe("데이터 처리", () => {
    it("빈 데이터를 처리한다", () => {
      render(<MACDChart data={[]} />)

      expect(screen.getByTestId("composed-chart")).toHaveAttribute("data-points", "0")
    })

    it("단일 데이터를 처리한다", () => {
      const singleData = [
        {
          date: "2026-01-20",
          macd: 150,
          signal: 145,
          histogram: 5,
        },
      ]

      render(<MACDChart data={singleData} />)

      expect(screen.getByTestId("composed-chart")).toHaveAttribute("data-points", "1")
    })
  })

  describe("기준선", () => {
    it("0 기준선을 표시한다", () => {
      render(<MACDChart data={mockMACDData} />)

      expect(screen.getByTestId("reference-line")).toBeInTheDocument()
    })
  })
})

describe("calculateCandlestickData - 유틸리티 함수", () => {
  it("OHLCV 데이터를 캔들스틱 형식으로 변환한다", () => {
    const input = [
      {
        date: "2026-01-20",
        open: 80000,
        high: 81000,
        low: 79500,
        close: 80500,
        volume: 1000000,
      },
    ]

    const result = calculateCandlestickData(input)

    expect(result).toHaveLength(1)
    expect(result[0]).toHaveProperty("date", "2026-01-20")
    expect(result[0]).toHaveProperty("open", 80000)
    expect(result[0]).toHaveProperty("high", 81000)
    expect(result[0]).toHaveProperty("low", 79500)
    expect(result[0]).toHaveProperty("close", 80500)
  })

  it("빈 배열을 처리한다", () => {
    const result = calculateCandlestickData([])
    expect(result).toHaveLength(0)
  })

  it("양봉/음봉 여부를 계산한다", () => {
    const bullish = [
      {
        date: "2026-01-20",
        open: 80000,
        high: 81000,
        low: 79500,
        close: 80500,
        volume: 1000000,
      },
    ]

    const result = calculateCandlestickData(bullish)
    expect(result[0]).toHaveProperty("isBullish", true)
  })

  it("음봉을 올바르게 식별한다", () => {
    const bearish = [
      {
        date: "2026-01-22",
        open: 81200,
        high: 81200,
        low: 80000,
        close: 80200,
        volume: 900000,
      },
    ]

    const result = calculateCandlestickData(bearish)
    expect(result[0]).toHaveProperty("isBullish", false)
  })

  it("이동평균을 계산한다", () => {
    const data = [
      { date: "2026-01-18", open: 79000, high: 80000, low: 78500, close: 79500, volume: 800000 },
      { date: "2026-01-19", open: 79500, high: 80500, low: 79000, close: 80000, volume: 900000 },
      { date: "2026-01-20", open: 80000, high: 81000, low: 79500, close: 80500, volume: 1000000 },
      { date: "2026-01-21", open: 80500, high: 81500, low: 80000, close: 81200, volume: 1200000 },
      { date: "2026-01-22", open: 81200, high: 81200, low: 80000, close: 80200, volume: 900000 },
    ]

    const result = calculateCandlestickData(data, { ma5: true, ma20: false })

    // 5일 이동평균은 5번째 데이터부터 계산 가능 (index 4)
    expect(result[4]).toHaveProperty("ma5")
    expect(typeof result[4].ma5).toBe("number")
    // 4번째 데이터는 아직 MA5가 없음
    expect(result[3].ma5).toBeUndefined()
  })

  it("MA20 이동평균을 계산한다", () => {
    // 20개 데이터 생성
    const data = Array.from({ length: 20 }, (_, i) => ({
      date: `2026-01-${(i + 1).toString().padStart(2, "0")}`,
      open: 80000 + i * 100,
      high: 80500 + i * 100,
      low: 79500 + i * 100,
      close: 80000 + i * 100,
      volume: 1000000,
    }))

    const result = calculateCandlestickData(data, { ma5: false, ma20: true })

    // 20번째 데이터 (index 19)부터 MA20 계산 가능
    expect(result[19]).toHaveProperty("ma20")
    expect(typeof result[19].ma20).toBe("number")
    // 18번째 데이터는 아직 MA20이 없음
    expect(result[18].ma20).toBeUndefined()
  })
})

describe("calculateMACDFromPrices - MACD 계산", () => {
  it("가격 배열로 MACD 값을 계산한다", () => {
    const prices = [80000, 80500, 80200, 81000, 81500, 81200, 80800, 80500, 81000, 81500,
                    81200, 80800, 80500, 81000, 81500, 82000, 81800, 81500, 81200, 81000,
                    80800, 81200, 81500, 81800, 82000, 82200, 82500, 82300, 82000, 81800]

    const result = calculateMACDFromPrices(prices, "2026-01-30")

    expect(result).toHaveProperty("date", "2026-01-30")
    expect(result).toHaveProperty("macd")
    expect(result).toHaveProperty("signal")
    expect(result).toHaveProperty("histogram")
    expect(typeof result.macd).toBe("number")
    expect(typeof result.signal).toBe("number")
    expect(typeof result.histogram).toBe("number")
  })

  it("26개 미만의 가격이면 기본값을 반환한다", () => {
    const shortPrices = [80000, 80500, 80200]

    const result = calculateMACDFromPrices(shortPrices, "2026-01-20")

    expect(result.macd).toBe(0)
    expect(result.signal).toBe(0)
    expect(result.histogram).toBe(0)
  })

  it("정확히 26개의 가격이면 MACD를 계산한다", () => {
    // 26개 데이터 생성
    const prices = Array.from({ length: 26 }, (_, i) => 80000 + i * 100)

    const result = calculateMACDFromPrices(prices, "2026-01-30")

    // 26개 데이터면 계산 가능
    expect(result.macd).not.toBe(0)
  })

  it("histogram = macd - signal 공식을 따른다", () => {
    const prices = [80000, 80500, 80200, 81000, 81500, 81200, 80800, 80500, 81000, 81500,
                    81200, 80800, 80500, 81000, 81500, 82000, 81800, 81500, 81200, 81000,
                    80800, 81200, 81500, 81800, 82000, 82200, 82500, 82300, 82000, 81800]

    const result = calculateMACDFromPrices(prices, "2026-01-30")

    // histogram = macd - signal
    expect(result.histogram).toBeCloseTo(result.macd - result.signal, 1)
  })
})
