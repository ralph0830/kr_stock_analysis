# 백엔드 ELW 지원 검증 보고서

**검증 일자**: 2026-02-03
**검증 유형**: 코드 수정 검증 및 기능 테스트
**검증자**: Claude Code QA

---

## 1. 실행 요약

### 1.1 검증 결과

| 항목 | 상태 | 설명 |
|------|------|------|
| `_is_valid_ticker()` 구현 | ✅ 완료 | ELW 지원 검증 로직 추가 |
| `subscribe()` ELW 지원 | ✅ 코드 수정 | `_is_valid_ticker()` 호출 추가 |
| `unsubscribe()` ELW 지원 | ✅ 코드 수정 | `_is_valid_ticker()` 호출 추가 |
| WebSocket ELW 구독 | ❌ 미작동 | 구독자 0명, 데이터 미전송 |
| 폴링 API `/api/kr/realtime-prices` | ❌ 미구현 | `return {"prices": {}}` |
| Kiwoom WebSocket Bridge | ✅ 작동 중 | 실시간 데이터 수신 중 |

### 1.2 코드 수정 확인

#### ConnectionManager._is_valid_ticker() 추가

**파일**: `src/websocket/server.py:144-168`

```python
def _is_valid_ticker(self, ticker: str) -> bool:
    """
    종목 코드 유효성 검증 (ELW 지원)

    - KOSPI/KOSDAQ: 6자리 숫자
    - ELW(상장지수증권): 6자리 (숫자+알파벳 조합)

    Args:
        ticker: 종목 코드

    Returns:
        bool: 유효한 종목 코드이면 True
    """
    if not ticker or len(ticker) != 6:
        return False

    # 전체 숫자이면 통과 (KOSPI/KOSDAQ)
    if ticker.isdigit():
        return True

    # ELW 형식: 숫자+알파벳 조합
    has_digit = any(c.isdigit() for c in ticker)
    has_alpha = any(c.isalpha() for c in ticker)

    return has_digit and has_alpha
```

**검증 결과**: ✅ 코드 정상 구현됨

#### subscribe() 메서드 ELW 지원

**파일**: `src/websocket/server.py:170-202`

```python
def subscribe(self, client_id: str, topic: str) -> None:
    """토픽 구독"""
    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()

    self.subscriptions[topic].add(client_id)
    logger.info(f"Client {client_id} subscribed to {topic}")

    # price:{ticker} 형식이면 KiwoomWebSocketBridge에 ticker 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]

        # ELW 포함한 종목 코드 검증  ← 수정됨
        if self._is_valid_ticker(ticker):
            # KiwoomWebSocketBridge에 ticker 추가
            ws_bridge = get_kiwoom_ws_bridge()
            if ws_bridge and ws_bridge.is_running():
                asyncio.create_task(ws_bridge.add_ticker(ticker))
                print(f"[WS BRIDGE] Added ticker to KiwoomWebSocketBridge: {ticker}")
            else:
                # Fallback: price_broadcaster에 추가
                price_broadcaster.add_ticker(ticker)
```

**검증 결과**: ✅ 코드 수정됨 (`ticker.isdigit()` → `self._is_valid_ticker(ticker)`)

---

## 2. 기능 테스트 결과

### 2.1 WebSocket 통계 확인

```bash
$ curl http://localhost:5111/ws/stats | jq .
```

```json
{
  "active_connections": 2,
  "subscriptions": {
    "price:005930": 0,
    "price:000660": 0,
    "signals": 0,
    "market-gate": 12
  },
  "bridge_running": true,
  "bridge_tickers": [
    "035420",
    "217590",      ← ELW (티엠씨)
    "491000",      ← ELW (리브스메드)
    "005380",
    "000020",
    "028260",
    "005930",
    "000660",
    "493330"       ← ELW (지에프아이)
  ],
  "broadcaster_running": true,
  "active_tickers": [],
  "heartbeat_running": false
}
```

**분석**:
- `bridge_tickers`에 ELW 종목 포함 (`217590`, `491000`, `493330`)
- 하지만 `subscriptions`에 ELW 토픽 누락 (`price:0015N0` 등 없음)
- `active_tickers`가 비어있음

### 2.2 브로드캐스트 로그 확인

```bash
$ docker logs api-gateway --tail 50 | grep -E "\[WS BRIDGE\]|BROADCAST"
```

```
[WS BRIDGE] Broadcasting price update for 005930: 159900.0
[BROADCAST] Topic=price:005930, subscribers=0
[BROADCAST] No recipients found to send to

[WS BRIDGE] Broadcasting price update for 000660: 893500.0
[BROADCAST] Topic=price:000660, subscribers=0
[BROADCAST] No recipients found to send to
```

**분석**:
- Kiwoom WebSocket Bridge가 실시간 데이터를 수신 중 (삼성전자 159,900원, SK하이닉스 893,500원)
- 하지만 `subscribers=0`으로 구독자가 없음
- 데이터 전송 안 됨

### 2.3 프론트엔드 구독 요청 확인

브라우저 콘솔 로그:
```
[useRealtimePrices] Subscribing to price:0015N0
[useRealtimePrices] Subscribing to price:493330
[useRealtimePrices] Subscribing to price:217590
[useRealtimePrices] Subscribing to price:0004V0
[useRealtimePrices] Subscribing to price:491000
[useRealtimePrices] Subscribing to price:0120X0
```

**분석**:
- 프론트엔드에서 ELW 종목 구독 요청 전송
- 하지만 백엔드 `subscriptions`에 등록되지 않음

---

## 3. 원인 분석

### 3.1 구독 처리 미작동 원인

**예상 동작**:
```
프론트엔드 → WebSocket 메시지 → subscribe() 메서드
                              → subscriptions[topic].add(client_id)
                              → ws_bridge.add_ticker(ticker)
                              → active_tickers에 추가
                              → 브로드캐스트 시작
```

**실제 동작**:
```
프론트엔드 → WebSocket 메시지 → subscribe() 메서드
                              → subscriptions[topic].add(client_id) ??
                              → ws_bridge.add_ticker(ticker) ??
                              → active_tickers에 추가 안 됨
                              → 구독자 0명
```

**가능한 원인**:

1. **WebSocket 메시지 핸들러 문제**:
   - `routes.py`의 `websocket_endpoint()`에서 메시지 수신 후 `connection_manager.subscribe()` 호출 확인 필요
   - `message_type == "subscribe"` 분기 확인 필요

2. **로그 레벨 문제**:
   - `logger.info()` 로그가 표시되지 않을 수 있음
   - `print()` 로그로 확인 필요

### 3.2 KiwoomWebSocketBridge 동작 확인

**파일**: `src/websocket/kiwoom_bridge.py:184-210`

```python
async def add_ticker(self, ticker: str) -> bool:
    """종목 구독 추가"""
    self._active_tickers.add(ticker)
    logger.info(f"Added ticker to KiwoomWebSocketBridge: {ticker}")
    return True
```

**문제**:
- `add_ticker()`가 호출되면 `_active_tickers`에 추가됨
- 하지만 `bridge_tickers`에 ELW가 있어도 `active_tickers`는 비어있음
- 이는 `add_ticker()`가 호출되지 않았거나, 다른 인스턴스가 사용되고 있음을 의미

### 3.3 두 개의 별도 bridge_tickers 목록

WebSocket 통계에서 `bridge_tickers`와 `active_tickers`가 다름:

| 속성 | 값 | 설명 |
|------|-----|------|
| `bridge_tickers` | `["035420", "217590", "491000", ...]` | KiwoomWebSocketBridge의 `_active_tickers` |
| `active_tickers` | `[]` | PriceUpdateBroadcaster의 `_active_tickers` |

**분석**:
- `bridge_tickers`는 `KiwoomWebSocketBridge._active_tickers`를 반환
- ELW 종목이 여기에 포함되어 있어 Kiwoom WebSocket으로 데이터를 받고 있음
- 하지만 `subscriptions`에 ELW 토픽이 없어서 클라이언트로 전송 안 됨

---

## 4. WebSocket 라우트 핸들러 분석

**파일**: `src/websocket/routes.py:32-98`

```python
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    subscribe: Optional[str] = Query(None, description="구독할 토픽 (콤마로 구분)"),
):
    # 클라이언트 ID 생성
    client_id = str(uuid.uuid4())

    # 연결 수락
    await websocket.accept()

    # ConnectionManager에 등록
    connection_manager.active_connections[client_id] = websocket

    # 초기 구독 처리
    if subscribe:
        topics = subscribe.split(",")
        for topic in topics:
            topic = topic.strip()
            if topic:
                connection_manager.subscribe(client_id, topic)  # ← 초기 구독

    # 환영 메시지
    await websocket.send_json({
        "type": "connected",
        "client_id": client_id,
        "message": "WebSocket connection established",
    })

    # 메시지 수신 루프
    while True:
        try:
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=float(WS_RECV_TIMEOUT)
            )

            message_type = data.get("type")

            # 메시지 타입별 처리
            if message_type == "subscribe":
                topic = data.get("topic")
                if topic:
                    connection_manager.subscribe(client_id, topic)  # ← 동적 구독
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "message": f"Subscribed to {topic}",
                    })
            # ...
```

**검증 필요 사항**:
1. 프론트엔드에서 보낸 `{"type": "subscribe", "topic": "price:0015N0"}` 메시지가 수신되는지
2. `connection_manager.subscribe()`가 호출되는지
3. `subscriptions[topic]`에 `client_id`가 추가되는지

---

## 5. 디버깅 제안

### 5.1 로깅 강화

**파일**: `src/websocket/server.py`

```python
def subscribe(self, client_id: str, topic: str) -> None:
    """토픽 구독 (디버깅용 로깅 추가)"""
    print(f"[SUBSCRIBE] Client {client_id} subscribing to {topic}")  # 디버깅

    if topic not in self.subscriptions:
        self.subscriptions[topic] = set()
        print(f"[SUBSCRIBE] Created new topic set for {topic}")

    self.subscriptions[topic].add(client_id)
    print(f"[SUBSCRIBE] Added client {client_id} to {topic}, total: {len(self.subscriptions[topic])}")

    # price:{ticker} 형식이면 ticker 검증 후 추가
    if topic.startswith("price:"):
        ticker = topic.split(":", 1)[1]
        print(f"[SUBSCRIBE] Processing price ticker: {ticker}")

        if self._is_valid_ticker(ticker):
            print(f"[SUBSCRIBE] Ticker {ticker} is valid, adding to bridge")
            # ... (기존 코드)
        else:
            print(f"[SUBSCRIBE] Ticker {ticker} is INVALID, skipping")
```

### 5.2 WebSocket 메시지 핸들러 로깅

**파일**: `src/websocket/routes.py`

```python
# 메시지 수신 루프
while True:
    try:
        data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=float(WS_RECV_TIMEOUT)
        )

        message_type = data.get("type")
        print(f"[WS ROUTER] Received message: type={message_type}, data={data}")  # 디버깅

        if message_type == "subscribe":
            topic = data.get("topic")
            print(f"[WS ROUTER] Processing subscribe request for topic: {topic}")  # 디버깅
            if topic:
                connection_manager.subscribe(client_id, topic)
```

---

## 6. 테스트 시나리오

### 6.1 WebSocket 구독 흐름 테스트

```python
# tests/integration/test_websocket_elw.py

import pytest
import asyncio
from httpx import AsyncClient
from websockets.client import connect

@pytest.mark.asyncio
async def test_elw_subscription_flow():
    """ELW 종목 WebSocket 구독 흐름 테스트"""
    uri = "ws://localhost:5111/ws"

    async with connect(uri) as ws:
        # 1. 연결 확인
        response = await ws.recv()
        connected = json.loads(response)
        assert connected["type"] == "connected"
        client_id = connected["client_id"]

        # 2. ELW 종목 구독
        await ws.send(json.dumps({
            "type": "subscribe",
            "topic": "price:0015N0"
        }))

        # 3. 구독 확인 응답 수신
        response = await ws.recv()
        subscribed = json.loads(response)
        assert subscribed["type"] == "subscribed"
        assert subscribed["topic"] == "price:0015N0"

        # 4. 구독 상태 확인
        stats = await get_ws_stats()
        assert "price:0015N0" in stats["subscriptions"]
        assert client_id in stats["subscriptions"]["price:0015N0"]
```

### 6.2 KiwoomWebSocketBridge ELW 등록 테스트

```python
# tests/unit/test_kiwoom_bridge_elw.py

import pytest
from src.websocket.kiwoom_bridge import KiwoomWebSocketBridge

@pytest.mark.asyncio
async def test_elw_ticker_registration():
    """ELW 종목 KiwoomWebSocketBridge 등록 테스트"""
    bridge = KiwoomWebSocketBridge()
    await bridge.start(None)  # Mock pipeline

    # ELW 종목 추가
    result = await bridge.add_ticker("0015N0")

    # 등록 확인
    assert result is True
    assert "0015N0" in bridge.get_active_tickers()

    # 이중 등록 방지 확인
    result2 = await bridge.add_ticker("0015N0")
    assert result2 is True
    assert len(bridge.get_active_tickers()) == 1

    # 제거 확인
    await bridge.remove_ticker("0015N0")
    assert "0015N0" not in bridge.get_active_tickers()
```

---

## 7. 단위 테스트 작성 제안

### 7.1 ConnectionManager._is_valid_ticker() 테스트

```python
# tests/unit/test_connection_manager_elw.py

import pytest
from src.websocket.server import ConnectionManager

class TestConnectionManagerELW:
    """ConnectionManager ELW 지원 테스트"""

    def test_is_valid_ticker_kospi(self):
        """KOSPI 종목 코드 검증"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("005930") is True
        assert manager._is_valid_ticker("000660") is True
        assert manager._is_valid_ticker("035420") is True

    def test_is_valid_ticker_elw(self):
        """ELW 종목 코드 검증"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("0015N0") is True
        assert manager._is_valid_ticker("0004V0") is True
        assert manager._is_valid_ticker("0120X0") is True
        assert manager._is_valid_ticker("493330") is True  # 숫자만 있는 ELW

    def test_is_valid_ticker_invalid(self):
        """잘못된 종목 코드"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("12345") is False  # 5자리
        assert manager._is_valid_ticker("1234567") is False  # 7자리
        assert manager._is_valid_ticker("ABCDEF") is False  # 알파벳만
        assert manager._is_valid_ticker("") is False  # 빈 문자열
        assert manager._is_valid_ticker(None) is False  # None
```

---

## 8. 검증 결론

### 8.1 완료 항목

1. ✅ **백엔드 ELW 검증 로직**: `_is_valid_ticker()` 메서드 구현
2. ✅ **subscribe() 메서드 수정**: `_is_valid_ticker()` 호출 추가
3. ✅ **unsubscribe() 메서드 수정**: `_is_valid_ticker()` 호출 추가
4. ✅ **Kiwoom WebSocket Bridge**: 실시간 데이터 수신 작동 중

### 8.2 미완료 항목

1. ❌ **WebSocket ELW 구독**: 코드 수정됨 but 구독자 0명 문제 지속
2. ❌ **폴링 API**: `/api/kr/realtime-prices` 미구현
3. ⚠️ **디버깅 로그**: 구독 처리 과정 로깅 부족

### 8.3 다음 단계

1. **디버깅 로그 추가**: `subscribe()` 메서드에 상세 로깅
2. **WebSocket 메시지 트래킹**: 프론트엔드 → 백엔드 메시지 흐름 확인
3. **폴링 API 구현**: Kiwoom REST API 기반 ELW 가격 조회

---

## 9. 참고 자료

### 9.1 수정된 파일

| 파일 | 수정 내용 |
|------|-----------|
| `src/websocket/server.py` | `_is_valid_ticker()` 추가 |
| `src/websocket/server.py` | `subscribe()` ELW 지원 수정 |
| `src/websocket/server.py` | `unsubscribe()` ELW 지원 수정 |

### 9.2 관련 이슈

| 이슈 | 상태 |
|------|------|
| ELW 종목 구독 처리 | ⚠️ 코드 수정됨, 동작 미확인 |
| ELW 폴링 API | ❌ 미구현 |
| Kiwoom WebSocket ELW 지원 | ✅ `_active_tickers`에 추가됨 |

---

*보고서 종료*

*마지막 수정: 2026-02-03*
