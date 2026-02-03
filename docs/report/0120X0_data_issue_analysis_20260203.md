# 0120X0 (유진 챔피언) 종목 데이터 미수신 원인 분석 보고서

**분석 일자**: 2026-02-03
**분석자**: Claude Code QA
**종목**: 유진 챔피언중단기크레딧 X클래스 (0120X0)

---

## 1. 문제 개요

### 1.1 발견된 문제

| 항목 | 내용 |
|------|------|
| 종목코드 | 0120X0 |
| 종목명 | 유진 챔피언중단기크레딧 X클래스 |
| 증권유형분류 | KOSPI (ELW 제거 후 변경) |
| 문제 | 데이터가 2026-01-21 이후 업데이트되지 않음 |
| 최신 데이터 | 2026-01-21 (13일 간격) |

### 1.2 다른 시그널 종목 비교

| 종목코드 | 최신 데이터 | 업데이트 간격 |
|----------|------------|--------------|
| 0015N0 (아로마티카) | 2026-02-03 | 1일 |
| 493330 (지에프아이) | 2026-02-03 | 1일 |
| 217590 (티엠씨) | 2026-02-03 | 1일 |
| 0004V0 (엔비알모션) | 2026-02-03 | 1일 |
| 491000 (리브스메드) | 2026-02-03 | 1일 |
| **0120X0 (유진 챔피언)** | **2026-01-21** | **13일** ❌ |

---

## 2. 원인 분석

### 2.1 초기 가설 및 검증

#### 가설 1: ELW 만료로 인한 상장폐지

**검증 결과**: ❌ **부정**

```bash
# pykrx API로 데이터 조회
$ python3 -c "
from pykrx import stock
df = stock.get_market_ohlcv_by_date('20260122', '20260203', '0120X0')
print(f'Data points: {len(df)}')
"

Data points: 9
               시가     고가     저가     종가  거래량       등락률
날짜
2026-01-22   9995   9995   9995   9995  368 -0.050000
2026-01-23   9995   9995   9995   9995    0  0.000000
2026-01-26  10000  10000  10000  10000    0  0.050025
2026-01-27  10000  10000  10000  10000   50  0.000000
2026-01-28  10000  10000  10000  10000    0  0.000000
2026-01-29  10005  10005  10005  10005  475  0.050000
2026-01-30  10005  10005  10005  10005    0  0.000000
2026-02-02  10000  10000  10000  10000    0 -0.049975
2026-02-03   9985   9985   9985   9985   12 -0.150000
```

**결론**: pykrx API는 정상적으로 데이터를 반환함. ELW는 여전히 거래 중.

#### 가설 2: DB에 종목 정보가 없음

**검증 결과**: ❌ **부정**

```sql
SELECT ticker, name, market FROM stocks WHERE ticker = '0120X0';

 ticker |              name               | market
--------+---------------------------------+--------
 0120X0 | 유진 챔피언중단기크레딧 X클래스 | KOSPI
```

**결론**: stocks 테이블에 종목 정보 존재

#### 가설 3: 수집 태스크 문제

**검증 결과**: ✅ **확인됨**

```bash
# 수집 태스크 수동 실행
$ python3 -c "
from src.tasks.collection_tasks import collect_daily_prices
result = collect_daily_prices('0120X0', '2026-01-22', '2026-02-03')
print(f'Collection result: {result} records collected')
"

Collection result: 9 records collected
```

**결론**: 수집 태스크는 정상 작동함

### 2.2 근본 원인

**자동 수집 태스크가 2026-01-21 이후 0120X0 종목을 누락**

가능한 원인:
1. **Celery Beat 스케줄러에서 해당 종목을 건너뜀**
2. **특정 일자에 수집 태스크 실행 실패 후 재시도 안 함**
3. **종목 필터링 로직에서 0120X0이 제외됨**

---

## 3. 데이터 복구

### 3.1 복구 전 상태

```sql
SELECT date, close_price, volume
FROM daily_prices
WHERE ticker = '0120X0'
ORDER BY date DESC
LIMIT 5;

    date    | close_price | volume
------------+-------------+--------
 2026-01-21 |       10000 | 104777
 2026-01-20 |        9995 |      0
 2026-01-19 |        9995 |    301
 2026-01-16 |       10005 |     16
 2026-01-15 |       10005 |      0
```

### 3.2 수동 수집 실행

```bash
# 수동으로 누락된 데이터 수집
python3 -c "
from src.tasks.collection_tasks import collect_daily_prices
collect_daily_prices('0120X0', '2026-01-22', '2026-02-03')
"
```

### 3.3 복구 후 상태

```sql
SELECT date, close_price, volume
FROM daily_prices
WHERE ticker = '0120X0'
ORDER BY date DESC
LIMIT 10;

    date    | close_price | volume
------------+-------------+--------
 2026-02-03 |        9985 |     12
 2026-02-02 |       10000 |      0
 2026-01-30 |       10005 |      0
 2026-01-29 |       10005 |    475
 2026-01-28 |       10000 |      0
 2026-01-27 |       10000 |     50
 2026-01-26 |       10000 |      0
 2026-01-23 |        9995 |      0
 2026-01-22 |        9995 |    368
 2026-01-21 |       10000 | 104777
```

### 3.4 API 응답 확인

```bash
curl -X POST http://localhost:5111/api/kr/realtime-prices \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["0120X0"]}'

{
  "prices": {
    "0120X0": {
      "ticker": "0120X0",
      "price": 9985.0,
      "change": 0.0,
      "change_rate": 0.0,
      "volume": 12,
      "timestamp": "2026-02-03"
    }
  }
}
```

---

## 4. 해결 방안

### 4.1 단기 해결 (완료)

| 조치 | 상태 |
|------|------|
| 수동으로 누락된 데이터 수집 | ✅ 완료 |
| API 응답 정상화 확인 | ✅ 완료 |

### 4.2 장기 해결 (필요)

#### 1. 수집 태스크 로그 강화

**파일**: `src/tasks/collection_tasks.py`

```python
@shared_task(name="tasks.collect_daily_prices")
def collect_daily_prices(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    logger.info(f"📊 {ticker} 일봉 데이터 수집 시작...")

    # ... 수집 로직 ...

    # 수집 결과 로그 강화
    logger.info(f"✅ {ticker} 일봉 데이터 {len(df)}개 조회 완료 (기간: {start_date} ~ {end_date})")

    # 수집된 데이터가 없는 경우 경고
    if df.empty:
        logger.warning(f"⚠️ {ticker} 일봉 데이터 없음 (기간: {start_date} ~ {end_date})")
```

#### 2. Celery Beat 모니터링

**Celery Beat 로그 확인**:
```bash
docker logs celery-beat --tail 100 | grep -i "collect"
```

#### 3. 데이터 갭 모니터링 시스템

**추가 필요**: 각 종목의 최신 데이터 날짜를 모니터링하고, 일정 기간 이상 업데이트되지 않은 종목을 알림

```python
# 예시: 데이터 갭 검출 쿼리
SELECT
    s.ticker,
    s.name,
    MAX(dp.date) as latest_date,
    (CURRENT_DATE - MAX(dp.date)::date) as days_since_update
FROM daily_prices dp
JOIN stocks s ON s.ticker = dp.ticker
GROUP BY s.ticker, s.name
HAVING (CURRENT_DATE - MAX(dp.date)::date) > 3  -- 3일 이상 업데이트 없음
ORDER BY days_since_update DESC;
```

---

## 5. 요약

### 5.1 문제

- 0120X0 종목의 데이터가 2026-01-21 이후 업데이트되지 않음 (13일 간격)

### 5.2 원인

- 자동 수집 태스크가 해당 종목을 누락
- pykrx API는 정상적으로 데이터를 반환함 (ELW 만료 아님)

### 5.3 해결

- 수동으로 `collect_daily_prices()` 태스크 실행하여 9개 레코드 수집 완료
- 현재 최신 데이터(2026-02-03) 정상 표시됨

### 5.4 향후 조치

1. 수집 태스크 실패 모니터링 강화
2. 데이터 갭 자동 검출 및 알림 시스템 구축
3. Celery Beat 스케줄 정기 검증

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
