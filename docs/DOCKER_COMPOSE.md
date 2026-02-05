# Docker Compose 통합 가이드

**작성일**: 2026-02-05
**버전**: 2.0 (통합 완료)

---

## 📋 목차

1. [개요](#개요)
2. [파일 구조](#파일-구조)
3. [사용법](#사용법)
4. [Profiles](#profiles)
5. [서비스 포트](#서비스-포트)
6. [환경 변수](#환경-변수)
7. [문제 해결](#문제-해결)

---

## 개요

Docker Compose 통합으로 **단일 진입점** (`docker-compose.yml`)과 **Profiles 기반 환경 구성**을 제공합니다.

### 주요 특징

- ✅ 단일 `docker-compose.yml` 진입점
- ✅ Profiles 기반 환경 분리 (dev/prod/test)
- ✅ 모듈화된 서비스 정의
- ✅ 상대 경로 사용 (이식성)
- ✅ 통합 네트워크 (`ralph-network`)

---

## 파일 구조

```
kr_stock_analysis/
├── docker-compose.yml              # 🎯 유일한 진입점
├── .env                            # 공통 환경 변수
├── .env.dev                        # 개발 환경 변수 (gitignored)
├── .env.prod                       # 프로덕션 환경 변수 (gitignored)
└── docker/compose/
    ├── profiles/                   # 환경별 오버라이드
    │   ├── dev.yml                 # 개발용 (핫 리로드)
    │   ├── prod.yml                # 프로덕션용 (최적화)
    │   └── test.yml                # 테스트용 (테스트 DB)
    ├── services/                   # 모듈화 서비스 정의
    │   ├── api-gateway.yml
    │   ├── vcp-scanner.yml
    │   ├── signal-engine.yml
    │   ├── daytrading-scanner.yml
    │   ├── chatbot.yml
    │   ├── frontend.yml
    │   └── celery.yml
    └── infra.yml                   # 인프라 (PostgreSQL, Redis)
```

---

## 사용법

### 테스트 실행 방법

**방법 1: Profiles 기반 (권장)**
```bash
# 테스트 환경 시작 (메인 구성 + test 오버라이드)
docker compose --profile test up --abort-on-container-exit
```

**방법 2: 독립 테스트 Compose**
```bash
# 완전히 독립된 테스트 환경 (test-runner 포함)
docker compose -f docker/compose/docker-compose.test.yml up --abort-on-container-exit
```

### 기본 명령어

```bash
# 개발 환경 시작
docker compose --profile dev up -d

# 프로덕션 환경 시작
docker compose --profile prod up -d

# 테스트 환경 시작
docker compose --profile test up -d

# 전체 중지
docker compose down

# 로그 보기
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f api-gateway
```

### Makefile 사용 (권장)

```bash
make dev        # 개발 환경 시작
make prod       # 운영 환경 시작
make stop       # 중지
make logs       # 로그 보기
make restart    # 재시작
make clean      # 전체 삭제 (볼륨 포함)
```

---

## Profiles

### dev (개발 환경)

**특징:**
- 핫 리로드 (소스 변경 시 자동 재시작)
- 소스 코드 볼륨 마운트
- 디버깅 모드 활성화
- 상세 로그 출력

```yaml
# 개발용 오버라이드 예시
services:
  api-gateway:
    volumes:
      - ../../src:/app/src:ro
    command: ["uvicorn", "main:app", "--reload"]
```

### prod (운영 환경)

**특징:**
- 최적화된 이미지 (production target)
- 리소스 제한 (CPU, Memory)
- 재시작 정책 (`restart: always`)
- 볼륨 마운트 없음 (baked images)

```yaml
# 운영용 오버라이드 예시
services:
  api-gateway:
    build:
      target: production
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
```

### test (테스트 환경)

**특징:**
- 별도 테스트 DB (`ralph_postgres_test`)
- 테스트용 Redis
- `tmpfs` 사용 (종료 후 자동 정리)
- 포트 분리 (5434, 6381)

---

## 서비스 포트

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Frontend | 5110 | Next.js UI |
| API Gateway | 5111 | 메인 API |
| VCP Scanner | 5112 | VCP 패턴 스캐너 |
| Signal Engine | 5113 | 시그널 엔진 |
| Chatbot | 5114 | AI 챗봇 |
| Daytrading Scanner | 5115 | 데이트레이딩 스캐너 |
| PostgreSQL | 5433 | 데이터베이스 |
| Redis | 6380 | 캐시/메시지 브로커 |
| Flower | 5555 | Celery 모니터링 |

### 테스트 환경 포트

| 서비스 | 포트 |
|--------|------|
| PostgreSQL (테스트) | 5434 |
| Redis (테스트) | 6381 |

---

## 환경 변수

### 필수 환경 변수 (`.env`)

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

# Kiwoom REST API (선택)
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true
```

### 개발/운영 환경 변수

```bash
# .env.dev (개발용)
LOG_LEVEL=DEBUG
RELOAD=true

# .env.prod (운영용)
LOG_LEVEL=INFO
RELOAD=false
```

---

## 문제 해결

### 포트 충돌

```bash
# 포트 사용 중인 프로세스 확인
sudo lsof -ti:5110 | xargs -r sudo kill -9
```

### 빌드 캐시 문제

```bash
# 캐시 없이 재빌드
docker compose build --no-cache
```

### 볼륨 초기화

```bash
# 전체 삭제 (데이터 포함)
docker compose down -v
```

### 네트워크 문제

```bash
# 네트워크 재생성
docker compose down
docker network prune
docker compose --profile dev up -d
```

---

## 이전 문서

- [DOCKER_COMPOSE_UNIFICATION.md](./DOCKER_COMPOSE_UNIFICATION.md) - 통합 계획 및 분석 문서

---

*마지막 업데이트: 2026-02-05*
