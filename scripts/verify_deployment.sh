#!/bin/bash
###############################################################################
# Ralph Stock Analysis - 배포 검증 스크립트
###############################################################################
#
# 배포 후 서비스 상태를 확인합니다.
#
# 사용법:
#   bash scripts/verify_deployment.sh
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
log_header() { echo -e "${BLUE}[CHECK]${NC} $1"; }

# 서비스 URL
SITE_URL="https://stock.ralphpark.com"
FRONTEND_PORT=5110
API_PORT=5111

log_info "=== Ralph Stock Analysis - 배포 검증 ==="
echo ""

# 1. systemd 서비스 상태
log_header "1. systemd 서비스 상태"
if systemctl is-active --quiet ralph-stock.service 2>/dev/null; then
    log_info "   ✅ ralph-stock.service 실행 중"
    systemctl status ralph-stock.service --no-pager -l | grep -E "(Active:|Loaded:)" | sed 's/^/     /'
else
    log_warn "   ⚠️  ralph-stock.service 실행 중이 아님"
fi
echo ""

# 2. Docker 컨테이너 상태
log_header "2. Docker Compose 서비스 상태"
cd /home/ralph/work/python/kr_stock_analysis

# 프로덕션 프로필로 실행 중인 컨테이너 확인
RUNNING_CONTAINERS=$(docker compose --profile prod ps --quiet 2>/dev/null | wc -l)
log_info "   실행 중인 컨테이너: $RUNNING_CONTAINERS"

echo ""
docker compose --profile prod ps 2>/dev/null | head -20 || log_warn "   Docker Compose 상태 확인 실패"
echo ""

# 3. 포트 Listening 확인
log_header "3. 포트 Listening 상태"
for port in $FRONTEND_PORT $API_PORT; do
    if ss -tuln | grep -q ":$port "; then
        log_info "   ✅ 포트 $port: Listening"
    else
        log_error "   ❌ 포트 $port: Not listening"
    fi
done
echo ""

# 4. 로컬 접속 테스트
log_header "4. 로컬 접속 테스트"

# Frontend
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT | grep -q "200\|301\|302"; then
    log_info "   ✅ Frontend (:$FRONTEND_PORT): 접속 가능"
else
    log_error "   ❌ Frontend (:$FRONTEND_PORT): 접속 실패"
fi

# API Health
API_HEALTH=$(curl -s http://localhost:$API_PORT/health 2>/dev/null || echo "failed")
if [[ "$API_HEALTH" == "failed" ]]; then
    # /health가 없으면 /api/health 시도
    API_HEALTH=$(curl -s http://localhost:$API_PORT/api/health 2>/dev/null || echo "failed")
fi

if [[ "$API_HEALTH" != "failed" ]]; then
    log_info "   ✅ API Gateway (:$API_PORT): 응답 정상"
else
    log_warn "   ⚠️  API Gateway (:$API_PORT): 응답 없음 (/health 엔드포인트 확인 필요)"
fi
echo ""

# 5. NPM 네트워크 연결 상태
log_header "5. Nginx Proxy Manager 네트워크 연결"

# NPM 컨테이너 찾기
NPM_CONTAINER=$(docker ps --format "{{.Names}}" | grep -iE "(npm|nginx.*proxy|proxy.*manager)" | head -n 1 || echo "")

if [[ -n "$NPM_CONTAINER" ]]; then
    log_info "   NPM 컨테이너: $NPM_CONTAINER"

    # ralph-network 연결 확인
    if docker network inspect ralph-network --format='{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null | grep -q "^${NPM_CONTAINER} "; then
        log_info "   ✅ NPM이 ralph-network에 연결됨"
    else
        log_error "   ❌ NPM이 ralph-network에 연결되지 않음"
        log_info "      다음 명령어로 연결: sudo docker network connect ralph-network $NPM_CONTAINER"
    fi
else
    log_warn "   ⚠️  NPM 컨테이너를 찾을 수 없음"
fi
echo ""

# 6. ralph-network 상태
log_header "6. ralph-network 상태"
if docker network inspect ralph-network >/dev/null 2>&1; then
    log_info "   ✅ ralph-network 존재"

    CONNECTED_COUNT=$(docker network inspect ralph-network --format='{{len .Containers}}' 2>/dev/null || echo "0")
    log_info "   연결된 컨테이너: $CONNECTED_COUNT"

    echo "   연결된 컨테이너 목록:"
    docker network inspect ralph-network --format='{{range .Containers}}   - {{.Name}} ({{.IPv4Address}}){{"\n"}}{{end}}' 2>/dev/null || echo "     (없음)"
else
    log_error "   ❌ ralph-network이 존재하지 않음"
fi
echo ""

# 7. 외부 접속 테스트
log_header "7. 외부 접속 테스트"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
    log_info "   ✅ $SITE_URL: HTTP $HTTP_CODE"
elif [[ "$HTTP_CODE" == "502" ]]; then
    log_error "   ❌ $SITE_URL: HTTP 502 Bad Gateway"
    log_info "      NPM → Backend 연결 문제일 수 있습니다."
elif [[ "$HTTP_CODE" == "000" ]]; then
    log_warn "   ⚠️  $SITE_URL: 접속 불가 (DNS 또는 방화벽 문제)"
else
    log_warn "   ⚠️  $SITE_URL: HTTP $HTTP_CODE"
fi
echo ""

# 8. 최근 로그 확인 (에러 포함)
log_header "8. 최근 에러 로그"
ERROR_LOGS=$(docker compose --profile prod logs --tail=20 2>/dev/null | grep -iE "error|fail|exception" || echo "")
if [[ -n "$ERROR_LOGS" ]]; then
    echo "$ERROR_LOGS" | head -10 | sed 's/^/   /'
else
    log_info "   최근 에러 로그 없음"
fi
echo ""

# 9. 요약
log_info "=== 검증 요약 ==="
echo ""

# 건강 상태 점수 계산
SCORE=0
MAX_SCORE=7

systemctl is-active --quiet ralph-stock.service 2>/dev/null && ((SCORE++))
ss -tuln | grep -q ":$FRONTEND_PORT " && ((SCORE++))
ss -tuln | grep -q ":$API_PORT " && ((SCORE++))
curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT | grep -q "200\|301\|302" && ((SCORE++))
[[ -n "$NPM_CONTAINER" ]] && docker network inspect ralph-network --format='{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null | grep -q "^${NPM_CONTAINER} " && ((SCORE++))
docker network inspect ralph-network >/dev/null 2>&1 && ((SCORE++))
[[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]] && ((SCORE++))

echo "건강 상태: $SCORE / $MAX_SCORE"

if [[ $SCORE -eq $MAX_SCORE ]]; then
    log_info "✅ 모든 검사 통과!"
elif [[ $SCORE -ge $MAX_SCORE-2 ]]; then
    log_warn "⚠️  일부 검사 실패 (위 내용 참조)"
else
    log_error "❌ 다수의 검사 실패. 재배포가 필요할 수 있습니다."
fi

echo ""
log_info "로그 확인:"
log_info "   sudo journalctl -u ralph-stock -f"
log_info "   docker compose --profile prod logs -f"
