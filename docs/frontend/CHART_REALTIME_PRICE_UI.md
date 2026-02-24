# 차트 페이지 실시간 가격 UI 디자인 가이드

**작성일:** 2026-02-07
**작성자:** Frontend Architect
**상태:** 구현 완료

---

## 1. 개요

차트 페이지에 실시간 주식 가격 정보를 표시하는 UI 컴포넌트 설계 및 구현 문서입니다.

### 1.1 목표

- 실시간 가격 표시 (WebSocket 우선, 폴링 폴백)
- 가격 변동 시 색상 애니메이션 (빨강 ↔ 파랑)
- WebSocket 연결 상태 인디케이터
- 반응형 레이아웃 (모바일/태블릿/데스크톱)

---

## 2. 컴포넌트 구조

```
components/realtime/
├── ChartRealtimePrice.tsx         # 메인 컴포넌트
│   ├── ChartRealtimePrice         # 실시간 가격 그리드
│   ├── ChartRealtimePriceHeader   # 선택된 종목 상세 헤더
│   └── StockPriceItem             # 개별 종목 가격 아이템 (내부)
```

### 2.1 인터페이스 정의

```typescript
/**
 * 종목 정보 인터페이스
 */
export interface IStockInfo {
  ticker: string;  // 종목 코드 (6자리)
  name: string;    // 종목명
}

/**
 * 컴포넌트 Props 인터페이스
 */
export interface IChartRealtimePriceProps {
  stocks: IStockInfo[];              // 표시할 종목 목록
  selectedTicker?: string;           // 현재 선택된 종목 티커
  onStockSelect?: (ticker: string) => void;  // 선택 콜백
  compact?: boolean;                 // 컴팩트 모드 (미니 차트용)
}

/**
 * 헤더 Props 인터페이스
 */
export interface IChartRealtimePriceHeaderProps {
  ticker: string;
  name: string;
}
```

---

## 3. 디자인 사양

### 3.1 색상 시스템 (한국 주식 시장 표준)

| 상태 | 색상 | Tailwind 클래스 |
|------|------|-----------------|
| 상승 | 빨강 | `text-red-600`, `bg-red-100` |
| 하락 | 파랑 | `text-blue-600`, `bg-blue-100` |
| 보합 | 회색 | `text-gray-600`, `bg-gray-100` |
| 실시간 연결 | 초록 | `bg-green-500` (animate-pulse) |
| 연결 중 | 파랑 | `bg-blue-500` (animate-pulse) |
| 폴링 모드 | 회색 | `bg-gray-400` |

### 3.2 애니메이션

#### 가격 업데이트 하이라이트
```css
/* 상승 시 배경 애니메이션 */
bg-red-50 dark:bg-red-900/10 → transition-colors duration-300

/* 하락 시 배경 애니메이션 */
bg-blue-50 dark:bg-blue-900/10 → transition-colors duration-300

/* 애니메이션 지속 시간: 1.5초 후 초기화 */
```

#### 변동량 바 애니메이션
```css
/* 부드러운 전환 */
transition-all duration-500 ease-out
width: ${Math.min(Math.abs(change_rate) * 10, 100)}%
```

#### 펄스 애니메이션 (실시간 표시)
```css
/* 연결 상태 인디케이터 */
animate-pulse → Tailwind 내장
```

### 3.3 레이아웃 (반응형)

#### 표준 모드
| 화면 크기 | 그리드 열 |
|-----------|----------|
| 모바일 (< 640px) | 1열 |
| 태블릿 (640px - 1024px) | 2열 |
| 데스크톱 (> 1024px) | 3열 |

#### 컴팩트 모드 (미니 차트 그리드)
| 화면 크기 | 그리드 열 |
|-----------|----------|
| 모바일 (< 640px) | 2열 |
| 태블릿 (640px - 1024px) | 3열 |
| 데스크톱 (> 1024px) | 4열 |

---

## 4. 기능 명세

### 4.1 WebSocket 연결 상태 표시

| 상태 | 아이콘 | 라벨 | 색상 |
|------|-------|------|------|
| 연결됨 | ● (펄스) | 실시간 | 초록 |
| 연결 중 | ● (펄스) | 연결 중... | 파랑 |
| 폴링 | ● (고정) | 폴링 모드 | 회색 |

### 4.2 가격 정보 표시 항목

#### 표준 모드
- 종목명 (크기: base, 굵기: semibold)
- 티커 (크기: xs, 색상: gray-500)
- 현재가 (크기: 2xl, 굵기: bold, 색상: 상승/하락)
- 전일비 변동 (크기: sm, 굵기: medium)
- 등락률 (크기: xs, 배지: 둥근)
- 거래량 (크기: xs)
- 업데이트 시간 (크기: xs, HH:MM:SS)
- 변동량 바 (높이: 1.5, 둥근)

#### 컴팩트 모드
- 종목명 (크기: sm, 굵기: medium)
- 현재가 (크기: lg, 굵기: bold)
- 등락률 (크기: xs)
- 데이터 소스 뱃지

### 4.3 사용자 인터랙션

| 액션 | 동작 |
|------|------|
| 카드 클릭 | `onStockSelect(ticker)` 호출 |
| 가격 업데이트 | 배경 색상 애니메이션 (1.5초) |
| 호버 | 그림자 강조 (`hover:shadow-lg`) |

---

## 5. 접근성 (WCAG 2.1 AA)

### 5.1 ARIA 라벨

```tsx
// 종목 카드
<button
  aria-label={`${stock.name} (${stock.ticker}) 현재가 ${formatPrice(priceData.price)}, 전일대비 ${formatPrice(priceData.change)}`}
>

// 섹션
<section aria-label="실시간 주식 가격">

// 스크린 리더 안내
<p className="sr-only">
  실시간 주식 가격 정보입니다. 현재 WebSocket 실시간 연결 상태입니다.
</p>
```

### 5.2 색상 대비

- 상승/하락 색상: WCAG AA 준수 (4.5:1 이상)
- 다크 모드: 대비율 7:1 이상 (AAA)
- 텍스트 크기: 최소 14px

### 5.3 키보드 내비게이션

- `Tab`: 종목 카드 간 이동
- `Enter`/`Space`: 종목 선택
- 포커스 표시: `focus-visible` 스타일

---

## 6. 사용 예시

### 6.1 차트 페이지 헤더

```tsx
import { ChartRealtimePriceHeader } from "@/components/realtime/ChartRealtimePrice";

<ChartRealtimePriceHeader
  ticker="005930"
  name="삼성전자"
/>
```

### 6.2 실시간 가격 그리드

```tsx
import { ChartRealtimePrice } from "@/components/realtime/ChartRealtimePrice";

const stocks = [
  { ticker: "005930", name: "삼성전자" },
  { ticker: "000020", name: "동서" },
];

<ChartRealtimePrice
  stocks={stocks}
  selectedTicker={selectedTicker}
  onStockSelect={(ticker) => setSelectedTicker(ticker)}
  compact={false}
/>
```

### 6.3 컴팩트 모드 (미니 차트 그리드)

```tsx
<ChartRealtimePrice
  stocks={stocks}
  compact={true}
/>
```

---

## 7. 구현 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| 컴포넌트 | `frontend/components/realtime/ChartRealtimePrice.tsx` | 메인 컴포넌트 |
| 페이지 | `frontend/app/chart/page.tsx` | 차트 페이지 (사용) |
| 훅 | `frontend/hooks/useWebSocket.ts` | WebSocket 연결 |
| 유틸 | `frontend/lib/utils.ts` | 포맷팅 함수 |

---

## 8. 테스트 가이드

### 8.1 시각적 테스트

1. **가격 업데이트 확인**
   - WebSocket 연결 상태에서 가격 변경 확인
   - 배경 색상 애니메이션 확인 (빨강/파랑)

2. **반응형 레이아웃 확인**
   - 모바일 (375px): 1열/2열 레이아웃
   - 태블릿 (768px): 2열/3열 레이아웃
   - 데스크톱 (1280px): 3열/4열 레이아웃

3. **다크 모드 확인**
   - 배경 색상 전환 확인
   - 텍스트 대비율 확인

### 8.2 기능 테스트

1. **WebSocket 연결**
   - 연결 성공 시 "실시간" 뱃지 표시
   - 연결 실패 시 "폴링" 뱃지 표시

2. **종목 선택**
   - 카드 클릭 시 선택 상태 변경
   - 선택된 종목 하이라이트 (파랑 테두리)

3. **접근성**
   - 스크린 리더로 종목 정보 읽기
   - 키보드 탭 내비게이션

---

## 9. 성능 최적화

### 9.1 렌더링 최적화

- `useMemo`: 색상 클래스 계산
- `useCallback`: 이벤트 핸들러
- `useState`: 애니메이션 상태 관리

### 9.2 네트워크 최적화

- WebSocket: 실시간 데이터 스트리밍
- 폴링: 15초 간격 (연결 실패 시)

---

## 10. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-02-07 | 초기 구현 |

---

**문서 버전:** 1.0
**마지막 업데이트:** 2026-02-07
