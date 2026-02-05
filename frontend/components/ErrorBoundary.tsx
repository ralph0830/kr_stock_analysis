"use client";

import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

/**
 * 클라이언트 사이드 에러를 캡처하는 Error Boundary 컴포넌트
 *
 * - 자식 컴포넌트 트리에서 발생하는 JavaScript 에러를 캡처
 * - 에러 발생 시 Fallback UI를 렌더링
 * - 에러 정보 로깅 (개발 환경)
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // 에러 상태 업데이트 (다음 렌더링에서 Fallback UI 표시)
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // 에러 로깅
    if (process.env.NODE_ENV === "development") {
      console.error("[ErrorBoundary] 에러 발생:", error);
      console.error("[ErrorBoundary] 컴포넌트 스택:", errorInfo.componentStack);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // 커스텀 Fallback이 있으면 사용
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 기본 Fallback UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 text-center">
            {/* 에러 아이콘 */}
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            {/* 에러 메시지 */}
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              오류가 발생했습니다
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {this.state.error?.message || "알 수 없는 오류가 발생했습니다."}
            </p>

            {/* 개발 환경에서만 스택 트레이스 표시 */}
            {process.env.NODE_ENV === "development" && this.state.error?.stack && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                  에러 상세보기
                </summary>
                <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-900 rounded-lg text-xs overflow-auto max-h-40 text-gray-700 dark:text-gray-300">
                  {this.state.error.stack}
                </pre>
              </details>
            )}

            {/* 액션 버튼 */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition text-sm font-medium"
              >
                다시 시도
              </button>
              <button
                onClick={this.handleReload}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
              >
                페이지 새로고침
              </button>
            </div>

            {/* 홈으로 이동 링크 */}
            <a
              href="/"
              className="inline-block mt-4 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            >
              홈으로 이동
            </a>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
