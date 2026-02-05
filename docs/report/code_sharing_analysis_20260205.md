# 프론트엔드 코드 공유 분석 보고서

**작성일:** 2026-02-05
**범위:** 메인 대시보드(VCP) vs 단타 추천(Daytrading) 프론트엔드 코드 공유 현황

---

## 1. 개요

메인 대시보드와 단타 추천 페이지 간의 프론트엔드 코드 공유 현황을 분석하고, 중복 구현을 찾아 통합 방안을 제안합니다.

**원칙:** 메인 대시보드가 표준 (Standard), 단타 추천이 따라야 함 (Follow)

---

## 2. 이미 공유 중인 컴포넌트 ✅

### 2.1 ShadCN UI Components

| 컴포넌트 | 경로 | 사용 현황 |
|----------|------|----------|
| Button | `components/ui/button.tsx` | 메인, 단타 공통 ✅ |
| Card | `components/ui/card.tsx` | 메인, 단타 공통 ✅ |
| Badge | `components/ui/badge.tsx` | 메인, 단타 공통 ✅ |
| Table | `components/ui/table.tsx` | 메인, 단타 공통 ✅ |
| Skeleton | `components/ui/skeleton.tsx` | 로딩 상태 공통 ✅ |

### 2.2 유틸리티 함수 (lib/utils.ts)

| 함수 | 설명 | 공유 현황 |
|------|------|----------|
| `formatPrice()` | 가격 포맷팅 (원화) | ✅ 공유 중 |
| `formatPercent()` | 퍼센트 포맷팅 | ✅ 공유 중 |
| `formatNumber()` | 숫자 포맷팅 | ✅ 공유 중 |
| `getMarketGateColor()` | Market Gate 색상 | ✅ 공유 중 |
| `getGradeColor()` | 등급 색상 | ⚠️ 단타에서 미사용 |
| `cn()` | Tailwind 클래스 결합 | ✅ 공유 중 |

### 2.3 API/WebSocket 클라이언트

| 클라이언트 | 경로 | 공유 현황 |
|-----------|------|----------|
| API Client | `lib/api-client.ts` | ✅ 단일 인스턴스 공유 |
| WebSocket Client | `lib/websocket.ts` | ✅ 단일 클라이언트 공유 |

### 2.4 공통 컴포넌트

| 컴포넌트 | 설명 | 사용처 |
|----------|------|--------|
| RealtimePriceCard | 실시간 가격 카드 | 메인, 단타 공통 ✅ |
| WebSocketStatus | WebSocket 연결 상태 | 공통 ✅ |
| ThemeToggle | 다크 모드 토글 | 공통 ✅ |

---

## 3. 중복 구현 발견 (통합 필요) ⚠️

### 3.1 Grade Color (등급 색상) - **색상이 완전히 다름!**

#### 메인 대시보드 (lib/utils.ts)

```typescript
export function getGradeColor(grade: string): string {
  switch (grade) {
    case "S":
      return "bg-red-100 text-red-700 border-red-300 dark:bg-red-900/30 dark:text-red-400"
    case "A":
      return "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-900/30 dark:text-orange-400"
    case "B":
      return "bg-yellow-100 text-yellow-700 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-400"
    case "C":
      return "bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-400"
    default:
      return "bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-900/30 dark:text-gray-400"
  }
}
```

**특징:**
- ✅ Dark Mode 지원 (`dark:bg-red-900/30`)
- ✅ Border 포함 (`border-red-300`)
- ✅ Pastel 톤 (100 배경색)

#### 단타 추천 (DaytradingSignalTable.tsx)

```typescript
const GRADE_COLORS: Record<string, string> = {
  S: "bg-yellow-500 text-white",
  A: "bg-green-500 text-white",
  B: "bg-blue-500 text-white",
  C: "bg-gray-500 text-white",
}
```

**특징:**
- ❌ Dark Mode 미지원
- ❌ Border 없음
- ❌ 진한 색상 (500 배경색)

#### 색상 비교표

| 등급 | 메인 대시보드 | 단타 추천 | 일치 여부 |
|------|-------------|----------|----------|
| S | **Red** (빨강) | **Yellow** (노랑) | ❌ |
| A | **Orange** (주황) | **Green** (초록) | ❌ |
| B | **Yellow** (노랑) | **Blue** (파랑) | ❌ |
| C | **Blue** (파랑) | **Gray** (회색) | ❌ |

#### 수정 필요

**파일:** `frontend/components/DaytradingSignalTable.tsx:45-50`

```typescript
// 삭제
const GRADE_COLORS: Record<string, string> = {
  S: "bg-yellow-500 text-white",
  A: "bg-green-500 text-white",
  B: "bg-blue-500 text-white",
  C: "bg-gray-500 text-white",
}

// 변경 (라인 193)
// 기존
<Badge className={GRADE_COLORS[signal.grade]}>

// 수정 후
import { getGradeColor } from "@/lib/utils"
<Badge className={getGradeColor(signal.grade)}>
```

---

### 3.2 Signal Type 인터페이스 - 필드명 불일치

#### 메인 대시보드 (types/index.ts)

```typescript
export interface Signal {
  ticker: string;
  name: string;
  signal_type: string;          // "VCP" | "JONGGA_V2"
  score: number | ScoreDetail;  // ✅ score
  grade: string;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;           // ✅ stop_loss
  position_size?: number;
  reasons?: string[];
  created_at: string;           // ✅ created_at
}
```

#### 단타 추천 (types/index.ts)

```typescript
export interface IDaytradingSignal {
  ticker: string;
  name: string;
  market: "KOSPI" | "KOSDAQ";
  total_score: number;          // ⚠️ total_score (다름)
  grade: "S" | "A" | "B" | "C";
  checks: IDaytradingCheck[];    // ✅ 체크리스트 배열
  signal_type: DaytradingSignalType;  // "STRONG_BUY" | "BUY" | "WATCH"
  current_price?: number;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;           // ✅ stop_loss (일치)
  detected_at?: string;         // ⚠️ detected_at (다름)
}
```

#### 필드명 비교

| 필드 | 메인 대시보드 | 단타 추천 | 통합 제안 |
|------|-------------|----------|----------|
| 점수 | `score` | `total_score` | → `score` |
| 생성일시 | `created_at` | `detected_at` | → `created_at` |
| 손절가 | `stop_loss` (FE) / `stop_price` (DB) | `stop_loss` | → `stop_loss` |
| 체크리스트 | 없음 | `checks[]` | 단타 전용 유지 |

---

### 3.3 State Management (Zustand Store)

#### 메인 대시보드 (store/index.ts)

```typescript
interface AppState {
  signals: Signal[];
  filters: FilterState;
  // ... 공통 상태
}

export const useStore = create<AppState>((set) => ({...}));
```

#### 단타 추천 (store/daytradingStore.ts)

```typescript
interface IDaytradingState {
  signals: IDaytradingSignal[];
  filters: DaytradingFilterState;
  fetchDaytradingSignals: () => Promise<void>;
  scanDaytradingMarket: () => Promise<void>;
  // ... 단타 전용 상태
}

export const useDaytradingStore = create<IDaytradingState>((set) => ({...}));
```

#### 통합 가능성

**공통 패턴:**
```typescript
// 공통 베이스 인터페이스
interface ISignalBase {
  ticker: string;
  name: string;
  score: number;
  grade: "S" | "A" | "B" | "C";
  created_at: string;
}

// 시그널 타입별 확장
interface IVCPSignal extends ISignalBase {
  signal_type: "VCP" | "JONGGA_V2";
  contraction_ratio?: number;
  foreign_5d?: number;
  inst_5d?: number;
}

interface IDaytradingSignal extends ISignalBase {
  signal_type: "STRONG_BUY" | "BUY" | "WATCH";
  checks: IDaytradingCheck[];
}
```

---

### 3.4 WebSocket Hooks

#### 메인 대시보드 (hooks/useWebSocket.ts)

```typescript
export function useSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  // ...
  subscribe("signal:vcp");  // ✅ 작동
}
```

#### 단타 추천 (hooks/useWebSocket.ts)

```typescript
export function useDaytradingSignals() {
  const [signals, setSignals] = useState<IDaytradingSignal[]>([]);
  // ...
  subscribe("signal:daytrading");  // ⚠️ 백엔드 미구현
}
```

#### 통합 가능성

```typescript
// 통합 패턴
export function useSignals(signalType: "vcp" | "daytrading") {
  const [signals, setSignals] = useState<ISignalBase[]>([]);

  useEffect(() => {
    if (connected) {
      subscribe(`signal:${signalType}`);
    }
  }, [connected, signalType]);

  return { signals, isRealtime, connected };
}
```

---

## 4. 통합 우선순위 및 작업량

### Phase 1: Grade Color 통일 (긴급)

**목표:** 단타 추천 페이지도 메인 대시보드의 등급 색상 사용

- [ ] `DaytradingSignalTable.tsx`의 `GRADE_COLORS` 상수 삭제
- [ ] `lib/utils.ts`의 `getGradeColor()` 함수 import
- [ ] `Badge` 컴포넌트의 className 변경
- [ ] Dark Mode 지원 확인

**작업량:** 30분

**영향 파일:**
- `frontend/components/DaytradingSignalTable.tsx`

### Phase 2: 타입 정의 통일

**목표:** 공통 베이스 인터페이스 정의

- [ ] `ISignalBase` 베이스 인터페이스 정의
- [ ] `IVCPSignal`, `IDaytradingSignal` 확장 인터페이스 정의
- [ ] 기존 `Signal`, `IDaytradingSignal` 타입 마이그레이션

**작업량:** 1-2시간

**영향 파일:**
- `frontend/types/index.ts`

### Phase 3: State/Hook 통합

**목표:** 단일 Store/Hook 패턴 구현

- [ ] 공통 `useSignals(signalType)` Hook 구현
- [ ] Store 구조 재검토 (선택 사항)

**작업량:** 2-3시간

**영향 파일:**
- `frontend/hooks/useWebSocket.ts`
- `frontend/store/index.ts`
- `frontend/store/daytradingStore.ts`

---

## 5. 결론

### 주요 발견

1. **Grade Color 중복**: 색상이 완전히 다름, 메인 대시보드 기준으로 통일 필요
2. **타입 필드명 불일치**: `score` vs `total_score`, `created_at` vs `detected_at`
3. **Store/Hook 분리**: 두 시스템이 별도의 Store/Hook 사용

### 통합 방향

1. **Grade Color**: 메인 대시보드의 `getGradeColor()` 함수를 표준으로 사용
2. **타입 정의**: 공통 베이스 인터페이스 + 시그널 타입별 확장 패턴
3. **State/Hook**: `useSignals(signalType)` 패턴으로 단일화

**총 작업량 예상:** 4-6시간 (Grade Color 30분 + 타입 정의 1-2시간 + State/Hook 2-3시간)

---

## 6. 참고 파일

| 파일 | 설명 |
|------|------|
| `frontend/lib/utils.ts` | 공통 유틸리티 (getGradeColor 포함) |
| `frontend/components/DaytradingSignalTable.tsx` | 단타 시그널 테이블 (GRADE_COLORS 중복) |
| `frontend/types/index.ts` | 타입 정의 (Signal, IDaytradingSignal) |
| `frontend/store/index.ts` | 메인 대시보드 Store |
| `frontend/store/daytradingStore.ts` | 단타 추천 Store |
| `frontend/hooks/useWebSocket.ts` | WebSocket Hooks |

### 관련 보고서

- `schema_comparison_20260205.md` - 스키마 및 전체 비교
- `websocket_backend_20260205.md` - WebSocket 백엔드 분석
- `websocket_frontend_20260205.md` - WebSocket 프론트엔드 분석
