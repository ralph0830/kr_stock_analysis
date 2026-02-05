import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "대시보드 | Ralph Stock Analysis",
  description: "한국 주식 시장 대시보드 - Market Gate 상태, VCP 시그널, 종가베팅 V2 시그널, 백테스트 성과를 한눈에 확인하세요.",
  openGraph: {
    title: "대시보드 | Ralph Stock Analysis",
    description: "실시간 한국 주식 시장 분석 대시보드",
    url: "https://stock.ralphpark.com/dashboard",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
