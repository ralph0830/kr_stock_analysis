# Frontend Architecture Analysis Report

**Date:** 2026-02-06
**Analyst:** Frontend Architect Agent
**Project:** Ralph Stock Analysis System

---

## Executive Summary

Ralph Stock Analysis Frontend는 **Next.js 15 (App Router)** 기반의 현대적인 주식 분석 플랫폼입니다. React 19, TypeScript, Zustand를 활용하여 실시간 WebSocket 연동, 마이크로서비스 아키텍처와의 통합, 그리고 종합적인 주식 분석 기능을 제공합니다.

### Key Strengths
- **최신 기술 스택**: Next.js 15 + React 19 + TypeScript 5
- **실시간 데이터**: WebSocket 기반 실시간 가격/시그널 업데이트
- **상태 관리**: Zustand를 활용한 효율적인 전역 상태 관리
- **타입 안전성**: 800+ 라인의 엄격한 TypeScript 타입 정의
- **컴포넌트 재사용**: Radix UI 기반 ShadCN UI 컴포넌트 활용

### Critical Improvement Areas
1. **재사용 가능한 컴포넌트 부족**: 페이지별 컴포넌트가 `components/` 루트에 혼재
2. **페이지 간 코드 중복**: 유사한 테이블/카드 UI가 중복 구현
3. **UI 디자인 시스템 부재**: Design Token이 체계화되지 않음
4. **테스트 커버리지**: E2E 테스트는 있으나 컴포넌트 단위 테스트 부족
5. **성능 최적화**: 이미지 최적화, 코드 분할, 렌더링 최적화 개선 필요

---

## 1. Technology Stack

### Core Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 15.1.3 | React Framework (App Router) |
| **React** | 19.0.0 | UI Library |
| **TypeScript** | 5.x | Type Safety |
| **Zustand** | 5.0.2 | State Management |
| **Tailwind CSS** | 3.4.17 | Styling |
| **Radix UI** | Latest | Accessible Components (ShadCN) |

### Key Libraries
| Library | Purpose |
|---------|---------|
| **axios** | API Client with retry logic |
| **recharts** | Chart visualization |
| **lucide-react** | Icon system |
| **date-fns** | Date formatting |
| **class-variance-authority** | Component variants |
| **clsx + tailwind-merge** | Class name utilities |

### Testing Stack
| Tool | Purpose |
|------|---------|
| **vitest** | Unit testing |
| **@testing-library/react** | Component testing |
| **playwright** | E2E testing |

---

## 2. Project Structure Analysis

### Current Directory Structure
```
frontend/
├── app/                      # Next.js App Router (페이지 및 라우팅)
│   ├── page.tsx              # 메인 대시보드
│   ├── layout.tsx            # 루트 레이아웃
│   ├── dashboard/            # 대시보드 페이지들
│   ├── custom-recommendation/# 단타 추천 페이지
│   ├── signals/              # 시그널 페이지
│   ├── chatbot/              # AI 챗봇 페이지
│   ├── chart/                # 차트 페이지
│   └── stock/[ticker]/       # 종목 상세 페이지 (동적 라우팅)
│
├── components/               # 컴포넌트 (22개, ~5,000 라인)
│   ├── ui/                   # Radix UI 기반 컴포넌트 (9개)
│   ├── layout/               # 레이아웃 컴포넌트
│   ├── *.tsx                 # 비즈니스 컴포넌트 (13개)
│
├── store/                    # Zustand Stores (4개)
│   ├── index.ts              # 메인 스토어 (시그널, 필터, KPI)
│   ├── daytradingStore.ts    # 단타 스캐너 스토어
│   ├── stockStore.ts         # 종목 스토어
│   └── systemStore.ts        # 시스템 상태 스토어
│
├── hooks/                    # Custom Hooks (2개)
│   ├── useWebSocket.ts       # WebSocket 연동 (~840 라인) ⭐
│   └── useTypingAnimation.ts # 챗봇 타이핑 효과
│
├── lib/                      # 유틸리티 라이브러리
│   ├── api-client.ts         # API 클라이언트 (~600 라인) ⭐
│   ├── websocket.ts          # WebSocket 클라이언트 (~700 라인) ⭐
│   ├── signalFilters.ts      # 시그널 필터링 로직
│   └── utils.ts              # 공통 유틸리티
│
├── types/                    # TypeScript 타입 정의
│   └── index.ts              # 전체 타입 (~810 라인) ⭐
│
├── constants/                # 상수 정의
│   └── daytrading.ts         # 단타 관련 상수
│
└── tests/                    # 테스트 파일
    ├── e2e/                  # Playwright E2E 테스트
    └── lib/                  # Vitest 단위 테스트
```

### Structure Issues
1. **컴포넌트 분리 미흡**: 비즈니스 컴포넌트와 UI 컴포넌트가 같은 레벨에 존재
2. **feature 폴더 부재**: 페이지별 컴포넌트가 `app/` 외부에 분산
3. **공통 컴포넌트 부족**: 테이블, 카드 등이 각 페이지에서 중복 구현

---

## 3. Component Architecture Analysis

### Component Overview (22개 컴포넌트)

#### UI Components (Radix/ShadCN) - 9개
| Component | Lines | Purpose | Status |
|-----------|-------|---------|--------|
| `button.tsx` | 58 | 기본 버튼 | ✅ 완료 |
| `card.tsx` | - | 카드 컨테이너 | ✅ 완료 |
| `dialog.tsx` | - | 모달 다이얼로그 | ✅ 완료 |
| `input.tsx` | - | 텍스트 입력 | ✅ 완료 |
| `select.tsx` | - | 드롭다운 선택 | ✅ 완료 |
| `slider.tsx` | - | 범위 슬라이더 | ✅ 완료 |
| `checkbox.tsx` | - | 체크박스 | ✅ 완료 |
| `table.tsx` | - | 테이블 | ✅ 완료 |
| `badge.tsx` | - | 라벨/배지 | ✅ 완료 |

**평가**: Radix UI 기반으로 접근성 준수, 기능 충실

#### Business Components - 13개
| Component | Lines | Purpose | Reusability |
|-----------|-------|---------|-------------|
| `DaytradingSignalTable.tsx` | 322 | 단타 시그널 테이블 | 🔴 Low (Page-specific) |
| `RealtimePriceCard.tsx` | 466 | 실시간 가격 카드 | 🟡 Medium (Tight coupling) |
| `StockChart.tsx` | 364 | 주식 차트 | 🟢 High (Reusable) |
| `CandlestickChart.tsx` | 366 | 캔들 차트 | 🟢 High (Reusable) |
| `SignalHistory.tsx` | 249 | 시그널 히스토리 | 🟡 Medium |
| `TechnicalIndicators.tsx` | 281 | 기술적 지표 | 🟢 High (Reusable) |
| `NewsFeed.tsx` | 296 | 뉴스 피드 | 🟢 High (Reusable) |
| `FlowChart.tsx` | 202 | 수급 차트 | 🟢 High (Reusable) |
| `ScanTriggerPanel.tsx` | 318 | 스캔 트리거 패널 | 🟡 Medium |
| `ChatbotWidget.tsx` | 273 | AI 챗봇 | 🟢 High (Reusable) |
| `AIAnalysisSummary.tsx` | 263 | AI 분석 요약 | 🟡 Medium |
| `ReturnAnalysis.tsx` | 224 | 수익률 분석 | 🟢 High (Reusable) |
| `SignalFilter.tsx` | 162 | 시그널 필터 | 🟡 Medium |

**평가**:
- **재사용성 개선 필요**: 페이지 의존적인 컴포넌트가 다수 존재
- **Props 구조 개선**: 일부 컴포넌트가 너무 많은 책임을 담당
- **컴포지션 패턴 도입**: 더 작은 단위로 분리하여 조합 가능하게 개선

### Component Complexity Analysis
```
가장 복잡한 컴포넌트 (상위 5개):
1. RealtimePriceCard.tsx    466 라인 (WebSocket 연동 + 가격 표시)
2. StockChart.tsx            364 라인 (Recharts 차트)
3. CandlestickChart.tsx      366 라인 (캔들 차트)
4. DaytradingSignalTable.tsx 322 라인 (단타 시그널 테이블)
5. ScanTriggerPanel.tsx      318 라인 (스캔 제어)
```

**개선 권장사항**:
- 300+ 라인 컴포넌트를 하위 컴포넌트로 분리
- 복잡한 로직을 Custom Hook으로 추출

---

## 4. State Management Analysis

### Zustand Stores (4개)

#### 1. Main Store (`store/index.ts`) - 180 라인
```typescript
interface AppState {
  // 시그널 상태
  signals: Signal[]
  loadingSignals: boolean
  signalsError: string | null

  // Market Gate 상태
  marketGate: MarketGateStatus | null
  loadingMarketGate: boolean
  marketGateError: string | null

  // 백테스트 KPI 상태
  backtestKPI: IBacktestKPI | null
  loadingBacktestKPI: boolean
  backtestKPIError: string | null

  // 실시간 가격 상태
  prices: Record<string, StockPrice>
  pricesError: string | null

  // 필터/정렬 상태
  filters: ISignalFilters
  sortConfig: ISortConfig
}
```

**책임**: 시그널, Market Gate, 백테스트 KPI, 실시간 가격, 필터/정렬
**평가**: 너무 많은 책임을 담당 → 분리 권장

#### 2. Daytrading Store (`store/daytradingStore.ts`) - 211 라인
```typescript
interface IDaytradingState {
  signals: IDaytradingSignal[]
  loading: boolean
  error: string | null
  filters: {
    minScore: number
    market: "ALL" | "KOSPI" | "KOSDAQ"
    limit: number
  }
}
```

**책임**: 단타 시그널, 필터, 스캔/분석 액션
**평가**: 적절한 크기, 잘 설계됨

#### 3. Stock Store (`store/stockStore.ts`)
**책임**: 종목별 상태
**평가**: 미사용 또는 간단한 상태만 관리

#### 4. System Store (`store/systemStore.ts`)
**책임**: 시스템 헬스, 연결 상태
**평가**: 미사용 또는 간단한 상태만 관리

### State Management Issues
1. **과도한 책임**: Main Store가 너무 많은 도메인을 담당
2. **데이터 정규화 불필요**: 대부분 API 응답을 그대로 저장
3. **캐싱 전략 부족**: 반복적인 API 호출 방지 로직 부족
4. **낙관적 업데이트 미구현**: UI 반응성 개선 여지 있음

---

## 5. Type System Analysis

### TypeScript Types (`types/index.ts`) - 810 라인

#### 주요 타입 카테고리
1. **API 응답 타입** (18개)
   - `Signal`, `MarketGateStatus`, `StockPrice`, `HealthCheck`
   - `IStockDetail`, `IStockChart`, `IFlowHistory`
   - `IAIAnalysis`, `INewsFeed`, `ISignalHistory`

2. **WebSocket 타입** (10개)
   - Discriminated Union 패턴 활용
   - `IWSMessage`, `IWSPriceUpdateMessage`, `IWSMarketGateUpdateMessage`
   - 타입 안전성 확보

3. **필터/정렬 타입** (2개)
   - `ISignalFilters`, `ISortConfig`

4. **챗봇 타입** (6개)
   - `IChatMessage`, `IChatRequest`, `IChatResponse`, `IChatContext`

5. **단타 스캐너 타입** (5개)
   - `IDaytradingSignal`, `IDaytradingScanRequest`

#### 타입 시스템 강점
- **엄격한 타입 정의**: `noImplicitAny` 활성화
- **인터페이스 명명 규칙**: `I` 접두사 사용 (CLAUDE.md 가이드 준수)
- **Discriminated Union**: WebSocket 메시지 타입 안전성 확보
- **공통 타입 재사용**: `StockPrice`, `Signal` 등 중앙 집중화

#### 개선 권장사항
1. **타입 분리**: `types/index.ts`가 너무 큼 → 도메인별 파일로 분리
2. **API 레이어 타입**: `types/api/` 디렉토리 생성
3. **컴포넌트 Props 타입**: `types/components/` 디렉토리 생성
4. **유틸리티 타입**: `Pick`, `Omit`, `Partial` 활용 증대

---

## 6. Custom Hooks Analysis

### useWebSocket Hook - 840 라인 ⭐

**기능**: WebSocket 연결 관리, 실시간 데이터 수신

**하위 훅**:
1. `useRealtimePrices(tickers)` - 실시간 가격 구독
2. `useMarketIndices()` - KOSPI/KOSDAQ 지수 구독
3. `useMarketGate()` - Market Gate 실시간 업데이트
4. `useSignals()` - VCP 시그널 실시간 구독
5. `useDaytradingSignals()` - 단타 시그널 실시간 구독

**강점**:
- 싱글톤 WebSocket 클라이언트 패턴
- 자동 재연결 로직 (최대 10회)
- 폴백 메커니즘 (WebSocket 실패 시 API 폴링)
- 에러 타입별 명확한 사용자 메시지

**개선 권장사항**:
1. **파일 분리**: 840라인이 너무 김 → `hooks/websocket/` 디렉토리로 분리
2. **의존성 주입**: WebSocket 클라이언트를 훅 외부에서 생성 가능하게
3. **테스트 가능성**: Mock WebSocket 지원 개선

---

## 7. API Client Analysis

### api-client.ts - 600 라인 ⭐

**기능**: Axios 기반 API 클라이언트, 재시도 로직, 에러 처리

**주요 기능**:
1. 동적 baseURL 결정 (로컬/프로덕션 자동 감지)
2. 요청 재시도 (최대 5회, 지수 백오프)
3. 에러 로깅 (상세한 에러 타입 분류)
4. 40개 이상의 API 메서드

**API 카테고리**:
- 시그널 API: `getSignals()`, `getVCPSignals()`
- Market Gate: `getMarketGate()`
- 종목 데이터: `getStockDetail()`, `getStockChart()`, `getStockFlow()`
- AI 분석: `getAISummary()`, `triggerAIAnalysis()`
- 챗봇: `chat()`, `getContext()`, `getRecommendations()`
- Performance: `getCumulativeReturns()`, `getTopPerformers()`
- 뉴스: `getLatestNews()`, `getNewsByTicker()`
- 단타 스캐너: `getDaytradingSignals()`, `scanDaytradingMarket()`

**강점**:
- 강력한 재시도 로직
- 상세한 에러 로깅
- SSR/CSR 자동 감지

**개선 권장사항**:
1. **API 모듈화**: 기능별 파일 분리 (`api/signals.ts`, `api/stocks.ts`)
2. **캐싱 레이어**: React Query 또는 SWR 도입 검토
3. **요청 취소**: 중복 요청 자동 취소 (AbortController)
4. **타입 제네릭**: 반복적인 타입 정의 줄이기

---

## 8. Routing & Page Structure

### App Router Structure

| Route | Page | Component Count | Complexity |
|-------|------|-----------------|------------|
| `/` | 메인 대시보드 | Medium | 실시간 데이터 연동 |
| `/dashboard` | 대시보드 홈 | Low | - |
| `/dashboard/kr` | 한국 시장 | Medium | VCP/종가베팅 |
| `/dashboard/kr/vcp` | VCP 스캔 | High | 스캔 제어 |
| `/dashboard/kr/closing-bet` | 종가베팅 | High | 시그널 생성 |
| `/signals` | 시그널 목록 | Medium | 필터/정렬 |
| `/stock/[ticker]` | 종목 상세 | Very High | 10+ 컴포넌트 |
| `/chart` | 차트 페이지 | Medium | 시각화 |
| `/chatbot` | AI 챗봇 | Medium | WebSocket 챗 |
| `/custom-recommendation` | 단타 추천 | High | 실시간 연동 |

### 라우팅 개선 권장사항
1. **라우트 보호**: 인증이 필요한 페이지에 미들웨어 적용
2. **로딩 상태**: `loading.tsx` 도입
3. **에러 처리**: `error.tsx` 도입
4. **메타데이터**: 각 페이지에 SEO 메타데이터 추가

---

## 9. Styling & Design System

### Tailwind CSS 설정
- **커스텀 색상**: 없음 (기본 팔레트 사용)
- **커스텀 스타일**: `globals.css`에 최소한의 커스텀 스타일
- **다크 모드**: `dark:` 클래스 기반 지원
- **반응형**: 기본 Tailwind 브레이크포인트 사용

### Design Token 현황
| Category | Status | Location |
|----------|--------|----------|
| Colors | 🔴 None | Tailwind 기본값 사용 |
| Spacing | 🔴 None | Tailwind 기본값 사용 |
| Typography | 🔴 None | Tailwind 기본값 사용 |
| Shadows | 🔴 None | Tailwind 기본값 사용 |
| Border Radius | 🟡 Partial | 일부 컴포넌트에 하드코딩 |
| Components | 🟢 Good | Radix UI + CVA 사용 |

### Design System 부족 문제
1. **일관성 부족**: 유사한 컴포넌트가 다른 스타일 사용
2. **테마 부재**: 브랜드 색상, 폰트가 정의되지 않음
3. **스케일 불일치**: 간격, 크기가 임의로 설정

---

## 10. Performance Analysis

### 번들 크기
```json
{
  "dependencies": {
    "next": "15.1.3",
    "react": "^19.0.0",
    "axios": "^1.7.7",
    "recharts": "^2.15.0",  // ~200KB
    "zustand": "^5.0.2"     // ~3KB
  }
}
```

**예상 번들 크기**:
- Next.js Core: ~80KB
- React: ~45KB
- Recharts: ~200KB (가장 큰 의존성)
- Axios: ~15KB
- **Total (gzip)**: ~350KB ~ 400KB

### 성능 개선 기회
1. **코드 분할**: 동적 import (`next/dynamic`) 활용
2. **이미지 최적화**: `next/image` 사용
3. **폰트 최적화**: `next/font` 사용
4. **번들 분석**: `@next/bundle-analyzer` 도입
5. **서버 컴포넌트**: 클라이언트 컴포넌트를 서버 컴포넌트로 전환

---

## 11. Testing Analysis

### 테스트 파일 구조
```
tests/
├── e2e/                     # Playwright E2E 테스트
│   ├── websocket-e2e.spec.ts
│   ├── chatbot/news-link-click.spec.ts
│   ├── filter-e2e.spec.ts
│   └── page-load.spec.ts
│
└── lib/                     # Vitest 단위 테스트
    ├── markdown.test.ts
    └── signalFilters.test.ts
```

### 테스트 커버리지 현황
- **E2E 테스트**: 4개 (WebSocket, 필터, 페이지 로드)
- **단위 테스트**: 2개 (유틸리티 함수)
- **컴포넌트 테스트**: 0개
- **통합 테스트**: 0개

### 테스트 개선 권장사항
1. **컴포넌트 테스트**: `@testing-library/react` 활용
2. **Hook 테스트**: `@testing-library/react-hooks` 활용
3. **Mock WebSocket**: 테스트용 Mock 서버 도입
4. **커버리지 목표**: 최소 70% 달성

---

## 12. Accessibility (WCAG 2.1 AA)

### 접근성 현황
| 항목 | 상태 | 비고 |
|------|------|------|
| ARIA 라벨 | 🟡 Partial | 일부 버튼에 `aria-label` 존재 |
| 키보드 네비게이션 | 🟢 Good | Radix UI 기본 지원 |
| 색상 대비 | 🔴 Unknown | 측정 필요 |
| 포커스 관리 | 🟡 Partial | 일부 모달에 포커스 트랩 |
| 스크린 리더 | 🟡 Partial | 시맨틱 HTML 사용 |

### 개선 권장사항
1. **색상 대비 검사**: axe DevTools 또는 Lighthouse 사용
2. **ARIA 라벨 추가**: 모든 대화형 요소에 라벨 추가
3. **키보드 테스트**: 전체 기능 키보드만으로 사용 가능한지 확인
4. **포커스 표시**: 명확한 포커스 인디케이터 추가

---

## 13. Security Analysis

### 보안 현황
| 항목 | 상태 | 비고 |
|------|------|------|
| 인증 | 🔴 None | 구현되지 않음 |
| API 키 보호 | 🟢 Good | 환경 변수 사용 |
| XSS 방지 | 🟢 Good | React 자동 이스케이프 |
| CSRF 보호 | 🟡 Partial | SameSite 쿠키 필요 |
| CORS 설정 | 🟢 Good | 백엔드에서 설정 |

### 개선 권장사항
1. **인증 도입**: Clerk 또는 NextAuth.js 도입
2. **API 레이트 리밋**: 클라이언트측 요청 제한
3. **CSP 헤더**: Content Security Policy 추가

---

## 14. Recommendations (Priority Matrix)

### P0 - Critical (즉시 실행)
1. **컴포넌트 재사용성 개선**
   - 페이지별 컴포넌트를 `features/` 폴더로 이동
   - 공통 테이블, 카드 컴포넌트 추출

2. **타입 시스템 개선**
   - `types/index.ts`를 도메인별로 분리
   - API 타입, 컴포넌트 Props 타입 분리

3. **성능 최적화**
   - Recharts 동적 import
   - 이미지 최적화 (`next/image`)

### P1 - High (1-2주 내)
4. **Design System 구축**
   - Design Token 정의 (색상, 간격, 타이포그래피)
   - `tailwind.config.ts` 확장

5. **테스트 커버리지 확대**
   - 컴포넌트 단위 테스트 작성
   - 목표 커버리지 70%

6. **WebSocket Hook 모듈화**
   - `useWebSocket.ts`를 파일 5개로 분리
   - 테스트 가능성 개선

### P2 - Medium (1개월 내)
7. **API 클라이언트 개선**
   - React Query 또는 SWR 도입
   - 캐싱 전략 수립

8. **접근성 개선**
   - WCAG 2.1 AA 준수
   - 색상 대비, ARIA 라벨 추가

9. **상태 관리 개선**
   - Main Store 분리
   - 낙관적 업데이트 도입

### P3 - Low (Nice to have)
10. **인증 도입**
    - Clerk 또는 NextAuth.js

11. **번들 최적화**
    - `@next/bundle-analyzer` 도입
    - 코드 분할 최적화

12. **국제화 (i18n)**
    - `next-intl` 도입
    - 다국어 지원

---

## 15. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Design System 구축
- [ ] 타입 시스템 재구성
- [ ] 컴포넌트 구조 개편

### Phase 2: Quality (Week 3-4)
- [ ] 테스트 커버리지 70% 달성
- [ ] 접근성 개선
- [ ] 성능 최적화

### Phase 3: Enhancement (Month 2)
- [ ] API 클라이언트 개선
- [ ] 상태 관리 최적화
- [ ] 번들 최적화

---

## 16. Conclusion

Ralph Stock Analysis Frontend는 **최신 기술 스택과 견고한 아키텍처**를 기반으로 구축되었습니다. 특히 WebSocket 기반 실시간 데이터 연동과 TypeScript 타입 시스템이 우수합니다.

그러나 **컴포넌트 재사용성, Design System, 테스트 커버리지** 측면에서 개선이 필요합니다. 이 보고서의 권장사항을 순차적으로 도입하면 **생산성, 유지보수성, 사용자 경험**을 크게 개선할 수 있습니다.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-06
**Next Review**: 2026-03-06
