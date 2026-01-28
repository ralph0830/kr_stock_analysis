"use client";

import { useEffect, useMemo, useState } from "react";
import { useStore } from "@/store";
import { formatPrice, getGradeColor } from "@/lib/utils";
import type { Signal, ScoreDetail } from "@/types";

export default function SignalsPage() {
  const { signals, loadingSignals, fetchSignals } = useStore();
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // 등급별 그룹핑
  const gradeS = signals.filter((s) => s.grade === "S");
  const gradeA = signals.filter((s) => s.grade === "A");
  const gradeB = signals.filter((s) => s.grade === "B");
  const gradeC = signals.filter((s) => s.grade === "C");

  // 점수 추출 함수
  const getScoreValue = (signal: Signal): number => {
    if (typeof signal.score === "number") return signal.score;
    return signal.score?.total ?? 0;
  };

  // 점수 상세 추출 함수
  const getScoreDetail = (signal: Signal): ScoreDetail | null => {
    if (typeof signal.score === "object" && signal.score !== null) {
      return signal.score as ScoreDetail;
    }
    return null;
  };

  // 점수 항목 라벨
  const scoreLabels: Record<keyof ScoreDetail, string> = {
    total: "총점",
    news: "뉴스",
    volume: "거래대금",
    chart: "차트패턴",
    candle: "캔들",
    period: "기간조정",
    flow: "수급",
  };

  // 점수 항목 최대값
  const scoreMax: Record<keyof Omit<ScoreDetail, "total">, number> = {
    news: 3,
    volume: 3,
    chart: 2,
    candle: 1,
    period: 1,
    flow: 2,
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              🎯 종가베팅 V2 시그널
            </h1>
            <a
              href="/"
              className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
            >
              ← 홈
            </a>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* 요약 카드 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-1">S 등급</p>
            <p className="text-2xl font-bold text-yellow-900 dark:text-yellow-100">{gradeS.length}개</p>
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <p className="text-sm text-green-700 dark:text-green-300 mb-1">A 등급</p>
            <p className="text-2xl font-bold text-green-900 dark:text-green-100">{gradeA.length}개</p>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-700 dark:text-blue-300 mb-1">B 등급</p>
            <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">{gradeB.length}개</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-1">C 등급</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{gradeC.length}개</p>
          </div>
        </div>

        {/* 시그널 목록 */}
        {loadingSignals ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg text-center">
            <p className="text-gray-500">로딩 중...</p>
          </div>
        ) : signals.length > 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      등급
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      티커
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      종목명
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      점수
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      진입가
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      목표가 / 손절가
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      포지션
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      매매 사유
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      생성일
                    </th>
                    <th className="px-2 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {signals.map((signal) => {
                    const scoreDetail = getScoreDetail(signal);
                    const isExpanded = expandedRow === signal.ticker;
                    return (
                      <>
                        <tr key={signal.ticker} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="px-4 py-4 whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getGradeColor(signal.grade)}`}>
                              {signal.grade}
                            </span>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                            <a
                              href={`/stock/${signal.ticker}`}
                              className="hover:text-blue-600 hover:underline"
                            >
                              {signal.ticker}
                            </a>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                            {signal.name}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                {getScoreValue(signal).toFixed(0)}
                              </span>
                              <span className="text-xs text-gray-500">/ 12</span>
                            </div>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                            {signal.entry_price ? formatPrice(signal.entry_price) : "-"}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm">
                            <div className="flex flex-col gap-1">
                              <span className="text-green-600 dark:text-green-400">
                                목표: {signal.target_price ? formatPrice(signal.target_price) : "-"}
                              </span>
                              <span className="text-red-600 dark:text-red-400">
                                손절: {signal.stop_loss ? formatPrice(signal.stop_loss) : "-"}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
                            {signal.position_size ? signal.position_size.toLocaleString() : "-"} 주
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex flex-wrap gap-1">
                              {signal.reasons && signal.reasons.length > 0 ? (
                                signal.reasons.slice(0, 2).map((reason, idx) => (
                                  <span key={idx} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                                    {reason}
                                  </span>
                                ))
                              ) : (
                                <span className="text-xs text-gray-500">-</span>
                              )}
                              {signal.reasons && signal.reasons.length > 2 && (
                                <span className="text-xs text-gray-500">+{signal.reasons.length - 2}</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                            {new Date(signal.created_at).toLocaleDateString("ko-KR")}
                          </td>
                          <td className="px-2 py-4">
                            <button
                              onClick={() => setExpandedRow(isExpanded ? null : signal.ticker)}
                              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                              {isExpanded ? "▼" : "▶"}
                            </button>
                          </td>
                        </tr>
                        {/* 확장된 점수 상세 행 */}
                        {isExpanded && scoreDetail && (
                          <tr key={`${signal.ticker}-detail`} className="bg-gray-50 dark:bg-gray-800/50">
                            <td colSpan={10} className="px-4 py-4">
                              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                                {(Object.keys(scoreDetail) as Array<keyof ScoreDetail>).map((key) => {
                                  if (key === "total") return null;
                                  const value = scoreDetail[key];
                                  const max = scoreMax[key] || 3;
                                  const percentage = (value / max) * 100;

                                  // 색상 결정
                                  const getColor = () => {
                                    if (percentage >= 80) return "bg-green-500";
                                    if (percentage >= 50) return "bg-yellow-500";
                                    if (percentage > 0) return "bg-orange-500";
                                    return "bg-gray-300";
                                  };

                                  return (
                                    <div key={key} className="bg-white dark:bg-gray-700 rounded-lg p-3">
                                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                                        {scoreLabels[key]}
                                      </p>
                                      <div className="flex items-center gap-2 mb-2">
                                        <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
                                          {value}
                                        </span>
                                        <span className="text-xs text-gray-400">/ {max}</span>
                                      </div>
                                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                                        <div
                                          className={`${getColor()} h-2 rounded-full transition-all`}
                                          style={{ width: `${Math.min(percentage, 100)}%` }}
                                        />
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                              {/* 전체 매매 사유 */}
                              {signal.reasons && signal.reasons.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    매매 사유:
                                  </p>
                                  <div className="flex flex-wrap gap-2">
                                    {signal.reasons.map((reason, idx) => (
                                      <span key={idx} className="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                                        {reason}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg text-center">
            <p className="text-gray-500">시그널이 없습니다.</p>
            <p className="text-sm text-gray-400 mt-2">
              시그널 생성을 실행하려면{" "}
              <a href="/" className="text-blue-600 hover:underline">
                대시보드
              </a>
              {" "}에서 스캔을 시작하세요.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
