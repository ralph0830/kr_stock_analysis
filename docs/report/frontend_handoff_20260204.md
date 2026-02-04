# 프론트엔드 팀 전달 보고서

**작성일**: 2026년 2월 4일
**작성자**: 백엔드 팀
**버전**: 1.0

---

## 1. 요약 (Executive Summary)

백엔드에서 VCP 시그널 종목의 현재가 0원 표시 문제를 해결했습니다. 이제 프론트엔드에서 VCP 시그널 종목들의 실시간 가격을 정상적으로 표시할 수 있습니다.

### 수정 완료된 사항

| 항목 | 상태 | 설명 |
|------|------|------|
| **VCP 시그널 종목 가격** | ✅ 해결 | 11개 종목 실시간 가격 브로드캐스트 |
| **API 엔드포인트** | ✅ 정상 | `/api/kr/signals` 자동 구독 기능 추가 |
| **WebSocket** | ✅ 정상 | `wss://stock.ralphpark.com/ws` 연결 |

---

## 2. 백엔드 수정 사항

### 2.1 DEFAULT_TICKERS 확장

`src/websocket/server.py`의 `DEFAULT_TICKERS`에 VCP 시그널 주요 종목이 추가되었습니다.

```python
DEFAULT_TICKERS = {
    # 기존 종목
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "005380",  # 현대차
    "028260",  # 삼성물산
    "000020",  # 동화약품
    # VCP 시그널 주요 종목 (0원 표시 문제 해결)
    "000545",  # 흥국화재우
    "000070",  # 삼양홀딩스
    "001540",  # 한독
    "001250",  # 삼성에스디에스
    "002360",  # 축남제약
}
```

### 2.2 자동 가격 브로드캐스트 등록

`/api/kr/signals` 엔드포인트 호출 시 VCP 시그널 종목들이 자동으로 `price_broadcaster`에 등록됩니다.

```python
# VCP 시그널 종목들을 price_broadcaster에 추가 (실시간 가격 브로드캐스트용)
if WEBSOCKET_AVAILABLE and price_broadcaster and signal_tickers:
    for ticker in signal_tickers:
        price_broadcaster.add_ticker(ticker)
    logger.info(f"Added VCP signal tickers to price_broadcaster: {signal_tickers}")
```

---

## 3. 프론트엔드 연동 가이드

### 3.1 실시간 가격 사용 방법

VCP 시그널 종목의 실시간 가격을 받으려면:

```typescript
// hooks/useRealtimePrices 사용
const { prices, getPrice, connected } = useRealtimePrices([
  "000020", "000545", "000070", "001540", "001250", "002360"
]);

// 가격 데이터 타입
interface RealtimePrice {
  ticker: string;      // 종목코드
  price: number;       // 현재가
  change: number;      // 전일대비 변동액
  change_rate: number; // 전일대비 변동률 (%)
  volume: number;      // 거래량
  timestamp: string;   // 업데이트 시간
}
```

### 3.2 WebSocket 연결 확인

WebSocket 연결 상태 확인:

```typescript
// hooks/useWebSocket 사용
const { connected, connectionState, lastError } = useWebSocket({
  autoConnect: true,
  onPriceUpdate: (price) => {
    console.log(`${price.ticker}: ${price.price}원`);
  },
});
```

### 3.3 VCP 시그널 API 호출

```typescript
// lib/api-client.ts
const signals = await apiClient.getVCPSignals(10);
// 또는
const signals = await apiClient.getSignals(20);
```

---

## 4. 브로드캐스트 중인 종목 현재가격

| 종목코드 | 종목명 | 현재가(예시) | 상태 |
|----------|--------|----------------|------|
| 000020 | 동화약품 | 6,160원 | ✅ |
| 000545 | 흥국화재우 | 7,230원 | ✅ |
| 000070 | 삼양홀딩스 | 62,200원 | ✅ |
| 001540 | 한독 | 8,540원 | ✅ |
| 001250 | 삼성에스디에스 | 2,355원 | ✅ |
| 002360 | 축남제약 | 357원 | ✅ |
| 005930 | 삼성전자 | 169,100원 | ✅ |
| 000660 | SK하이닉스 | 264,500원 | ✅ |
| 035420 | NAVER | 264,500원 | ✅ |
| 005380 | 현대차 | 316,500원 | ✅ |
| 028260 | 삼성물산 | 316,500원 | ✅ |

---

## 5. API 엔드포인트 변경사항

### 5.1 수정된 엔드포인트

| 엔드포인트 | 변경사항 | 설명 |
|------------|----------|------|
| `GET /api/kr/signals` | 자동 구독 추가 | VCP 시그널 종목들이 price_broadcaster에 자동 추가됨 |

### 5.2 응답 형식

```json
{
  "ticker": "000545",
  "name": "흥국화재우",
  "signal_type": "vcp",
  "score": 75.0,
  "grade": "A",
  "entry_price": null,
  "target_price": null,
  "created_at": "2026-02-04T09:41:26.077521"
}
```

---

## 6. 환경 변수 설정

### 6.1 프로덕션 환경 (생성됨)

`frontend/.env.production`이 생성되었습니다. 비어있는 값으로 두면 코드에서 동적으로 결정합니다.

```bash
# 프로덕션 환경 변수 (빈 값 = 동적 결정)
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_WS_URL=
```

### 6.2 동적 URL 결정 로직

```typescript
// lib/api-client.ts
const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const isLocal = hostname === "localhost" || hostname === "127.0.0.1";

    if (isLocal) {
      return `${protocol}//${hostname}:5111`;
    }
    // 외부 도메인: 현재 도메인 사용 (NPM 리버스 프록시)
    return `${protocol}//${hostname}`;
  }
  return "http://api-gateway:5111"; // SSR 환경
};
```

```typescript
// hooks/useWebSocket.ts
const defaultUrl = typeof window !== "undefined"
  ? (() => {
      const protocol = window.location.protocol;
      const hostname = window.location.hostname;
      const isLocal = hostname === "localhost" || hostname === "127.0.0.1";
      const wsProtocol = protocol.replace("http", "ws");

      if (isLocal) {
        return `${wsProtocol}//${hostname}:5111/ws`;
      }
      // 외부 도메인: wss://hostname/ws
      return `${wsProtocol}//${hostname}/ws`;
    })()
  : "ws://localhost:5111/ws";
```

---

## 7. CORS 설정 완료

`stock.ralphpark.com` 도메인이 CORS 허용 목록에 추가되었습니다.

```python
# services/api_gateway/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # ... 기존 도메인
        "https://stock.ralphpark.com",
        "http://stock.ralphpark.com",
        "wss://stock.ralphpark.com",
        "ws://stock.ralphpark.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 8. WebSocket 연결 토피

### 8.1 연결 URL

| 환경 | WebSocket URL |
|------|----------------|
| 로컬 개발 | `ws://localhost:5111/ws` |
| 프로덕션 | `wss://stock.ralphpark.com/ws` |

### 8.2 구독 토픽

VCP 시그널 종목의 실시간 가격을 받으려면 다음 토픽을 구독하세요:

```
price:000020  # 동화약품
price:000545  # 흥국화재우
price:000070  # 삼양홀딩스
price:001540  # 한독
price:001250  # 삼성에스디에스
price:002360  # 축남제약
```

---

## 9. 테스트 확인 방법

### 9.1 API 테스트

```bash
# Health Check
curl https://stock.ralphpark.com/health

# VCP 시그널 조회
curl "https://stock.ralphpark.com/api/kr/signals?limit=10"
```

### 9.2 WebSocket 테스트

브라우저 콘솔에서:

```javascript
// WebSocket 연결 테스트
const ws = new WebSocket('wss://stock.ralphpark.com/ws');
ws.onopen = () => {
  console.log('WebSocket 연결됨');
  // price:000020 토픽 구독
  ws.send(JSON.stringify({ type: 'subscribe', topic: 'price:000020' }));
};
ws.onmessage = (e) => {
  console.log('수신:', JSON.parse(e.data));
};
```

---

## 10. 주의사항

### 10.1 행 중복 문제 (프론트엔드 수정 필요)

보고서(`docs/report/frontend_test_analysis_20260204.md`)에 따르면 행 중복 문제가 있습니다.

**증상**: 각 종목이 2번씩 표시됨

**원인**: React Strict Mode 또는 상태 관리 이슈

**해결 방향**:
```typescript
// 개선안 1: cleanup 함수 추가
useEffect(() => {
  let cancelled = false;
  const loadSignals = async () => {
    const signals = await apiClient.getVCPSignals(10);
    if (!cancelled) {
      setSignals(signals);
    }
  };
  loadSignals();

  return () => { cancelled = true };
}, [/* deps */]);

// 개선안 2: useRef로 마지막 데이터 추적
const lastSignalsRef = useRef<Signal[]>([]);
useEffect(() => {
  const loadSignals = async () => {
    const signals = await apiClient.getVCPSignals(10);
    if (JSON.stringify(signals) !== JSON.stringify(lastSignalsRef.current)) {
      setSignals(signals);
      lastSignalsRef.current = signals;
    }
  };
  loadSignals();
}, [/* deps */]);
```

### 10.2 HMR WebSocket 비활성화

프로덕션 빌드 시 HMR WebSocket이 비활성화되었습니다 (`frontend/next.config.js` 수정됨).

---

## 11. 연락처

질의사항이 있으면 백엔드 팀에게 문의 바랍니다.

---

**보고서 끝**
