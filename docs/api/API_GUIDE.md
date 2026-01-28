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
  - [AI 분석](#ai-분석)
  - [백테스트](#백테스트)
  - [성과 분석](#성과-분석)
  - [스캔 트리거](#스캔-트리거)
  - [챗봇](#챗봇)
- [에러 처리](#에러-처처)
- [Rate Limiting](#rate-limiting)

---

## 시작하기

### Base URL

```
http://localhost:5111
```

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
  "timestamp": "2026-01-28T10:00:00"
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
  "timestamp": "2026-01-28T10:00:00",
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
  "last_update": "2026-01-28T09:30:00",
  "data_files": {
    "prices": "OK",
    "signals": "OK"
  },
  "details": [
    {
      "name": "prices",
      "status": "OK",
      "last_update": "2026-01-28T09:30:00",
      "record_count": 125000
    },
    {
      "name": "signals",
      "status": "OK",
      "last_update": "2026-01-28T09:30:00",
      "record_count": 500
    }
  ]
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
    "created_at": "2026-01-28T09:00:00"
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
    "created_at": "2026-01-28T10:48:55"
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
  "name": "삼성전자",
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
  "updated_at": "2026-01-28T09:30:00"
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
  "updated_at": "2026-01-28"
}
```

#### 종목 차트 데이터 조회

```http
GET /api/kr/stocks/{ticker}/chart?days=30
```

지정된 기간 동안의 종목 차트 데이터(OHLCV)를 조회합니다.

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
  "analysis_date": "2026-01-28",
  "sentiment": "positive",
  "score": 0.65,
  "summary": "삼성전자는 반도체 경기 회복 기대와 함께 긍정적 흐름입니다...",
  "keywords": ["반도체", "HBM", "AI"],
  "recommendation": "OVERWEIGHT"
}
```

#### 전체 AI 분석 조회

```http
GET /api/kr/ai-analysis?analysis_date=2026-01-28&limit=50
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
      "analysis_date": "2026-01-28",
      "sentiment": "positive",
      "score": 0.65,
      "summary": "삼성전자는 반도체 경기 회복 기대...",
      "keywords": ["반도체", "HBM", "AI"],
      "recommendation": "OVERWEIGHT"
    }
  ],
  "total": 100,
  "analysis_date": "2026-01-28"
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
      "backtest_date": "2026-01-28",
      "total_return_pct": 5.2,
      "win_rate": 70.0,
      "sharpe_ratio": 2.1,
      "max_drawdown_pct": -6.5
    }
  ],
  "total": 20
}
```

#### 백테스트 히스토리 조회

```http
GET /api/kr/backtest/history?start_date=2026-01-01&end_date=2026-01-28&config_name=vcp&limit=50
```

날짜 범위 및 설정명으로 필터링한 백테스트 히스토리를 반환합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| start_date | string | No | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | No | 종료 날짜 (YYYY-MM-DD) |
| config_name | string | No | 설정명 필터 |
| limit | integer | No | 최대 반환 수 (1-100, 기본 50) |

**Response:**
```json
{
  "results": [...],
  "total": 30
}
```

#### 최고 수익률 백테스트 조회

```http
GET /api/kr/backtest/best?config_name=vcp
```

전체 또는 특정 설정 중 최고 수익률을 기록한 백테스트 결과를 반환합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| config_name | string | No | 설정명 필터 |

**Response:**
```json
{
  "id": 15,
  "config_name": "vcp_conservative",
  "backtest_date": "2026-01-15",
  "total_return_pct": 15.8,
  "win_rate": 80.0,
  "sharpe_ratio": 2.5,
  "max_drawdown_pct": -4.2
}
```

---

## 성과 분석

#### 누적 수익률 조회

```http
GET /api/kr/performance/cumulative?signal_type=VCP&start_date=2026-01-01&end_date=2026-01-28
```

시그널 기반 누적 수익률을 날짜별로 조회합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| signal_type | string | No | 시그널 타입 (VCP, JONGGA_V2) |
| start_date | string | No | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | No | 종료 날짜 (YYYY-MM-DD) |

**Response:**
```json
{
  "data": [
    {
      "date": "2026-01-01",
      "daily_return_pct": 0.5,
      "cumulative_return_pct": 0.5
    },
    {
      "date": "2026-01-02",
      "daily_return_pct": 1.2,
      "cumulative_return_pct": 1.7
    }
  ],
  "total_points": 20,
  "final_return_pct": 5.2
}
```

#### 시그널별 성과 조회

```http
GET /api/kr/performance/by-signal?ticker=005930&signal_type=VCP&days=30
```

특정 종목 또는 전체 시그널의 성과 지표를 조회합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| ticker | string | No | 종목 코드 |
| signal_type | string | No | 시그널 타입 (VCP, JONGGA_V2) |
| days | integer | No | 조회 기간 (일, 기본 30) |

**Response:**
```json
{
  "total_signals": 10,
  "closed_signals": 8,
  "win_rate": 75.0,
  "avg_return": 5.2,
  "best_return": 15.8,
  "worst_return": -3.2
}
```

#### 기간별 성과 조회

```http
GET /api/kr/performance/by-period?period=3mo&signal_type=VCP
```

특정 기간 동안의 성과 지표를 조회합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| period | string | No | 기간 (1w, 2w, 1mo, 3mo, 6mo, 1y) |
| signal_type | string | No | 시그널 타입 (VCP, JONGGA_V2) |

**Response:**
```json
{
  "period": "3mo",
  "total_signals": 45,
  "win_rate": 68.5,
  "avg_return": 4.8,
  "cumulative_return": 12.5,
  "mdd": -8.2,
  "best_return": 18.5,
  "worst_return": -5.1,
  "sharpe_ratio": 1.9
}
```

#### 최고 성과 종목 조회

```http
GET /api/kr/performance/top-performers?signal_type=VCP&limit=10&days=30
```

수익률 기준 최고 성과 종목 목록을 조회합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| signal_type | string | No | 시그널 타입 (VCP, JONGGA_V2) |
| limit | integer | No | 최대 반환 수 (1-50, 기본 10) |
| days | integer | No | 조회 기간 (일, 기본 30) |

**Response:**
```json
{
  "performers": [
    {
      "ticker": "005930",
      "signal_type": "VCP",
      "entry_price": 75000,
      "exit_price": 86500,
      "return_pct": 15.3,
      "signal_date": "2026-01-15"
    }
  ],
  "total_count": 10
}
```

#### 샤프 비율 조회

```http
GET /api/kr/performance/sharpe-ratio?signal_type=VCP&days=30&risk_free_rate=2.0
```

시그널 전략의 샤프 비율을 계산합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| signal_type | string | No | 시그널 타입 (VCP, JONGGA_V2) |
| days | integer | No | 조회 기간 (일, 기본 30) |
| risk_free_rate | float | No | 무위험 이자율 (연율 %, 기본 2.0) |

**Response:**
```json
{
  "sharpe_ratio": 1.8542,
  "period_days": 30,
  "risk_free_rate": 2.0
}
```

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
| market | string | No | 시장 (KOSPI, KOSDAQ) |
| min_score | float | No | 최소 점수 |
| min_grade | string | No | 최소 등급 (S, A, B, C) |

**Response:**
```json
{
  "status": "completed",
  "scanned_count": 2500,
  "found_signals": 15,
  "started_at": "2026-01-28T10:00:00",
  "completed_at": "2026-01-28T10:02:30",
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
  "started_at": "2026-01-28T10:05:00",
  "completed_at": "2026-01-28T10:06:30"
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
  "last_vcp_scan": "2026-01-28T10:00:00",
  "last_signal_generation": "2026-01-28T10:05:00",
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
  "timestamp": "2026-01-28T10:10:00"
}
```

#### 대화 컨텍스트 조회

```http
POST /api/kr/chatbot/context
```

사용자 질문에서 추출한 종목, 시그널, 뉴스 등의 컨텍스트를 반환합니다.

**Request Body:**
```json
{
  "query": "삼성전자랑 NAVER 최신 시그널 알려줘"
}
```

**Response:**
```json
{
  "stocks": [
    {"ticker": "005930", "name": "삼성전자"},
    {"ticker": "035420", "name": "NAVER"}
  ],
  "signals": [...],
  "news": [...],
  "market_status": {...}
}
```

#### 챗봇 서비스 헬스 체크

```http
GET /api/kr/chatbot/health
```

챗봇 서비스의 가용성을 확인합니다.

**Response:**
```json
{
  "status": "healthy",
  "service": "chatbot"
}
```

#### 종목 추천 조회

```http
GET /api/kr/chatbot/recommendations?strategy=both&limit=5
```

VCP/종가베팅 시그널 기반 종목 추천을 반환합니다.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| strategy | string | No | 전략 (vcp, jongga, both) |
| limit | integer | No | 최대 추천 수 |

**Response:**
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "grade": "A",
    "score": 85,
    "position_size_pct": 12
  }
]
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
