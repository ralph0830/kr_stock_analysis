/**
 * 테스트 헬퍼 함수
 * Recharts 컴포넌트 Mock 및 테스트 유틸리티
 */

import { ReactNode } from "react"

/**
 * Recharts 컴포넌트 Mock
 * 테스트 시 실제 차트 렌더링 대신 Mock 사용
 */

export function mockRechartsComponents() {
  return {
    ResponsiveContainer: ({ children, width, height }: {
      children: ReactNode
      width?: number | string
      height?: number | string
    }) => (
      <div
        data-testid="recharts-responsive-container"
        style={{ width: width || '100%', height: height || 400 }}
      >
        {children}
      </div>
    ),
    LineChart: ({ children, data }: {
      children: ReactNode
      data: any[]
    }) => (
      <div data-testid="recharts-line-chart" data-points={data.length}>
        {children}
      </div>
    ),
    AreaChart: ({ children, data }: {
      children: ReactNode
      data: any[]
    }) => (
      <div data-testid="recharts-area-chart" data-points={data.length}>
        {children}
      </div>
    ),
    BarChart: ({ children, data }: {
      children: ReactNode
      data: any[]
    }) => (
      <div data-testid="recharts-bar-chart" data-points={data.length}>
        {children}
      </div>
    ),
    ComposedChart: ({ children, data }: {
      children: ReactNode
      data: any[]
    }) => (
      <div data-testid="recharts-composed-chart" data-points={data.length}>
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
        data-testid={`recharts-line-${dataKey}`}
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
        data-testid={`recharts-area-${dataKey}`}
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
        data-testid={`recharts-bar-${dataKey}`}
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
        data-testid="recharts-x-axis"
        data-key={dataKey}
        className="recharts-x-axis"
      />
    ),
    YAxis: ({ domain, tickFormatter }: {
      domain?: [number, number]
      tickFormatter?: (value: any) => string
    }) => (
      <div
        data-testid="recharts-y-axis"
        data-domain={domain ? domain.join(',') : undefined}
        className="recharts-y-axis"
      />
    ),
    CartesianGrid: ({ strokeDasharray }: { strokeDasharray?: string | number }) => (
      <div
        data-testid="recharts-cartesian-grid"
        data-stroke-dasharray={strokeDasharray}
        className="recharts-grid"
      />
    ),
    Tooltip: ({ content }: { content?: any }) => (
      <div data-testid="recharts-tooltip" className="recharts-tooltip" />
    ),
    Legend: () => (
      <div data-testid="recharts-legend" className="recharts-legend" />
    ),
    ReferenceLine: ({ label }: { label?: string }) => (
      <div
        data-testid="recharts-reference-line"
        data-label={label}
        className="recharts-reference-line"
      />
    ),
  }
}

/**
 * 테스트용 더미 데이터 생성기
 */

export function createRandomPrice(
  base: number = 80000,
  range: number = 2000
): number {
  return Math.round(base + (Math.random() - 0.5) * range)
}

export function createRandomVolume(
  base: number = 10000000,
  range: number = 5000000
): number {
  return Math.round(base + (Math.random() - 0.5) * range)
}

/**
 * 날짜 범위 생성
 */
export function createDateRange(
  days: number,
  startDate?: Date
): string[] {
  const start = startDate || new Date()
  const dates: string[] = []

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(start)
    date.setDate(date.getDate() - i)
    dates.push(date.toISOString().split('T')[0])
  }

  return dates
}

/**
 * 테스트 결과 검증 헬퍼
 */

export function expectValidPriceData(data: any) {
  expect(data).toHaveProperty('date')
  expect(data).toHaveProperty('close')
  expect(data).toHaveProperty('volume')
  expect(typeof data.date).toBe('string')
  expect(typeof data.close).toBe('number')
  expect(typeof data.volume).toBe('number')
  expect(data.close).toBeGreaterThan(0)
  expect(data.volume).toBeGreaterThanOrEqual(0)
}

export function expectValidFlowData(data: any) {
  expect(data).toHaveProperty('date')
  expect(data).toHaveProperty('foreign_net')
  expect(data).toHaveProperty('inst_net')
  expect(typeof data.date).toBe('string')
  expect(typeof data.foreign_net).toBe('number')
  expect(typeof data.inst_net).toBe('number')
}

/**
 * 비동기 테스트 대기 헬퍼
 */
export function waitFor(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Mock API 클라이언트 응답 지연
 */
export function delayResponse<T>(data: T, ms: number = 100): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(data), ms))
}

/**
 * Recharts 컴포넌트 Mock 설정 (vi.mock 사용 시)
 */
export const rechartsMock = {
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children, data }: { children: ReactNode; data: any[] }) => (
    <div data-testid="line-chart" data-points={data.length}>{children}</div>
  ),
  AreaChart: ({ children, data }: { children: ReactNode; data: any[] }) => (
    <div data-testid="area-chart" data-points={data.length}>{children}</div>
  ),
  BarChart: ({ children, data }: { children: ReactNode; data: any[] }) => (
    <div data-testid="bar-chart" data-points={data.length}>{children}</div>
  ),
  ComposedChart: ({ children, data }: { children: ReactNode; data: any[] }) => (
    <div data-testid="composed-chart" data-points={data.length}>{children}</div>
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
}
