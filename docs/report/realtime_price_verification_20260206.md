# 실시간 가격 API 및 WebSocket 데이터 검증 보고서

**날짜:** 2026-02-06
**담당자:** Backend Architect Agent
**목적:** 실시간 가격 API와 WebSocket 데이터의 정확성 검증

---

## 1. API 엔드포인트 검증

### 1.1 정상 작동하는 엔드포인트

#### `/api/kr/realtime-prices` (일괄 조회)

**요청:**
```bash
GET /api/kr/realtime-prices?tickers=005930,000660,035420
```

**응답 예시:**
```json
{
  "prices": {
    "005930": {
      "ticker": "005930",
      "price": 58200.0,
      "change": -200.0,
      "change_rate": -0.3424657534246575,
      "volume": 22198428,
      "timestamp": "2025-02-21"
    },
    "000660": {
      "ticker": "000660",
      "price": 128000.0,
      "change": -1000.0,
      "change_rate": -0.7751937984496124,
      "volume": 15024657,
      "timestamp": "2025-02-21"
    }
  }
}
```

**데이터 타입 검증:**
| 필드 | 타입 | 설명 | 상태 |
|------|------|------|------|
| ticker | string | 종목코드 | ✅ 정상 |
| price | float | 현재가 | ✅ 정상 |
| change | float | 전일 대비 변동 | ✅ 정상 |
| change_rate | float | 등락률 (%) | ✅ 정상 |
| volume | int | 거래량 | ✅ 정상 |
| timestamp | string (YYYY-MM-DD) | 데이터 기준일 | ✅ 정상 |

### 1.2 존재하지 않는 엔드포인트

#### `/api/kr/stocks/{ticker}/realtime-price`

**상태:** ❌ **404 Not Found**

**설명:** 단일 종목 실시간 가격 API가 구현되어 있지 않습니다.
**해결 방안:** 내부 엔드포인트 `/internal/price/{ticker}`를 사용하거나 신규 구현 필요

#### `/internal/price/{ticker}`, `/internal/prices`

**상태:** ❌ **404 Not Found (Nginx Proxy Manager)**

**설명:** Nginx Proxy Manager가 `/internal/*` 경로를 API Gateway로 전달하지 않습니다.
**해결 방안:** NPM 설정에 `/internal/*` Location 추가 필요

---

## 2. WebSocket 메시지 형식 검증

### 2.1 연결 메시지

**클라이언트 → 서버:**
```json
// 연결 요청 (자동)
WebSocket Upgrade: ws://localhost:5111/ws
Origin: http://localhost:5110
```

**서버 → 클라이언트:**
```json
{
  "type": "connected",
  "client_id": "c48a207f-d1b9-48d1-9d4c-d6f3d0c44de5",
  "message": "WebSocket connection established"
}
```

### 2.2 구독 메시지

**클라이언트 → 서버:**
```json
{
  "type": "subscribe",
  "topic": "price:005930"
}
```

**서버 → 클라이언트 (응답):**
```json
{
  "type": "subscribed",
  "topic": "price:005930",
  "message": "Subscribed to price:005930"
}
```

### 2.3 가격 업데이트 메시지

**서버 → 클라이언트:**
```json
{
  "type": "price_update",
  "ticker": "005930",
  "data": {
    "price": 158600,
    "change": -700,
    "change_rate": -0.4394224733207784,
    "volume": 36358081,
    "bid_price": 158600,
    "ask_price": 158600
  },
  "timestamp": "2026-02-06T22:48:44.590151+00:00"
}
```

**WebSocket 데이터 타입 검증:**
| 필드 | 타입 | 설명 | 상태 |
|------|------|------|------|
| type | string | 메시지 타입 | ✅ 정상 |
| ticker | string | 종목코드 | ✅ 정상 |
| data.price | int | 현재가 | ✅ 정상 |
| data.change | int | 전일 대비 변동 | ✅ 정상 |
| data.change_rate | float | 등락률 | ✅ 정상 |
| data.volume | int | 거래량 | ✅ 정상 |
| data.bid_price | int | 매수호가 | ✅ 정상 |
| data.ask_price | int | 매도호가 | ✅ 정상 |
| timestamp | string (ISO 8601) | 타임스탬프 | ✅ 정상 |

### 2.4 하트비트 메시지

**서버 → 클라이언트:**
```json
{
  "type": "ping",
  "timestamp": "2026-02-06T22:48:XX.XXXXXX+00:00"
}
```

**클라이언트 → 서버 (응답):**
```json
{
  "type": "pong"
}
```

---

## 3. 데이터 흐름 검증

### 3.1 정상 흐름 (로컬)

```
1. WebSocket 연결 → 2. 토픽 구독 → 3. 메시지 수신 → 4. 상태 업데이트
```

**검증 결과:** ✅ 정상 작동 확인

### 3.2 API 폴백 동작

**Kiwoom Pipeline 미작동 시:**
- DB에서 최신 일봉 데이터 조회
- `price_broadcaster`가 주기적으로 브로드캐스트

**검증 결과:** ✅ 정상 작동 확인

### 3.3 WebSocket 연결 상태

**로컬 서버:**
```
Active Connections: 3
Subscriptions: 10+ topics
Bridge Running: true (Kiwoom WebSocket)
Broadcaster Running: true
```

---

## 4. 발견된 문제점

### 4.1 🔴 **API vs WebSocket 데이터 불일치**

**문제:**
- `/api/kr/realtime-prices`: DB에 저장된 일봉 종가 반환 (58,200원)
- WebSocket `price:005930`: 실시간 현재가 반환 (158,600원)

**원인:**
- API는 `DailyPrice` 테이블의 최신 데이터를 조회
- WebSocket은 Kiwoom 실시간 스트리밍 또는 DB 최신 데이터를 사용

**영향:**
- 사용자가 API와 WebSocket에서 다른 가격을 볼 수 있음
- 차트 페이지에서 가격 불일치 발생 가능

**해결 방안:**
1. **단기:** API 엔드포인트에 실시간 가격 캐시 사용
   ```python
   # services/api_gateway/main.py 수정
   from src.websocket.server import price_broadcaster

   @app.get("/api/kr/stocks/{ticker}/realtime-price")
   async def get_realtime_price(ticker: str):
       cached = price_broadcaster.get_cached_price(ticker)
       if cached:
           return {"ticker": ticker, **cached}
       # Fallback to DB
   ```

2. **장기:** 실시간 가격 통합 레이어 구현

### 4.2 🟡 **데이터 갭 문제 (소형주)**

**문제:**
- 동서(000020): 최신 데이터 2023-10-05 (2년 이상 경과)
- 일부 소형주는 데이터가 전혀 없음

**원인:**
- 일봉 데이터 수집이 특정 종목에만 집중
- 거래 정지 종목 처리 필요

**해결 방안:**
1. 일봉 수집 대상 종목 확대
2. 거래 정지 종목 필터링 로직 개선

### 4.3 🟡 **Nginx Proxy Manager WebSocket 설정**

**문제:**
- `wss://stock.ralphpark.com/ws` 연결 시 HTTP 403 반환
- `/internal/*` 경로가 프록시되지 않음

**해결 방안:**
```nginx
# NPM Custom Nginx Configuration
location /ws {
    proxy_pass http://112.219.120.75:5111/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /internal/ {
    proxy_pass http://112.219.120.75:5111/internal/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 5. 데이터 타입 비교

### 5.1 API vs WebSocket 데이터 타입

| 필드 | API 타입 | WebSocket 타입 | 호환성 |
|------|----------|----------------|--------|
| ticker | string | string | ✅ |
| price | float | int | ⚠️ float → int 변환 필요 |
| change | float | int | ⚠️ float → int 변환 필요 |
| change_rate | float | float | ✅ |
| volume | int | int | ✅ |
| timestamp | YYYY-MM-DD | ISO 8601 | ⚠️ 형식 불일치 |

### 5.2 프론트엔드 타입 정의 검증

**frontend/types/index.ts:**
```typescript
export interface IRealtimePrice {
  ticker: string
  price: number
  change: number
  change_rate: number
  volume: number
  timestamp?: string
}
```

**검증 결과:** ✅ 인터페이스 정의가 API/WebSocket 데이터와 호환됨

---

## 6. 테스트 종목 결과

| 종목코드 | 종목명 | API 가격 | API 날짜 | WebSocket 가격 | 데이터 상태 |
|----------|--------|----------|----------|----------------|-------------|
| 005930 | 삼성전자 | 58,200원 | 2025-02-21 | 158,600원 | ⚠️ 불일치 |
| 000020 | 동서 | 9,730원 | 2023-10-05 | 실시간 | 🔴 데이터 갭 |
| 000660 | SK하이닉스 | 128,000원 | 2025-02-21 | 실시간 | ✅ 정상 |

---

## 7. 권장 사항

### 7.1 즉시 조치 필요
1. **API 데이터 소스 통일:** WebSocket과 동일한 데이터 소스 사용
2. **NPM 설정 수정:** WebSocket 및 `/internal/*` 경로 프록시 추가

### 7.2 단기 개선 (1주 이내)
1. **단일 종목 실시간 가격 API** 구현
2. **데이터 갭 모니터링** 대시보드 추가
3. **API 응답 캐싱**으로 성능 개선

### 7.3 장기 개선 (1개월 이내)
1. **실시간 가격 통합 레이어** 구현
2. **데이터 수집 대상 종목** 확대
3. **거래 정지 종목** 처리 로직 개선

---

## 8. 결론

1. **WebSocket 구조는 정상** 작동함
2. **API 엔드포인트는 부분적으로** 작동 (일괄 조회 OK, 단일 조회 미구현)
3. **데이터 소스 불일치**가 주요 문제
4. **Nginx Proxy Manager 설정** 필요

**우선순위:**
1. API ↔ WebSocket 데이터 소스 통일
2. NPM 설정 수정
3. 단일 종목 실시간 가격 API 구현

---

*보고서 작성: 2026-02-06*
*검증 환경: 로컬 개발 서버 (localhost:5111)*
