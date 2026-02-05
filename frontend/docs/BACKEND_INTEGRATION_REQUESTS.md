# 백엔드 연동 요청사항

**작성일:** 2026-02-04
**작성자:** Claude Code (프론트엔드 분석 기반)

---

## 📋 개요

프론트엔드(`frontend/`)를 분석한 결과, 백엔드 API(`services/api_gateway/`)에 이미 구현되어 있으나 **프론트엔드에서 활용하지 않는 API**와 **프론트엔드에서 필요로 하는데 백엔드에 구현되지 않은 API**를 정리합니다.

---

## 1. 백엔드에 구현되어 있으나 프론트엔드에서 미사용 중인 API

### 1.1 Performance API (`/api/kr/performance/*`)

| 엔드포인트 | 설명 | 백엔드 구현 | 프론트엔드 사용 |
|-----------|------|-------------|---------------|
| `GET /api/kr/performance/cumulative` | 누적 수익률 조회 | ✅ | ❌ |
| `GET /api/kr/performance/by-signal` | 시그널별 성과 조회 | ✅ | ❌ |
| `GET /api/kr/performance/by-period` | 기간별 성과 조회 | ✅ | ❌ |
| `GET /api/kr/performance/top-performers` | 최고 성과 종목 조회 | ✅ | ❌ |
| `GET /api/kr/performance/sharpe-ratio` | 샤프 비율 조회 | ✅ | ❌ |

**파일:** `services/api_gateway/routes/performance.py`

### 1.2 News API (`/api/kr/news/*`)

| 엔드포인트 | 설명 | 백엔드 구현 | 프론트엔드 사용 |
|-----------|------|-------------|---------------|
| `GET /api/kr/news/latest` | 최신 뉴스 목록 조회 | ✅ | ❌ |
| `GET /api/kr/news/{ticker}` | 종목별 뉴스 조회 | ✅ | ❌ (컴포넌트만 있음) |

**파일:** `services/api_gateway/routes/news.py`

### 1.3 System API (`/api/system/*`)

| 엔드포인트 | 설명 | 백엔드 구현 | 프론트엔드 사용 |
|-----------|------|-------------|---------------|
| `GET /api/system/data-status` | 데이터 상태 조회 | ✅ | ❌ |
| `GET /api/system/health` | 시스템 헬스 체크 | ✅ | ❌ |
| `GET /api/system/services` | 서비스 상태 목록 | ✅ | ❌ |
| `POST /api/system/scan/vcp` | VCP 스캔 트리거 | ✅ | ❌ |
| `GET /api/system/scan/status` | 스캔 상태 조회 | ✅ | ❌ |

**파일:** `services/api_gateway/routes/system.py`

### 1.4 Backtest API (`/api/kr/backtest/*`)

| 엔드포인트 | 설명 | 백엔드 구현 | 프론트엔드 사용 |
|-----------|------|-------------|---------------|
| `GET /api/kr/backtest/summary` | 백테스트 요약 | ✅ | ❌ |
| `GET /api/kr/backtest/by-ticker` | 종목별 백테스트 | ✅ | ❌ |
| `GET /api/kr/backtest/by-date` | 날짜별 백테스트 | ✅ | ❌ |
| `GET /api/kr/backtest/export` | 백테스트 내보내기 | ✅ | ❌ |

**파일:** `services/api_gateway/routes/backtest.py`

---

## 2. 프론트엔드에서 사용 중인데 API 응답 형식 불일치 가능성

### 2.1 `/api/kr/signals/vcp` 응답 형식

**백엔드 응답 (`signals.py`):**
```python
class VCPSignalsResponse(BaseModel):
    signals: List[VCPSignalItem]
    count: int
    generated_at: Optional[str]
```

**프론트엔드 기대 (`api-client.ts`):**
```typescript
async getVCPSignals(): Promise<{
  signals: Signal[];
  count: number;
  generated_at?: string;
}>
```

**VCPSignalItem 필드 불일치:**
- 백엔드: `market`, `signal_date`, `current_price`, `contraction_ratio`, `foreign_5d`, `inst_5d`
- 프론트엔드: `name`, `signal_type`, `score`, `grade`, `entry_price`, `target_price`

### 2.2 종가베팅 V2 관련 미구현 API

프론트엔드 `api-client.ts`에 정의되어 있으나 백엔드에 없는 API:

```typescript
// 종가베팅 V2 가능한 날짜 목록 조회
async getJonggaV2Dates(): Promise<string[]>

// 종가베팅 V2 특정 날짜 시그널 조회
async getJonggaV2History(date: string): Promise<Signal[]>

// 종가베팅 V2 엔진 실행
async runJonggaV2Engine(): Promise<any>
```

---

## 3. 프론트엔드 추가 요청사항

### 3.1 새로운 API 엔드포인트 필요

| 엔드포인트 | 설명 | 우선순위 |
|-----------|------|----------|
| `POST /api/kr/jongga-v2/run` | 종가베팅 V2 엔진 트리거 | 🔴 높음 |
| `GET /api/kr/jongga-v2/dates` | 종가베팅 V2 가능한 날짜 목록 | 🟡 중간 |
| `GET /api/kr/jongga-v2/history/{date}` | 특정 날짜 종가베팅 시그널 | 🟡 중간 |
| `GET /api/dashboard/overview` | 대시보드 개요 (서비스 상태) | 🟢 낮음 |
| `GET /api/dashboard/connections` | 연결 정보 (WebSocket 상태) | 🟢 낮음 |

### 3.2 응답 데이터 형식 통일 요청

**VCP 시그널 응답에 필드 추가:**
```typescript
// 프론트엔드에서 필요한 필드
interface VCPSignalItem {
  ticker: string;
  name: string;           // ✅ 백엔드 있음 (stock에서 가져옴)
  market: string;         // ✅ 백엔드 있음
  signal_type: string;    // ✅ 백엔드 있음
  score: number;          // ✅ 백엔드 있음
  grade: string;          // ✅ 백엔드 있음
  entry_price?: number;   // ✅ 백엔드 있음
  target_price?: number;  // ✅ 백엔드 있음
  contraction_ratio?: number;  // ✅ 백엔드 있음
  foreign_5d?: number;    // ✅ 백엔드 있음
  inst_5d?: number;       // ✅ 백엔드 있음
  signal_date?: string;  // ✅ 백엔드 있음
  current_price?: number; // ❌ 백엔드에서 null 반환 - 실시간 가격 연동 필요
}
```

---

## 4. 프론트엔드 컴포넌트별 백엔드 API 매핑 현황

### 4.1 메인 페이지 (`app/page.tsx`)

| 기능 | 프론트엔드 사용 | 백엔드 API | 상태 |
|------|---------------|------------|------|
| 시그널 목록 | `apiClient.getSignals()` | `GET /api/kr/signals` | ✅ |
| Market Gate | `apiClient.getMarketGate()` | `GET /api/kr/market-gate` | ✅ |
| 실시간 가격 | `useMarketGate()` | WebSocket | ✅ |

### 4.2 시그널 페이지 (`app/signals/page.tsx`)

| 기능 | 프론트엔드 사용 | 백엔드 API | 상태 |
|------|---------------|------------|------|
| VCP 시그널 | `apiClient.getVCPSignals()` | `GET /api/kr/signals/vcp` | ✅ |
| 필터/정렬 | 클라이언트 사이드 | - | ✅ |

### 4.3 차트 페이지 (`app/chart/page.tsx`)

| 기능 | 프론트엔드 사용 | 백엔드 API | 상태 |
|------|---------------|------------|------|
| 차트 데이터 | `apiClient.getStockChart()` | `GET /api/kr/stocks/{ticker}/chart` | ✅ |
| 볼린저밴드 | 클라이언트 계산 | - | ✅ |

### 4.4 종목 상세 (`app/stock/[ticker]/page.tsx`)

| 기능 | 프론트엔드 사용 | 백엔드 API | 상태 |
|------|---------------|------------|------|
| 종목 상세 | `apiClient.getStockDetail()` | `GET /api/kr/stocks/{ticker}` | ✅ |
| 수급 데이터 | `apiClient.getStockFlow()` | `GET /api/kr/stocks/{ticker}/flow` | ✅ |
| 시그널 히스토리 | `apiClient.getStockSignals()` | `GET /api/kr/stocks/{ticker}/signals` | ✅ |
| AI 분석 | `apiClient.getAISummary()` | `GET /api/kr/ai-summary/{ticker}` | ✅ |

---

## 5. WebSocket 통신 상태

### 5.1 WebSocket 엔드포인트

| 항목 | 상태 |
|------|------|
| WebSocket 경로 | `/ws` |
| 프론트엔드 연결 | ✅ `lib/websocket.ts` |
| 백엔드 브로드캐스트 | ✅ `src/websocket/server.py` |

### 5.2 WebSocket 메시지 타입

| 메시지 타입 | 프론트엔드 | 백엔드 | 상태 |
|-------------|----------|--------|------|
| `connected` | ✅ | ✅ | ✅ |
| `price_update` | ✅ | ✅ | ✅ |
| `index_update` | ✅ | ✅ | ✅ |
| `market_gate_update` | ✅ | ✅ | ✅ |
| `signal_update` | ✅ | ✅ | ✅ |

---

## 6. 우선순위별 작업 요약

### 🔴 P0 - 즉시 필요

1. **종가베팅 V2 엔진 트리거 API**
   - `POST /api/kr/jongga-v2/run`
   - 프론트엔드 `ScanTriggerPanel` 컴포넌트에서 호출 필요

### 🟡 P1 - 곧 필요

2. **종가베팅 V2 날짜별 조회 API**
   - `GET /api/kr/jongga-v2/dates`
   - `GET /api/kr/jongga-v2/history/{date}`

3. **Performance API 프론트엔드 연동**
   - 누적 수익률 차트 컴포넌트 추가
   - 최고 성과 종목 표시

### 🟢 P2 - 추후 개선

4. **News API 프론트엔드 연동**
   - 뉴스 피드 컴포넌트 (`NewsFeed.tsx`)에 실제 API 연결
   - 현재는 컴포넌트만 존재

5. **System Health API 연동**
   - 대시보드에 시스템 헬스 표시
   - `SystemHealthIndicator` 컴포넌트 활용

---

## 7. 참고: 프론트엔드 API 클라이언트 구조

**파일:** `frontend/lib/api-client.ts`

```typescript
export const apiClient = {
  // 헬스 체크
  async healthCheck(retries = 3): Promise<HealthCheck>
  async waitForService(timeoutMs = 10000): Promise<boolean>

  // VCP 시그널
  async getSignals(limit = 20): Promise<Signal[]>
  async getVCPSignals(limit = 10, market?: string): Promise<{...}>

  // Market Gate
  async getMarketGate(): Promise<MarketGateStatus>

  // 종가베팅 V2
  async getJonggaV2Latest(): Promise<Signal[]>
  async getJonggaV2Dates(): Promise<string[]>          // ❓ 백엔드 미구현
  async getJonggaV2History(date: string): Promise<Signal[]>  // ❓ 백엔드 미구현
  async runJonggaV2Engine(): Promise<any>              // ❓ 백엔드 미구현

  // 실시간 가격
  async getRealtimePrices(tickers: string[]): Promise<Record<string, StockPrice>>

  // 종목 데이터
  async getStockDetail(ticker: string): Promise<IStockDetail>
  async getStockChart(ticker: string, period = "6mo"): Promise<IStockChart>
  async getStockFlow(ticker: string, days = 20): Promise<IFlowHistory>
  async getStockSignals(ticker: string, limit = 50): Promise<ISignalHistory>

  // AI 분석
  async getAISummary(ticker: string): Promise<IAIAnalysis>
  async getAIAnalysis(params?): Promise<IAIAnalysisList>
  async getAIHistoryDates(limit = 30): Promise<IAIHistoryDates>
  async getAIHistoryByDate(date: string): Promise<IAIAnalysisList>
  async triggerAIAnalysis(ticker: string): Promise<{...}>

  // 시스템
  async getDataStatus(): Promise<IDataStatus>
  async getSystemHealth(): Promise<ISystemHealth>

  // 스캔 트리거
  async triggerVCPScan(options?): Promise<IVCPScanResponse>
  async triggerSignalGeneration(tickers?): Promise<ISignalGenerationResponse>
  async getScanStatus(): Promise<IScanStatus>

  // 백테스트 KPI
  async getBacktestKPI(): Promise<IBacktestKPI>

  // 챗봇
  async chat(request: IChatRequest): Promise<IChatResponse>
  async getContext(query: string): Promise<IChatContext>
  async getRecommendations(strategy = "both", limit = 5): Promise<IRecommendationItem[]>
  // ...
}
```

---

## 8. 백엔드 개발자를 위한 요약

### 프론트엔드에서 이미 잘 작동하는 API

1. ✅ `GET /api/kr/signals` - 시그널 목록
2. ✅ `GET /api/kr/signals/vcp` - VCP 시그널 상위 N개
3. ✅ `GET /api/kr/market-gate` - Market Gate 상태
4. ✅ `GET /api/kr/jongga-v2/latest` - 최신 종가베팅 시그널
5. ✅ `GET /api/kr/stocks/{ticker}` - 종목 상세
6. ✅ `GET /api/kr/stocks/{ticker}/chart` - 차트 데이터
7. ✅ `GET /api/kr/stocks/{ticker}/flow` - 수급 데이터
8. ✅ `GET /api/kr/stocks/{ticker}/signals` - 시그널 히스토리
9. ✅ `GET /api/kr/realtime-prices` - 실시간 가격 (POST/GET 모두)
10. ✅ `POST /api/kr/realtime-prices` - 실시간 가격 일괄 조회
11. ✅ `GET /api/kr/backtest-kpi` - 백테스트 KPI

### 추가로 구현 필요한 API

1. ❌ `POST /api/kr/jongga-v2/run` - 종가베팅 V2 엔진 실행
2. ❌ `GET /api/kr/jongga-v2/dates` - 종가베팅 V2 가능한 날짜 목록
3. ❌ `GET /api/kr/jongga-v2/history/{date}` - 특정 날짜 종가베팅 시그널

---

## 9. 연락처

- **프론트엔드 담당자:** Claude Code (AI Assistant)
- **백엔드 코드 위치:** `services/api_gateway/`
- **프론트엔드 코드 위치:** `frontend/lib/api-client.ts`
