# stock.ralphpark.com 접속 테스트 보고서

**테스트 일자**: 2026-02-03
**테스트 URL**: https://stock.ralphpark.com/
**테스트 목적**: 외부 도메인 접속 오류 확인

---

## 1. 실행 요약

| 항목 | 상태 | 설명 |
|------|------|------|
| 프론트엔드 페이지 | ✅ 작동 | 메인 페이지, VCP, 차트 페이지 로드 |
| API 시그널 엔드포인트 | ✅ 작동 | `/api/kr/signals` 정상 응답 |
| API 실시간 가격 | ✅ 작동 | `/api/kr/realtime-prices` 정상 응답 |
| API 헬스 체크 | ❌ 404 | `/api/health` 엔드포인트 누락 |
| WebSocket 연결 | ❌ 404 | `/ws` 엔드포인트 프록시 미설정 |

---

## 2. 상세 테스트 결과

### 2.1 프론트엔드 페이지 로딩

| 페이지 | URL | 상태 | 설명 |
|-------|-----|------|------|
| 메인 | `/` | ✅ | "Ralph Stock 대시보드" 표시 |
| VCP | `/dashboard/kr/vcp` | ⚠️ | 로딩 중 (시그널 0개) |
| 차트 | `/chart` | ⚠️ | 로딩 중 (차트 데이터 없음) |

**콘솔 오류**:
- 8개의 404 에러 로그 (상세 URL 미확인)

### 2.2 API 엔드포인트 테스트

| 엔드포인트 | HTTP 상태 | 응답 |
|-----------|----------|------|
| `GET /api/health` | **404** | `{"detail":"Not Found"}` |
| `GET /api/kr/signals?limit=5` | **200** | 5개 시그널 반환 ✅ |
| `POST /api/kr/realtime-prices` | **200** | 실시간 가격 반환 ✅ |

**실시간 가격 응답 예시**:
```json
{
  "prices": {
    "005930": {
      "ticker": "005930",
      "price": 150400.0,
      "change": -5300.0,
      "change_rate": -3.40,
      "volume": 39737461,
      "timestamp": "2026-02-02"
    }
  }
}
```

### 2.3 WebSocket 연결 테스트

| 엔드포인트 | HTTP 상태 | 응답 |
|-----------|----------|------|
| `wss://stock.ralphpark.com/ws` | **404** | `{"detail":"Not Found"}` |

**curl 테스트 결과**:
```bash
$ curl -i -N -H "Upgrade: websocket" https://stock.ralphpark.com/ws
HTTP/2 404
server: openresty
{"detail":"Not Found"}
```

---

## 3. 로컬 vs 외부 비교

| 구분 | 로컬 (localhost:5111) | 외부 (stock.ralphpark.com) |
|------|----------------------|--------------------------|
| API Gateway | ✅ 200 | ✅ 200 (일부 엔드포인트) |
| `/health` | ✅ 200 | ❌ 404 |
| `/ws` | ✅ 연결 | ❌ 404 |
| Nginx | 해당 없음 | openresty 사용 중 |

---

## 4. 문제 분석

### 4.1 심각한 문제 (Critical)

**WebSocket 연결 실패 (404)**
- **증상**: `wss://stock.ralphpark.com/ws` 접속 시 404 오류
- **영향**: 실시간 가격 업데이트, 시그널 브로드캐스트 불가
- **원인**: Nginx Proxy Manager에서 `/ws` 경로에 대한 Custom Location 미설정

### 4.2 중간 문제 (Medium)

**API 헬스 체크 누락 (404)**
- **증상**: `/api/health` 엔드포인트 404 오류
- **영향**: 서비스 상태 모니터링 불가
- **원인**: API Gateway 라우팅 또는 Nginx 프록시 설정 누락

### 4.3 경미한 문제 (Low)

**프론트엔드 콘솔 404 에러**
- **증상**: 8개의 리소스 로드 실패
- **영향**: 일부 UI 기능 작동 안 할 수 있음
- **원인**: 정적 리소스 경로 또는 API 엔드포인트 매칭 문제

---

## 5. Nginx Proxy Manager 설정 확인 필요

### 5.1 현재 상태
- **Proxy Host**: `stock.ralphpark.com` → `172.18.0.1:5111`
- **Websocket Support**: 체크되어 있어야 함
- **Custom Locations**: `/ws` 경로 설정 필요

### 5.2 필요한 설정

**`/ws` Custom Location**:
```nginx
location /ws {
    proxy_pass http://172.18.0.1:5111;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

---

## 6. 해결 방안

### 6.1 WebSocket 연결 복구 (우선순위: 높음)

**옵션 A: Nginx Proxy Manager UI 설정**
1. Proxy Hosts → `stock.ralphpark.com` 선택
2. Custom Locations 탭 → `/ws` 경로 추가
3. Advanced Config에 위 WebSocket 설정 입력

**옵션 B: 자동화 스크립트 사용**
```bash
python scripts/setup_npm_proxy.py
```

### 6.2 API 헬스 체크 복구 (우선순위: 중간)

**API Gateway 라우팅 추가**:
```python
# services/api_gateway/main.py
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}
```

### 6.3 프론트엔드 콘솔 오류 해결 (우선순위: 낮음)

- 브라우저 개발자 도구에서 404 오류 발생 URL 확인
- 해당 리소스가 실제로 필요한지 확인
- 불필요한 요청 제거 또는 경로 수정

---

## 7. 검증 계획

### 7.1 WebSocket 연결 테스트

```bash
# 테스트 1: curl로 연결 확인
curl -i -N -H "Upgrade: websocket" https://stock.ralphpark.com/ws

# 테스트 2: wscat으로 연결 확인 (설치 시)
wscat -c wss://stock.ralphpark.com/ws

# 테스트 3: 브라우저 콘솔 확인
# https://stock.ralphpark.com/dashboard/kr/vcp 페이지에서
# ws = new WebSocket("wss://stock.ralphpark.com/ws");
```

### 7.2 API 엔드포인트 테스트

```bash
# 헬스 체크
curl https://stock.ralphpark.com/api/health

# 시그널 조회
curl https://stock.ralphpark.com/api/kr/signals?limit=1
```

---

## 8. 결론

### 8.1 현재 상태

| 구분 | 상태 |
|------|------|
| 프론트엔드 | ✅ 페이지 로드 가능 |
| REST API | ⚠️ 일부 엔드포인트만 작동 |
| WebSocket | ❌ 연결 불가 |

### 8.2 우선 해결 과제

1. **WebSocket `/ws` 경로 프록시 설정** (최우선)
2. **API `/health` 엔드포인트 복구** (차선)

---

*보고서 작성일: 2026-02-03*
*테스터: Claude Code*
*버전: 1.0*
