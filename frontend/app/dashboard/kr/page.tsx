"use client";

import { useEffect, useState, useMemo } from "react";
import { apiClient } from "@/lib/api-client";
import type { MarketGateStatus, SectorItem, IBacktestKPI } from "@/types";

/**
 * 원형 프로그레스 컴포넌트 (Market Gate Level)
 */
function CircularProgress({
  value,
  max = 100,
  size = 120,
  strokeWidth = 8,
  status
}: {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  status: "GREEN" | "YELLOW" | "RED";
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const progress = Math.min(value / max, 1);
  const offset = circumference - progress * circumference;

  // 상태별 색상
  const getColor = () => {
    switch (status) {
      case "GREEN": return "#10b981"; // emerald-500
      case "YELLOW": return "#f59e0b"; // amber-500
      case "RED": return "#ef4444"; // red-500
      default: return "#6b7280"; // gray-500
    }
  };

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-200 dark:text-gray-700"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {value}
        </span>
        <span className="text-xs text-gray-500">/ {max}</span>
      </div>
    </div>
  );
}

/**
 * 섹터 카드 컴포넌트
 */
function SectorCard({ sector }: { sector: SectorItem }) {
  const isBullish = sector.signal === "bullish";
  const isBearish = sector.signal === "bearish";

  const bgClass = isBullish
    ? "bg-green-500/10 border-green-500/20"
    : isBearish
    ? "bg-red-500/10 border-red-500/20"
    : "bg-gray-500/10 border-gray-500/20";

  const iconClass = isBullish
    ? "text-green-500"
    : isBearish
    ? "text-red-500"
    : "text-gray-500";

  const icon = isBullish ? "▲" : isBearish ? "▼" : "─";

  return (
    <div
      className={`p-4 rounded-xl border ${bgClass} hover:shadow-md transition-shadow cursor-pointer`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {sector.name}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${iconClass} bg-white/50 dark:bg-black/20`}>
          {icon}
        </span>
      </div>
      <div className="flex items-center justify-between">
        <span className={`text-lg font-bold ${isBullish ? "text-green-600 dark:text-green-400" : isBearish ? "text-red-600 dark:text-red-400" : "text-gray-600"}`}>
          {sector.change_pct > 0 ? "+" : ""}{sector.change_pct.toFixed(1)}%
        </span>
        {sector.score !== undefined && (
          <span className="text-xs text-gray-500">
            점수: {sector.score}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * KPI 카드 컴포넌트
 */
function KPICard({
  title,
  value,
  subtitle,
  icon,
  trend
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  trend?: "up" | "down" | "neutral";
}) {
  const trendColor = trend === "up" ? "text-green-500" : trend === "down" ? "text-red-500" : "text-gray-500";
  const trendIcon = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {value}
        </span>
        {trend && (
          <span className={`text-sm ${trendColor}`}>{trendIcon}</span>
        )}
      </div>
      {subtitle && (
        <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
      )}
    </div>
  );
}

/**
 * 백테스트 상태 표시
 */
function BacktestStats({
  stats,
  label
}: {
  stats: IBacktestStatsItem;
  label: string;
}) {
  const isAccumulating = stats.status === "Accumulating";
  const isNoData = stats.status === "No Data";

  const statusColor = isAccumulating
    ? "text-yellow-500"
    : isNoData
    ? "text-gray-500"
    : "text-green-500";

  const statusBg = isAccumulating
    ? "bg-yellow-500/10"
    : isNoData
    ? "bg-gray-500/10"
    : "bg-green-500/10";

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">{label}</h3>
        <span className={`text-xs px-2 py-1 rounded-full ${statusBg} ${statusColor}`}>
          {stats.status}
        </span>
      </div>
      {stats.status === "OK" && (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">건수</span>
            <p className="font-semibold text-gray-900 dark:text-gray-100">{stats.count}</p>
          </div>
          <div>
            <span className="text-gray-500">승률</span>
            <p className="font-semibold text-green-600">{stats.win_rate?.toFixed(1)}%</p>
          </div>
          <div>
            <span className="text-gray-500">수익률</span>
            <p className="font-semibold text-blue-600">{stats.avg_return?.toFixed(1)}%</p>
          </div>
          <div>
            <span className="text-gray-500">PF</span>
            <p className="font-semibold text-purple-600">{stats.profit_factor?.toFixed(2)}</p>
          </div>
        </div>
      )}
      {(isAccumulating || isNoData) && (
        <p className="text-sm text-gray-500">{stats.message || "데이터 수집 중..."}</p>
      )}
    </div>
  );
}

/**
 * 백테스트 스탯 아이템 타입
 */
interface IBacktestStatsItem {
  strategy: string;
  status: "OK" | "Accumulating" | "No Data";
  count: number;
  win_rate?: number;
  avg_return?: number;
  profit_factor?: number;
  message?: string;
}

export default function KROverviewPage() {
  const [marketGate, setMarketGate] = useState<MarketGateStatus | null>(null);
  const [backtestKPI, setBacktestKPI] = useState<IBacktestKPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  // 데이터 로드
  const loadData = async () => {
    try {
      const [gateRes, backtestRes] = await Promise.all([
        apiClient.getMarketGate(),
        apiClient.getBacktestKPI(),
      ]);
      setMarketGate(gateRes);
      setBacktestKPI(backtestRes);
      setLastUpdated(new Date().toLocaleTimeString("ko-KR"));
    } catch (error) {
      console.error("Failed to load KR overview data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // 1분마다 데이터 갱신
    const interval = setInterval(loadData, 60000);
    return () => clearInterval(interval);
  }, []);

  // 섹터 정렬 (변화률 순)
  const sortedSectors = useMemo(() => {
    if (!marketGate?.sectors) return [];
    return [...marketGate.sectors].sort((a, b) => b.change_pct - a.change_pct);
  }, [marketGate]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="container mx-auto px-4 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-16 text-center shadow">
            <div className="inline-flex items-center gap-3">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-600 dark:text-gray-400">한국 시장 개요를 불러오는 중...</p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                KR Market Overview
              </h1>
              <span className="px-2 py-1 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 text-xs font-medium">
                한국 주식 시장
              </span>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={loadData}
                className="px-3 py-1.5 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
              >
                리프레시
              </button>
              <a
                href="/dashboard"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
              >
                ← 대시보드
              </a>
            </div>
          </div>
          {lastUpdated && (
            <p className="text-xs text-gray-500 mt-2">마지막 업데이트: {lastUpdated}</p>
          )}
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Market Gate 상태 섹션 */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
            Market Gate 상태
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Market Gate 원형 프로그레스 */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-lg flex flex-col items-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                시장 레벨
              </h3>
              <CircularProgress
                value={marketGate?.level ?? 0}
                max={100}
                status={marketGate?.status ?? "YELLOW"}
              />
              <p className={`mt-4 text-sm font-medium ${
                marketGate?.status === "GREEN"
                  ? "text-green-600 dark:text-green-400"
                  : marketGate?.status === "RED"
                  ? "text-red-600 dark:text-red-400"
                  : "text-yellow-600 dark:text-yellow-400"
              }`}>
                {marketGate?.status === "GREEN" ? "강세장" : marketGate?.status === "RED" ? "약세장" : "중립"}
              </p>
            </div>

            {/* 지수 현황 */}
            <div className="md:col-span-2 grid grid-cols-2 gap-4">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow">
                <h4 className="text-sm text-gray-500 mb-2">KOSPI</h4>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {marketGate?.kospi_close?.toLocaleString() ?? "-"}
                  </span>
                  <span className={`text-sm ${marketGate?.kospi_change_pct && marketGate.kospi_change_pct >= 0 ? "text-red-600" : "text-blue-600"}`}>
                    {marketGate?.kospi_change_pct && marketGate.kospi_change_pct >= 0 ? "+" : ""}
                    {marketGate?.kospi_change_pct?.toFixed(2)}%
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{marketGate?.kospi_status ?? "-"}</p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow">
                <h4 className="text-sm text-gray-500 mb-2">KOSDAQ</h4>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {marketGate?.kosdaq_close?.toLocaleString() ?? "-"}
                  </span>
                  <span className={`text-sm ${marketGate?.kosdaq_change_pct && marketGate.kosdaq_change_pct >= 0 ? "text-red-600" : "text-blue-600"}`}>
                    {marketGate?.kosdaq_change_pct && marketGate.kosdaq_change_pct >= 0 ? "+" : ""}
                    {marketGate?.kosdaq_change_pct?.toFixed(2)}%
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{marketGate?.kosdaq_status ?? "-"}</p>
              </div>

              {/* 백테스트 KPI 카드 */}
              {backtestKPI && (
                <>
                  <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow">
                    <h4 className="text-xs text-gray-500 mb-2">VCP 백테스트</h4>
                    <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {backtestKPI.vcp.status === "OK"
                        ? `${backtestKPI.vcp.count}건`
                        : backtestKPI.vcp.status}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {backtestKPI.vcp.win_rate
                        ? `승률 ${backtestKPI.vcp.win_rate.toFixed(0)}%`
                        : "데이터 수집중"}
                    </p>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow">
                    <h4 className="text-xs text-gray-500 mb-2">종가베팅 백테스트</h4>
                    <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {backtestKPI.closing_bet.status === "OK"
                        ? `${backtestKPI.closing_bet.count}건`
                        : backtestKPI.closing_bet.status}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {backtestKPI.closing_bet.win_rate
                        ? `승률 ${backtestKPI.closing_bet.win_rate.toFixed(0)}%`
                        : "데이터 수집중"}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* 섹터별 현황 */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
            섹터별 현황
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {sortedSectors.map((sector, idx) => (
              <SectorCard key={`${sector.name}-${idx}`} sector={sector} />
            ))}
          </div>
        </div>

        {/* 백테스트 상세 */}
        {backtestKPI && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              백테스트 성과
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <BacktestStats
                stats={backtestKPI.vcp}
                label="VCP 스캔 전략"
              />
              <BacktestStats
                stats={backtestKPI.closing_bet}
                label="종가베팅 V2"
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
