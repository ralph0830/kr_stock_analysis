# Frontend Component Reusability Improvement Plan

**Date:** 2026-02-06
**Author:** Frontend Architect Agent
**Status:** Planning Phase

---

## Problem Statement

현재 프론트엔드 컴포넌트 구조는 다음과 같은 문제가 있습니다:

1. **비즈니스 컴포넌트와 UI 컴포넌트의 혼재**: `components/` 루트에 모든 컴포넌트가 평면적으로 배치
2. **페이지별 컴포넌트의 위치 모호성**: 어느 페이지에서 사용되는지 명확하지 않음
3. **코드 중복**: 유사한 테이블, 카드 UI가 여러 곳에서 중복 구현
4. **재사용성 낮음**: 페이지 의존적인 컴포넌트가 다수 존재

---

## Proposed Directory Structure

### Current Structure
```
frontend/
├── components/
│   ├── ui/                    # Radix UI 컴포넌트 (9개)
│   ├── layout/                # 레이아웃 컴포넌트
│   ├── DaytradingSignalTable.tsx      # 단타 시그널 테이블
│   ├── RealtimePriceCard.tsx          # 실시간 가격 카드
│   ├── StockChart.tsx                 # 주식 차트
│   ├── SignalHistory.tsx              # 시그널 히스토리
│   ├── ... (13개 비즈니스 컴포넌트)
```

### Proposed Structure
```
frontend/
├── components/
│   ├── ui/                        # 기본 UI 컴포넌트 (Radix/ShadCN)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── table.tsx
│   │   └── ...
│   │
│   ├── layout/                    # 레이아웃 컴포넌트
│   │   ├── header.tsx
│   │   ├── sidebar.tsx
│   │   ├── footer.tsx
│   │   └── container.tsx
│   │
│   ├── data-display/              # 데이터 표시 컴포넌트 (재사용 가능)
│   │   ├── DataTable.tsx          # 공통 테이블
│   │   ├── DataCard.tsx           # 공통 카드
│   │   ├── StatCard.tsx           # 통계 카드
│   │   ├── Badge.tsx              # 라벨/배지 (확장)
│   │   ├── EmptyState.tsx
│   │   └── ErrorState.tsx
│   │
│   ├── charts/                    # 차트 컴포넌트 (재사용 가능)
│   │   ├── LineChart.tsx          # 라인 차트
│   │   ├── CandlestickChart.tsx   # 캔들 차트
│   │   ├── FlowChart.tsx          # 수급 차트
│   │   ├── TechnicalIndicators.tsx
│   │   └── ReturnAnalysis.tsx
│   │
│   ├── stock/                     # 종목 관련 컴포넌트
│   │   ├── StockDetail.tsx
│   │   ├── StockChart.tsx
│   │   ├── StockHeader.tsx
│   │   └── StockPrice.tsx
│   │
│   ├── signal/                    # 시그널 관련 컴포넌트
│   │   ├── VCPSignalTable.tsx     # VCP 시그널 테이블
│   │   ├── DaytradingSignalTable.tsx
│   │   ├── SignalFilter.tsx
│   │   ├── SignalHistory.tsx
│   │   └── SignalSearch.tsx
│   │
│   ├── realtime/                  # 실시간 데이터 컴포넌트
│   │   ├── RealtimePriceCard.tsx
│   │   ├── RealtimeIndexCard.tsx
│   │   ├── WebSocketStatus.tsx
│   │   └── MarketGateStatus.tsx
│   │
│   ├── chatbot/                   # 챗봇 관련 컴포넌트
│   │   ├── ChatbotWidget.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   └── AIAnalysisSummary.tsx
│   │
│   ├── news/                      # 뉴스 관련 컴포넌트
│   │   ├── NewsFeed.tsx
│   │   ├── NewsCard.tsx
│   │   └── NewsSentimentBadge.tsx
│   │
│   └── system/                    # 시스템 관련 컴포넌트
│       ├── SystemHealthIndicator.tsx
│       ├── ScanTriggerPanel.tsx
│       └── ErrorBoundary.tsx
│
├── features/                      # 기능별 폴더 (페이지 전용 컴포넌트)
│   ├── dashboard/                 # 대시보드 기능
│   │   ├── DashboardStats.tsx
│   │   ├── MarketOverview.tsx
│   │   └── BacktestKPI.tsx
│   │
│   ├── custom-recommendation/     # 단타 추천 기능
│   │   ├── DaytradingFilters.tsx
│   │   ├── DaytradingScanButton.tsx
│   │   └── DaytradingDescription.tsx
│   │
│   ├── stock-detail/              # 종목 상세 기능
│   │   ├── StockDetailHeader.tsx
│   │   ├── StockDetailTabs.tsx
│   │   └── StockDetailActions.tsx
│   │
│   └── watchlist/                 # 관심종목 기능
│       ├── Watchlist.tsx
│       ├── WatchlistItem.tsx
│       └── WatchlistAddModal.tsx
```

---

## Component Migration Plan

### Phase 1: Data Display Components (Week 1)

**목표**: 재사용 가능한 데이터 표시 컴포넌트 추출

#### 1.1 DataTable Component
```typescript
// components/data-display/DataTable.tsx
interface DataTableProps<T> {
  data: T[]
  columns: ColumnDef<T>[]
  sortable?: boolean
  filterable?: boolean
  pagination?: boolean
  loading?: boolean
  empty?: React.ReactNode
}

// 사용 예시
<DataTable
  data={signals}
  columns={[
    { key: 'ticker', label: '티커', sortable: true },
    { key: 'name', label: '종목명' },
    { key: 'score', label: '점수', sortable: true, render: (v) => v.toFixed(1) },
  ]}
  sortable
  pagination
/>
```

**이동 대상**:
- `DaytradingSignalTable.tsx` → DataTable 활용
- VCP 시그널 테이블 → DataTable 활용
- 시그널 히스토리 테이블 → DataTable 활용

#### 1.2 StatCard Component
```typescript
// components/data-display/StatCard.tsx
interface StatCardProps {
  title: string
  value: string | number
  change?: number
  unit?: string
  trend?: 'up' | 'down' | 'neutral'
  loading?: boolean
  icon?: React.ReactNode
}

// 사용 예시
<StatCard
  title="총 시그널"
  value={signals.length}
  change={5.2}
  trend="up"
  unit="개"
/>
```

**이동 대상**:
- 백테스트 KPI 카드들
- Market Gate 상태 카드
- 시스템 헬스 카드

### Phase 2: Feature-Based Components (Week 2)

**목표**: 페이지 전용 컴포넌트를 `features/`로 이동

#### 2.1 Dashboard Components
```
features/dashboard/
├── DashboardStats.tsx        # 대시보드 통계 카드
├── MarketOverview.tsx        # 시장 개요
├── BacktestKPI.tsx           # 백테스트 KPI
└── SignalSummary.tsx         # 시그널 요약
```

#### 2.2 Custom Recommendation Components
```
features/custom-recommendation/
├── DaytradingFilters.tsx     # 필터 패널 (components/에서 이동)
├── DaytradingScanButton.tsx  # 스캔 버튼
└── DaytradingDescription.tsx # 설명 카드
```

### Phase 3: Refactor Existing Components (Week 3-4)

**목표**: 기존 컴포넌트를 새로운 구조로 리팩토링

#### 3.1 RealtimePriceCard.tsx (466라인) → 분해
```
components/realtime/
├── RealtimePriceCard.tsx      # 메인 컴포넌트 (150라인)
├── RealtimePriceGrid.tsx      # 가격 그리드 (100라인)
├── WebSocketStatus.tsx        # 연결 상태 (50라인)
└── PriceChangeBadge.tsx       # 가격 변화 배지 (50라인)
```

#### 3.2 StockChart.tsx (364라인) → 분해
```
components/charts/
├── StockChart.tsx             # 메인 컴포넌트 (100라인)
├── ChartContainer.tsx         # 차트 컨테이너 (50라인)
├── ChartControls.tsx          # 차트 컨트롤 (50라인)
├── PriceChart.tsx             # 가격 차트 (80라인)
└── VolumeChart.tsx            # 거래량 차트 (50라인)
```

---

## Common Components Specification

### 1. DataTable Component

**기능**:
- 정렬 (단일/다중 컬럼)
- 필터링 (텍스트 검색, 범위 필터)
- 페이지네이션
- 로딩 상태
- 빈 상태 처리
- 행 선택 (checkbox)

**인터페이스**:
```typescript
interface ColumnDef<T> {
  key: keyof T | string
  label: string
  sortable?: boolean
  filterable?: boolean
  render?: (value: any, row: T) => React.ReactNode
  width?: string | number
  align?: 'left' | 'center' | 'right'
}

interface DataTableProps<T> {
  data: T[]
  columns: ColumnDef<T>[]
  onRowClick?: (row: T) => void
  onSort?: (key: string, direction: 'asc' | 'desc') => void
  onFilter?: (filters: Record<string, any>) => void
  selectable?: boolean
  selectedRows?: T[]
  onSelectionChange?: (rows: T[]) => void
  pagination?: {
    page: number
    pageSize: number
    total: number
    onPageChange: (page: number) => void
  }
  loading?: boolean
  empty?: React.ReactNode
  className?: string
}
```

### 2. StatCard Component

**기능**:
- 통계 값 표시
- 변화율 표시 (추세 아이콘)
- 로딩 스켈레톤
- 커스텀 아이콘

**인터페이스**:
```typescript
interface StatCardProps {
  title: string
  value: string | number
  previousValue?: number
  change?: number
  unit?: string
  trend?: 'up' | 'down' | 'neutral'
  loading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'outlined' | 'filled'
  className?: string
}
```

### 3. DataCard Component

**기능**:
- 제목 + 컨텐츠
- 액션 버튼
- 확장/축소
- 로딩 상태

**인터페이스**:
```typescript
interface DataCardProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  actions?: React.ReactNode
  collapsible?: boolean
  defaultCollapsed?: boolean
  loading?: boolean
  variant?: 'default' | 'bordered' | 'elevated'
  className?: string
}
```

---

## Component Reuse Metrics

### Before (Current)
| Metric | Value |
|--------|-------|
| 총 컴포넌트 수 | 22개 |
| 재사용 가능한 컴포넌트 | 9개 (ui/) |
| 페이지 전용 컴포넌트 | 13개 |
| 평균 컴포넌트 크기 | 230라인 |
| 코드 중복도 | 높음 (테이블, 카드 중복) |

### After (Target)
| Metric | Value | Improvement |
|--------|-------|-------------|
| 총 컴포넌트 수 | 50개+ | +128% |
| 재사용 가능한 컴포넌트 | 30개+ | +233% |
| 페이지 전용 컴포넌트 | 20개 | features/로 이동 |
| 평균 컴포넌트 크기 | 150라인 | -35% |
| 코드 중복도 | 낮음 | 공통 컴포넌트 활용 |

---

## Migration Steps

### Step 1: Preparation (Day 1-2)
1. 새로운 디렉토리 구조 생성
2. 공통 컴포넌트 인터페이스 정의
3. Storybook 또는 컴포넌트 문서 도입 결정

### Step 2: Core Components (Day 3-7)
1. `DataTable` 컴포넌트 구현
2. `StatCard` 컴포넌트 구현
3. `DataCard` 컴포넌트 구현
4. `EmptyState`, `ErrorState` 구현

### Step 3: Feature Components (Day 8-14)
1. `features/` 폴더 생성
2. 페이지별 컴포넌트 이동
3. import 경로 업데이트

### Step 4: Refactor (Day 15-21)
1. 기존 컴포넌트를 공통 컴포넌트로 교체
2. 대형 컴포넌트 분해
3. 테스트 코드 작성

### Step 5: Documentation (Day 22-28)
1. 컴포넌트 사용 가이드 작성
2. Storybook 스토리 작성 (선택)
3. 예제 코드 추가

---

## Success Criteria

1. **재사용성**: 최소 50%의 페이지가 공통 컴포넌트를 사용
2. **일관성**: 모든 테이블, 카드가 일관된 UI를 가짐
3. **유지보수성**: 공통 컴포넌트 수정 시 모든 곳에 반영
4. **테스트 가능성**: 공통 컴포넌트의 단위 테스트 커버리지 80%+

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| import 경로 변경으로 인한 빌드 실패 | High | 점진적 마이그레이션, 별칭(alias) 사용 |
| 기존 기능 회귀 | Medium | 포괄적인 E2E 테스트 |
| 개발 속도 저하 | Medium | 우선순위 기반 단계적 도입 |
| 과도한 엔지니어링 | Low | MVP 먼저 구현, 점진적 개선 |

---

## Next Actions

1. [ ] 팀 리뷰 및 승인
2. [ ] Phase 1 시작: Data Display Components 구현
3. [ ] Storybook 도입 검토
4. [ ] 컴포넌트 문서화 플랫폼 결정

---

**Document Version**: 1.0
**Last Updated**: 2026-02-06
**Owner**: Frontend Architect
