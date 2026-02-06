# Infrastructure Down Root Cause Analysis Report

**분석 일시:** 2026-02-06 09:10 ~ 09:15 (KST)
**분석 대상:** stock.ralphpark.com 인프라
**심각도:** 🔴 **CRITICAL**

---

## 1. 요약 (Executive Summary)

### 근본 원인 (Root Cause)

**WebSocket 연결 무한 재시도 루프로 인한 API Gateway 자원 고갈**

- Kiwoom WebSocket(`wss://api.kiwoom.com:10000`) 연결이 지속적으로 실패
- 재시도 로직이 폭주하여 CPU 102%, 메모리 10GB 점유
- 로그가 22만 개 이상 쌓여 서비스 응답 불가 상태

---

## 2. 현재 상태

### 2.1 서비스 상태

| 서비스 | 상태 | CPU | 메모리 | 비고 |
|--------|------|-----|--------|------|
| api-gateway | 🔴 **CRITICAL** | **102.80%** | **10.23 GB** | 자원 고갈 |
| frontend | 🟢 Healthy | 3.83% | 257 MB | 정상 |
| vcp-scanner | 🟢 Healthy | 0.10% | 30 MB | 정상 |
| signal-engine | 🟢 Healthy | 0.12% | 9 MB | 정상 |
| chatbot | 🟢 Healthy | 0.12% | 17 MB | 정상 |
| daytrading-scanner | 🟢 Healthy | 0.12% | 19 MB | 정상 |
| postgres | 🟢 Healthy | 0.01% | 109 MB | 정상 |
| redis | 🟢 Healthy | 2.47% | 4 MB | 정상 |

### 2.2 전체 시스템 리소스

```
메모리: 23 GB 중 18 GB 사용 (78%)
스왑: 8 GB 중 3.7 GB 사용 (46%)
```

---

## 3. 상세 분석

### 3.1 API Gateway 문제

**CPU 및 메모리 과다 사용:**
```
api-gateway    102.80%   10.23GiB / 23.33GiB
```

**로그 파일 크기:**
- 총 로그 라인 수: **220,314개**
- 주요 로그 내용: `WebSocket connection timeout`, `Reconnection failed after 5 attempts`

### 3.2 WebSocket 연결 실패 패턴

```
WebSocket connection timeout
Reconnection failed after 5 attempts
WebSocket connection timeout
Reconnection failed after 5 attempts
... (무한 반복)
```

**연결 대상:**
- `wss://api.kiwoom.com:10000/api/dostk/websocket`

### 3.3 Healthcheck 실패

```json
{
  "Status": "unhealthy",
  "FailingStreak": 397,
  "Log": [...]
}
```

Healthcheck 명령:
```bash
python -c "import httpx; httpx.get('http://localhost:5111/health').raise_for_status()"
```

에러: `httpx.ReadTimeout: timed out`

### 3.4 외부 접속 테스트 결과

| 테스트 항목 | 결과 | 응답 시간 |
|------------|------|----------|
| 로컬 헬스체크 (`localhost:5111/health`) | ✅ 200 OK | <1s |
| 서버 직접 접속 (`112.219.120.75:5111/health`) | ✅ 200 OK | <1s |
| 도메인 API (`https://stock.ralphpark.com/api/...`) | ❌ Timeout | >15s |
| 도메인 WebSocket (`wss://stock.ralphpark.com/ws`) | ❌ 502 Bad Gateway | - |

---

## 4. 원인 분석

### 4.1 직접적 원인 (Direct Cause)

1. **Kiwoom WebSocket 연결 실패**
   - Kiwoom API 서버(`wss://api.kiwoom.com:10000`)가 연결을 거부하거나 응답하지 않음
   - 가능한 원인:
     - Kiwoom API 서버 다운
     - 방화벽/포트 차단
     - 인증 정보 만료
     - 네트워크 문제

2. **무한 재시도 루프**
   - 연결 실패 시 즉시 재시도
   - 지수 백오프(Exponential Backoff) 미적용
   - 최대 재시도 횟수 제한 없음

### 4.2 2차적 원인 (Secondary Cause)

1. **자원 고갈**
   - CPU 100% 사용으로 다른 요청 처리 불가
   - 메모리 10GB 사용으로 스왑 발생
   - 로그 폭주로 디스크 I/O 부하

2. **Healthcheck 타임아웃**
   - 자원 고갈로 헬스체크 요청이 처리되지 않음
   - Docker가 unhealthy로 판단

### 4.3 근본적 원인 (Root Cause)

**WebSocket 재시도 로직의 결함:**

| 문제 | 현재 상태 | 올바른 동작 |
|------|----------|-------------|
| 재시도 간격 | 0초 (즉시) | 지수 백오프 (1s → 2s → 4s → ...) |
| 최대 재시도 | 무한 | 제한 필요 (예: 100회) |
| 로깅 | 매 재시도마다 로그 | 로그 레벨 조정 또는 주기적 요약 |
| CPU 사용 | 블로킹 호출 | 비동기 처리 |

---

## 5. Nginx Proxy Manager 설정 분석

### 5.1 현재 설정 (`/data/nginx/proxy_host/33.conf`)

```nginx
location /api {
    proxy_pass       http://112.219.120.75:5111;
    ...
    proxy_set_header Connection $http_connection;  # ⚠️ 문제 가능성
}

location /ws {
    proxy_pass       http://112.219.120.75:5111;
    ...
    proxy_set_header Connection $http_connection;  # ⚠️ 문제 가능성
}
```

### 5.2 설정 문제점

`$http_connection` 변수는 클라이언트가 보낸 `Connection` 헤더 값을 그대로 사용합니다.
WebSocket 업그레이드 시 클라이언트가 `Connection: keep-alive`를 보내면
서버도 `keep-alive`로 응답하여 WebSocket 연결이 실패할 수 있습니다.

**올바른 설정:**
```nginx
location /ws {
    proxy_pass http://112.219.120.75:5111;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";  # 하드코딩된 "upgrade"
    ...
}
```

---

## 6. 영향 범위

### 6.1 영향 받는 기능

- ✅ 정상: 프론트엔드 페이지 렌더링 (`/`)
- ❌ 불가: 모든 API 요청 (`/api/*`)
- ❌ 불가: WebSocket 실시간 연결 (`/ws`)
- ❌ 불가: VCP 시그널 조회
- ❌ 불가: 종가베팅 V2 시그널 조회
- ❌ 불가: Market Gate 상태 조회
- ❌ 불가: 차트 데이터 조회
- ❌ 불가: 단타 추천 기능

### 6.2 사용자 경험

- 페이지는 열리지만 데이터가 로드되지 않음
- "데이터를 불러오는 중..." 메시지가 계속 표시됨
- WebSocket 연결 상태 아이콘이 "○ 대기 중"으로 표시됨

---

## 7. 해결 방안

### 7.1 즉시 조치 (Immediate Actions)

#### 1. API Gateway 재시작

```bash
docker compose restart api-gateway
# 또는
docker restart api-gateway
```

#### 2. 로그 파일 정리

```bash
docker logs api-gateway --tail 1000 > /tmp/api-gateway-logs-backup.log
# 컨테이너 재시작 시 로그 자동 초기화
```

#### 3. Kiwoom API 상태 확인

```bash
# Kiwoom API 서버 접속 테스트
curl -v --connect-timeout 5 https://api.kiwoom.com
openssl s_client -connect api.kiwoom.com:10000
```

### 7.2 코드 수정 필요 사항 (Backend)

| 파일 | 수정 내용 | 우선순위 |
|------|----------|----------|
| `src/websocket/client.py` | 지수 백오프 추가 | P0 |
| `src/websocket/client.py` | 최대 재시도 횟수 제한 | P0 |
| `src/websocket/client.py` | 로그 레벨 조정 (INFO → WARNING) | P1 |
| `services/api_gateway/main.py` | WebSocket 연결 실패 시 그레이스풀 데그레이션 | P1 |

**예시 코드 (지수 백오프):**
```python
import asyncio

async def connect_with_backoff(max_retries=10):
    retry_count = 0
    while retry_count < max_retries:
        try:
            await websocket.connect()
            return
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Max retries exceeded: {e}")
                return
            wait_time = min(2 ** retry_count, 60)  # 최대 60초
            logger.warning(f"Retry {retry_count}/{max_retries} in {wait_time}s")
            await asyncio.sleep(wait_time)
```

### 7.3 Nginx Proxy Manager 설정 수정

**수정 전:**
```nginx
proxy_set_header Connection $http_connection;
```

**수정 후:**
```nginx
# WebSocket용
location /ws {
    proxy_set_header Connection "upgrade";
}

# API용
location /api {
    proxy_set_header Connection "keep-alive";
}
```

### 7.4 모니터링 강화

1. **CPU/메모리 알림**
   - API Gateway CPU > 50% 시 알림
   - 메모리 > 2GB 시 알림

2. **로그 모니터링**
   - "WebSocket connection timeout" 로그가 1분간 10회 이상 발생 시 알림

3. **Healthcheck 개선**
   - 외부 서비스 연결 상태를 별도로 체크
   - 핵심 기능만 체크하여 헬스체크 타임아웃 방지

---

## 8. 예방 조치 (Prevention)

### 8.1 서킷 브레이커 (Circuit Breaker)

- 연속 실패 횟수가 임계값 도달 시 재시도 중단
- 일정 시간 후에만 재시도 시도

### 8.2 리소스 제한 (Resource Limits)

```yaml
# docker-compose.yml
services:
  api-gateway:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 8.3 로그 관리

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 9. 결론

### 9.1 문제 요약

1. **WebSocket 재시도 로직의 결함**으로 인한 CPU/메모리 과다 사용
2. Kiwoom API 서비스와의 연결이 지속적으로 실패
3. 자원 고갈로 인한 API 응답 불가 상태

### 9.2 즉시 조치 필요

1. API Gateway 컨테이너 재시작
2. WebSocket 재시도 로직 수정 (지수 백오프, 최대 재시도 제한)
3. Nginx Proxy Manager Connection 헤더 설정 수정

### 9.3 장기적 개선

1. 서킷 브레이커 패턴 도입
2. 리소스 제한 설정
3. 로그 관리 정책 수립
4. 모니터링 및 알림 강화

---

**보고서 작성일:** 2026-02-06 09:15 (KST)
**작성자:** Claude Code QA Agent
