# 백엔드 개발자 전달 수정사항 (QA 대응)

**전달 일자**: 2026-02-03
**작성자**: Claude Code (Frontend QA)
**관련 문서**: `docs/report/frontend_qa_20260203.md`

---

## 1. 요약

프론트엔드 QA 중 발견된 **FE-001 (폴링 API 500 에러)**를 수정했습니다.

| 항목 | 상태 | 설명 |
|------|------|------|
| FE-001 | ✅ 수정 완료 | `async with` → `with` 변경 |
| FE-002 | 🔴 확인 필요 | WebSocket 구독자 0명 문제 |
| FE-003 | 🟡 확인 필요 | 숫자만 있는 ELW 분류 |

---

## 2. 백엔드 수정 내역

### 2.1 수정 파일

**파일**: `services/api_gateway/main.py`

**엔드포인트**: `POST /api/kr/realtime-prices`, `GET /api/kr/realtime-prices`

### 2.2 문제 원인

```python
# 문제 코드 (500 에러 발생)
async def get_kr_realtime_prices(request: RealtimePricesRequest):
    async with get_db_session() as db:  # ❌ get_db_session은 일반 제너레이터
        result = await db.execute(query)  # ❌ 동기 세션에서 await 사용 불가
```

**에러 메시지**:
```
'generator' object does not support the asynchronous context manager protocol
```

### 2.3 수정 내용

```python
# 수정 후 코드
async def get_kr_realtime_prices(request: RealtimePricesRequest):
    prices = {}

    # async with → with 변경
    with get_db_session() as db:
        for ticker in request.tickers:
            query = (
                select(DailyPrice)
                .where(DailyPrice.ticker == ticker)
                .order_by(desc(DailyPrice.date))
                .limit(1)
            )
            # await db.execute → db.execute 변경
            result = db.execute(query)
            daily_price = result.scalar_one_or_none()
            # ... 가격 데이터 변환
    return {"prices": prices}
```

### 2.4 변경 사항

| 변경 전 | 변경 후 |
|---------|---------|
| `async with get_db_session()` | `with get_db_session()` |
| `await db.execute(query)` | `db.execute(query)` |

---

## 3. 테스트 방법

### 3.1 API 테스트

```bash
# POST 요청 테스트
curl -X POST http://localhost:5111/api/kr/realtime-prices \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["005930", "000660", "0015N0"]}'

# GET 요청 테스트
curl "http://localhost:5111/api/kr/realtime-prices?tickers=005930,000660,0015N0"
```

### 3.2 기대 결과

```json
{
  "prices": {
    "005930": {
      "ticker": "005930",
      "price": 159400.0,
      "change": 2400.0,
      "change_rate": 1.53,
      "volume": 15234000,
      "timestamp": "2026-02-03"
    },
    "0015N0": {
      "ticker": "0015N0",
      "price": ...,
      ...
    }
  }
}
```

### 3.3 프론트엔드 확인

1. **페이지 접속**: https://stock.ralphpark.com/
2. **콘솔 확인**: 더 이상 `[API Error] POST /api/kr/realtime-prices: 500` 에러 없음
3. **UI 확인**: ELW 종목 카드에 폴링 데이터 표시

---

## 4. 백엔드 개발자 확인 요청

### 4.1 WebSocket 구독 문제 (FE-002)

**증상**: WebSocket 구독자가 0명으로 데이터 수신 안 됨

**조치 필요**:
1. `src/websocket/routes.py`의 구독 처리 로그 확인
2. `src/websocket/server.py:ConnectionManager.subscribe()` 디버깅

**테스트 명령어**:
```bash
curl http://localhost:5111/ws/stats | jq '.subscriptions'
# 기대: price:* 항목에 구독자 1명 이상
```

### 4.2 ELW 분류 문제 (FE-003)

**증상**: 숫자로만 구성된 ELW(`493330`)가 KOSDAQ으로 분류됨

**옵션 1**: 프론트엔드에서 ELW 마스터 데이터 조회 후 분류
**옵션 2**: 백엔드 API에서 종목 정보에 ELW 플래그 추가

---

## 5. 검증 체크리스트

백엔드 개발자 확인 후:

- [ ] API 재배포 완료 (`docker compose restart api-gateway`)
- [ ] POST `/api/kr/realtime-prices` 200 응답 확인
- [ ] GET `/api/kr/realtime-prices` 200 응답 확인
- [ ] 프론트엔드에서 ELW 종목 가격 데이터 표시 확인
- [ ] WebSocket 구독자 수 확인 (FE-002)
- [ ] ELW 분류 개선 방안 논의 (FE-003)

---

## 6. 관련 파일

| 파일 | 설명 |
|------|------|
| `services/api_gateway/main.py` | API 엔드포인트 수정 완료 |
| `src/database/session.py` | `get_db_session()` 제너레이터 |
| `docs/report/frontend_qa_20260203.md` | 전체 QA 보고서 |

---

*전달일: 2026-02-03*
