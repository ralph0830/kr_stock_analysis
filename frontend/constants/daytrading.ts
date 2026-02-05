/**
 * 단타 추천(Daytrading) 관련 상수
 */

/**
 * 체크리스트 라벨
 */
export const CHECK_LABELS: Record<string, string> = {
  "거래량 폭증": "거래량 폭증",
  "모멘텀 돌파": "모멘텀 돌파",
  "박스권 탈출": "박스권 탈출",
  "5일선 위": "5일선 위",
  "기관 매수": "기관 매수",
  "낙폭 과대": "낙폭 과대",
  "외국인 순매수": "외국인 순매수",
}

/**
 * 체크리스트 접근성 설명
 */
export const CHECK_DESCRIPTIONS: Record<string, string> = {
  "거래량 폭증": "전일 대비 거래량이 급증함",
  "모멘텀 돌파": "모멘텀이 돌파하여 상승 추세",
  "박스권 탈출": "횡보 박스권을 상향 돌파",
  "5일선 위": "현재가가 5일 이동평균선 위쪽",
  "기관 매수": "기관 투자자의 순매수",
  "낙폭 과대": "최근 낙폭이 과도하여 반등 가능성",
  "외국인 순매수": "외국인 투자자의 순매수",
}

/**
 * 시그널 타입 색상
 */
export const SIGNAL_TYPE_COLORS: Record<string, string> = {
  STRONG_BUY: "bg-red-100 text-red-800 border-red-300",
  BUY: "bg-orange-100 text-orange-800 border-orange-300",
  MODERATE_BUY: "bg-yellow-100 text-yellow-800 border-yellow-300",
  NEUTRAL: "bg-gray-100 text-gray-800 border-gray-300",
}

/**
 * 시그널 타입 라벨
 */
export const SIGNAL_TYPE_LABELS: Record<string, string> = {
  STRONG_BUY: "강력 매수",
  BUY: "매수",
  MODERATE_BUY: "약간 매수",
  NEUTRAL: "중립",
}

/**
 * 단타 추천 설명 텍스트
 */
export const DAYTRADING_DESCRIPTION = "7가지 체크리스트를 기반으로 당일 매수 후 익일 일봉 기준으로 매도하는 단타 매매 기회를 제공합니다."

/**
 * 단타 체크리스트 항목
 */
export const DAYTRADING_CHECKLIST = [
  "거래량 폭증",
  "모멘텀 돌파",
  "박스권 탈출",
  "5일선 위",
  "기관 매수",
  "낙폭 과대",
  "외국인 순매수",
] as const
