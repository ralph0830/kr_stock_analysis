# Frontend Fixes Report

**Date:** 2026-02-05
**URL:** https://stock.ralphpark.com
**Framework:** Next.js 14 (App Router)

---

## Executive Summary

이 보고서는 Ralph Stock Analysis 시스템의 프론트엔드를 전체적으로 테스트하고 발견한 문제점과 수정 제안을 정리한 것입니다.

**테스트 결과:**
- 전체 페이지 접근성: **PASS** (모든 페이지 200 OK 응답)
- API 엔드포인트: **PASS** (모든 API 200 OK 응답)
- WebSocket 연결: **ISSUE** (/ws 경로 404 응답 - NPM 설정 필요)
- 반응형 디자인: **PASS** (Tailwind CSS 사용)
- 접근성: **PARTIAL** (일부 개선 필요)

---

## Critical Issues

### 1. WebSocket Endpoint Configuration (CRITICAL)

**파일:** `/frontend/lib/api-client.ts`, `/frontend/hooks/useWebSocket.ts`
**라인:** `api-client.ts:44-67`, `useWebSocket.ts:122-145`

**문제점:**
```typescript
// 현재 구현
const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const isLocal = hostname === "localhost" || hostname === "127.0.0.1";

    if (!isLocal) {
      return `${protocol}//${hostname}`;
    }
    return `${protocol}//${hostname}:5111`;
  }
  return "http://api-gateway:5111";
};
```

WebSocket URL이 `/ws` 경로를 사용하지만, NPM(Nginx Proxy Manager) 설정이 필요합니다.

**증거:**
```bash
curl -I https://stock.ralphpark.com/ws
# HTTP/2 404
# server: openresty
```

**수정 제안:**

1. **NPM 리버스 프록시 설정 추가**
   ```nginx
   location /ws {
       proxy_pass http://localhost:5111/ws;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 86400;
   }
   ```

2. **또는 환경 변수 기반 WebSocket URL 사용**
   ```typescript
   const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultUrl;
   ```

**영향도:**
- 실시간 가격 업데이트 기능 불가
- Market Gate 실시간 업데이트 불가
- VCP 시그널 실시간 업데이트 불가

---

## High Priority Issues

### 2. Missing Page Title SEO Tags

**파일:** `/frontend/app/layout.tsx`
**라인:** `4-7`

**문제점:**
```typescript
export const metadata: Metadata = {
  title: "Ralph Stock Analysis",
  description: "한국 주식 분석 시스템 - VCP 패턴, 종가베팅 V2 시그널",
};
```

개별 페이지 메타데이터가 없어 SEO 최적화가 필요합니다.

**수정 제안:**
```typescript
// 각 페이지별 메타데이터 추가 예시
export async function generateMetadata({ params }): Promise<Metadata> {
  return {
    title: "KR Market Overview | Ralph Stock Analysis",
    description: "한국 주식 시장 개요 - Market Gate 상태, 섹터별 현황, VCP 시그널",
    openGraph: {
      title: "KR Market Overview",
      description: "실시간 한국 주식 시장 분석",
      url: "https://stock.ralphpark.com/dashboard/kr",
      siteName: "Ralph Stock Analysis",
      locale: "ko_KR",
      type: "website",
    },
  };
}
```

---

### 3. No Error Boundary for Client-Side Errors

**파일:** `/frontend/app/layout.tsx`, 페이지 컴포넌트들

**문제점:**
React Error Boundary가 구현되어 있지 않아 클라이언트 사이드 에러가 전체 앱을 중단시킬 수 있습니다.

**수정 제안:**
```typescript
// components/ErrorBoundary.tsx 생성
"use client";

import React from "react";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="min-h-screen flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-red-600 mb-4">
                오류가 발생했습니다
              </h1>
              <p className="text-gray-600 mb-4">
                {this.state.error?.message}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg"
              >
                새로고침
              </button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

// layout.tsx에서 사용
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="antialiased bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
```

---

## Medium Priority Issues

### 4. Accessibility Improvements Needed

**파일:** 여러 페이지 컴포넌트

**문제점:**
- `aria-label` 속석 누락 (버튼, 아이콘)
- 키보드 네비게이션 지원 부족
- 스크린 리더 지원 부족

**수정 제안:**

1. **버튼에 aria-label 추가**
   ```tsx
   // Bad
   <button onClick={handleRefresh}>
     <RefreshCw className="w-4 h-4" />
   </button>

   // Good
   <button
     onClick={handleRefresh}
     aria-label="새로고침"
     title="새로고침"
   >
     <RefreshCw className="w-4 h-4" />
   </button>
   ```

2. **대화형 요소에 키보드 지원 추가**
   ```tsx
   // 카드 클릭 가능하도록
   <div
     role="button"
     tabIndex={0}
     onKeyDown={(e) => e.key === "Enter" && handleClick()}
     onClick={handleClick}
     className="cursor-pointer"
   >
     ...
   </div>
   ```

3. **시각적 상태에 대한 aria-live 추가**
   ```tsx
   <div
     role="status"
     aria-live="polite"
     aria-label="WebSocket 연결 상태"
   >
     {connected ? "연결됨" : "연결 안됨"}
   </div>
   ```

---

### 5. Loading States Need Skeleton Screens

**파일:** `/frontend/app/dashboard/page.tsx`, `/frontend/app/dashboard/kr/page.tsx`

**문제점:**
로딩 상태가 단순한 텍스트("로딩 중...")로만 표시되어 UX가 저하됩니다.

**수정 제안:**
```tsx
// components/Skeleton.tsx 생성
export function TableSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="h-12 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          <div className="h-12 flex-1 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}

// 페이지에서 사용
{loading ? (
  <TableSkeleton />
) : (
  <Table>{/* ... */}</Table>
)}
```

---

### 6. Infinite Scroll Could Replace Pagination

**파일:** `/frontend/app/dashboard/kr/vcp/page.tsx`

**문제점:**
대량의 시그널 데이터를 한 번에 로드하면 성능 저하 가능성이 있습니다.

**수정 제안:**
```tsx
import { useInfiniteQuery } from "@tanstack/react-query";

// 무한 스크롤 구현
const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
} = useInfiniteQuery({
  queryKey: ["signals"],
  queryFn: ({ pageParam = 0 }) => fetchSignals(pageParam),
  getNextPageParam: (lastPage) => lastPage.nextPage,
});

// Intersection Observer로 스크롤 감지
const observer = useRef<IntersectionObserver>();

useEffect(() => {
  const element = document.querySelector("#sentinel");
  if (!element) return;

  observer.current = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && hasNextPage) {
      fetchNextPage();
    }
  });

  observer.current.observe(element);
  return () => observer.current?.disconnect();
}, [hasNextPage, fetchNextPage]);
```

---

## Low Priority Issues

### 7. Toast Notifications Not Implemented

**파일:** 전체 앱

**문제점:**
사용자 피드백(성공/실패 메시지)이 Toast로 구현되지 않았습니다.

**수정 제안:**
```typescript
// hooks/useToast.ts 생성
import { create } from "zustand";

interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info" | "warning";
}

interface ToastStore {
  toasts: Toast[];
  addToast: (message: string, type: Toast["type"]) => void;
  removeToast: (id: string) => void;
}

export const useToast = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (message, type) => {
    const id = Math.random().toString(36).slice(2);
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }));
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 3000);
  },
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
}));
```

---

### 8. Theme Toggle Animation Improvement

**파일:** `/frontend/components/ThemeToggle.tsx` (존재 여부 확인 필요)

**수정 제안:**
```tsx
// 부드러운 테마 전환 애니메이션
"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="relative w-14 h-8 rounded-full bg-gray-200 dark:bg-gray-700
                 transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
      aria-label="테마 전환"
    >
      <span
        className={`absolute top-1 left-1 w-6 h-6 rounded-full bg-white shadow-md
                    transform transition-transform duration-300
                    ${theme === "dark" ? "translate-x-6" : ""}`}
      >
        {theme === "dark" ? "?" : "??"}
      </span>
    </button>
  );
}
```

---

## Performance Optimizations

### 9. Image Optimization

**파일:** 전체 앱

**수정 제안:**
```tsx
import Image from "next/image";

// logo, favicon 등 최적화
<Image
  src="/logo.svg"
  alt="Ralph Stock Analysis"
  width={200}
  height={50}
  priority
/>
```

---

### 10. Bundle Size Optimization

**파일:** `next.config.mjs` (확인 필요)

**수정 제안:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 번들 사이즈 최적화
  modularizeImports: {
    "lucide-react": {
      transform: "lucide-react/dist/esm/icons/{{kebabCase member}}",
    },
  },

  // 압축
  compress: true,

  // SWC minification
  swcMinify: true,

  // 이미지 최적화
  images: {
    formats: ["image/webp", "image/avif"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
  },
};

module.exports = nextConfig;
```

---

## Security Considerations

### 11. Content Security Policy (CSP)

**파일:** `next.config.mjs`

**수정 제안:**
```javascript
const nextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self';",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval';",
              "style-src 'self' 'unsafe-inline';",
              "img-src 'self' data: blob:;",
              "font-src 'self' data:;",
              "connect-src 'self' ws://localhost:5111 wss://stock.ralphpark.com;",
            ].join(" "),
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
        ],
      },
    ];
  },
};
```

---

## Summary Table

| ID | Issue | Priority | File | Impact |
|----|-------|----------|------|--------|
| 1 | WebSocket Endpoint 404 | Critical | api-client.ts, useWebSocket.ts | 실시간 기능 불가 |
| 2 | Missing SEO Metadata | High | layout.tsx, page.tsx | 검색 엔진 노출 저하 |
| 3 | No Error Boundary | High | layout.tsx | 앱 전체 중단 가능 |
| 4 | Accessibility Gaps | Medium | 전체 컴포넌트 | WCAG 미준수 |
| 5 | Loading UX | Medium | page.tsx 파일들 | 사용자 경험 저하 |
| 6 | No Infinite Scroll | Medium | vcp/page.tsx | 대량 데이터 성능 |
| 7 | No Toast Notification | Low | 전체 앱 | 사용자 피드백 부족 |
| 8 | Theme Toggle UX | Low | ThemeToggle.tsx | 테마 전환 UX |
| 9 | Image Optimization | Low | 전체 앱 | 로딩 속도 |
| 10 | Bundle Size | Low | next.config.mjs | 초기 로딩 시간 |
| 11 | CSP Headers | Low | next.config.mjs | 보안 강화 |

---

## Testing Checklist Results

| Category | Test | Result | Notes |
|----------|------|--------|-------|
| Page Access | / (main) | PASS | 200 OK, 63ms |
| Page Access | /dashboard | PASS | 200 OK, 1058ms |
| Page Access | /dashboard/kr | PASS | 200 OK, 493ms |
| Page Access | /dashboard/kr/vcp | PASS | 200 OK, 694ms |
| Page Access | /custom-recommendation | PASS | 200 OK, 118ms |
| API | /api/kr/market-gate | PASS | 200 OK, 46ms |
| API | /api/kr/signals | PASS | 200 OK, 54ms |
| API | /api/kr/backtest-kpi | PASS | 200 OK, 60ms |
| API | /api/daytrading/signals | PASS | 200 OK, 57ms |
| WebSocket | /ws endpoint | FAIL | 404 Not Found (NPM 설정 필요) |

---

## Recommendations

1. **즉시 조치:** WebSocket NPM 리버스 프록시 설정 (Issue #1)
2. **단계적 개선:** Error Boundary 구현 후 SEO 메타데이터 추가
3. **장기 계획:** 접근성 개선 및 무한 스크롤 구현

---

*Report generated by Claude Code - Frontend Architecture Analysis*
