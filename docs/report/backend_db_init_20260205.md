# 백엔드 데이터베이스 초기화 이슈 보고서

**작성일**: 2026-02-05
**대상**: 백엔드 팀
**심각도**: 🔴 높음 (서비스 기능 장애)

---

## 1. 요약 (Executive Summary)

### 문제
Docker Compose로 실행 시 데이터베이스 테이블이 자동으로 생성되지 않아 API 엔드포인트에서 HTTP 500 에러가 발생합니다.

### 영향 범위
| 엔드포인트 | 상태 | 에러 원인 |
|------------|------|-----------|
| `GET /api/kr/signals` | ❌ 500 | `relation "signals" does not exist` |
| `GET /api/kr/market-gate` | ❌ 500 | `relation "market_status" does not exist` |
| `WebSocket /ws` | ✅ 정상 | DB 의존성 없음 |
| `GET /health` | ✅ 정상 | DB 의존성 없음 |

### 원인
1. DB Schema 정의는 존재 (`src/database/models.py`)
2. Migration 스크립트는 존재 (`migrations/add_missing_tables.py`)
3. **단, 실행 절차가 문서화되어 있지 않음**
4. Docker Compose에 DB init 프로세스가 없음

---

## 2. 현재 상황

### 2.1 Database 상태 (초기화 전)

```sql
SELECT tablename FROM pg_tables WHERE schemaname='public';
-- 결과: 0 rows (테이블 없음)
```

### 2.2 필요한 테이블 목록

| 테이블 | 용도 | 의존성 |
|--------|------|--------|
| `stocks` | 종목 기본 정보 | - |
| `signals` | VCP/종가베팅 시그널 | stocks(ticker) |
| `daily_prices` | 일봉 데이터 | stocks(ticker) |
| `market_status` | Market Gate 상태 | - |
| `ai_analyses` | AI 분석 결과 | stocks(ticker) |
| `backtest_results` | 백테스트 결과 | - |
| `daytrading_signals` | 단타 매수 신호 | - |
| `institutional_flows` | 기관 수급 데이터 | stocks(ticker) |

### 2.3 에러 로그

```
ERROR: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 2: FROM signals JOIN stocks ON signals.ticker = stocks.ticker

ERROR: (psycopg2.errors.UndefinedTable) relation "market_status" does not exist
LINE 2: FROM market_status ORDER BY market_status.date DESC
```

---

## 3. 존재하는 리소스

### 3.1 SQLAlchemy Models

```python
# src/database/models.py
class Stock(Base):
    __tablename__ = "stocks"
    # ...

class Signal(Base):
    __tablename__ = "signals"
    # ...

class DailyPrice(Base):
    __tablename__ = "daily_prices"
    # ...

class MarketStatus(Base):
    __tablename__ = "market_status"
    # ...
```

### 3.2 Migration Scripts

```
migrations/
├── add_missing_tables.py    # daily_prices, market_status 생성
└── add_news_urls_to_ai_analysis.py  # ai_analyses 테이블 수정
```

### 3.3 실행 명령어 (문서화되지 않음)

```bash
# 방법 1: SQLAlchemy create_all() 사용
uv run python -c "
from src.database.session import engine, Base
from src.database.models import Stock, Signal, DailyPrice, MarketStatus
Base.metadata.create_all(engine)
"

# 방법 2: Migration script 사용
uv run python migrations/add_missing_tables.py
```

---

## 4. 해결 방안

### 4.1 단기 해결 (즉시 필요)

#### 옵션 A: Docker Compose에 Init Container 추가

```yaml
# docker-compose.yml
services:
  db-init:
    image: ralph-stock-api-gateway:latest
    command: >
      sh -c "
      python -c 'from src.database.session import engine, Base;
      from src.database.models import *;
      Base.metadata.create_all(engine)'
      "
    depends_on:
      postgres:
        condition: service_healthy
```

#### 옵션 B: Entrypoint Script 추가

```bash
# scripts/init-db.sh
#!/bin/bash
echo "Initializing database..."
python -c "
from src.database.session import engine, Base
from src.database.models import *
Base.metadata.create_all(engine)
echo 'Database initialized successfully.'
"
```

### 4.2 장기 해결 (권장)

#### Alembic 도입

```bash
# Alembic 초기화
uv init alembic

# Migration 생성
uv run alembic revision --autogenerate -m "Initial schema"

# Migration 실행
uv run alembic upgrade head
```

#### Docker Compose 통합

```yaml
services:
  api-gateway:
    # ...
    entrypoint: ["/app/scripts/docker-entrypoint.sh"]
```

```bash
# scripts/docker-entrypoint.sh
#!/bin/bash
# Run migrations
uv run alembic upgrade head

# Start application
exec uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111
```

---

## 5. 문서화 요구사항

### 5.1 OPEN_ARCHITECTURE.md에 추가할 내용

```markdown
## Database Initialization

### First-time Setup

1. **Local Development**
   ```bash
   uv sync
   docker compose up -d postgres redis
   uv run python -c "from src.database.session import engine, Base; from src.database.models import *; Base.metadata.create_all(engine)"
   ```

2. **Docker Compose**
   ```bash
   docker compose --profile dev up -d
   # DB init container automatically creates tables
   ```

### Running Migrations

```bash
# Method 1: SQLAlchemy create_all
uv run python scripts/init_db.py

# Method 2: Alembic (recommended for production)
uv run alembic upgrade head
```
```

### 5.2 README.md에 추가할 내용

```markdown
## Quick Start

1. Clone and install dependencies
2. Start services: `make dev`
3. **Database initializes automatically on first run**
```

---

## 6. 검증 체크리스트

| 항목 | 상태 | 비고 |
|------|------|------|
| DB Models 정의 | ✅ | `src/database/models.py` |
| Migration Scripts | ✅ | `migrations/*.py` |
| 실행 절차 문서화 | ❌ | **추가 필요** |
| Docker Init Container | ❌ | **추가 필요** |
| Seed Data Loader | ❌ | **추가 필요** (종목 기본 정보 등) |
| Alembic 설정 | ❌ | **추가 권장** |

---

## 7. 권장 우선순위

| 순위 | 작업 | 예상 소요 시간 |
|------|------|----------------|
| 1 | DB init script 생성 | 1시간 |
| 2 | OPEN_ARCHITECTURE.md 문서 업데이트 | 30분 |
| 3 | Docker Compose에 init service 추가 | 1시간 |
| 4 | Seed data loader 작성 | 2시간 |
| 5 | Alembic 도입 (선택) | 4시간 |

---

## 8. 관련 문서

| 문서 | 경로 |
|------|------|
| Open Architecture | `docs/OPEN_ARCHITECTURE.md` |
| DB Models | `src/database/models.py` |
| Migration Scripts | `migrations/*.py` |
| Docker Compose | `docker-compose.yml` |
| 프론트엔드 테스트 보고서 | `docs/report/frontend_test_20260205.md` |

---

## 9. 연락처

| 팀 | 이슈 |
|------|------|
| 프론트엔드 | 프론트엔드 코드 정상 작동 중 |
| 백엔드 | DB 초기화 절차 구현 필요 |

---

*마지막 업데이트: 2026-02-05*
