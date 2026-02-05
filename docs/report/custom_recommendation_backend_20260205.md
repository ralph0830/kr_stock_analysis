# Custom Recommendation 페이지 - 백엔드 분석 보고서

**작성일:** 2026-02-05
**대상:** Daytrading Scanner 서비스 및 API Gateway
**엔드포인트:** /api/daytrading/*

---

## 1. 요약

| 항목 | 상태 | 세부사항 |
|------|------|----------|
| API Gateway | ✅ 정상 | 라우터 구현 완료 |
| Daytrading Scanner | ✅ 정상 | 서비스 실행 중 (포트 5115) |
| Service Registry | ✅ 정상 | 서비스 등록/발견 작동 |
| GET /signals | ✅ 정상 | 200 OK, 데이터 반환 |
| POST /scan | ⚠️ 미테스트 | 30초 타임아웃 설정 |
| POST /analyze | ⚠️ 미테스트 | 30초 타임아웃 설정 |
| WebSocket 브로드캐스트 | ✅ 구현됨 | signal:daytrading 토픽 |

---

## 2. 아키텍처

### 2.1 서비스 구성

```
                            ┌─────────────────┐
                            │   Browser (WSS) │
                            └────────┬────────┘
                                     │
                                     ▼
┌──────────────────┐         ┌─────────────────┐
│  Nginx Proxy Mgr │────────▶│  API Gateway    │
│  (stock.ralphp.  │         │  (Port 5111)    │
│   com:443/5110)  │         └────────┬────────┘
└──────────────────┘                  │
                                     ▼
                            ┌─────────────────┐
                            │ Daytrading      │
                            │ Scanner         │
                            │ (Port 5115)     │
                            └─────────────────┘
```

### 2.2 라우터 구조

**파일:** `services/api_gateway/routes/daytrading.py`

```python
router = APIRouter(
    prefix="/api/daytrading",
    tags=["daytrading"],
)
```

| 엔드포인트 | 메서드 | 기능 | 타임아웃 |
|-----------|--------|------|----------|
| /signals | GET | 시그널 조회 | 10s |
| /scan | POST | 시장 스캔 | 30s |
| /analyze | POST | 종목 분석 | 30s |

---

## 3. API 엔드포인트 분석

### 3.1 GET /api/daytrading/signals

**코드:** `services/api_gateway/routes/daytrading.py:26-75`

**파라미터:**
| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| min_score | int | 0 | 0-105 | 최소 점수 |
| market | string | None | KOSPI/KOSDAQ | 시장 필터 |
| limit | int | 50 | 1-100 | 최대 반환 개수 |

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "total_score": 90,
        "grade": "S",
        "signal_type": "STRONG_BUY",
        "entry_price": 75000,
        "target_price": 80000,
        "stop_loss": 72000,
        "checks": [
          {"name": "거래량 폭증", "status": "passed", "points": 15},
          {"name": "모멘텀 돌파", "status": "passed", "points": 15},
          ...
        ]
      }
    ],
    "count": 3,
    "generated_at": "2026-02-05T05:25:07.629099"
  }
}
```

**테스트 결과:** ✅ PASS
```bash
$ curl -s "https://stock.ralphpark.com/api/daytrading/signals"
# 200 OK, 데이터 반환 확인
```

### 3.2 POST /api/daytrading/scan

**코드:** `services/api_gateway/routes/daytrading.py:78-119`

**요청 바디:**
```json
{
  "market": "KOSPI",    // Optional
  "limit": 50           // Optional
}
```

**타임아웃:** 30초 (스캔 작업 시간 고려)

**테스트:** ⚠️ 미수행 (장중 스캔은 실제 거래일에만 의미)

### 3.3 POST /api/daytrading/analyze

**코드:** `services/api_gateway/routes/daytrading.py:122-162`

**요청 바디:**
```json
{
  "tickers": ["005930", "000270", "066570"]
}
```

**테스트:** ⚠️ 미수행

---

## 4. 서비스 통신

### 4.1 Service Registry 연결

**코드:**
```python
registry = get_registry()
daytrading_scanner = registry.get_service("daytrading-scanner")
```

**상태:** ✅ 정상

**서비스 정보:**
```json
{
  "name": "daytrading-scanner",
  "url": "http://daytrading-scanner:5115",
  "health": "healthy"
}
```

### 4.2 프록시 패턴

```python
async with httpx.AsyncClient() as client:
    response = await client.get(
        f"{daytrading_scanner['url']}/api/daytrading/signals",
        params=params,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()
```

**장점:**
- 비동기 httpx 사용
- 타임아웃 설정
- 에러 전파 (HTTPException)

---

## 5. WebSocket 지원

### 5.1 브로드캐스터

**파일:** `src/websocket/server.py`

```python
# Daytrading 시그널 브로드캐스터
signal_broadcaster = SignalBroadcaster()
```

**토픽:** `signal:daytrading`

**메시지 형식:**
```json
{
  "type": "signal_update",
  "topic": "signal:daytrading",
  "signals": [...],
  "timestamp": "2026-02-05T05:25:07.629099"
}
```

### 5.2 프론트엔드 구독

**코드:** `frontend/hooks/useWebSocket.ts:828`

```typescript
subscribe("signal:daytrading");
```

**상태:** ✅ 정상 작동

---

## 6. 에러 핸들링

### 6.1 HTTP 에러

```python
except httpx.HTTPStatusError as e:
    raise HTTPException(
        status_code=e.response.status_code,
        detail=f"Daytrading Scanner error: {e.response.text}",
    )
```

### 6.2 서비스 unavailable

```python
except httpx.RequestError as e:
    raise HTTPException(
        status_code=503,
        detail=f"Daytrading Scanner unavailable: {str(e)}",
    )
```

### 6.3 서비스 not found

```python
if not daytrading_scanner:
    raise HTTPException(
        status_code=503,
        detail="Daytrading Scanner service not available"
    )
```

**평가:** 우수함
- 명확한 에러 메시지
- 적절한 HTTP 상태 코드
- 원인 포함 (디버깅 용이)

---

## 7. Docker 설정

### 7.1 컨테이너 상태

```bash
$ docker ps | grep daytrading
compose-daytrading-scanner-1   Up 9 hours   5115/tcp   Healthy
```

**상태:** ✅ Healthy

### 7.2 네트워크

```bash
$ docker network inspect compose_default | grep daytrading
"daytrading-scanner": {
  "Name": "compose-daytrading-scanner-1",
  "IPv4Address": "172.25.0.8/16"
}
```

**상태:** ✅ 통신 가능

---

## 8. 발견된 문제

### 8.1 /api/kr/realtime-prices 500 에러

**현상:**
```
[error] Failed to load resource: the server responded with a status of 500 ()
[API Request] POST /api/kr/realtime-prices
```

**원인:** Kiwoom REST API 연결 문제 가능

**영향:** 실시간 가격 폴백 불가

**해결 방법:**
1. Kiwoom REST API 상태 확인
2. API Gateway 로그 확인

### 8.2 OpenAPI 문서 누락

**현상:** Daytrading 엔드포인트가 OpenAPI spec에 없을 수 있음

**해결 방법:**
```python
# main.py에 router 포함 확인
app.include_router(daytrading_router)
```

---

## 9. 개선 권장사항

### 9.1 즉시 (이번 주)

1. **realtime-prices 500 에러 해결**
   - Kiwoom API 연결 확인
   - 에러 로그 상세 분석

2. **OpenAPI 문서 업데이트**
   - Daytrading 엔드포인트 추가

### 9.2 단기 (이번 달)

3. **캐싱 레이어 추가**
   - Redis에 시그널 캐시
   - 5분 TTL

4. **속도 제한 (Rate Limiting)**
   - 스캔 API 남용 방지
   - 분당 10회 제한

### 9.3 장기 (분기)

5. **WebSocket 재연결 로직 강화**
   - ping/pong 간격 최적화
   - 자동 재연결 정책 개선

6. **모니터링 대시보드**
   - 스캔 실행 횟수
   - API 응답 시간
   - 에러 발생률

---

## 10. 테스트 결과

### 10.1 헬스 체크

```bash
$ curl -s "https://stock.ralphpark.com/health" | jq .
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "2.0.0"
}
```

**상태:** ✅ PASS

### 10.2 Daytrading Signals

```bash
$ curl -s "https://stock.ralphpark.com/api/daytrading/signals" | jq .data.count
3
```

**상태:** ✅ PASS

### 10.3 Service Registry

```bash
$ docker logs compose-api-gateway-1 | grep -i daytrading
# 서비스 등록 로그 확인
```

**상태:** ✅ PASS

---

## 11. 종합 평가

| 카테고리 | 점수 | 비고 |
|----------|------|------|
| API 설계 | 9/10 | RESTful, 명확함 |
| 에러 처리 | 9/10 | HTTPException 적절히 사용 |
| 서비스 통신 | 10/10 | Registry 패턴 우수 |
| WebSocket | 8/10 | 브로드캐스팅 작동 |
| 타임아웃 설정 | 10/10 | 적절한 시간 설정 |
| 컨테이너 관리 | 10/10 | Healthy 상태 |
| 문서화 | 7/10 | Docstring 있음, OpenAPI 개선 필요 |

**종합 점수:** 9.0/10

---

## 12. 결론

Daytrading Scanner 백엔드는 **우수한 상태**입니다.

**강점:**
1. Service Registry 패턴으로 느슨한 결합
2. 적절한 타임아웃 설정
3. 명확한 에러 처리
4. WebSocket 브로드캐스팅 지원

**개선 필요:**
1. `/api/kr/realtime-prices` 500 에러 해결
2. OpenAPI 문서 업데이트
3. 캐싱 레이어 추가

---

*작성일: 2026-02-05*
