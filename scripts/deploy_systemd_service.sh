#!/bin/bash
###############################################################################
# Ralph Stock Analysis - systemd 서비스 배포 스크립트
###############################################################################
#
# 기능:
#   1. systemd 서비스 파일 설치
#   2. NPM 컨테이너를 ralph-network에 연결
#   3. 서비스 자동 시작 설정
#
# 사용법:
#   sudo bash scripts/deploy_systemd_service.sh
#
###############################################################################

set -e  # 오류 발생 시 중단

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

# 프로젝트 경로 (스크립트 위치 기반)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_FILE="${PROJECT_DIR}/systemd/ralph-stock.service"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_NAME="ralph-stock.service"

log_info "=== Ralph Stock Analysis - systemd 서비스 배포 ==="
echo ""

# 1. root 권한 확인
if [[ $EUID -ne 0 ]]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    log_info "사용법: sudo bash $0"
    exit 1
fi

# 2. 서비스 파일 존재 확인
if [[ ! -f "$SERVICE_FILE" ]]; then
    log_error "서비스 파일을 찾을 수 없습니다: $SERVICE_FILE"
    exit 1
fi

log_info "1. systemd 서비스 파일 설치..."

# 3. 기존 서비스 백업
if [[ -f "${SYSTEMD_DIR}/${SERVICE_NAME}" ]]; then
    log_warn "기존 서비스 파일 발견, 백업 생성..."
    cp "${SYSTEMD_DIR}/${SERVICE_NAME}" "${SYSTEMD_DIR}/${SERVICE_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# 4. 서비스 파일 복사
cp "$SERVICE_FILE" "${SYSTEMD_DIR}/${SERVICE_NAME}"
chmod 644 "${SYSTEMD_DIR}/${SERVICE_NAME}"
log_info "   서비스 파일 설치 완료: ${SYSTEMD_DIR}/${SERVICE_NAME}"

# 5. systemd 재로드
log_info "2. systemd 데몬 재로드..."
systemctl daemon-reload

# 6. Docker 네트워크 확인/생성
log_info "3. Docker 네트워크 확인..."
if docker network inspect ralph-network >/dev/null 2>&1; then
    log_info "   ralph-network 이미 존재"
else
    log_info "   ralph-network 생성 중..."
    docker network create ralph-network
    log_info "   ralph-network 생성 완료"
fi

# 7. NPM 컨테이너 네트워크 연결
log_info "4. Nginx Proxy Manager 네트워크 연결..."

# NPM 컨테이너 이름 찾기 (가능한 이름들)
NPM_CONTAINERS=("npm" "nginx-proxy-manager" "nginxproxymanager" "Nginx-Proxy-Manager")
NPM_CONTAINER=""

for name in "${NPM_CONTAINERS[@]}"; do
    if docker inspect "$name" >/dev/null 2>&1; then
        NPM_CONTAINER="$name"
        break
    fi
done

if [[ -z "$NPM_CONTAINER" ]]; then
    log_warn "   NPM 컨테이너를 찾을 수 없습니다 (실행 중이 아님)"
    log_warn "   NPM 컨테이너가 시작된 후 다음 명령어로 네트워크 연결:"
    log_warn "   docker network connect ralph-network <npm-container-name>"
else
    # 이미 연결되어 있는지 확인
    if docker network inspect ralph-network --format='{{range .Containers}}{{.Name}} {{end}}' | grep -q "^${NPM_CONTAINER} "; then
        log_info "   NPM 컨테이너가 이미 ralph-network에 연결됨"
    else
        log_info "   NPM 컨테이너(${NPM_CONTAINER})를 ralph-network에 연결 중..."
        if docker network connect ralph-network "$NPM_CONTAINER" 2>/dev/null; then
            log_info "   NPM 컨테이너 네트워크 연결 완료"
        else
            log_warn "   NPM 컨테이너 네트워크 연결 실패 (이미 연결되어 있을 수 있음)"
        fi
    fi
fi

# 8. 서비스 자동 시작 설정
log_info "5. 서비스 자동 시작 설정..."
systemctl enable "$SERVICE_NAME"
log_info "   부팅 시 자동 시작이 활성화되었습니다"

# 9. 서비스 시작 (이미 실행 중이면 재시작)
log_info "6. 서비스 시작..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "   서비스가 이미 실행 중입니다. 재시작합니다..."
    systemctl restart "$SERVICE_NAME"
else
    systemctl start "$SERVICE_NAME"
fi

# 10. 상태 확인
sleep 3
echo ""
log_info "=== 배포 완료 ==="
echo ""

if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "✅ 서비스 상태: 실행 중"
    echo ""
    log_info "컨테이너 상태:"
    docker ps --filter "network=ralph-network" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
else
    log_error "❌ 서비스 시작 실패"
    echo ""
    log_info "로그 확인:"
    log_info "   sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi

echo ""
log_info "=== 관리 명령어 ==="
echo "   상태 확인:  sudo systemctl status ${SERVICE_NAME}"
echo "   재시작:     sudo systemctl restart ${SERVICE_NAME}"
echo "   중지:       sudo systemctl stop ${SERVICE_NAME}"
echo "   로그 보기:  sudo journalctl -u ${SERVICE_NAME} -f"
echo "   컨테이너 로그: docker compose logs -f --tail=100"
echo ""
