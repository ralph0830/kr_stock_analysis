#!/bin/bash
# Next.js Frontend 빌드 검증 스크립트
# 프로덕션 빌드 후 필수 청크 파일이 존재하는지 확인합니다.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/../frontend"

echo "=== Next.js Build Verification ==="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 검증할 청크 파일 목록
CHUNKS=(
    ".next/static/chunks/app/page.js"
    ".next/static/chunks/app/layout.js"
    ".next/static/chunks/app/dashboard/page.js"
    ".next/static/chunks/app/dashboard/layout.js"
    ".next/static/chunks/app/dashboard/kr/page.js"
    ".next/static/chunks/app/dashboard/kr/vcp/page.js"
)

MISSING_COUNT=0

echo "Frontend 경로: ${FRONTEND_DIR}"
echo ""

# .next 디렉토리 존재 확인
if [ ! -d "${FRONTEND_DIR}/.next" ]; then
    echo -e "${RED}❌ .next 디렉토리가 존재하지 않습니다. 빌드를 먼저 실행하세요.${NC}"
    echo "   실행: cd frontend && npm run build"
    exit 1
fi

echo -e "${GREEN}✅ .next 디렉토리 확인${NC}"
echo ""

# 청크 파일 검증
echo "청크 파일 검증:"
echo "-------------------"

for chunk in "${CHUNKS[@]}"; do
    chunk_path="${FRONTEND_DIR}/${chunk}"

    if [ -f "$chunk_path" ]; then
        size=$(du -h "$chunk_path" | cut -f1)
        echo -e "${GREEN}✅${NC} ${chunk} (${size})"
    else
        echo -e "${RED}❌${NC} ${chunk} ${RED}[누락]${NC}"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

echo ""
echo "==================="

# 결과 요약
if [ $MISSING_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 청크 파일이 존재합니다.${NC}"
    echo ""
    echo "빌드 상태: 정상"
    echo "배포 가능합니다."
    exit 0
else
    echo -e "${RED}❌ ${MISSING_COUNT}개 청크 파일이 누락되었습니다.${NC}"
    echo ""
    echo -e "${YELLOW}조치:${NC}"
    echo "  cd frontend"
    echo "  rm -rf .next"
    echo "  npm run build"
    echo ""
    echo "빌드 후 다시 검증해 주세요."
    exit 1
fi
