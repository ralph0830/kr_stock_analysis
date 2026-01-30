"use client";

import { useEffect, useMemo } from "react";
import { useStore } from "@/store";
import { useRealtimePrices } from "@/hooks/useWebSocket";
import { formatPrice, formatPercent, cn, getMarketGateColor, getGradeColor } from "@/lib/utils";
import type { MarketGateStatus, Signal, SectorItem } from "@/types";
import { RealtimePriceGrid, WebSocketStatus } from "@/components/RealtimePriceCard";
import { SystemHealthIndicator } from "@/components/SystemHealthIndicator";
import { ScanTriggerPanel } from "@/components/ScanTriggerPanel";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// 섹터 신호 색상 유틸리티
const getSectorColor = (signal: string) => {
  if (signal === "bullish") return "bg-green-500/20 text-green-700 border-green-500/30 dark:text-green-400";
  if (signal === "bearish") return "bg-red-500/20 text-red-700 border-red-500/30 dark:text-red-400";
  return "bg-yellow-500/20 text-yellow-700 border-yellow-500/30 dark:text-yellow-400";
};

// 백테스트 상태 배지
const BacktestStatusBadge = ({ status, message }: { status: string; message?: string }) => {
  if (status === "Accumulating") {
    return (
      <Badge variant="outline" className="bg-amber-500/10 text-amber-700 border-amber-500/20 dark:text-amber-400 animate-pulse">
        <span className="mr-1">⏳</span>축적 중
      </Badge>
    );
  }
  if (status === "No Data") {
    return (
      <Badge variant="outline" className="bg-gray-500/10 text-gray-700 border-gray-500/20 dark:text-gray-400">
        데이터 없음
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="bg-emerald-500/10 text-emerald-700 border-emerald-500/20 dark:text-emerald-400">
      <span className="mr-1">✓</span>정상
    </Badge>
  );
};

export default function DashboardPage() {
  const {
    signals,
    loadingSignals,
    marketGate,
    loadingMarketGate,
    backtestKPI,
    loadingBacktestKPI,
    fetchSignals,
    fetchMarketGate,
    fetchBacktestKPI,
  } = useStore();

  // 시그널 종목들의 실시간 가격 조회
  const signalTickers = useMemo(() => signals.map((s) => s.ticker), [signals]);
  const { prices, getPrice, connected: pricesConnected } = useRealtimePrices(signalTickers);

  useEffect(() => {
    fetchSignals();
    fetchMarketGate();
    fetchBacktestKPI();
  }, [fetchSignals, fetchMarketGate, fetchBacktestKPI]);

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
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <a
                href="/"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
              >
                ← 홈
              </a>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* 사이드바: 시스템 상태 + 스캔 제어 / 메인: Market Gate */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 왼쪽 사이드바 */}
          <div className="lg:col-span-1 space-y-6">
            <SystemHealthIndicator />
            <ScanTriggerPanel />
          </div>
          {/* 메인 영역 */}
          <div className="lg:col-span-3 space-y-6">
            {/* Market Gate Status */}
            <section>
              <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
                Market Gate 상태
              </h2>
              {loadingMarketGate ? (
                <Card>
                  <CardContent className="p-6 text-center">
                    <p className="text-gray-500">로딩 중...</p>
                  </CardContent>
                </Card>
              ) : marketGate ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 게이트 점수 카드 */}
                  <Card className={`border-l-4 ${getMarketGateColor(marketGate.status).replace("text-", "border-l-").split(" ")[0]}`}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm text-gray-500">Market Gate 레벨</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4">
                        <div className="text-4xl font-black text-gray-900 dark:text-gray-100">
                          {marketGate.level}
                        </div>
                        <Badge
                          variant="outline"
                          className={`text-lg px-3 py-1 ${getMarketGateColor(marketGate.status)}`}
                        >
                          {marketGate.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(marketGate.updated_at).toLocaleString("ko-KR")}
                      </p>
                    </CardContent>
                  </Card>

                  {/* KOSPI/KOSDAQ 카드 */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm text-gray-500">시장 지수</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">KOSPI</span>
                        <div className="flex items-center gap-2">
                          {marketGate.kospi_close && (
                            <span className="text-sm font-mono">
                              {marketGate.kospi_close.toLocaleString()}
                            </span>
                          )}
                          {marketGate.kospi_change_pct !== undefined && (
                            <span className={`text-sm font-medium ${marketGate.kospi_change_pct >= 0 ? "text-red-500" : "text-blue-500"}`}>
                              {marketGate.kospi_change_pct >= 0 ? "+" : ""}{marketGate.kospi_change_pct.toFixed(2)}%
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">KOSDAQ</span>
                        <div className="flex items-center gap-2">
                          {marketGate.kosdaq_close && (
                            <span className="text-sm font-mono">
                              {marketGate.kosdaq_close.toLocaleString()}
                            </span>
                          )}
                          {marketGate.kosdaq_change_pct !== undefined && (
                            <span className={`text-sm font-medium ${marketGate.kosdaq_change_pct >= 0 ? "text-red-500" : "text-blue-500"}`}>
                              {marketGate.kosdaq_change_pct >= 0 ? "+" : ""}{marketGate.kosdaq_change_pct.toFixed(2)}%
                            </span>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <Card>
                  <CardContent className="p-6 text-center">
                    <p className="text-red-500">Market Gate 정보를 불러올 수 없습니다.</p>
                  </CardContent>
                </Card>
              )}
            </section>

            {/* 섹터별 현황 */}
            {marketGate?.sectors && marketGate.sectors.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
                  섹터별 현황
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {marketGate.sectors.map((sector) => (
                    <Card
                      key={sector.name}
                      className={`border ${getSectorColor(sector.signal)} transition-all hover:scale-105`}
                    >
                      <CardContent className="p-3">
                        <div className="text-xs font-bold truncate mb-1">{sector.name}</div>
                        <div className={`text-lg font-black ${sector.change_pct >= 0 ? "text-red-500" : "text-blue-500"}`}>
                          {sector.change_pct >= 0 ? "+" : ""}{sector.change_pct.toFixed(2)}%
                        </div>
                        {sector.score !== undefined && (
                          <div className="text-[10px] text-gray-500 mt-1">
                            점수: {sector.score.toFixed(0)}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </section>
            )}
          </div>
        </div>

        {/* 백테스트 KPI 카드 */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
            백테스트 성과
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* VCP 전략 */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">VCP 전략</CardTitle>
                  {!loadingBacktestKPI && backtestKPI && (
                    <BacktestStatusBadge status={backtestKPI.vcp.status} message={backtestKPI.vcp.message} />
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {loadingBacktestKPI ? (
                  <p className="text-sm text-gray-500">로딩 중...</p>
                ) : backtestKPI ? (
                  <div className="space-y-2">
                    {backtestKPI.vcp.status === "OK" ? (
                      <>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                            {backtestKPI.vcp.win_rate?.toFixed(1)}%
                          </span>
                          <span className="text-sm text-gray-500">승률</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className={`text-lg font-semibold ${(backtestKPI.vcp.avg_return ?? 0) > 0 ? "text-red-500" : "text-blue-500"}`}>
                            {(backtestKPI.vcp.avg_return ?? 0) >= 0 ? "+" : ""}{backtestKPI.vcp.avg_return?.toFixed(2)}%
                          </span>
                          <span className="text-sm text-gray-500">평균 수익률</span>
                        </div>
                        <p className="text-xs text-gray-500">
                          총 {backtestKPI.vcp.count}건 백테스트
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-gray-500">
                        {backtestKPI.vcp.message || "데이터 축적 중"}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">데이터 없음</p>
                )}
              </CardContent>
            </Card>

            {/* 종가베팅 V2 전략 */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">종가베팅 V2</CardTitle>
                  {!loadingBacktestKPI && backtestKPI && (
                    <BacktestStatusBadge status={backtestKPI.closing_bet.status} message={backtestKPI.closing_bet.message} />
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {loadingBacktestKPI ? (
                  <p className="text-sm text-gray-500">로딩 중...</p>
                ) : backtestKPI ? (
                  <div className="space-y-2">
                    {backtestKPI.closing_bet.status === "OK" ? (
                      <>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                            {backtestKPI.closing_bet.win_rate?.toFixed(1)}%
                          </span>
                          <span className="text-sm text-gray-500">승률</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className={`text-lg font-semibold ${(backtestKPI.closing_bet.avg_return ?? 0) > 0 ? "text-red-500" : "text-blue-500"}`}>
                            {(backtestKPI.closing_bet.avg_return ?? 0) >= 0 ? "+" : ""}{backtestKPI.closing_bet.avg_return?.toFixed(2)}%
                          </span>
                          <span className="text-sm text-gray-500">평균 수익률</span>
                        </div>
                        <p className="text-xs text-gray-500">
                          총 {backtestKPI.closing_bet.count}건 백테스트
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-gray-500">
                        {backtestKPI.closing_bet.message || "데이터 축적 중"}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">데이터 없음</p>
                )}
              </CardContent>
            </Card>
          </div>
        </section>

        {/* 실시간 가격 모니터링 */}
        {realtimeTickers.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              실시간 가격 모니터링
            </h2>
            <RealtimePriceGrid stocks={realtimeTickers} />
          </section>
        )}

        {/* VCP Signals */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
            활성 VCP 시그널 {pricesConnected && <span className="text-sm text-green-500 ml-2">● 실시간</span>}
          </h2>
          {loadingSignals ? (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-gray-500">로딩 중...</p>
              </CardContent>
            </Card>
          ) : signals.length > 0 ? (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>티커</TableHead>
                    <TableHead>종목명</TableHead>
                    <TableHead>시그널</TableHead>
                    <TableHead>점수</TableHead>
                    <TableHead>등급</TableHead>
                    <TableHead className="text-right">현재가</TableHead>
                    <TableHead className="text-right">전일비</TableHead>
                    <TableHead className="text-right">등락률</TableHead>
                    <TableHead className="text-right">진입가</TableHead>
                    <TableHead className="text-right">목표가</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.map((signal) => {
                    const realtimePrice = getPrice(signal.ticker);
                    const isPositive = realtimePrice?.change ?? 0 > 0;
                    const isNegative = realtimePrice?.change ?? 0 < 0;

                    return (
                      <TableRow key={signal.ticker}>
                        <TableCell className="font-medium">{signal.ticker}</TableCell>
                        <TableCell>{signal.name}</TableCell>
                        <TableCell>{signal.signal_type}</TableCell>
                        <TableCell>
                          {typeof signal.score === "number"
                            ? signal.score.toFixed(1)
                            : signal.score?.total?.toFixed(1) ?? "0"}
                        </TableCell>
                        <TableCell>
                          <Badge className={getGradeColor(signal.grade)}>{signal.grade}</Badge>
                        </TableCell>
                        {/* 실시간 현재가 */}
                        <TableCell className="text-right font-medium">
                          {realtimePrice ? (
                            <span className={cn(
                              isPositive ? "text-red-600 dark:text-red-400" :
                              isNegative ? "text-blue-600 dark:text-blue-400" :
                              "text-gray-900 dark:text-gray-100"
                            )}>
                              {formatPrice(realtimePrice.price)}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </TableCell>
                        {/* 전일비 */}
                        <TableCell className="text-right">
                          {realtimePrice ? (
                            <span className={cn(
                              "font-medium",
                              isPositive ? "text-red-600 dark:text-red-400" :
                              isNegative ? "text-blue-600 dark:text-blue-400" :
                              "text-gray-600 dark:text-gray-400"
                            )}>
                              {isPositive ? "+" : ""}{formatPrice(realtimePrice.change)}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </TableCell>
                        {/* 등락률 */}
                        <TableCell className="text-right">
                          {realtimePrice ? (
                            <span className={cn(
                              "font-medium",
                              isPositive ? "text-red-600 dark:text-red-400" :
                              isNegative ? "text-blue-600 dark:text-blue-400" :
                              "text-gray-600 dark:text-gray-400"
                            )}>
                              {isPositive ? "+" : ""}{formatPercent(realtimePrice.change_rate)}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">{signal.entry_price ? formatPrice(signal.entry_price) : "-"}</TableCell>
                        <TableCell className="text-right">{signal.target_price ? formatPrice(signal.target_price) : "-"}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-gray-500">활성 시그널이 없습니다.</p>
              </CardContent>
            </Card>
          )}
        </section>

        {/* 챗봇 바로가기 */}
        <section>
          <Card className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-purple-200 dark:border-purple-800">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                    🤖 AI 주식 챗봇
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    주식 관련 질문을 하고 AI 답변을 받아보세요
                  </p>
                </div>
                <a
                  href="/chatbot"
                  className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition text-sm font-medium"
                >
                  챗봇 시작하기
                </a>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
