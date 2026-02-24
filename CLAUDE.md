# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

Microservices-based Korean stock analysis platform built with Python (FastAPI) and Next.js.

**Key Features:**
- VCP (Volatility Contraction Pattern) scanner
- 종가베팅 V2 signal engine with 12-point scoring
- **Daytrading Scanner** - 단타 매수 신호 7개 체크리스트 (거래량, 모멘텀, 박스권, 5일선, 기관, 낙폭, 섹터)
- Real-time market data via Kiwoom REST API
- SmartMoney flow analysis (foreign/institutional investors)
- AI chatbot with Gemini integration
- Custom Recommendation - 실시간 가격 연동 종목 추천

---

## Quick Start

### Docker Compose (권장) ⭐

> **📖 상세 가이드:** [docs/DOCKER_COMPOSE.md](docs/DOCKER_COMPOSE.md) - Profiles 기반 통합 설정

```bash
make dev     # 개발 환경 (hot reload)
make prod    # 운영 환경
make stop    # 서비스 중지
make logs    # 로그 확인
```

**Profiles:**
- `dev`: 개발용 (핫 리로드, 소스 마운트)
- `prod`: 운영용 (최적화, 리소스 제한)
- `test`: 테스트용 (테스트 DB + Mock 서비스)

### 로컬 개발

```bash
uv sync
docker compose up -d postgres redis

# API Gateway (Port: 5111)
uv run uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111 --reload

# VCP Scanner (Port: 5112)
uv run uvicorn services.vcp_scanner.main:app --port 5112 --reload

# Signal Engine (Port: 5113)
uv run uvicorn services.signal_engine.main:app --port 5113 --reload

# Chatbot (Port: 5114)
uv run uvicorn services.chatbot.main:app --port 5114 --reload

# Daytrading Scanner (Port: 5115)
uv run uvicorn services.daytrading_scanner.main:app --port 5115 --reload

# Frontend (Port: 5110)
cd frontend && npm run dev

# Celery
celery -A tasks.celery_app worker --loglevel=info
celery -A tasks.celery_app beat --loglevel=info
```

---

## Port Configuration

| Port | Service | Description |
|------|---------|-------------|
| 5110 | Frontend | Next.js UI |
| 5111 | API Gateway | Main FastAPI Gateway |
| 5112 | VCP Scanner | Pattern detection |
| 5113 | Signal Engine | Signal generation |
| 5114 | Chatbot | AI chatbot service |
| 5115 | Daytrading Scanner | Daytrading signal scanner |
| 5116 | Mock Kiwoom API | 키움 API Mock (테스트용) |
| 5117 | Mock WebSocket | WebSocket Mock (테스트용) |
| 5433 | PostgreSQL | Database (dev) |
| 5434 | PostgreSQL Test | Database (test) |
| 6380 | Redis | Cache/message broker (dev) |
| 6381 | Redis Test | Cache/message broker (test) |
| 5555 | Flower | Celery monitoring |

> **규칙:** 모든 서비스는 `511x` 포트 범위 사용
> **Mock 서비스:** 테스트 환경에서만 사용 (`make test-up`)

---

## Environment Variables

Create `.env` in project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ralph_stock

# Redis
REDIS_URL=redis://localhost:6380/0

# Celery
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Services
VCP_SCANNER_URL=http://localhost:5112
SIGNAL_ENGINE_URL=http://localhost:5113
CHATBOT_SERVICE_URL=http://localhost:5114
DAYTRADING_SCANNER_URL=http://localhost:5115

# Kiwoom REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true

# Gemini (optional)
GEMINI_API_KEY=your_gemini_key
```

Frontend (`frontend/.env.local`):
```bash
# 환경 변수를 비워두면 코드에서 동적으로 결정 (외부 도메인 지원)
# NEXT_PUBLIC_API_URL=http://localhost:5111
# NEXT_PUBLIC_WS_URL=ws://localhost:5111
```

### Database Initialization

데이터베이스 테이블 자동 생성 (최초 1회만 실행):

```bash
# 방법 1: 로컬 개발 환경
uv run python scripts/init_db.py

# 방법 2: Docker Compose (자동 실행)
docker compose --profile dev up -d
# db-init service가 자동으로 테이블 생성 후 완료됨

# 방법 3: Docker에서 수동 실행
docker compose run --rm db-init
```

**생성되는 테이블:**
- `stocks` - 종목 기본 정보 (관리종목, SPAC, 채권, 제외ETF 플래그 포함)
- `signals` - VCP/종가베팅 시그널
- `daily_prices` - 일봉 데이터 (TimescaleDB 하이퍼테이블)
- `institutional_flows` - 기관 수급 데이터 (TimescaleDB 하이퍼테이블)
- `market_status` - Market Gate 상태
- `ai_analyses` - AI 분석 결과
- `backtest_results` - 백테스트 결과
- `daytrading_signals` - 단타 매수 신호 (7개 체크리스트 점수)

### Nginx Proxy Manager (NPM) - Reverse Proxy 설정

**중요:** 프로덕션 환경에서는 NPM을 통해 Reverse Proxy를 구성합니다.

**환경 설정** (`.env.npm`):
```bash
NPM_URL=http://112.219.120.75:81
NPM_EMAIL=your-email@example.com
NPM_PASSWORD=your-password
```

**NPM 설정 관리 스크립트:**
- `scripts/setup_npm_proxy.py` - NPM 프록시 호스트 자동 설정
- `scripts/fix_npm_proxy.py` - forward_host 수정 스크립트

**stock.ralphpark.com 프록시 구성:**
| 경로 | 포워드 | 설명 |
|------|--------|------|
| `/` (메인) | `112.219.120.75:5110` | Frontend (Next.js) |
| `/api` | `112.219.120.75:5111` | API Gateway |
| `/ws` | `112.219.120.75:5111` | WebSocket |
| WebSocket Upgrade | ✅ 활성화 | `allow_websocket_upgrade: true` |

**NPM 관리 명령어:**
```bash
# NPM 설정 확인
uv run python scripts/setup_npm_proxy.py

# 수동 설정 (NPM 웹 UI: http://112.219.120.75:81)
# Proxy Hosts → stock.ralphpark.com → Advanced
# Custom Nginx Configuration 추가:
```

```nginx
# WebSocket Headers
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;

# Cache 비활성화 (실시간 데이터)
add_header Cache-Control "no-store, no-cache, must-revalidate";
add_header Pragma "no-cache";
```

---

## Documentation

| 문서 | 경로 | 설명 |
|------|------|------|
| **Docker Compose** | `docs/DOCKER_COMPOSE.md` | **Profiles 기반 통합 설정** ⭐ |
| Docker Compose 통합 | `docs/DOCKER_COMPOSE_UNIFICATION.md` | 통합 계획 및 완료 보고서 ✅ |
| **Mock 서비스** | `docs/TEST_MOCK_SERVICES.md` | **테스트용 Mock 서비스 구축** ⭐ |
| **Open Architecture** | `docs/OPEN_ARCHITECTURE.md` | **마이크로서비스 구조** ⭐ |
| **WebSocket 설정** | `docs/WEBSOCKET.md` | WebSocket 연결, CORS |
| **실시간 OHLC 수집** | `docs/OHLC_COLLECTOR.md` | Kiwoom OHLC 수집기 |
| **Nginx Proxy 설정** | `docs/NGINX_PROXY_SETUP.md` | 역프록시 설정 |
| **테스트 가이드** | `docs/TESTING.md` | pytest 테스트 |
| 서비스 모듈화 | `docs/SERVICE_MODULARIZATION.md` | 모듈화 보고서 |
| API 가이드 | `docs/api/API_GUIDE.md` | 전체 API 엔드포인트 |
| 차트 시스템 | `docs/api/CHART_SYSTEM.md` | 차트 시각화 |
| 프론트엔드 | `frontend/README.md` | Next.js 구조 |
| 진행 상황 | `PROGRESS.md` | 진행 상태 |
| TODO | `TODO.md` | 진행 중/예정 작업 |

---

## Testing

### Python (pytest)

```bash
# 전체 테스트
uv run pytest tests/ -v

# 빠른 단위 테스트만
uv run pytest -m fast -v

# 통합 테스트 제외
uv run pytest -m "not integration" -v

# 개별 파일
uv run pytest tests/unit/kiwoom/test_websocket.py -v

# 커버리지 포함
uv run pytest --cov=src --cov-report=term

# 병렬 실행
uv run pytest -n 4 -v
```

### Frontend (Vitest + Playwright)

```bash
cd frontend

# 단위 테스트
npm run test

# E2E 테스트
npm run test:e2e

# 커버리지
npm run test:coverage
```

---

## Critical Notes

### Kiwoom REST API
- Chart data returns in **reverse chronological order** → always sort by date asc
- Rate limiting: Add 0.5s delay between requests
- `get_daily_prices()`: Use `timedelta(days=days - 1 - i)` to include today

### Frontend Development
- Port 5110 conflicts: `sudo lsof -ti:5110 | xargs -r sudo kill -9`
- Build permission issues: `sudo chown -R ralph:ralph frontend/.next`
- ESLint errors: Set `eslint: { ignoreDuringBuilds: true }` in next.config.mjs

### Linting & Formatting

```bash
# Python (ruff)
make lint      # 코드 검사
make format    # 코드 포맷

# 직접 실행
uv run ruff check .
uv run ruff format .
```

### Sleep Command
- **Always use full path**: `/home/ralph/bin/sleep` (not `sleep`)
- System has custom coreutils in `/home/ralph/bin/`

---

## Claude Code Sub-agent 활용 가이드 ⭐

프로젝트 진행 시 복잡한 작업은 **반드시 서브에이전트를 활용**하여 효율성을 극대화하세요.

### 서브에이전트 사용 시나리오

| 작업 유형 | 추천 Agent | 명령어 예시 |
|----------|-----------|----------|
| 코드베이스 탐색 | `Explore` | `전체 VCP 스캐너 구조 분석` |
| 복잡한 구현 | `Plan` | `새로운 API 엔드포인트 설계` |
| 파이썬 개발 | `python-expert` | `FastAPI 서비스 구현` |
| 프론트엔드 개발 | `frontend-architect` | `Next.js 페이지 추가` |
| 테스트 작성 | `quality-engineer` | `통합 테스트 작성` |
| 성능 최적화 | `performance-engineer` | `쿼리 성능 분석` |
| 리팩토링 | `refactoring-expert` | `코드 정리 및 개선` |
| 백엔드 설계 | `backend-architect` | `DB 스키마 설계` |

### Task 툴 활용 패턴

```markdown
# 코드베이스 탐색 (새로운 기능 추가 전)
"프로젝트의 전체 인증 구조를 분석해줘"

# 구현 계획 수립
"종가베팅 V3 엔진을 위한 구현 계획을 세워줘"

# 병렬 작업 위임
"다음 작업들을 병렬로 실행해줘: 1) 테스트 작성, 2) API 문서화, 3) 리팩토링"
```

### 활용 원칙

- **3단계 이상 작업**: 반드시 서브에이전트 위임
- **다중 파일 변경**: `Task` 도구로 병렬 처리
- **탐색 작업**: `Explore` agent로 자동화
- **구현 작업**: 전문 agent 활용 (`python-expert`, `frontend-architect`)

---

## Repository Pattern

Always use Repository pattern for database access:

```python
from src.repositories.stock_repository import StockRepository
from src.database.session import get_db_session

async def get_stock(ticker: str):
    async with get_db_session() as db:
        repo = StockRepository(db)
        return await repo.get_by_ticker(ticker)
```

---

## Project Structure

```
ralph_stock_analysis/
├── services/              # FastAPI microservices (독립 배포)
│   ├── api_gateway/       # Main gateway (5111)
│   ├── vcp_scanner/       # VCP scanner (5112)
│   ├── signal_engine/     # Signal generation (5113)
│   ├── daytrading_scanner/ # Daytrading scanner (5115)
│   └── chatbot/           # AI chatbot (5114)
├── src/                   # Core Python modules (db, kiwoom, websocket, etc.)
├── frontend/              # Next.js 15 App Router
├── tasks/                 # Celery background tasks
├── tests/                 # pytest tests (unit, integration, e2e)
└── docker/                # Docker Compose 설정
```

---

## Status

| 항목 | 상태 |
|------|------|
| Migration | 7/7 Phases Complete (100%) ✅ |
| Modularization | 7/7 Phases Complete (100%) ✅ |
| Docker Compose | 통합 완료 (100%) ✅ |
| Tests | 842 passed, 20 skipped |

**2026-02-23:** 일봉 데이터 수집 서비스, Daytrading Scanner 서비스, Custom Recommendation 실시간 연동 구현

---

*Last updated: 2026-02-23*
