# 차트 시스템 가이드

Ralph Stock Analysis의 차트 시각화 시스템 문서입니다.

---

## 개요

차트 시스템은 **Recharts** 라이브러리를 기반으로 구현되었으며, 다음 데이터 소스를 통합합니다:

- **Kiwoom REST API** - 실시간 차트 데이터
- **TimescaleDB** - 과거 OHLCV 데이터
- **네이버 금융** - 외부 차트 위젯

---

## 프론트엔드 구조

### 컴포넌트 구성

| 파일 | 역할 |
|------|------|
| `frontend/app/chart/page.tsx` | 차트 데모 페이지 |
| `frontend/components/StockChart.tsx` | 주식 가격 차트 (Recharts) |
| `frontend/components/FlowChart.tsx` | 수급 흐름 차트 |
| `frontend/components/NaverChartWidget.tsx` | 네이버 금융 위젯 |

### StockChart 컴포넌트

```typescript
// 내보내는 컴포넌트
- FullStockChart    // 전체 차트 (가격 + 볼린저밴드 + 거래량)
- PriceChart        // 가격 라인 차트
- VolumeChart       // 거래량 바 차트
- MiniChart         // 스파크라인 미니 차트
- BollingerBands    // 볼린저밴드 영역
- PriceChange       // 가격 변화율 표시
```

### 데이터 타입

```typescript
interface PriceData {
  date: string;
  close: number;
  volume: number;
  upper_band?: number;   // 볼린저밴드 상단
  lower_band?: number;   // 볼린저밴드 하단
  middle_band?: number;  // 볼린저밴드 중단
}

interface IFlowDataPoint {
  date: string;
  foreign_net: number;        // 외국인 순매수
  inst_net: number;           // 기관 순매수
  foreign_net_amount?: number;
  inst_net_amount?: number;
  supply_demand_score?: number;
}
```

---

## API 엔드포인트

### 1. 종목 차트 데이터

```
GET /api/kr/stocks/{ticker}/chart
```

**Query Parameters:**
| 파라미터 | 타입 | 범위 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `days` | integer | 1-365 | 30 | 조회 일수 |

**Response:**
```json
{
  "ticker": "005930",
  "period": "30d",
  "data": [
    {
      "date": "2026-01-01",
      "open": 80000,
      "high": 81000,
      "low": 79500,
      "close": 80500,
      "volume": 15000000
    }
  ],
  "total_points": 30
}
```

**사용 예시:**
```bash
# 최근 90일 차트 데이터
curl "http://localhost:5111/api/kr/stocks/005930/chart?days=90"
```

---

### 2. 수급 데이터 (외국인/기관 순매수)

```
GET /api/kr/stocks/{ticker}/flow
```

**Query Parameters:**
| 파라미터 | 타입 | 범위 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `days` | integer | 5-60 | 20 | 조회 일수 |

**Response:**
```json
{
  "ticker": "005930",
  "period_days": 20,
  "data": [
    {
      "date": "2026-01-20",
      "foreign_net": 1500000,
      "inst_net": 800000,
      "foreign_net_amount": 120000000000,
      "inst_net_amount": 64000000000,
      "supply_demand_score": 65.5
    }
  ],
  "smartmoney_score": 72.5,
  "total_points": 20
}
```

**SmartMoney 점 산출:**
- 외국인 5일 순매수 비중: 40%
- 기관 5일 순매수 비중: 30%
- 외국인 연속 순매수 일수: 15%
- 이중 매수 (외국인+기관 동시 순매수): 15%

**사용 예시:**
```bash
# 최근 20일 수급 데이터
curl "http://localhost:5111/api/kr/stocks/005930/flow?days=20"
```

---

### 3. Kiwoom 차트 API

```
GET /api/kr/kiwoom/chart/{ticker}
```

Kiwoom REST API를 통해 실시간 차트 데이터를 제공합니다.

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `days` | integer | 조회 일수 (30, 60, 120) |

**주의사항:**
- Kiwoom API는 역순으로 데이터 반환 → 날짜 오름차순 정렬 필수
- Rate limiting: 요청 간 0.5초 지연 권장

---

## 기술적 지표

### 제공되는 지표

`frontend/lib/utils/technicalIndicators.ts`:

| 함수 | 설명 |
|------|------|
| `calculateSMA(prices, period)` | 단순 이동평균 |
| `calculateEMA(prices, period)` | 지수 이동평균 |
| `calculateRSI(prices, period)` | RSI (0-100) |
| `calculateMACD(prices)` | MACD 라인/Signal/Histogram |
| `calculateBollingerBands(prices)` | 볼린저밴드 (상단/중간/하단) |
| `calculate52WeekHighLow(prices)` | 52주 신고가/신저가 |

### 볼린저밴드 계산

```typescript
function calculateBollingerBands(
  prices: number[],
  period: number = 20,
  multiplier: number = 2
): {
  upper: number;    // 중간밴드 + (2 × 표준편차)
  middle: number;   // 기간 SMA
  lower: number;    // 중간밴드 - (2 × 표준편차)
  bandwidth: number; // 상단 - 하단
}
```

---

## Recharts 차트 구성

### 가격 차트

```tsx
<LineChart data={chartData} syncId="price">
  <CartesianGrid strokeDasharray="3 3" />
  <XAxis dataKey="date" />
  <YAxis domain={[minPrice, maxPrice]} />
  <Tooltip />
  <Legend />
  <Line dataKey="price" stroke="#3b82f6" strokeWidth={2} />
  <Line dataKey="upper" stroke="#ef4444" strokeDasharray="5 5" />
  <Line dataKey="lower" stroke="#22c55e" strokeDasharray="5 5" />
</LineChart>
```

### 거래량 차트

```tsx
<BarChart data={chartData} syncId="volume">
  <XAxis dataKey="date" />
  <YAxis tickFormatter={(value) => {
    if (value >= 100000000) return `${(value / 100000000).toFixed(1)}억`;
    if (value >= 10000) return `${(value / 10000).toFixed(0)}천`;
    return value;
  }} />
  <Bar dataKey="volume" fill="#3b82f6" opacity={0.5} />
</BarChart>
```

### 수급 차트

```tsx
<BarChart data={chartData}>
  <XAxis dataKey="date" />
  <YAxis />
  <Bar dataKey="foreign_net" name="외국인" fill="#ef4444" />
  <Bar dataKey="inst_net" name="기관" fill="#3b82f6" />
</BarChart>
```

---

## 데이터 흐름

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Chart Page     │────▶│   apiClient     │────▶│  API Gateway    │
│  (chart/page)   │     │ (api-client.ts) │     │  (main.py)      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                           │
                              ┌──────────────────────────────┼───────────────────┐
                              ▼                              ▼                   ▼
                       ┌─────────────┐            ┌──────────────┐      ┌──────────────┐
                       │ TimescaleDB │            │ Kiwoom REST  │      │ StockRepo    │
                       │ (DailyPrice)│            │  (실시간)     │      │ (flow data)  │
                       └─────────────┘            └──────────────┘      └──────────────┘
```

---

## 포맷 유틸리티

`frontend/lib/utils.ts`:

| 함수 | 설명 | 예시 |
|------|------|------|
| `formatPrice()` | 가격 포맷 | "159,500원" |
| `formatPercent()` | 퍼센트 포맷 | "+5.23%" |
| `formatNumber()` | 숫자 콤마 | "1,234,567" |
| `getGradeColor()` | 등급별 색상 | S: 노란색, A: 초록색 |

---

## 의존성

```json
{
  "recharts": "^2.x",      // 차트 라이브러리
  "axios": "^1.x",         // API 클라이언트
  "clsx": "^2.x",          // 클래스 유틸리티
  "tailwind-merge": "^2.x" // Tailwind 병합
}
```

---

## 차트 페이지 사용법

### 접속

```
http://localhost:5110/chart
```

### 기능

1. **종목 선택**
   - 검색으로 종목 찾기
   - 빠른 선택 버튼 (삼성전자, SK하이닉스, NAVER, 현대차)

2. **미니 차트**
   - 4개 종목의 1개월 요약 차트
   - 클릭하여 메인 차트에서 종목 변경

3. **전체 차트**
   - 가격 라인 차트
   - 볼린저밴드 (상단/하단)
   - 거래량 바 차트

---

*Last updated: 2026-01-30*
