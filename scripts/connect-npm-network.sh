#!/bin/bash
# Nginx Proxy Manager 네트워크 연결 스크립트
#
# NPM 컨테이너를 ralph-network에 연결하여
# Docker 컨테이너 간 통신을 가능하게 합니다.

set -e

NETWORK_NAME="ralph-network"
NPM_CONTAINER_NAME="npm"

echo "🔗 NPM 네트워크 연결 확인 및 설정..."
echo ""

# 1. 네트워크 존재 확인
echo "1. 네트워크 확인..."
if docker network ls | grep -q "$NETWORK_NAME"; then
    echo "   ✅ $NETWORK_NAME 네트워크 존재"
else
    echo "   ⚠️  $NETWORK_NAME 네트워크가 없습니다. 생성합니다..."
    docker network create "$NETWORK_NAME"
    echo "   ✅ $NETWORK_NAME 네트워크 생성 완료"
fi

# 2. NPM 컨테이너 확인
echo ""
echo "2. NPM 컨테이너 확인..."
NPM_CONTAINERS=$(docker ps --filter "name=npm" --format "{{.Names}}")
if [[ -z "$NPM_CONTAINERS" ]]; then
    echo "   ⚠️  NPM 컨테이너가 실행 중이 아닙니다."
    echo "   먼저 NPM을 시작해주세요."
    exit 1
fi

# 여러 NPM 컨테이너가 있을 경우 첫 번째 것 사용
NPM_CONTAINER=$(echo "$NPM_CONTAINERS" | head -n 1)
echo "   ✅ NPM 컨테이너 발견: $NPM_CONTAINER"

# 3. 현재 네트워크 연결 상태 확인
echo ""
echo "3. 현재 네트워크 연결 상태..."
CONNECTED_NETWORKS=$(docker inspect "$NPM_CONTAINER" --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}')
if echo "$CONNECTED_NETWORKS" | grep -q "$NETWORK_NAME"; then
    echo "   ✅ 이미 $NETWORK_NAME에 연결되어 있습니다."
else
    echo "   ⚠️  $NETWORK_NAME에 연결되어 있지 않습니다. 연결합니다..."

    # 4. 네트워크 연결
    echo ""
    echo "4. 네트워크 연결..."
    docker network connect "$NETWORK_NAME" "$NPM_CONTAINER"
    echo "   ✅ $NETWORK_NAME에 연결 완료"
fi

# 5. 연결 상태 최종 확인
echo ""
echo "5. 최종 연결 상태..."
docker inspect "$NPM_CONTAINER" --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}: {{$v.IPAddress}}{{"\n"}}{{end}}'

echo ""
echo "✅ NPM 네트워크 연결 설정 완료!"
echo ""
echo "연결된 네트워크:"
docker network inspect "$NETWORK_NAME" --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || echo "   (연결된 컨테이너 없음)"
