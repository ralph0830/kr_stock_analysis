#!/bin/bash
# Daytrading Scanner 롤백 스크립트
# Daytrading Scanner 서비스를 이전 상태로 복구합니다.

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
echo "  Daytrading Scanner 롤백"
echo "========================================="
echo ""

# 롤백 확인
read -p "정말로 Daytrading Scanner를 롤백하시겠습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "롤백이 취소되었습니다."
    exit 0
fi

# 1. Daytrading Scanner 컨테이너 중지/제거
echo "1️⃣  Daytrading Scanner 컨테이너 제거..."
echo ""
log_info "daytrading-scanner 컨테이너 중지..."
docker compose -f docker/compose/docker-compose.prod.yml stop daytrading-scanner || true

log_info "daytrading-scanner 컨테이너 제거..."
docker compose -f docker/compose/docker-compose.prod.yml rm -f daytrading-scanner || true

# 2. API Gateway에서 Daytrading 라우팅 제거 (백업)
echo ""
echo "2️⃣  API Gateway 라우팅 제거..."
echo ""
BACKUP_DIR="$PROJECT_ROOT/.backup/rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

log_info "API Gateway 라우터 백업..."
if [ -f "$PROJECT_ROOT/services/api_gateway/routes/daytrading.py" ]; then
    cp "$PROJECT_ROOT/services/api_gateway/routes/daytrading.py" "$BACKUP_DIR/"
    log_info "백업 완료: $BACKUP_DIR/daytrading.py"

    log_info "daytrading 라우터 제거..."
    rm "$PROJECT_ROOT/services/api_gateway/routes/daytrading.py"
fi

log_info "main.py 백업..."
if [ -f "$PROJECT_ROOT/services/api_gateway/main.py" ]; then
    cp "$PROJECT_ROOT/services/api_gateway/main.py" "$BACKUP_DIR/main.py.before-rollback"
fi

log_info "main.py에서 daytrading 라우터 주석 처리..."
# daytrading 관련 import와 router 주석 처리
sed -i.bak '/from .*daytrading import/s/^/# ROLLBACK: /' "$PROJECT_ROOT/services/api_gateway/main.py" || true
sed -i.bak '/app.include_router.*daytrading/s/^/# ROLLBACK: /' "$PROJECT_ROOT/services/api_gateway/main.py" || true

# 3. API Gateway 재시작
echo ""
echo "3️⃣  API Gateway 재시작..."
echo ""
log_info "API Gateway 재시작 중..."
docker compose -f docker/compose/docker-compose.prod.yml restart api-gateway

sleep 3

# 4. 롤백 확인
echo ""
echo "4️⃣  롤백 확인..."
echo ""

log_info "Daytrading 엔드포인트 확인 (실패해야 함)..."
if curl -s http://localhost:5111/api/daytrading/signals > /dev/null 2>&1; then
    log_warn "⚠️ Daytrading 엔드포인트가 여전히 응답합니다."
else
    log_info "✅ Daytrading 엔드포인트가 비활성화되었습니다."
fi

log_info "VCP 엔드포인트 확인 (정상 응답해야 함)..."
if curl -s http://localhost:5111/api/vcp/signals > /dev/null 2>&1; then
    log_info "✅ VCP 엔드포인트가 정상 작동합니다."
else
    log_error "❌ VCP 엔드포인트 오류!"
fi

echo ""
echo "========================================="
echo "  ✅ 롤백 완료"
echo "========================================="
echo ""
echo "📋 백업 파일 위치: $BACKUP_DIR"
echo ""
echo "🔄 복구 방법:"
echo "  1. 백업 파일에서 복원:"
echo "     cp $BACKUP_DIR/daytrading.py services/api_gateway/routes/"
echo "     cp $BACKUP_DIR/main.py.before-rollback services/api_gateway/main.py"
echo "  2. 재배포:"
echo "     bash scripts/deploy-daytrading.sh"
echo ""
