#!/bin/bash
###############################################################################
# Nginx Proxy Manager - ralph-network 연결 스크립트
###############################################################################
#
# NPM 컨테이너를 ralph-network에 연결하여
# Docker Compose 서비스와 통신할 수 있도록 합니다.
#
# 사용법:
#   sudo bash scripts/connect_npm_network.sh
#
###############################################################################

set -e

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

NETWORK_NAME="ralph-network"

# NPM 컨테이너 이름 후보들 (Docker Compose 설정, 이미지 이름 등 다양한 경우)
NPM_CONTAINER_NAMES=(
    "npm"                    # 가장 일반적인 이름
    "nginx-proxy-manager"    # 공식 이름
    "nginxproxymanager"      # 대소문자 없는 버전
    "Nginx-Proxy-Manager"    # 대문자 포함
    "nginxproxymanager-app"  # 일부 Docker Compose 설정
    "npm-app"                # 일부 Docker Compose 설정
)

log_info "=== NPM 네트워크 연결 스크립트 ==="
echo ""

# root 권한 확인
if [[ $EUID -ne 0 ]]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    log_info "사용법: sudo bash $0"
    exit 1
fi

# 1. 네트워크 존재 확인
log_info "1. Docker 네트워크 확인..."
if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    log_info "   $NETWORK_NAME 네트워크가 없습니다. 생성 중..."
    docker network create "$NETWORK_NAME"
    log_info "   네트워크 생성 완료"
else
    log_info "   $NETWORK_NAME 네트워크가 존재합니다"
fi

# 2. NPM 컨테이너 찾기
log_info "2. Nginx Proxy Manager 컨테이너 검색 중..."
NPM_CONTAINER=""

# 먼저 Docker로 실행 중인 모든 컨테이너에서 NPM 관련 컨테이너 찾기
RUNNING_NPM_CONTAINERS=$(docker ps --format "{{.Names}}" | grep -iE "(npm|nginx.*proxy|proxy.*manager)" || true)

if [[ -n "$RUNNING_NPM_CONTAINERS" ]]; then
    log_info "   발견된 NPM 관련 컨테이너:"
    echo "$RUNNING_NPM_CONTAINERS" | while read -r container; do
        echo "     - $container"
    done
    # 첫 번째 컨테이너 사용
    NPM_CONTAINER=$(echo "$RUNNING_NPM_CONTAINERS" | head -n 1)
    log_info "   선택된 컨테이너: $NPM_CONTAINER"
else
    # 미리 정의된 이름들로 시도
    for name in "${NPM_CONTAINER_NAMES[@]}"; do
        if docker inspect "$name" >/dev/null 2>&1; then
            NPM_CONTAINER="$name"
            break
        fi
    done
fi

if [[ -z "$NPM_CONTAINER" ]]; then
    log_error "   NPM 컨테이너를 찾을 수 없습니다!"
    echo ""
    log_info "다음 명령어로 실행 중인 컨테이너를 확인하세요:"
    log_info "   docker ps"
    echo ""
    log_info "NPM 컨테이너 이름을 찾은 후 수동으로 연결:"
    log_info "   sudo docker network connect $NETWORK_NAME <npm-container-name>"
    exit 1
fi

# 3. 현재 네트워크 연결 상태 확인
log_info "3. 네트워크 연결 상태 확인..."
if docker network inspect "$NETWORK_NAME" --format='{{range .Containers}}{{.Name}} {{end}}' | grep -q "^${NPM_CONTAINER} "; then
    log_warn "   $NPM_CONTAINER 컨테이너가 이미 $NETWORK_NAME에 연결되어 있습니다"
    echo ""
    log_info "연결된 네트워크 목록:"
    docker inspect "$NPM_CONTAINER" --format='{{range $net := .NetworkSettings.Networks}}{{$net.NetworkID}} {{end}}' | while read -r net_id; do
        net_name=$(docker network inspect "$net_id" --format='{{.Name}}' 2>/dev/null || echo "$net_id")
        echo "     - $net_name"
    done
    exit 0
fi

# 4. 네트워크 연결
log_info "4. 네트워크 연결 중..."
log_info "   컨테이너: $NPM_CONTAINER"
log_info "   네트워크: $NETWORK_NAME"

if docker network connect "$NETWORK_NAME" "$NPM_CONTAINER" 2>/dev/null; then
    log_info "   ✅ 네트워크 연결 성공!"
else
    # 실패 시 상세 오류 확인
    ERROR_OUTPUT=$(docker network connect "$NETWORK_NAME" "$NPM_CONTAINER" 2>&1 || true)
    log_error "   네트워크 연결 실패"
    echo "$ERROR_OUTPUT"
    exit 1
fi

# 5. 연결 후 상태 확인
log_info "5. 연결 상태 재확인..."
if docker network inspect "$NETWORK_NAME" --format='{{range .Containers}}{{.Name}} {{end}}' | grep -q "^${NPM_CONTAINER} "; then
    log_info "   ✅ 연결 확인 완료"
else
    log_error "   연결 확인 실패 (수동 확인 필요)"
fi

# 6. 네트워크 내 IP 주소 표시
NPM_IP=$(docker inspect "$NPM_CONTAINER" --format="{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || echo "알 수 없음")
log_info "   NPM IP (ralph-network 내): $NPM_IP"

# 7. ralph-network에 연결된 다른 컨테이너 표시
echo ""
log_info "ralph-network에 연결된 컨테이너:"
docker network inspect "$NETWORK_NAME" --format='{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}' | sort || echo "  (없음)"

echo ""
log_info "=== 연결 완료 ==="
echo ""
log_info "이제 NPM에서 Docker Compose 서비스에 접근할 수 있습니다."
log_info "포워드 호스트 설정:"
log_info "   - 외부 접근용: 172.17.0.1 (Docker 기본 게이트웨이)"
log_info "   - 내부 네트워크용: 컨테이너 이름 (api-gateway, frontend 등)"
