/**
 * Daytrading Signal Normalizer
 *
 * 백엔드 응답 데이터를 IDaytradingSignal 형식으로 변환하는 유틸리티 함수
 * 중복되는 변환 로직을 제거하기 위해 추출됨
 */

import type { IDaytradingSignal } from "@/types"

/**
 * Candidate 데이터 타입 (백엔드에서 반환하는 candidates 필드 형식)
 */
export interface CandidateData {
  ticker: string
  name?: string
  price?: number
  current_price?: number
  scan_time?: string
  score?: number
  total_score?: number
  grade?: string
  market?: string
  checks?: IDaytradingSignal["checks"]
  signal_type?: IDaytradingSignal["signal_type"]
  entry_price?: number
  target_price?: number
  stop_loss?: number
  detected_at?: string
}

/**
 * Scan 응답 데이터 타입
 */
export interface ScanResponseData {
  signals?: IDaytradingSignal[]
  candidates?: CandidateData[]
}

/**
 * 점수 기본 signal_type 결정
 */
function getSignalTypeByScore(score: number): IDaytradingSignal["signal_type"] {
  if (score >= 80) return "STRONG_BUY"
  if (score >= 60) return "BUY"
  return "MODERATE_BUY"
}

/**
 * 시장 코드 결정 (티커 기반)
 */
function getMarketByTicker(ticker: string): "KOSPI" | "KOSDAQ" {
  // KOSDAQ은 0으로 시작하지만, 실제로는 KOSPI도 0으로 시작할 수 있음
  // 정확한 판단을 위해서는 DB 조회가 필요하지만, 여기서는 간단히 처리
  return ticker?.startsWith("0") ? "KOSDAQ" : "KOSPI"
}

/**
 * market 문자열을 "KOSPI" | "KOSDAQ" 타입으로 변환
 */
function normalizeMarket(market?: string): "KOSPI" | "KOSDAQ" {
  if (!market) return "KOSPI"
  if (market === "KOSPI" || market === "KOSDAQ") {
    return market
  }
  // 문자열이 올바르지 않은 경우 ticker 기반 판단
  return "KOSPI"
}

/**
 * grade 문자열을 "A" | "S" | "B" | "C" 타입으로 변환
 */
function normalizeGrade(grade?: string): "S" | "A" | "B" | "C" {
  if (!grade) return "C"
  if (grade === "S" || grade === "A" || grade === "B" || grade === "C") {
    return grade
  }
  // 문자열이 올바르지 않은 경우 기본값 "C"
  return "C"
}

/**
 * Candidate 데이터를 IDaytradingSignal 형식으로 변환
 */
function normalizeCandidate(candidate: CandidateData): IDaytradingSignal {
  const scoreValue = candidate.total_score ?? candidate.score ?? 0

  return {
    ticker: candidate.ticker,
    name: candidate.name ?? "",
    market: normalizeMarket(candidate.market),
    total_score: scoreValue,
    grade: normalizeGrade(candidate.grade),
    checks: candidate.checks ?? [],
    signal_type: candidate.signal_type ?? getSignalTypeByScore(scoreValue),
    current_price: candidate.price ?? candidate.current_price,
    entry_price: candidate.entry_price,
    target_price: candidate.target_price,
    stop_loss: candidate.stop_loss,
    detected_at: candidate.detected_at ?? candidate.scan_time ?? new Date().toISOString(),
  }
}

/**
 * 백엔드 응답 데이터를 IDaytradingSignal[] 형식으로 정규화
 *
 * @param rawData - 백엔드 응답 데이터 (signals 또는 candidates)
 * @returns 정규화된 시그널 배열
 *
 * @example
 * ```ts
 * const response = await apiClient.scanDaytradingMarket(request)
 * const signals = normalizeDaytradingSignals(response.data)
 * ```
 */
export function normalizeDaytradingSignals(rawData: ScanResponseData | unknown): IDaytradingSignal[] {
  // 응답 데이터에서 signals 또는 candidates 추출
  const responseData = rawData as ScanResponseData | undefined
  const rawSignals = responseData?.signals || responseData?.candidates || []

  if (rawSignals.length === 0) {
    return []
  }

  // 이미 IDaytradingSignal 형식인지 확인 (checks 필드 존재 여부로 판단)
  const hasChecks = rawSignals.some(
    (s) => s && typeof s === "object" && "checks" in s && Array.isArray(s.checks)
  )

  if (hasChecks) {
    // 이미 올바른 형식이면 그대로 반환
    return rawSignals as IDaytradingSignal[]
  }

  // candidates 형식이면 변환
  return rawSignals.map((candidate) => normalizeCandidate(candidate as CandidateData))
}
