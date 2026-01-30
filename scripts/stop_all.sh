#!/bin/bash
# Ralph Stock 시스템 전체 중지 스크립트

set -e

echo "========================================="
echo "  Ralph Stock Analysis System 중지"
echo "========================================="
echo ""

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# PID 파일 디렉토리
mkdir -p .pids

# 서비스 목록
services=("api-gateway" "vcp-scanner" "signal-engine" "frontend")

# 서비스 중지
for service in "${services[@]}"; do
    pid_file=".pids/${service}.pid"

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")

        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "🛑 중지: $service (PID: $pid)"
            kill "$pid" 2>/dev/null || true
            sleep 1

            # 강제 종료 (아직 실행 중인 경우)
            if ps -p "$pid" > /dev/null 2>&1; then
                log_info "   강제 종료: $service"
                kill -9 "$pid" 2>/dev/null || true
            fi
        else
            log_info "⚠️  이미 중지됨: $service"
        fi

        rm -f "$pid_file"
    else
        log_info "⚠️  PID 파일 없음: $service"
    fi
done

# npm dev 프로세스 정리 (백업)
echo ""
pkill -f "next dev" || true

echo ""
echo "========================================="
echo "  ✅ 모든 서비스 중지 완료"
echo "========================================="
echo ""
