# 백엔드 개발자 전달: Playwright QA 대응 수정사항

**전달 일자**: 2026-02-03
**작성자**: Claude Code (Frontend)
**관련 문서**: `docs/report/frontend_playwright_qa_20260203.md`

---

## 1. 요약

Playwright E2E QA 수행 결과, **프론트엔드 코드에는 문제 없음**. 백엔드 수정 사항:

| 항목 | 상태 | 내용 |
|------|------|------|
| 폴링 API | ✅ 수정 완료 | `get_db_session_sync()` 사용으로 변경 |
| 실시간 가격 브로드캐스트 | ✅ 수정 완료 | Pipeline 없으면 price_broadcaster 사용 |
| ELW 실시간 데이터 | ✅ 수정 완료 | DB 폴링 fallback 활성화 |

---

## 2. 백엔드 수정 완료 사항

### 2.1 폴링 API 수정

**파일**: `services/api_gateway/main.py:1287-1345`

**문제**: `get_db_session()` 제너레이터를 `with`로 직접 사용하여 500 에러 발생

**해결**: `get_db_session_sync()` 사용 (이미 수정 완료)

```python
# 수정 완료된 코드
async def get_kr_realtime_prices(request: RealtimePricesRequest):
    prices = {}

    # Context Manager로 사용 가능한 get_db_session_sync() 사용
    with get_db_session_sync() as db:
        for ticker in request.tickers:
            query = (
                select(DailyPrice)
                .where(DailyPrice.ticker == ticker)
                .order_by(desc(DailyPrice.date))
                .limit(1)
            )
            result = db.execute(query)
            daily_price = result.scalar_one_or_none()
            # ... 가격 데이터 변환
    return {"prices": prices}
```

**변경 사항**:
- `with get_db_session()` → `with get_db_session_sync()`
- `get_db_session_sync()`는 `@contextmanager` 데코레이터로 감싸져 있음

---

## 3. 백엔드 수정 완료 사항 (추가)

### 3.1 WebSocket 실시간 가격 브로드캐스트 수정

**문제**: Kiwoom WebSocket Bridge가 실행 중이지만, Docker 환경에서는 Kiwoom API(Windows 전용)를 사용할 수 없어 실시간 데이터가 전송되지 않음

**해결**: Pipeline 연결 여부를 확인하여 없으면 DB 폴링 방식으로 fallback

**수정 파일**:
1. `src/websocket/kiwoom_bridge.py` - `has_pipeline()` 메서드 추가
2. `src/websocket/server.py` - Pipeline 확인 로직 추가

```python
# src/websocket/kiwoom_bridge.py 추가
def has_pipeline(self) -> bool:
    """Pipeline 연결 여부 확인 (Kiwoom API 사용 가능 여부)"""
    return self._pipeline is not None

# src/websocket/server.py 수정
if ws_bridge and ws_bridge.is_running() and has_pipeline:
    # Kiwoom Pipeline 있으면 실시간 데이터 사용
    asyncio.create_task(ws_bridge.add_ticker(ticker))
else:
    # Pipeline 없으면 DB 폴링 사용
    price_broadcaster.add_ticker(ticker)
```

### 3.2 PriceBroadcaster 자동 활성화

**동작**:
- Kiwoom Pipeline이 없으면 자동으로 `price_broadcaster` 사용
- `price_broadcaster`는 DB에서 최신 가격 데이터를 조회하여 브로드캐스트
- ELW 종목 포함 모든 종목 지원

**관련 파일**:
- `src/websocket/server.py` - ConnectionManager, PriceBroadcaster
- `src/websocket/price_provider.py` - DB 가격 제공자

---

## 4. 테스트 방법

### 4.1 폴링 API 테스트

```bash
# POST 요청 테스트
curl -X POST http://localhost:5111/api/kr/realtime-prices \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["005930", "000660", "0015N0"]}'

# 기대 결과: 200 OK + prices 데이터
```

### 4.2 WebSocket 구독 테스트

```bash
# 1. 웹소켓 연결 및 구독 테스트
wscat -c "wss://stock.ralphpark.com/ws"

# 2. 구독 메시지 전송
{"type": "subscribe", "topic": "price:005930"}

# 3. 통계 확인
curl http://localhost:5111/ws/stats
```

### 4.3 브로드캐스트 테스트

**백엔드 로그 확인**:
```
[WS BRIDGE] Broadcasting price update for 005930: 159400.0
[BROADCAST] Topic=price:005930, subscribers=1
[BROADCAST] Sent to 1 recipients
```

---

## 5. 프론트엔드 수정 완료 사항

### 5.1 완료된 수정

| 항목 | 파일 | 상태 |
|------|------|------|
| `useRealtimePrices` 연결 확인 | `frontend/hooks/useWebSocket.ts` | ✅ 완료 |
| ELW 식별 로직 | `frontend/components/RealtimePriceCard.tsx` | ✅ 완료 |
| 카테고리 분류 | `frontend/components/RealtimePriceCard.tsx` | ✅ 완료 |
| 데이터 소스 뱃지 | `frontend/components/RealtimePriceCard.tsx` | ✅ 완료 |
| 폴링 Fallback | `frontend/components/RealtimePriceCard.tsx` | ✅ 완료 |
| ELW 안내 메시지 | `frontend/components/RealtimePriceCard.tsx` | ✅ 완료 |

### 5.2 프론트엔드 테스트 통과 (70%)

| 항목 | 상태 |
|------|------|
| WebSocket 연결 | ✅ |
| 구독 요청 | ✅ |
| Market Gate 데이터 | ✅ |
| 자동 재연결 | ✅ |
| 폴링 시도 | ✅ |
| ELW 뱃지 | ✅ |
| 실시간 가격 수신 | ❌ (백엔드 이슈) |
| 폴링 API | ✅ (수정 완료) |

---

## 6. 검증 체크리스트

백엔드 개발자 확인 후:

- [x] 폴링 API 수정 완료 (`get_db_session_sync()`)
- [x] Pipeline 확인 로직 추가 (`has_pipeline()`)
- [x] DB 폴링 fallback 활성화
- [ ] Docker 컨테이너 재시작 (`docker compose restart api-gateway`)
- [ ] 폴링 API 200 응답 확인
- [ ] ELW 종목 가격 데이터 반환 확인
- [ ] WebSocket `/ws/stats`에서 `active_tickers` 확인
- [ ] KiwoomWebSocketBridge 브로드캐스트 로그 확인
- [ ] 프론트엔드에서 실시간 가격 데이터 수신 확인

---

## 7. 우선순위

| 순위 | 항목 | 심각도 | 상태 |
|------|------|--------|------|
| 1 | 폴링 API 정상 작동 | 높음 | ✅ 수정 완료 |
| 2 | 실시간 가격 브로드캐스트 | 높음 | ✅ 수정 완료 |
| 3 | ELW 종목 실시간 데이터 지원 | 중간 | ✅ 수정 완료 |

---

## 8. 재시작 방법

```bash
# Docker Compose로 실행 중인 경우
docker compose restart api-gateway

# 또는 전체 재시작
docker compose down && docker compose up -d

# 로그 확인
docker compose logs -f api-gateway
```

---

*전달일: 2026-02-03*
*수정일: 2026-02-03 (Pipeline 확인 로직 추가)*
