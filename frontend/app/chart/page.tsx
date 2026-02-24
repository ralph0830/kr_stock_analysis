/**
 * 차트 데모 페이지
 */
"use client";

import { useState, useEffect } from "react";
import { FullStockChart, MiniChart, PriceChange, PriceData } from "@/components/StockChart";
import { apiClient } from "@/lib/api-client";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  ChartRealtimePrice,
  ChartRealtimePriceHeader,
  type IStockInfo,
} from "@/components/realtime/ChartRealtimePrice";

// 인기 종목 목록 (데이터가 있는 종목만)
const POPULAR_STOCKS = [
  { ticker: "005930", name: "삼성전자" },
  { ticker: "000020", name: "동서" },
];

// 에러 메시지 타입
interface ErrorMessage {
  title: string;
  message: string;
  canRetry: boolean;
}

export default function ChartPage() {
  const [chartData, setChartData] = useState<PriceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicker, setSelectedTicker] = useState("005930"); // 삼성전자
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [miniChartsReady, setMiniChartsReady] = useState(false);
  const [error, setError] = useState<ErrorMessage | null>(null);

  // 선택된 종목 정보 조회
  const selectedStockInfo = POPULAR_STOCKS.find((s) => s.ticker === selectedTicker);

  // 미니 차트 데이터 상태
  const [miniChartData, setMiniChartData] = useState<Record<string, PriceData[]>>({});
  const [miniChartsLoading, setMiniChartsLoading] = useState(true);

  // 미니 차트용 종목 목록 (데이터가 있는 종목만)
  const MINI_CHART_STOCKS = [
    { ticker: "005930", name: "삼성전자" },
    { ticker: "000020", name: "동서" },
  ];

  // 클라이언트 마운트 후 미니 차트 렌더링
  useEffect(() => {
    setMiniChartsReady(true);
  }, []);

  // 미니 차트 데이터 가져오기
  useEffect(() => {
    const fetchMiniChartData = async () => {
      setMiniChartsLoading(true);
      const results: Record<string, PriceData[]> = {};

      // 각 종목별로 병렬 조회
      const promises = MINI_CHART_STOCKS.map(async (stock) => {
        try {
          const stockChart = await apiClient.getStockChart(stock.ticker, "6mo"); // 6개월 데이터 (데이터 부족 대응)
          const chartData: PriceData[] = (stockChart.data || []).map((item) => {
            const dateStr = item.date;
            const formattedDate = dateStr.length === 8
              ? `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
              : dateStr;
            return {
              date: formattedDate,
              close: item.close || 0,
              volume: item.volume || 0,
              upper_band: 0,
              lower_band: 0,
              middle_band: 0,
            };
          });
          // 시간 순서대로 정렬 (오래된 데이터 first)
          chartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
          results[stock.ticker] = chartData;
        } catch (error) {
          console.error(`Failed to fetch mini chart data for ${stock.ticker}:`, error);
          results[stock.ticker] = [];
        }
      });

      await Promise.all(promises);
      setMiniChartData(results);
      setMiniChartsLoading(false);
    };

    fetchMiniChartData();
  }, []);

  useEffect(() => {
    // API에서 실제 데이터 가져오기
    const fetchChartData = async () => {
      setLoading(true);
      setError(null);
      try {
        // DB 기반 차트 데이터 가져오기
        // 데이터 부족 문제로 1년 데이터를 기본으로 사용
        const stockChart = await apiClient.getStockChart(selectedTicker, "1y");

        // DB 응답 (YYYY-MM-DD 형식)을 차트 데이터 형식으로 변환
        const chartData: PriceData[] = (stockChart.data || []).map((item) => {
          // 날짜 형식 변환: YYYYMMDD 또는 YYYY-MM-DD -> YYYY-MM-DD
          const dateStr = item.date;
          const formattedDate = dateStr.length === 8
            ? `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
            : dateStr;

          return {
            date: formattedDate,
            close: item.close || 0,
            volume: item.volume || 0,
            upper_band: 0,
            lower_band: 0,
            middle_band: 0,
          };
        });

        // 시간 순서대로 정렬 (오래된 데이터 first)
        chartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        // 데이터가 비있으면 안내 메시지 표시
        if (chartData.length === 0) {
          setError({
            title: "차트 데이터가 없습니다",
            message: "일봉 데이터는 매일 장 마감 후 자동으로 수집됩니다. 잠시 후 다시 확인해 주세요.",
            canRetry: true,
          });
        }

        setChartData(chartData);
      } catch (err) {
        console.error("차트 데이터 로드 실패:", err);
        setChartData([]);
        setError({
          title: "차트 데이터 로드 실패",
          message: "서버 연결에 실패했거나 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
          canRetry: true,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [selectedTicker]);

  // 데이터는 시간 순서대로 정렬됨 (오래된 데이터 first, 최신 데이터 last)
  const currentPrice = chartData[chartData.length - 1]?.close || 0;
  const previousPrice = chartData[0]?.close || 0;

  // 검색 필터링
  const filteredStocks = POPULAR_STOCKS.filter(
    (stock) =>
      stock.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stock.ticker.includes(searchQuery)
  );

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              📊 차트 시각화
            </h1>
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

      <div className="container mx-auto px-4 py-8">
        {/* 실시간 가격 헤더 - 선택된 종목 상세 표시 */}
        {selectedStockInfo && (
          <section className="mb-8">
            <ChartRealtimePriceHeader
              ticker={selectedStockInfo.ticker}
              name={selectedStockInfo.name}
            />
          </section>
        )}

        {/* 종목 선택 및 검색 */}
        <section className="mb-8">
          <div className="flex flex-wrap items-center gap-4">
            {/* 검색 입력 */}
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowSearchResults(e.target.value.length > 0);
                }}
                onFocus={() => setShowSearchResults(searchQuery.length > 0)}
                onBlur={() => setTimeout(() => setShowSearchResults(false), 200)}
                placeholder="종목명 또는 티커 검색..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
              {/* 검색 결과 드롭다운 */}
              {showSearchResults && filteredStocks.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg shadow-lg max-h-60 overflow-auto">
                  {filteredStocks.map((stock) => (
                    <button
                      key={stock.ticker}
                      onClick={() => {
                        setSelectedTicker(stock.ticker);
                        setSearchQuery("");
                        setShowSearchResults(false);
                      }}
                      className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between"
                    >
                      <span className="text-gray-900 dark:text-gray-100">
                        {stock.name}
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {stock.ticker}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 빠른 선택 버튼 */}
            <div className="flex gap-2">
              {POPULAR_STOCKS.map((stock) => (
                <button
                  key={stock.ticker}
                  onClick={() => setSelectedTicker(stock.ticker)}
                  className={`px-3 py-1 rounded-lg text-sm transition ${
                    selectedTicker === stock.ticker
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  {stock.name}
                </button>
              ))}
            </div>
            {chartData.length > 0 && (
              <div className="ml-4">
                <PriceChange current={currentPrice} previous={previousPrice} />
              </div>
            )}
          </div>
        </section>

        {/* 실시간 가격 그리드 - 모든 종목 */}
        <section className="mb-8">
          <ChartRealtimePrice
            stocks={POPULAR_STOCKS}
            selectedTicker={selectedTicker}
            onStockSelect={setSelectedTicker}
            compact={false}
          />
        </section>

        {/* 미니 차트 그리드 - 클라이언트에서만 렌더링 */}
        {miniChartsReady && (
          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              미니 차트
            </h2>
            {miniChartsLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
                {[...Array(2)].map((_, i) => (
                  <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow animate-pulse">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
                    <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
                {MINI_CHART_STOCKS.map((item) => {
                  const data = miniChartData[item.ticker] || [];
                  // 데이터는 시간 순서대로 정렬됨 (오래된 데이터 first, 최신 데이터 last)
                  const oldestPrice = data[0]?.close || 0;
                  const currentPrice = data[data.length - 1]?.close || 0;
                  const change = oldestPrice > 0 ? ((currentPrice - oldestPrice) / oldestPrice) * 100 : 0;

                  return (
                    <div
                      key={item.ticker}
                      className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow hover:shadow-lg transition cursor-pointer"
                      onClick={() => setSelectedTicker(item.ticker)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {item.name} ({item.ticker})
                        </span>
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            change >= 0
                              ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                              : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                          }`}
                        >
                          {change >= 0 ? "+" : ""}
                          {change.toFixed(2)}%
                        </span>
                      </div>
                      {data.length > 0 ? (
                        <>
                          <MiniChart data={data} height={80} />
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-2">
                            {currentPrice > 0 ? currentPrice.toLocaleString() + "원" : "-"}
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                          데이터 없음
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* 전체 차트 */}
        <section>
          {loading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-12 shadow text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-gray-500 dark:text-gray-400">차트 데이터를 불러오는 중...</p>
            </div>
          ) : error ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-12 shadow text-center">
              <div className="max-w-md mx-auto">
                <div className="text-yellow-500 text-4xl mb-4">⚠️</div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  {error.title}
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                  {error.message}
                </p>
                {error.canRetry && (
                  <button
                    onClick={() => {
                      // 선택된 종목 다시 선택하여 재요청 트리거
                      setSelectedTicker(selectedTicker);
                    }}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                  >
                    다시 시도
                  </button>
                )}
              </div>
            </div>
          ) : chartData.length > 0 ? (
            <FullStockChart data={chartData} height={400} />
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-12 shadow text-center">
              <p className="text-gray-500 dark:text-gray-400">데이터가 없습니다.</p>
            </div>
          )}
        </section>

        {/* 차트 설명 */}
        <section className="mt-8 bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
            차트 기능 안내
          </h3>
          <div className="grid md:grid-cols-3 gap-6 text-sm text-gray-600 dark:text-gray-400">
            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                📈 가격 차트
              </h4>
              <p>
                일봉 종가 라인 차트로 가격 추이를 한눈에 확인할 수 있습니다.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                📊 볼린저밴드
              </h4>
              <p>
                상단/하단 밴드로 변동성을 시각화합니다. 밴드 수축 시 매수 기회입니다.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                📉 거래량
              </h4>
              <p>
                거래량 바 차트로 거래 활동도를 확인할 수 있습니다.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
