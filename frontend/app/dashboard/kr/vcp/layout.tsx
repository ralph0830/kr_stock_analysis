import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "VCP Signals | Ralph Stock Analysis",
  description: "VCP(Volatility Contraction Pattern) 시그널 - 변동성 축소 패턴을 감지한 종목을 실시간으로 확인하세요. 외국인/기관 수급, 수축률 분석 제공.",
  openGraph: {
    title: "VCP Signals | Ralph Stock Analysis",
    description: "실시간 VCP 패턴 시그널 - 변동성 축소 패턴 분석",
    url: "https://stock.ralphpark.com/dashboard/kr/vcp",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function VCPLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
