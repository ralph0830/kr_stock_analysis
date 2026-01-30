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

```bash
# Install dependencies
uv sync

# Start infrastructure
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
├── services/              # FastAPI microservices
│   ├── api_gateway/       # Main gateway (5111)
│   ├── vcp_scanner/       # VCP scanner (5112)
│   ├── signal_engine/     # Signal generation (5113)
│   └── chatbot/           # AI chatbot (5114)
├── src/                   # Core Python modules
│   ├── collectors/        # Data collectors (KRX, Kiwoom)
│   ├── analysis/          # Sentiment, SmartMoney
│   ├── repositories/      # Database repository pattern
│   ├── database/          # SQLAlchemy models
│   ├── kiwoom/            # Kiwoom REST API client
│   └── websocket/         # WebSocket server
├── frontend/              # Next.js 14 App Router
├── tasks/                 # Celery background tasks
└── tests/                 # pytest tests
```

---

## Documentation

| 문서 | 경로 | 설명 |
|------|------|------|
| API 가이드 | `docs/api/API_GUIDE.md` | 전체 API 엔드포인트 |
| 마이그레이션 | `docs/migration/` | Open Architecture 7 Phase |
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
**Tests:** 622 passed, 20 skipped

---

*Last updated: 2026-01-30*
