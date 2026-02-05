import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "차트 분석 | Ralph Stock Analysis",
  description: "종목별 차트 분석 - 캔들 차트, VCP 패턴 마크, 이동평균선, 거래량을 한눈에 확인하세요.",
  openGraph: {
    title: "차트 분석 | Ralph Stock Analysis",
    description: "종목별 기술적 분석 차트",
    url: "https://stock.ralphpark.com/chart",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function ChartLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
