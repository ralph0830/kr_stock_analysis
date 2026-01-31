# CLAUDE.md

Ralph Stock Analysis System - Quick Start Guide for Claude Code

---

## Project Overview

Microservices-based Korean stock analysis platform built with Python (FastAPI) and Next.js.

**Key Features:**
- VCP (Volatility Contraction Pattern) scanner
- 종가베팅 V2 signal engine with 12-point scoring
- Real-time market data via Kiwoom REST API
- SmartMoney flow analysis (foreign/institutional investors)
- AI chatbot with Gemini integration

---

## Port Configuration

| Port | Service | Description |
|------|---------|-------------|
| 5110 | Frontend | Next.js UI |
| 5111 | API Gateway | Main FastAPI Gateway |
| 5112 | VCP Scanner | Pattern detection |
| 5113 | Signal Engine | Signal generation |
| 5114 | Chatbot | AI chatbot service |
| 5433 | PostgreSQL | Database (dev) |
| 6380 | Redis | Cache/message broker (dev) |
| 5555 | Flower | Celery monitoring |

---

## Quick Start

### Docker Compose (권장) ⭐

```bash
# Profiles 기반 실행 (make dev 권장)
make dev     # 개발 환경 (hot reload)
make prod    # 운영 환경 (optimized)
make stop    # 서비스 중지
make logs    # 로그 확인

# 또는 직접 docker compose 사용
docker compose --profile dev up -d
docker compose --profile prod up -d
docker compose down
```

### 로컬 개발

```bash
# Install dependencies
uv sync

# Start infrastructure only
docker compose up -d postgres redis

# Start API Gateway
.venv/bin/python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111 --reload

# Start VCP Scanner
.venv/bin/python -m uvicorn services.vcp_scanner.main:app --host 0.0.0.0 --port 5112 --reload

# Start Signal Engine
.venv/bin/python -m uvicorn services.signal_engine.main:app --host 0.0.0.0 --port 5113 --reload

# Start Chatbot
.venv/bin/python -m uvicorn services.chatbot.main:app --host 0.0.0.0 --port 5114 --reload

# Start Frontend
cd frontend && npm run dev  # port 5110

# Start Celery
celery -A tasks.celery_app worker --loglevel=info
celery -A tasks.celery_app beat --loglevel=info
```

---

## Testing

```bash
# All tests
pytest tests/ -v

# Unit tests only (no infrastructure)
pytest tests/unit/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

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

# Kiwoom REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true

# Gemini (optional)
GEMINI_API_KEY=your_gemini_key
```

Frontend (`frontend/.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:5111
NEXT_PUBLIC_WS_URL=ws://localhost:5111
```

---

## Project Structure

```
ralph_stock_analysis/
├── lib/                   # 공유 라이브러리 (modularization)
│   └── ralph_stock_lib/   # DB, Repositories
├── services/              # FastAPI microservices (독립 배포 가능)
│   ├── api_gateway/       # Main gateway (5111)
│   │   ├── Dockerfile     # 멀티스테이지 빌드
│   │   ├── pyproject.toml # 서비스 의존성
│   │   └── tests/         # 서비스 테스트
│   ├── vcp_scanner/       # VCP scanner (5112)
│   ├── signal_engine/     # Signal generation (5113)
│   └── chatbot/           # AI chatbot (5114)
├── docker/
│   └── compose/           # Profiles 기반 Compose
│       ├── services/      # 서비스 정의 (모듈화)
│       ├── infra.yml      # 인프라 (postgres, redis)
│       ├── README.md      # Compose 가이드
│       └── tests/         # Compose 테스트 (42개)
├── docker-compose.yml     # 메인 Compose (profiles)
├── docker-compose.dev.yml  # 개발용 override
├── docker-compose.prod.yml # 운영용 override
├── Makefile               # 편의 명령어
├── src/                   # Core Python modules
├── frontend/              # Next.js 14 App Router
├── tasks/                 # Celery background tasks
├── tests/                 # pytest tests
└── .github/
    └── workflows/         # CI/CD 파이프라인
```

### 서비스 독립 배포

각 서비스는 독립적인 Docker 이미지로 빌드 가능합니다:

```bash
# 서비스별 Docker 빌드
docker build -f services/api_gateway/Dockerfile -t api-gateway:prod .
docker build -f services/vcp_scanner/Dockerfile -t vcp-scanner:prod .
docker build -f services/signal_engine/Dockerfile -t signal-engine:prod .
docker build -f services/chatbot/Dockerfile -t chatbot:prod .
```

---

## Documentation

| 문서 | 경로 | 설명 |
|------|------|------|
| **Docker Compose** | `docker/compose/README.md` | **Compose 사용 가이드** ⭐ |
| **Docker Compose Plan** | `docs/plans/PLAN_docker_compose_integration.md` | Compose 통합 계획 |
| **서비스 모듈화** | `docs/SERVICE_MODULARIZATION.md` | 모듈화 완료 보고서 |
| API 가이드 | `docs/api/API_GUIDE.md` | 전체 API 엔드포인트 |
| 차트 시스템 | `docs/api/CHART_SYSTEM.md` | 차트 시각화 시스템 가이드 |
| 마이그레이션 | `docs/migration/` | Open Architecture 7 Phase |
| 모듈화 계획 | `docs/plans/PLAN_service_modularization.md` | 7 Phase 상세 계획 |
| 프론트엔드 | `frontend/README.md` | Next.js 구조 및 개발 |
| 진행 상황 | `PROGRESS.md` | 전체 진행 상태 |
| TODO | `TODO.md` | 진행 중/예정 작업 |
| 아카이브 | `docs/archive_originals/` | 레거시 문서 (Flask) |

---

## Critical Notes

### Kiwoom REST API Integration
- Chart data returns in **reverse chronological order** → always sort by date asc
- Rate limiting: Add 0.5s delay between requests
- `get_daily_prices()`: Use `timedelta(days=days - 1 - i)` to include today

### Frontend Development
- Port 5110 conflicts: `sudo lsof -ti:5110 | xargs -r sudo kill -9`
- Build permission issues: `sudo chown -R ralph:ralph frontend/.next`
- ESLint errors blocking build: Set `eslint: { ignoreDuringBuilds: true }` in next.config.js

### Port Convention
- All services use `511x` port range
- Database: `5433` (PostgreSQL), `6380` (Redis)
- No other services should use these ports

### Sleep Command
- **Always use full path**: `/home/ralph/bin/sleep` (not `sleep`)
- System has custom coreutils in `/home/ralph/bin/`
- Using `sleep` without full path causes option parsing errors in Bash tool

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

## Status

**Migration:** 7/7 Phases Complete (100%)
**Modularization:** 7/7 Phases Complete (100%) ✅
**Docker Compose Integration:** 5/5 Phases Complete (100%) ✅
**Tests:** 622 passed, 20 skipped

**CI/CD:** GitHub Actions 구축 완료
- CI: PR 자동 테스트/Docker 빌드
- CD Staging: main 브랜치 자동 배포
- CD Production: 수동 승인 배포

**Docker Compose:**
- Profiles 기반 dev/prod 환경 분리
- 42개 테스트 모두 통과
- `make dev/prod`로 간단 시작 가능

---

*Last updated: 2026-01-31*
