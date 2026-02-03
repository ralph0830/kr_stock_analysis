# 실시간 가격 모니터링 문제 분석 및 수정 방안

**분석 일자**: 2026-02-03
**분석자**: Claude Code QA
**테스트 방법**: Playwright + Sequential Thinking

---

## 1. 문제 요약

### 1.1 현재 상태

| 항목 | 상태 | 설명 |
|------|------|------|
| 폴링 API | ✅ 정상 | 6개 카드 모두 가격 데이터 표시됨 |
| WebSocket 연결 | ✅ 정상 | wss://stock.ralphpark.com/ws 연결됨 |
| 구독 등록 | ✅ 정상 | price:0015N0 등 구독자 4명 |
| **실시간 가격 브로드캐스트** | ❌ **작동 안 함** | Kiwoom WebSocket 데이터 미수신 |

### 1.2 UI 상태

```
아로마티카 0015N0 • ELW
폴링 ELW 9,170원 +30원 (+0.33%)
"현재 실시간 연결이 없습니다. 15초마다 업데이트됩니다."
```

- 6개 카드 모두 **"폴링"**으로 표시됨
- 실시간 WebSocket 데이터를 받지 못하고 있음

---

## 2. 근본 원인 분석

### 2.1 문제 흐름도

```
프론트엔트 구독 요청
    ↓
ConnectionManager.subscribe()
    → ConnectionManager.subscriptions에 등록 ✅
    → KiwoomWebSocketBridge.add_ticker() 호출 ✅
        ↓
KiwoomWebSocketBridge._active_tickers에 추가 ✅
    ↓
[문제] Kiwoom WebSocket으로 실제 구독 요청 미전송 ❌
    ↓
Kiwoom 서버에서 실시간 데이터 미발송
    ↓
_on_realtime_data() 핸들러 미호출
    ↓
브로드캐스트 안 됨
```

### 2.2 코드 분석

#### KiwoomWebSocketBridge.add_ticker() (src/websocket/kiwoom_bridge.py:210-230)

```python
async def add_ticker(self, ticker: str) -> bool:
    """종목 구독 추가"""
    # 종목 코드 검증 (ELW 지원)
    if not self._is_valid_ticker(ticker):
        logger.warning(f"Invalid ticker format: {ticker}")
        return False

    if ticker in self._active_tickers:
        return True

    self._active_tickers.add(ticker)  # ← 내부 set에만 추가!
    logger.info(f"Added ticker to KiwoomWebSocketBridge: {ticker}")
    return True
    # ← 여기서 끝! 실제 Kiwoom WebSocket 구독 요청 안 함!
```

**문제**: `_active_tickers`에만 추가하고, 실제 Kiwoom WebSocket으로 구독 요청(REG 전문)을 보내지 않음

#### KiwoomWebSocket.subscribe_realtime() (src/kiwoom/websocket.py:263-297)

```python
async def subscribe_realtime(self, ticker: str) -> bool:
    """실시간 시세 등록 (키움 프로토콜)"""
    if not self._connected or not self._authenticated:
        logger.warning("Cannot subscribe: not connected or authenticated")
        return False

    try:
        # 키움 실시간 시세 등록 전문 (trnm: REG)
        reg_request = {
            "trnm": "REG",
            "grp_no": "1",
            "refresh": "1",
            "data": [{
                "item": [ticker],
                "type": [self.TYPE_STOCK_QUOTE, self.TYPE_STOCK_TRADE]
            }]
        }
        await self._ws.send(json.dumps(reg_request))  # ← 실제 WebSocket 구독 요청!

        self._subscribed_tickers.add(ticker)
        logger.info(f"Subscribed to real-time data: {ticker} (types: 0A, 0B)")
        return True
    except Exception as e:
        logger.error(f"Subscribe failed for {ticker}: {e}")
        return False
```

**핵심**: `KiwoomWebSocket.subscribe_realtime()`을 호출해야 실제 Kiwoom 서버로 구독 요청이 전송됨

### 2.3 아키텍처 문제

```
┌─────────────────────────────────────────────────────────┐
│ KiwoomWebSocketBridge                                 │
│ - _active_tickers: Set[str] (내부 상태만 관리)        │
│ - _pipeline: KiwoomPipelineManager                     │
│ - add_ticker() → _active_tickers.add()만 수행         │
└─────────────────────────────────────────────────────────┘
         ↑ 이벤트 등록
┌─────────────────────────────────────────────────────────┐
│ KiwoomPipelineManager                                   │
│ - _service: KiwoomRealtimeService                      │
│ - service._bridge: KiwoomWebSocket                      │
└─────────────────────────────────────────────────────────┘
         ↑ 실제 연결
┌─────────────────────────────────────────────────────────┐
│ KiwoomWebSocket                                        │
│ - subscribe_realtime() → Kiwoom 서버에 REG 전문 전송   │
│ - _on_receive() → 데이터 수신 시 이벤트 발생           │
└─────────────────────────────────────────────────────────┘
```

**문제**: KiwoomWebSocketBridge에서 KiwoomWebSocket으로 직접 접근할 수 없음

---

## 3. 수정 방안

### 3.1 KiwoomWebSocketBridge에 Bridge 참조 추가 (권장)

**파일**: `src/websocket/kiwoom_bridge.py`

**수정 내용**:

```python
class KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket Bridge

    Kiwoom Pipeline에서 발생하는 실시간 데이터 이벤트를 수신하여
    WebSocket 클라이언트에게 전달합니다.
    """

    def __init__(self, bridge: Optional['IKiwoomBridge'] = None):
        """
        초기화

        Args:
            bridge: Kiwoom WebSocket 인스턴스 (직접 구독 요청용)
        """
        self._running = False
        self._pipeline: Optional[Any] = None
        self._event_handlers: Dict[KiwoomEventType, list] = {}

        # 구독 중인 종목 (WebSocket 클라이언트들이 구독한 종목)
        self._active_tickers: Set[str] = set()
        # 구독 중인 지수 (KOSPI, KOSDAQ)
        self._active_indices: Set[str] = set()

        # Kiwoom WebSocket 직접 참조 (구독 요청용) ← 추가
        self._bridge = bridge  # KiwoomWebSocket 인스턴스
```

**add_ticker() 메서드 수정**:

```python
async def add_ticker(self, ticker: str) -> bool:
    """
    종목 구독 추가

    Args:
        ticker: 종목코드

    Returns:
        성공 여부
    """
    # 종목 코드 검증 (ELW 지원)
    if not self._is_valid_ticker(ticker):
        logger.warning(f"Invalid ticker format: {ticker}")
        return False

    if ticker in self._active_tickers:
        return True

    # 내부 set에 추가
    self._active_tickers.add(ticker)
    logger.info(f"Added ticker to KiwoomWebSocketBridge._active_tickers: {ticker}")

    # Kiwoom WebSocket으로 실제 구독 요청 전송 ← 추가
    if self._bridge:
        try:
            # KiwoomWebSocketBridge는 IKiwoemBridge 인터페이스를 구현하므로
            # 직접 구독 요청을 보낼 수 있는지 확인 필요
            # KiwoomWebSocket에 직접 접근 가능하다면:
            if hasattr(self._bridge, 'subscribe_realtime'):
                await self._bridge.subscribe_realtime(ticker)
                logger.info(f"Kiwoom WebSocket subscribe_realtime() called for {ticker}")
            # 또는 Pipeline을 통해 구독
            elif self._pipeline and hasattr(self._pipeline, 'subscribe_realtime'):
                await self._pipeline.subscribe_realtime(ticker)
                logger.info(f"Kiwoom Pipeline subscribe_realtime() called for {ticker}")
        except Exception as e:
            logger.error(f"Failed to subscribe to Kiwoom WebSocket for {ticker}: {e}")

    return True
```

### 3.2 초기화 시 Bridge 참조 전달

**파일**: `src/websocket/kiwoom_bridge.py:294-325`

```python
async def init_kiwoom_ws_bridge(
    pipeline: Any,
    default_tickers: list = None,
    subscribe_indices: bool = True
) -> KiwoomWebSocketBridge:
    """
    Kiwoom WebSocket Bridge 초기화 및 시작

    Args:
        pipeline: KiwoomPipelineManager 인스턴스
        default_tickers: 기본 구독 종목 리스트
        subscribe_indices: KOSPI/KOSDAQ 지수 구독 여부

    Returns:
        KiwoomWebSocketBridge 인스턴스
    """
    global _kiwoom_ws_bridge

    if _kiwoom_ws_bridge is None:
        # Pipeline에서 Bridge 인스턴스 추출 ← 수정
        bridge_instance = None
        if hasattr(pipeline, '_service'):
            if hasattr(pipeline._service, '_bridge'):
                bridge_instance = pipeline._service._bridge

        # Bridge 인스턴스 전달하여 생성 ← 수정
        _kiwoom_ws_bridge = KiwoomWebSocketBridge(bridge=bridge_instance)

    await _kiwoom_ws_bridge.start(pipeline)

    # 기본 종목 추가 및 실시간 구독 ← 수정
    if default_tickers:
        for ticker in default_tickers:
            await _kiwoom_ws_bridge.add_ticker(ticker)
            # Bridge 참조가 있으면 직접 구독도 시도
            if _kiwoom_ws_bridge._bridge and hasattr(_kiwoom_ws_bridge._bridge, 'subscribe_realtime'):
                await _kiwoom_ws_bridge._bridge.subscribe_realtime(ticker)
        logger.info(f"Added default tickers to KiwoomWebSocketBridge: {default_tickers}")

    # KOSPI/KOSDAQ 지수 구독
    if subscribe_indices:
        await _kiwoom_ws_bridge.add_index("001")  # KOSPI
        await _kiwoom_ws_bridge.add_index("201")  # KOSDAQ
        logger.info("Added KOSPI/KOSDAQ indices to KiwoomWebSocketBridge")

    return _kiwoom_ws_bridge
```

### 3.3 KiwoomPipelineManager에 구독 메서드 추가

**파일**: `src/kiwoom/pipeline.py`

```python
async def subscribe_realtime(self, ticker: str) -> bool:
    """
    실시간 데이터 구독

    Args:
        ticker: 종목코드

    Returns:
        성공 여부
    """
    if not self._running:
        logger.warning("Pipeline not running, cannot subscribe")
        return False

    # Service를 통해 구독
    if hasattr(self._service, 'subscribe_realtime'):
        return await self._service.subscribe_realtime(ticker)

    # Bridge에 직접 접근
    if hasattr(self._service, '_bridge'):
        bridge = self._service._bridge
        if hasattr(bridge, 'subscribe_realtime'):
            return await bridge.subscribe_realtime(ticker)

    logger.warning(f"No subscribe_realtime method available for {ticker}")
    return False
```

### 3.4 KiwoomRealtimeService에 구독 메서드 추가

**파일**: `src/kiwoom/service.py`

```python
async def subscribe_realtime(self, ticker: str) -> bool:
    """
    실시간 데이터 구독

    Args:
        ticker: 종목코드

    Returns:
        성공 여부
    """
    if not self._running:
        logger.warning("Service not running, cannot subscribe")
        return False

    if not self._bridge:
        logger.warning("Bridge not available, cannot subscribe")
        return False

    # Bridge에 구독 요청 위임
    if hasattr(self._bridge, 'subscribe_realtime'):
        return await self._bridge.subscribe_realtime(ticker)

    logger.warning(f"Bridge does not support subscribe_realtime for {ticker}")
    return False
```

---

## 4. 구독 흐름 수정 (변경 후)

```
프론트엔드 구독 요청
    ↓
ConnectionManager.subscribe()
    → ConnectionManager.subscriptions에 등록 ✅
    → KiwoomWebSocketBridge.add_ticker() 호출 ✅
        ↓
KiwoomWebSocketBridge._active_tickers에 추가 ✅
    ↓
[추가] KiwoomWebSocket.subscribe_realtime() 호출 ✅
    ↓
Kiwoom WebSocket 서버로 REG 전문 전송 ✅
    ↓
Kiwoom 서버에서 실시간 데이터 발송 ✅
    ↓
KiwoomWebSocket._on_receive() 수신
    ↓
이벤트 발생 → KiwoomWebSocketBridge._on_realtime_data()
    ↓
ConnectionManager.broadcast() → 프론트엔트로 전송 ✅
```

---

## 5. ELW 종목 지원

### 5.1 현재 ELW 지원 상태

| 항목 | 상태 | 설명 |
|------|------|------|
| ELW ticker 검증 | ✅ | `_is_valid_ticker()에서 알파벳 포함 검증 |
| Bridge에 등록 | ✅ | `_active_tickers`에 ELW 추가됨 |
| WebSocket 구독 | ❌ | Kiwoom WebSocket에 REG 전문 미전송 |
| 실시간 데이터 | ❌ | Kiwoom 서버에서 데이터 미발송 |

### 5.2 ELW 실시간 데이터 지원 방안

**Kiwoom API에서 ELW 실시간 데이터 지원 확인 필요**:

1. **Kiwoom REST API WebSocket에서 ELW 지원하는지 확인**
   - ELW(상장지수증권)도 일반 주식과 동일한 프로토콜로 지원하는지 확인 필요
   - 0B(주식체결) 타입으로 ELW 체결 데이터 수신 가능한지 확인

2. **ELW 종목 코드 형식**
   - ELW는 6자리 코드 (숫자+알파벳 조합)
   - 예: 0015N0, 0004V0, 0120X0

3. **구독 요청 예시**:
   ```json
   {
     "trnm": "REG",
     "grp_no": "1",
     "data": [{
       "item": ["0015N0"],  // ELW 종목
       "type": ["0A", "0B"]
     }]
   }
   ```

---

## 6. 테스트 및 검증

### 6.1 수정 후 테스트 절차

1. **코드 수정 후 컨테이너 재시작**
   ```bash
   docker compose restart api-gateway
   ```

2. **Kiwoom WebSocket 연결 확인**
   ```bash
   docker logs api-gateway | grep -i "kiwoom.*connect\|websocket.*establish"
   ```

3. **구독 요청 로그 확인**
   ```bash
   docker logs api-gateway | grep -i "subscribed.*real-time\|REG.*0015N0"
   ```

4. **실시간 데이터 수신 확인**
   ```bash
   docker logs api-gateway | grep -i "broadcast.*price.*0015N0"
   ```

5. **프론트엔드에서 가격 업데이트 확인**
   - https://stock.ralphpark.com/ 접속
   - 브라우저 콘솔에서 `price_update` 메시지 확인

### 6.2 기대 결과

| 항목 | 현재 | 수정 후 |
|------|------|--------|
| 데이터 소스 | 폴링 (15초) | 실시간 WebSocket |
| UI 표시 | "폴링" | "실시간" |
| 가격 업데이트 | 15초 간격 | Kiwoom 서버 푸시 |

---

## 7. 요약

### 7.1 핵심 문제

**KiwoomWebSocketBridge.add_ticker()는 내부 상태만 업데이트하고, 실제 Kiwoom WebSocket으로 구독 요청을 보내지 않음**

### 7.2 해결 방안

1. **KiwoomWebSocketBridge에 Bridge 참조 추가**
2. **add_ticker()에서 KiwoomWebSocket.subscribe_realtime() 호출**
3. **초기화 시 Bridge 참조 전달**

### 7.3 파일 수정 목록

| 파일 | 수정 내용 |
|------|----------|
| `src/websocket/kiwoom_bridge.py` | Bridge 참조 추가, add_ticker() 수정 |
| `src/kiwoom/pipeline.py` | subscribe_realtime() 메서드 추가 |
| `src/kiwoom/service.py` | subscribe_realtime() 메서드 추가 |

---

*보고서 종료*

*분석일: 2026-02-03*
*버전: 1.0*
