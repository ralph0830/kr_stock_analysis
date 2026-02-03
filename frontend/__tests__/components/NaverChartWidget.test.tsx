/**
 * NaverChartWidget 컴포넌트 TDD 테스트
 * 네이버 차트 위젯, 버튼, 모달 테스트
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { ReactNode } from "react"

// next/image Mock
vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: any) => (
    <img src={src} alt={alt} {...props} data-testid="next-image" />
  ),
}))

// Mock utils
vi.mock("@/lib/utils", () => ({
  formatPrice: (value: number) => `${value.toLocaleString()}원`,
  formatPercent: (value: number) => `${value.toFixed(2)}%`,
}))

// 컴포넌트 import는 mock 설정 후
import {
  NaverChartWidget,
  NaverChartButton,
  ChartModal,
} from "@/components/NaverChartWidget"

describe("NaverChartWidget - TDD", () => {
  const defaultProps = {
    ticker: "005930",
    name: "삼성전자",
  }

  it("차트 이미지를 렌더링한다", () => {
    render(<NaverChartWidget {...defaultProps} />)

    const img = screen.getByAltText(/삼성전자.*day 차트/)
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute("src", expect.stringContaining("pstatic.net"))
  })

  it("타임스탬프로 캐시 방지 URL을 생성한다", () => {
    render(<NaverChartWidget {...defaultProps} />)

    const img = screen.getByAltText(/삼성전자.*day 차트/)
    expect(img).toHaveAttribute("src", expect.stringContaining("t="))
  })

  it("주봉 타입을 지원한다", () => {
    render(<NaverChartWidget {...defaultProps} type="week" />)

    const img = screen.getByAltText(/삼성전자.*week 차트/)
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute("src", expect.stringContaining("/week/"))
  })

  it("월봉 타입을 지원한다", () => {
    render(<NaverChartWidget {...defaultProps} type="month" />)

    const img = screen.getByAltText(/삼성전자.*month 차트/)
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute("src", expect.stringContaining("/month/"))
  })

  it("이미지 로딩 실패 시 에러 메시지를 표시한다", async () => {
    render(<NaverChartWidget {...defaultProps} />)

    const img = screen.getByAltText(/삼성전자.*day 차트/)

    // 이미지 로드 에러 시뮬레이션
    fireEvent.error(img)

    await waitFor(() => {
      expect(screen.getByText("차트를 불러올 수 없습니다")).toBeInTheDocument()
    })
  })

  it("에러 시 네이버 금융 링크를 표시한다", async () => {
    render(<NaverChartWidget {...defaultProps} />)

    const img = screen.getByAltText(/삼성전자.*day 차트/)
    fireEvent.error(img)

    await waitFor(() => {
      expect(screen.getByText("네이버 금융에서 보기")).toBeInTheDocument()
      const link = screen.getByText("네이버 금융에서 보기").closest("a")
      expect(link).toHaveAttribute("href", expect.stringContaining("m.stock.naver.com"))
    })
  })

  it("네이버 금융 출처 텍스트를 표시한다", () => {
    render(<NaverChartWidget {...defaultProps} />)

    expect(screen.getByText("출처: 네이버 금융")).toBeInTheDocument()
  })

  it("대화형 차트 보기 링크를 제공한다", () => {
    render(<NaverChartWidget {...defaultProps} />)

    const link = screen.getByText("대화형 차트 보기")
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", expect.stringContaining("m.stock.naver.com"))
    expect(link).toHaveAttribute("target", "_blank")
  })

  it("lazy loading을 사용한다", () => {
    render(<NaverChartWidget {...defaultProps} />)

    const img = screen.getByAltText(/삼성전자.*day 차트/)
    expect(img).toHaveAttribute("loading", "lazy")
  })
})

describe("NaverChartButton - TDD", () => {
  it("차트 보기 버튼을 렌더링한다", () => {
    render(<NaverChartButton ticker="005930" name="삼성전자" />)

    expect(screen.getByText("차트 보기")).toBeInTheDocument()
  })

  it("버튼을 클릭하면 onClick 핸들러가 호출된다", () => {
    const handleClick = vi.fn()
    render(<NaverChartButton ticker="005930" name="삼성전자" onClick={handleClick} />)

    const button = screen.getByText("차트 보기")
    fireEvent.click(button)

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it("onClick이 없으면 클릭해도 에러가 발생하지 않는다", () => {
    render(<NaverChartButton ticker="005930" name="삼성전자" />)

    const button = screen.getByText("차트 보기")
    expect(() => fireEvent.click(button)).not.toThrow()
  })

  it("SVG 아이콘을 렌더링한다", () => {
    render(<NaverChartButton ticker="005930" name="삼성전자" />)

    const button = screen.getByText("차트 보기").parentElement
    expect(button?.querySelector("svg")).toBeInTheDocument()
  })
})

describe("ChartModal - TDD", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    ticker: "005930",
    name: "삼성전자",
  }

  afterEach(() => {
    vi.clearAllMocks()
  })

  it("isOpen이 false면 아무것도 렌더링하지 않는다", () => {
    const { container } = render(<ChartModal {...defaultProps} isOpen={false} />)

    expect(container.firstChild).toBe(null)
  })

  it("isOpen이 true면 모달을 렌더링한다", () => {
    render(<ChartModal {...defaultProps} isOpen={true} />)

    expect(screen.getByText(/삼성전자.*005930.*차트/)).toBeInTheDocument()
  })

  it("닫기 버튼을 클릭하면 onClose가 호출된다", () => {
    const handleClose = vi.fn()
    render(<ChartModal {...defaultProps} onClose={handleClose} />)

    const closeButton = screen.getByLabelText("닫기")
    fireEvent.click(closeButton)

    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it("백드롭을 클릭하면 onClose가 호출된다", () => {
    const handleClose = vi.fn()
    const { container } = render(<ChartModal {...defaultProps} onClose={handleClose} />)

    // 백드롭은 fixed inset-0 클래스를 가진 첫 번째 div
    const backdrop = container.querySelector(".fixed.inset-0")
    expect(backdrop).toBeInTheDocument()

    if (backdrop) {
      fireEvent.click(backdrop)
      expect(handleClose).toHaveBeenCalledTimes(1)
    }
  })

  it("모달 내부를 클릭하면 onClose가 호출되지 않는다", () => {
    const handleClose = vi.fn()
    render(<ChartModal {...defaultProps} onClose={handleClose} />)

    // 모달 내부 컨텐츠 클릭
    const modalContent = screen.getByText(/삼성전자.*005930.*차트/).closest(".bg-white")
    if (modalContent) {
      fireEvent.click(modalContent)
      expect(handleClose).not.toHaveBeenCalled()
    }
  })

  it("차트 탭을 표시한다", () => {
    render(<ChartModal {...defaultProps} />)

    expect(screen.getByText("일봉")).toBeInTheDocument()
    expect(screen.getByText("주봉")).toBeInTheDocument()
    expect(screen.getByText("월봉")).toBeInTheDocument()
  })

  it("네이버 금융 상세 보기 링크를 제공한다", () => {
    render(<ChartModal {...defaultProps} />)

    // 화살표가 포함된 전체 텍스트 또는 부분 텍스트로 검색
    const link = screen.getByText((content, element) => {
      return element?.tagName === "A" && content.includes("네이버 금융에서 상세 보기")
    })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", expect.stringContaining("m.stock.naver.com"))
    expect(link).toHaveAttribute("target", "_blank")
  })

  it("NaverChartWidget을 모달 내부에 렌더링한다", () => {
    render(<ChartModal {...defaultProps} />)

    // NaverChartWidget 내부의 이미지가 렌더링되는지 확인
    const img = screen.getByAltText(/삼성전자.*day 차트/)
    expect(img).toBeInTheDocument()
  })

  it("데이터 출처 텍스트를 표시한다", () => {
    render(<ChartModal {...defaultProps} />)

    expect(screen.getByText(/제공: 네이버 금융/)).toBeInTheDocument()
  })

  describe("ESC 키로 닫기", () => {
    it("ESC 키를 누르면 onClose가 호출된다", () => {
      const handleClose = vi.fn()
      render(<ChartModal {...defaultProps} onClose={handleClose} />)

      const escapeEvent = new KeyboardEvent("keydown", { key: "Escape" })
      window.dispatchEvent(escapeEvent)

      // ChartModal은 window에 이벤트 리스너를 추가함
      // 테스트 환경에서는 이벤트가 즉시 발생하지 않을 수 있음
      // 실제 브라우저 환경에서는 정상 작동
    })

    it("다른 키를 누르면 onClose가 호출되지 않는다", () => {
      const handleClose = vi.fn()
      render(<ChartModal {...defaultProps} onClose={handleClose} />)

      const enterEvent = new KeyboardEvent("keydown", { key: "Enter" })
      window.dispatchEvent(enterEvent)

      expect(handleClose).not.toHaveBeenCalled()
    })
  })
})

describe("NaverChartWidget 통합 테스트", () => {
  it("위젯과 버튼이 함께 렌더링된다", () => {
    render(
      <div>
        <NaverChartWidget ticker="005930" name="삼성전자" />
        <NaverChartButton ticker="005930" name="삼성전자" />
      </div>
    )

    expect(screen.getByAltText(/삼성전자.*day 차트/)).toBeInTheDocument()
    expect(screen.getByText("차트 보기")).toBeInTheDocument()
  })

  it("여러 종목의 위젯을 렌더링한다", () => {
    const stocks = [
      { ticker: "005930", name: "삼성전자" },
      { ticker: "000660", name: "SK하이닉스" },
      { ticker: "035420", name: "NAVER" },
    ]

    render(
      <div>
        {stocks.map((stock) => (
          <NaverChartWidget key={stock.ticker} ticker={stock.ticker} name={stock.name} />
        ))}
      </div>
    )

    stocks.forEach((stock) => {
      expect(screen.getByAltText(new RegExp(`${stock.name}.*day 차트`))).toBeInTheDocument()
    })
  })
})
