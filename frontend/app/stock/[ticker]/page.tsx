/**
 * 종목 상세 페이지
 * 동적 라우팅으로 종목별 상세 정보 표시
 */
import { StockDetail } from "@/components/StockDetail"
import { ThemeToggle } from "@/components/ThemeToggle"

interface PageProps {
  params: Promise<{
    ticker: string
  }>
}

export default async function StockPage({ params }: PageProps) {
  const { ticker } = await params

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <a href="/signals" className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100">
              ← 시그널 목록
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="container mx-auto px-4 py-8">
        <StockDetail ticker={ticker} />
      </div>
    </main>
  )
}
