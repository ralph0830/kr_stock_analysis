# 대시보드 "활성 시그널 없음" 현상 분석 보고서

**작성일:** 2026-02-05
**범위:** 대시보드(/dashboard) 시그널 미표시 문제

---

## 1. 개요

대시보드 페이지에서 "활성 시그널이 없습니다" 메시지가 표시되는 현상의 원인을 분석했습니다.

---

## 2. 문제 현상

### 2.1 사용자 관찰
- **페이지**: `https://stock.ralphpark.com/dashboard`
- **메시지**: "활성 시그널이 없습니다."
- **추가 증상**:
  - WebSocket 연결 상태: "○ 대기 중" (연결 안됨)
  - Market Gate: "Market Gate 정보를 불러올 수 없습니다."
  - 시스템 상태: "알 수 없음"

### 2.2 브라우저 콘솔 에러
```
ChunkLoadError: Loading chunk app/dashboard/page failed.
(timeout: https://stock.ralphpark.com/_next/static/chunks/app/dashboard/page.js)
```

---

## 3. 원인 분석

### 3.1 근본 원인: Next.js ChunkLoadError

**JavaScript 청크 로드 실패**
```
Failed to load: /_next/static/chunks/app/dashboard/page.js
Reason: timeout
```

### 3.2 데이터 흐름 분석

```
[정상 흐름]
프론트엔드 → useStore().fetchSignals()
         → apiClient.getSignals()
         → GET /api/kr/signals
         → 백엔드 → DB → 시그널 반환
         → 프론트엔드 표시

[실제 발생]
프론트엔드 → ChunkLoadError 발생!
         → React 컴포넌트 실행 안됨
         → fetchSignals() 호출 안됨
         → signals = [] (초기값)
         → "활성 시그널이 없습니다" 표시
```

### 3.3 API 백엔드 확인 (정상)

**직접 API 호출 테스트:**
```bash
GET https://stock.ralphpark.com/api/kr/signals
```

**응답 (20개 시그널):**
```json
[
  {"ticker":"000040","name":"KR모터스","signal_type":"vcp","score":25.0,"grade":"C",...},
  {"ticker":"000050","name":"경방","signal_type":"vcp","score":25.0,"grade":"C",...},
  ... (총 20개)
]
```

**결론**: API 백엔드는 정상 작동, 20개의 시그널 데이터 존재

---

## 4. 기술적 상세

### 4.1 Next.js 청킹 구조

| 파일 | 경로 | 상태 |
|------|------|------|
| `app/dashboard/page.js` | `/_next/static/chunks/app/dashboard/page.js` | ❌ 로드 실패 |
| `app/dashboard/layout.js` | `/_next/static/chunks/app/dashboard/layout.js` | ❌ 로드 실패 |

### 4.2 영향 범위

| 페이지 | 경로 | 상태 |
|--------|------|------|
| 메인 대시보드 | `/dashboard` | ❌ 청크 로드 실패 |
| KR Overview | `/dashboard/kr` | ❌ 동일 청크 사용, 실패 |
| VCP 페이지 | `/dashboard/kr/vcp` | 미확인 (동일 문제 예상) |

### 4.3 발생 시점

- **배포 후**: 프로덕션 빌드 이후부터 발생
- **빌드 문제**: 정적 청크 파일이 제대로 생성되지 않았거나 누락
- **캐시 문제**: CDN/NPM 캐시로 인해 구버전 참조

---

## 5. 개선 방안

### 5.1 긴급 조치 (즉시 실행)

#### 1. Next.js 프로덕션 빌드 재실행
```bash
cd frontend
rm -rf .next
npm run build
```

#### 2. 정적 청크 파일 재생성 확인
```bash
ls -la .next/static/chunks/app/dashboard/
```

#### 3. CDN/리버스 프록시 캐시 삭제
```bash
# Nginx Proxy Manager 캐시 삭제
# 또는 Cloudflare 캐시 퍼지
```

#### 4. 배포 후 헬스 체크
```bash
curl -I https://stock.ralphpark.com/_next/static/chunks/app/dashboard/page.js
# 200 OK 확인
```

### 5.2 중기 개선 (구조적)

#### 1. 페이지 구조 단순화
- 대용량 컴포넌트를 별도 파일로 분리
- 동적 import로 지연 로드 적용

```typescript
// 현재: 단일 파일에 모든 컴포넌트
// app/dashboard/page.tsx (567줄)

// 개선: 컴포넌트 분리
import { VCPSignalTable } from '@/components/dashboard/VCPSignalTable';
import { MarketGateCard } from '@/components/dashboard/MarketGateCard';
```

#### 2. Code Splitting 전략 재검토
```typescript
// next.config.js
experimental = {
  optimizePackageImports: ['@/components', '@/lib']
}
```

#### 3. Error Boundary로 그레이스풀 디그레이션
```typescript
// 이미 존재하는 ErrorBoundary.tsx 활용
// 청크 로드 실패 시 대체 UI 표시
```

### 5.3 장기 개선 (인프라)

#### 1. 빌드 프로세스 자동화
```yaml
# .github/workflows/deploy.yml
- name: Build Frontend
  run: |
    cd frontend
    npm ci
    npm run build
    # 청크 파일 존재 확인
    ls -la .next/static/chunks/app/dashboard/page.js

- name: Cache Purge
  run: |
    # NPM/Cloudflare 캐시 삭제
```

#### 2. 배포 후 헬스 체크 추가
```python
# tests/integration/test_frontend_health.py
async def test_dashboard_chunks_accessible():
    response = client.get("/_next/static/chunks/app/dashboard/page.js")
    assert response.status_code == 200
```

#### 3. 청크 로드 모니터링
```typescript
// lib/monitoring.ts
window.addEventListener('error', (event) => {
  if (event.message.includes('ChunkLoadError')) {
    // Sentry/Analytics에 에러 보고
    captureMessage(`ChunkLoadError: ${event.message}`);
  }
});
```

---

## 6. 예방 조치

### 6.1 빌드 검증 스크립트
```bash
#!/bin/bash
# scripts/verify-frontend-build.sh

CHUNKS=(
  ".next/static/chunks/app/dashboard/page.js"
  ".next/static/chunks/app/dashboard/layout.js"
  ".next/static/chunks/app/page.js"
)

for chunk in "${CHUNKS[@]}"; do
  if [ ! -f "frontend/$chunk" ]; then
    echo "❌ Missing chunk: $chunk"
    exit 1
  fi
done

echo "✅ All chunks verified"
```

### 6.2 배포 체크리스트

- [ ] 빌드 성공 (exit code 0)
- [ ] 청크 파일 존재 확인
- [ ] 핵심 페이지 접근 테스트
- [ ] API 엔드포인트 테스트
- [ ] CDN 캐시 삭제
- [ ] 모니터링 대시보드 확인

---

## 7. 결론

### 7.1 요약

"활성 시그널이 없습니다" 메시지의 **근본 원인**은:
- ❌ 데이터 부족이 아님
- ❌ API 백엔드 문제가 아님
- ✅ **Next.js JavaScript 청크 로드 실패**

### 7.2 현재 상태

| 구분 | 상태 |
|------|------|
| API 백엔드 | ✅ 정상 (20개 시그널 존재) |
| DB 데이터 | ✅ 정상 |
| 프론트엔드 빌드 | ❌ 청크 로드 실패 |
| 사용자 경험 | ❌ "시그널 없음" 메시지 |

### 7.3 조치 요청

1. **긴급**: Next.js 프로덕션 빌드 재실행
2. **검증**: 청크 파일 접근성 테스트
3. **예방**: 빌드 검증 스크립트 추가

---

## 8. 참고 파일

| 파일 | 설명 |
|------|------|
| `frontend/app/dashboard/page.tsx` | 대시보드 메인 페이지 (567줄) |
| `frontend/app/dashboard/kr/page.tsx` | KR Overview 페이지 |
| `services/api_gateway/routes/signals.py` | 시그널 API 엔드포인트 |
| `src/repositories/signal_repository.py` | 시그널 리포지토리 |
| `frontend/store/index.ts` | Zustand Store |

### 관련 보고서

- `schema_comparison_20260205.md` - 스키마 비교 분석
- `code_sharing_analysis_20260205.md` - 프론트엔드 코드 공유 분석
- `websocket_backend_20260205.md` - WebSocket 백엔드 분석
