# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KR Stock Analysis System is a microservices-based Korean stock analysis platform built with Python. The system has completed a 7-phase Open Architecture migration, transitioning from a monolithic Flask application to a distributed microservices architecture with event-driven communication.

**Key Features:**
- VCP (Volatility Contraction Pattern) scanner for stock pattern detection
- 종가베팅 V2 (Closing Bet V2) signal engine with 12-point scoring system
- Real-time market data collection and analysis
- SmartMoney flow analysis (foreign/institutional investors)
- Event-driven architecture with Redis Pub/Sub
- Asynchronous task processing with Celery
- Kiwoom REST API integration for real-time stock trading

## Architecture

### Microservices Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Client    │─────▶│ API Gateway  │─────▶│  VCP Scanner    │
└─────────────┘      │  (FastAPI)   │      │  (FastAPI)      │
                     └──────────────┘      └─────────────────┘
                            │                       │
                            │                       ▼
                            │              ┌─────────────────┐
                            │              │  Signal Engine  │
                            │              │  (FastAPI)      │
                            │              └─────────────────┘
                            │
                            ▼
                     ┌──────────────┐      ┌─────────────────┐
                     │ Event Bus    │─────▶│  Celery Worker  │
                     │ (Redis)      │      │  (Tasks)        │
                     └──────────────┘      └─────────────────┘
```

### Port Configuration

| Service | Port | Description |
|----------|------|-------------|
| **Frontend (Next.js)** | 5110 | React-based UI |
| **API Gateway** | 5111 | Main API Gateway |
| **VCP Scanner** | 5112 | Pattern detection service |
| **Signal Engine** | 5113 | Scoring & signal generation |
| **Market Analyzer** | 5114 | Market analysis service |
| **PostgreSQL** | 5433 | Database (external: 5432) |
| **Redis** | 6380 | Cache/Message broker (external: 6379) |
| **Flower** | 5555 | Celery monitoring |

### Core Services

1. **API Gateway** (`services/api_gateway/`)
   - FastAPI-based gateway on port 5111
   - Service discovery and routing proxy
   - CORS middleware and error handling
   - Kiwoom REST API integration
   - Routes: `/api/kr/signals`, `/api/kr/market-gate`, `/api/kr/jongga-v2/latest`, `/api/kr/kiwoom/*`

2. **VCP Scanner Service** (`services/vcp_scanner/`)
   - FastAPI service on port 5112
   - VCP pattern detection algorithm
   - SmartMoney scoring (foreign 40%, institutional 30%)
   - Endpoints: `/signals`, `/scan`, `/analyze/{ticker}`

3. **Signal Engine Service** (`services/signal_engine/`)
   - FastAPI service on port 5113
   - 12-point scoring system (news, volume, chart, candle, period, flow)
   - Grade calculation (S/A/B/C) with position sizing
   - Endpoints: `/signals/latest`, `/generate`, `/analyze`

4. **Kiwoom REST API** (`src/kiwoom/`)
   - REST API client for Kiwoom securities
   - WebSocket real-time data streaming
   - Mock bridge for testing
   - Endpoints: `/api/kr/kiwoom/health`, `/api/kr/kiwoom/subscribe`, `/api/kr/kiwoom/prices`

5. **Event Bus** (`services/event_bus/`)
   - Redis Pub/Sub for async messaging
   - Event types: `SignalEvent`, `MarketUpdateEvent`
   - Channels: `signals:created`, `market:gate`, `prices:update`

6. **Cache Layer** (`services/cache/`)
   - Redis-based caching with TTL support
   - `@cached` decorator for function results
   - Batch operations: `get_many`, `set_many`, `clear_pattern`

7. **Celery Tasks** (`tasks/`)
   - Background job processing with Redis broker
   - Scheduled tasks: VCP scan (15min), signals (30min), market gate (1hr)
   - Task modules: `scan_tasks.py`, `signal_tasks.py`, `market_tasks.py`

8. **Data Collectors** (`src/collectors/`)
   - `BaseCollector` - Abstract base class defining collector interface
   - `KRXCollector` - pykrx wrapper for Korean stock data
     - `fetch_stock_list()` - Stock master data from KOSPI/KOSDAQ
     - `fetch_daily_prices()` - OHLCV daily price data
     - `fetch_supply_demand()` - Foreign/institutional flow data
     - Includes fallback to mock data when pykrx unavailable

9. **Analysis Modules** (`src/analysis/`)
   - `SentimentAnalyzer` - Gemini API-based news sentiment analysis
     - `Sentiment` enum (POSITIVE/NEGATIVE/NEUTRAL)
     - `SentimentResult` with confidence, keywords, summary, score (-1.0~1.0)
     - Fallback to keyword-based mock analysis without API key
   - `NewsScorer` - 종가베팅 V2 news scoring (0-3 points)
     - `calculate_daily_score()` - Daily news score calculation
     - `calculate_weekly_score()` - Weekly aggregation

## Common Commands

### CLI Entry Point (NEW)

```bash
# Run interactive CLI (Rich-based UI)
.venv/bin/python run.py

# CLI 메뉴:
# 1. 수급 스크리닌 (VCP 스캔)
# 2. 종가베팅 V2 시그널 생성
# 3. 시그널 조회 (Rich Table)
# 4. Market Gate 상태 (섹터별 현황)
# 5. AI 분석
# 6. 시스템 헬스 체크
# 7. 백테스트 KPI
```

### Development Setup

```bash
# Install dependencies (uv recommended)
uv sync

# Start infrastructure (PostgreSQL + Redis)
docker compose up -d postgres redis

# Start services (individual terminals) - USE VENV PYTHON
.venv/bin/python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111 --reload
.venv/bin/python -m uvicorn services.vcp_scanner.main:app --host 0.0.0.0 --port 5112 --reload
.venv/bin/python -m uvicorn services.signal_engine.main:app --host 0.0.0.0 --port 5113 --reload

# Start Frontend (Next.js)
cd frontend && npm run dev  # Runs on port 5110

# Start Celery worker and beat
celery -A tasks.celery_app worker --loglevel=info
celery -A tasks.celery_app beat --loglevel=info
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only (no infrastructure required)
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run migration tests
pytest tests/migration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/services/test_service_discovery.py -v

# Run single test with verbose output
pytest tests/unit/services/test_service_discovery.py::test_get_service_url -v
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy src/

# SQL style checking
sqlfluff lint
```

### Database Operations

```bash
# Run CSV to DB migration
python scripts/migrate_csv_to_db.py

# Connect to PostgreSQL
docker exec -it kr_stock_db psql -U postgres -d kr_stock

# Check TimescaleDB extension
docker exec -it kr_stock_db psql -U postgres -d kr_stock -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Backup database
docker exec kr_stock_db pg_dump -U postgres kr_stock > backup.sql

# Restore database
docker exec -i kr_stock_db psql -U postgres kr_stock < backup.sql
```

### Infrastructure

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f [service_name]

# Restart specific service
docker compose restart [service_name]

# Flower monitoring (Celery)
# Access at http://localhost:5555

# Test data collector (KRX)
python scripts/test_krx_collector.py

# Test news sentiment analysis
python scripts/test_news_sentiment.py
```

## Repository Pattern

The project uses SQLAlchemy 2.0 with Repository pattern for data access:

**BaseRepository** (`src/repositories/base.py`)
- Generic CRUD operations: `create`, `get_by_id`, `get_all`, `update`, `delete`
- Filter support: `count`, `exists`
- All repositories inherit from this base class

**Concrete Repositories:**
- `StockRepository` (`src/repositories/stock_repository.py`)
  - `get_by_ticker()` - Find stock by ticker symbol
  - `list_all()` - List all stocks with market/sector filters
  - `search()` - Search by name or ticker
  - `create_if_not_exists()` - Upsert operation

- `SignalRepository` (`src/repositories/signal_repository.py`)
  - `get_active()` - Get open signals
  - `get_by_ticker_and_date()` - Historical signal lookup
  - `update_status()` - Close signal with exit reason

**Database Models** (`src/database/models.py`)
- `Stock` - Basic stock information
- `DailyPrice` - OHLCV data (TimescaleDB hypertable)
- `Signal` - VCP/종가베팅 signals with entry/exit tracking
- `InstitutionalFlow` - Foreign/institutional money flow data
- `MarketStatus` - Market Gate status (GREEN/YELLOW/RED)

## Scoring Systems

### VCP Score (0-100)
- Bollinger Band contraction (30%)
- Volume decrease (20%)
- Volatility decrease (20%)
- RSI neutral (15%)
- MACD alignment (15%)

### SmartMoney Score (0-100)
- Foreign net buying (40%)
- Institutional net buying (30%)
- Pension fund buying (15%)
- Foreign ownership ratio (15%)

### 종가베팅 V2 (12 Points)
- News score (0-3): LLM sentiment analysis
- Volume score (0-3): Trading amount thresholds
- Chart score (0-2): VCP + 52-week high proximity
- Candle score (0-1): Bullish candle breakout
- Period score (0-1): Pullback duration
- Flow score (0-2): Foreign/institutional net buying

**Grading:**
- S grade (10+ points): 15% position size
- A grade (8+ points): 12% position size
- B grade (6+ points): 10% position size
- C grade (<6 points): Not recommended

## Testing Strategy

The project follows TDD with pytest:

**Unit Tests** (`tests/unit/`)
- Repository tests with mock sessions
- Service tests with mocked external APIs
- Event bus tests with Redis mocks
- Cache tests with mock Redis client
- Celery task tests (no broker required)

**Integration Tests** (`tests/integration/`)
- API endpoint tests (httpx TestClient)
- Service communication tests
- Database integration tests (require PostgreSQL)
- Event handler tests

**Migration Tests** (`tests/migration/`)
- CSV to DB data migration accuracy
- Foreign key integrity validation
- Data type conversion verification

**Test Fixtures** (`tests/conftest.py`)
- `event_loop` - Asyncio event loop for async tests
- `mock_session` - Mock DB session for unit tests
- `database_setup` - Session-wide DB initialization

## Key Technologies

- **FastAPI** - Async web framework for all microservices
- **SQLAlchemy 2.0** - ORM with async support
- **PostgreSQL + TimescaleDB** - Time-series optimized database
- **Redis** - Cache layer and message broker
- **Celery** - Distributed task queue
- **Pydantic** - Data validation and settings
- **pytest-asyncio** - Async test support

## Environment Variables

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/kr_stock

# Redis
REDIS_URL=redis://localhost:6380/0

# Celery
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Service URLs (for API Gateway)
VCP_SCANNER_URL=http://localhost:5112
SIGNAL_ENGINE_URL=http://localhost:5113
MARKET_ANALYZER_URL=http://localhost:5114

# Kiwoom REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true
USE_MOCK=true
```

### Frontend Environment Variables

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:5111
NEXT_PUBLIC_WS_URL=ws://localhost:5111
```

## Frontend Architecture

### Project Structure (Next.js 14 App Router)

```
frontend/
├── app/                    # App Router pages
│   ├── page.tsx            # Home page
│   ├── dashboard/          # Dashboard with system health & scan controls
│   ├── chart/               # Chart visualization
│   ├── signals/             # Signals list page
│   └── stock/[ticker]/      # Stock detail page
├── components/             # React components
│   ├── ui/                  # shadcn/ui base components
│   ├── layout/              # Layout components (header, footer, sidebar)
│   ├── RealtimePriceCard.tsx    # WebSocket real-time prices
│   ├── SystemHealthIndicator.tsx # System status monitoring (NEW)
│   ├── ScanTriggerPanel.tsx      # Scan trigger buttons (NEW)
│   ├── AIAnalysisSummary.tsx     # AI sentiment analysis (NEW)
│   └── StockDetail.tsx            # Stock detail page
├── store/                  # Zustand state management
│   ├── index.ts             # Main store (signals, marketGate, prices)
│   ├── stockStore.ts        # Stock detail state (including AI analysis)
│   └── systemStore.ts       # System health state with polling (NEW)
├── lib/                    # Utility functions
│   ├── api-client.ts        # API client with P1 endpoints
│   └── utils.ts             # Format utilities (formatPrice, etc.)
└── types/index.ts          # TypeScript type definitions
```

### Frontend Components

#### SystemHealthIndicator (`components/SystemHealthIndicator.tsx`)
- **Purpose**: Display system health status in real-time
- **Features**:
  - Overall system status (healthy/degraded/unhealthy)
  - Service status grid (database, redis, celery, api_gateway)
  - Data file status (prices, signals)
  - Uptime display
  - Auto-refresh every 30 seconds
- **API Endpoints Used**:
  - `GET /api/system/health` - System health check
  - `GET /api/system/data-status` - Data file status

#### ScanTriggerPanel (`components/ScanTriggerPanel.tsx`)
- **Purpose**: Trigger VCP scans and signal generation
- **Features**:
  - VCP scan buttons (전체/KOSPI/KOSDAQ)
  - Signal generation button
  - Real-time scan status polling (5s interval)
  - Last execution timestamps
- **API Endpoints Used**:
  - `GET /api/kr/scan/status` - Scan status polling
  - `POST /api/kr/scan/vcp` - Trigger VCP scan
  - `POST /api/kr/scan/signals` - Trigger signal generation

#### AIAnalysisSummary (`components/AIAnalysisSummary.tsx`)
- **Purpose**: Display AI sentiment analysis for stocks
- **Features**:
  - Sentiment indicator (positive/negative/neutral)
  - Sentiment score bar (-1.0 ~ 1.0)
  - Recommendation badge (BUY/SELL/HOLD/OVERWEIGHT/UNDERWEIGHT)
  - Summary text
  - Keywords tags
- **API Endpoints Used**:
  - `GET /api/kr/ai-summary/{ticker}` - AI analysis summary
  - `POST /api/kr/ai-analyze/{ticker}` - Trigger AI analysis

### Frontend API Client

**Location**: `frontend/lib/api-client.ts`

**P1 API Methods**:
```typescript
// AI Analysis
apiClient.getAISummary(ticker: string)
apiClient.getAIAnalysis(params?)
apiClient.getAIHistoryDates(limit?)
apiClient.getAIHistoryByDate(date)
apiClient.triggerAIAnalysis(ticker)

// System Management
apiClient.getDataStatus()
apiClient.getSystemHealth()

// Scan Triggers
apiClient.triggerVCPScan(options?)
apiClient.triggerSignalGeneration(tickers?)
apiClient.getScanStatus()
```

### Frontend Development Commands

```bash
# Install frontend dependencies
cd frontend && npm install

# Start development server (port 5110)
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type checking
npx tsc --noEmit
```

### Frontend P1 Integration (2026-01-27)

#### Completed Features
1. **System Health Monitoring**
   - Real-time system status display
   - 30-second auto-refresh polling
   - Service status grid (database, redis, celery, api_gateway)
   - Data file status tracking

2. **Scan Trigger Controls**
   - VCP scan trigger (all/KOSPI/KOSDAQ)
   - Signal generation trigger
   - Real-time scan status monitoring
   - Result display after completion

3. **AI Analysis Display**
   - Sentiment analysis visualization
   - Recommendation badges
   - Keyword tags
   - Analysis summary

#### API Integration Status
All P1 backend APIs successfully integrated:
- ✅ `/api/system/health` - System health check
- ✅ `/api/system/data-status` - Data status
- ✅ `/api/kr/scan/status` - Scan status
- ✅ `/api/kr/scan/vcp` - VCP scan trigger
- ✅ `/api/kr/scan/signals` - Signal generation trigger
- ✅ `/api/kr/ai-summary/{ticker}` - AI analysis summary
- ✅ `/api/kr/ai-analysis` - AI analysis list
- ✅ WebSocket `/ws` - Real-time price streaming

#### Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│  KR Stock 대시보드                                  [홈]      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │  시스템 상태     │  │  Market Gate 상태               │  │
│  │  └───────────────┤  │  - YELLOW 레벨 50              │  │
│  │  스캔 제어        │  │  - KOSPI/KOSDAQ 상태           │  │
│  │  └───────────────┤  └─────────────────────────────────┘  │
│  └─────────────────┘                                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  실시간 가격 모니터링 (삼성전자, NAVER, ...)          │ │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  활성 VCP 시그널 (삼성전자, NAVER, ...)              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Development Guidelines

### Collector Pattern
All data collectors should inherit from `BaseCollector` in `src/collectors/base.py`:
- Implement `fetch_stock_list()`, `fetch_daily_prices()`, `fetch_supply_demand()`
- Use `normalize_ticker()` for consistent 6-digit ticker codes
- Use `validate_date_range()` for date range handling
- Include fallback/mock data for offline development

### Service Communication
- Use `ServiceRegistry` for service discovery (no hardcoded URLs)
- HTTP clients via `httpx.AsyncClient` for service-to-service calls
- Publish events via `EventBus` for async communication
- Cache frequently accessed data via `@cached` decorator

### Database Access
- Always use Repository pattern, never direct ORM calls in services
- Repository methods accept `AsyncSession` for transaction management
- Use `select()` with explicit columns for query optimization
- TimescaleDB hypertables for time-series data (DailyPrice)

### Testing Strategy
- Unit tests: Mock external dependencies (pykrx, Gemini API, Redis)
- Integration tests: Use real database via pytest fixtures
- Test scripts in `scripts/` for manual data collection testing

## Project Status

**Migration Complete:** 7/7 Phases (100%)
- ✅ Phase 1: Database Layer (SQLAlchemy + TimescaleDB)
- ✅ Phase 2: API Gateway (Service Discovery + Routing)
- ✅ Phase 3: VCP Scanner Service
- ✅ Phase 4: Signal Engine Service
- ✅ Phase 5: Celery Async Processing
- ✅ Phase 6: Event Bus (Redis Pub/Sub)
- ✅ Phase 7: Caching & Optimization

**PART_04-07 Complete:** 4/4 Phases (100%)
- ✅ Phase 1: Volume Score (거래대금 기반)
- ✅ Phase 2: Chart Score (VCP 패턴)
- ✅ Phase 3: Candle/Period/Flow Score
- ✅ Phase 4: Frontend UI 개선

**Test Results:** 622 passed, 20 skipped

---

## 📂 Documentation Structure

| 파일 | 용도 | 길이 |
|------|------|------|
| `PROGRESS.md` | 전체 진행 상황 요약 | ~130줄 |
| `TODO.md` | 진행 중/예정 작업 (P2, P3) | ~130줄 |
| `CLAUDE.md` | 프로젝트 개요 및 가이드 (이 파일) | |
| **docs/migration/** | 마이그레이션 상세 기록 (아카이브) | |
| ↳ `MIGRATION_COMPLETE.md` | Open Architecture 7 Phase 상세 | |
| ↳ `MIGRATION_NOTES.md` | 기술 스택, 버그 수정, 엔드포인트 | |
| ↳ `TODO_ARCHIVE.md` | 완료된 P0/P1 작업 내역 | |
| **docs/plans/** | 구현 계획서 | |
| ↳ `PLAN_*.md` | 각 기능별 상세 계획 |

### 문서 찾기 가이드
- **빠른 상태 확인**: `PROGRESS.md` 읽기
- **진행 중 작업**: `TODO.md` 읽기
- **완료된 작업 상세**: `docs/migration/` 폴더
- **마이그레이션 기록**: `docs/migration/MIGRATION_COMPLETE.md`

---

## Lessons Learned & Critical Notes

### Kiwoom REST API Integration (2026-01)

#### ⚠️ Common Pitfalls

1. **Chart Data Date Ordering**
   - **Issue**: Kiwoom API returns data in **reverse chronological order** (newest first), but frontend charts expect chronological order (oldest first)
   - **Fix**: Always sort chart data by date in ascending order before sending to frontend:
     ```typescript
     chartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
     ```
   - **Location**: `frontend/app/chart/page.tsx` lines 113, 72

2. **Missing Today's Data in `get_daily_prices()`**
   - **Issue**: Original date calculation `timedelta(days=days - i)` excluded today
   - **Fix**: Change to `timedelta(days=days - 1 - i)` to include today
   - **Location**: `src/kiwoom/rest_api.py` line 566

3. **Investor Chart API Returns All Historical Data**
   - **Issue**: `get_investor_chart()` API returns ALL historical data in response, not just the requested date
   - **Fix**: Filter results by requested date:
     ```python
     item_date = item.get("dt", "")
     if item_date != date_str:
         continue
     ```
   - **Location**: `src/kiwoom/rest_api.py` lines 624-627

4. **Rate Limiting (HTTP 429)**
   - **Issue**: Multiple rapid API calls trigger Kiwoom rate limits
   - **Fix**: Add 0.5s delay between requests + retry logic for 429 errors
   - **Location**: `src/kiwoom/rest_api.py` lines 580-581, 533-563

#### ✅ Price Display Format
- **Issue**: `formatPrice()` was converting prices ≥ 10,000 to "천원" format (e.g., "152천원")
- **Fix**: Always display full amount with commas: `formatPrice()` now returns "152,000원"
- **Location**: `frontend/lib/utils.ts` line 35

#### 🔧 Service Management
```bash
# API Gateway uses venv python (not system python)
.venv/bin/python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111

# Always check logs when API seems stuck
tail -f /tmp/api.log
```

#### 📊 Chart Component Data Flow
```
Kiwoom API (reverse order)
→ Backend transforms (sort by date asc)
→ Frontend displays (oldest → left, newest → right)
```

### Frontend Development Notes

#### Price Calculation Logic (After Sorting)
```typescript
// Data is now sorted: oldest [0] → newest [last]
const currentPrice = chartData[chartData.length - 1]?.close;  // Newest
const previousPrice = chartData[0]?.close;                   // Oldest
```

#### MiniChart Component
- Assumes data in chronological order
- `isPositive = lastPrice >= firstPrice` works correctly with sorted data

### Environment Variables (Updated)
```bash
# Kiwoom REST API
KIWOOM_APP_KEY=79YOf4S3zPm1NPTaie7WP3qamJnLD-Oxi1EOT4V-jA8
KIWOOM_SECRET_KEY=u0GjsIxLV8H4oY4jX5OPoEl_LpZR12NJnTd1BXkGqVY
KIWOOM_BASE_URL=https://api.kiwoom.com
USE_KIWOOM_REST=true
# USE_MOCK=false (default, not set in .env)
```
