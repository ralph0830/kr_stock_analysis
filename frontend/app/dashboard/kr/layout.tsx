import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "KR Market Overview | Ralph Stock Analysis",
  description: "한국 주식 시장 개요 - Market Gate 레벨, KOSPI/KOSDAQ 지수, 섹터별 현황, 백테스트 KPI를 실시간으로 확인하세요.",
  openGraph: {
    title: "KR Market Overview | Ralph Stock Analysis",
    description: "실시간 한국 주식 시장 분석 - Market Gate, 섹터별 현황",
    url: "https://stock.ralphpark.com/dashboard/kr",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function KRMarketLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
