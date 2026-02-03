# 프론트엔드 QA 분석 보고서

**분석 일자:** 2026-02-02
**수정 일자:** 2026-02-02 (최신 업데이트)
**분석 대상:** frontend/ 디렉토리 전체
**분석 범위:** TypeScript 타입 안전성, React 패턴, 성능, 접근성, 에러 처리, 보안, UI/UX, 코드 품질

---

## 백엔드 팀 전용: 프론트엔드-백엔드 협력 가이드 🔗

### API 응답 표준

프론트엔드는 다음 API 응답 형식을 기대합니다:

```typescript
// 차트 데이터 응답 (GET /api/kr/stocks/{ticker}/chart)
interface IStockChartResponse {
  ticker: string;           // 종목 코드 (예: "005930")
  period: string;           // 조회 기간 ("1mo" | "3mo" | "6mo" | "1y")
  data: ChartPoint[];
  total_points: number;     // 데이터 개수
}

interface ChartPoint {
  date: string;             // YYYY-MM-DD 형식 권장
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
```

### 에러 응답 표준

```typescript
// 에러 발생 시 프론트엔드가 기대하는 형식
interface IErrorResponse {
  error: {
    code: string;           // 에러 코드 (예: "NO_DATA", "SERVER_ERROR")
    message: string;        // 사용자에게 표시할 메시지
    details?: any;          // 디버깅용 상세 정보
  }
}
```

### WebSocket 메시지 포맷

```typescript
// WebSocket 메시지 표준
interface IWSMessage {
  type: "connected" | "price_update" | "index_update" | "market_gate" | "error";
  data: any;
  timestamp?: string;
}
```

### 백엔드 수정 요청사항 (2026-02-02)

| 우선순위 | 항목 | 설명 | 관련 파일 |
|----------|------|------|----------|
| P0 | 데이터 수집 | `daily_prices` 테이블에 OHLCV 데이터 필요 | `src/tasks/collection_tasks.py` |
| P0 | Celery Worker | 데이터 수집 태스크 실행 중인지 확인 | `tasks/celery_app.py` |
| P1 | API 파라미터 | `period` 파라미터 지원 확인 ("1mo", "3mo", "6mo", "1y") | `services/api_gateway/main.py` |

상세 내용은 `docs/report/backend_chart_fix_request_20260202.md` 참고.

---

## 1. 요약 (Executive Summary)

전체적으로 **양호한 코드 품질**을 보이나, 몇 가지 개선이 필요한 영역이 있습니다.

| 평가 항목 | 등급 | 비고 |
|-----------|------|------|
| TypeScript 타입 안전성 | 🟡 B+ | `any` 타입 사용, 일부 누락된 타입 |
| React 패턴/모범 사례 | 🟢 A | 클린 코드, 적절한 Hook 사용 |
| 성능 최적화 | 🟢 A | useMemo/useCallback 적절히 활용 |
| 접근성 (a11y) | 🟡 B | aria-label 부분적 사용, 개선 여지 |
| 에러 처리 | 🟡 B | console.error만, 사용자 피드백 부족 |
| 보안 | 🟢 A | XSS 방지, 외부 URL 처리 적절 |
| UI/UX | 🟢 A | 반응형 디자인, 다크 모드 지원 |
| 코드 품질 | 🟢 A | 일관된 스타일, 적절한 모듈화 |

---

## 2. 발견된 이슈

### 2.1 [HIGH] TypeScript 타입 안전성

#### Issue 2.1.1: `any` 타입 사용 (`websocket.ts:34`, `types/index.ts:91`)

```typescript
// lib/websocket.ts:34
export interface WSMessage {
  type: WSMessageType;
  [key: string]: any;  // ⚠️ any 타입
}

// types/index.ts:91
export interface WSMessage {
  type: WSMessageType;
  [key: string]: any;  // ⚠️ any 타입
}
```

**위험도:** 중간
- 타입 안전성 보장 X
- 런타임 에러 가능성

**제안:** discriminated union 사용

```typescript
// 개선 제안
export type WSMessage =
  | ConnectedMessage
  | SubscribedMessage
  | PriceUpdateMessage
  | IndexUpdateMessage
  | MarketGateUpdateMessage
  | ErrorMessage;
```

#### Issue 2.1.2: 누락된 Props 타입 (`dashboard/kr/page.tsx:173`)

```typescript
function BacktestStats({
  stats,
  label
}: {
  stats: IBacktestStatsItem;  // ⚠️ IBacktestStatsItem는 로컬 인터페이스
  label: string;
}) {
```

**문제:** `IBacktestStatsItem`이 로컬 인터페이스로 정의되어 있음 (line 227)
- 타입 Import 오류 가능성
- `types/index.ts`에 없는 타입 사용

**제안:** 공통 타입을 `types/index.ts`로 이동

---

### 2.2 [MEDIUM] 에러 처리 및 사용자 피드백

#### Issue 2.2.1: console.error만 사용, 사용자 알림 없음 ✅ **부분 해결 (2026-02-02)**

**해결된 파일:** `app/chart/page.tsx`

```typescript
// app/chart/page.tsx - 개선됨
const [error, setError] = useState<ErrorMessage | null>(null);

interface ErrorMessage {
  title: string;
  message: string;
  canRetry: boolean;
}

// 에러 발생 시 상태 설정
catch (err) {
  console.error("차트 데이터 로드 실패:", err);
  setChartData([]);
  setError({
    title: "차트 데이터 로드 실패",
    message: "서버 연결에 실패했거나 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    canRetry: true,
  });
}
```

**남은 파일 (개선 필요):**

```typescript
// lib/api-client.ts:117
if (process.env.NODE_ENV === "development") {
  console.error(`[API Error] ...`, error.message);
}
// 사용자에게 알림 없음

// app/dashboard/kr/page.tsx:257
} catch (error) {
  console.error("Failed to load KR overview data:", error);
  // 사용자에게 알림 없음
}
```

**제안:**
```typescript
// 글로벌 에러 핸들러 또는 Toast UI 사용
import { toast } from "@/hooks/use-toast"; // 또는 Toast UI

catch (error) {
  console.error("Failed to load...", error);
  toast.error("데이터를 불러오지 못했습니다. 다시 시도해주세요.");
}
```

#### Issue 2.2.2: API 재시도 로직이 사용자에게 표시되지 않음

```typescript
// lib/api-client.ts:98-112
// 최대 5회 재시도하지만 사용자에게 표시하지 않음
if (originalRequest._retryCount <= 5) {
  // 재시도 중이라는 표시 없음
}
```

---

### 2.3 [MEDIUM] 접근성 (Accessibility)

#### Issue 2.3.1: 누락된 aria-label

```typescript
// app/page.tsx:52
<button
  onClick={() => setShowDashboard(!showDashboard)}
  className="..."
  // ⚠️ aria-label 없음
>
  {showDashboard ? "간단 보기" : "전체 보기"}
</button>
```

**제안:**
```typescript
<button
  onClick={() => setShowDashboard(!showDashboard)}
  aria-label={showDashboard ? "간단 보기로 전환" : "전체 보기로 전환"}
  aria-pressed={showDashboard}
>
```

#### Issue 2.3.2: 키보드 네비게이션 개선 필요

```typescript
// components/Watchlist.tsx (추정 확인 필요)
// 클릭만 가능하고 키보드 엔터 지원 안 될 수 있음
```

---

### 2.4 [MEDIUM] React 패턴

#### Issue 2.4.1: useEffect 의존성 배열 오류 (`app/page.tsx:26`)

```typescript
useEffect(() => {
  fetchSignals();
}, [fetchSignals]);  // ⚠️ fetchSignals가 매번 새로 생성됨
```

**문제:** `useStore`가 함수를 매번 새로 생성하면 무한 루프 가능성

**확인 필요:** Zustand store의 `fetchSignals` 안정성

#### Issue 2.4.2: 빈 의존성 배열의 콜백 경고 (`useWebSocket.ts:270`)

```typescript
useEffect(() => {
  // ...
}, []);  // 빈 배열이지만 `options`를 사용하지 않음
```

**실제 코드:** `options`는 deps에 없지만 함수 내부에서 사용 - 이는 의도적인 설계일 수 있음

---

### 2.5 [LOW] UI/UX 개선 사항

#### Issue 2.5.1: 로딩 상태 일관성 부족

| 컴포넌트 | 로딩 표현 | 개선 필요 |
|----------|-----------|----------|
| `chart/page.tsx` | "로딩 중..." 텍스트 | 스켈레톤 UI 권장 |
| `dashboard/kr/page.tsx` | 스피너 + 텍스트 | ✅ 양호 |
| `RealtimePriceCard` | "연결 중..." 텍스트 | ✅ 양호 |

#### Issue 2.5.2: 빈 상태 처리 ✅ **해결 완료 (2026-02-02)**

```typescript
// chart/page.tsx:334-351 - 수정됨
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
        <button onClick={() => setSelectedTicker(selectedTicker)} className="...">
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
```

**개선 사항:**
- 에러 상태 관리 추가 (`error` state)
- 재시도 버튼 구현
- 로딩 스피너 애니메이션 추가
- 사용자 친화적인 에러 메시지

#### Issue 2.5.3: 다크 모드 전환 시 깜빡임

```typescript
// layout.tsx:15
<html lang="ko" suppressHydrationWarning>
```

- `suppressHydrationWarning`이 있어 경고는 억제되지만
- FOCR (Flash of Content) 발생 가능
- `next-themes` 라이브러리 사용 권장

---

### 2.6 [LOW] 성능

#### Issue 2.6.1: 불필요한 재렌더링 가능성

```typescript
// dashboard/kr/page.tsx:271-274
const sortedSectors = useMemo(() => {
  if (!marketGate?.sectors) return [];
  return [...marketGate.sectors].sort((a, b) => b.change_pct - a.change_pct);
}, [marketGate]);  // ⚠️ marketGate 전체 객체를 의존성으로 사용
```

**문제:** `marketGate`의 다른 속성이 변경되어도 재계산됨

**개선:**
```typescript
}, [marketGate?.sectors]);  // sectors만 의존성으로 사용
```

#### Issue 2.6.2: WebSocket 재연결 시도 제한

```typescript
// lib/websocket.ts:152
maxAttempts: 10,     // 최대 10회 시도
```

**설계 확인:** 10회 후 재시도 포기가 의도적인가?
- 사용자가 수동으로 재연결할 방법이 없음

---

### 2.7 [LOW] 코드 품질

#### Issue 2.7.1: 일관되지 않은 인터페이스 네이밍

| 파일 | 규칙 | 예시 |
|------|------|------|
| `types/index.ts` | `I` 접두사 사용 | `IStockDetail`, `IChartPoint` |
| `websocket.ts` | `I` 접두사 미사용 | `WSMessage`, `PriceUpdateMessage` |
| `utils.ts` | `I` 접두사 미사용 | `MarkdownPart` |

**제안:** 전역적으로 `I` 접두사 규칙 통일 (클린 코드에서는 권장하지 않으나 프로젝트 규칙에 따름)

#### Issue 2.7.2: 중복 타입 정의

```typescript
// types/index.ts:89-92
export interface WSMessage { ... }  // 전역 정의

// lib/websocket.ts:31-34
export interface WSMessage { ... }  // 로컬 정의
```

**문제:** 같은 타입이 두 곳에 정의됨

---

### 2.8 [SECURITY] 보안

#### Issue 2.8.1: XSS 방지 - 양호 ✅

```typescript
// utils.ts:228-236
export function isExternalUrl(url: string): boolean {
  // 외부 URL 확인 로직 적절히 구현됨
}

// ChatbotWidget.tsx:129
rel={isExternal ? "noopener noreferrer" : undefined}  // ✅ 보안 안전
```

#### Issue 2.8.2: dangerouslySetInnerHTML 미사용 ✅

- 모든 렌더링에서 React 기본 방식 사용
- 마크다운 파싱도 안전하게 처리됨

---

## 3. 양호한 부분 ✅

### 3.1 React 모범 사례

1. **적절한 Hook 분리**: `useWebSocket`, `useMarketIndices`, `useRealtimePrices`
2. **커스텀 Hook 재사용**: `useTypingAnimation`
3. **Zustand 활용**: 간단한 전역 상태 관리
4. **클라이언트/서버 컴포넌트 분리**: `"use client"` 지시자 적절히 사용

### 3.2 타입 안전성

1. **대부분의 인터페이스 정의 완료**: `types/index.ts`에 547개 라인
2. **API 응답 타입 정의**: `IStockChart`, `IFlowHistory`, `ISignalHistory` 등

### 3.3 WebSocket 구현

1. **싱글톤 패턴**: 중복 연결 방지
2. **재연결 로직**: 지수 백오프
3. **종료 코드별 대응**: `noReconnectCodes`, `immediateCodes`
4. **대기열 처리**: `_pendingSubscriptions`로 Fast Refresh 대응

### 3.4 UI/UX

1. **다크 모드 지원**: 모든 컴포넌트에 `dark:` 클래스 적용
2. **반응형 디자인**: Tailwind Grid 활용
3. **로딩 상태 표시**: 스켈레톤 또는 텍스트

---

## 4. 개선 우선순위

| Priority | Issue | 영향 | 상태 | 예상 작업량 |
|----------|-------|------|------|-------------|
| **P1** | 에러 처리 사용자 피드백 추가 | 사용자 경험 | 🔶 진행중 (chart/page.tsx 완료) | 1-2시간 |
| **P2** | `any` 타입 제거 | 타입 안전성 | ⏳ 대기중 | 1-2시간 |
| **P2** | 접근성 aria-label 추가 | 접근성 | ⏳ 대기중 | 1시간 |
| **P3** | 빈 상태 UI 개선 | 사용자 경험 | ✅ 완료 (chart/page.tsx) | - |
| **P3** | 타입 정의 통일 (중복 제거) | 유지보수성 | ⏳ 대기중 | 30분 |
| **P4** | 성능 최적화 (useMemo 의존성) | 성능 | ⏳ 대기중 | 30분 |

### 2026-02-02 수정 완료 사항 ✅

| 파일 | 수정 내용 |
|------|----------|
| `frontend/lib/api-client.ts` | API 파라미터 `days` → `period` 통일 |
| `frontend/app/chart/page.tsx` | 에러 상태 관리, 재시도 버튼, 로딩 스피너 추가 |

---

## 5. 테스트 커버리지 현황

**파일:** `__tests__/` 디렉토리

| 테스트 파일 | 상태 | 커버리지 |
|-------------|------|----------|
| `StockChart.test.tsx` | ✅ 존재 | 양호 |
| `NaverChartWidget.test.tsx` | ✅ 존재 | 확인 필요 |
| `CandlestickChart.test.tsx` | ✅ 존재 | 확인 필요 |
| `WebSocketStatus.test.tsx` | ✅ 존재 | 확인 필요 |
| `chart.test.tsx` | ✅ 존재 | 확인 필요 |
| `infrastructure.test.ts` | ✅ 존재 | 양호 |

**개선 제안:**
- `lib/api-client.ts` 테스트 추가
- `lib/websocket.ts` 테스트 추가
- E2E 테스트 확장

---

## 6. ESLint 설정

```javascript
// next.config.js:9-11
eslint: {
  ignoreDuringBuilds: true,  // ⚠️ 빌드 시 ESLint 무시
}
```

**문제:** 빌드 시 코드 품질 검사를 건너뜀

**제안:** 개발 환경에서는 ESLint 활성화, CI/CD에서 강제

---

## 7. 결론

전체적으로 **잘 작성된 프론트엔드 코드**입니다. 특히:
- WebSocket 구현이 견고함
- 타입 정의가 대부분 완료됨
- React 패턴을 잘 따름

**2026-02-02 개선 완료:**
1. ✅ 차트 페이지 에러 처리 개선
2. ✅ API 파라미터 백엔드와 통합 (`period`)
3. ✅ 빈 상태 UI 개선 (재시도 버튼)

**다음 우선 개선:**
1. 다른 페이지 에러 처리 사용자 피드백 추가 (P1)
2. `any` 타입 제거 (P2)
3. 접근성 속성 추가 (P2)

---

## 8. 백엔드 팀 협력 체크리스트

프론트엔드가 원활히 동작하기 위해 백엔드 팀의 협력이 필요합니다:

- [ ] **Celery Worker 실행 상태 확인**
  ```bash
  docker ps | grep celery
  ```

- [ ] **데이터 수집 태스크 실행**
  ```bash
  curl -X POST http://localhost:5111/api/kr/collect/daily-prices
  ```

- [ ] **DB 데이터 확인**
  ```sql
  SELECT ticker, COUNT(*), MAX(date) FROM daily_prices GROUP BY ticker;
  ```

- [ ] **API 응답 형식 확인**
  - `period` 파라미터 지원 여부
  - 에러 응답 표준 준수 여부

---

*보고서 작성: Claude Code*
*수정 일자: 2026-02-02*
*분석 도구: Code Analysis, TypeScript Compiler*
*관련 문서: `backend_chart_fix_request_20260202.md`*
