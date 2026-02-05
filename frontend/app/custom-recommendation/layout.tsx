import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "단타 추천 | Ralph Stock Analysis",
  description: "AI 기반 단타 추천 시스템 - 7가지 체크리스트(시가 상승률, 거래량 급증, 외국인/기관 수급, VCP 패턴 등)를 분석하여 당실매수 종목을 추천합니다.",
  openGraph: {
    title: "단타 추천 | Ralph Stock Analysis",
    description: "AI 기반 단타 추천 - 7가지 체크리스트 분석",
    url: "https://stock.ralphpark.com/custom-recommendation",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function CustomRecommendationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
