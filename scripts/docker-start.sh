#!/bin/bash
# ============================================================================
# Ralph Stock Analysis - Docker 시작 스크립트
# ============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로고 출력
print_logo() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║          Ralph Stock Analysis - Docker Manager                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 도움말
show_help() {
    cat << EOF
사용법:
  ./scripts/docker-start.sh [명령]

명령어:
  up        모든 서비스 시작 (기본)
  down      모든 서비스 중지 및 삭제
  restart   모든 서비스 재시작
  logs      서비스 로그 보기
  status    서비스 상태 확인
  build     Docker 이미지 재빌드
  clean     전체 삭제 (volumes 포함)

예시:
  ./scripts/docker-start.sh up          # 전체 시작
  ./scripts/docker-start.sh up infra    # 인프라만 시작
  ./scripts/docker-start.sh logs api     # API 로그 확인
  ./scripts/docker-start.sh clean       # 전체 삭제

EOF
}

# 메시지 출력
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Docker Compose 실행 확인
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker가 설치되지 않았습니다."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        error "Docker 데몬이 실행 중이 아닙니다."
        exit 1
    fi

    success "Docker 실행 중"
}

# 인프라 서비스만 시작
start_infra() {
    info "인프라 서비스 시작 (PostgreSQL, Redis)..."
    docker compose up -d postgres redis
    success "인프라 서비스 시작 완료"
}

# 전체 서비스 시작
start_all() {
    info "전체 서비스 시작 중..."

    # 1단계: 인프라
    info "[1/4] 인프라 서비스 시작..."
    docker compose up -d postgres redis

    # 인프라 헬스체크 대기
    info "인프라 헬스체크 대기..."
    sleep 5

    # 2단계: 백엔드 서비스
    info "[2/4] 백엔드 서비스 시작..."
    docker compose up -d api-gateway vcp-scanner signal-engine chatbot

    # 3단계: 백그라운드 작업
    info "[3/4] 백그라운드 작업 시작..."
    docker compose up -d celery-worker celery-beat flower

    # 4단계: 프론트엔드
    info "[4/4] 프론트엔드 시작..."
    docker compose up -d frontend

    echo ""
    success "전체 서비스 시작 완료!"
    echo ""
    show_urls
}

# URL 표시
show_urls() {
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  서비스 URL${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "  🌐 Frontend (Next.js):     ${BLUE}http://localhost:5110${NC}"
    echo -e "  🚪 API Gateway:           ${BLUE}http://localhost:5111${NC}"
    echo -e "  🔍 VCP Scanner:           ${BLUE}http://localhost:5112${NC}"
    echo -e "  📊 Signal Engine:         ${BLUE}http://localhost:5113${NC}"
    echo -e "  🤖 Chatbot:               ${BLUE}http://localhost:5114${NC}"
    echo -e "  🌻 Flower (Celery):       ${BLUE}http://localhost:5555${NC}"
    echo -e "  📦 PostgreSQL:            ${BLUE}localhost:5433${NC}"
    echo -e "  🔴 Redis:                 ${BLUE}localhost:6380${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
}

# 서비스 상태 확인
show_status() {
    info "서비스 상태 확인..."
    docker compose ps
}

# 로그 보기
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker compose logs -f --tail=100
    else
        docker compose logs -f --tail=100 "$service"
    fi
}

# 서비스 중지
stop_all() {
    info "모든 서비스 중지..."
    docker compose down
    success "서비스 중지 완료"
}

# 서비스 재시작
restart_all() {
    info "서비스 재시작..."
    docker compose restart
    success "서비스 재시작 완료"
    show_urls
}

# 이미지 재빌드
rebuild() {
    info "Docker 이미지 재빌드..."
    docker compose build --no-cache
    success "빌드 완료"
    info "서비스 재시작..."
    docker compose up -d
    success "재시작 완료"
    show_urls
}

# 전체 삭제
clean_all() {
    warn "⚠️  모든 컨테이너, 네트워크, 볼륨을 삭제합니다."
    read -p "정말 진행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "삭제 진행 중..."
        docker compose down -v
        docker system prune -f
        success "삭제 완료"
    else
        info "취소되었습니다."
    fi
}

# 메인
main() {
    print_logo
    check_docker

    case "${1:-up}" in
        up)
            if [ "$2" == "infra" ]; then
                start_infra
            else
                start_all
            fi
            ;;
        down|stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        logs)
            show_logs "$2"
            ;;
        status)
            show_status
            ;;
        build)
            rebuild
            ;;
        clean)
            clean_all
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "알 수 없는 명령어: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
