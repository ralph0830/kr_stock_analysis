# Frontend QA Test Report

**테스트 일시:** 2026-02-05 17:53 ~ 17:55
**테스트 대상:** https://stock.ralphpark.com
**테스트 도구:** Playwright (Headless Chrome)

---

## 1. 테스트 개요

### 1.1 테스트 범위

| 페이지 | 경로 | 접속 결과 |
|--------|------|-----------|
| 메인 페이지 | `/` | ⚠️ 부분적 로드 |
| 대시보드 | `/dashboard` | ⚠️ 부분적 로드 |
| 한국 시장 | `/dashboard/kr` | ⚠️ 부분적 로드 |
| VCP 시그널 | `/dashboard/kr/vcp` | ⚠️ 부분적 로드 |
| 종가베팅 V2 | `/dashboard/kr/closing-bet` | ⚠️ 부분적 로드 |
| 차트 | `/chart` | ⚠️ 부분적 로드 |
| 단타 추천 | `/custom-recommendation` | ⚠️ 부분적 로드 |

### 1.2 전체 평가

- **전체 상태:** 🔴 **CRITICAL** - 기능 사용 불가
- **페이지 로드:** ✅ 정상 (HTML 렌더링)
- **데이터 로딩:** ❌ 실패 (API 타임아웃)
- **실시간 연결:** ❌ 실패 (WebSocket 502)

---

## 2. Frontend 이슈 사항

### 2.1 콘솔 에러 분석

#### 2.1.1 WebSocket 연결 실패

```
[error] WebSocket connection to 'wss://stock.ralphpark.com/ws' failed:
    Error during WebSocket handshake: Unexpected response code: 502
```

- **발생 빈도:** 모든 페이지에서 지속적 발생
- **재시도 동작:** 자동 재시도함 (최대 10회), 그러나 모두 실패
- **최종 상태:** `disconnected`, 연결 상태 아이콘 "○ 대기 중" 표시

**원인 분석 (Frontend):**
- WebSocket endpoint가 정상적으로 응답하지 않음
- Nginx Proxy Manager에서 WebSocket 업그레이드가 제대로 처리되지 않을 가능성

**Frontend 수정 필요 여부:** ❌ 없음 (Backend/Infrastructure 문제)

#### 2.1.2 404 에러

```
[error] Failed to load resource: the server responded with a status of 404 ()
```

- **발생 빈도:** 각 페이지 로드 시 3개씩 발생
- **발생 페이지:** `/dashboard/kr`, `/dashboard/kr/vcp`, `/dashboard/kr/closing-bet`, `/chart`, `/custom-recommendation`

**원인 분석 (Frontend):**
- 어떤 리소스가 404를 반환하는지 콘솔 로그만으로는 식별 불가
- `fetcher.ts` 등에서 API 요청 실패 시 로그를 남기도록 되어 있으나 URL이 노출되지 않음

**Frontend 수정 필요:**
- 에러 로그에 실패한 URL을 포함하도록 개선 필요
- `/utils/fetcher.ts` 또는 API 호출 부분에 에러 핸들링 강화

---

### 2.2 UI 상태 분석

#### 2.2.1 로딩 상태

모든 페이지에서 데이터 로딩 메시지가 계속 표시됨:

| 페이지 | 로딩 메시지 |
|--------|-------------|
| 메인 | "Market Gate 정보를 불러오는 중..." |
| 대시보드 | "Market Gate 정보를 불러올 수 없습니다." |
| 한국 시장 | "한국 시장 개요를 불러오는 중..." |
| VCP 시그널 | "VCP 시그널을 불러오는 중..." |
| 종가베팅 V2 | "종가베팅 V2 시그널을 불러오는 중..." |
| 차트 | "차트 데이터를 불러오는 중..." |
| 단타 추천 | "실시간 연결이 안됩니다. 새로고침하거나 시장 스캔을 실행하세요." |

**평가:** API 타임아웃으로 인한 정상적인 동작이나, 사용자 경험상 개선 필요

#### 2.2.2 연결 상태 표시

- 헤더에 WebSocket 상태 아이콘: `○ 대기 중` (정상: `● 연결됨`)
- 상태 변경: `connecting` → `error` → `disconnected`

---

## 3. API 요청 분석

### 3.1 API 요청 로그

콘솔에서 확인된 API 요청:

```
[log] [API Request] GET /api/kr/market-gate
[log] [API Request] GET /api/kr/signals
```

### 3.2 재시도 동작

```
[log] [API] Retrying request (1/5): /api/kr/market-gate after 1000ms
[log] [API] Retrying request (1/5): /api/kr/signals after 1000ms
```

- 재시도 기능이 정상 동작함
- 최대 5회 재시도 설정됨
- 그러나 모든 요청이 타임아웃으로 실패

---

## 4. Frontend 개선 사항

> **✅ 개선 완료 (2026-02-05 18:10)**
> 자세한 내용은 [`frontend_improvements_20260205.md`](./frontend_improvements_20260205.md) 참고

### 4.1 필수 (Critical)

| 항목 | 내용 | 우선순위 | 상태 |
|------|------|----------|------|
| 에러 로그 개선 | 404/500 에러 발생 시 실패한 URL을 콘솔에 명시 | P0 | ✅ 완료 |
| 타임아웃 메시지 | API 타임아웃 시 사용자에게 명확한 안내 메시지 표시 | P0 | ✅ 완료 |

### 4.2 권장 (Recommended)

| 항목 | 내용 | 우선순위 | 상태 |
|------|------|----------|------|
| WebSocket 상태 | 연결 실패 원인을 사용자에게 더 명확히 표시 | P2 | ✅ 완료 |
| 502 에러 식별 | Bad Gateway 에러 명확히 식별 및 트러블슈팅 가이드 | P1 | ✅ 완료 |

### 4.3 수정 파일

- `frontend/lib/api-client.ts` - API 에러 로깅 개선
- `frontend/hooks/useWebSocket.ts` - WebSocket 에러 처리 강화
- `frontend/lib/websocket.ts` - WebSocket 에러 로그 상세화

---

## 5. 스크린샷 참고

저장된 스크린샷 파일:

1. `stock_ralphpark_com_homepage-2026-02-05T08-53-31-277Z.png`
2. `dashboard_page-2026-02-05T08-54-07-613Z.png`
3. `dashboard_kr_page-2026-02-05T08-54-19-305Z.png`
4. `dashboard_kr_vcp_page-2026-02-05T08-54-30-359Z.png`
5. `dashboard_kr_closing_bet_page-2026-02-05T08-54-38-996Z.png`
6. `chart_page-2026-02-05T08-54-53-060Z.png`
7. `custom_recommendation_page-2026-02-05T08-55-19-754Z.png`

---

## 6. 결론

### 6.1 Frontend 상태

- ✅ **페이지 렌더링:** 정상
- ✅ **네비게이션:** 정상
- ✅ **UI 컴포넌트:** 정상
- ✅ **에러 핸들링:** 개선 완료 (2026-02-05)
- ❌ **데이터 로딩:** Backend 의존 (Backend 수정 필요)

### 6.2 Frontend 수정 범위

**✅ 완료된 작업 (2026-02-05):**
1. 에러 로그에 URL 포함
2. 에러 타입별 명확한 메시지 (NOT_FOUND, SERVER_ERROR, BAD_GATEWAY, TIMEOUT 등)
3. WebSocket 502 에러 식별 및 트러블슈팅 가이드
4. 사용자에게 명확한 에러 메시지 제공

**Backend 조치 필요:**
- API Gateway 서비스 실행 확인 (포트 5111)
- Nginx Proxy Manager WebSocket 업그레이드 설정 확인
- Docker 컨테이너 상태 점검
