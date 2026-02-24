/**
 * Client Body Wrapper
 *
 * layout.tsx의 body를 Client Component로 래핑하여
 * Toast와 같은 클라이언트 기능을 사용할 수 있게 합니다.
 */

"use client"

import { ReactNode } from "react"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ToastProvider as RadixToastProvider } from "@/components/ui/toast"
import { Toaster } from "@/components/ui/toaster"

interface ClientBodyProps {
  children: ReactNode
}

export function ClientBody({ children }: ClientBodyProps) {
  return (
    <RadixToastProvider>
      <ErrorBoundary>{children}</ErrorBoundary>
      <Toaster />
    </RadixToastProvider>
  )
}
