# 백엔드 수정사항 보고서

**작성 일자:** 2026-02-05
**작성자:** Claude Code (Backend Architect)

---

## 1. Critical (즉시 수정 필요)

### 1.1 Docker Compose Volume Mount 경로 오류

**심각도:** Critical
**영향 서비스:** VCP Scanner, Signal Engine, Chatbot
**파일:** `/docker/compose/services/vcp-scanner.yml`, `/docker/compose/services/signal-engine.yml`, `/docker/compose/services/chatbot.yml`

**문제점:**
```yaml
# 현재 설정 (잘못됨)
volumes:
  - ./services/vcp_scanner:/app/services/vcp_scanner:ro
  - ./src:/app/src:ro
```

docker-compose.yml이 `/docker/compose/` 디렉토리에 있으므로 상대 경로 `./services/vcp_scanner`는 `/docker/compose/services/vcp_scanner`를 가리킵니다. 하지만 실제 소스는 프로젝트 루트의 `/services/vcp_scanner`에 있습니다.

**수정 코드:**
```yaml
# 수정된 설정
volumes:
  - ../../services/vcp_scanner:/app/services/vcp_scanner:ro
  - ../../src:/app/src:ro
```

**파일 위치:**
- `/home/ralph/work/python/kr_stock_analysis/docker/compose/services/vcp-scanner.yml` (라인 20-22)
- `/home/ralph/work/python/kr_stock_analysis/docker/compose/services/signal-engine.yml` (라인 20-22)
- `/home/ralph/work/python/kr_stock_analysis/docker/compose/services/chatbot.yml` (라인 21-23)

**증상:**
```
ERROR: Error loading ASGI app. Could not import module "services.vcp_scanner.main".
```

---

### 1.2 중복 API Gateway 컨테이너

**심각도:** Critical
**영향 서비스:** API Gateway
**컨테이너:** `api-gateway`, `compose-api-gateway-1`

**문제점:**
두 개의 API Gateway 컨테이너가 실행 중입니다.
- `api-gateway`: 네트워크에 연결되지 않음, 포트 매핑 없음
- `compose-api-gateway-1`: 정상 작동, 포트 5111 매핑됨

**수정 방법:**
```bash
# 중복 컨테이너 제거
docker stop api-gateway
docker rm api-gateway

# 또는 compose만 사용하도록 설정
docker compose down
docker compose up -d
```

---

### 1.3 Celery Tasks Import 오류

**심각도:** Critical
**영향:** 종가베팅 V2 기능
**파일:** `/services/api_gateway/routes/jongga_v2.py` (라인 229)

**문제점:**
```python
# 현재 코드
from tasks.signal_tasks import generate_jongga_signals
```

**증상:**
```json
{
  "status": "error",
  "code": 500,
  "detail": "종가베팅 V2 엔진 실행 실패: No module named 'tasks'"
}
```

**수정 코드:**
```python
# 옵션 1: 절대 경로 사용
from ralph_stock_lib.tasks.signal_tasks import generate_jongga_signals

# 옵션 2: 상대 경로 사용
try:
    from tasks.signal_tasks import generate_jongga_signals
except ImportError:
    from ralph_stock_lib.tasks.signal_tasks import generate_jongga_signals

# 옵션 3: 환경 변수로 모듈 경로 설정
import os
import sys
sys.path.insert(0, os.getenv("TASKS_MODULE_PATH", "/app/tasks"))
from tasks.signal_tasks import generate_jongga_signals
```

---

## 2. High (중요 수정)

### 2.1 Service Registry 서비스 연결 불가

**심각도:** High
**영향:** VCP Scanner, Signal Engine, Chatbot 프록시
**파일:** `/services/api_gateway/service_registry.py`

**문제점:**
`api-gateway` 컨테이너에서 Docker 네트워크 외부에 있어 `vcp-scanner`, `signal-engine`, `chatbot` 서비스에 접근할 수 없습니다.

**수정 제안:**
1. 모든 서비스가 `ralph-network`에 연결되도록 확인
2. `compose-api-gateway-1`만 사용하도록 중복 컨테이너 제거
3. 환경 변수 확인:
   ```bash
   # docker-compose.yml 또는 .env 파일에서
   VCP_SCANNER_URL=http://vcp-scanner:5112
   SIGNAL_ENGINE_URL=http://signal-engine:5113
   CHATBOT_SERVICE_URL=http://chatbot:5114
   DAYTRADING_SCANNER_URL=http://daytrading-scanner:5115
   ```

---

### 2.2 데이터베이스 데이터 부족

**심각도:** High
**영향:** 차트, 시그널, 성과 분석 기능

**문제점:**
| 테이블 | 레코드 수 |
|--------|-----------|
| daily_prices | 0 |
| signals | 0 |
| daytrading_signals | 0 |
| market_status | 0 |

**수정 제안:**
1. 과거 차트 데이터 수집 태스크 실행
2. 실시간 가격 데이터 수집 확인
3. 시그널 생성 스케줄러 확인
4. Market Status 수집 태스크 실행

---

### 2.3 엔드포인트 경로 불일치

**심각도:** High
**영향:** API 클라이언트 (프론트엔드)

**문제점:**
프론트엔드에서 호출하는 경로와 실제 엔드포인트 경로가 다릅니다.

| 호출 경로 | 실제 경로 | 상태 |
|-----------|-----------|------|
| /api/kr/chart/{ticker} | /api/kr/stock-chart/{ticker} | 404 |
| /api/stocks/{ticker} | /api/kr/stocks/{ticker} | 404 |
| /api/vcp/signals | /api/kr/scan/signals | 404 |
| /api/vcp/analyze/{ticker} | 존재하지 않음 | 404 |
| /api/vcp/scan | /api/kr/scan/vcp | 404 |
| /api/chat/history | 존재하지 않음 | 404 |
| /api/chatbot/sessions | 존재하지 않음 | 404 |
| /api/ai/analyze | 존재하지 않음 | 404 |

**수정 제안:**
1. 프론트엔드 API 호출 경로 수정
2. 또는 백엔드에 별칭 엔드포인트 추가
3. API 문서 업데이트

---

## 3. Medium (개선 제안)

### 3.1 CORS 설정 확인

**심각도:** Medium
**파일:** `/services/api_gateway/main.py` (라인 454-480)

**현재 설정:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5110",
        "http://127.0.0.1:5110",
        "https://stock.ralphpark.com",
        # ... 기타 도메인
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**확인 필요:**
- WebSocket origin 허용 (`wss://stock.ralphpark.com`)
- 개발 환경에서 로컬 프론트엔드 접근 허용

---

### 3.2 WebSocket 연결 테스트

**심각도:** Medium

**테스트 필요:**
```javascript
// WebSocket 연결 테스트
const ws = new WebSocket('wss://stock.ralphpark.com/ws');

ws.onopen = () => {
  console.log('WebSocket connected');
  // 구독 메시지 전송
  ws.send(JSON.stringify({
    type: 'subscribe',
    topic: 'market-gate'
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', event.data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

---

### 3.3 에러 처리 개선

**심각도:** Medium

**현재 문제:**
- 서비스 연결 실패 시 상세 에러 메시지 부족
- 404 에러 시 올바른 엔드포인트 안내 부족

**개선 제안:**
```python
# 에러 응답 개선 예시
@app.exception_handler(httpx.RequestError)
async def service_unavailable_handler(request: Request, exc: httpx.RequestError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service Unavailable",
            "message": f"Unable to reach service: {str(exc)}",
            "available_services": registry.list_services()
        }
    )
```

---

## 4. Low (사소한 문제)

### 4.1 API Gateway 로그 설정

**심각도:** Low

**개선 제안:**
- DEBUG 레벨 로그 감소
- 요청/응답 로그 포맷 표준화
- 성능 모니터링 로그 추가

---

### 4.2 Health Check 개선

**심각도:** Low

**개선 제안:**
```python
# 상세 헬스 체크 응답
{
    "status": "healthy",
    "services": {
        "database": {"status": "up", "latency_ms": 5},
        "redis": {"status": "up", "latency_ms": 1},
        "vcp-scanner": {"status": "up", "last_check": "2026-02-05T02:00:00"},
        "signal-engine": {"status": "down", "error": "Connection timeout"},
        "chatbot": {"status": "up", "latency_ms": 15}
    }
}
```

---

## 5. 수정 우선순위

1. **즉시 실행 (금일 내):**
   - [ ] Docker 볼륨 마운트 경로 수정
   - [ ] 중복 API Gateway 컨테이너 제거
   - [ ] Celery tasks import 경로 수정

2. **중기 실행 (주간 내):**
   - [ ] 데이터베이스 데이터 수집
   - [ ] 엔드포인트 경로 표준화
   - [ ] Service Registry 연결 확인

3. **장기 개선 (월간 내):**
   - [ ] 에러 처리 개선
   - [ ] WebSocket 연결 테스트
   - [ ] API 문서 업데이트

---

## 6. 테스트 확인清单

수정 후 다음 항목을 재테스트해야 합니다:

- [ ] VCP Scanner health 체크 (http://localhost:5112/health)
- [ ] Signal Engine health 체크 (http://localhost:5113/health)
- [ ] Chatbot health 체크 (http://localhost:5114/health)
- [ ] 종가베팅 V2 실행 (POST /api/kr/jongga-v2/run)
- [ ] 차트 데이터 조회 (GET /api/kr/stocks/{ticker}/chart)
- [ ] WebSocket 연결 및 메시지 송수신

---

*수정사항 보고서 작성: 2026-02-05*
