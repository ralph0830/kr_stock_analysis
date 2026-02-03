/**
 * 캔들스틱 차트 및 MACD 히스토그램 컴포넌트
 * Recharts를 사용한 한국 주식 시장 캔들스틱 차트 (양봉: 빨간색, 음봉: 파란색)
 */
"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import { formatPrice } from "@/lib/utils";

// OHLCV 데이터 타입
export interface OHLCVData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 캔들스틱 데이터 타입 (내부 사용)
interface CandlestickData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  isBullish: boolean; // 양봉 (close > open)
  ma5?: number; // 5일 이동평균
  ma20?: number; // 20일 이동평균
}

// MACD 데이터 타입
export interface MACDDataPoint {
  date: string;
  macd: number;
  signal: number;
  histogram: number;
}

interface CandlestickChartProps {
  data: OHLCVData[];
  height?: number;
  showMA?: boolean; // 이동평균선 표시
  showVolume?: boolean; // 거래량 표시
}

interface MACDChartProps {
  data: MACDDataPoint[];
  height?: number;
}

/**
 * OHLCV 데이터를 캔들스틱 형식으로 변환
 * 이동평균 계산 및 양봉/음봉 판별
 */
export function calculateCandlestickData(
  data: OHLCVData[],
  options: { ma5?: boolean; ma20?: boolean } = {}
): CandlestickData[] {
  const { ma5: calcMA5 = false, ma20: calcMA20 = false } = options;

  return data.map((item, index) => {
    const isBullish = item.close > item.open;

    const result: CandlestickData = {
      date: item.date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
      volume: item.volume,
      isBullish,
    };

    // 5일 이동평균 계산
    if (calcMA5 && index >= 4) {
      const sum5 = data
        .slice(index - 4, index + 1)
        .reduce((sum, d) => sum + d.close, 0);
      result.ma5 = sum5 / 5;
    }

    // 20일 이동평균 계산
    if (calcMA20 && index >= 19) {
      const sum20 = data
        .slice(index - 19, index + 1)
        .reduce((sum, d) => sum + d.close, 0);
      result.ma20 = sum20 / 20;
    }

    return result;
  });
}

/**
 * 가격 배열로 MACD 계산
 * @param prices 종가 배열 (과거에서 최신 순서)
 * @param date 현재 날짜
 * @returns MACD 데이터 포인트
 */
export function calculateMACDFromPrices(
  prices: number[],
  date: string
): MACDDataPoint {
  const slowPeriod = 26;
  const fastPeriod = 12;
  const signalPeriod = 9;

  // 데이터 부족 시 기본값 반환
  if (prices.length < slowPeriod) {
    return { date, macd: 0, signal: 0, histogram: 0 };
  }

  // EMA 계산 함수
  const calculateEMA = (data: number[], period: number): number => {
    if (data.length < period) return 0;
    const multiplier = 2 / (period + 1);
    let ema = data.slice(0, period).reduce((sum, p) => sum + p, 0) / period;

    for (let i = period; i < data.length; i++) {
      ema = (data[i] - ema) * multiplier + ema;
    }
    return ema;
  };

  // MACD = 12일 EMA - 26일 EMA
  const emaFast = calculateEMA(prices, fastPeriod);
  const emaSlow = calculateEMA(prices, slowPeriod);
  const macd = emaFast - emaSlow;

  // Signal = MACD의 9일 EMA (단순화: 현재 MACD 사용)
  const signal = macd * 0.9;

  // Histogram = MACD - Signal
  const histogram = macd - signal;

  return { date, macd, signal, histogram };
}

/**
 * 캔들스틱 차트 컴포넌트
 */
export function CandlestickChart({
  data,
  height = 400,
  showMA = true,
  showVolume = false,
}: CandlestickChartProps) {
  // 캔들스틱 데이터 계산
  const chartData = useMemo(
    () => calculateCandlestickData(data, { ma5: showMA, ma20: showMA }),
    [data, showMA]
  );

  // Y축 범위 계산
  const allPrices = data.flatMap((d) => [d.high, d.low]);
  const minPrice = Math.min(...allPrices) * 0.99;
  const maxPrice = Math.max(...allPrices) * 1.01;

  // 캔들 색상 (한국 주식 시장: 양봉=빨간색, 음봉=파란색)
  const getCandleColor = (isBullish: boolean) => (isBullish ? "#ef4444" : "#3b82f6");

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} syncId="candlestick">
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
        <XAxis
          dataKey="date"
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12 }}
          tickFormatter={(value) => {
            const date = new Date(value);
            return `${date.getMonth() + 1}/${date.getDate()}`;
          }}
        />
        <YAxis
          domain={[minPrice, maxPrice]}
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12 }}
          tickFormatter={(value) => formatPrice(value)}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload as CandlestickData;
              return (
                <div className="bg-white dark:bg-gray-800 p-3 rounded shadow border border-gray-200 dark:border-gray-700">
                  <p className="text-sm font-medium mb-1">{data.date}</p>
                  <p className="text-sm">시가: {formatPrice(data.open)}</p>
                  <p className="text-sm">고가: {formatPrice(data.high)}</p>
                  <p className="text-sm">저가: {formatPrice(data.low)}</p>
                  <p className="text-sm font-bold">종가: {formatPrice(data.close)}</p>
                  {data.ma5 && (
                    <p className="text-xs text-gray-500">MA5: {formatPrice(data.ma5)}</p>
                  )}
                  {data.ma20 && (
                    <p className="text-xs text-gray-500">MA20: {formatPrice(data.ma20)}</p>
                  )}
                </div>
              );
            }
            return null;
          }}
        />
        <Legend />

        {/* 이동평균선 */}
        {showMA && chartData.some((d) => d.ma5) && (
          <Line
            type="monotone"
            dataKey="ma5"
            stroke="#f59e0b"
            strokeWidth={1}
            dot={false}
            name="MA5"
          />
        )}
        {showMA && chartData.some((d) => d.ma20) && (
          <Line
            type="monotone"
            dataKey="ma20"
            stroke="#8b5cf6"
            strokeWidth={1}
            dot={false}
            name="MA20"
          />
        )}

        {/* 거래량 바 (하단에 표시) */}
        {showVolume && (
          <Bar
            dataKey="volume"
            fill="#3b82f6"
            opacity={0.3}
            yAxisId="volume"
            name="거래량"
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/**
 * MACD 히스토그램 차트 컴포넌트
 */
export function MACDChart({ data, height = 200 }: MACDChartProps) {
  // Histogram 색상 (양수=빨간색, 음수=파란색)
  const getHistogramColor = (value: number) => (value >= 0 ? "#ef4444" : "#3b82f6");

  // 양수/음수 분리된 데이터 생성
  const chartData = useMemo(() => {
    return data.map((item) => ({
      ...item,
      positiveHistogram: item.histogram > 0 ? item.histogram : 0,
      negativeHistogram: item.histogram < 0 ? Math.abs(item.histogram) : 0,
    }));
  }, [data]);

  // Y축 범위
  const allValues = data.flatMap((d) => [d.macd, d.signal]);
  const minValue = Math.min(...allValues, 0);
  const maxValue = Math.max(...allValues, 0);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} syncId="macd">
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
        <XAxis
          dataKey="date"
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12 }}
          tickFormatter={(value) => {
            const date = new Date(value);
            return `${date.getMonth() + 1}/${date.getDate()}`;
          }}
        />
        <YAxis
          domain={[minValue, maxValue]}
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12 }}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload as MACDDataPoint;
              return (
                <div className="bg-white dark:bg-gray-800 p-3 rounded shadow border border-gray-200 dark:border-gray-700">
                  <p className="text-sm font-medium mb-1">{data.date}</p>
                  <p className="text-sm">MACD: {data.macd.toFixed(2)}</p>
                  <p className="text-sm">Signal: {data.signal.toFixed(2)}</p>
                  <p
                    className={`text-sm font-bold ${
                      data.histogram >= 0 ? "text-red-600" : "text-blue-600"
                    }`}
                  >
                    Histogram: {data.histogram > 0 ? "+" : ""}
                    {data.histogram.toFixed(2)}
                  </p>
                </div>
              );
            }
            return null;
          }}
        />
        <Legend />

        {/* 0 기준선 */}
        <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="2 2" />

        {/* MACD 라인 */}
        <Line
          type="monotone"
          dataKey="macd"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          name="MACD"
        />

        {/* Signal 라인 */}
        <Line
          type="monotone"
          dataKey="signal"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          name="Signal"
        />

        {/* Histogram 바 - positiveHistogram과 negativeHistogram 사용 */}
        <Bar
          dataKey="positiveHistogram"
          fill="#ef4444"
          opacity={0.5}
          name="Histogram (+)"
          stackId="histogram"
        />
        <Bar
          dataKey="negativeHistogram"
          fill="#3b82f6"
          opacity={0.5}
          name="Histogram (-)"
          stackId="histogram"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
