# 백엔드 개발자 전달 수정사항

**전달 일자**: 2026-02-03
**작성자**: Claude Code (Frontend)
**수정 범위**: 프론트엔드 ELW 지원 + 백엔드 폴링 API 구현

---

## 1. 요약

프론트엔드에서 **ELW 종목 실시간 가격 표시**를 위해 다음과 같은 수정이 진행되었습니다.

| 구분 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 프론트엔드 | `useRealtimePrices` 연결 확인 | ✅ 완료 | WebSocket 연결 후 구독 |
| 프론트엔드 | `RealtimePriceCard` 개선 | ✅ 완료 | 데이터 소스 뱃지, 폴링 Fallback |
| 백엔드 | `/api/kr/realtime-prices` 구현 | ✅ 완료 | DB 조회 기반 |

---

## 2. 백엔드 수정 내역

### 2.1 폴링 API 구현

**파일**: `services/api_gateway/main.py`

**엔드포인트**: `POST /api/kr/realtime-prices`

**변경 사항**:
- 기존: `return {"prices": {}}` (빈 결과 반환)
- 변경: DB에서 최신 일봉 데이터 조회하여 반환

**구현 코드**:
```python
async def get_kr_realtime_prices(request: RealtimePricesRequest):
    """
    실시간 가격 일괄 조회

    ## 설명
    여러 종목의 실시간 가격 정보를 일괄 조회합니다.
    DB에 저장된 최신 일봉 데이터를 반환합니다.

    ## Request Body
    - **tickers**: 종목 코드 리스트

    ## 반환 데이터
    - **prices**: 종목별 실시간 가격 정보
    """
    prices = {}

    async with get_db_session() as db:
        for ticker in request.tickers:
            try:
                # 최신 일봉 데이터 조회
                query = (
                    select(DailyPrice)
                    .where(DailyPrice.ticker == ticker)
                    .order_by(desc(DailyPrice.date))
                    .limit(1)
                )
                result = await db.execute(query)
                daily_price = result.scalar_one_or_none()

                if daily_price:
                    change = daily_price.close_price - daily_price.open_price
                    change_rate = 0.0
                    if daily_price.open_price and daily_price.open_price > 0:
                        change_rate = (change / daily_price.open_price) * 100

                    prices[ticker] = {
                        "ticker": ticker,
                        "price": daily_price.close_price,
                        "change": change,
                        "change_rate": change_rate,
                        "volume": daily_price.volume,
                        "timestamp": daily_price.date.isoformat() if daily_price.date else datetime.utcnow().isoformat(),
                    }
                    logger.debug(f"[RealtimePrices] {ticker}: {daily_price.close_price}")
                else:
                    logger.warning(f"[RealtimePrices] No price data found for {ticker}")

            except Exception as e:
                logger.error(f"[RealtimePrices] Error fetching price for {ticker}: {e}")
                continue

    return {"prices": prices}
```

---

## 3. 프론트엔드 수정 내역

### 3.1 useRealtimePrices 연결 상태 확인

**파일**: `frontend/hooks/useWebSocket.ts`

**변경 사항**: WebSocket 연결(`connected`) 확인 후 구독

```typescript
// 변경 전
useEffect(() => {
  tickers.forEach((ticker) => {
    subscribe(`price:${ticker}`);
  });
  // ...
}, [tickers.join(","), subscribe, unsubscribe]); // connected 없음

// 변경 후
useEffect(() => {
  if (!connected) {  // 연결 상태 확인
    console.log(`[useRealtimePrices] Waiting for connection...`);
    return;
  }

  tickers.forEach((ticker) => {
    subscribe(`price:${ticker}`);
  });
  // ...
}, [tickers.join(","), subscribe, unsubscribe, connected]); // connected 추가
```

### 3.2 RealtimePriceCard 개선

**파일**: `frontend/components/RealtimePriceCard.tsx`

**추가 기능**:
1. ELW 종목 식별 (`isELW()`, `getTickerCategory()`)
2. 데이터 소스 뱃지 (실시간/폴링/연결 중/대기 중)
3. 폴링 Fallback (15초 간격)
4. ELW 안내 메시지

```typescript
// ELW 식별
function isELW(ticker: string): boolean {
  return ticker.length === 6 && /[A-Za-z]/.test(ticker);
}

// 폴링 Fallback
useEffect(() => {
  if (realtimeSupported && connected) return;  // WebSocket 정상 작동 시 스킵
  if (realtimePrice) return;  // WebSocket 데이터 있으면 스킵

  const fetchPollingPrice = async () => {
    const prices = await apiClient.getRealtimePrices([ticker]);
    if (prices[ticker]) {
      setPollingPrice(prices[ticker]);
      setDataSource("polling");
    }
  };

  fetchPollingPrice();
  const interval = setInterval(fetchPollingPrice, 15000);
  return () => clearInterval(interval);
}, [ticker, realtimeSupported, connected, realtimePrice]);
```

---

## 4. 테스트 방법

### 4.1 API 테스트

```bash
# 1. API 서비스 재시작
docker compose restart api-gateway

# 2. API 테스트
curl -X POST http://localhost:5111/api/kr/realtime-prices \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["005930", "000660", "0015N0"]}'

# 기대 결과:
{
  "prices": {
    "005930": {
      "ticker": "005930",
      "price": 159400.0,
      "change": ...,
      "change_rate": ...,
      "volume": ...,
      "timestamp": "2026-02-03"
    },
    "0015N0": {
      # ELW 종목 데이터 (DB에 있는 경우)
    }
  }
}
```

### 4.2 프론트엔드 테스트

1. **페이지 접속**: https://stock.ralphpark.com/
2. **콘솔 확인**:
   ```
   [useRealtimePrices] Waiting for connection...
   [useRealtimePrices] Subscribing to price:005930
   ```
3. **UI 확인**:
   - "실시간" 뱃지 (WebSocket 연결 시)
   - "폴링 ELW" 뱃지 (ELW 종목)
   - 가격 데이터 정상 표시

### 4.3 WebSocket 구독자 확인

```bash
curl http://localhost:5111/ws/stats | jq '.subscriptions'

# 기대 결과:
{
  "price:005930": 1,  # ← 구독자 1명 이상
  "price:000660": 1,
  "market-gate": 1
}
```

---

## 5. 검증 체크리스트

- [ ] API 빌드 성공 (`docker compose build api-gateway`)
- [ ] API 서비스 정상 시작 (`docker compose up -d api-gateway`)
- [ ] `/api/kr/realtime-prices` 엔드포인트 응답 확인
- [ ] ELW 종목 데이터 반환 확인
- [ ] 프론트엔드에서 가격 데이터 표시 확인
- [ ] 데이터 소스 뱃지 정상 표시

---

## 6. 관련 문서

- `docs/report/frontend_analysis_20260203.md` - 프론트엔드 분석 보고서
- `docs/report/frontend_verification_20260203.md` - 프론트엔드 검증 보고서
- `docs/report/realtime_price_issue_analysis_20260203.md` - 실시간 가격 이슈 분석

---

*문서 작성: 2026-02-03*
