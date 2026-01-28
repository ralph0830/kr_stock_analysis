#!/bin/bash
# KR Stock 시스템 전체 시작 스크립트

set -e

echo "========================================="
echo "  KR Stock Analysis System 시작"
echo "========================================="
echo ""

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 인프라 상태 확인
echo "1️⃣  인프라 상태 확인..."
echo ""

if docker compose ps postgres | grep -q "Up"; then
    log_info "✅ PostgreSQL 실행 중"
else
    log_warn "⚠️  PostgreSQL 미실행. 시작 중..."
    docker compose up -d postgres
fi

if docker compose ps redis | grep -q "Up"; then
    log_info "✅ Redis 실행 중"
else
    log_warn "⚠️  Redis 미실행. 시작 중..."
    docker compose up -d redis
fi

echo ""
echo "2️⃣  서비스 시작 준비..."
echo ""

# PID 파일 디렉토리
mkdir -p .pids

# 포트 설정
API_GATEWAY_PORT=5111
VCP_SCANNER_PORT=5112
SIGNAL_ENGINE_PORT=5113
FRONTEND_PORT=5110

# 로그 디렉토리
mkdir -p logs

# 서비스 중지 함수
stop_service() {
    local name=$1
    local pid_file=".pids/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "🛑 중지: $name (PID: $pid)"
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    fi
}

# 기존 서비스 중지
echo "기존 서비스 중지..."
stop_service "api-gateway"
stop_service "vcp-scanner"
stop_service "signal-engine"
stop_service "frontend"

sleep 2

# 3. API Gateway 시작
echo ""
echo "3️⃣  API Gateway 시작 (포트: $API_GATEWAY_PORT)..."
nohup uv run uvicorn services.api_gateway.main:app \
    --host 0.0.0.0 \
    --port $API_GATEWAY_PORT \
    --reload > logs/api-gateway.log 2>&1 &
echo $! > .pids/api-gateway.pid
log_info "✅ API Gateway 시작됨"
sleep 5

# Health check
log_info "🔍 API Gateway health check..."
if curl -s http://localhost:$API_GATEWAY_PORT/health > /dev/null; then
    log_info "✅ API Gateway health check 통과"
else
    log_error "❌ API Gateway health check 실패"
    cat logs/api-gateway.log
fi

# 4. VCP Scanner 시작
echo ""
echo "4️⃣  VCP Scanner 시작 (포트: $VCP_SCANNER_PORT)..."
nohup uv run uvicorn services.vcp_scanner.main:app \
    --host 0.0.0.0 \
    --port $VCP_SCANNER_PORT \
    --reload > logs/vcp-scanner.log 2>&1 &
echo $! > .pids/vcp-scanner.pid
log_info "✅ VCP Scanner 시작됨"
sleep 2

# 5. Signal Engine 시작
echo ""
echo "5️⃣  Signal Engine 시작 (포트: $SIGNAL_ENGINE_PORT)..."
nohup uv run uvicorn services.signal_engine.main:app \
    --host 0.0.0.0 \
    --port $SIGNAL_ENGINE_PORT \
    --reload > logs/signal-engine.log 2>&1 &
echo $! > .pids/signal-engine.pid
log_info "✅ Signal Engine 시작됨"
sleep 2

# 6. Frontend 시작
echo ""
echo "6️⃣  Frontend 시작 (포트: $FRONTEND_PORT)..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
echo $! > ../.pids/frontend.pid
cd ..
log_info "✅ Frontend 시작됨"
sleep 3

# 요약
echo ""
echo "========================================="
echo "  ✅ 모든 서비스 시작 완료"
echo "========================================="
echo ""
echo "📍 서비스 주소:"
echo ""
echo "  🌐 Frontend (Next.js):"
echo "     - 로컬:   http://localhost:$FRONTEND_PORT"
echo "     - 외부:   http://112.219.120.75:$FRONTEND_PORT"
echo ""
echo "  🔌 API Gateway (FastAPI):"
echo "     - 로컬:   http://localhost:$API_GATEWAY_PORT"
echo "     - 외부:   http://112.219.120.75:$API_GATEWAY_PORT"
echo "     - Swagger: http://112.219.120.75:$API_GATEWAY_PORT/docs"
echo "     - ReDoc:  http://112.219.120.75:$API_GATEWAY_PORT/redoc"
echo ""
echo "  📡 VCP Scanner:"
echo "     - 로컬:   http://localhost:$VCP_SCANNER_PORT"
echo "     - 외부:   http://112.219.120.75:$VCP_SCANNER_PORT"
echo ""
echo "  🎯 Signal Engine:"
echo "     - 로컬:   http://localhost:$SIGNAL_ENGINE_PORT"
echo "     - 외부:   http://112.219.120.75:$SIGNAL_ENGINE_PORT"
echo ""
echo "📋 로그 파일:"
echo "  - API Gateway:   logs/api-gateway.log"
echo "  - VCP Scanner:   logs/vcp-scanner.log"
echo "  - Signal Engine: logs/signal-engine.log"
echo "  - Frontend:      logs/frontend.log"
echo ""
echo "🛑 서비스 중지:"
echo "  ./scripts/stop_all.sh"
echo ""
echo "📊 로그 확인:"
echo "  tail -f logs/api-gateway.log"
echo ""
