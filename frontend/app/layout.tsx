import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KR Stock Analysis",
  description: "한국 주식 분석 시스템 - VCP 패턴, 종가베팅 V2 시그널",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
