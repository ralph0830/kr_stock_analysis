# QA Test Summary - stock.ralphpark.com

**테스트 일시:** 2026-02-05 17:53 ~ 17:55 (KST)
**테스트 도구:** Playwright (Headless Chrome)
**테스터:** Claude Code QA Agent

---

## 🔴 전체 평가: CRITICAL - 서비스 중단

### 한 줄 요약
**API Gateway 서비스가 응답하지 않아 모든 데이터 로딩 및 실시간 연결 기능이 작동하지 않습니다.**

---

## 테스트 결과

### 페이지 접속 테스트 (7개 페이지)

| 페이지 | 경로 | 페이지 로드 | 데이터 로딩 | 실시간 연결 |
|--------|------|:----------:|:----------:|:----------:|
| 메인 | `/` | ✅ | ❌ | ❌ |
| 대시보드 | `/dashboard` | ✅ | ❌ | ❌ |
| 한국 시장 | `/dashboard/kr` | ✅ | ❌ | ❌ |
| VCP 시그널 | `/dashboard/kr/vcp` | ✅ | ❌ | ❌ |
| 종가베팅 V2 | `/dashboard/kr/closing-bet` | ✅ | ❌ | ❌ |
| 차트 | `/chart` | ✅ | ❌ | ❌ |
| 단타 추천 | `/custom-recommendation` | ✅ | ❌ | ❌ |

### API 직접 호출 테스트

| 엔드포인트 | 결과 |
|------------|------|
| `GET /api/kr/market-gate` | ❌ Timeout (>30s) |
| `GET /api/kr/signals` | ❌ Timeout (>30s) |
| `GET /api/kr/vcp-signals` | ❌ Timeout (>30s) |
| `GET /api/stocks` | ❌ Timeout (>30s) |
| `WS /ws` | ❌ 502 Bad Gateway |

---

## 이슈 분류

### Backend 이슈 (🔴 즉시 조치 필요)

| 이슈 | 증상 | 원인 (추정) |
|------|------|------------|
| API 타임아웃 | 모든 API 요청 30초 후 타임아웃 | API Gateway 서버 다운 |
| WebSocket 502 | `wss://.../ws` 연결 실패 (502) | Upstream 서버 응답 없음 |

### Frontend 이슈 (⚠️ 개선 권장)

| 이슈 | 증상 | 영향 |
|------|------|------|
| 에러 로그 불명확 | 404 에러 시 URL 노출 안됨 | 디버깅 어려움 |
| 타임아웃 메시지 | 사용자에게 명확한 안내 부족 | UX 저하 |

---

## 즉시 조치 사항 (Backend)

### 1. 서비스 상태 확인

```bash
# 컨테이너 상태 확인
docker ps -a | grep api_gateway

# 로그 확인
docker logs api_gateway --tail 50
```

### 2. 서비스 재시작

```bash
# API Gateway 재시작
docker compose restart api_gateway

# 또는 전체 서비스 재시작
docker compose restart
```

### 3. 헬스체크

```bash
# 로컬 테스트
curl http://localhost:5111/health

# 외부 테스트
curl https://stock.ralphpark.com/api/kr/market-gate
```

---

## 보고서 파일

- **전체 보고서:** `docs/report/qa_summary_20260205.md` (이 파일)
- **Frontend 상세:** `docs/report/qa_frontend_20260205.md`
- **Backend 상세:** `docs/report/qa_backend_20260205.md`

---

## 스크린샷

| 파일명 | 설명 |
|--------|------|
| `stock_ralphpark_com_homepage-*.png` | 메인 페이지 |
| `dashboard_page-*.png` | 대시보드 |
| `dashboard_kr_page-*.png` | 한국 시장 |
| `dashboard_kr_vcp_page-*.png` | VCP 시그널 |
| `dashboard_kr_closing_bet_page-*.png` | 종가베팅 V2 |
| `chart_page-*.png` | 차트 페이지 |
| `custom_recommendation_page-*.png` | 단타 추천 |

*모든 스크린샷은 `~/Downloads/` 디렉토리에 저장됨*
