"use client";

import { useEffect, useState, useMemo } from "react";
import { apiClient } from "@/lib/api-client";
import { formatPrice } from "@/lib/utils";
import type { Signal, ScoreDetail } from "@/types";

/**
 * 종가베팅 V2 시그널 타입
 */
interface JonggaSignal extends Signal {
  news_score?: number;
  volume_score?: number;
  chart_score?: number;
  candle_score?: number;
  period_score?: number;
  flow_score?: number;
  has_news?: boolean;
  is_new_high?: boolean;
  flow_good?: boolean;
  signal_date?: string;
}

/**
 * 점수 바 컴포넌트
 */
function ScoreBar({
  label,
  score,
  max = 3
}: {
  label: string;
  score: number | undefined;
  max?: number;
}) {
  const displayScore = score ?? 0;
  const percentage = (displayScore / max) * 100;

  const getColor = () => {
    if (displayScore >= max) return "bg-green-500";
    if (displayScore >= max * 0.7) return "bg-blue-500";
    if (displayScore >= max * 0.4) return "bg-yellow-500";
    return "bg-gray-400";
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-600 dark:text-gray-400 w-12">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-6 text-right">
        {displayScore}/{max}
      </span>
    </div>
  );
}

/**
 * 체크리스트 뱃지 컴포넌트
 */
function ChecklistBadge({
  checked,
  label
}: {
  checked: boolean | undefined;
  label: string;
}) {
  if (checked) {
    return (
      <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-700 dark:text-green-400 border border-green-500/30">
        ✓ {label}
      </span>
    );
  }
  return (
    <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-500/20 text-gray-600 dark:text-gray-400 border border-gray-500/30">
      {label}
    </span>
  );
}

/**
 * 차트 모달 컴포넌트
 */
function ChartModal({
  isOpen,
  onClose,
  ticker,
  name
}: {
  isOpen: boolean;
  onClose: () => void;
  ticker: string;
  name: string;
}) {
  if (!isOpen) return null;

  // 네이버 금융 차트 이미지 URL (일봉)
  const chartUrl = `https://ssl.pstatic.net/imgfinance/chart/item/candle/day/${ticker}.png?t=${Date.now()}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name} ({ticker}) 차트
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="p-4">
          <img
            src={chartUrl}
            alt={`${name} 차트`}
            className="w-full h-auto rounded-lg"
            onError={(e) => {
              e.currentTarget.src = "/placeholder-chart.png";
            }}
          />
          <a
            href={`https://m.stock.naver.com/domestic/stock/${ticker}/chart`}
            target="_blank"
            rel="noopener noreferrer"
            className="block mt-4 text-center text-sm text-blue-600 hover:text-blue-700"
          >
            네이버 금융에서 상세 차트 보기 →
          </a>
        </div>
      </div>
    </div>
  );
}

export default function ClosingBetV2Page() {
  const [signals, setSignals] = useState<JonggaSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string>("latest");
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedChart, setSelectedChart] = useState<{ ticker: string; name: string } | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // 날짜 목록 로드
  useEffect(() => {
    const loadDates = async () => {
      try {
        const dates = await apiClient.getJonggaV2Dates();
        setAvailableDates(dates);
      } catch (error) {
        console.error("Failed to load dates:", error);
      }
    };
    loadDates();
  }, []);

  // 시그널 로드
  const loadSignals = async (date: string) => {
    setLoading(true);
    try {
      let data: Signal[];
      if (date === "latest") {
        data = await apiClient.getJonggaV2Latest();
      } else {
        data = await apiClient.getJonggaV2History(date);
      }
      setSignals(data as JonggaSignal[]);
    } catch (error) {
      console.error("Failed to load signals:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSignals(selectedDate);
  }, [selectedDate]);

  // 엔진 실행 핸들러
  const handleRunEngine = async () => {
    setIsRunning(true);
    try {
      const result = await apiClient.runJonggaV2Engine();
      if (result.status === "completed") {
        // Reload signals after engine run
        loadSignals(selectedDate);
      }
    } catch (error) {
      console.error("Failed to run engine:", error);
    } finally {
      setIsRunning(false);
    }
  };

  // 점수 계산 헬퍼
  const getScoreValue = (signal: JonggaSignal): number => {
    if (typeof signal.score === "number") return signal.score;
    return signal.score?.total ?? 0;
  };

  // 등급별 색상
  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "S": return "bg-rose-500/20 text-rose-700 border-rose-500/20 dark:text-rose-400";
      case "A": return "bg-amber-500/20 text-amber-700 border-amber-500/20 dark:text-amber-400";
      case "B": return "bg-blue-500/20 text-blue-700 border-blue-500/20 dark:text-blue-400";
      default: return "bg-gray-500/20 text-gray-700 border-gray-500/20 dark:text-gray-400";
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                종가베팅 V2
              </h1>
              <span className="px-2 py-1 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 text-xs font-medium">
                12점 스코어링 시스템
              </span>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={handleRunEngine}
                disabled={isRunning}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isRunning
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-purple-500 text-white hover:bg-purple-600"
                }`}
              >
                {isRunning ? "엔진 실행 중..." : "엔진 실행"}
              </button>
              <a
                href="/dashboard"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
              >
                ← 대시보드
              </a>
            </div>
          </div>

          {/* 날짜 선택기 */}
          <div className="mt-4 flex items-center gap-3">
            <label className="text-sm text-gray-600 dark:text-gray-400">날짜:</label>
            <select
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
            >
              <option value="latest">최신</option>
              {availableDates.map((date) => (
                <option key={date} value={date}>
                  {date}
                </option>
              ))}
            </select>
            {signals.length > 0 && (
              <span className="text-xs text-gray-500">
                {signals.length}개 시그널
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* 로딩 상태 */}
        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-16 text-center shadow">
            <div className="inline-flex items-center gap-3">
              <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-600 dark:text-gray-400">종가베팅 V2 시그널을 불러오는 중...</p>
            </div>
          </div>
        ) : signals.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-16 text-center shadow">
            <p className="text-gray-500 dark:text-gray-400">
              {selectedDate === "latest" ? "오늘 종가베팅 시그널이 없습니다." : `${selectedDate} 시그널이 없습니다.`}
            </p>
          </div>
        ) : (
          /* 시그널 카드 그리드 */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {signals.map((signal) => {
              const score = getScoreValue(signal);
              const scoreDetail = typeof signal.score === "object" ? signal.score : undefined;

              return (
                <div
                  key={`${signal.ticker}-${signal.created_at}`}
                  className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
                >
                  {/* 카드 헤더 */}
                  <div className="p-5 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-white/10 flex items-center justify-center text-white font-bold text-lg">
                          {signal.name?.charAt(0) || signal.ticker?.charAt(0) || "?"}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-gray-900 dark:text-gray-100">
                              {signal.name || signal.ticker}
                            </h3>
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-bold ${getGradeColor(signal.grade)}`}
                            >
                              {signal.grade}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 font-mono">{signal.ticker}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                          {score}
                        </div>
                        <p className="text-xs text-gray-500">/ 12점</p>
                      </div>
                    </div>

                    {/* 가격 정보 */}
                    <div className="flex items-center justify-between text-sm">
                      <div>
                        <span className="text-gray-500">진입가:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                          ₩{formatPrice(signal.entry_price)}
                        </span>
                      </div>
                      {signal.target_price && (
                        <div>
                          <span className="text-gray-500">목표가:</span>
                          <span className="ml-2 font-medium text-green-600">
                            ₩{formatPrice(signal.target_price)}
                          </span>
                        </div>
                      )}
                      {signal.stop_loss && (
                        <div>
                          <span className="text-gray-500">손절가:</span>
                          <span className="ml-2 font-medium text-red-600">
                            ₩{formatPrice(signal.stop_loss)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 카드 내용 */}
                  <div className="p-5">
                    {/* 점수 바 */}
                    <div className="mb-4 space-y-2">
                      <ScoreBar label="뉴스" score={signal.news_score} max={3} />
                      <ScoreBar label="거래량" score={signal.volume_score} max={3} />
                      <ScoreBar label="차트" score={signal.chart_score} max={2} />
                      <ScoreBar label="캔들" score={signal.candle_score} max={1} />
                      <ScoreBar label="기간" score={signal.period_score} max={1} />
                      <ScoreBar label="수급" score={signal.flow_score} max={2} />
                    </div>

                    {/* 체크리스트 */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      <ChecklistBadge checked={signal.has_news} label="뉴스 있음" />
                      <ChecklistBadge checked={signal.flow_good} label="수급 양호" />
                      <ChecklistBadge checked={signal.is_new_high} label="신고가" />
                      {score >= 10 && (
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-500/20 text-purple-700 border border-purple-500/30">
                          강력매수
                        </span>
                      )}
                    </div>

                    {/* 사유 */}
                    {signal.reasons && signal.reasons.length > 0 && (
                      <div className="mb-4">
                        <p className="text-xs text-gray-500 mb-1">매매 사유:</p>
                        <ul className="text-sm text-gray-700 dark:text-gray-300 list-disc list-inside">
                          {signal.reasons.slice(0, 3).map((reason, idx) => (
                            <li key={idx}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 액션 버튼 */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSelectedChart({ ticker: signal.ticker, name: signal.name })}
                        className="flex-1 px-3 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
                      >
                        차트 보기
                      </button>
                      <a
                        href={`/stock/${signal.ticker}`}
                        className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium text-center hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                      >
                        상세 보기
                      </a>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 차트 모달 */}
      {selectedChart && (
        <ChartModal
          isOpen={!!selectedChart}
          onClose={() => setSelectedChart(null)}
          ticker={selectedChart.ticker}
          name={selectedChart.name}
        />
      )}
    </main>
  );
}
