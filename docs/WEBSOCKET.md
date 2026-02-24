# WebSocket 설정 가이드

**버전:** 1.1.0
**최종 수정:** 2026-02-23

---

## 목차

1. [개요](#1-개요)
2. [External Domain Support](#2-external-domain-support)
3. [WebSocket Endpoint](#3-websocket-endpoint)
4. [Middleware Compatibility](#4-middleware-compatibility)
5. [CORS Configuration](#5-cors-configuration)

---

## 1. 개요

이 프로젝트는 FastAPI WebSocket을 사용하여 실시간 데이터를 전송합니다.

**지원하는 실시간 데이터:**
- 실시간 가격 업데이트 (Kiwoom API)
- 지수 업데이트 (KOSPI, KOSDAQ)
- Market Gate 상태 변경
- VCP 시그널 업데이트

---

## 2. External Domain Support

### 2.1 동적 URL 결정

프론트엔드는 현재 접속한 도메인을 기반으로 동적으로 API/WebSocket URL을 결정합니다:

```typescript
// frontend/lib/api-client.ts
const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;

    const isLocal = hostname === "localhost" || hostname === "127.0.0.1";

    if (isLocal) {
      return `${protocol}//${hostname}:5111`;
    }

    return `${protocol}//${hostname}`;
  }

  return "http://api-gateway:5111";  // SSR 환경
};
```

### 2.2 URL 매핑

| 환경 | 프론트엔드 URL | WebSocket URL |
|------|----------------|----------------|
| 로컬 개발 | `http://localhost:5110` | `ws://localhost:5111/ws` |
| 외부 도메인 | `http://ralphpark.com:5110` | `ws://ralphpark.com:5111/ws` |
| HTTPS | `https://stock.ralphpark.com` | `wss://stock.ralphpark.com/ws` |

---

## 3. WebSocket Endpoint

### 3.1 연결 정보

| 항목 | 값 |
|------|-----|
| **URL** | `ws://{domain}:5111/ws` 또는 `wss://{domain}:5111/ws` |
| **서버** | API Gateway (FastAPI WebSocket) |
| **Heartbeat** | 30초 간격 ping/pong |
| **재연결** | 최대 10회 시도 (exponential backoff) |

### 3.2 WebSocket 메시지 타입

```typescript
// frontend/types/index.ts
export type WSMessageType =
  | "connected"           // 연결 확인
  | "subscribed"          // 구독 확인
  | "unsubscribed"        // 구독 해지
  | "price_update"        // 가격 업데이트
  | "index_update"        // 지수 업데이트
  | "market_gate_update"  // Market Gate 업데이트
  | "signal_update"       // VCP/Daytrading 시그널 업데이트
  | "error"               // 에러
  | "ping"                // 핑
  | "pong"                // 퐁;
```

### 3.3 구독 토픽

| 토픽 | 설명 | 예시 |
|------|------|------|
| `price:{ticker}` | 종목 가격 | `price:005930` |
| `market:{name}` | 지수 | `market:kospi`, `market:kosdaq` |
| `market-gate` | Market Gate 상태 | - |
| `signal:vcp` | VCP 시그널 | - |
| `signal:daytrading` | Daytrading 시그널 | - |

---

## 4. Middleware Compatibility

### 4.1 중요: BaseHTTPMiddleware 제약

**FastAPI의 `BaseHTTPMiddleware`는 WebSocket 연결을 지원하지 않습니다.**

모든 커스텀 미들웨어는 WebSocket 요청을 건너뛰도록 구현되어야 합니다.

### 4.2 WebSocket 요청 감지

```python
def _is_websocket_request(self, request: Request) -> bool:
    """WebSocket 요청인지 확인"""
    # 1. 경로 기반 확인
    if request.url.path.startswith("/ws"):
        return True

    # 2. 헤더 기반 확인
    upgrade_header = request.headers.get("upgrade", "").lower()
    return upgrade_header == "websocket"
```

### 4.3 WebSocket을 지원하는 미들웨어

| 미들웨어 | 파일 | 상태 |
|----------|------|------|
| RequestIDMiddleware | `src/middleware/request_id.py` | ✅ 스킵 구현됨 |
| RequestLoggingMiddleware | `src/middleware/logging_middleware.py` | ✅ 스킵 구현됨 |
| MetricsMiddleware | `src/middleware/metrics_middleware.py` | ✅ 스킵 구현됨 |
| SlowEndpointMiddleware | `src/middleware/slow_endpoint.py` | ✅ 스킵 구현됨 |

### 4.4 미들웨어 스킵 예시

```python
# src/middleware/request_id.py
class RequestIDMiddleware:
    async def dispatch(self, request: Request, call_next):
        # WebSocket 요청 스킵
        if self._is_websocket_request(request):
            return await call_next(request)

        # 일반 요청만 처리
        request_id = generate_request_id()
        request.state.request_id = request_id
        response = await call_next(request)
        return response
```

---

## 5. CORS Configuration

### 5.1 외부 도메인에서 접속 시

외부 도메인에서 접속 시 CORS 설정에 추가 필요합니다.

### 5.2 CORS 설정

```python
# services/api_gateway/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # 로컬 개발
        "http://localhost:5110",
        "http://127.0.0.1:5110",
        "http://localhost:3000",
        "http://127.0.0.1:3000",

        # 외부 도메인
        "https://ralphpark.com",
        "http://ralphpark.com",
        "https://ralphpark.com:5110",
        "http://ralphpark.com:5110",
        "https://ralphpark.com:5111",
        "http://ralphpark.com:5111",
        "https://stock.ralphpark.com",
        "http://stock.ralphpark.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5.3 WebSocket CORS

WebSocket은 별도의 CORS 처리가 필요 없습니다 (HTTP Upgrade 요청으로 처리).

---

## 관련 문서

- [Open Architecture](OPEN_ARCHITECTURE.md) - 전체 아키텍처
- [Nginx Proxy Setup](NGINX_PROXY_SETUP.md) - 역프록시 설정
