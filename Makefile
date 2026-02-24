# ============================================================================
# Ralph Stock Analysis - Makefile
# ============================================================================
# Profiles 기반 Docker Compose 관리
# ============================================================================
# 사용법: make [명령어]
# ============================================================================

.PHONY: help dev prod test stop restart logs status build clean test lint format \
        up down up-infra logs-api logs-vcp logs-signal logs-db logs-celery logs-frontend \
        shell db-shell redis-shell \
        monitoring monitoring-stop monitoring-status monitoring-logs \
        prometheus grafana alertmanager \
        test-up test-down test-logs test-status

# 기본 타겟: 도움말
help:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║          Ralph Stock Analysis - Docker Commands              ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "사용법: make [명령어]"
	@echo ""
	@echo "Profiles 기반 실행:"
	@echo "  make dev         - 개발 환경 시작 (hot reload)"
	@echo "  make prod        - 운영 환경 시작 (optimized)"
	@echo "  make stop        - 모든 서비스 중지"
	@echo ""
	@echo "Docker 명령어 (호환성):"
	@echo "  make up          - 전체 서비스 시작 (dev profile)"
	@echo "  make down        - 전체 서비스 중지"
	@echo "  make up-infra    - 인프라만 시작 (PostgreSQL, Redis)"
	@echo "  make restart     - 전체 서비스 재시작"
	@echo "  make logs        - 전체 로그 보기"
	@echo "  make status      - 서비스 상태 확인"
	@echo "  make build       - 이미지 재빌드"
	@echo "  make clean       - 전체 삭제 (볼륨 포함)"
	@echo ""
	@echo "로그 보기:"
	@echo "  make logs-api    - API Gateway 로그"
	@echo "  make logs-vcp    - VCP Scanner 로그"
	@echo "  make logs-signal - Signal Engine 로그"
	@echo "  make logs-db     - DB 로그"
	@echo "  make logs-celery - Celery 로그"
	@echo "  make logs-frontend - Frontend 로그"
	@echo ""
	@echo "개발 명령어:"
	@echo "  make shell       - API Gateway 컨테이너 bash 접속"
	@echo "  make db-shell    - PostgreSQL 접속"
	@echo "  make redis-shell - Redis 접속"
	@echo "  make test        - 테스트 실행"
	@echo "  make lint        - 코드 검사"
	@echo "  make format      - 코드 포맷"
	@echo ""
	@echo "모니터링:"
	@echo "  make monitoring      - 모니터링 스택 시작"
	@echo "  make monitoring-stop - 모니터링 스택 중지"
	@echo "  make monitoring-status - 모니터링 상태"
	@echo "  make prometheus      - Prometheus 접속"
	@echo "  make grafana         - Grafana 접속"
	@echo "  make alertmanager    - AlertManager 접속"
	@echo ""
	@echo "테스트 환경:"
	@echo "  make test-up     - 테스트 환경 시작 (Mock 서비스 포함)"
	@echo "  make test-down   - 테스트 환경 중지"
	@echo "  make test-logs   - 테스트 로그 보기"
	@echo "  make test-status - 테스트 환경 상태 확인"
	@echo ""

# ============================================================================
# Profiles 기반 실행
# ============================================================================

# 개발 환경 시작
dev:
	@echo "🚀 개발 환경 시작 (dev profile)..."
	docker compose --profile dev up -d
	@echo ""
	@echo "✅ 개발 환경 시작 완료!"
	@echo ""
	@echo "📱 접속 URL:"
	@echo "   Frontend:   http://localhost:5110"
	@echo "   API:        http://localhost:5111/docs"
	@echo "   VCP:        http://localhost:5112/docs"
	@echo "   Signal:     http://localhost:5113/docs"
	@echo "   Chatbot:    http://localhost:5114/docs"
	@echo "   Flower:     http://localhost:5555"
	@echo ""
	@echo "📋 로그 보기: make logs"

# 운영 환경 시작
prod:
	@echo "🚀 운영 환경 시작 (prod profile)..."
	docker compose --profile prod up -d
	@echo ""
	@echo "✅ 운영 환경 시작 완료!"
	@echo ""
	@echo "📋 로그 보기: make logs"

# 서비스 중지
stop:
	@echo "🛑 서비스 중지..."
	docker compose down
	@echo "✅ 중지 완료"

# ============================================================================
# Docker 명령어 (호환성)
# ============================================================================

# 전체 서비스 시작 (dev profile)
up: dev

# 인프라만 시작
up-infra:
	@echo "🔧 인프라 서비스 시작..."
	docker compose up -d postgres redis
	@echo "✅ 인프라 시작 완료"

# 서비스 중지 (alias)
down: stop

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

logs-chatbot:
	docker compose logs -f chatbot

logs-db:
	docker compose logs -f postgres

logs-celery:
	docker compose logs -f celery-worker celery-beat

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

# ============================================================================
# 개발 명령어
# ============================================================================

# 컨테이너 접속
shell:
	@docker compose exec api-gateway /bin/bash

db-shell:
	@docker compose exec postgres psql -U postgres -d ralph_stock

redis-shell:
	@docker compose exec redis redis-cli

# 테스트
test:
	@echo "🧪 테스트 실행..."
	uv run pytest tests/ -v

# 코드 검사
lint:
	@echo "🔍 코드 검사..."
	uv run ruff check .
	uv run ruff format --check .

# 포맷
format:
	@echo "✨ 코드 포맷..."
	uv run ruff format .

# ============================================================================
# 모니터링 스택
# ============================================================================

# 모니터링 스택 시작
monitoring:
	@echo "📊 모니터링 스택 시작..."
	docker compose -f docker/compose/infra.yml -f docker/compose/services/monitoring.yml up -d
	@echo ""
	@echo "✅ 모니터링 스택 시작 완료!"
	@echo ""
	@echo "📱 접속 URL:"
	@echo "   Prometheus:   http://localhost:9090"
	@echo "   Grafana:      http://localhost:3000 (admin/admin)"
	@echo "   AlertManager: http://localhost:9093"
	@echo ""
	@echo "📋 로그 보기: make monitoring-logs"

# 모니터링 스택 중지
monitoring-stop:
	@echo "🛑 모니터링 스택 중지..."
	docker compose -f docker/compose/infra.yml -f docker/compose/services/monitoring.yml down
	@echo "✅ 중지 완료"

# 모니터링 스택 상태
monitoring-status:
	@echo "📊 모니터링 스택 상태:"
	@docker compose -f docker/compose/infra.yml -f docker/compose/services/monitoring.yml ps

# 모니터링 로그
monitoring-logs:
	docker compose -f docker/compose/infra.yml -f docker/compose/services/monitoring.yml logs -f --tail=100

# Prometheus 접속
prometheus:
	@echo "🔗 Prometheus 열기: http://localhost:9090"
	@xdg-open http://localhost:9090 2>/dev/null || echo "브라우저에서 http://localhost:9090 접속"

# Grafana 접속
grafana:
	@echo "🔗 Grafana 열기: http://localhost:3000"
	@xdg-open http://localhost:3000 2>/dev/null || echo "브라우저에서 http://localhost:3000 접속"

# AlertManager 접속
alertmanager:
	@echo "🔗 AlertManager 열기: http://localhost:9093"
	@xdg-open http://localhost:9093 2>/dev/null || echo "브라우저에서 http://localhost:9093 접속"

# ============================================================================
# 테스트 환경
# ============================================================================

# 테스트 환경 시작 (test profile + mock services)
test-up:
	@echo "🧪 테스트 환경 시작 (test profile + Mock 서비스)..."
	docker compose --profile test up -d
	@echo ""
	@echo "✅ 테스트 환경 시작 완료!"
	@echo ""
	@echo "📱 접속 URL:"
	@echo "   Mock Kiwoom API:   http://localhost:5116"
	@echo "   Mock WebSocket:    http://localhost:5117"
	@echo "   Test DB (Postgres): localhost:5434"
	@echo "   Test Redis:        localhost:6381"
	@echo ""
	@echo "📋 로그 보기: make test-logs"
	@echo "📋 상태 확인: make test-status"

# 테스트 환경 중지
test-down:
	@echo "🛑 테스트 환경 중지..."
	docker compose --profile test down
	@echo "✅ 중지 완료"

# 테스트 로그 보기
test-logs:
	@echo "📋 테스트 환경 로그:"
	docker compose --profile test logs -f --tail=100

# 테스트 환경 상태 확인
test-status:
	@echo "📊 테스트 환경 상태:"
	@docker compose --profile test ps
	@echo ""
	@echo "📊 Mock 서비스 헬스 체크:"
	@echo "   Mock Kiwoom API:"
	@wget -q -O- http://localhost:5116/ 2>/dev/null || echo "   ❌ 접속 실패"
	@echo "   Mock WebSocket:"
	@wget -q -O- http://localhost:5117/health 2>/dev/null || echo "   ❌ 접속 실패"

