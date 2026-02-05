# Ralph Stock Analysis - Open Architecture 문서

**버전:** 2.1.0
**최종 수정:** 2026-02-05

---

## 목차

1. [개요](#1-개요)
2. [아키텍처 원칙](#2-아키텍처-원칙)
3. [서비스 구조](#3-서비스-구조)
4. [API 엔드포인트](#4-api-엔드포인트)
5. [데이터베이스 스키마](#5-데이터베이스-스키마)
6. [통신 구조](#6-통신-구조)
7. [배포 가이드](#7-배포-가이드)
8. [확장 가이드](#8-확장-가이드)

---

## 1. 개요

### 1.1 Open Architecture란?

**Open Architecture**는 다음 특징을 가진 소프트웨어 아키텍처 스타일입니다:

| 특징 | 설명 |本项目 구현 |
|------|------|-----------|
| **모듈화** | 각 서비스가 독립적인 모듈 | ✅ Docker Compose로 분리 |
| **느슨한 결합** | 서비스 간 의존성 최소화 | ✅ API Gateway를 통한 간접 통신 |
| **독립 배포** | 각 서비스를 개별 배포 가능 | ✅ 개별 Docker 이미지 |
| **확장성** | 수평/수직 확장 용이 | ✅ Celery Worker, Redis Pub/Sub |
| **개방형 표준** | 표준 API, 프로토콜 사용 | ✅ RESTful API, WebSocket |

### 1.2 프로젝트 구조

```
ralph_stock_analysis/
├── frontend/              # Next.js App Router (Port: 5110)
│   ├── app/               # 페이지 라우트
│   ├── components/        # 공통 컴포넌트
│   ├── lib/               # 유틸리티
│   ├── store/             # Zustand 상태 관리
│   └── types/             # TypeScript 타입 정의
│
├── services/              # FastAPI 마이크로서비스
│   ├── api_gateway/       # API Gateway (Port: 5111) ⭐
│   ├── vcp_scanner/       # VCP Scanner (Port: 5112)
│   ├── signal_engine/     # Signal Engine (Port: 5113)
│   ├── chatbot/           # AI Chatbot (Port: 5114)
│   └── daytrading_scanner/ # Daytrading Scanner (Port: 5115) 🆕
│
├── src/                   # 공유 Python 모듈
│   ├── database/          # DB 세션, 모델
│   ├── repositories/      # Repository 패턴
│   ├── collectors/        # 데이터 수집기
│   ├── kiwoom/            # 키움 API 연동
│   └── websocket/         # WebSocket 서버
│
├── tasks/                 # Celery 백그라운드 태스크
├── tests/                 # pytest 테스트
└── docker/                # Docker 설정 파일
```

---

## 2. 아키텍처 원칙

### 2.1 마이크로서비스 분리

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                     │
│                      Port: 5110                            │
│  - 사용자 인터페이스                                         │
│  - React Server Components                                  │
│  - WebSocket 클라이언트                                      │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTPS/WSS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                   │
│                    Port: 5111  ⭐ Entry Point             │
│  - CORS 처리                                                 │
│  - 요청 라우팅                                               │
│  - WebSocket 엔드포인트 (/ws)                               │
│  - 인증/인가 (예정)                                          │
└───┬───────────┬───────────┬───────────┬────────────────────┤
    │           │           │           │
    ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│  VCP   │ │ Signal │ │ Chatbot│ │Daytrade│ │   Redis     │
│ Scanner│ │ Engine │ │        │ │Scanner │ │  (Cache)  │
│:5112   │ │:5113   │ │:5114   │ │:5115   │ │   :6380    │
└────────┘ └────────┘ └────────┘ └────────┘ └─────────────┘
     │
     ▼
┌────────┐
│   DB   │
│(PGSQL) │
│:5433   │
└────────┘
```

### 2.2 포트 할당 규칙

| 포트 | 서비스 | 설명 |
|------|--------|------|
| **5110** | Frontend | Next.js 개발/운영 서버 |
| **5111** | API Gateway | 메인 API 엔트리 포인트 ⭐ |
| **5112** | VCP Scanner | 볼린저밴드 수축 패턴 스캐너 |
| **5113** | Signal Engine | 종가베팅 V2 시그널 생성 |
| **5114** | Chatbot | AI 챗봇 서비스 |
| **5115** | Daytrading Scanner | 단타 매수 신호 스캐너 🆕 |
| **5433** | PostgreSQL | 데이터베이스 (TimescaleDB) |
| **6380** | Redis | 캐시/메시지 브로커 |
| **5555** | Flower | Celery 모니터링 |

> **규칙:** 모든 애플리케이션 서비스는 `511x` 포트 범위를 사용합니다. (DB/Redis 제외)

---

## 3. 서비스 구조

### 3.1 API Gateway (`services/api_gateway/`)

**책임:** 모든 외부 요청의 단일 진입점

```python
# services/api_gateway/main.py
app = FastAPI(title="Ralph Stock API Gateway")

# 라우터 등록
app.include_router(signals.router)    # /api/kr/signals
app.include_router(stocks.router)     # /api/kr/stocks
app.include_router(news.router)       # /api/kr/news
app.include_router(chatbot.router)    # /api/kr/chatbot
```

**주요 엔드포인트:**
- `GET /health` - 헬스 체크
- `GET /metrics` - Prometheus 메트릭
- `WS /ws` - WebSocket 연결

### 3.2 VCP Scanner (`services/vcp_scanner/`)

**책임:** 볼린저밴드 수축 패턴(VCP) 탐지

```python
# VCP 패턴 조건
1. 상승 추세 (50일 이동평균 > 200일 이동평균)
2. 변동성 수축 (볼린저밴드 폭 축소)
3. 거래량 감소 후 증가
```

### 3.3 Signal Engine (`services/signal_engine/`)

**책임:** 종가베팅 V2 시그널 생성 (12점 스코어링)

```python
# 점수 항목
{
    "news": 3,      # 뉴스 감성 분석
    "volume": 3,    # 거래대금 급증
    "chart": 2,     # 차트 패턴
    "candle": 1,    # 캔들 패턴
    "period": 1,    # 기간 조정
    "flow": 2       # 수급 흐름
}
# 총점: 0-12점 → 등급: S(11-12), A(9-10), B(7-8), C(6이하)
```

### 3.4 Daytrading Scanner (`services/daytrading_scanner/`) 🆕

**책임:** 단타 매수 신호 스캔 및 분석

```python
# 단타 매수 조건
1. 시가가 전날 고가 대비 3% 이상 하락 (과매도)
2. 거래량 급증 (이폭 매수 체산)
3. 15분 캔들이 강세 음봉 (녹음, 돌파, 역할)
4. RSI 과매도 (14 기준 35 이하)
5. MACD 골득차이 크게 발생
```

**주요 엔드포인트:**
- `GET /api/kr/daytrading/signals` - 활성 단타 시그널
- `GET /api/kr/daytrading/{ticker}` - 종목별 단타 분석
- `GET /api/kr/daytrading/stats` - 스캔 통계

```python
# 점수 항목
{
    "news": 3,      # 뉴스 감성 분석
    "volume": 3,    # 거래대금 급증
    "chart": 2,     # 차트 패턴
    "candle": 1,    # 캔들 패턴
    "period": 1,    # 기간 조정
    "flow": 2       # 수급 흐름
}
# 총점: 0-12점 → 등급: S(11-12), A(9-10), B(7-8), C(6이하)
```

### 3.5 Chatbot (`services/chatbot/`)

**책임:** AI 기반 주식 챗봇 (RAG + Gemini)

```
사용자 질문 → NLP 티커 추출 → Vector DB 검색 → LLM 답변 생성
```

---

## 4. API 엔드포인트

### 4.1 시그널 API

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| GET | `/api/kr/signals` | 전체 활성 시그널 | `Signal[]` |
| GET | `/api/kr/signals/vcp` | VCP 시그널 상위 N개 | `VCPSignalsResponse` |
| GET | `/api/kr/signals/top` | 최소 점수 이상 VCP | `VCPSignalsResponse` |
| GET | `/api/kr/jongga-v2/latest` | 최신 종가베팅 시그널 | `Signal[]` |
| POST | `/api/kr/jongga-v2/analyze` | 종가베팅 단일 분석 | `SignalResponse` |

### 4.2 종목 API

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| GET | `/api/kr/stocks/{ticker}` | 종목 상세 정보 | `StockDetailResponse` |
| GET | `/api/kr/stocks/{ticker}/chart` | 차트 데이터 (OHLCV) | `StockChartResponse` |
| GET | `/api/kr/stocks/{ticker}/flow` | 수급 데이터 | `StockFlowResponse` |
| GET | `/api/kr/stocks/{ticker}/signals` | 시그널 히스토리 | `SignalHistoryResponse` |
| GET/POST | `/api/kr/realtime-prices` | 실시간 가격 일괄 | `Record<string, StockPrice>` |

### 4.3 시장 API

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| GET | `/api/kr/market-gate` | Market Gate 상태 | `MarketGateStatus` |
| GET | `/api/kr/backtest-kpi` | 백테스트 KPI | `BacktestKPIResponse` |

### 4.4 뉴스 API

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| GET | `/api/kr/news/latest` | 최신 뉴스 목록 | `NewsListResponse` |
| GET | `/api/kr/news/{ticker}` | 종목별 뉴스 | `NewsListResponse` |

### 4.5 챗봇 API

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| POST | `/api/kr/chatbot/chat` | 챗봇 대화 | `IChatResponse` |
| POST | `/api/kr/chatbot/context` | 대화 컨텍스트 | `IChatContext` |
| GET | `/api/kr/chatbot/recommendations` | 종목 추천 | `IRecommendationItem[]` |
| GET | `/api/kr/chatbot/health` | 헬스 체크 | `{status, service}` |

### 4.6 Daytrading API 🆕

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| GET | `/api/kr/daytrading/signals` | 활성 단타 매수 신호 | `DaytradingSignal[]` |
| GET | `/api/kr/daytrading/{ticker}` | 종목별 단타 분석 | `DaytradingAnalysis` |
| GET | `/api/kr/daytrading/stats` | 스캔 통계 | `DaytradingStats` |
| GET | `/api/kr/daytrading/checks` | 체크리스트 점수 | `ChecksResponse` |

### 4.7 시스템 API

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| GET | `/health` | 헬스 체크 | `HealthCheckResponse` |
| GET | `/metrics` | Prometheus 메트릭 | `text/plain` |
| GET | `/api/metrics` | JSON 메트릭 | `MetricsResponse` |

---

## 5. 데이터베이스 스키마

### 5.1 ER 다이어그램

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   stocks    │     │   signals    │     │ daily_prices │
├─────────────┤     ├──────────────┤     ├──────────────┤
│ id          │     │ id           │     │ ticker (PK)  │
│ ticker (PK) │←───││ ticker (FK)  │←───││ date (PK)    │
│ name        │     │ signal_type  │     │ open_price   │
│ market      │     │ score        │     │ high_price   │
│ sector      │     │ grade        │     │ low_price    │
└─────────────┘     │ status       │     │ close_price  │
                    │ entry_price  │     │ volume       │
                    └──────────────┘     └──────────────┘
```

### 5.2 주요 테이블

| 테이블 | 설명 | TimescaleDB |
|--------|------|-------------|
| `stocks` | 종목 기본 정보 | ❌ |
| `signals` | VCP/종가베팅 시그널 | ❌ |
| `daily_prices` | 일봉 데이터 | ✅ (하이퍼테이블) |
| `institutional_flows` | 수급 데이터 | ✅ (하이퍼테이블) |
| `market_status` | 시장 상태 | ❌ |
| `backtest_results` | 백테스트 결과 | ❌ |
| `ai_analyses` | AI 분석 결과 | ❌ |

---

## 6. 통신 구조

### 6.1 REST API 통신

```
Frontend ──HTTPS──> API Gateway ──HTTP──> Microservices
   │                        │
   │                        └──> /api/kr/signals → VCP Scanner
   │                        └──> /api/kr/jongga-v2 → Signal Engine
   │                        └──> /api/kr/chatbot → Chatbot
   │                        └──> /api/kr/stocks → DB 직접 조회
```

### 6.2 WebSocket 통신

```
Frontend ──WSS──> API Gateway (/ws)
                    │
                    ├──> Price Broadcaster (실시간 가격)
                    ├──> Index Broadcaster (KOSPI/KOSDAQ)
                    └──> Signal Broadcaster (VCP 시그널)
```

**WebSocket 메시지 타입:**
```typescript
type IWSMessage =
  | IWSConnectedMessage      // 연결 확인
  | IWSSubscribedMessage      // 구독 확인
  | IWSPriceUpdateMessage     // 가격 업데이트
  | IWSIndexUpdateMessage     // 지수 업데이트
  | IWSMarketGateUpdateMessage // Market Gate 업데이트
  | IWSSignalUpdateMessage    // 시그널 업데이트
  | IWSPingMessage            // 핑/퐁
```

### 6.3 Celery 통신

```
API Gateway ──> Redis (Broker) ──> Celery Worker
                    │
                    └──> Result Backend
```

---

## 7. 배포 가이드

### 7.1 Docker Compose로 전체 시작

```bash
# 개발 환경 (hot reload)
make dev

# 또는
docker compose --profile dev up -d

# 운영 환경
docker compose --profile prod up -d
```

### 7.2 개별 서비스 실행

```bash
# Frontend
cd frontend && npm run dev  # Port: 5110

# API Gateway
uv run uvicorn services.api_gateway.main:app --port 5111 --reload

# VCP Scanner
uv run uvicorn services.vcp_scanner.main:app --port 5112 --reload

# Signal Engine
uv run uvicorn services.signal_engine.main:app --port 5113 --reload

# Chatbot
uv run uvicorn services.chatbot.main:app --port 5114 --reload
```

### 7.3 외부 도메인 배포

1. **Nginx Proxy Manager 설정**
   - 도메인: `stock.ralphpark.com`
   - Forward Hostname: `172.18.0.1` (또는 서버 IP)
   - Forward Port: `5111`
   - Custom Location `/ws` (WebSocket)

2. **CORS 설정**
   ```python
   # services/api_gateway/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://ralphpark.com",
           "https://stock.ralphpark.com",
           "http://localhost:5110",
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

## 8. 확장 가이드

### 8.1 새로운 마이크로서비스 추가

1. **서비스 폴더 생성**
   ```bash
   mkdir services/new_service
   cd services/new_service
   uv init --name new-service
   ```

2. **FastAPI 앱 생성**
   ```python
   # services/new_service/main.py
   from fastapi import FastAPI
   app = FastAPI(title="New Service")

   @app.get("/health")
   async def health():
       return {"status": "healthy"}
   ```

3. **Dockerfile 작성**
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY pyproject.toml uv.lock ./
   RUN uv sync --frozen
   COPY . .
   CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5115"]
   ```

4. **docker-compose.yml에 추가**
   ```yaml
   services:
     new-service:
       build:
         context: .
         dockerfile: services/new_service/Dockerfile
       ports:
         - "5115:5115"
   ```

### 8.2 새로운 API 엔드포인트 추가

1. **라우터 생성**
   ```python
   # services/api_gateway/routes/new_feature.py
   from fastapi import APIRouter
   router = APIRouter(prefix="/api/kr/new-feature", tags=["new_feature"])

   @router.get("/")
   async def get_items():
       return {"items": []}
   ```

2. **API Gateway에 등록**
   ```python
   # services/api_gateway/main.py
   _include_router("new_feature", "router", "New Feature")
   ```

3. **프론트엔드 API 클라이언트 추가**
   ```typescript
   // frontend/lib/api-client.ts
   async getNewFeature(): Promise<any> {
     const response = await api.get("/api/kr/new-feature");
     return response.data;
   }
   ```

---

## 관련 문서

- [API 가이드](../api/API_GUIDE.md)
- [Docker Compose 가이드](../docker/compose/README.md)
- [차트 시스템 가이드](../api/CHART_SYSTEM.md)
- [서비스 모듈화 문서](../SERVICE_MODULARIZATION.md)
- [Daytrading 시스템 문서](../api/DAYTRADING_SCANNER.md) 🆕
- [Nginx Proxy 설정](../NGINX_PROXY_SETUP.md)
- [WebSocket 설정](../WEBSOCKET.md)
