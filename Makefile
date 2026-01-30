# ============================================================================
# KR Stock Analysis - Makefile
# ============================================================================
# 사용법: make [명령어]
# ============================================================================

.PHONY: help up down restart logs status build clean test lint

# 기본 타겟: 도움말
help:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║          KR Stock Analysis - Docker Commands               ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "사용법: make [명령어]"
	@echo ""
	@echo "Docker 명령어:"
	@echo "  make up          - 전체 서비스 시작"
	@echo "  make up-infra    - 인프라만 시작 (PostgreSQL, Redis)"
	@echo "  make down        - 전체 서비스 중지"
	@echo "  make restart     - 전체 서비스 재시작"
	@echo "  make logs        - 전체 로그 보기"
	@echo "  make logs-api    - API Gateway 로그"
	@echo "  make logs-db     - DB 로그"
	@echo "  make status      - 서비스 상태 확인"
	@echo "  make build       - 이미지 재빌드"
	@echo "  make clean       - 전체 삭제 (볼륨 포함)"
	@echo ""
	@echo "개발 명령어:"
	@echo "  make shell       - 컨테이너 bash 접속"
	@echo "  make db-shell    - PostgreSQL 접속"
	@echo "  make redis-shell - Redis 접속"
	@echo "  make test        - 테스트 실행"
	@echo "  make lint        - 코드 검사"
	@echo ""

# 전체 서비스 시작
up:
	@echo "🚀 전체 서비스 시작..."
	docker compose up -d
	@echo ""
	@echo "✅ 시작 완료!"
	@echo ""
	@echo "📱 접속 URL:"
	@echo "   Frontend:   http://localhost:5110"
	@echo "   API:        http://localhost:5111"
	@echo "   VCP:        http://localhost:5112"
	@echo "   Signal:     http://localhost:5113"
	@echo "   Flower:     http://localhost:5555"

# 인프라만 시작
up-infra:
	@echo "🔧 인프라 서비스 시작..."
	docker compose up -d postgres redis
	@echo "✅ 인프라 시작 완료"

# 서비스 중지
down:
	@echo "🛑 서비스 중지..."
	docker compose down
	@echo "✅ 중지 완료"

# 재시작
restart:
	@echo "🔄 서비스 재시작..."
	docker compose restart
	@echo "✅ 재시작 완료"

# 로그 보기
logs:
	docker compose logs -f --tail=100

logs-api:
	docker compose logs -f api-gateway

logs-vcp:
	docker compose logs -f vcp-scanner

logs-signal:
	docker compose logs -f signal-engine

logs-db:
	docker compose logs -f postgres

logs-celery:
	docker compose logs -f celery-worker

logs-frontend:
	docker compose logs -f frontend

# 상태 확인
status:
	@echo "📊 서비스 상태:"
	@docker compose ps

# 빌드
build:
	@echo "🔨 이미지 재빌드..."
	docker compose build --no-cache
	@echo "✅ 빌드 완료"

# 전체 삭제
clean:
	@echo "⚠️  모든 컨테이너, 네트워크, 볼륨을 삭제합니다."
	@read -p "진행하시겠습니까? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker compose down -v; \
		echo "✅ 삭제 완료"; \
	else \
		echo "❌ 취소됨"; \
	fi

# 컨테이너 접속
shell:
	@docker compose exec api-gateway /bin/bash

db-shell:
	@docker compose exec postgres psql -U postgres -d kr_stock

redis-shell:
	@docker compose exec redis redis-cli

# 테스트
test:
	@echo "🧪 테스트 실행..."
	docker compose exec api-gateway pytest tests/ -v

# 코드 검사
lint:
	@echo "🔍 코드 검사..."
	docker compose exec api-gateway ruff check .
	docker compose exec api-gateway ruff format --check .

# 포맷
format:
	@echo "✨ 코드 포맷..."
	docker compose exec api-gateway ruff format .
