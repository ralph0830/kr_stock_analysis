#!/bin/bash
# Ralph Stock Analysis - systemd 서비스 배포 스크립트
#
# 사용법:
#   sudo bash scripts/deploy-systemd-service.sh [--install|--uninstall|--status|--enable|--disable]
#
# 기능:
#   systemd 서비스 파일을 생성하고 등록하여 서버 재부팅 시 자동 시작되도록 설정

set -e

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 경로 설정
PROJECT_DIR="/home/ralph/work/python/kr_stock_analysis"
SERVICE_NAME="ralph-stock"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TEMPLATE_FILE="${PROJECT_DIR}/templates/${SERVICE_NAME}.service"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 루트 권한 확인
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "이 스크립트는 루트 권한으로 실행해야 합니다."
        echo "사용법: sudo $0 $@"
        exit 1
    fi
}

# systemd 서비스 설치
install_service() {
    log_info "systemd 서비스 설치를 시작합니다..."

    # 템플릿 파일 확인
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        log_error "템플릿 파일을 찾을 수 없습니다: $TEMPLATE_FILE"
        exit 1
    fi

    # 서비스 파일 복사
    log_info "서비스 파일 복사: $TEMPLATE_FILE → $SERVICE_FILE"
    cp "$TEMPLATE_FILE" "$SERVICE_FILE"

    # systemd 리로드
    log_info "systemd 데몬 리로드..."
    systemctl daemon-reload

    # 서비스 활성화 (부팅 시 자동 시작)
    log_info "서비스 활성화 (부팅 시 자동 시작)..."
    systemctl enable "$SERVICE_NAME"

    # 서비스 상태 확인
    log_info "서비스 상태 확인..."
    systemctl status "$SERVICE_NAME" --no-pager || true

    echo ""
    log_info "✅ systemd 서비스 설치 완료!"
    echo ""
    echo "사용 가능한 명령어:"
    echo "  sudo systemctl start $SERVICE_NAME     # 서비스 시작"
    echo "  sudo systemctl stop $SERVICE_NAME      # 서비스 중지"
    echo "  sudo systemctl restart $SERVICE_NAME   # 서비스 재시작"
    echo "  sudo systemctl status $SERVICE_NAME    # 서비스 상태 확인"
    echo "  sudo journalctl -u $SERVICE_NAME -f    # 로그 실시간 보기"
}

# systemd 서비스 제거
uninstall_service() {
    log_info "systemd 서비스 제거를 시작합니다..."

    # 서비스 중지 및 비활성화
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "서비스 중지..."
        systemctl stop "$SERVICE_NAME"
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log_info "서비스 비활성화..."
        systemctl disable "$SERVICE_NAME"
    fi

    # 서비스 파일 삭제
    if [[ -f "$SERVICE_FILE" ]]; then
        log_info "서비스 파일 삭제: $SERVICE_FILE"
        rm "$SERVICE_FILE"
        systemctl daemon-reload
    fi

    log_info "✅ systemd 서비스 제거 완료!"
}

# 서비스 상태 확인
show_status() {
    log_info "서비스 상태 확인..."
    systemctl status "$SERVICE_NAME" --no-pager || true

    echo ""
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log_info "부팅 시 자동 시작: ✅ 활성화"
    else
        log_warn "부팅 시 자동 시작: ❌ 비활성화"
    fi

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "현재 상태: ✅ 실행 중"
    else
        log_warn "현재 상태: ❌ 중지됨"
    fi
}

# 서비스 활성화
enable_service() {
    log_info "서비스 활성화 (부팅 시 자동 시작)..."
    systemctl enable "$SERVICE_NAME"
    log_info "✅ 활성화 완료"
}

# 서비스 비활성화
disable_service() {
    log_info "서비스 비활성화..."
    systemctl disable "$SERVICE_NAME"
    log_info "✅ 비활성화 완료"
}

# 서비스 시작
start_service() {
    log_info "서비스 시작..."
    systemctl start "$SERVICE_NAME"
    log_info "✅ 시작 완료"
}

# 서비스 중지
stop_service() {
    log_info "서비스 중지..."
    systemctl stop "$SERVICE_NAME"
    log_info "✅ 중지 완료"
}

# 도움말
show_help() {
    cat << EOF
Ralph Stock Analysis - systemd 서비스 배포 스크립트

사용법:
  sudo bash $0 [옵션]

옵션:
  --install, -i     systemd 서비스 설치 (기본값)
  --uninstall, -u   systemd 서비스 제거
  --status, -s      서비스 상태 확인
  --enable, -e      부팅 시 자동 시작 활성화
  --disable, -d     부팅 시 자동 시작 비활성화
  --start           서비스 시작
  --stop            서비스 중지
  --help, -h        도움말 표시

예시:
  # 서비스 설치 및 활성화
  sudo bash $0 --install

  # 서비스 상태 확인
  sudo bash $0 --status

  # 서비스 수동 시작
  sudo bash $0 --start

  # 서비스 제거
  sudo bash $0 --uninstall
EOF
}

# 메인
main() {
    local command="${1:-install}"

    case "$command" in
        --install|-i)
            check_root "$@"
            install_service
            ;;
        --uninstall|-u)
            check_root "$@"
            uninstall_service
            ;;
        --status|-s)
            show_status
            ;;
        --enable|-e)
            check_root "$@"
            enable_service
            ;;
        --disable|-d)
            check_root "$@"
            disable_service
            ;;
        --start)
            check_root "$@"
            start_service
            ;;
        --stop)
            check_root "$@"
            stop_service
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "알 수 없는 명령어: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
