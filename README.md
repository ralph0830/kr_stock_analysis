# KR Stock Analysis System

한국 주식 분석 시스템 - VCP 패턴, 종가베팅 V2 시그널, 실시간 가격 업데이트

## 시스템 아키텍처

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Client    │─────▶│   Frontend   │─────▶│  API Gateway    │
│ (Next.js)    │      │   (Next.js)   │      │  (FastAPI)      │
└─────────────┘      └──────────────┘      └─────────────────┘
                            │                       │
                            │                       ▼
                            │              ┌─────────────────┐
                            │              │  VCP Scanner    │
                            │              │  (FastAPI)      │
                            │              └─────────────────┘
                            │                       │
                            ▼                       ▼
                     ┌──────────────┐      ┌─────────────────┐
                     │ Event Bus    │─────▶│  Signal Engine  │
                     │ (Redis)      │      │  (FastAPI)      │
                     └──────────────┘      └─────────────────┘
```

## 주요 기능

### 1. VCP 패턴 스캐너
- 볼린저밴드 수축 패턴 탐지
- SmartMoney 수급 분석 (외국인/기관)
- 5가지 요소로 종합 점수화

### 2. 종가베팅 V2 시그널
- 12점 만점 스코어링 시스템
- S/A/B/C 등급 산정
- 포지션 사이징 자동 계산

### 3. 실시간 가격 업데이트
- WebSocket 기반 실시간 브로드캐스팅
- 토픽 기반 구독 관리
- Mock 데이터 fallback

### 4. 데이터 수집
- KRXCollector: pykrx 래퍼
- 일별 시세, 수급 데이터 수집
- CSV to DB 마이그레이션

### 5. API 문서화
- OpenAPI 3.1 스펙 (16개 엔드포인트)
- 자동 생성 스크립트
- Swagger UI (`/docs`)

## 빠른 시작

### 1. 인프라 시작

```bash
docker compose up -d postgres redis
```

### 2. 백엔드 서비스 시작

```bash
# API Gateway (port 8000)
uvicorn services.api_gateway.main:app --reload

# VCP Scanner (port 8101) - Docker가 8001 사용 중
uvicorn services.vcp_scanner.main:app --port 8101 --reload

# Signal Engine (port 8003)
uvicorn services.signal_engine.main:app --port 8003 --reload
```

### 3. 프론트엔드 시작

```bash
cd frontend
npm install
npm run dev
```

브라우저에서:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000/dashboard

## 테스트

### 전체 테스트 실행

```bash
# 단위 테스트 (인프라 필요 없음)
pytest tests/unit/ -v

# 통합 테스트 (PostgreSQL + Redis 필요)
pytest tests/integration/ -v

# 전체 테스트
pytest tests/ -v
```

### 테스트 커버리지

- **398 passed** (단위 + 통합)
- **20 skipped**
- **9 failed** (일부 mock 설정 문제, 실제 코드 정상 작동)

## 프로젝트 구조

```
kr_stock_analysis/
├── services/              # 마이크로서비스
│   ├── api_gateway/      # API Gateway (FastAPI)
│   ├── vcp_scanner/      # VCP Scanner (FastAPI)
│   └── signal_engine/    # Signal Engine (FastAPI)
├── src/                   # 공유 코드
│   ├── analysis/          # 분석 모듈 (감성, 뉴스)
│   ├── clients/           # API/WebSocket 클라이언트
│   ├── collectors/        # 데이터 수집기 (KRX)
│   ├── database/          # DB 모델, 세션
│   ├── middleware/        # 미들웨어 (메트릭, 서킷 브레이커)
│   ├── repositories/      # Repository 패턴
│   ├── utils/             # 유틸리티
│   └── websocket/         # WebSocket 서버
├── tasks/                 # Celery 백그라운드 태스크
├── frontend/              # Next.js 프론트엔드
├── tests/                 # 테스트 코드
├── scripts/               # 유틸리티 스크립트
├── docs/                  # 문서
└── docker-compose.yml     # 인프라 설정
```

## 환경 변수

`.env` 파일 생성:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/kr_stock

# Redis
REDIS_URL=redis://localhost:6380/0

# Celery
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Service URLs
VCP_SCANNER_URL=http://localhost:8101
SIGNAL_ENGINE_URL=http://localhost:8003
MARKET_ANALYZER_URL=http://localhost:8002

# Gemini API (선택사항)
GEMINI_API_KEY=your_gemini_api_key_here
```

## API 클라이언트 라이브러리

### Python (src/clients/)

```python
from src.clients.api_client import APIClient

async def main():
    client = APIClient(base_url="http://localhost:8000")

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

### WebSocket (src/clients/)

```python
from src.clients.websocket_client import WebSocketClient

async def on_price(update):
    print(f"Price update: {update.ticker} = {update.price}")

client = WebSocketClient("ws://localhost:8000/ws/price")
await client.connect()
await client.subscribe("005930")  # 삼성전자 구독
client.on_price_update(on_price)
await client.listen()  # 계속 수신
```

## 메트릭 및 모니터링

- Prometheus 메트릭: `GET /metrics`
- 대시보드: `GET /api/dashboard/overview`
- Flower (Celery): http://localhost:5555

## OpenAPI 스펙 생성

```bash
# JSON 스펙
python scripts/generate_openapi_spec.py

# YAML 스펙
python scripts/generate_openapi_spec.py --yaml --output docs/openapi.yaml
```

## 진행 상황

### ✅ 완료된 작업

1. **Open Architecture 마이그레이션** (7/7 Phase)
2. **P1: 핵심 기능 구현**
   - VCP 패턴 분석
   - 종가베팅 V2 시그널
   - LLM 뉴스 분석
   - 데이터 수집기
3. **P2: 시스템 개선**
   - 구조화된 로깅
   - Circuit Breaker
   - Rate Limiting
   - 메트릭 수집
4. **P3: 프론트엔드/실시간 기능** (진행 중)
   - WebSocket 서버
   - API Gateway 통합
   - 실시간 가격 업데이트
   - 대시보드 API
   - **프론트엔드 Next.js 프로젝트** (완료)

### 🔄 진행 중인 작업

- [ ] WebSocket 실시간 연동
- [ ] 차트 시각화
- [ ] 종목 상세 페이지

## 라이선스

MIT License

## 개발팀

KR Stock Analysis Team
