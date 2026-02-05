# [요청] 대시보드 Frontend 빌드 재실행 필요

**요청일:** 2026-02-05
**우선순위:** 긴급 (P0)
**요청자:** 프론트엔드 개발

---

## 1. 문제 현상

### 사용자 보고
- **페이지:** `https://stock.ralphpark.com/dashboard`
- **메시지:** "활성 시그널이 없습니다."
- **WebSocket:** "○ 대기 중" (연결 안됨)
- **Market Gate:** "Market Gate 정보를 불러올 수 없습니다."

### 브라우저 콘솔 에러
```
ChunkLoadError: Loading chunk app/dashboard/page failed
(timeout: https://stock.ralphpark.com/_next/static/chunks/app/dashboard/page.js)
```

---

## 2. 원인 분석 결과

### ✅ API 백엔드 정상 확인

```bash
GET https://stock.ralphpark.com/api/kr/signals
```

**응답:** 20개 시그널 존재
```json
[
  {"ticker":"000040","name":"KR모터스","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000050","name":"경방","signal_type":"vcp","score":25.0,"grade":"C"},
  ... (총 20개)
]
```

### ❌ Frontend 청크 로드 실패

| 파일 | 경로 | 상태 |
|------|------|------|
| `page.js` | `/_next/static/chunks/app/dashboard/page.js` | 로드 실패 (timeout) |
| `layout.js` | `/_next/static/chunks/app/dashboard/layout.js` | 로드 실패 |

### 데이터 흐름
```
[정상]
Frontend → API /api/kr/signals → 20개 시그널 반환 → 표시

[실제]
Frontend → ChunkLoadError! → React 컴포넌트 미실행 → signals = [] → "시그널 없음"
```

---

## 3. 결론

**근본 원인:** Next.js 프로덕션 빌드 후 JavaScript 청크 파일이 제대로 생성되지 않거나 접근 불가

| 구분 | 상태 |
|------|------|
| API 백엔드 | ✅ 정상 |
| DB 데이터 | ✅ 정상 (20개 시그널) |
| Frontend 빌드 | ❌ 청크 로드 실패 |

---

## 4. 필요한 조치

### 4.1 긴급 (즉시 실행)

```bash
# 1. Frontend 빌드 재실행
cd frontend
rm -rf .next
npm run build

# 2. 청크 파일 확인
ls -la .next/static/chunks/app/dashboard/
# page.js, layout.js 존재 확인

# 3. 재배포
docker compose restart frontend

# 4. CDN 캐시 삭제 (NPM 또는 Cloudflare)
```

### 4.2 검증

```bash
# 청크 파일 접근 테스트
curl -I https://stock.ralphpark.com/_next/static/chunks/app/dashboard/page.js
# 기대: 200 OK
```

---

## 5. 예방 조치

### 빌드 검증 스크립트 추가 (생성 완료)

```bash
# scripts/verify-frontend-build.sh 실행
./scripts/verify-frontend-build.sh
```

### 배포 체크리스트

- [ ] 빌드 성공 (exit code 0)
- [ ] 청크 파일 존재 확인
- [ ] 핵심 페이지 접근 테스트
- [ ] CDN 캐시 삭제

---

## 6. 첨부 파일

| 파일 | 설명 |
|------|------|
| `scripts/verify-frontend-build.sh` | 빌드 검증 스크립트 |
| `docs/report/dashboard_empty_signals_analysis_20260205.md` | 상세 분석 보고서 |

---

**연락:** 추가 정보 필요시 프론트엔드 개발팀으로 문의 바랍니다.
