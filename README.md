# Ralph Stock Analysis System

한국 주식 분석 시스템 - VCP 패턴, 종가베팅 V2 시그널, 실시간 가격 업데이트

> **모듈화 완료**: 7/7 Phases | 상세: [docs/SERVICE_MODULARIZATION.md](docs/SERVICE_MODULARIZATION.md)

---

## 시스템 아키텍처 (모듈화 후)

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Client    │─────▶│   Frontend   │─────▶│  API Gateway    │
│  (Next.js)  │      │   (Next.js)   │      │   (FastAPI)     │
│   Port 5110 │      │               │      │    Port 5111    │
└─────────────┘      └──────────────┘      └────────┬────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
                    ▼                          ▼                      ▼
          ┌─────────────────┐        ┌─────────────────┐   ┌─────────────────┐
          │  VCP Scanner    │        │  Signal Engine  │   │   Chatbot       │
          │   (FastAPI)     │        │   (FastAPI)     │   │   (FastAPI)     │
          │    Port 5112    │        │    Port 5113    │   │    Port 5114    │
          └─────────────────┘        └─────────────────┘   └─────────────────┘
                    │                          │                      │
                    └──────────────────────────┼──────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
                    ▼                          ▼                      ▼
          ┌─────────────────┐        ┌─────────────────┐   ┌─────────────────┐
          │  PostgreSQL     │        │     Redis       │   │     Celery      │
          │  TimescaleDB    │        │   Cache/Broker  │   │   Background    │
          │    Port 5433    │        │    Port 6380    │   │   Workers       │
          └─────────────────┘        └─────────────────┘   └─────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │         lib/ralph_stock_lib (공유)          │
                    │  - database/ (models, session)            │
                    │  - repositories/ (stock, signal)           │
                    └─────────────────────────────────────────────┘
```

---

## 주요 기능

### 1. VCP 패턴 스캐너 (Port 5112)
- 볼린저밴드 수축 패턴 탐지
- SmartMoney 수급 분석 (외국인/기관)
- 5가지 요소로 종합 점수화
- **독립 Docker 이미지**: `vcp-scanner`

### 2. 종가베팅 V2 시그널 (Port 5113)
- 12점 만점 스코어링 시스템
- S/A/B/C 등급 산정
- 포지션 사이징 자동 계산
- **독립 Docker 이미지**: `signal-engine`

### 3. AI 챗봇 (Port 5114)
- Gemini 3.0 Flash 연동
- RAG 기반 질의응답
- 종목 추천 시스템
- **독립 Docker 이미지**: `chatbot`

### 4. API Gateway (Port 5111)
- 서비스 디스커버리 및 라우팅
- WebSocket 실시간 브로드캐스팅
- 통합 헬스체크
- **독립 Docker 이미지**: `api-gateway`

### 5. 데이터 수집
- KRXCollector: pykrx 래퍼
- Kiwoom REST API 연동
- Celery 백그라운드 태스크

---

## 빠른 시작

### 방법 1: Docker Compose (권장) ⭐

```bash
# 개발 환경 시작 (핫 리로드)
make dev

# 운영 환경 시작 (최적화)
make prod

# 로그 확인
make logs

# 서비스 중지
make stop

# 전체 정리
make clean
```

### 방법 2: 로컬 개발

```bash
# 1. 의존성 설치
uv sync

# 2. 인프라만 Docker로 실행
docker compose up -d postgres redis

# 3. 서비스들 개별 실행 (각 터미널에서)
.venv/bin/python -m uvicorn services.api_gateway.main:app --port 5111 --reload
.venv/bin/python -m uvicorn services.vcp_scanner.main:app --port 5112 --reload
.venv/bin/python -m uvicorn services.signal_engine.main:app --port 5113 --reload
.venv/bin/python -m uvicorn services.chatbot.main:app --port 5114 --reload

# 4. 프론트엔드
cd frontend && npm run dev  # port 5110
```

### 접속 URL

| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:5110 |
| API Docs | http://localhost:5111/docs |
| VCP Scanner | http://localhost:5112/docs |
| Signal Engine | http://localhost:5113/docs |
| Chatbot | http://localhost:5114/docs |
| Flower (Celery) | http://localhost:5555 |

---

## 프로젝트 구조

```
ralph_stock_analysis/
├── lib/                          # ⭐ 공유 라이브러리
│   └── ralph_stock_lib/
│       ├── database/             # DB 모델, 세션
│       └── repositories/         # Repository 패턴
├── services/                     # ⭐ 독립형 마이크로서비스
│   ├── api_gateway/              # API Gateway (5111)
│   │   ├── Dockerfile            # 멀티스테이지 빌드
│   │   ├── pyproject.toml        # 서비스 의존성
│   │   └── tests/                # 서비스 테스트
│   ├── vcp_scanner/              # VCP Scanner (5112)
│   ├── signal_engine/            # Signal Engine (5113)
│   └── chatbot/                  # Chatbot (5114)
├── docker/
│   └── compose/                  # ⭐ Profiles 기반 Compose
│       ├── services/             # 서비스 정의 (모듈화)
│       │   ├── api-gateway.yml
│       │   ├── vcp-scanner.yml
│       │   ├── signal-engine.yml
│       │   ├── chatbot.yml
│       │   ├── frontend.yml
│       │   └── celery.yml
│       ├── infra.yml            # 인프라 (postgres, redis)
│       ├── .env.example         # 환경 변수 예시
│       ├── .env.dev             # 개발용 기본값
│       ├── .env.prod.template   # 운영용 템플릿
│       └── README.md            # Compose 가이드
├── docker-compose.yml            # ⭐ 메인 Compose (profiles)
├── docker-compose.dev.yml        # 개발용 override
├── docker-compose.prod.yml       # 운영용 override
├── Makefile                      # ⭐ 편의 명령어
├── src/                          # 기존 소스 (호환성 유지)
├── frontend/                     # Next.js 14 App Router
├── tasks/                        # Celery 태스크
├── tests/                        # 통합/단위 테스트
└── .github/workflows/            # CI/CD 파이프라인
```

---

## 서비스 독립 배포

각 서비스는 독립적으로 빌드하고 배포할 수 있습니다:

```bash
# 서비스별 Docker 빌드
docker build -f services/api_gateway/Dockerfile -t api-gateway:prod .
docker build -f services/vcp_scanner/Dockerfile -t vcp-scanner:prod .
docker build -f services/signal_engine/Dockerfile -t signal-engine:prod .
docker build -f services/chatbot/Dockerfile -t chatbot:prod .

# 개발용 (development target)
docker build -f services/api_gateway/Dockerfile --target development -t api-gateway:dev .
```

---

## 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 단위 테스트만 (인프라 필요 없음)
pytest tests/unit/ -v

# 통합 테스트 (PostgreSQL + Redis 필요)
pytest tests/integration/ -v

# 커버리지 포함
pytest tests/ --cov=src --cov-report=html

# 서비스별 테스트
pytest services/api_gateway/tests/ -v
pytest services/vcp_scanner/tests/ -v
pytest services/signal_engine/tests/ -v
pytest services/chatbot/tests/ -v

# Docker Compose 검증
python docker/compose/test_config.py
```

---

## 환경 변수

`.env` 파일 생성:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ralph_stock

# Redis
REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Services
VCP_SCANNER_URL=http://localhost:5112
SIGNAL_ENGINE_URL=http://localhost:5113
CHATBOT_SERVICE_URL=http://localhost:5114

# Kiwoom REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true

# Gemini AI (선택사항)
GEMINI_API_KEY=your_gemini_key
```

Frontend (`frontend/.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:5111
NEXT_PUBLIC_WS_URL=ws://localhost:5111
```

---

## API 클라이언트 사용

### Python

```python
from src.clients.api_client import APIClient

async def main():
    client = APIClient(base_url="http://localhost:5111")

    # 헬스 체크
    health = await client.health_check()
    print(f"Status: {health['status']}")

    # 시그널 조회
    signals = await client.get_signals(limit=10)
    for signal in signals:
        print(f"{signal.ticker}: {signal.grade} ({signal.score})")

    # Market Gate
    market_gate = await client.get_market_gate()
    print(f"Market: {market_gate.status}")
```

### WebSocket

```python
from src.clients.websocket_client import WebSocketClient

async def on_price(update):
    print(f"Price update: {update.ticker} = {update.price}")

client = WebSocketClient("ws://localhost:5111/ws/price")
await client.connect()
await client.subscribe("005930")  # 삼성전자 구독
client.on_price_update(on_price)
await client.listen()
```

---

## CI/CD

- **CI**: PR 생성 시 자동 테스트/Docker 빌드
- **CD Staging**: main 브랜치 merge 시 자동 배포
- **CD Production**: 수동 승인 배포 (`YES` 입력 필요)

```bash
# Production 배포
# GitHub Actions → workflows → cd-production.yml → Run workflow
# Version: v1.0.0
# Confirm: YES
```

---

## 진행 상황

### ✅ 완료된 작업

1. **서비스 모듈화** (7/7 Phase) - 2026-01-31
   - lib/ 패키지 기반 구축
   - signal_engine, vcp_scanner, chatbot, api_gateway 독립화
   - docker-compose 환경별 분리
   - CI/CD 파이프라인 구축

2. **Open Architecture 마이그레이션** (7/7 Phase) - 2026-01-24

3. **P1~P7 기능 구현** - 2026-01-29
   - VCP 패턴 분석
   - 종가베팅 V2 시그널
   - LLM 뉴스 분석
   - 데이터 수집기
   - WebSocket 실시간 연동
   - 프론트엔드 Next.js 프로젝트

---

## 포트 구성

| 서비스 | 포트 | 프로토콜 |
|--------|------|----------|
| Frontend (Next.js) | 5110 | HTTP |
| API Gateway | 5111 | HTTP/WS |
| VCP Scanner | 5112 | HTTP |
| Signal Engine | 5113 | HTTP |
| Chatbot | 5114 | HTTP |
| PostgreSQL | 5433 | TCP |
| Redis | 6380 | TCP |
| Flower (Celery) | 5555 | HTTP |

---

## 메트릭 및 모니터링

- Prometheus 메트릭: `GET /metrics`
- 대시보드: `GET /api/dashboard/overview`
- Flower (Celery): http://localhost:5555

---

## 문서

| 문서 | 설명 |
|------|------|
| [docker/compose/README.md](docker/compose/README.md) | **Docker Compose 사용 가이드** ⭐ |
| [SERVICE_MODULARIZATION.md](docs/SERVICE_MODULARIZATION.md) | 모듈화 완료 보고서 |
| [PLAN_docker_compose_integration.md](docs/plans/PLAN_docker_compose_integration.md) | Docker Compose 통합 계획 |
| [PLAN_service_modularization.md](docs/plans/PLAN_service_modularization.md) | 모듈화 상세 계획 |
| [API_GUIDE.md](docs/api/API_GUIDE.md) | API 엔드포인트 가이드 |
| [CHART_SYSTEM.md](docs/api/CHART_SYSTEM.md) | 차트 시스템 문서 |
| [PROGRESS.md](PROGRESS.md) | 전체 진행 상태 |
| [CLAUDE.md](CLAUDE.md) | Claude Code 가이드 |

---

## 라이선스

MIT License

---

## 개발팀

Ralph Stock Analysis Team
