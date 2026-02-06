# Infrastructure Down - 요약 보고서

**분석 일시:** 2026-02-06 09:15 (KST)

---

## 🔴 근본 원인 (한 줄 요약)

**WebSocket 연결 무한 재시도 루프 → API Gateway CPU 102%, 메모리 10GB 사용 → 서비스 응답 불가**

---

## 📊 현재 상태

| 서비스 | 상태 | CPU | 메모리 |
|--------|------|-----|--------|
| api-gateway | 🔴 **CRITICAL** | **102.80%** | **10.23 GB** |
| frontend | 🟢 Healthy | 3.83% | 257 MB |
| 기타 서비스 | 🟢 Healthy | <1% | <100 MB |

---

## 🐛 문제 상세

### 1. WebSocket 연결 실패 무한 루프

```
WebSocket connection timeout
Reconnection failed after 5 attempts
... (22만 개 이상의 로그)
```

- **대상:** `wss://api.kiwoom.com:10000/api/dostk/websocket`
- **문제:** 연결 실패 시 즉시 재시도 (지수 백오프 없음)
- **결과:** CPU 100%, 로그 폭주

### 2. Healthcheck 실패

```json
{
  "Status": "unhealthy",
  "FailingStreak": 397
}
```

### 3. 외부 접속 결과

| 경로 | 결과 |
|------|------|
| `localhost:5111/health` | ✅ 정상 |
| `112.219.120.75:5111/health` | ✅ 정상 |
| `https://stock.ralphpark.com/api/*` | ❌ 타임아웃 (>15s) |
| `wss://stock.ralphpark.com/ws` | ❌ 502 Bad Gateway |

---

## ⚠️ 원인 분석

### 1. 직접적 원인

- Kiwoom WebSocket 연결 실패
- 무한 재시도 로직 (지수 백오프 없음)
- 로그 폭주 (22만 개)

### 2. 2차적 원인

- CPU 고갈로 다른 요청 처리 불가
- 메모리 과다 사용 (10GB)
- Healthcheck 타임아웃

### 3. 코드 문제점

| 문제 | 현재 | 올바른 동작 |
|------|------|-------------|
| 재시도 간격 | 0초 | 1s → 2s → 4s → ... |
| 최대 재시도 | 무한 | 제한 필요 (예: 100회) |
| 로깅 | 매번 | 주기적 요약 |

---

## 🔧 해결 방안

### 즉시 조치 (Emergency)

```bash
# 1. API Gateway 재시작
docker restart api-gateway

# 2. 로그 확인
docker logs -f api-gateway --tail 100

# 3. 상태 확인
curl http://localhost:5111/health
```

### 코드 수정 (Backend)

| 파일 | 수정 내용 | 우선순위 |
|------|----------|----------|
| `src/websocket/client.py` | 지수 백오프 추가 | P0 |
| `src/websocket/client.py` | 최대 재시도 제한 | P0 |
| `src/websocket/client.py` | 로그 레벨 조정 | P1 |

### Nginx Proxy Manager 수정

```nginx
# /ws 경로
location /ws {
    proxy_set_header Connection "upgrade";  # 하드코딩
}

# 현재: Connection $http_connection  # 문제 발생 가능
```

### 장기적 개선

1. 서킷 브레이커 패턴 도입
2. 리소스 제한 설정 (CPU 1코어, 메모리 2GB)
3. 로그 관리 정책 (max-size: 10m, max-file: 3)
4. 모니터링 알림 강화

---

## 📁 보고서 파일

- **상세 보고서:** `docs/report/infrastructure_down_root_cause_20260206.md`
- **요약 보고서:** `docs/report/infrastructure_down_summary_20260206.md` (이 파일)

---

## ✅ 체크리스트 (재발 방지)

- [ ] WebSocket 재시도 로직에 지수 백오프 추가
- [ ] 최대 재시도 횟수 제한 설정
- [ ] 로그 레벨 조정 (INFO → WARNING for retries)
- [ ] Docker 리소스 제한 설정
- [ ] Nginx Connection 헤더 수정
- [ ] CPU/메모리 모니터링 알림 설정
