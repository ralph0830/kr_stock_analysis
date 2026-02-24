# Mock 서비스 구축 완료 보고서

**작성일**: 2026-02-06
**작성자**: DevOps Architect (DevOps-Infrastructure Team)
**상태**: ✅ 완료

---

## 📋 개요

테스트 환경에서 외부 API 의존성을 제거하기 위해 Mock 서비스를 구축했습니다.

### 구축 목표

- ✅ 키움 증권 REST API Mock 서버 구현
- ✅ 실시간 데이터 전송용 Mock WebSocket 서버 구현
- ✅ Docker Compose test profile 통합
- ✅ 자동화된 테스트 환경 제공

---

## 🏗️ 아키텍처

### 구성 요소

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Environment                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ Mock Kiwoom API  │         │ Mock WebSocket   │        │
│  │   Port: 5116     │────────▶│   Port: 5117     │        │
│  │                  │         │                  │        │
│  │ - OAuth2 Mock    │         │ - 실시간 가격    │        │
│  │ - 현재가 조회    │         │ - VCP 시그널     │        │
│  │ - 차트 데이터    │         │ - 종가베팅      │        │
│  │ - 종목 목록      │         │ - SmartMoney     │        │
│  └──────────────────┘         └──────────────────┘        │
│           ▲                            ▲                   │
│           │                            │                   │
│  ┌────────┴────────────────────────────┴────────┐         │
│  │           API Gateway (Test)                 │         │
│  │              Port: 5111                      │         │
│  └──────────────────────────────────────────────┘         │
│           │                                                │
│           ▼                                                │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ postgres-test    │         │  redis-test      │        │
│  │   Port: 5434     │         │   Port: 6381     │        │
│  └──────────────────┘         └──────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 파일 구조

### 생성된 파일

```
tests/mock_servers/
├── __init__.py                          # 패키지 초기화
├── kiwoom_mock_server.py                # 키움 API Mock 서버
├── websocket_mock_server.py             # WebSocket Mock 서버
├── websocket_mock_app.py                # WebSocket FastAPI 앱
├── Dockerfile.kiwoom-mock               # Kiwoom Mock용 Dockerfile
└── Dockerfile.websocket-mock            # WebSocket Mock용 Dockerfile

docker/compose/services/
└── mock-services.yml                    # Mock 서비스 정의

docker/compose/profiles/
└── test.yml                             # Test profile (업데이트)
```

---

## 🔧 구현 상세

### 1. Mock Kiwoom REST API 서버

**기능**:
- OAuth2 토큰 발급/갱신 시뮬레이션
- 현재가 조회 (ka10001)
- 종목별투자자기관별차트 (ka10060)
- 종목정보 리스트 (ka10099)
- 주식 일봉 차트 (ka10081)
- 지수 데이터 조회

**API 엔드포인트**:
```
POST /oauth2/token                    # 토큰 발급
POST /api/dostk/ka10001               # 현재가 조회
POST /api/dostk/chart                 # 차트 데이터
POST /api/dostk/stkinfo               # 종목 목록/지수
POST /api/dostk/ka10081               # 일봉 차트
```

**특징**:
- FastAPI 기반 경량 서버
- 무작위 데이터 생성 (테스트용)
- 실제 키움 API 응답 구조 모방
- HTTP 헤더 검증 (Authorization, api-id)

### 2. Mock WebSocket 서버

**기능**:
- 실시간 가격 데이터 브로드캐스트 (2초 간격)
- VCP 시그널 전송 (10% 확률)
- 종가베팅 시그널 전송 (10% 확률)
- 클라이언트 구독/구독취소 지원

**WebSocket 엔드포인트**:
```
WS /ws                                 # WebSocket 연결
GET  /                                 # 헬스 체크
GET  /health                           # 헬스 체크 (Docker용)
GET  /stats                            # 서버 통계
```

**특징**:
- FastAPI WebSocket 구현
- 자동 브로드캐스팅 (백그라운드 태스크)
- 연결 관리 및 자동 정리
- Ping/Pong 지원

### 3. Docker Compose 통합

**Test Profile 오버라이드**:
```yaml
# Mock 서비스 환경변수 설정
api-gateway:
  environment:
    - KIWOOM_API_URL=http://mock-kiwoom-api:5116
    - USE_KIWOOM_REST=false

# Mock 서비스 의존성 추가
depends_on:
  mock-kiwoom-api:
    condition: service_healthy
  mock-websocket:
    condition: service_healthy
```

**리소스 제한**:
- Mock Kiwoom API: CPU 0.5, Memory 512MB
- Mock WebSocket: CPU 0.25, Memory 256MB

---

## 🚀 사용 방법

### 테스트 환경 시작

```bash
# Mock 서비스 포함하여 테스트 환경 시작
make test-up

# 또는 직접 실행
docker compose --profile test up -d
```

### 접속 URL

| 서비스 | URL | 설명 |
|--------|-----|------|
| Mock Kiwoom API | http://localhost:5116 | 키움 API Mock |
| Mock WebSocket | http://localhost:5117 | WebSocket Mock |
| Mock API Docs | http://localhost:5116/docs | FastAPI 문서 |
| Test DB | localhost:5434 | PostgreSQL 테스트 DB |
| Test Redis | localhost:6381 | Redis 테스트 |

### 상태 확인

```bash
# 테스트 환경 상태 확인
make test-status

# 로그 보기
make test-logs

# Mock 서비스 헬스 체크
curl http://localhost:5116/          # Kiwoom Mock
curl http://localhost:5117/health    # WebSocket Mock
```

### 테스트 환경 중지

```bash
make test-down
```

---

## 📊 포트 할당

| 포트 | 서비스 | 설명 |
|------|--------|------|
| 5111 | API Gateway | 메인 API (테스트 환경) |
| 5116 | Mock Kiwoom API | 키움 API Mock |
| 5117 | Mock WebSocket | WebSocket Mock |
| 5434 | postgres-test | 테스트용 PostgreSQL |
| 6381 | redis-test | 테스트용 Redis |

---

## 🧪 테스트 시나리오

### 1. Mock Kiwoom API 테스트

```bash
# 토큰 발급 테스트
curl -X POST http://localhost:5116/oauth2/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "appkey": "test_key",
    "secretkey": "test_secret"
  }'

# 현재가 조회 테스트
curl -X POST http://localhost:5116/api/dostk/ka10001 \
  -H "Authorization: Bearer mock_token" \
  -H "api-id: ka10001" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "t0414",
    "params": {
      "t0414InBlock": {"shcode": "005930"}
    },
    "id": 1
  }'
```

### 2. Mock WebSocket 테스트

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:5117/ws"
    async with websockets.connect(uri) as websocket:
        # 구독 요청
        await websocket.send(json.dumps({
            "type": "subscribe",
            "ticker": "005930"
        }))

        # 메시지 수신
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"수신: {data}")

asyncio.run(test_websocket())
```

---

## 🔍 모니터링

### Docker Healthcheck

모든 Mock 서비스는 healthcheck가 구성되어 있습니다:

```yaml
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://localhost:5116/"]
  interval: 10s
  timeout: 5s
  retries: 3
```

### 로그 확인

```bash
# Mock Kiwoom API 로그
docker compose logs -f mock-kiwoom-api

# Mock WebSocket 로그
docker compose logs -f mock-websocket

# 전체 테스트 환경 로그
make test-logs
```

---

## 🎯 다음 단계

### 추가 기능 (향후 개발)

- [ ] Prometheus metrics export
- [ ] Grafana 대시보드 연동
- [ ] 더 많은 테스트 시나리오 데이터
- [ ] 에러 케이스 시뮬레이션 (Rate Limiting, 서버 에러 등)
- [ ] 성능 테스트 지원 (대량 데이터 생성)

### 문서화

- [ ] API 사용 가이드
- [ ] 테스트 작성 예제
- [ ] CI/CD 파이프라인 통합 가이드

---

## 📝 참고 사항

### 테스트 환경 변수

```bash
# .env.test
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/ralph_stock_test
REDIS_URL=redis://localhost:6381/0
KIWOOM_API_URL=http://mock-kiwoom-api:5116
USE_KIWOOM_REST=false
```

### 한계점

- Mock 데이터는 무작위 생성이므로 실제 시장 데이터와 다름
- 복잡한 에러 케이스는 아직 구현되지 않음
- 인증 로직이 단순화됨

---

## ✅ 완료 체크리스트

- [x] Mock Kiwoom REST API 서버 구현
- [x] Mock WebSocket 서버 구현
- [x] Dockerfile 작성
- [x] Docker Compose 통합
- [x] Test profile 업데이트
- [x] Makefile 명령 추가
- [x] Healthcheck 구성
- [x] 로깅 설정
- [x] 리소스 제한 설정
- [x] 문서 작성

---

**DevOps Architect**: DevOps-Infrastructure Team
**프로젝트**: Ralph Stock Analysis System
**문서 버전**: 1.0
