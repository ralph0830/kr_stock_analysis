/**
 * 빈 상태 UI 공통 컴포넌트
 * 데이터가 없을 때 사용자에게 안내와 액션을 제공
 */
"use client"

import { Button } from "@/components/ui/button"
import { LucideIcon } from "lucide-react"

interface EmptyStateProps {
  /** 아이콘 컴포넌트 */
  icon?: LucideIcon
  /** 제목 */
  title: string
  /** 설명 */
  description?: string
  /** CTA 버튼 텍스트 */
  actionText?: string
  /** CTA 버튼 클릭 핸들러 */
  onAction?: () => void
  /** 로딩 상태 */
  loading?: boolean
  /** 추가 CSS 클래스 */
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
  loading = false,
  className = "",
}: EmptyStateProps) {
  return (
    <div className={`text-center space-y-4 py-8 ${className}`}>
      {Icon && (
        <div className="flex justify-center">
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full">
            <Icon className="w-8 h-8 text-gray-400" />
          </div>
        </div>
      )}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
          {title}
        </h3>
        {description && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {description}
          </p>
        )}
      </div>
      {actionText && onAction && (
        <Button
          onClick={onAction}
          disabled={loading}
          className="mt-2"
          aria-label={loading ? `${actionText} 중` : actionText}
        >
          {Icon && <Icon className={`w-4 h-4 mr-2 ${loading ? "animate-pulse" : ""}`} />}
          {loading ? `${actionText} 중...` : actionText}
        </Button>
      )}
    </div>
  )
}
