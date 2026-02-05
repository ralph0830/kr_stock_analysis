# Docker Compose 통합 분석 및 제안

**작성일**: 2026-02-05
**완료일**: 2026-02-05 ✅
**상태**: **완료** - 모든 계획 실행됨

---

## ✅ 완료 상태

| 단계 | 작업 | 상태 |
|------|------|------|
| 1 | `docker/compose/profiles/` 디렉토리 생성 | ✅ |
| 2 | dev.yml, prod.yml, test.yml 생성 | ✅ |
| 3 | docker-compose.yml 수정 (include 추가) | ✅ |
| 4 | 중복 파일 6개 삭제 | ✅ |
| 5 | 문서화 (DOCKER_COMPOSE.md) | ✅ |
| 6 | CLAUDE.md 참조 링크 추가 | ✅ |

---

## 1. 현재 파일 구조

### 1.1 파일 목록

| 경로 | 라인 | 설명 | 사용 중? |
|------|------|------|----------|
| `docker-compose.yml` | 82 | 메인 파일 (include 방식) | ✅ |
| `docker-compose.dev.yml` | 118 | 개발 환경 오버라이드 (루트) | ⚠️ 중복 |
| `docker-compose.prod.yml` | 180 | 프로덕션 환경 오버라이드 (루트) | ⚠️ 중복 |
| `docker/compose/docker-compose.base.yml` | 69 | 인프라 정의 | ⚠️ 미사용 |
| `docker/compose/docker-compose.dev.yml` | 202 | 개발 환전체 | ⚠️ 중복 |
| `docker/compose/docker-compose.prod.yml` | 400 | 프로덕션 환경 전체 | ⚠️ 중복 |
| `docker/compose/docker-compose.test.yml` | - | 테스트 환경 | ❓ 확인 필요 |
| `docker/compose/infra.yml` | 59 | 인프라 (PostgreSQL, Redis) | ✅ 사용 중 |
| `docker/compose/services/*.yml` | 6개 | 모듈화 서비스 정의 | ✅ 사용 중 |

### 1.2 파일 계층 구조

```
현재 구조 (복잡):
├── docker-compose.yml (메인, include 사용)
├── docker-compose.dev.yml (개발 오버라이드) ← 중복
├── docker-compose.prod.yml (프로덕션 오버라이드) ← 중복
└── docker/compose/
    ├── docker-compose.base.yml (인프라) ← 미사용
    ├── docker-compose.dev.yml (개발 전체) ← 중복
    ├── docker-compose.prod.yml (프로덕션 전체) ← 중복
    ├── docker-compose.test.yml (테스트)
    ├── infra.yml (인프라) ✅
    └── services/ (모듈화 서비스) ✅
```

---

## 2. 중복 분석

### 2.1 인프라 (PostgreSQL, Redis) 정의 중복

| 파일 | PostgreSQL | Redis | 네트워크 |
|------|-----------|-------|---------|
| `docker-compose.base.yml` | ✅ | ✅ | `ralph_stock_network` |
| `infra.yml` | ✅ | ✅ | `ralph-network` |
| `docker-compose.prod.yml` | 주석 처리 | 주석 처리 | - |

**문제**: `docker-compose.base.yml`과 `infra.yml`이 동일한 역할을 하지만, 네트워크 이름이 다릅니다.

### 2.2 개발 환경 정의 중복

| 파일 | 서비스 정의 수 | 경로 |
|------|---------------|------|
| `docker-compose.dev.yml` | 8개 (전체) | 프로젝트 루트 |
| `docker/compose/docker-compose.dev.yml` | 8개 (전체) | docker/compose/ |
| `docker/compose/services/*.yml` | 6개 (모듈화) | docker/compose/services/ |

**문제**: 동일한 서비스가 3곳에서 중복 정의됨

### 2.3 프로덕션 환경 정의 중복

| 파일 | 서비스 정의 수 | 경로 |
|------|---------------|------|
| `docker-compose.prod.yml` | 10개 (전체) | 프로젝트 루트 |
| `docker/compose/docker-compose.prod.yml` | 10개 (전체) | docker/compose/ |

**문제**: 동일한 서비스가 2곳에서 중복 정의됨

---

## 3. 현재 사용 방식

### 3.1 메인 파일 (`docker-compose.yml`)

```yaml
include:
  - docker/compose/infra.yml
  - docker-compose.dev.yml              # ⚠️ 루트에 있는 파일
  - docker/compose/services/*.yml      # ✅ 모듈화 서비스

services:
  api-gateway:
    profiles: [dev, prod]
    # 기본 정의만, override는 각 환경 파일에서
```

### 3.2 실제 실행 명령어

```bash
# 개발 환경
docker compose --profile dev up -d
# → docker-compose.yml + docker-compose.dev.yml + services/*.yml

# 프로덕션 환경
docker compose --profile prod up -d
# → docker-compose.yml + docker-compose.prod.yml + services/*.yml

# 또는 개별 파일 직접 지정
docker compose -f docker/compose/docker-compose.dev.yml up -d
```

---

## 4. 문제점 요약

| 문제 | 영향 | 심각도 |
|------|------|--------|
| **파일 중복** | 동일 서비스가 3~4곳에서 정의됨 | 🔴 높음 |
| **네트워크 이름 불일치** | `ralph-network` vs `ralph_stock_network` | 🟡 중간 |
| **경로 하드코딩** | `/home/ralph/work/python/kr_stock_analysis` | 🟡 중간 |
| **include 순환 참조** | 서로를 참조하는 복잡한 구조 | 🟡 중간 |
| **환경 변수 위치** | `.env` vs `.env.production` | 🟢 낮음 |
| **프론트엸드 환경 변수** | `NEXT_PUBLIC_WS_URL` 하드코딩 | 🔴 높음 |

---

## 5. 통합 제안

### 5.1 목표 구조

```
제안 구조 (단순):
├── docker-compose.yml           # 유일한 진입점 (profiles 사용)
├── .env                          # 공통 환경 변수
├── .env.dev                     # 개발 환경 변수 (gitignored)
├── .env.prod                    # 프로덕션 환경 변수 (gitignored)
└── docker/compose/
    ├── profiles/
    │   ├── dev.yml             # 개발용 오버라이드
    │   ├── prod.yml            # 프로덕션용 오버라이드
    │   └── test.yml            # 테스트용 오버라이드
    ├── services/                 # 서비스 정의 (모듈화 유지)
    │   ├── api-gateway.yml
    │   ├── vcp-scanner.yml
    │   ├── signal-engine.yml
    │   ├── daytrading-scanner.yml
    │   ├── chatbot.yml
    │   ├── frontend.yml
    │   └── celery.yml
    └── infra.yml                 # 인프라 (PostgreSQL, Redis)
```

### 5.2 단일 `docker-compose.yml` 구조

```yaml
# docker-compose.yml
# =============================================================================
# Ralph Stock Analysis - 통합 Docker Compose 설정
# =============================================================================

include:
  - docker/compose/infra.yml
  - docker/compose/services/api-gateway.yml
  - docker/compose/services/vcp-scanner.yml
  - docker/compose/services/signal-engine.yml
  - docker/compose/services/daytrading-scanner.yml
  - docker/compose/services/chatbot.yml
  - docker/compose/services/frontend.yml
  - docker/compose/services/celery.yml

# Profiles-based environment configuration
include:
  - docker/compose/profiles/dev.yml
  - docker/compose/profiles/prod.yml
  - docker/compose/profiles/test.yml

# 네트워크 정의 (공통)
networks:
  ralph-network:
    name: ralph-network
    driver: bridge

# 볼륨 정의 (공통)
volumes:
  postgres-data:
  redis-data:
```

### 5.3 Profile별 오버라이드 파일

#### `docker/compose/profiles/dev.yml`

```yaml
# 개발 환경 오버라이드
services:
  api-gateway:
    build:
      target: development
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
    volumes:
      - ../../src:/app/src:ro
      - ../../services:/app/services:ro
    command: ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "5111", "--reload"]

  frontend:
    environment:
      # 비워서 동적 URL 결정
      NEXT_PUBLIC_API_URL: ""
      NEXT_PUBLIC_WS_URL: ""
    volumes:
      - ../../frontend:/app
      - /app/node_modules
      - /app/.next

  # ... 다른 서비스들도 동일한 패턴
```

#### `docker/compose/profiles/prod.yml`

```yaml
# 프로덕션 환경 오버라이드
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

  frontend:
    environment:
      # 빈 값으로 전달하여 동적 결정
      NEXT_PUBLIC_API_URL: ""
      NEXT_PUBLIC_WS_URL: ""
    restart: always
    # No volumes for production

  # ... 다른 서비스들도 동일한 패턴
```

---

## 6. 삭제 제안

### 6.1 삭제할 파일

| 파일 | 이유 | 대체 |
|------|------|------|
| `docker-compose.dev.yml` | `docker/compose/profiles/dev.yml`로 통합 | profiles/dev.yml |
| `docker-compose.prod.yml` | `docker/compose/profiles/prod.yml`로 통합 | profiles/prod.yml |
| `docker/compose/docker-compose.base.yml` | `infra.yml`과 중복 | infra.yml |
| `docker/compose/docker-compose.dev.yml` | `profiles/dev.yml`로 통합 | profiles/dev.yml |
| `docker/compose/docker-compose.prod.yml` | `profiles/prod.yml`로 통합 | profiles/prod.yml |

### 6.2 보관할 파일

| 파일 | 이유 |
|------|------|
| `docker-compose.yml` | 유일한 진입점 |
| `docker/compose/infra.yml` | 인프라 정의 |
| `docker/compose/services/*.yml` | 모듈화 서비스 정의 |
| `docker/compose/profiles/*.yml` | 환경별 오버라이드 (새로 생성) |

---

## 7. 이전 절차

### 7.1 1단계: 새 디렉토리 구조 생성

```bash
mkdir -p docker/compose/profiles
```

### 7.2 2단계: Profile 파일 생성

```bash
# docker/compose/profiles/dev.yml 생성
# docker/compose/profiles/prod.yml 생성
# docker/compose/profiles/test.yml 생성
```

### 7.3 3단계: 메인 파일 수정

```bash
# docker-compose.yml 수정
# include에 profiles 추가
```

### 7.4 4단계: 네트워크 이름 통일

```bash
# 모든 파일에서 ralph_stock_network → ralph-network
```

### 7.5 5단계: 기존 파일 삭제

```bash
rm docker-compose.dev.yml
rm docker-compose.prod.yml
rm docker/compose/docker-compose.base.yml
rm docker/compose/docker-compose.dev.yml
rm docker/compose/docker-compose.prod.yml
```

### 7.6 6단계: 테스트

```bash
# 개발 환경 테스트
docker compose --profile dev up -d

# 프로덕션 환경 테스트
docker compose --profile prod up -d

# 정지
docker compose down
```

---

## 8. 사용 명령어 변경

### 8.1 변경 전

```bash
# 방법 1: profiles 사용
docker compose --profile dev up -d

# 방법 2: 직접 파일 지정 (혼란)
docker compose -f docker/compose/docker-compose.dev.yml up -d

# 방법 3: 여러 파일 지정 (복잡)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 8.2 변경 후

```bash
# 개발 환경 (단일 명령어)
docker compose --profile dev up -d

# 프로덕션 환경 (단일 명령어)
docker compose --profile prod up -d

# 테스트 환경 (단일 명령어)
docker compose --profile test up -d
```

---

## 9. Makefile 통합

```makefile
# Makefile
.PHONY: dev prod stop restart logs clean

dev:
	docker compose --profile dev up -d

prod:
	docker compose --profile prod up -d

stop:
	docker compose down

restart:
	docker compose down
	docker compose --profile dev up -d

logs:
	docker compose logs -f

clean:
	docker compose down -v
```

---

## 10. 기대 효과

| 항목 | 변경 전 | 변경 후 | 개선 |
|------|--------|--------|------|
| docker-compose 파일 | 7개 | 1개 + profiles | 🟢 단순화 |
| 중복 정의 | 다수 | 제거 | 🟢 유지보수 향상 |
| 실행 명령어 | 여러 방법 | 단일 방법 | 🟢 사용성 향상 |
| 네트워크 이름 | 2개 | 1개 | 🟢 일관성 |
| 경로 하드코딩 | 절대경로 | 상대경로 | 🟢 이식성 |

---

*마지막 업데이트: 2026-02-05*
