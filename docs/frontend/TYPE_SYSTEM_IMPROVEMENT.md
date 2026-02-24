# TypeScript Type System Improvement Plan

**Date:** 2026-02-06
**Author:** Frontend Architect Agent
**Status**: Planning Phase

---

## Problem Statement

현재 타입 시스템은 `types/index.ts` (810라인)에 모든 타입이集中되어 있어 다음과 같은 문제가 있습니다:

1. **파일 크기**: 810라인으로 너무 커서 탐색과 유지보수가 어려움
2. **책임 명확성 부족**: API 타입, 컴포넌트 Props, 유틸리티 타입이 혼재
3. **재사용성 낮음**: 관련 없는 타입끼리 묶여 있어 필요한 부분만 import 어려움
4. **순환 의존성 위험**: 모든 타입이 하나의 파일에 있어 순환 참조 위험

---

## Current Type Structure Analysis

### types/index.ts (810 lines)

```typescript
// API 응답 타입 (18개)
export interface Signal { ... }
export interface MarketGateStatus { ... }
export interface StockPrice { ... }
export interface IStockDetail { ... }
export interface IStockChart { ... }
export interface IFlowHistory { ... }
export interface ISignalHistory { ... }
export interface IAIAnalysis { ... }
export interface INewsFeed { ... }
// ... 9개 더

// WebSocket 타입 (10개)
export type WSMessageType = ...
export interface IWSConnectedMessage { ... }
export interface IWSPriceUpdateMessage { ... }
export interface IWSMarketGateUpdateMessage { ... }
export interface IWSSignalUpdateMessage { ... }
// ... 6개 더

// 필터/정렬 타입 (2개)
export interface ISignalFilters { ... }
export interface ISortConfig { ... }

// 종목 관련 타입 (5개)
export interface IStockDetail { ... }
export interface IChartPoint { ... }
export interface IStockChart { ... }
export interface IFlowDataPoint { ... }
export interface IFlowHistory { ... }

// 시스템 관리 타입 (6개)
export interface IDataStatus { ... }
export interface IServiceStatusItem { ... }
export interface ISystemHealth { ... }
export interface IVCPScanResponse { ... }
export interface ISignalGenerationResponse { ... }
export interface IScanStatus { ... }

// 챗봇 타입 (6개)
export interface IChatMessage { ... }
export interface IChatRequest { ... }
export interface IChatResponse { ... }
export interface IMarkdownPart { ... }
export interface IChatContext { ... }
export interface IChatSession { ... }

// Performance API 타입 (5개)
export interface ICumulativeReturnPoint { ... }
export interface ICumulativeReturnResponse { ... }
export interface ISignalPerformanceResponse { ... }
export interface IPeriodPerformanceResponse { ... }
export interface ITopPerformersResponse { ... }

// News API 타입 (2개)
export interface INewsApiItem { ... }
export interface INewsListResponse { ... }

// Daytrading Scanner API 타입 (4개)
export interface IDaytradingCheck { ... }
export type DaytradingSignalType = ...
export interface IDaytradingSignal { ... }
export interface IDaytradingSignalsResponse { ... }
export interface IDaytradingScanRequest { ... }
export interface IDaytradingAnalyzeRequest { ... }
```

---

## Proposed Type Structure

### New Directory Structure

```
types/
├── index.ts                    # 모든 타입 re-export (하위 호환성)
│
├── api/                        # API 레이어 타입
│   ├── index.ts                # API 타입 re-export
│   ├── signals.ts              # 시그널 API 타입
│   ├── stocks.ts               # 종목 API 타입
│   ├── market-gate.ts          # Market Gate API 타입
│   ├── ai-analysis.ts          # AI 분석 API 타입
│   ├── chatbot.ts              # 챗봇 API 타입
│   ├── performance.ts          # Performance API 타입
│   ├── news.ts                 # 뉴스 API 타입
│   ├── daytrading.ts           # 단타 스캐너 API 타입
│   ├── system.ts               # 시스템 API 타입
│   └── common.ts               # 공통 API 응답 타입
│
├── websocket/                  # WebSocket 타입
│   ├── index.ts
│   ├── messages.ts             # 메시지 타입
│   ├── client.ts               # WebSocket 클라이언트 타입
│   └── hooks.ts                # Hook 관련 타입
│
├── components/                 # 컴포넌트 Props 타입
│   ├── index.ts
│   ├── tables.ts               # 테이블 컴포넌트 타입
│   ├── cards.ts                # 카드 컴포넌트 타입
│   ├── charts.ts               # 차트 컴포넌트 타입
│   ├── forms.ts                # 폼 컴포넌트 타입
│   └── filters.ts              # 필터 컴포넌트 타입
│
├── features/                   # 기능별 타입
│   ├── index.ts
│   ├── signals.ts              # 시그널 관련 타입
│   ├── filters.ts              # 필터/정렬 타입
│   ├── watchlist.ts            # 관심종목 타입
│   └── scanner.ts              # 스캐너 타입
│
└── utils/                      # 유틸리티 타입
    ├── index.ts
    ├── common.ts               # 공통 유틸리티 타입
    └── formatters.ts           # 포매터 타입
```

---

## Type Migration Plan

### Phase 1: API Types (Week 1)

#### 1.1 Common API Types (`types/api/common.ts`)

```typescript
/**
 * 공통 API 응답 구조
 */
export interface IAPIResponse<T> {
  success: boolean
  data: T
  message?: string
  error?: string
  timestamp: string
}

/**
 * 페이지네이션 요청
 */
export interface IPaginationRequest {
  page: number
  pageSize: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

/**
 * 페이지네이션 응답
 */
export interface IPaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

/**
 * 필터 요청
 */
export interface IFilterRequest {
  filters: Record<string, any>
  operator?: 'AND' | 'OR'
}
```

#### 1.2 Signal API Types (`types/api/signals.ts`)

```typescript
/**
 * 점수 상세
 */
export interface IScoreDetail {
  total: number
  news: number
  volume: number
  chart: number
  candle: number
  period: number
  flow: number
}

/**
 * VCP/종가베팅 시그널
 */
export interface ISignal {
  ticker: string
  name: string
  signal_type: 'VCP' | 'JONGGA_V2' | 'DAYTRADING'
  score: number | IScoreDetail
  grade: 'S' | 'A' | 'B' | 'C'
  entry_price?: number
  target_price?: number
  stop_loss?: number
  position_size?: number
  reasons?: string[]
  created_at: string
}

/**
 * 시그널 목록 응답
 */
export interface ISignalsResponse {
  signals: ISignal[]
  count: number
  generated_at?: string
}
```

#### 1.3 Stock API Types (`types/api/stocks.ts`)

```typescript
/**
 * OHLCV 데이터 포인트
 */
export interface IOHLCVPoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/**
 * 종목 기본 정보
 */
export interface IStockBasicInfo {
  ticker: string
  name: string
  market: 'KOSPI' | 'KOSDAQ'
  sector?: string
}

/**
 * 종목 상세 정보
 */
export interface IStockDetail extends IStockBasicInfo {
  current_price?: number
  price_change?: number
  price_change_pct?: number
  volume?: number
  updated_at?: string
}

/**
 * 종목 차트 데이터
 */
export interface IStockChart {
  ticker: string
  period: string
  data: IOHLCVPoint[]
  total_points: number
}

/**
 * 수급 데이터 포인트
 */
export interface IFlowDataPoint {
  date: string
  foreign_net: number
  inst_net: number
  foreign_net_amount?: number
  inst_net_amount?: number
  supply_demand_score?: number
}

/**
 * 수급 데이터 응답
 */
export interface IFlowHistory {
  ticker: string
  period_days: number
  data: IFlowDataPoint[]
  smartmoney_score: number
  total_points: number
}
```

#### 1.4 Market Gate API Types (`types/api/market-gate.ts`)

```typescript
/**
 * 섹터 항목
 */
export interface ISectorItem {
  name: string
  signal: 'bullish' | 'neutral' | 'bearish'
  change_pct: number
  score?: number
}

/**
 * Market Gate 상태
 */
export interface IMarketGateStatus {
  status: 'GREEN' | 'YELLOW' | 'RED'
  level: number
  kospi_status: string
  kosdaq_status: string
  kospi_close?: number
  kospi_change_pct?: number
  kosdaq_close?: number
  kosdaq_change_pct?: number
  sectors: ISectorItem[]
  updated_at: string
}
```

#### 1.5 Daytrading API Types (`types/api/daytrading.ts`)

```typescript
/**
 * 단타 체크리스트 항목
 */
export interface IDaytradingCheck {
  name: string
  status: 'passed' | 'failed'
  points: number
}

/**
 * 단타 시그널 타입
 */
export type DaytradingSignalType =
  | 'STRONG_BUY'
  | 'BUY'
  | 'MODERATE_BUY'
  | 'NEUTRAL'

/**
 * 단타 시그널
 */
export interface IDaytradingSignal {
  ticker: string
  name: string
  market: 'KOSPI' | 'KOSDAQ'
  total_score: number
  grade: 'S' | 'A' | 'B' | 'C'
  checks: IDaytradingCheck[]
  signal_type: DaytradingSignalType
  current_price?: number
  entry_price?: number
  target_price?: number
  stop_loss?: number
  detected_at?: string
}

/**
 * 단타 시그널 응답
 */
export interface IDaytradingSignalsResponse {
  success: boolean
  data: {
    signals: IDaytradingSignal[]
    count: number
  }
}

/**
 * 단타 스캔 요청
 */
export interface IDaytradingScanRequest {
  market?: 'KOSPI' | 'KOSDAQ' | 'ALL'
  limit?: number
}

/**
 * 단타 분석 요청
 */
export interface IDaytradingAnalyzeRequest {
  tickers: string[]
}
```

### Phase 2: WebSocket Types (Week 1)

#### 2.1 WebSocket Message Types (`types/websocket/messages.ts`)

```typescript
/**
 * WebSocket 메시지 타입 (Discriminated Union)
 */
export type WSMessageType =
  | 'connected'
  | 'subscribed'
  | 'unsubscribed'
  | 'price_update'
  | 'index_update'
  | 'market_gate_update'
  | 'signal_update'
  | 'error'
  | 'ping'
  | 'pong'

/**
 * 연결 확인 메시지
 */
export interface IWSConnectedMessage {
  type: 'connected'
  client_id: string
  message: string
}

/**
 * 구독 확인 메시지
 */
export interface IWSSubscribedMessage {
  type: 'subscribed' | 'unsubscribed'
  topic: string
  message: string
}

/**
 * 가격 업데이트 메시지
 */
export interface IWSPriceUpdateMessage {
  type: 'price_update'
  ticker: string
  data: {
    price: number
    change: number
    change_rate: number
    volume: number
  }
  timestamp: string
}

/**
 * 지수 업데이트 메시지
 */
export interface IWSIndexUpdateMessage {
  type: 'index_update'
  code: string // 001: KOSPI, 201: KOSDAQ
  name: string // KOSPI, KOSDAQ
  data: {
    index: number
    change: number
    change_rate: number
    volume: number
  }
  timestamp: string
}

/**
 * Market Gate 업데이트 메시지
 */
export interface IWSMarketGateUpdateMessage {
  type: 'market_gate_update'
  timestamp: string
  data: {
    status: 'RED' | 'YELLOW' | 'GREEN'
    level: number
    kospi: number | null
    kospi_change_pct: number | null
    kosdaq: number | null
    kosdaq_change_pct: number | null
    sectors: Array<{
      name: string
      ticker: string | null
      change_pct: number | null
      signal: 'bullish' | 'bearish' | 'neutral'
    }>
  }
}

/**
 * 시그널 업데이트 메시지
 */
export interface IWSSignalUpdateMessage {
  type: 'signal_update'
  data: {
    signals: ISignal[] // api/signals.ts에서 import
    count: number
    timestamp: string
  }
}

/**
 * 에러 메시지
 */
export interface IWSErrorMessage {
  type: 'error'
  message: string
}

/**
 * Ping/Pong 메시지
 */
export interface IWSPingMessage {
  type: 'ping'
}

export interface IWSPongMessage {
  type: 'pong'
}

/**
 * WebSocket 메시지 통합 타입 (Discriminated Union)
 */
export type IWSMessage =
  | IWSConnectedMessage
  | IWSSubscribedMessage
  | IWSPriceUpdateMessage
  | IWSIndexUpdateMessage
  | IWSMarketGateUpdateMessage
  | IWSSignalUpdateMessage
  | IWSErrorMessage
  | IWSPingMessage
  | IWSPongMessage
```

#### 2.2 WebSocket Client Types (`types/websocket/client.ts`)

```typescript
/**
 * 연결 상태
 */
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error'

/**
 * 연결 옵션
 */
export interface IConnectionOptions {
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  reconnectDelay?: number
  pingInterval?: number
}

/**
 * WebSocket 클라이언트 인터페이스
 */
export interface IWebSocketClient {
  connectionState: ConnectionState
  clientId: string | null
  reconnectCount: number
  connect: () => void
  disconnect: () => void
  subscribe: (topic: string) => void
  unsubscribe: (topic: string) => void
  ping: () => void
  onMessage: (callback: (message: IWSMessage) => void) => () => void
  onStateChange: (callback: (state: ConnectionState) => void) => () => void
}
```

### Phase 3: Feature Types (Week 2)

#### 3.1 Signal Filters (`types/features/filters.ts`)

```typescript
/**
 * 시그널 필터 인터페이스
 */
export interface ISignalFilters {
  grades: ('S' | 'A' | 'B' | 'C')[]
  minScore: number
  maxScore: number
  signalType: 'all' | 'VCP' | 'JONGGA_V2' | 'DAYTRADING'
  market?: 'KOSPI' | 'KOSDAQ' | 'ALL'
}

/**
 * 정렬 설정 인터페이스
 */
export interface ISortConfig {
  sortBy: 'score' | 'grade' | 'created_at' | 'ticker'
  order: 'asc' | 'desc'
}
```

#### 3.2 Watchlist Types (`types/features/watchlist.ts`)

```typescript
/**
 * 관심종목 항목
 */
export interface IWatchlistItem {
  ticker: string
  name: string
  addedAt: string
  notes?: string
  alertPrice?: number
}

/**
 * 관심종목 그룹
 */
export interface IWatchlistGroup {
  id: string
  name: string
  items: IWatchlistItem[]
  createdAt: string
}
```

### Phase 4: Component Props Types (Week 2)

#### 4.1 Table Component Types (`types/components/tables.ts`)

```typescript
/**
 * 테이블 컬럼 정의
 */
export interface ITableColumn<T> {
  key: keyof T | string
  label: string
  sortable?: boolean
  filterable?: boolean
  render?: (value: any, row: T, index: number) => React.ReactNode
  width?: string | number
  align?: 'left' | 'center' | 'right'
  className?: string
}

/**
 * 테이블 정렬 상태
 */
export interface ITableSort {
  column: string
  direction: 'asc' | 'desc'
}

/**
 * 테이블 필터 상태
 */
export interface ITableFilter {
  column: string
  value: any
  operator?: 'eq' | 'contains' | 'gt' | 'lt' | 'between'
}

/**
 * 테이블 페이지네이션 상태
 */
export interface ITablePagination {
  page: number
  pageSize: number
  total: number
}
```

#### 4.2 Card Component Types (`types/components/cards.ts`)

```typescript
/**
 * 통계 카드 Props
 */
export interface IStatCardProps {
  title: string
  value: string | number
  change?: number
  unit?: string
  trend?: 'up' | 'down' | 'neutral'
  loading?: boolean
  icon?: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'outlined' | 'filled'
}

/**
 * 데이터 카드 Props
 */
export interface IDataCardProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  actions?: React.ReactNode
  collapsible?: boolean
  defaultCollapsed?: boolean
  loading?: boolean
  variant?: 'default' | 'bordered' | 'elevated'
}
```

### Phase 5: Re-export (`types/index.ts`)

```typescript
/**
 * 타입 시스템 중앙 진입점
 * 하위 호환성을 위해 모든 타입을 re-export
 */

// API 타입
export * from './api/signals'
export * from './api/stocks'
export * from './api/market-gate'
export * from './api/ai-analysis'
export * from './api/chatbot'
export * from './api/performance'
export * from './api/news'
export * from './api/daytrading'
export * from './api/system'
export * from './api/common'

// WebSocket 타입
export * from './websocket/messages'
export * from './websocket/client'
export * from './websocket/hooks'

// 컴포넌트 타입
export * from './components/tables'
export * from './components/cards'
export * from './components/charts'
export * from './components/forms'
export * from './components/filters'

// 기능 타입
export * from './features/signals'
export * from './features/filters'
export * from './features/watchlist'
export * from './features/scanner'

// 유틸리티 타입
export * from './utils/common'
export * from './utils/formatters'

// 레거시 별칭 (하위 호환성)
export type WSMessage = IWSMessage
```

---

## Migration Strategy

### Option 1: Big Bang (일회성 마이그레이션)

**장점**:
- 한 번의 작업으로 완료
- 이후 일관성 유지 용이

**단점**:
- 리스크 큼
- import 경로 일괄 변경 필요
- 빌드 실패 가능성 높음

**일정**: 1-2일 소요

### Option 2: Gradual (점진적 마이그레이션) ⭐ 추천

**장점**:
- 리스크 분산
- 기존 코드와 병행 가능
- 문제 발생 시 롤백 용이

**단점**:
- 마이그레이션 기간 깁음
- 일시적 중복 존재

**일정**: 2-3주 소요

**단계**:
1. Week 1: API Types 분리 (`types/api/`)
2. Week 2: WebSocket/Component Types 분리
3. Week 3: 기존 import 경로 점진적 변경
4. Week 4: 레거시 `types/index.ts` 제거

---

## Utility Types Library

### Common Utility Types

```typescript
// types/utils/common.ts

/**
 * Nullable 타입
 */
export type Nullable<T> = T | null

/**
 * Optional 타입
 */
export type Optional<T> = T | undefined

/**
 * DeepPartial 타입 (모든 속성을 optional로)
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

/**
 * 선택적 속성만 추출
 */
export type OptionalProps<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? K : never
}[keyof T]

/**
 * 필수 속성만 추출
 */
export type RequiredProps<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? never : K
}[keyof T]

/**
 * 특정 속성 제거
 */
export type OmitMultiple<T, K extends keyof T> = Omit<T, K>

/**
 * readonly 제거
 */
export type Mutable<T> = {
  -readonly [P in keyof T]: T[P]
}

/**
 * 배열 요소 타입 추출
 */
export type ArrayElement<T> = T extends (infer U)[] ? U : never

/**
 * 함수 반환 타입 추출
 */
export type ReturnTypeOf<T> = T extends (...args: any[]) => infer R ? R : never

/**
 * Promise 타입 추출
 */
export type UnwrapPromise<T> = T extends Promise<infer U> ? U : T
```

### API-Specific Utility Types

```typescript
// types/utils/api.ts

import type { IAPIResponse, IPaginatedResponse } from '../api/common'

/**
 * API 응답 데이터 타입 추출
 */
export type APIResponseData<T> = T extends IAPIResponse<infer D> ? D : never

/**
 * 페이지네이션된 데이터 타입 추출
 */
export type PaginatedData<T> = T extends IPaginatedResponse<infer D> ? D : never

/**
 * API 요청 파라미터 (선택적)
 */
export type APIParams = Record<string, string | number | boolean | undefined>

/**
 * 필터 가능한 타입
 */
export type Filterable<T> = {
  [K in keyof T]?: T[K] | { operator: string; value: T[K] }
}
```

---

## Type Safety Improvements

### 1. Discriminated Union 활용

**Before**:
```typescript
interface IWSMessage {
  type: string
  data: any
}
```

**After**:
```typescript
type IWSMessage =
  | IWSPriceUpdateMessage
  | IWSIndexUpdateMessage
  | IWSMarketGateUpdateMessage

// TypeScript가 type을 기반으로 데이터 구조를 추론
function handleMessage(message: IWSMessage) {
  if (message.type === 'price_update') {
    console.log(message.data.price) // 타입 안전함
  }
}
```

### 2. Branding Types (Nominal Typing)

```typescript
// types/utils/common.ts

/**
 * 브랜딩 타입 (Nominal Typing)
 * 서로 다른 의미를 가진 같은 내부 타입을 구분
 */
export type Brand<T, B> = T & { __brand: B }

/**
 * 티커 심볼 (단순 문자열과 구분)
 */
export type TickerSymbol = Brand<string, 'TickerSymbol'>

/**
 * 날짜 문자열 (ISO 8601)
 */
export type ISODateString = Brand<string, 'ISODateString'>

/**
 * 퍼센트 값 (0-100)
 */
export type Percent = Brand<number, 'Percent'>

// 사용 예시
function getStockPrice(ticker: TickerSymbol) { ... }
getStockPrice('005930' as TickerSymbol) // ✅
getStockPrice('005930') // ❌ 컴파일 에러
```

### 3. Generic Type Constraints

```typescript
// types/utils/common.ts

/**
 * ID를 가진 엔티티
 */
export interface IEntity {
  id: string | number
}

/**
 * 생성 시간을 가진 엔티티
 */
export interface ICreatedAt {
  created_at: string
}

/**
 * 업데이트 시간을 가진 엔티티
 */
export interface IUpdatedAt {
  updated_at: string
}

/**
 * 전체 엔티티 기본 타입
 */
export interface IBaseEntity extends IEntity, ICreatedAt {}

/**
 * 엔티티 목록 응답
 */
export interface IEntityList<T extends IBaseEntity> {
  items: T[]
  total: number
  page: number
  pageSize: number
}
```

---

## Type Definition Best Practices

### 1. Naming Conventions

| 타입 종류 | 접두사 | 예시 |
|----------|--------|------|
| 인터페이스 | `I` | `ISignal`, `IStockDetail` |
| 타입 별칭 | 없음 | `TickerSymbol`, `Percent` |
| 제네릭 | `T` | `T`, `TData`, `TResponse` |
| 유틸리티 타입 | 접두사 | `Nullable`, `Optional`, `DeepPartial` |

### 2. Export/Import Guidelines

**Export**:
```typescript
// Named export (권장)
export interface ISignal { ... }
export type SignalType = ...

// Default export (비권장)
export default ISignal // ❌
```

**Import**:
```typescript
// Named import (권장)
import { ISignal, SignalType } from '@/types/api/signals'

// Namespace import (타입이 많을 때)
import * as SignalTypes from '@/types/api/signals'
SignalTypes.ISignal

// 전체 import (비권장)
import * as Types from '@/types' // ❌
```

### 3. Type Guards

```typescript
// types/utils/guards.ts

/**
 * WebSocket 메시지 타입 가드
 */
export function isPriceUpdateMessage(msg: IWSMessage): msg is IWSPriceUpdateMessage {
  return msg.type === 'price_update'
}

/**
 * 시그널 타입 가드
 */
export function isVCPSignal(signal: ISignal): boolean {
  return signal.signal_type === 'VCP'
}

/**
 * 배열 타입 가드
 */
export function isArray<T>(value: T | T[]): value is T[] {
  return Array.isArray(value)
}

// 사용 예시
function handleMessage(message: IWSMessage) {
  if (isPriceUpdateMessage(message)) {
    console.log(message.data.price) // 타입 좁혀짐
  }
}
```

---

## Success Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| `types/index.ts` 크기 | 810 라인 | 100 라인 (re-export only) | -88% |
| 파일 개수 | 1개 | 25개+ | 분리 완료 |
| 관련성 없는 import | 높음 | 낮음 | 필요한 것만 import |
| 순환 의존성 위험 | 높음 | 낮음 | 계층 구조 |
| 탐색 용이성 | 어려움 | 쉬움 | 도메인별 파일 |

---

## Migration Checklist

### Week 1: API Types
- [ ] `types/api/` 디렉토리 생성
- [ ] API 타입 파일별 분리
- [ ] `api-client.ts` import 경로 변경
- [ ] Store 타입 import 경로 변경

### Week 2: WebSocket & Component Types
- [ ] `types/websocket/` 디렉토리 생성
- [ ] WebSocket 타입 분리
- [ ] `useWebSocket.ts` import 경로 변경
- [ ] `types/components/` 디렉토리 생성
- [ ] 컴포넌트 Props 타입 분리

### Week 3: Feature Types & Utils
- [ ] `types/features/` 디렉토리 생성
- [ ] 기능별 타입 분리
- [ ] `types/utils/` 유틸리티 타입 작성
- [ ] 전체 코드베이스 import 경로 변경

### Week 4: Cleanup
- [ ] 레거시 `types/index.ts` 제거
- [ ] TypeScript 컴파일 에러 확인
- [ ] 테스트 통과 확인
- [ ] 문서 업데이트

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import 경로 변경으로 인한 빌드 실패 | High | High | 점진적 마이그레이션, 별칭 사용 |
| 타입 누락 | Medium | Medium | 철저한 테스트, 팀 리뷰 |
| 순환 의존성 발생 | Low | High | 계층 구조 준수, lint 규칙 |
| 개발 생산성 저하 | Medium | Low | 명확한 가이드라인, IDE 자동완성 |

---

## Next Actions

1. [ ] 팀 승인 및 피드백
2. [ ] Week 1 시작: API Types 분리
3. [ ] TypeScript lint 규칙 추가 (`no-relative-imports`)
4. [ ] 마이그레이션 자동화 스크립트 작성 (선택)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-06
**Owner**: Frontend Architect
