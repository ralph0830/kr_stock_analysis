# 차트 페이지 실시간 가격 연동 가이드

## 개요

차트 페이지(`/chart`)에 대시보드의 `useRealtimePrices` Hook 인프라를 활용하여 실시간 가격 표시 기능을 통합했습니다.

## 통합 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Chart Page                              │
├─────────────────────────────────────────────────────────────────┤
│  1. ChartRealtimePriceHeader (선택된 종목 상세)                │
│  2. ChartRealtimePrice (모든 종목 실시간 가격 그리드)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ChartRealtimePrice.tsx                       │
│  - useWebSocket Hook → 실시간 데이터 연결                       │
│  - getPrice(ticker) → 종목별 가격 조회                          │
│  - WebSocket 실패 시 API 폴링 자동 전환                         │
└─────────────────────────────────────────────────────────────────┘
```

## 주요 컴포넌트

### 1. ChartRealtimePriceHeader

선택된 종목의 현재 가격을 크게 표시하는 헤더 컴포넌트입니다.

**위치:** `frontend/components/realtime/ChartRealtimePrice.tsx`

**기능:**
- 종목명, 티커 표시
- 실시간 가격 (대형 폰트)
- 전일대비 변동액/변동률
- 거래량, 업데이트 시간
- WebSocket 연결 상태 인디케이터
- 가격 변동 시 색상 애니메이션

**사용 예시:**
```tsx
<ChartRealtimePriceHeader
  ticker="005930"
  name="삼성전자"
/>
```

### 2. ChartRealtimePrice

여러 종목의 실시간 가격을 그리드로 표시하는 컴포넌트입니다.

**Props:**
```typescript
interface IChartRealtimePriceProps {
  stocks: IStockInfo[];           // 표시할 종목 목록
  selectedTicker?: string;        // 현재 선택된 종목
  onStockSelect?: (ticker: string) => void;  // 종목 선택 콜백
  compact?: boolean;              // 컴팩트 모드
}
```

**사용 예시:**
```tsx
<ChartRealtimePrice
  stocks={[
    { ticker: "005930", name: "삼성전자" },
    { ticker: "000020", name: "동서" },
  ]}
  selectedTicker={selectedTicker}
  onStockSelect={setSelectedTicker}
  compact={false}
/>
```

## 데이터 흐름

### 1. WebSocket 연결 흐름

```
클라이언트 마운트
    │
    ▼
useWebSocket({ autoConnect: true })
    │
    ├─► WebSocket 연결 성공
    │       │
    │       ▼
    │   price:{ticker} 토픽 구독
    │       │
    │       ▼
    │   실시간 가격 업데이트 (WebSocket)
    │
    └─► WebSocket 연결 실패
            │
            ▼
        API 폴링 모드 (15초 간격)
```

### 2. 가격 데이터 구독

`useRealtimePrices` Hook은 자동으로 다음을 처리합니다:

1. **WebSocket 연결 시:** `price:{ticker}` 토픽 구독
2. **WebSocket 연결 실패 시:** API 폴링으로 자동 전환
3. **종목 변경 시:** 자동으로 토픽 재구독

## 파일 구조

```
frontend/
├── app/
│   └── chart/
│       └── page.tsx                    # 차트 페이지 (진입점)
├── components/
│   └── realtime/
│       └── ChartRealtimePrice.tsx      # 실시간 가격 컴포넌트
├── hooks/
│   └── useWebSocket.ts                 # WebSocket Hook (공통)
└── lib/
    └── utils.ts                        # 유틸리티 함수
```

## UI 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  📊 차트 시각화                          [테마] [← 홈]    │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │  [실시간 가격 헤더 - 선택된 종목]                      │  │
│  │  삼성전자 (005930)                    ● 실시간       │  │
│  │  75,300원 (+500 +0.67%)                              │  │
│  │  거래량: 12,345,678주   업데이트: 15:30:45           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  [종목 검색] [삼성전자] [동서] [+0.67%]                      │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  실시간 가격                    ● 실시간 연결됨       │  │
│  ├───────────────────────┬───────────────────────────────┤  │
│  │  삼성전자 (005930)     │  동서 (000020)               │  │
│  │  75,300원 (+0.67%)    │  12,450원 (-1.23%)          │  │
│  │  거래량: 12.3M주      │  거래량: 456K주             │  │
│  └───────────────────────┴───────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  미니 차트                                              │  │
│  ├───────────────────────┬───────────────────────────────┤  │
│  │  [삼성전자 미니차트]   │  [동서 미니차트]              │  │
│  └───────────────────────┴───────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  [전체 차트]                                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## TypeScript 타입 정의

```typescript
// 종목 정보
export interface IStockInfo {
  ticker: string;
  name: string;
}

// 실시간 가격 데이터
export interface RealtimePrice {
  ticker: string;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  timestamp: string;
}

// 컴포넌트 Props
export interface IChartRealtimePriceProps {
  stocks: IStockInfo[];
  selectedTicker?: string;
  onStockSelect?: (ticker: string) => void;
  compact?: boolean;
}

export interface IChartRealtimePriceHeaderProps {
  ticker: string;
  name: string;
}
```

## 접근성 (WCAG 2.1 AA)

- `aria-label`: 종목 선택 버튼에 접근 가능한 라벨 제공
- `role="list"`: 가격 그리드에 리스트 역할 지정
- `sr-only`: 스크린 리더용 안내 메시지
- 색상 외 텍스트로 상태 정보 전달

## 애니메이션

- 가격 변동 시 배경색 애니메이션 (상승: 빨강, 하락: 파랑)
- 1.5초 후 자동 초기화
- `transition-all duration-300`으로 부드러운 전환

## 사용 예시

### 차트 페이지에서 사용

```tsx
import {
  ChartRealtimePrice,
  ChartRealtimePriceHeader,
  type IStockInfo,
} from "@/components/realtime/ChartRealtimePrice";

const POPULAR_STOCKS: IStockInfo[] = [
  { ticker: "005930", name: "삼성전자" },
  { ticker: "000020", name: "동서" },
];

export default function ChartPage() {
  const [selectedTicker, setSelectedTicker] = useState("005930");

  const selectedStockInfo = POPULAR_STOCKS.find(
    (s) => s.ticker === selectedTicker
  );

  return (
    <main>
      {/* 선택된 종목 상세 헤더 */}
      {selectedStockInfo && (
        <ChartRealtimePriceHeader
          ticker={selectedStockInfo.ticker}
          name={selectedStockInfo.name}
        />
      )}

      {/* 실시간 가격 그리드 */}
      <ChartRealtimePrice
        stocks={POPULAR_STOCKS}
        selectedTicker={selectedTicker}
        onStockSelect={setSelectedTicker}
      />
    </main>
  );
}
```

## 참고 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| 차트 페이지 | `frontend/app/chart/page.tsx` | 메인 차트 페이지 |
| 실시간 가격 컴포넌트 | `frontend/components/realtime/ChartRealtimePrice.tsx` | 실시간 가격 UI |
| WebSocket Hook | `frontend/hooks/useWebSocket.ts` | WebSocket 연결 Hook |
| 대시보드 | `frontend/app/page.tsx` | 대시보드 (참고 구현) |

## 업데이트 내역

- **2026-02-07**: 초기 통합 완료
  - `ChartRealtimePrice` 컴포넌트 생성
  - `ChartRealtimePriceHeader` 컴포넌트 생성
  - 차트 페이지에 실시간 가격 표시 추가
