#!/bin/bash
# 서비스 재시작 스크립트 (서버 재부팅 후 실행)
# 사용법: bash scripts/start_services.sh

set -e

PROJECT_DIR="/home/ralph/work/python/kr_stock_analysis"
cd "$PROJECT_DIR"

echo "🚀 Ralph Stock Analysis 서비스 시작"
echo "=================================="
echo ""

# 1. Docker가 실행 중인지 확인
echo "1. Docker 상태 확인..."
if ! docker info &> /dev/null; then
    echo "   ⚠️  Docker가 실행 중이 아닙니다. 시작합니다..."
    sudo systemctl start docker
    echo "   ✅ Docker 시작 완료"
    sleep 3
else
    echo "   ✅ Docker 실행 중"
fi

# 2. Docker Compose로 서비스 시작
echo ""
echo "2. Docker Compose 서비스 시작 (prod profile)..."
docker compose --profile prod up -d

echo ""
echo "3. 서비스 상태 확인..."
docker compose ps

echo ""
echo "4. 컨테이너 상태..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "✅ 서비스 시작 완료!"
echo ""
echo "접속 확인:"
echo "  Frontend:  http://112.219.120.75:5110"
echo "  API:       http://112.219.120.75:5111/health"
echo "  Website:   https://stock.ralphpark.com/"
echo ""
echo "로그 확인:"
echo "  docker compose logs -f"
