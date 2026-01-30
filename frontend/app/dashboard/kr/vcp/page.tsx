"use client";

import { useEffect, useState, useMemo } from "react";
import { apiClient } from "@/lib/api-client";
import { formatPrice } from "@/lib/utils";
import type { Signal } from "@/types";
import type { IAIAnalysisList } from "@/types";

// VCP 전용 시그널 타입 (Signal 타입 확장)
interface VCPSignal extends Signal {
  foreign_5d?: number;
  inst_5d?: number;
  contraction_ratio?: number;
}

// AI 추천 타입
interface AIRecommendation {
  action: "BUY" | "SELL" | "HOLD";
  reason: string;
  confidence?: number;
}

// AI 분석 아이템 (VCP 페이지용)
interface AIAnalysisItem {
  ticker: string;
  gpt_recommendation?: AIRecommendation;
  gemini_recommendation?: AIRecommendation;
}

/**
 * VCP 수급 포맷팅 (억/만 단위)
 */
function formatFlow(value: number | undefined): string {
  if (value === undefined || value === null) return "-";
  const absValue = Math.abs(value);
  if (absValue >= 100000000) {
    return `${(value / 100000000).toFixed(1)}억`;
  } else if (absValue >= 10000) {
    return `${(value / 10000).toFixed(0)}만`;
  }
  return value.toLocaleString();
}

/**
 * AI 추천 뱃지 컴포넌트
 */
function AIBadge({
  recommendation,
  // model is kept for future use (e.g., different styling per model)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  model
}: {
  recommendation: AIRecommendation | undefined;
  model: "gpt" | "gemini";
}) {
  if (!recommendation) return <span className="text-gray-500 text-xs">-</span>;

  const action = recommendation.action;
  let bgClass = "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
  let icon = "■";
  let label = "관망";

  if (action === "BUY") {
    bgClass = "bg-green-500/20 text-green-400 border-green-500/30";
    icon = "▲";
    label = "매수";
  } else if (action === "SELL") {
    bgClass = "bg-red-500/20 text-red-400 border-red-500/30";
    icon = "▼";
    label = "매도";
  }

  return (
    <span
      className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${bgClass} border border-current/30`}
      title={recommendation.reason}
    >
      {icon} {label}
    </span>
  );
}

/**
 * 수축률 색상 반환
 */
function getContractionColor(value: number | undefined): string {
  if (value === undefined || value === null) return "text-purple-400";
  if (value <= 0.6) return "text-emerald-400";
  return "text-purple-400";
}

/**
 * 실시간 가격 업데이트 커스텀 훅
 */
function useRealtimePrices(signals: Signal[], intervalMs: number = 60000) {
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    if (signals.length === 0) return;

    const updatePrices = async () => {
      try {
        const tickers = signals.map((s) => s.ticker);
        const priceData = await apiClient.getRealtimePrices(tickers);
        // StockPrice 객체에서 price만 추출
        const pricesMap: Record<string, number> = {};
        for (const [ticker, stockPrice] of Object.entries(priceData)) {
          pricesMap[ticker] = stockPrice.price;
        }
        setPrices(pricesMap);
        setLastUpdated(new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }));
      } catch (e) {
        console.error("Price update failed:", e);
      }
    };

    // 초기 업데이트
    updatePrices();

    // 주기적 업데이트
    const interval = setInterval(updatePrices, intervalMs);
    return () => clearInterval(interval);
  }, [signals, intervalMs]);

  return { prices, lastUpdated };
}

// AI 분석 데이터 매핑 (ticker 기반)
function mapAIAnalysisData(aiList: IAIAnalysisList): Map<string, AIAnalysisItem> {
  const map = new Map<string, AIAnalysisItem>();
  for (const item of aiList.analyses) {
    map.set(item.ticker, {
      ticker: item.ticker,
      gpt_recommendation: undefined,
      gemini_recommendation: undefined,
    });
  }
  return map;
}

export default function VCPPage() {
  const [signals, setSignals] = useState<VCPSignal[]>([]);
  const [aiDataMap, setAiDataMap] = useState<Map<string, AIAnalysisItem>>(new Map());
  const [loading, setLoading] = useState(true);
  const [signalDate, setSignalDate] = useState<string>("");

  // 실시간 가격 업데이트
  const { prices, lastUpdated } = useRealtimePrices(signals);

  // 데이터 로드
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [signalsRes, aiRes] = await Promise.all([
          apiClient.getSignals(),
          apiClient.getAIAnalysis(),
        ]);

        // Signal을 VCPSignal으로 타입 변환 (VCP 관련 속성이 있을 경우)
        setSignals(signalsRes as VCPSignal[]);

        // AI 분석 데이터를 Map으로 변환
        const aiMap = mapAIAnalysisData(aiRes);
        setAiDataMap(aiMap);

        // 생성일 추출
        if (aiRes.analysis_date) {
          const d = new Date(aiRes.analysis_date);
          setSignalDate(d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" }));
        }
      } catch (error) {
        console.error("Failed to load VCP data:", error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // 시그널 정렬 (점수순)
  const sortedSignals = useMemo(() => {
    return [...signals].sort((a, b) => {
      const scoreA = typeof a.score === "number" ? a.score : a.score?.total ?? 0;
      const scoreB = typeof b.score === "number" ? b.score : b.score?.total ?? 0;
      return scoreB - scoreA;
    });
  }, [signals]);

  // AI 추천 조회 헬퍼
  const getAIRecommendation = (ticker: string, model: "gpt" | "gemini"): AIRecommendation | undefined => {
    const signal = aiDataMap.get(ticker);
    if (!signal) return undefined;
    return model === "gpt" ? signal.gpt_recommendation : signal.gemini_recommendation;
  };

  // 현재가 계산 (실시간 가격 또는 entry_price)
  const getCurrentPrice = (signal: VCPSignal): number => {
    const realtimePrice = prices[signal.ticker];
    if (realtimePrice) return realtimePrice;
    return signal.entry_price || 0;
  };

  // 수익률 계산
  const getReturnPct = (signal: VCPSignal): number => {
    const entryPrice = signal.entry_price || 0;
    const currentPrice = getCurrentPrice(signal);
    if (entryPrice > 0) {
      return ((currentPrice - entryPrice) / entryPrice) * 100;
    }
    return 0;
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                VCP Signals
              </h1>
              <span className="px-2 py-1 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 text-xs font-medium">
                Volatility Contraction Pattern
              </span>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="/dashboard"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
              >
                ← 대시보드
              </a>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* 헤더 섹션 */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-xs text-blue-600 dark:text-blue-400 font-medium mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping"></span>
            VCP Pattern Scanner
          </div>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tighter text-gray-900 dark:text-gray-100 leading-tight mb-2">
            VCP <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">Signals</span>
          </h2>
          <p className="text-gray-600 dark:text-gray-400 text-lg">
            변동성 수축 패턴 + 기관/외국인 수급
          </p>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
            <span>생성일: {signalDate || "-"}</span>
            <span>•</span>
            <span>시그널: {sortedSignals.length}개</span>
            {lastUpdated && (
              <>
                <span>•</span>
                <span>마지막 업데이트: {lastUpdated}</span>
              </>
            )}
          </div>
        </div>

        {/* 로딩 상태 */}
        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-16 text-center shadow">
            <div className="inline-flex items-center gap-3">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-600 dark:text-gray-400">VCP 시그널을 불러오는 중...</p>
            </div>
          </div>
        ) : sortedSignals.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-16 text-center shadow">
            <p className="text-gray-500 dark:text-gray-400">오늘 VCP 시그널이 없습니다.</p>
          </div>
        ) : (
          /* 시그널 테이블 */
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      종목
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      날짜
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      외국인 5D
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      기관 5D
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      점수
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      수축률
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      진입가
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      현재가
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      수익률
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      GPT
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Gemini
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {sortedSignals.map((signal, idx) => {
                    const currentPrice = getCurrentPrice(signal);
                    const returnPct = getReturnPct(signal);
                    const isPositive = returnPct >= 0;

                    // 등급별 색상
                    const getGradeColor = (grade: string) => {
                      if (grade === "S") return "bg-rose-500/20 text-rose-700 border-rose-500/20 dark:text-rose-400";
                      if (grade === "A") return "bg-amber-500/20 text-amber-700 border-amber-500/20 dark:text-amber-400";
                      if (grade === "B") return "bg-blue-500/20 text-blue-700 border-blue-500/20 dark:text-blue-400";
                      return "bg-gray-500/20 text-gray-700 border-gray-500/20 dark:text-gray-400";
                    };

                    return (
                      <tr
                        key={`${signal.ticker}-${idx}`}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                      >
                        {/* 종목명 */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center text-white font-bold text-sm dark:text-gray-700">
                              {signal.name?.charAt(0) || signal.ticker?.charAt(0) || "?"}
                            </div>
                            <div className="flex flex-col">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                  {signal.name || signal.ticker}
                                </span>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getGradeColor(signal.grade)}`}
                                >
                                  {signal.grade}
                                </span>
                              </div>
                              <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                {signal.ticker}
                              </span>
                            </div>
                          </div>
                        </td>

                        {/* 날짜 */}
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400 text-xs">
                          {signalDate || "-"}
                        </td>

                        {/* 외국인 5D */}
                        <td
                          className={`px-4 py-3 text-right font-mono text-xs ${
                            (signal.foreign_5d ?? 0) > 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                          }`}
                        >
                          <div className="flex items-center justify-end gap-1">
                            {(signal.foreign_5d ?? 0) > 0 ? (
                              <span className="text-[10px]">▲</span>
                            ) : (signal.foreign_5d ?? 0) < 0 ? (
                              <span className="text-[10px]">▼</span>
                            ) : null}
                            {formatFlow(signal.foreign_5d)}
                          </div>
                        </td>

                        {/* 기관 5D */}
                        <td
                          className={`px-4 py-3 text-right font-mono text-xs ${
                            (signal.inst_5d ?? 0) > 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                          }`}
                        >
                          <div className="flex items-center justify-end gap-1">
                            {(signal.inst_5d ?? 0) > 0 ? (
                              <span className="text-[10px]">▲</span>
                            ) : (signal.inst_5d ?? 0) < 0 ? (
                              <span className="text-[10px]">▼</span>
                            ) : null}
                            {formatFlow(signal.inst_5d)}
                          </div>
                        </td>

                        {/* 점수 */}
                        <td className="px-4 py-3 text-center">
                          <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                            {typeof signal.score === "number" ? signal.score.toFixed(0) : signal.score?.total?.toFixed(0) ?? "-"}
                          </span>
                        </td>

                        {/* 수축률 */}
                        <td className={`px-4 py-3 text-center font-mono text-xs ${getContractionColor(signal.contraction_ratio)}`}>
                          {signal.contraction_ratio ? signal.contraction_ratio.toFixed(2) : "-"}
                        </td>

                        {/* 진입가 */}
                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-600 dark:text-gray-400">
                          ₩{formatPrice(signal.entry_price)}
                        </td>

                        {/* 현재가 */}
                        <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-gray-100">
                          ₩{formatPrice(currentPrice)}
                        </td>

                        {/* 수익률 */}
                        <td
                          className={`px-4 py-3 text-right font-bold ${isPositive ? "text-red-600 dark:text-red-400" : "text-blue-600 dark:text-blue-400"}`}
                        >
                          {returnPct !== 0 ? (isPositive ? "+" : "") + returnPct.toFixed(1) + "%" : "-"}
                        </td>

                        {/* GPT 추천 */}
                        <td className="px-4 py-3 text-center">
                          <AIBadge
                            recommendation={getAIRecommendation(signal.ticker, "gpt")}
                            model="gpt"
                          />
                        </td>

                        {/* Gemini 추천 */}
                        <td className="px-4 py-3 text-center">
                          <AIBadge
                            recommendation={getAIRecommendation(signal.ticker, "gemini")}
                            model="gemini"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
