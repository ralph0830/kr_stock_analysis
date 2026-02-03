# 실시간 가격 모니터링 기능 재분석 보고서

**분석 일자**: 2026-02-03
**분석 유형**: 재분석 (Root Cause 재확인)
**심각도**: 높음 (기능 미작동)

---

## 1. 실행 요약

### 1.1 이전 보고서와의 차이

| 항목 | 이전 보고서 | 재분석 결과 |
|------|-------------|-------------|
| 원인 | 구독 타이밍 문제 | **데이터 불일치** |
| 해결 방안 | 연결 확인 로직 추가 | **종목 변경 또는 ELW 지원** |

### 1.2 핵심 발견

**시그널 종목(ELW)과 브로드캐스터 종목(KOSPI 대종목)이 다릅니다!**

```
시그널 종목 (브로드캐스터 안 됨):
├── 0015N0 (아로마티카) - ELW
├── 493330 (지에프아이) - ELW
└── 217590 (티엠씨) - ELW

브로드캐스터 종목 (실시간 지원):
├── 005930 (삼성전자)
├── 000660 (SK하이닉스)
├── 035420 (NAVER)
├── 005380 (현대차)
├── 028260 (삼성물산)
└── 000020 (동화약품)
```

### 1.3 근본 원인

**시스템 설계 제약**:
1. 시그널 데이터가 ELW 종목에서 발생
2. 실시간 가격 브로드캐스터는 KOSPI 대종목만 지원
3. ELW 종목은 현재 시스템에서 실시간 가격 지원 안 함

---

## 2. 상세 분석

### 2.1 시그널 데이터 확인

#### API 응답
```bash
$ curl http://localhost:5111/api/kr/signals?limit=6
```

```json
[
  {
    "ticker": "0015N0",
    "name": "아로마티카",
    "signal_type": "bullish",
    ...
  },
  {
    "ticker": "493330",
    "name": "지에프아이",
    "signal_type": "bullish",
    ...
  },
  {
    "ticker": "217590",
    "name": "티엠씨",
    ...
  }
]
```

**모든 상위 시그널 종목이 ELW입니다!**

### 2.2 브로드캐스터 설정 확인

#### 백엔드 코드
```python
# src/websocket/server.py:259-261
class PriceUpdateBroadcaster:
    # 기본 종목 (마켓 개장 시 항상 포함)
    # 삼성전자, SK하이닉스, NAVER, 현대차, 삼성물산, 동화약품
    DEFAULT_TICKERS = {"005930", "000660", "035420", "005380", "028260", "000020"}
```

### 2.3 구독 처리 로직 확인

#### 백엔드 구독 처리
```python
# src/websocket/server.py:144-177
def subscribe(self, client_id: str, topic: str) -> None:
    # ...

    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ticker는 6자리 숫자여야 함
        if ticker.isdigit() and len(ticker) == 6:  # ← 문제!
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
```

**ELW 종목 코드 예시**:
- `0015N0` - `isdigit()` = False ('N' 포함)
- `493330` - `isdigit()` = True ✓
- `217590` - `isdigit()` = True ✓

따라서 일부 ELW 종목은 체크를 통과하지만, Kiwoom WebSocket 브리지에서 ELW 종목을 지원하지 않을 수 있습니다.

### 2.4 서버 로그 분석

#### 브로드캐스트 로그
```bash
$ docker logs api-gateway | grep "BROADCAST"
```

```
[BROADCAST] Topic=price:005930, subscribers=0
[BROADCAST] Topic=price:000660, subscribers=0
[BROADCAST] Topic=price:005380, subscribers=0
[BROADCAST] Topic=price:000020, subscribers=0
```

- 브로드캐스터는 KOSPI 대종목 가격을 전송 중
- 하지만 구독자가 0명

#### WebSocket 통계
```bash
$ curl http://localhost:5111/ws/stats
```

```json
{
  "active_connections": 1,
  "subscriptions": {
    "price:005930": 0,     ← 구독자 0명
    "price:000660": 0,     ← 구독자 0명
    "market-gate": 2       ← 구독자 2명
  },
  "bridge_running": true,
  "broadcaster_running": true
}
```

### 2.5 프론트엔드 분석

#### 랜딩 페이지 코드
```typescript
// frontend/app/page.tsx:28-34
const realtimeTickers = useMemo(() => {
  return signals.slice(0, 6).map((signal) => ({
    ticker: signal.ticker,  // ← ELW 종목: "0015N0", "493330", "217590"
    name: signal.name,
  }));
}, [signals]);
```

#### 프론트엔드 구독 로직
```typescript
// frontend/hooks/useWebSocket.ts:395-414
useEffect(() => {
  if (!connected) {
    console.log(`[useRealtimePrices] Waiting for connection...`);
    return;
  }

  tickers.forEach((ticker) => {
    console.log(`[useRealtimePrices] Subscribing to price:${ticker}`);
    subscribe(`price:${ticker}`);  // ← "price:0015N0" 등 구독 시도
  });
  // ...
}, [tickers.join(","), subscribe, unsubscribe, connected]);
```

프론트엔드는 ELW 종목(`0015N0`, `493330`, `217590`)에 대해 구독을 시도하지만, 서버에서 해당 종목을 브로드캐스트하지 않습니다.

---

## 3. 근본 원인 (Root Cause)

### 3.1 직접 원인

**불일치**: 랜딩 페이지에서 표시하려는 종목과 시스템이 실시간으로 지원하는 종목이 다릅니다.

| 구분 | 종목 |
|------|------|
| 랜딩 페이지 시그널 | ELW (0015N0, 493330, 217590) |
| 브로드캐스터 지원 | KOSPI 대종목 (005930, 000660, ...) |

### 3.2 시스템 설계 제약

1. **VCP 스캐너가 ELW 종목에서 시그널 발생**
2. **실시간 가격 시스템은 KOSPI 대종목만 지원**
3. **ELW 종목에 대한 실시간 가격 데이터 소스 없음**

### 3.3 Kiwoom API 제약

ELW(상장지수증권)는 Kiwoom WebSocket에서 별도 처리가 필요할 수 있습니다:
- ELW 종목 코드 형식: 숫자+알파벳 (예: `0015N0`)
- `ticker.isdigit()` 체크로 일부 ELW가 필터링됨
- Kiwoom WebSocket 브리지가 ELW를 지원하지 않을 수 있음

---

## 4. 영향 분석

### 4.1 기능적 영향

| 페이지 | 종목 | 실시간 가격 | 원인 |
|--------|------|-------------|------|
| 랜딩 페이지 | ELW (0015N0) | ❌ 안 됨 | 브로드캐스터 미지원 |
| /dashboard/kr | KOSPI 지수 | ✅ 됨 | 별도 API |

### 4.2 사용자 경험

1. **데이터 없음**: 실시간 가격 카드에 "데이터 대기 중..." 메시지
2. **혼동**: WebSocket 연결은 "연결됨"인데 데이터 없음
3. **기대치 불일치**: "실시간"이라고 표시되지만 실시간 데이터 없음

### 4.3 비즈니스 영향

- 시그널 종목의 실시간 가격 확인 불가
- 사용자가 시그널 종목의 현재 가격을 알 수 없음
- 매매 결정에 필요한 실시간 정보 부족

---

## 5. 개선 제안

### 5.1 우선순위 1: 랜딩 페이지 종목 변경 (높음)

#### 방안 A: 인기 종목 하드코딩

```typescript
// frontend/app/page.tsx
const POPULAR_STOCKS = [
  { ticker: "005930", name: "삼성전자" },
  { ticker: "000660", name: "SK하이닉스" },
  { ticker: "035420", name: "NAVER" },
  { ticker: "005380", name: "현대차" },
  { ticker: "028260", name: "삼성물산" },
  { ticker: "000020", name: "동화약품" },
];

const realtimeTickers = POPULAR_STOCKS;
```

**장점**:
- 즉시 해결 가능
- 브로드캐스터와 일치

**단점**:
- 시그널 종목과 불일치
- 사용자가 시그널 종목의 가격을 볼 수 없음

#### 방안 B: 시그널 종목 + 인기 종목 혼합

```typescript
const realtimeTickers = useMemo(() => {
  // 시그널 종목 중 상위 3개 + 인기 종목 3개
  const signalStocks = signals.slice(0, 3).map(s => ({
    ticker: s.ticker,
    name: s.name,
  }));

  const popularStocks = [
    { ticker: "005930", name: "삼성전자" },
    { ticker: "000660", name: "SK하이닉스" },
    { ticker: "035420", name: "NAVER" },
  ];

  return [...signalStocks, ...popularStocks];
}, [signals]);
```

### 5.2 우선순위 2: ELW 실시간 지원 (중간)

#### 백엔드 수정

```python
# src/websocket/server.py
def subscribe(self, client_id: str, topic: str) -> None:
    # ...
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ELW 지원 (6자리, 숫자+알파벳)
        if len(ticker) == 6:
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
```

**주의사항**:
- Kiwoom WebSocket이 ELW를 지원하는지 확인 필요
- ELW 종목 별도 처리 로직 추가 필요

### 5.3 우선순위 3: 폴링 Fallback (낮음)

```typescript
// WebSocket으로 실시간 데이터를 받지 못하면 폴링으로 fallback
useEffect(() => {
  if (!connected || realtimePrice) {
    // WebSocket 연결 안 되거나 이미 데이터 있으면 스킵
    return;
  }

  // 폴링으로 가격 조회
  const fetchPrice = async () => {
    const price = await apiClient.getRealtimePrices([ticker]);
    setPrices(prev => ({ ...prev, [ticker]: price[ticker] }));
  };

  fetchPrice();
  const interval = setInterval(fetchPrice, 5000);  // 5초마다 폴링

  return () => clearInterval(interval);
}, [ticker, connected, realtimePrice]);
```

### 5.4 우선순위 4: UI 개선 (낮음)

```typescript
// ELW 종목인 경우 실시간 지원 안 함을 표시
{isELW(ticker) && (
  <div className="text-xs text-yellow-600">
    ⚠️ ELW 종목은 실시간 지원이 제한됩니다
  </div>
)}
```

---

## 6. 검증 계획

### 6.1 방안 A 테스트

1. 랜딩 페이지 접속
2. KOSPI 대종목(삼성전자, SK하이닉스 등) 가격 표시 확인
3. 실시간 업데이트 확인

### 6.2 방안 B 테스트

1. ELW 종목 구독 시도
2. Kiwoom WebSocket 브리지 로그 확인
3. 가격 업데이트 수신 확인

---

## 7. 권장 사항

### 7.1 단기 (즉시 실행)

**방안 A 추천**: 랜딩 페이지에 인기 종목 표시

- 시그널 종목의 실시간 가격 표시는 포기
- 대신 인기 종목의 실시간 가격을 표시하여 기능 시연

### 7.2 중기 (1-2주)

1. 시그널 종목 필터링: KOSPI 대종목만 시그널 발생하도록 수정
2. 또는 ELW 종목에 대한 별도 데이터 소스 확보

### 7.3 장기 (1개월 이상)

1. Kiwoom WebSocket ELW 지원 확인
2. 필요시 별도 실시간 데이터 소스 구축

---

## 8. 참고 자료

### 8.1 관련 파일

| 경로 | 설명 |
|------|------|
| `frontend/app/page.tsx` | 랜딩 페이지 |
| `frontend/hooks/useWebSocket.ts` | WebSocket 훅 |
| `src/websocket/server.py` | WebSocket 서버 및 브로드캐스터 |
| `src/websocket/routes.py` | WebSocket 라우터 |

### 8.2 API 엔드포인트

```
GET /api/kr/signals?limit=6  # 시그널 조회 (ELW 종목 반환)
GET /ws/stats                 # WebSocket 통계 조회
```

---

## 9. 변경 이력

| 일자 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-03 | 2.0 | 재분석: ELW 종목 불일치 발견 |
| 2026-02-03 | 1.0 | 초기 분석 보고서 |

---

*보고서 종료*
