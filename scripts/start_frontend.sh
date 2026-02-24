#!/bin/bash
# Frontend 서비스 시작 스크립트
# 포트 매핑 문제 영구 해결

set -e

echo "🚀 Starting Frontend service..."

# 기존 컨테이너 중지 및 삭제
if docker ps -a | grep -q frontend; then
    echo "Stopping existing frontend container..."
    docker stop frontend 2>/dev/null || true
    docker rm frontend 2>/dev/null || true
fi

# 네트워크 확인
if ! docker network ls | grep -q ralph-network; then
    echo "Creating ralph-network..."
    docker network create ralph-network
fi

# Frontend 컨테이너 실행
echo "Starting frontend container..."
docker run -d \
    --name frontend \
    --network ralph-network \
    -p 5110:5110 \
    -v /home/ralph/work/python/kr_stock_analysis/frontend:/app/frontend:delegated \
    -v /home/ralph/work/python/kr_stock_analysis/frontend/node_modules:/app/node_modules \
    -w /app/frontend \
    -e NODE_ENV=development \
    --restart unless-stopped \
    node:20-alpine \
    sh -c "npm install && npm run dev"

# NPM을 ralph-network에 연결 (선택 사항)
# 이렇게 하면 NPM이 컨테이너 이름으로 접속 가능
if docker ps | grep -q npm; then
    echo "Connecting NPM to ralph-network..."
    docker network connect ralph-network npm 2>/dev/null && echo "✅ NPM connected to ralph-network" || echo "⚠️ NPM already connected or failed"
fi

echo ""
echo "✅ Frontend service started!"
echo "   URL: http://localhost:5110"
echo "   Container: frontend"
echo "   Network: ralph-network"
echo ""

# 헬스 체크
echo "Waiting for frontend to be ready..."
sleep 15

if curl -sf http://localhost:5110 > /dev/null; then
    echo "✅ Frontend is ready!"
else
    echo "⚠️ Frontend may still be starting..."
    echo "   Check logs: docker logs frontend"
fi
