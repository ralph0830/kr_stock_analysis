import type { Metadata } from "next";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ralph Stock Analysis",
  description: "한국 주식 분석 시스템 - VCP 패턴, 종가베팅 V2 시그널",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="antialiased bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
