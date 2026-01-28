/**
 * API 응답 타입 정의
 */

export interface Signal {
  ticker: string;
  name: string;
  signal_type: string;
  score: number | ScoreDetail;
  grade: string;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;
  position_size?: number;
  reasons?: string[];
  created_at: string;
}

export interface ScoreDetail {
  total: number;
  news: number;
  volume: number;
  chart: number;
  candle: number;
  period: number;
  flow: number;
}

export interface SectorItem {
  name: string;
  signal: "bullish" | "neutral" | "bearish";
  change_pct: number;
  score?: number;
}

export interface MarketGateStatus {
  status: "GREEN" | "YELLOW" | "RED";
  level: number;
  kospi_status: string;
  kosdaq_status: string;
  kospi_close?: number;
  kospi_change_pct?: number;
  kosdaq_close?: number;
  kosdaq_change_pct?: number;
  sectors: SectorItem[];
  updated_at: string;
}

export interface StockPrice {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp?: string;
}

export interface HealthCheck {
  status: string;
  service: string;
  version: string;
  timestamp?: string;
}

export interface SystemOverview {
  status: string;
  uptime_seconds: number;
  timestamp: string;
  services: Record<string, string>;
}

export interface ConnectionInfo {
  active_connections: number;
  subscriptions: Record<string, number>;
  broadcaster_running: boolean;
}

// WebSocket 타입
export type WSMessageType =
  | "connected"
  | "subscribed"
  | "unsubscribed"
  | "price_update"
  | "error"
  | "ping"
  | "pong";

export interface WSMessage {
  type: WSMessageType;
  [key: string]: any;
}

export interface RealtimePrice {
  ticker: string;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  timestamp: string;
}

// ============================================================================
// 필터/정렬 타입
// ============================================================================

/**
 * 시그널 필터 인터페이스
 */
export interface ISignalFilters {
  grades: string[];      // ['S', 'A', 'B', 'C']
  minScore: number;      // 0-12
  maxScore: number;      // 0-12
  signalType: string;    // 'all' | 'VCP' | '종가베팅'
}

/**
 * 정렬 설정 인터페이스
 */
export interface ISortConfig {
  sortBy: 'score' | 'grade' | 'created_at';
  order: 'asc' | 'desc';
}

// ============================================================================
// 종목 관련 타입
// ============================================================================

/**
 * 종목 상세 정보 인터페이스
 */
export interface IStockDetail {
  ticker: string;
  name: string;
  market: string;
  sector?: string;
  current_price?: number;
  price_change?: number;
  price_change_pct?: number;
  volume?: number;
  updated_at?: string;
}

/**
 * 차트 데이터 포인트 인터페이스
 */
export interface IChartPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * 종목 차트 응답 인터페이스
 */
export interface IStockChart {
  ticker: string;
  period: string;
  data: IChartPoint[];
  total_points: number;
}

/**
 * 수급 데이터 포인트 인터페이스
 */
export interface IFlowDataPoint {
  date: string;
  foreign_net: number;
  inst_net: number;
  foreign_net_amount?: number;
  inst_net_amount?: number;
  supply_demand_score?: number;
}

/**
 * 종목 수급 응답 인터페이스
 */
export interface IFlowHistory {
  ticker: string;
  period_days: number;
  data: IFlowDataPoint[];
  smartmoney_score: number;
  total_points: number;
}

/**
 * 시그널 히스토리 아이템 인터페이스
 */
export interface ISignalHistoryItem {
  id: number;
  ticker: string;
  signal_type: "VCP" | "JONGGA_V2";
  signal_date: string;
  status: "OPEN" | "CLOSED";
  score?: number;
  grade?: string;
  entry_price?: number;
  exit_price?: number;
  entry_time?: string;
  exit_time?: string;
  return_pct?: number;
  exit_reason?: string;
}

/**
 * 종목 시그널 히스토리 응답 인터페이스
 */
export interface ISignalHistory {
  ticker: string;
  total_signals: number;
  open_signals: number;
  closed_signals: number;
  avg_return_pct?: number;
  win_rate?: number;
  signals: ISignalHistoryItem[];
}

/**
 * 누적 수익률 데이터 포인트
 */
export interface ICumulativeReturn {
  date: string
  value: number
  return_pct?: number
}

/**
 * 수익률 분석 결과 인터페이스
 */
export interface IReturnAnalysis {
  total_signals: number
  closed_signals: number
  win_rate: number
  avg_return: number
  mdd: number
  best_return: number | null
  worst_return: number | null
  cumulative_returns: ICumulativeReturn[]
  returns: number[]
}

/**
 * 뉴스 아이템 인터페이스
 */
export interface INewsItem {
  id: string
  ticker: string
  title: string
  content: string
  date: string
  source?: string
  url?: string
  sentiment_score?: number  // -1.0 ~ 1.0
  keywords?: string[]
  summary?: string
}

/**
 * 뉴스 피드 응답 인터페이스
 */
export interface INewsFeed {
  ticker: string
  total_news: number
  avg_sentiment: number  // -1.0 ~ 1.0
  sentiment_label: "긍정" | "부정" | "중립"
  news: INewsItem[]
}

// ============================================================================
// AI 분석 타입
// ============================================================================

/**
 * AI 종목 분석 응답 인터페이스
 */
export interface IAIAnalysis {
  ticker: string
  name: string
  analysis_date?: string
  sentiment?: "positive" | "negative" | "neutral"
  score?: number  // -1.0 ~ 1.0
  summary?: string
  keywords: string[]
  recommendation?: "BUY" | "SELL" | "HOLD" | "OVERWEIGHT" | "UNDERWEIGHT"
}

/**
 * AI 분석 아이템 (목록용)
 */
export interface IAIAnalysisItem {
  id: number
  ticker: string
  analysis_date: string
  sentiment: string
  score: number
  summary: string
  keywords: string[]
  recommendation: string
}

/**
 * AI 분석 목록 응답
 */
export interface IAIAnalysisList {
  analyses: IAIAnalysisItem[]
  total: number
  analysis_date?: string
}

/**
 * AI 분석 가능 날짜 응답
 */
export interface IAIHistoryDates {
  dates: string[]
  total: number
}

// ============================================================================
// 시스템 관리 타입
// ============================================================================

/**
 * 데이터 상태 아이템
 */
export interface IDataStatusItem {
  name: string
  status: "OK" | "ERROR" | "STALE"
  last_update?: string
  record_count?: number
  error_message?: string
}

/**
 * 데이터 상태 응답
 */
export interface IDataStatus {
  total_stocks: number
  updated_stocks: number
  last_update?: string
  data_files: Record<string, string>
  details: IDataStatusItem[]
}

/**
 * 서비스 상태 아이템
 */
export interface IServiceStatusItem {
  name: string
  status: "up" | "down" | "degraded"
  response_time_ms?: number
  error_message?: string
}

/**
 * 시스템 헬스 체크 응답
 */
export interface ISystemHealth {
  status: "healthy" | "degraded" | "unhealthy"
  services: Record<string, string>
  timestamp: string
  uptime_seconds?: number
  database_status: string
  redis_status: string
  celery_status?: string
}

// ============================================================================
// 스캔 트리거 타입
// ============================================================================

/**
 * VCP 시그널 아이템
 */
export interface IVCPSignalItem {
  ticker: string
  name: string
  signal_type: string
  score: number
  grade: string
  entry_price?: number
  target_price?: number
  detected_at?: string
}

/**
 * VCP 스캔 응답
 */
export interface IVCPScanResponse {
  status: "started" | "completed" | "error"
  scanned_count: number
  found_signals: number
  started_at: string
  completed_at?: string
  error_message?: string
  signals: IVCPSignalItem[]
}

/**
 * 시그널 생성 응답
 */
export interface ISignalGenerationResponse {
  status: "started" | "completed" | "error"
  generated_count: number
  started_at: string
  completed_at?: string
  error_message?: string
}

/**
 * 스캔 상태 응답
 */
export interface IScanStatus {
  vcp_scan_status: "idle" | "running" | "completed" | "error"
  signal_generation_status: "idle" | "running" | "completed" | "error"
  last_vcp_scan?: string
  last_signal_generation?: string
  current_operation?: string
  progress_percentage?: number
}

// ============================================================================
// 백테스트 KPI 타입
// ============================================================================

/**
 * 백테스트 전략별 통계 아이템
 */
export interface IBacktestStatsItem {
  strategy: string;
  status: "OK" | "Accumulating" | "No Data";
  count: number;
  win_rate?: number;
  avg_return?: number;
  profit_factor?: number;
  message?: string;
}

/**
 * 백테스트 KPI 응답 (대시보드용)
 */
export interface IBacktestKPI {
  vcp: IBacktestStatsItem;
  closing_bet: IBacktestStatsItem;
}
