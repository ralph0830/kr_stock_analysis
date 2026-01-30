"use client";

import { useState } from "react";

interface NaverChartWidgetProps {
  ticker: string;
  name: string;
  type?: "day" | "week" | "month";
}

/**
 * 네이버 금융 차트 위젯
 * 네이버 금융의 공개 차트 이미지를 표시
 */
export function NaverChartWidget({
  ticker,
  name,
  type = "day"
}: NaverChartWidgetProps) {
  const [imageError, setImageError] = useState(false);

  // 네이버 금융 차트 이미지 URL (타임스탬프로 캐시 방지)
  const chartUrl = `https://ssl.pstatic.net/imgfinance/chart/item/candle/${type}/${ticker}.png?t=${Date.now()}`;
  const mobileChartUrl = `https://m.stock.naver.com/domestic/stock/${ticker}/chart`;

  const handleError = () => {
    setImageError(true);
  };

  if (imageError) {
    return (
      <div className="aspect-video bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
        <p className="text-sm text-gray-500">차트를 불러올 수 없습니다</p>
        <a
          href={mobileChartUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-2 text-blue-500 hover:underline text-sm"
        >
          네이버 금융에서 보기
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="relative group">
        <img
          src={chartUrl}
          alt={`${name} (${ticker}) ${type} 차트`}
          className="w-full h-auto rounded-lg border border-gray-200 dark:border-gray-700"
          onError={handleError}
          loading="lazy"
        />
        {/* Hover overlay */}
        <a
          href={mobileChartUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center"
        >
          <span className="text-white font-medium">네이버 금융에서 상세 보기 →</span>
        </a>
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>출처: 네이버 금융</span>
        <a
          href={mobileChartUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:underline"
        >
          대화형 차트 보기
        </a>
      </div>
    </div>
  );
}

interface NaverChartButtonProps {
  ticker: string;
  name: string;
  onClick?: () => void;
}

/**
 * 네이버 차트 보기 버튼
 * 차트 모달을 열거나 네이버 금융으로 이동하는 버튼
 */
export function NaverChartButton({ ticker, name, onClick }: NaverChartButtonProps) {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <button
      onClick={handleClick}
      className="px-3 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors flex items-center gap-2"
    >
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"
        />
      </svg>
      차트 보기
    </button>
  );
}

interface ChartModalProps {
  isOpen: boolean;
  onClose: () => void;
  ticker: string;
  name: string;
}

/**
 * 차트 모달 컴포넌트
 */
export function ChartModal({ isOpen, onClose, ticker, name }: ChartModalProps) {
  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    }
  };

  // ESC 키로 닫기
  if (typeof window !== "undefined") {
    window.addEventListener("keydown", handleEscape);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-4xl w-full mx-4 overflow-hidden animate-fadeIn"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {name} ({ticker}) 차트
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="닫기"
          >
            <svg
              className="w-5 h-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4">
          {/* 차트 탭 */}
          <div className="flex gap-2 mb-4">
            <button className="px-3 py-1 text-sm rounded-full bg-blue-500 text-white">
              일봉
            </button>
            <button className="px-3 py-1 text-sm rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
              주봉
            </button>
            <button className="px-3 py-1 text-sm rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
              월봉
            </button>
          </div>

          {/* 차트 이미지 */}
          <NaverChartWidget ticker={ticker} name={name} type="day" />
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <p className="text-xs text-gray-500">
            제공: 네이버 금융 | 실시간 데이터 연동 중
          </p>
          <a
            href={`https://m.stock.naver.com/domestic/stock/${ticker}/chart`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-500 hover:text-blue-600 font-medium"
          >
            네이버 금융에서 상세 보기 →
          </a>
        </div>
      </div>
    </div>
  );
}

export default NaverChartWidget;
