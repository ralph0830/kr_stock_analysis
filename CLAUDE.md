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

## Quick Start

### Docker Compose (권장) ⭐

```bash
make dev     # 개발 환경 (hot reload)
make prod    # 운영 환경
make stop    # 서비스 중지
make logs    # 로그 확인
```

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
| 5433 | PostgreSQL | Database (dev) |
| 6380 | Redis | Cache/message broker (dev) |
| 5555 | Flower | Celery monitoring |

> **규칙:** 모든 서비스는 `511x` 포트 범위 사용

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
# 환경 변수를 비워두면 코드에서 동적으로 결정 (외부 도메인 지원)
# NEXT_PUBLIC_API_URL=http://localhost:5111
# NEXT_PUBLIC_WS_URL=ws://localhost:5111
```

---

## Documentation

| 문서 | 경로 | 설명 |
|------|------|------|
| **Open Architecture** | `docs/OPEN_ARCHITECTURE.md` | **마이크로서비스 구조** ⭐ |
| **WebSocket 설정** | `docs/WEBSOCKET.md` | WebSocket 연결, CORS |
| **실시간 OHLC 수집** | `docs/OHLC_COLLECTOR.md` | Kiwoom OHLC 수집기 |
| **Nginx Proxy 설정** | `docs/NGINX_PROXY_SETUP.md` | 역프록시 설정 |
| **테스트 가이드** | `docs/TESTING.md` | pytest 테스트 |
| Docker Compose | `docker/compose/README.md` | Compose 사용 가이드 |
| 서비스 모듈화 | `docs/SERVICE_MODULARIZATION.md` | 모듈화 보고서 |
| API 가이드 | `docs/api/API_GUIDE.md` | 전체 API 엔드포인트 |
| 차트 시스템 | `docs/api/CHART_SYSTEM.md` | 차트 시각화 |
| 프론트엔드 | `frontend/README.md` | Next.js 구조 |
| 진행 상황 | `PROGRESS.md` | 진행 상태 |
| TODO | `TODO.md` | 진행 중/예정 작업 |

---

## Critical Notes

### Kiwoom REST API
- Chart data returns in **reverse chronological order** → always sort by date asc
- Rate limiting: Add 0.5s delay between requests
- `get_daily_prices()`: Use `timedelta(days=days - 1 - i)` to include today

### Frontend Development
- Port 5110 conflicts: `sudo lsof -ti:5110 | xargs -r sudo kill -9`
- Build permission issues: `sudo chown -R ralph:ralph frontend/.next`
- ESLint errors: Set `eslint: { ignoreDuringBuilds: true }` in next.config.js

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
│   └── chatbot/           # AI chatbot (5114)
├── src/                   # Core Python modules
├── frontend/              # Next.js 14 App Router
├── tasks/                 # Celery background tasks
├── tests/                 # pytest tests
└── docker/                # Docker 설정
```

---

## Status

| 항목 | 상태 |
|------|------|
| Migration | 7/7 Phases Complete (100%) ✅ |
| Modularization | 7/7 Phases Complete (100%) ✅ |
| Docker Compose | 5/5 Phases Complete (100%) ✅ |
| Tests | 622 passed, 20 skipped |

**2026-02-03:** 문서 파편화 완료 (WebSocket, OHLC, Nginx, Testing)

---

*Last updated: 2026-02-04*
