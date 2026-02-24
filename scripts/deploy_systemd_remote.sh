#!/bin/bash
###############################################################################
# Ralph Stock Analysis - 원격 서버 배포 스크립트
###############################################################################
#
# 로컬에서 생성한 파일들을 원격 서버로 전송하고 배포합니다.
#
# 사용법:
#   bash scripts/deploy_systemd_remote.sh <ssh-host>
#
# 예시:
#   bash scripts/deploy_systemd_remote.sh user@112.219.120.75
#
###############################################################################

set -e

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${BLUE}[STEP]${NC} $1"; }

# 프로젝트 경로
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# SSH 호스트 확인
if [[ -z "$1" ]]; then
    log_error "SSH 호스트를 지정해주세요."
    echo ""
    echo "사용법:"
    echo "  bash $0 <ssh-host>"
    echo ""
    echo "예시:"
    echo "  bash $0 user@112.219.120.75"
    exit 1
fi

SSH_HOST="$1"
REMOTE_PROJECT_DIR="/home/ralph/work/python/kr_stock_analysis"

log_info "=== Ralph Stock Analysis - 원격 배포 ==="
echo ""
log_info "SSH 호스트: $SSH_HOST"
log_info "원격 경로: $REMOTE_PROJECT_DIR"
echo ""

# 1. 연결 테스트
log_header "1. SSH 연결 테스트..."
if ssh "$SSH_HOST" "echo '연결 성공'" >/dev/null 2>&1; then
    log_info "   ✅ SSH 연결 성공"
else
    log_error "   ❌ SSH 연결 실패"
    log_info "   SSH 키가 설정되어 있는지 확인하세요"
    exit 1
fi

# 2. 파일 전송
log_header "2. 배포 파일 전송..."

# systemd 서비스 파일
log_info "   systemd/ralph-stock.service 전송..."
scp "${PROJECT_DIR}/systemd/ralph-stock.service" "${SSH_HOST}:${REMOTE_PROJECT_DIR}/systemd/"

# 스크립트 파일 전송
log_info "   스크립트 파일 전송..."
scp "${PROJECT_DIR}/scripts/deploy_systemd_service.sh" "${SSH_HOST}:${REMOTE_PROJECT_DIR}/scripts/"
scp "${PROJECT_DIR}/scripts/connect_npm_network.sh" "${SSH_HOST}:${REMOTE_PROJECT_DIR}/scripts/"
scp "${PROJECT_DIR}/scripts/verify_deployment.sh" "${SSH_HOST}:${REMOTE_PROJECT_DIR}/scripts/"

# 권한 설정
log_info "   스크립트 실행 권한 설정..."
ssh "$SSH_HOST" "chmod +x ${REMOTE_PROJECT_DIR}/scripts/deploy_systemd_service.sh"
ssh "$SSH_HOST" "chmod +x ${REMOTE_PROJECT_DIR}/scripts/connect_npm_network.sh"
ssh "$SSH_HOST" "chmod +x ${REMOTE_PROJECT_DIR}/scripts/verify_deployment.sh"

log_info "   ✅ 파일 전송 완료"

# 3. systemd 서비스 설치
log_header "3. systemd 서비스 설치..."
ssh "$SSH_HOST" "sudo bash ${REMOTE_PROJECT_DIR}/scripts/deploy_systemd_service.sh"

# 4. 배포 검증
log_header "4. 배포 검증..."
ssh "$SSH_HOST" "bash ${REMOTE_PROJECT_DIR}/scripts/verify_deployment.sh"

# 5. 완료
echo ""
log_info "=== 배포 완료 ==="
echo ""
log_info "서버 재부팅 후 자동 시작이 활성화되었습니다."
echo ""
log_info "원격 서버 관리 명령어:"
echo "  ssh $SSH_HOST 'sudo systemctl status ralph-stock'"
echo "  ssh $SSH_HOST 'sudo journalctl -u ralph-stock -f'"
echo "  ssh $SSH_HOST 'docker compose --profile prod logs -f'"
echo ""
log_info "웹사이트 접속:"
echo "  https://stock.ralphpark.com"
echo ""
