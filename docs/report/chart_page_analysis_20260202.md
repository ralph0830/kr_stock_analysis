# 차트 페이지 분석 보고서

**분석 일자:** 2026-02-02
**분석 대상:** https://stock.ralphpark.com/chart
**분석 범위:** 프론트엔드, 백엔드 API, 데이터베이스, UI/UX

---

## 1. 요약 (Executive Summary)

차트 페이지를 종합 분석한 결과, **핵심 문제는 데이터베이스에 차트 데이터가 존재하지 않는 것**으로 확인되었습니다. 프론트엔드와 백엔드는 정상적으로 동작하나, 데이터 수집 태스크가 실행되지 않아 차트가 표시되지 않는 상태입니다.

### 주요 발견사항
- **CRITICAL:** `daily_prices` 테이블에 OHLCV 데이터 없음
- **HIGH:** 프론트엔드/백엔드 API 파라미터 불일치 (`days` vs `period`)
- **MEDIUM:** 에러 처리 및 사용자 피드백 부족
- **LOW:** 중복 API 요청 발생

---

## 2. 문제 상세

### 2.1 [CRITICAL] 데이터베이스 데이터 부족

**증거:**
```bash
# API 응답
GET /api/kr/stocks/005930/chart?days=120
Response: {
  "ticker": "005930",
  "period": "6mo",
  "data": [],           # 빈 배열
  "total_points": 0     # 데이터 0건
}
```

**백엔드 코드 분석:**
- 파일: `services/api_gateway/main.py:1193-1253`
- 엔드포인트: `GET /api/kr/stocks/{ticker}/chart`
- 구현: `DailyPrice` 테이블에서 `ticker`와 `date >= cutoff_date` 조건으로 조회
- 쿼리 자체는 정상 구현됨

**원인 분석:**
1. Celery worker가 실행 중이 아님
2. 데이터 수집 태스크 (`collect_daily_prices`)가 실행되지 않음
3. KRX 수집기 연결 문제 가능성

### 2.2 [HIGH] API 파라미터 불일치

| 구분 | 파일/라인 | 파라미터 명 | 값 형식 |
|------|-----------|-------------|----------|
| 프론트엔드 | `lib/api-client.ts:260` | `days` | 숫자 (`30`, `120`) |
| 백엔드 | `main.py:1195` | `period` | 문자열 (`"1mo"`, `"3mo"`, `"6mo"`, `"1y"`) |

**문제 코드:**
```typescript
// frontend/lib/api-client.ts:256-261
async getStockChart(ticker: string, period: string = "6mo"): Promise<IStockChart> {
  const response = await api.get(
    `/api/kr/stocks/${ticker}/chart`,
    { params: { days: period === "6mo" ? 120 : period === "3mo" ? 60 : 30 } }
  );
```

- 프론트엔드는 `days=120`을 전송
- 백엔드는 `period` 파라미터를 기대하므로 `days`를 무시하고 기본값 `"6mo"` 사용
- 의도한 조회 기간과 실제 조회 기간이 상이할 수 있음

### 2.3 [MEDIUM] UI/UX 개선 필요

| 영역 | 현황 | 문제점 |
|------|------|--------|
| 미니 차트 | "데이터 없음" | 빈 상태에 대한 안내 부족 |
| 메인 차트 | "데이터가 없습니다" | 재시도 버튼, 원인 안내 없음 |
| 에러 처리 | console.error만 | 사용자에게 피드백 없음 |
| WebSocket | 정상 연동 | ✅ 양호 |

### 2.4 [LOW] 중복 API 요청

```javascript
// 브라우저 콘솔 확인
[API Request] GET /api/kr/stocks/005930/chart  // 2번 호출
[API Request] GET /api/kr/stocks/005930/chart
```

- `useEffect` 의존성 배열 문제로 인한 중복 호출
- React StrictMode 환경에서의 2회 호출 가능성

---

## 3. 코드 품질 분석

### 3.1 잘 구현된 부분 ✅

| 영역 | 설명 |
|------|------|
| **동적 도메인 지원** | 로컬/외부 도메인 자동 감지, NPM 리버스 프록시 환경 고려 |
| **WebSocket 연결** | 싱글톤 패턴, 자동 재연결, 상태 관리 |
| **차트 컴포넌트** | Recharts 활용, 반응형 디자인, 다크 모드 지원 |
| **타입 안전성** | TypeScript 인터페이스 정의 완료 |

### 3.3 개선 필요한 부분 ⚠️

| 파일 | 라인 | 문제 | 제안 |
|------|------|------|------|
| `chart/page.tsx` | 138-139 | `previousPrice`가 첫날 가격으로 계산됨 | 전날 가격과 비교하도록 수정 |
| `api-client.ts` | 260 | `days` 파라미터 사용 | 백엔드와 동일하게 `period` 사용 |
| `StockChart.tsx` | 341-363 | `PriceChange` 로직 명확하지 않음 | 주석 및 기준값 명확화 |

---

## 4. 개선 방안

### 4.1 Phase 1: 데이터 수집 (긴급)

```bash
# 1. Docker 컨테이너 상태 확인
docker ps | grep -E "(celery|postgres|api-gateway)"

# 2. DB 데이터 확인
docker exec -it ralph-stock-postgres-1 psql -U postgres -d ralph_stock -c "
SELECT ticker, COUNT(*), MAX(date) as latest_date
FROM daily_prices
GROUP BY ticker
ORDER BY ticker;
"

# 3. 데이터 수집 태스크 수동 실행
docker exec -it ralph-stock-api-gateway-1 python -c "
from src.tasks.collection_tasks import collect_daily_prices
collect_daily_prices.delay()
"

# 4. Celery beat가 스케줄링하는지 확인
# docker-compose.yml 또는 tasks/celery_app.py 확인
```

### 4.2 Phase 2: API 파라미터 통합

```typescript
// frontend/lib/api-client.ts 수정 제안

async getStockChart(ticker: string, period: string = "6mo"): Promise<IStockChart> {
  // period 파라미터 그대로 전달 (백엔드와 일치)
  const response = await api.get<IStockChart>(
    `/api/kr/stocks/${ticker}/chart`,
    { params: { period } }
  );

  return response.data;
}
```

```python
# 백엔드는 이미 period 파라미터를 지원함
# services/api_gateway/main.py:1195
async def get_stock_chart(
    ticker: str,
    period: str = Query(default="6mo", description="기간 (1mo, 3mo, 6mo, 1y)"),
    ...
```

### 4.3 Phase 3: 에러 처리 개선

```typescript
// frontend/app/chart/page.tsx 개선 제안

import { toast } from "@/hooks/use-toast";

// ...

} catch (error) {
  console.error("차트 데이터 로드 실패:", error);
  setChartData([]);

  // 사용자 피드백 추가
  toast({
    title: "차트 데이터 로드 실패",
    description: "서비스 점검 중이거나 데이터가 없습니다. 잠시 후 다시 시도해주세요.",
    variant: "destructive",
  });
}
```

### 4.4 Phase 4: 중복 요청 최적화

```typescript
// useEffect 의존성 배열 확인
useEffect(() => {
  const fetchChartData = async () => {
    // ...
  };
  fetchChartData();
}, [selectedTicker]);  // selectedTicker만 의존성으로 유지
```

---

## 5. 영향도 분석

| 컴포넌트 | 상태 | 영향 | 조치 우선순위 |
|----------|------|------|--------------|
| 미니 차트 (4종목) | ⛔ 비정상 | 데이터 없음 표시 | P0 |
| 메인 차트 | ⛔ 비정상 | 데이터 없음 표시 | P0 |
| WebSocket 연결 | ✅ 정상 | 영향 없음 | - |
| 실시간 가격 업데이트 | ❓ 미확인 | Kiwoom API 연동 필요 | P1 |

---

## 6. 우선순위 매트릭스

| 우선순위 | 항목 | 작업 내용 | 담당 | 예상 소요시간 |
|----------|------|----------|------|---------------|
| **P0** | 데이터 수집 | Celery worker 실행 및 데이터 수집 태스크 확인 | Backend | 1-2시간 |
| **P1** | API 통합 | 프론트엔드 `days` → `period` 파라미터 변경 | Frontend | 30분 |
| **P2** | 에러 처리 | 토스트 메시지 추가 및 사용자 피드백 개선 | Frontend | 1시간 |
| **P3** | 중복 요청 | useEffect 의존성 최적화 | Frontend | 30분 |

---

## 7. 첨부

### 7.1 관련 파일 목록

```
frontend/
├── app/chart/page.tsx              # 차트 페이지 메인 컴포넌트
├── lib/api-client.ts               # API 클라이언트 (파라미터 불일치)
├── hooks/useWebSocket.ts           # WebSocket 훅
└── components/StockChart.tsx       # 차트 컴포넌트

services/api_gateway/
├── main.py                         # 차트 API 엔드포인트
└── routes/stocks.py                # 종목 관련 라우트

src/
├── repositories/daily_price_repository.py  # DB 조회
└── tasks/collection_tasks.py       # 데이터 수집 태스크
```

### 7.2 API 스펙

```yaml
GET /api/kr/stocks/{ticker}/chart
Parameters:
  - ticker: string (종목 코드, 예: "005930")
  - period: string (기간, "1mo" | "3mo" | "6mo" | "1y")

Response:
  {
    "ticker": "005930",
    "period": "6mo",
    "data": [
      {
        "date": "2025-08-01",
        "open": 75000,
        "high": 76000,
        "low": 74500,
        "close": 75500,
        "volume": 15000000
      }
    ],
    "total_points": 120
  }
```

---

## 8. 결론

차트 페이지의 근본적인 문제는 **데이터베이스 데이터 부족**입니다. 프론트엔드와 백엔드 코드는 정상적으로 구현되어 있으므로, 데이터 수집 태스크를 실행하여 DB를 채우는 것이 최우선 과제입니다.

**추가 작업:**
1. Celery worker 상태 모니터링 강화
2. 데이터 수집 실패 시 알림 메커니즘 추가
3. API 파라미터 통합으로 혼동 방지

---

*보고서 작성: Claude Code*
*분석 도구: Playwright, Code Analysis, API Testing*
