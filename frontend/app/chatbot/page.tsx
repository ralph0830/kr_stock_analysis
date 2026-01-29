/**
 * AI 챗봇 페이지
 */
"use client"

import { ChatbotWidget } from "@/components/ChatbotWidget"
import { ThemeToggle } from "@/components/ThemeToggle"
import Link from "next/link"

export default function ChatbotPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                🤖 AI 주식 챗봇
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Link
                href="/"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
              >
                ← 홈
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* 안내 */}
          <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <h2 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
              주식 관련 질문을 해주세요!
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              AI 챗봇이 다음과 같은 질문에 답변해 드립니다.
            </p>
            <ul className="grid md:grid-cols-2 gap-2 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex items-center gap-2">
                <span className="text-blue-500">•</span>
                특정 종목의 현재가 및 실시간 가격
              </li>
              <li className="flex items-center gap-2">
                <span className="text-blue-500">•</span>
                VCP/종가베팅 시그널 종목 추천
              </li>
              <li className="flex items-center gap-2">
                <span className="text-blue-500">•</span>
                현재 시장 상태 (Market Gate)
              </li>
              <li className="flex items-center gap-2">
                <span className="text-blue-500">•</span>
                종목별 기본 정보 및 섹터
              </li>
            </ul>
          </div>

          {/* 챗봇 위젯 */}
          <ChatbotWidget />
        </div>
      </div>
    </main>
  )
}
