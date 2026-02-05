"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useStore } from "@/store";
import { useMarketGate, useRealtimePrices } from "@/hooks/useWebSocket";
import { formatPrice, formatPercent, getMarketGateColor, cn } from "@/lib/utils";
import { RealtimePriceGrid, WebSocketStatus } from "@/components/RealtimePriceCard";
import { Watchlist } from "@/components/Watchlist";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function HomePage() {
  const [showDashboard, setShowDashboard] = useState(false);

  const {
    signals,
    loadingSignals,
    fetchSignals,
  } = useStore();

  // Market Gate 실시간 WebSocket Hook 사용
  const { marketGate, isRealtime, connected, lastUpdate, loading: marketGateLoading, error: marketGateError, refetch: refetchMarketGate } = useMarketGate();

  // 실시간 가격 조회 (모든 시그널 종목에 대해 한 번만 호출)
  const signalTickers = useMemo(() => signals.map((s) => s.ticker), [signals]);
  const { getPrice, connected: pricesConnected } = useRealtimePrices(signalTickers);

  useEffect(() => {
    // 시그널 데이터 로드
    fetchSignals();
  }, [fetchSignals]);

  // 실시간 가격 모니터링할 종목 목록 (시그널 종목 중 상위 6개)
  const realtimeTickers = useMemo(() => {
    return signals.slice(0, 6).map((signal) => ({
      ticker: signal.ticker,
      name: signal.name,
    }));
  }, [signals]);

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                📊 Ralph Stock 대시보드
              </h1>
              <WebSocketStatus />
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/custom-recommendation"
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition text-sm font-medium"
              >
                단타 추천
              </Link>
              <ThemeToggle />
              <button
                onClick={() => setShowDashboard(!showDashboard)}
                aria-label={showDashboard ? "간단 보기로 전환" : "전체 보기로 전환"}
                aria-pressed={showDashboard}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
              >
                {showDashboard ? "간단 보기" : "전체 보기"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* 2단 레이아웃: 메인 컨텐츠 + 사이드바 */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 메인 컨텐츠 (3열) */}
          <div className="lg:col-span-3 space-y-8">
            {/* Market Gate Status - 실시간 WebSocket 업데이트 */}
            <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Market Gate 상태
            </h2>
            {/* 실시간 연결 상태 표시 */}
            {connected && (
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
                    isRealtime
                      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                      : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                  )}
                >
                  <span
                    className={cn(
                      "w-2 h-2 rounded-full mr-1.5",
                      isRealtime ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    )}
                  />
                  {isRealtime ? "실시간" : "연결 대기"}
                </span>
              </div>
            )}
          </div>

          {/* 에러 상태 */}
          {marketGateError ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
              <div className="text-center py-4">
                <AlertCircle className="w-8 h-8 text-yellow-500 mx-auto mb-3" />
                <p className="text-gray-900 dark:text-gray-100 font-medium mb-2">
                  Market Gate 정보를 불러올 수 없습니다
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  {marketGateError.message || "네트워크 연결을 확인해주세요"}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchMarketGate()}
                  className="mx-auto"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  다시 시도
                </Button>
              </div>
            </div>
          ) : marketGate ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">현재 상태</p>
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        "px-4 py-2 rounded-lg text-lg font-semibold",
                        getMarketGateColor(marketGate.status)
                      )}
                    >
                      {marketGate.status}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      레벨 {marketGate.level}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  {lastUpdate && (
                    <p className="text-sm text-gray-500">
                      {lastUpdate.toLocaleString("ko-KR")}
                    </p>
                  )}
                  {isRealtime ? (
                    <p className="text-xs text-green-600 dark:text-green-400">
                      WebSocket 실시간 업데이트
                    </p>
                  ) : !connected && (
                    <p className="text-xs text-yellow-600 dark:text-yellow-400">
                      API 폴링 모드
                    </p>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">KOSPI</p>
                  <div className="flex items-center gap-2">
                    {marketGate.kospi ? (
                      <>
                        <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {marketGate.kospi.toLocaleString()}
                        </span>
                        <span
                          className={cn(
                            "text-sm font-medium",
                            marketGate.kospi_change_pct && marketGate.kospi_change_pct >= 0
                              ? "text-red-600"
                              : "text-blue-600"
                          )}
                        >
                          {marketGate.kospi_change_pct && marketGate.kospi_change_pct >= 0 ? "+" : ""}
                          {marketGate.kospi_change_pct?.toFixed(2)}%
                        </span>
                      </>
                    ) : (
                      <span className="text-gray-400">데이터 없음</span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">KOSDAQ</p>
                  <div className="flex items-center gap-2">
                    {marketGate.kosdaq ? (
                      <>
                        <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {marketGate.kosdaq.toLocaleString()}
                        </span>
                        <span
                          className={cn(
                            "text-sm font-medium",
                            marketGate.kosdaq_change_pct && marketGate.kosdaq_change_pct >= 0
                              ? "text-red-600"
                              : "text-blue-600"
                          )}
                        >
                          {marketGate.kosdaq_change_pct && marketGate.kosdaq_change_pct >= 0 ? "+" : ""}
                          {marketGate.kosdaq_change_pct?.toFixed(2)}%
                        </span>
                      </>
                    ) : (
                      <span className="text-gray-400">데이터 없음</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg text-center">
              <p className="text-gray-500">Market Gate 정보를 불러오는 중...</p>
            </div>
          )}
        </section>

        {/* 실시간 가격 모니터링 */}
        {realtimeTickers.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              실시간 가격 모니터링
            </h2>
            <RealtimePriceGrid
              stocks={realtimeTickers}
              getPrice={getPrice}
              connected={pricesConnected}
            />
          </section>
        )}

        {/* VCP Signals (간단 버전) */}
        {!showDashboard && signals.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              활성 VCP 시그널 ({signals.length}개)
            </h2>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        티커
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        종목명
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        등급
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        점수
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {signals.map((signal) => (
                      <tr key={signal.ticker} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          {signal.ticker}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {signal.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                            {signal.grade}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {typeof signal.score === "number"
                            ? signal.score.toFixed(1)
                            : signal.score?.total?.toFixed(1) ?? "0"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {/* 전체 시그널 (확장 버전) */}
        {showDashboard && signals.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              전체 VCP 시그널 ({signals.length}개)
            </h2>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        티커
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        종목명
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        시그널
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        점수
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        등급
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        진입가
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        목표가
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {signals.map((signal) => (
                      <tr key={signal.ticker} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          {signal.ticker}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {signal.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {signal.signal_type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {typeof signal.score === "number"
                            ? signal.score.toFixed(1)
                            : signal.score?.total?.toFixed(1) ?? "0"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                            {signal.grade}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {signal.entry_price ? formatPrice(signal.entry_price) : "-"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                          {signal.target_price ? formatPrice(signal.target_price) : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {/* 안내 메시지 */}
        {signals.length === 0 && !loadingSignals && (
          <section className="text-center py-16">
            <p className="text-gray-500 dark:text-gray-400">
              현재 활성화된 시그널이 없습니다.
            </p>
          </section>
        )}

        {/* 차트 페이지 링크 */}
        <section>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow text-center">
            <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
              📊 차트 시각화 보기
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Recharts를 활용한 인터랙티브 가격 차트, 볼린저밴드, 거래량 차트를 확인하세요.
            </p>
            <a
              href="/chart"
              className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              차트 페이지로 이동
            </a>
          </div>
        </section>

        {/* 챗봇 링크 */}
        <section>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow text-center">
            <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
              🤖 AI 주식 챗봇
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              주식 관련 질문을 하고 AI 답변을 받아보세요. 종목 정보, 시장 상태, 시그널 추천 등을 지원합니다.
            </p>
            <a
              href="/chatbot"
              className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
            >
              챗봇 시작하기
            </a>
          </div>
        </section>
          </div>

          {/* 사이드바 (1열) */}
          <div className="lg:col-span-1 space-y-6">
            <Watchlist />
          </div>
        </div>
      </div>
    </main>
  );
}
