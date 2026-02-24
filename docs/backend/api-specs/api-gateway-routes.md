# API Gateway Routes Specification

**버전**: 2.0.0
**마지막 수정**: 2026-02-06
**유지보수자**: Backend Architect Team

---

## 개요

API Gateway는 한국 주식 분석 시스템의 중앙 진입점으로, 모든 클라이언트 요청을 적절한 마이크로서비스로 라우팅하고 응답을 집계합니다.

### Base URL
```
개발: http://localhost:5111
프로덕션: https://stock.ralphpark.com/api
```

### 포트 구성
| 서비스 | 포트 | 설명 |
|--------|------|------|
| Frontend | 5110 | Next.js UI |
| API Gateway | 5111 | Main Gateway |
| VCP Scanner | 5112 | Pattern Detection |
| Signal Engine | 5113 | Signal Generation |
| Chatbot | 5114 | AI Chatbot |
| Daytrading Scanner | 5115 | Daytrading Signals |

---

## API 엔드포인트 목록

### 1. Health Check & Metrics

#### 1.1 헬스 체크
```http
GET /health
GET /api/health
GET /
```

**설명**: API Gateway 서비스 상태 확인

**응답 모델**:
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "2.0.0",
  "timestamp": "2026-02-06T10:00:00"
}
```

#### 1.2 메트릭 조회
```http
GET /metrics
GET /api/metrics?metric_type=counter&limit=10
```

**설명**: Prometheus 형식 메트릭 또는 JSON 형식 메트릭

**Query Parameters**:
- `metric_type` (optional): counter, gauge, histogram
- `limit` (optional): 반환할 메트릭 수 (default: 10)

**응답 모델**:
```json
{
  "metrics": [
    {
      "name": "api_requests_total",
      "type": "counter",
      "value": 1250,
      "help": "Total API requests"
    }
  ],
  "total": 50,
  "filtered": 10
}
```

#### 1.3 메트릭 리셋 (개발용)
```http
POST /api/metrics/reset
```

---

### 2. Market Data (시장 데이터)

#### 2.1 VCP 시그널 조회
```http
GET /api/kr/signals?limit=20
```

**설명**: 활성 VCP 패턴 시그널 목록 조회

**Query Parameters**:
- `limit` (optional): 반환할 시그널 수 (1-100, default: 20)

**응답 모델**:
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "signal_type": "vcp",
    "score": 85,
    "grade": "A",
    "entry_price": 80000,
    "target_price": 92000,
    "created_at": "2026-02-06T09:30:00"
  }
]
```

#### 2.2 Market Gate 상태
```http
GET /api/kr/market-gate
```

**설명**: Market Gate 시장 상태 점수 조회

**응답 모델**:
```json
{
  "status": "YELLOW",
  "level": 50,
  "kospi_status": "소폭 상승",
  "kosdaq_status": "강세",
  "kospi_close": 2500.5,
  "kospi_change_pct": 0.8,
  "kosdaq_close": 850.3,
  "kosdaq_change_pct": 1.2,
  "sectors": [
    {
      "name": "반도체",
      "signal": "bullish",
      "change_pct": 2.5,
      "score": 75
    }
  ],
  "updated_at": "2026-02-06T15:30:00"
}
```

#### 2.3 종가베팅 V2 최신 시그널
```http
GET /api/kr/jongga-v2/latest
```

**설명**: 종가베팅 V2 최신 시그널 목록 조회

**응답 모델**:
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "signal_type": "jongga_v2",
    "score": {
      "total": 8,
      "news": 2,
      "volume": 2,
      "chart": 1,
      "candle": 1,
      "period": 1,
      "flow": 0
    },
    "grade": "A",
    "position_size": 1200,
    "entry_price": 80000,
    "target_price": 92000,
    "stop_loss": 76000,
    "reasons": ["긍정적 뉴스 다수", "거래대금 급증"],
    "created_at": "2026-02-06T10:48:55"
  }
]
```

#### 2.4 종가베팅 V2 단일 종목 분석
```http
POST /api/kr/jongga-v2/analyze
```

**요청 모델**:
```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "price": 80000
}
```

#### 2.5 백테스트 KPI
```http
GET /api/kr/backtest-kpi
```

**설명**: VCP 및 종가베팅 V2 전략 백테스트 요약

**응답 모델**:
```json
{
  "vcp": {
    "strategy": "vcp",
    "status": "OK",
    "count": 42,
    "win_rate": 65.5,
    "avg_return": 3.2,
    "profit_factor": 1.8
  },
  "closing_bet": {
    "strategy": "jongga_v2",
    "status": "Accumulating",
    "count": 1,
    "message": "최소 2일 데이터 필요"
  }
}
```

---

### 3. Stock Detail (종목 상세)

#### 3.1 종목 기본 정보
```http
GET /api/kr/stocks/{ticker}
```

**Path Parameters**:
- `ticker`: 종목 코드 (예: 005930)

**응답 모델**:
```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "market": "KOSPI",
  "sector": "전기전자",
  "current_price": 82400,
  "price_change": 400,
  "price_change_pct": 0.49,
  "volume": 15000000,
  "updated_at": "2026-02-06"
}
```

#### 3.2 종목 차트 데이터
```http
GET /api/kr/stocks/{ticker}/chart?period=6mo
```

**Query Parameters**:
- `period` (optional): 1mo, 3mo, 6mo, 1y (default: 6mo)

**응답 모델**:
```json
{
  "ticker": "005930",
  "period": "6mo",
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
  "total_points": 120
}
```

#### 3.3 종목 수급 데이터
```http
GET /api/kr/stocks/{ticker}/flow?days=20
```

**설명**: 외국인/기관 수급 데이터 및 SmartMoney 점수

**Query Parameters**:
- `days`: 조회 기간 (5-60, default: 20)

**응답 모델**:
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

#### 3.4 종목 시그널 히스토리
```http
GET /api/kr/stocks/{ticker}/signals?limit=50
```

**Query Parameters**:
- `limit`: 최대 조회 수 (1-100, default: 50)

**응답 모델**:
```json
{
  "ticker": "005930",
  "total_signals": 10,
  "open_signals": 2,
  "closed_signals": 8,
  "avg_return_pct": 5.2,
  "win_rate": 75.0,
  "signals": [
    {
      "id": 1,
      "ticker": "005930",
      "signal_type": "VCP",
      "signal_date": "2024-01-15",
      "status": "OPEN",
      "score": 85.0,
      "grade": "A",
      "entry_price": 75000,
      "exit_price": null,
      "entry_time": "2024-01-15T09:30:00",
      "exit_time": null,
      "return_pct": null
    }
  ]
}
```

---

### 4. Realtime Prices (실시간 가격)

#### 4.1 실시간 가격 일괄 조회 (POST)
```http
POST /api/kr/realtime-prices
```

**요청 모델**:
```json
{
  "tickers": ["005930", "000660", "035420"],
  "max_age_seconds": 60
}
```

**응답 모델**:
```json
{
  "prices": {
    "005930": {
      "ticker": "005930",
      "price": 82400,
      "change": 400,
      "change_rate": 0.49,
      "volume": 15000000,
      "timestamp": "2026-02-06T15:30:00"
    }
  }
}
```

#### 4.2 실시간 가격 일괄 조회 (GET)
```http
GET /api/kr/realtime-prices?tickers=005930,000660,035420
```

**Query Parameters**:
- `tickers` (required): 종목 코드 리스트 (콤마 구분)

---

### 5. Internal (내부 서비스 통신)

#### 5.1 실시간 가격 캐시 조회
```http
GET /internal/prices?tickers=005930,000660
```

**설명**: PriceUpdateBroadcaster가 수집한 실시간 가격 캐시 조회 (Daytrading Scanner 내부용)

#### 5.2 단일 종목 실시간 가격 조회
```http
GET /internal/price/{ticker}
```

---

## 모듈별 라우터 구성

### main.py (핵심 엔드포인트)
- `/health`, `/`, `/api/health` - Health Check
- `/metrics`, `/api/metrics`, `/api/metrics/reset` - Metrics
- `/api/kr/signals` - VCP Signals (VCP Scanner 프록시)
- `/api/kr/market-gate` - Market Gate Status
- `/api/kr/backtest-kpi` - Backtest KPI
- `/api/kr/jongga-v2/latest` - 종가베팅 V2 시그널
- `/api/kr/jongga-v2/analyze` - 종가베팅 V2 분석
- `/api/kr/stocks/{ticker}` - Stock Detail
- `/api/kr/stocks/{ticker}/chart` - Stock Chart
- `/api/kr/stocks/{ticker}/flow` - Stock Flow
- `/api/kr/stocks/{ticker}/signals` - Stock Signal History
- `/api/kr/realtime-prices` - Realtime Prices
- `/internal/prices`, `/internal/price/{ticker}` - Internal

### routes/ai.py
- `/api/kr/ai-analysis` - AI 분석 목록
- `/api/kr/ai-summary/{ticker}` - AI 종목 요약
- `/api/kr/ai-analyze/{ticker}` - AI 분석 트리거

### routes/backtest.py
- `/api/kr/backtest` - 백테스트 결과
- `/api/kr/backtest-summary` - 백테스트 요약

### routes/chatbot.py
- `/api/kr/chatbot/chat` - 챗봇 질의응답
- `/api/kr/chatbot/context` - 컨텍스트 검색
- `/api/kr/chatbot/recommendations` - 종목 추천
- `/api/kr/chatbot/session/{id}` - 세션 관리

### routes/daytrading.py
- `/api/kr/daytrading/scan` - 단타 스캔
- `/api/kr/daytrading/signals` - 단타 시그널
- `/api/kr/daytrading/status` - 스캔 상태

### routes/news.py
- `/api/kr/stocks/{ticker}/news` - 종목 뉴스

### routes/performance.py
- `/api/kr/performance` - 누적 수익률

### routes/system.py
- `/api/system/health` - 전체 시스템 헬스
- `/api/system/data-status` - 데이터 상태
- `/api/system/update-data-stream` - 데이터 업데이트

### routes/triggers.py
- `/api/kr/scan/vcp` - VCP 스캔 트리거
- `/api/kr/scan/signals` - 시그널 생성 트리거
- `/api/kr/scan/status` - 스캔 상태

---

## 상태 코드

| 코드 | 설명 | 사용 사례 |
|------|------|----------|
| 200 | 성공 | 정상 응답 |
| 400 | 잘못된 요청 | 파라미터 검증 실패 |
| 404 | 리소스 없음 | 종목을 찾을 수 없음 |
| 503 | 서비스 unavailable | 의존 서비스(VCP Scanner, Signal Engine) 다운 |
| 500 | 서버 에러 | 내부 처리 에러 |

---

## 에러 응답 형식

```json
{
  "status": "error",
  "code": 404,
  "detail": "Stock not found: 005930",
  "path": "/api/kr/stocks/005930"
}
```

---

## API 버전 관리

- **현재 버전**: v2.0.0
- **버전 정책**: URI에 버전 포함 (`/api/v2/...`)
- **하위 호환성**: 최소 1 major version 유지
- **Deprecation**: 최소 3개월 전 공지

---

## Rate Limiting

| 엔드포인트 그룹 | 제한 | 기간 |
|----------------|------|------|
| Health/Metrics | 제한 없음 | - |
| Market Data | 100 요청 | 1분 |
| Stock Detail | 60 요청 | 1분 |
| Realtime Prices | 30 요청 | 1분 |
| AI Analysis | 10 요청 | 1분 |

---

**다음 문서**: [Service Layer Specification](./service-layer-spec.md)
