import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "시그널 검색 | Ralph Stock Analysis",
  description: "VCP 시그널, 종가베팅 V2 시그널 검색 - 종목명, 티커, 시그널 타입, 등급으로 필터링하여 원하는 시그널를 찾아보세요.",
  openGraph: {
    title: "시그널 검색 | Ralph Stock Analysis",
    description: "VCP, 종가베팅 V2 시그널 검색 및 필터링",
    url: "https://stock.ralphpark.com/signals",
    siteName: "Ralph Stock Analysis",
    locale: "ko_KR",
    type: "website",
  },
};

export default function SignalsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
