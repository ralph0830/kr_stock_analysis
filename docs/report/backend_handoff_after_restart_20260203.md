# 백엔드 개발자 전달: 재시작 후 QA 테스트 결과

**전달 일자**: 2026-02-03
**작성자**: Claude Code (Frontend QA)
**관련 문서**: `docs/report/frontend_test_after_restart_20260203.md`

---

## 1. 요약

서비스 재시작 후 QA 테스트 결과, **프론트엔드는 정상 작동**. 백엔드에서 다음 사항 확인 필요:

| 항목 | 상태 | 내용 |
|------|------|------|
| 폴링 API | ✅ 정상 | 200 OK, 데이터 반환 |
| Market Gate | ✅ 정상 | WebSocket 실시간 업데이트 |
| WebSocket 가격 데이터 | ⚠️ 부분 | 5/6 종목만 데이터 표시 |
| 0120X0 종목 | 🔴 데이터 없음 | DB에 데이터 없음 |

---

## 2. 수정 완료 사항

### 2.1 KiwoomWebSocketBridge 구독 요청

**파일**: `src/websocket/kiwoom_bridge.py:210-243`

**이전 문제**: `add_ticker()`가 내부 상태만 업데이트하고 실제 Kiwoom WebSocket 구독 요청을 보내지 않음

**수정 완료**: `pipeline.subscribe()` 호출 추가

```python
async def add_ticker(self, ticker: str) -> bool:
    """종목 구독 추가"""
    if not self._is_valid_ticker(ticker):
        logger.warning(f"Invalid ticker format: {ticker}")
        return False

    if ticker in self._active_tickers:
        return True

    # Kiwoom WebSocket 실시간 시세 등록 (pipeline.subscribe() 사용)
    if self._pipeline:
        try:
            success = await self._pipeline.subscribe(ticker)
            if success:
                logger.info(f"Subscribed to Kiwoom real-time data: {ticker}")
            else:
                logger.warning(f"Failed to subscribe to Kiwoom real-time data for {ticker}")
        except Exception as e:
            logger.error(f"Error subscribing to {ticker}: {e}")

    self._active_tickers.add(ticker)
    logger.info(f"Added ticker to KiwoomWebSocketBridge: {ticker}")
    return True
```

### 2.2 remove_ticker() 수정

**파일**: `src/websocket/kiwoom_bridge.py:245-264`

```python
async def remove_ticker(self, ticker: str) -> bool:
    """종목 구독 제거"""
    # Kiwoom WebSocket 실시간 시세 해제 (pipeline.unsubscribe() 사용)
    if self._pipeline:
        try:
            await self._pipeline.unsubscribe(ticker)
        except Exception as e:
            logger.error(f"Error unsubscribing from {ticker}: {e}")

    self._active_tickers.discard(ticker)
    logger.info(f"Removed ticker from KiwoomWebSocketBridge: {ticker}")
    return True
```

### 2.3 add_index/remove_index 수정

**파일**: `src/websocket/kiwoom_bridge.py:266-313`

지수 구독도 동일하게 `pipeline.subscribe_index()`, `pipeline.unsubscribe_index()` 호출 추가

---

## 3. 백엔드 확인 필요 사항

### 3.1 0120X0 (유진 챔피언) 데이터 없음

**현상**:
```
┌─────────────────────────────────────────┐
│ 유진 챔피언중단기크레딧 X클래스  0120X0  │
│ • ELW                                   │
│ 폴링 ❌                                 │
│                                         │
│ 10,000원                                │
│ 0원 (+0.00%)                            │
│ 거래량 104,777                          │
│ 업데이트 오전 9:00:00 ← 2시간 경과     │
└─────────────────────────────────────────┘
```

**가능한 원인**:
1. DB에 해당 종목의 최근 가격 데이터 없음
2. 수집 태스크에서 이 종목을 건너뜀
3. Kiwoom API에서 해당 종목코드를 지원하지 않음

**확인 방법**:

```sql
-- DB 확인
SELECT * FROM daily_prices WHERE ticker = '0120X0' ORDER BY date DESC LIMIT 5;

-- stocks 테이블 확인
SELECT * FROM stocks WHERE ticker = '0120X0';
```

```python
# 수집 태스크 실행
from tasks.collection_tasks import collect_daily_prices
# 0120X0 종목에 대한 데이터 수집 실행
```

### 3.2 WebSocket 브로드캐스트 subscribers=0 문제

**현상**:
- `/ws/stats`에서는 구독자 2명으로 표시
- 실제 브로드캐스트에서는 `subscribers=0`

```bash
# 백엔드 로그
[BROADCAST] Topic=price:005380, subscribers=0
[BROADCAST] No recipients found to send to
```

**가능한 원인**:
1. ConnectionManager와 KiwoomWebSocketBridge 간의 구독 정보 동기화 문제
2. 브로드캐스트 타이밍 문제 (구독 전 브로드캐스트)

**확인 필요**:
```python
# src/websocket/server.py ConnectionManager.broadcast()
# subscribers=0인 경우 로그 확인
```

---

## 4. 테스트 결과 상세

### 4.1 6개 시그널 종목 상태

| 종목코드 | 종목명 | 종류 | 상태 | 업데이트 시간 |
|----------|--------|------|------|--------------|
| 0015N0 | 아로마티카 | ELW | ✅ 실시간 | 11:40:08 |
| 493330 | 지에프아이 | KOSDAQ | ✅ 실시간 | 11:40:05 |
| 217590 | 티엠씨 | KOSDAQ | ✅ 실시간 | 11:39:51 |
| 0004V0 | 엔비알모션 | ELW | ✅ 실시간 | 11:40:05 |
| 491000 | 리브스메드 | KOSDAQ | ✅ 실시간 | 11:40:08 |
| 0120X0 | 유진 챔피언 | ELW | ❌ 데이터 없음 | 09:00:00 |

**성공률**: 5/6 (83.3%)

### 4.2 WebSocket Stats

```json
{
  "active_connections": 2,
  "subscriptions": {
    "market-gate": 2,
    "price:0015N0": 2,
    "price:493330": 2,
    "price:217590": 2,
    "price:0004V0": 2,
    "price:491000": 2,
    "price:0120X0": 2
  },
  "bridge_running": true,
  "bridge_tickers": [
    "0004V0", "0120X0", "000660", "217590", "028260",
    "005930", "493330", "0015N0", "000020", "005380",
    "035420", "491000"
  ],
  "broadcaster_running": true,
  "active_tickers": [
    "0004V0", "0120X0", "000660", "217590", "028260",
    "005930", "493330", "0015N0", "000020", "005380",
    "035420", "491000"
  ],
  "heartbeat_running": false,
  "recv_timeout": 60
}
```

---

## 5. 프론트엔드 상태

### 5.1 정상 작동 항목

| 항목 | 상태 |
|------|------|
| WebSocket 연결 | ✅ |
| 구독 요청 | ✅ |
| Market Gate 데이터 | ✅ |
| 폴링 API | ✅ |
| 자동 재연결 | ✅ |
| ELW 뱃지 표시 | ✅ |

### 5.2 "실시간" 표시 기준

```javascript
// frontend/components/RealtimePriceCard.tsx
const isRealtime = priceData && (
  !lastPollUpdate ||       // 폴링 업데이트가 없거나
  priceData.timestamp > lastPollUpdate.timestamp  // WebSocket 데이터가 더 최신
);
```

- 데이터의 최신성 기반 (WebSocket 메시지 수신 여부와 무관)
- 폴링으로 가져온 데이터라도 최신이면 "실시간" 표시

---

## 6. 검증 체크리스트

백엔드 개발자 확인 후:

- [x] KiwoomWebSocketBridge 구독 요청 로직 수정 완료
- [ ] Docker 컨테이너 재시작 (`docker compose restart api-gateway`)
- [ ] 0120X0 종목 DB 데이터 확인
- [ ] WebSocket 브로드캐스트 subscribers=0 문제 확인
- [ ] Kiwoom Pipeline 구독 로그 확인
- [ ] 프론트엔드에서 WebSocket 가격 데이터 수신 확인

---

## 7. 우선순위

| 순위 | 항목 | 심각도 |
|------|------|--------|
| 1 | 0120X0 종목 데이터 수집 | 높음 |
| 2 | WebSocket 브로드캐스트 subscribers 확인 | 중간 |
| 3 | Kiwoom Pipeline 구독 로그 확인 | 중간 |

---

## 8. 재시작 방법

```bash
# API Gateway 재시작
docker compose restart api-gateway

# 로그 확인
docker compose logs -f api-gateway

# Kiwoom 구독 로그 확인
docker compose logs api-gateway | grep "Subscribed to Kiwoom"
```

---

*전달일: 2026-02-03*
*수정일: 2026-02-03 (pipeline.subscribe() 추가 완료)*
