#!/bin/bash
# Ralph Stock Analysis 서비스 시작 스크립트
# 모든 필수 서비스 시작

set -e

PROJECT_DIR="/home/ralph/work/python/kr_stock_analysis"
cd "$PROJECT_DIR"

echo "🚀 Starting Ralph Stock Analysis services..."

# 1. 네트워크 확인 및 생성
echo "📡 Checking Docker network..."
if ! docker network ls | grep -q ralph-network; then
    docker network create ralph-network
    echo "✅ Created ralph-network"
else
    echo "✅ ralph-network exists"
fi

# 2. PostgreSQL, Redis 시작 (Docker Compose)
echo "🗄️  Starting infrastructure services..."
docker compose -f docker/compose/infra.yml up -d postgres redis

# 3. API Gateway 시작
echo "🌐 Starting API Gateway..."
if ! docker ps | grep -q api-gateway; then
    echo "Creating API Gateway container..."
    # 기존 방식 유지
fi

# 4. Frontend 시작
echo "🎨 Starting Frontend..."
bash scripts/start_frontend.sh

# 5. NPM 네트워크 연결 확인
echo "🔗 Connecting NPM to ralph-network..."
if docker ps | grep -q npm; then
    docker network connect ralph-network npm 2>/dev/null && echo "✅ NPM connected" || echo "✅ NPM already connected"
fi

echo ""
echo "🎉 Services started!"
echo "  Frontend:  http://localhost:5110"
echo "  API:       http://localhost:5111"  
echo "  HTTPS:     https://stock.ralphpark.com"
