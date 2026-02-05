import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "종가베팅 V2 | Ralph Stock Analysis",
  description: "종가베팅 V2 시그널 - 12가지 체크리스트 기반 종가 매수 전략. 당일 종가에 매수하여 다음 날 상승을 노리는 단타 전략.",
  openGraph: {
    title: "종가베팅 V2 | Ralph Stock Analysis",
    description: "종가베팅 V2 시그널 - 12가지 체크리스트 기반 종가 매수 전략",
    url: "https://stock.ralphpark.com/dashboard/kr/closing-bet",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function ClosingBetLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
