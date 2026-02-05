#!/bin/bash
# Daytrading Scanner 배포 스크립트
# Daytrading Scanner 서비스를 프로덕션 환경에 배포합니다.

set -e

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  Daytrading Scanner 배포"
echo "========================================="
echo ""

# 1. Docker 이미지 빌드
echo "1️⃣  Docker 이미지 빌드..."
echo ""
log_info "Daytrading Scanner 이미지 빌드 중..."
docker compose -f docker/compose/docker-compose.prod.yml build daytrading-scanner

# 2. 기존 컨테이너 중지/재생성
echo ""
echo "2️⃣  컨테이너 배포..."
echo ""
log_info "기존 daytrading-scanner 컨테이너 중지..."
docker compose -f docker/compose/docker-compose.prod.yml stop daytrading-scanner || true

log_info "daytrading-scanner 컨테이너 제거..."
docker compose -f docker/compose/docker-compose.prod.yml rm -f daytrading-scanner || true

log_info "daytrading-scanner 컨테이너 시작..."
docker compose -f docker/compose/docker-compose.prod.yml up -d daytrading-scanner

# 3. 헬스 체크
echo ""
echo "3️⃣  헬스 체크..."
echo ""
sleep 3

log_info "Daytrading Scanner 헬스 체크..."
MAX_ATTEMPTS=10
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    if curl -s http://localhost:5115/health > /dev/null 2>&1; then
        log_info "✅ Daytrading Scanner health check 통과!"
        break
    else
        log_warn "⏳ 헬스 체크 실패... 재시도 ($ATTEMPT/$MAX_ATTEMPTS)"
        sleep 2
    fi
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    log_error "❌ Daytrading Scanner 헬스 체크 실패!"
    echo ""
    echo "📋 로그 확인:"
    docker compose -f docker/compose/docker-compose.prod.yml logs --tail=50 daytrading-scanner
    exit 1
fi

# 4. API Gateway 재시작 (의존 연결 확인)
echo ""
echo "4️⃣  API Gateway 재시작..."
echo ""
log_info "API Gateway 재시작 중..."
docker compose -f docker/compose/docker-compose.prod.yml restart api-gateway

sleep 3

log_info "API Gateway daytrading 프록시 확인..."
if curl -s http://localhost:5111/api/daytrading/signals > /dev/null 2>&1; then
    log_info "✅ API Gateway → Daytrading Scanner 프록시 확인!"
else
    log_error "❌ API Gateway 프록시 실패!"
    exit 1
fi

# 5. Nginx 설정 확인 (스크립트 실행)
echo ""
echo "5️⃣  Nginx 설정 확인..."
echo ""
log_info "NPM 프록시 설정 확인 중..."
python3 scripts/setup_npm_proxy.py

echo ""
echo "========================================="
echo "  ✅ 배포 완료"
echo "========================================="
echo ""
echo "📍 접속 가능 URL:"
echo ""
echo "  🌐 단타 추천 페이지:"
echo "     https://stock.ralphpark.com/custom-recommendation"
echo ""
echo "  🔌 Daytrading API:"
echo "     https://stock.ralphpark.com/api/daytrading/signals"
echo ""
echo "  📊 대시보드 (VCP만):"
echo "     https://stock.ralphpark.com/dashboard"
echo ""
echo "🧪 테스트 명령어:"
echo "  # Daytrading 시그널 조회"
echo "  curl https://stock.ralphpark.com/api/daytrading/signals"
echo ""
echo "  # 시장 스캔"
echo "  curl -X POST https://stock.ralphpark.com/api/daytrading/scan \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"market\":\"KOSPI\",\"limit\":5}'"
echo ""
