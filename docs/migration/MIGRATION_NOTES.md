# Migration Reference Notes

기술 스택, 버그 수정, 운영 가이드 등 마이그레이션 관련 참고 사항.

---

## 🔧 기술 스택

### Backend
- **Python**: 3.10+
- **FastAPI**: API 서버
- **SQLAlchemy**: 2.0 ORM
- **PostgreSQL**: + TimescaleDB (데이터베이스)
- **Redis**: 캐시 + 메시징
- **Celery**: 비동기 작업

### Testing
- **pytest**: 테스트 프레임워크
- **pytest-asyncio**: 비동기 테스트
- **httpx**: 비동기 HTTP 클라이언트
- **pytest-cov**: 커버리지

### Infrastructure
- **Docker Compose**: 컨테이너 오케스트레이션
- **Redis**: 브로커/캐시
- **PostgreSQL**: + TimescaleDB (데이터베이스)

---

## 🐛 Bug Fixes

### 캐시 직렬화 버그 수정 (Phase 7)
- **문제**: bool 값이 `str(True)` = `'True'`로 변환되어 역직렬화 시 타입 불일치
- **원인**: 기본 타입을 `str()`로 변환하여 JSON 호환성 문제
- **해결**: 모든 값을 `json.dumps()`로 직렬화하여 타입 보존
- **파일**: `services/cache/redis_cache.py:55-64`
- **결과**: 7 passed → 8 passed

### Database Models 문법 오류 수정
- **문제 1**: `inst_trend = Column(String(20)` - 닫는 괄호 누락
- **문제 2**: `Unique` import - SQLAlchemy에 존재하지 않는 이름
- **해결**:
  - 괄호 추가: `inst_trend = Column(String(20))`
  - `Unique` 제거, `UniqueConstraint` 추가
- **파일**: `src/database/models.py:6-8, 73`

### PostgreSQL 드라이버 설치
- **문제**: `ModuleNotFoundError: No module named 'psycopg2'`
- **해결**: `psycopg2-binary` 설치

---

## 📦 Database Models

### 구현한 모델
- `Stock`: 종목 기본 정보 (ticker, name, market, sector, market_cap)
- `DailyPrice`: 일별 가격 데이터 (TimescaleDB hypertable)
- `InstitutionalFlow`: 기관/외국인 수급 데이터
- `Signal`: VCP/종가베팅 시그널
- `Trade`: 매매 기록
- `BacktestResult`: 백테스팅 결과
- `MarketStatus`: Market Gate 상태

### Repository 패턴
- `BaseRepository`: CRUD 베이스 클래스
- `StockRepository`: 종목 데이터 접근
- `SignalRepository`: 시그널 데이터 접근

---

## 🚀 서비스 엔드포인트

### API Gateway (Port 5111)
- `GET /health`: 헬스 체크
- `GET /services`: 서비스 목록
- `POST /services`: 서비스 등록

### VCP Scanner (Port 5112)
- `GET /health`: 서비스 상태
- `GET /signals`: 최신 VCP 시그널
- `POST /scan`: 시장 전체 스캔
- `GET /analyze/{ticker}`: 종목 분석

### Signal Engine (Port 5113)
- `GET /health`: 서비스 상태
- `GET /signals/latest`: 최신 시그널
- `POST /generate`: 시그널 생성
- `POST /analyze`: 종목 분석

---

## 📊 Celery 태스크

### 주기적 작업
- `scan_vcp_patterns`: VCP 패턴 스캔 (15분)
- `generate_closing_bet_signals`: 종가베팅 시그널 (30분)
- `update_market_gate`: Market Gate 업데이트 (1시간)
- `scan_all_markets`: 전체 시장 스캔

---

## 🔑 이벤트 채널

- `CHANNEL_SIGNALS`: 시그널 이벤트
- `CHANNEL_MARKET`: 시장 데이터 이벤트
- `CHANNEL_VCP`: VCP 스캔 이벤트

---

## 🔐 캐시 키 상수

- `CACHE_KEY_SIGNALS`: 시그널 목록
- `CACHE_KEY_MARKET_GATE`: Market Gate 상태
- `CACHE_KEY_STOCK_PRICES`: 종목 가격
- `CACHE_KEY_VCP_RESULTS`: VCP 분석 결과
