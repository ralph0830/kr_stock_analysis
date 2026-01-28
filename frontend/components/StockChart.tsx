/**
 * 주식 가격 차트 컴포넌트
 * Recharts를 사용한 일봉 차트, 볼린저밴드, 거래량 표시
 */
"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import { formatPrice, formatPercent } from "@/lib/utils";

// 데이터 타입
export interface PriceData {
  date: string;
  close: number;
  volume: number;
  upper_band?: number;
  lower_band?: number;
  middle_band?: number;
}

interface StockChartProps {
  data: PriceData[];
  height?: number;
  showBollingerBands?: boolean;
  showVolume?: boolean;
}

// 볼린저밴드 영역
export function BollingerBands({ data }: { data: PriceData[] }) {
  const chartData = useMemo(() => {
    return data
      .map((item) => ({
        date: item.date,
        upper: item.upper_band || 0,
        lower: item.lower_band || 0,
      }))
      .filter((item) => item.upper > 0 && item.lower > 0);
  }, [data]);

  if (chartData.length === 0) return null;

  return (
    <AreaChart data={chartData} syncId="bollinger">
      <defs>
        <linearGradient id="colorUpper" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.1} />
          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="colorLower" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="#22c55e" stopOpacity={0} />
          <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1} />
        </linearGradient>
      </defs>
      <Area
        type="monotone"
        dataKey="upper"
        stroke="#ef4444"
        strokeWidth={1}
        fill="url(#colorUpper)"
        fillOpacity={0.3}
      />
      <Area
        type="monotone"
        dataKey="lower"
        stroke="#22c55e"
        strokeWidth={1}
        fill="url(#colorLower)"
        fillOpacity={0.3}
      />
      <XAxis dataKey="date" hide />
      <YAxis hide />
      <Tooltip
        content={({ active, payload }) => {
          if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
              <div className="bg-white dark:bg-gray-800 p-2 rounded shadow border border-gray-200 dark:border-gray-700">
                <p className="text-sm">{data.date}</p>
                <p className="text-sm text-red-500">상단: {formatPrice(data.upper)}</p>
                <p className="text-sm text-green-500">하단: {formatPrice(data.lower)}</p>
              </div>
            );
          }
          return null;
        }}
      />
    </AreaChart>
  );
}

// 거래량 바 차트
export function VolumeChart({ data }: { data: PriceData[] }) {
  const chartData = useMemo(() => {
    return data.map((item) => ({
      date: item.date,
      volume: item.volume,
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={chartData} syncId="volume">
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
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12 }}
          tickFormatter={(value) => {
            if (value >= 100000000) return `${(value / 100000000).toFixed(1)}억`;
            if (value >= 10000) return `${(value / 10000).toFixed(0)}천`;
            return value;
          }}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload;
              return (
                <div className="bg-white dark:bg-gray-800 p-2 rounded shadow border border-gray-200 dark:border-gray-700">
                  <p className="text-sm">{data.date}</p>
                  <p className="text-sm">거래량: {data.volume.toLocaleString()}주</p>
                </div>
              );
            }
            return null;
          }}
        />
        <Bar dataKey="volume" fill="#3b82f6" opacity={0.5} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// 메인 가격 차트
export function PriceChart({ data, height = 400 }: StockChartProps) {
  const chartData = useMemo(() => {
    return data.map((item) => ({
      date: item.date,
      price: item.close,
      upper: item.upper_band,
      lower: item.lower_band,
      middle: item.middle_band,
    }));
  }, [data]);

  const minPrice = useMemo(() => {
    const prices = data.map((d) => d.close);
    return Math.min(...prices) * 0.99;
  }, [data]);

  const maxPrice = useMemo(() => {
    const prices = data.map((d) => d.close);
    return Math.max(...prices) * 1.01;
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} syncId="price">
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
              const data = payload[0].payload;
              return (
                <div className="bg-white dark:bg-gray-800 p-3 rounded shadow border border-gray-200 dark:border-gray-700">
                  <p className="text-sm font-medium mb-1">{data.date}</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {formatPrice(data.price)}
                  </p>
                </div>
              );
            }
            return null;
          }}
        />
        <Legend />

        {/* 볼린저밴드 상단 */}
        {data.some((d) => d.upper_band) && (
          <Line
            type="monotone"
            dataKey="upper"
            stroke="#ef4444"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
            name="상단밴드"
          />
        )}

        {/* 볼린저밴드 하단 */}
        {data.some((d) => d.lower_band) && (
          <Line
            type="monotone"
            dataKey="lower"
            stroke="#22c55e"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
            name="하단밴드"
          />
        )}

        {/* 볼린저밴드 중단 */}
        {data.some((d) => d.middle_band) && (
          <Line
            type="monotone"
            dataKey="middle"
            stroke="#94a3b8"
            strokeWidth={1}
            strokeDasharray="2 2"
            dot={false}
            name="중단밴드"
          />
        )}

        {/* 종가 라인 */}
        <Line
          type="monotone"
          dataKey="price"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          name="종가"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// 전체 차트 (가격 + 볼린저밴드 + 거래량)
export function FullStockChart({ data, height = 400 }: StockChartProps) {
  return (
    <div className="space-y-4">
      {/* 가격 차트 + 볼린저밴드 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          가격 차트
        </h3>
        <PriceChart data={data} height={height} showBollingerBands={true} />
      </div>

      {/* 거래량 차트 */}
      {data.some((d) => d.volume > 0) && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
            거래량
          </h3>
          <VolumeChart data={data} />
        </div>
      )}
    </div>
  );
}

// 미니 차트 (스파크라인)
export function MiniChart({ data, height = 60 }: { data: PriceData[]; height?: number }) {
  const chartData = useMemo(() => {
    return data.map((item) => ({
      date: item.date,
      price: item.close,
    }));
  }, [data]);

  const lastPrice = data[data.length - 1]?.close || 0;
  const firstPrice = data[0]?.close || 0;
  const isPositive = lastPrice >= firstPrice;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData}>
        <XAxis hide />
        <YAxis hide />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload;
              return (
                <div className="bg-white dark:bg-gray-800 p-2 rounded shadow border border-gray-200 dark:border-gray-700">
                  <p className="text-sm">{data.date}</p>
                  <p className="text-sm font-medium">{formatPrice(data.price)}</p>
                </div>
              );
            }
            return null;
          }}
        />
        <Line
          type="monotone"
          dataKey="price"
          stroke={isPositive ? "#ef4444" : "#22c55e"}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// 가격 변화율 표시
export function PriceChange({ current, previous }: { current: number; previous: number }) {
  const change = current - previous;
  const changePercent = ((change / previous) * 100);

  const isPositive = change >= 0;

  return (
    <div className="flex items-center gap-2">
      <span className={`text-sm ${isPositive ? "text-red-600" : "text-blue-600"}`}>
        {formatPrice(current)}
      </span>
      <span
        className={`text-xs px-2 py-1 rounded ${
          isPositive
            ? "bg-red-100 text-red-800"
            : "bg-blue-100 text-blue-800"
        }`}
      >
        {isPositive ? "+" : ""}
        {changePercent.toFixed(2)}%
      </span>
    </div>
  );
}
