# Backend QA Test Report

**테스트 일시:** 2026-02-05 17:53 ~ 17:55
**테스트 대상:** https://stock.ralphpark.com
**테스트 도구:** Playwright API Context, Console Log Analysis

---

## 1. 테스트 개요

### 1.1 전체 평가

- **전체 상태:** 🔴 **CRITICAL** - 서비스 응답 불가
- **API Gateway:** ❌ 응답 없음 (30초 타임아웃)
- **WebSocket:** ❌ 502 Bad Gateway
- **REST API:** ❌ 전체 타임아웃

---

## 2. API 테스트 결과

### 2.1 REST API 타임아웃

Playwright API Context로 직접 호출한 결과:

| 엔드포인트 | 메서드 | 결과 | 응답 시간 |
|------------|--------|------|-----------|
| `/api/kr/market-gate` | GET | ❌ Timeout | >30s |
| `/api/kr/signals` | GET | ❌ Timeout | >30s |
| `/api/kr/vcp-signals` | GET | ❌ Timeout | >30s |
| `/api/stocks` | GET | ❌ Timeout | >30s |

**요청 헤더:**
```
User-Agent: Playwright/1.53.1 (x64; ubuntu 24.04) node/22.18
Accept: */*
Accept-Encoding: gzip,deflate,br
```

### 2.2 API 요청 로그 (브라우저 콘솔)

```
[log] [API Request] GET /api/kr/market-gate
[log] [API] baseURL: https://stock.ralphpark.com
[log] [API] Retrying request (1/5): /api/kr/market-gate after 1000ms
```

- Frontend에서 요청은 정상적으로 발생함
- 재시도 로직이 동작하나 모든 요청이 실패

---

## 3. WebSocket 테스트 결과

### 3.1 연결 실패 상세

```
[error] WebSocket connection to 'wss://stock.ralphpark.com/ws' failed:
    Error during WebSocket handshake: Unexpected response code: 502
```

### 3.2 연결 상태 변화

```
disconnected → connecting → error → disconnected
```

- WebSocket 핸드셰이크 단계에서 502 에러 발생
- 502 = "Bad Gateway" → Upstream 서버가 응답하지 않음

### 3.3 재시도 동작

```
[log] [WebSocket] Reconnecting in 0ms... (attempt 1/10)
[warning] WebSocket connection to 'wss://stock.ralphpark.com/ws' failed:
    WebSocket is closed before the connection is established.
[log] [WebSocket] Close code 1006: no reconnect
```

- 최대 10회 재시도 시도
- 모두 실패 후 재시도 중단

---

## 4. 원인 분석

### 4.1 근본 원인

**502 Bad Gateway**와 **API 타임아웃**이 동시에 발생하는 것으로 보아:

1. **API Gateway 서버가 실행 중이 아님**
   - `api_gateway` (포트 5111) 서비스 다운
   - Docker 컨테이너 중지

2. **또는 Nginx Proxy Manager 설정 문제**
   - `/api` 경로 포워딩 오류
   - WebSocket 업그레이드 설정 누락

### 4.2 가능성 분석

| 가능성 | 증거 | 확률 |
|--------|------|------|
| API Gateway 컨테이너 다운 | 전체 API 타임아웃, WS 502 | 🔴 높음 |
| NPM 포워딩 오류 | 일부 요청은 502, 일부는 타임아웃 | 🟡 중간 |
| 네트워크 문제 | 외부에서 접속 가능함 | 🟢 낮음 |

---

## 5. 확인 필요 사항

### 5.1 서비스 상태 확인 (Backend 팀)

```bash
# Docker 컨테이너 상태
docker ps | grep api_gateway

# API Gateway 로그
docker logs api_gateway

# Nginx Proxy Manager 상태
curl -I http://112.219.120.75:81
```

### 5.2 포트 확인

```bash
# 포트 listening 확인
netstat -tlnp | grep 5111

# 방화벽 확인
sudo ufw status
```

### 5.3 NPM 설정 확인

Nginx Proxy Manager에서 다음을 확인:

- [ ] `/api` → `112.219.120.75:5111` 포워딩 설정
- [ ] `/ws` → `112.219.120.75:5111` 포워딩 설정
- [ ] WebSocket Upgrade 헤더 설정
- [ ] Cache 비활성화 설정

---

## 6. 대응 방안

### 6.1 즉시 조치 (Critical)

| 순서 | 작업 | 명령어 |
|------|------|--------|
| 1 | API Gateway 컨테이너 재시작 | `docker compose restart api_gateway` |
| 2 | 로그 확인 | `docker logs -f api_gateway` |
| 3 | 헬스체크 | `curl http://localhost:5111/health` |

### 6.2 NPM 설정 확인

1. NPM 웹 UI 접속: `http://112.219.120.75:81`
2. `Proxy Hosts` → `stock.ralphpark.com` 선택
3. `Custom Nginx Configuration` 확인:

```nginx
# WebSocket Headers
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;

# Cache 비활성화
add_header Cache-Control "no-store, no-cache, must-revalidate";
add_header Pragma "no-cache";
```

### 6.3 영구 조치 (Recommended)

| 항목 | 내용 | 우선순위 |
|------|------|----------|
| 헬스체크 엔드포이트 | `/health` 엔드포인트에서 서비스 상태 반환 | P0 |
| 서비스 자동 재시작 | Docker 컨테이너 `restart: always` 설정 확인 | P1 |
| 모니터링 알림 | 서비스 다운 시 알림 발송 (Discord/Slack) | P1 |
| NPM HA 구성 | Nginx Proxy Manager 고가용성 구성 | P2 |

---

## 7. 재테스트 계획

### 7.1 Backend 재시작 후 테스트 항목

```bash
# 1. 로컬 헬스체크
curl http://localhost:5111/health

# 2. 외부 API 테스트
curl https://stock.ralphpark.com/api/kr/market-gate
curl https://stock.ralphpark.com/api/kr/signals
curl https://stock.ralphpark.com/api/stocks

# 3. WebSocket 테스트
wscat -c wss://stock.ralphpark.com/ws
```

### 7.2 Frontend 재테스트

1. 메인 페이지 접속
2. WebSocket 연결 상태 확인 ("● 연결됨" 표시)
3. 데이터 로딩 확인
4. 각 페이지별 기능 확인

---

## 8. 결론

### 8.1 현재 상태

- **API Gateway:** 서비스 중단 (응답 없음)
- **WebSocket:** 연결 불가 (502 Bad Gateway)
- **영향 범위:** 전체 기능 사용 불가

### 8.2 조치 요청

- **Backend 팀:** API Gateway 서비스 재시작 및 로그 분석
- **Infrastructure 팀:** Nginx Proxy Manager 설정 검토

### 8.3 예상 복구 시간

서비스 재시작만으로 해결된다면: **5분 이내**
NPM 설정 변경이 필요하다면: **15분 이내**
