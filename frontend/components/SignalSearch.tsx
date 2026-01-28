/**
 * 시그널 검색 컴포넌트
 * 종목명/티커 검색 및 필터링
 */

"use client";

import { useState, useMemo } from "react";
import { useStore } from "@/store";
import { cn } from "@/lib/utils";

export function SignalSearch() {
  const [searchQuery, setSearchQuery] = useState("");
  const { signals, filters, setFilters, getFilteredSignals } = useStore();

  // 검색 및 필터링된 시그널
  const filteredSignals = useMemo(() => {
    let result = signals;

    // 텍스트 검색
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (signal) =>
          signal.name.toLowerCase().includes(query) ||
          signal.ticker.toLowerCase().includes(query)
      );
    }

    // 등급 필터
    if (filters.grades.length > 0) {
      result = result.filter((signal) =>
        filters.grades.includes(signal.grade)
      );
    }

    // 점수 범위 필터
    result = result.filter(
      (signal) => {
        const scoreValue = typeof signal.score === "number" ? signal.score : signal.score?.total ?? 0;
        return scoreValue >= filters.minScore && scoreValue <= filters.maxScore;
      }
    );

    // 시그널 타입 필터
    if (filters.signalType !== "all") {
      result = result.filter(
        (signal) => signal.signal_type === filters.signalType
      );
    }

    return result;
  }, [signals, searchQuery, filters]);

  return (
    <div className="space-y-4">
      {/* 검색 입력 */}
      <div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="종목명 또는 티커 검색..."
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {searchQuery && (
          <p className="text-sm text-gray-500 mt-1">
            {filteredSignals.length}개 결과
          </p>
        )}
      </div>

      {/* 등급 필터 */}
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          등급 필터
        </p>
        <div className="flex flex-wrap gap-2">
          {["S", "A", "B", "C"].map((grade) => (
            <button
              key={grade}
              onClick={() => {
                const newGrades = filters.grades.includes(grade)
                  ? filters.grades.filter((g) => g !== grade)
                  : [...filters.grades, grade];
                setFilters({ grades: newGrades });
              }}
              className={cn(
                "px-3 py-1 rounded-full text-sm font-medium transition",
                filters.grades.includes(grade)
                  ? `${getGradeColor(grade)} text-white`
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
              )}
            >
              {grade}등급
            </button>
          ))}
        </div>
      </div>

      {/* 점수 범위 필터 */}
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          점수 범위: {filters.minScore} - {filters.maxScore}
        </p>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="100"
            value={filters.minScore}
            onChange={(e) => setFilters({ minScore: Number(e.target.value) })}
            className="flex-1"
          />
          <span className="text-sm text-gray-600 dark:text-gray-400 w-12 text-right">
            {filters.minScore}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="100"
            value={filters.maxScore}
            onChange={(e) => setFilters({ maxScore: Number(e.target.value) })}
            className="flex-1"
          />
          <span className="text-sm text-gray-600 dark:text-gray-400 w-12 text-right">
            {filters.maxScore}
          </span>
        </div>
      </div>

      {/* 시그널 타입 필터 */}
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          시그널 타입
        </p>
        <div className="flex flex-wrap gap-2">
          {["all", "VCP", "종가베팅"].map((type) => (
            <button
              key={type}
              onClick={() => setFilters({ signalType: type })}
              className={cn(
                "px-3 py-1 rounded-full text-sm font-medium transition",
                filters.signalType === type
                  ? "bg-blue-500 text-white"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
              )}
            >
              {type === "all" ? "전체" : type}
            </button>
          ))}
        </div>
      </div>

      {/* 필터 초기화 버튼 */}
      {(searchQuery ||
        filters.grades.length > 0 ||
        filters.minScore > 0 ||
        filters.maxScore < 100 ||
        filters.signalType !== "all") && (
        <button
          onClick={() => {
            setSearchQuery("");
            setFilters({
              grades: [],
              minScore: 0,
              maxScore: 100,
              signalType: "all",
            });
          }}
          className="w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
        >
          필터 초기화
        </button>
      )}
    </div>
  );
}

// 등급별 색상 헬퍼 함수
function getGradeColor(grade: string): string {
  switch (grade) {
    case "S":
      return "bg-yellow-500";
    case "A":
      return "bg-green-500";
    case "B":
      return "bg-blue-500";
    case "C":
      return "bg-gray-500";
    default:
      return "bg-gray-400";
  }
}
