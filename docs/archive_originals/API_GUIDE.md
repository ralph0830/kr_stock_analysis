# KR Stock API Gateway 가이드

한국 주식 분석 시스템 API Gateway의 공식 API 가이드 문서입니다.

## 목차

- [시작하기](#시작하기)
- [인증](#인증)
- [API 엔드포인트](#api-엔드포인트)
  - [헬스 체크](#헬스-체크)
  - [시스템 상태](#시스템-상태)
  - [시그널 조회](#시그널-조회)
  - [Market Gate](#market-gate)
  - [종목 상세](#종목-상세)
  - [종목 차트](#종목-차트)
  - [수급 데이터](#수급-데이터)
  - [실시간 가격](#실시간-가격)
  - [AI 분석](#ai-분석)
  - [백테스트](#백테스트)
  - [성과 분석](#성과-분석)
  - [스캔 트리거](#스캔-트리거)
  - [챗봇](#챗봇)
  - [WebSocket](#websocket)
- [에러 처리](#에러-처처)
- [Rate Limiting](#rate-limiting)

---

## 시작하기

### Base URL

```
http://localhost:5111
```

### 포트 구성

| 서비스 | 포트 | 설명 |
|--------|------|------|
| **API Gateway** | 5111 | 메인 API 엔드포인트 |
| **VCP Scanner** | 5112 | VCP 패턴 스캔 서비스 |
| **Signal Engine** | 5113 | 종가베팅 V2 시그널 생성 |
| **Market Analyzer** | 5114 | 마켓 분석 서비스 |
| **Frontend (Next.js)** | 5110 | React 기반 웹 UI |

### API 버전

- 현재 버전: `v2.0.0`

### Interactive Docs

- **Swagger UI**: `http://localhost:5111/docs`
- **ReDoc**: `http://localhost:5111/redoc`

---

## 인증

현재 개발 환경에서는 인증이 필요 없습니다.

프로덕션 환경에서는 API Key 기반 인증이 계획되어 있습니다.

---

## API 엔드포인트

### 헬스 체크

#### 서비스 헬스 체크

```http
GET /health
```

API Gateway 서비스가 정상 동작 중인지 확인합니다.

**Response:**
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "2.0.0",
  "timestamp": "2026-01-29T12:00:00"
}
```

#### 루트 엔드포인트

```http
GET /
```

API Gateway의 기본 정보와 문서 링크를 반환합니다.

**Response:**
```json
{
  "message": "KR Stock API Gateway",
  "version": "2.0.0",
  "docs": "/docs",
  "status": "operational"
}
```

---

## 시스템 상태

#### 시스템 헬스 체크

```http
GET /api/system/health
```

전체 시스템의 건강 상태를 조회합니다.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "up",
    "redis": "up",
    "celery": "up",
    "api_gateway": "up",
    "vcp_scanner": "up",
    "signal_engine": "up"
  },
  "timestamp": "2026-01-29T12:00:00",
  "uptime_seconds": 3600.5,
  "database_status": "up",
  "redis_status": "up",
  "celery_status": "up"
}
```

#### 데이터 상태 조회

```http
GET /api/system/data-status
```

데이터베이스에 저장된 주가, 시그널 데이터의 상태를 조회합니다.

**Response:**
```json
{
  "total_stocks": 2500,
  "updated_stocks": 2400,
  "last_update": "2026-01-29T09:30:00",
  "data_files": {
    "prices": "OK",
    "signals": "OK"
  },
  "details": [
    {
      "name": "prices",
      "status": "OK",
      "last_update": "2026-01-29T09:30:00",
      "record_count": 125000
    },
    {
      "name": "signals",
      "status": "OK",
      "last_update": "2026-01-29T09:30:00",
      "record_count": 500
    }
  ]
}
```

#### 데이터 업데이트 스트림

```http
POST /api/system/update-data-stream
```

Kiwoom REST API에서 전체 종목의 가격 데이터를 업데이트합니다.

**Response:**
```json
{
  "status": "completed",
  "updated_count": 2400,
  "started_at": "2026-01-29T12:00:00",
  "completed_at": "2026-01-29T12:05:00"
}
```

---

## 시그널 조회

#### 활성 VCP 시그널 목록

```http
GET /api/kr/signals?limit=20
```

VCP Scanner 서비스로 프록시하여 활성 시그널 목록을 반환합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | integer | No | 반환할 최대 시그널 수 (1-100, 기본 20) |

**Response:**
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "signal_type": "vcp",
    "score": 85.5,
    "grade": "A",
    "entry_price": null,
    "target_price": null,
    "created_at": "2026-01-29T09:00:00"
  }
]
```

#### 최신 종가베팅 V2 시그널

```http
GET /api/kr/jongga-v2/latest
```

Signal Engine 서비스로 프록시하여 최신 종가베팅 V2 시그널을 반환합니다.

**Response:**
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
    "created_at": "2026-01-29T10:48:55"
  }
]
```

#### 종가베팅 V2 단일 종목 분석

```http
POST /api/kr/jongga-v2/analyze
```

단일 종목의 종가베팅 V2 시그널을 생성합니다.

**Request Body:**
```json
{
  "ticker": "005930",
  "name": "삼전자",
  "price": 80000
}
```

**Response:**
```json
{
  "ticker": "005930",
  "name": "삼성전자",
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
  "reasons": ["긍정적 뉴스 다수", "거래대금 급증"]
}
```

---

## Market Gate

#### Market Gate 상태 조회

```http
GET /api/kr/market-gate
```

데이터베이스에서 가장 최신 Market Gate 상태를 반환합니다.

**상태 설명:**
- **GREEN**: 매수 우위 (전체 매수)
- **YELLOW**: 관망 (일부 매수)
- **RED**: 매도 (현금 보유 비중 증가)

**Response:**
```json
{
  "status": "YELLOW",
  "level": 50,
  "kospi_status": "소폭 상승",
  "kosdaq_status": "소폭 하락",
  "kospi_close": 2650.5,
  "kospi_change_pct": 0.5,
  "kosdaq_close": 850.25,
  "kosdaq_change_pct": -0.3,
  "sectors": [
    {
      "name": "반도체",
      "signal": "bullish",
      "change_pct": 2.5,
      "score": 75.0
    },
    {
      "name": "2차전지",
      "signal": "neutral",
      "change_pct": 0.0,
      "score": 50.0
    }
  ],
  "updated_at": "2026-01-29T09:30:00"
}
```

---

## 종목 상세

#### 종목 상세 조회

```http
GET /api/kr/stocks/{ticker}
```

종목 코드를 통해 기본 정보와 최신 가격을 조회합니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리, 예: 005930) |

**Response:**
```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "market": "KOSPI",
  "sector": "반도체",
  "current_price": 80000,
  "price_change": 500,
  "price_change_pct": 0.63,
  "volume": 15000000,
  "updated_at": "2026-01-29"
}
```

---

## 종목 차트

#### 종목 차트 데이터 조회

```http
GET /api/kr/stocks/{ticker}/chart?days=30
```

지정된 기간 동안의 종목 차트 데이터(OHLCV)를 조회합니다. Kiwoom REST API를 통해 데이터를 가져옵니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | integer | No | 조회 일수 (1-365, 기본 30) |

**Response:**
```json
{
  "ticker": "005930",
  "period": "30d",
  "data": [
    {
      "date": "2026-01-01",
      "open": 79000,
      "high": 80500,
      "low": 78500,
      "close": 80000,
      "volume": 15000000
    }
  ],
  "total_points": 30
}
```

---

## 수급 데이터

#### 종목 수급 데이터 조회

```http
GET /api/kr/stocks/{ticker}/flow?days=20
```

외국인/기관 순매수 데이터를 조회합니다. SmartMoney 점수(0-100)를 계산하여 제공합니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | integer | No | 조회 일수 (1-60, 기본 20) |

**SmartMoney 점수 산출:**
- 외국인 5일 순매수 비중: 40%
- 기관 5일 순매수 비중: 30%
- 외국인 연속 순매수 일수: 15%
- 이중 매수(외국인+기관 동시 순매수): 15%

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

#### 종목 시그널 히스토리 조회

```http
GET /api/kr/stocks/{ticker}/signals?limit=50
```

특정 종목의 과거 시그널 내역을 조회합니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리) |

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | integer | No | 최대 조회 수 (1-100, 기본 50) |

**Response:**
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

## 실시간 가격

#### 실시간 가격 조회

```http
POST /api/kr/realtime-prices
```

Kiwoom REST API를 통해 복수 종목의 실시간 가격을 조회합니다.

**Request Body:**
```json
{
  "tickers": ["005930", "000660", "035420"]
}
```

**Response:**
```json
{
  "prices": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "price": 160600,
      "change": 1800,
      "change_rate": 1.13,
      "volume": 15234567,
      "bid_price": 160500,
      "ask_price": 160700,
      "timestamp": "2026-01-29T12:00:00"
    }
  ],
  "timestamp": "2026-01-29T12:00:00"
}
```

> **참고**: 실시간 가격 업데이트는 WebSocket을 통해서도 받을 수 있습니다. `/ws` WebSocket 엔드포인트를 통해 Kiwoom WebSocket 0B TR 데이터를 실시간으로 수신할 수 있습니다.

---

## AI 분석

#### 종목 AI 요약 조회

```http
GET /api/kr/ai-summary/{ticker}
```

특정 종목의 최신 AI 분석 결과를 조회합니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리) |

**Response:**
```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "analysis_date": "2026-01-29",
  "sentiment": "positive",
  "score": 0.65,
  "summary": "삼성전자는 반도체 경기 회복 기대와 함께 긍정적 흐름입니다...",
  "keywords": ["반도체", "HBM", "AI"],
  "recommendation": "OVERWEIGHT"
}
```

#### 전체 AI 분석 조회

```http
GET /api/kr/ai-analysis?analysis_date=2026-01-29&limit=50
```

전체 종목 또는 특정 날짜의 AI 분석 목록을 조회합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| analysis_date | string | No | 분석 날짜 (YYYY-MM-DD) |
| limit | integer | No | 최대 반환 수 (1-100, 기본 50) |

**Response:**
```json
{
  "analyses": [
    {
      "id": 1,
      "ticker": "005930",
      "analysis_date": "2026-01-29",
      "sentiment": "positive",
      "score": 0.65,
      "summary": "삼성전자는 반도체 경기 회복 기대...",
      "keywords": ["반도체", "HBM", "AI"],
      "recommendation": "OVERWEIGHT"
    }
  ],
  "total": 100,
  "analysis_date": "2026-01-29"
}
```

#### AI 분석 트리거

```http
POST /api/kr/ai-analyze/{ticker}
```

특정 종목의 AI 분석을 수행합니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리) |

**Response:**
```json
{
  "status": "completed",
  "ticker": "005930",
  "sentiment": "positive",
  "score": 0.65,
  "recommendation": "OVERWEIGHT"
}
```

---

## 백테스트

#### 백테스트 요약 조회

```http
GET /api/kr/backtest/summary?config_name=vcp
```

전체 또는 특정 설정의 백테스트 결과 요약 통계를 반환합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| config_name | string | No | 설정명 필터 (예: vcp_conservative, jongga_v2) |

**Response:**
```json
{
  "total_backtests": 50,
  "avg_return_pct": 3.2,
  "avg_win_rate": 65.5,
  "best_return_pct": 15.8,
  "worst_return_pct": -5.2,
  "avg_sharpe_ratio": 1.8,
  "avg_max_drawdown_pct": -8.5
}
```

#### 최신 백테스트 목록 조회

```http
GET /api/kr/backtest/latest?config_name=vcp&limit=20
```

최신 백테스트 결과 목록을 반환합니다 (생성일 내림차순).

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| config_name | string | No | 설정명 필터 |
| limit | integer | No | 최대 반환 수 (1-100, 기본 20) |

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "config_name": "vcp_conservative",
      "backtest_date": "2026-01-29",
      "total_return_pct": 5.2,
      "win_rate": 70.0,
      "sharpe_ratio": 2.1,
      "max_drawdown_pct": -6.5
    }
  ],
  "total": 20
}
```

---

## 성과 분석

#### 누적 수익률 조회

```http
GET /api/kr/performance/cumulative?signal_type=VCP&start_date=2026-01-01&end_date=2026-01-29
```

시그널 기반 누적 수익률을 날짜별로 조회합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| signal_type | string | No | 시그널 타입 (VCP, JONGGA_V2) |
| start_date | string | No | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | No | 종료 날짜 (YYYY-MM-DD) |

---

## 스캔 트리거

#### VCP 스캔 트리거

```http
POST /api/kr/scan/vcp?market=KOSPI&min_score=70&min_grade=A
```

VCP (Volatility Contraction Pattern) 스캔을 실행합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| market | string | No | 시장 (KOSPI, KOSDAQ, ALL) |
| min_score | float | No | 최소 점수 (0-100) |
| min_grade | string | No | 최소 등급 (S, A, B, C) |
| top_n | integer | No | 상위 N개 종목만 스캔 (기본 30) |

**Response:**
```json
{
  "status": "completed",
  "scanned_count": 2500,
  "found_signals": 15,
  "started_at": "2026-01-29T10:00:00",
  "completed_at": "2026-01-29T10:02:30",
  "signals": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "score": 85.5,
      "grade": "A",
      "vcp_score": 82.0,
      "smartmoney_score": 75.5
    }
  ]
}
```

#### 복수 종목 스캔

```http
POST /api/kr/scan/multiple
```

여러 종목의 VCP 스캔을 병렬로 실행합니다.

**Request Body:**
```json
{
  "tickers": ["005930", "000660", "035420"],
  "min_score": 70.0
}
```

**Response:**
```json
{
  "status": "completed",
  "scanned_count": 3,
  "found_signals": 2,
  "signals": [...]
}
```

#### 종가베팅 V2 시그널 생성 트리거

```http
POST /api/kr/scan/signals?tickers=005930,000660
```

종가베팅 V2 시그널 생성을 실행합니다. 12점 스코어링 시스템으로 종목을 평가하고 시그널을 생성합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| tickers | string | No | 특정 종목만 생성 (쉼표 구분) |

**Response:**
```json
{
  "status": "completed",
  "generated_count": 25,
  "started_at": "2026-01-29T10:05:00",
  "completed_at": "2026-01-29T10:06:30"
}
```

#### 스캔 상태 조회

```http
GET /api/kr/scan/status
```

현재 진행 중인 VCP 스캔 및 시그널 생성의 상태를 조회합니다.

**Response:**
```json
{
  "vcp_scan_status": "idle",
  "signal_generation_status": "idle",
  "last_vcp_scan": "2026-01-29T10:00:00",
  "last_signal_generation": "2026-01-29T10:05:00",
  "current_operation": null,
  "progress_percentage": 100.0
}
```

---

## 챗봇

#### 챗봇 대화

```http
POST /api/kr/chatbot/chat
```

사용자 메시지를 처리하여 AI 응답을 생성합니다. RAG 기반으로 종목/시그널/뉴스 정보를 활용합니다.

**Request Body:**
```json
{
  "message": "삼성전자 현재가 알려줘",
  "session_id": "user-123"
}
```

**Response:**
```json
{
  "reply": "삼성전자(005930)의 현재가는 80,000원입니다...",
  "suggestions": [
    "삼성전자 최근 뉴스는?",
    "삼성전자 수급 상태는?"
  ],
  "session_id": "user-123",
  "timestamp": "2026-01-29T10:10:00"
}
```

---

## WebSocket

실시간 가격 데이터를 WebSocket을 통해 수신할 수 있습니다.

### 연결

```javascript
const ws = new WebSocket('ws://localhost:5111/ws');

ws.onopen = () => {
  console.log('WebSocket connected');

  // 종목 구독
  ws.send(JSON.stringify({
    type: 'subscribe',
    topic: 'price:005930'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'price_update') {
    console.log(`${data.ticker}: ${data.data.price}원 (${data.data.change_rate}%)`);
  }
};
```

### 메시지 형식

#### 가격 업데이트

```json
{
  "type": "price_update",
  "ticker": "005930",
  "data": {
    "price": 160600,
    "change": 1800,
    "change_rate": 1.13,
    "volume": 15234567,
    "bid_price": 160500,
    "ask_price": 160700
  },
  "timestamp": "2026-01-29T12:00:00",
  "source": "kiwoom_ws"
}
```

### WebSocket 엔드포인트

#### WebSocket 연결 통계

```http
GET /ws/stats
```

WebSocket 연결 통계를 조회합니다.

**Response:**
```json
{
  "active_connections": 3,
  "subscriptions": {
    "price:005930": 1,
    "price:000660": 0
  },
  "broadcaster_running": false,
  "active_tickers": ["005930", "000660", "035420", "005380"]
}
```

#### 종목 구독

```http
POST /ws/subscribe/{ticker}
```

종목을 실시간 가격 브로드캐스트에 추가합니다.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | Yes | 종목 코드 (6자리) |

**Response:**
```json
{
  "status": "subscribed",
  "ticker": "005930",
  "active_tickers": ["005930", "000660", "035420", "005380"]
}
```

#### 종목 구독 해제

```http
DELETE /ws/subscribe/{ticker}
```

종목 실시간 가격 브로드캐스트에서 제거합니다.

#### 활성 종목 목록 조회

```http
GET /ws/tickers
```

현재 활성화된 종목 목록을 조회합니다.

**Response:**
```json
{
  "active_tickers": ["005930", "000660", "035420", "005380"],
  "default_tickers": ["005930", "000660", "035420", "005380"]
}
```

---

## 에러 처리

### 표준 에러 응답

모든 에러는 다음 형식을 따릅니다:

```json
{
  "status": "error",
  "code": 404,
  "detail": "Stock 005930 not found",
  "path": "/api/kr/stocks/005930"
}
```

### HTTP 상태 코드

| Code | Description |
|------|-------------|
| 200 | 성공 |
| 400 | 잘못된 요청 |
| 404 | 리소스를 찾을 수 없음 |
| 409 | 이미 진행 중인 작업 있음 |
| 422 | 검증 실패 |
| 500 | 서버 내부 오류 |
| 503 | 서비스 unavailable |

---

## Rate Limiting

현재 개발 환경에서는 Rate Limiting이 적용되지 않습니다.

프로덕션 환경에서는 다음 제한이 계획되어 있습니다:

| 엔드포인트 | 제한 |
|-----------|------|
| 시그널 조회 | 100 req/min |
| 스캔 트리거 | 10 req/min |
| AI 분석 | 20 req/min |
| 기타 | 200 req/min |

---

## 추가 참고

- **Swagger UI**: `http://localhost:5111/docs`
- **ReDoc**: `http://localhost:5111/redoc`
- **Prometheus Metrics**: `http://localhost:5111/metrics`

## 서비스 포트

| 서비스 | 포트 | 설명 |
|--------|------|-------------|
| **API Gateway** | 5111 | 메인 API 엔드포인트 |
| **VCP Scanner** | 5112 | VCP 패턴 스캔 서비스 |
| **Signal Engine** | 5113 | 종가베팅 V2 시그널 생성 |
| **Market Analyzer** | 5114 | 마켓 분석 서비스 |
| **PostgreSQL** | 5433 | 데이터베이스 |
| **Redis** | 6380 | 캐시/메시지 브로커 |
| **Celery Worker** | - | 백그라운드 작업 |
| **Flower** | 5555 | Celery 모니터링 |

## WebSocket 실시간 데이터

Kiwoom WebSocket 0B TR(주식체결)을 통해 실시간 가격 데이터를 수신합니다.

### 데이터 필드 (0B TR)

| 필드 | 설명 |
|------|------|
| `10` | 현재가 |
| `11` | 전일대비 |
| `12` | 등락율 (%) |
| `13` | 누적거래량 |
| `15` | 거래량 |
| `20` | 체결시간 (HHMMSS) |
| `27` | 매도호가 |
| `28` | 매수호가 |

### 기본 구독 종목

실시간 가격 데이터를 제공하는 기본 종목:
- 005930 (삼성전자)
- 000660 (SK하이닉스)
- 035420 (NAVER)
- 005380 (현대차)

추가 종목 구독은 `POST /ws/subscribe/{ticker}` 엔드포인트를 사용하세요.
