# 백엔드 수정 요청: 차트 데이터 문제

**요청 일자:** 2026-02-02
**우선순위:** P0 - CRITICAL
**요청자:** 프론트엔드 팀

---

## 1. 문제 개요

차트 페이지에서 데이터가 표시되지 않는 문제가 발생했습니다. 프론트엔드는 정상 동작하나, DB에 OHLCV 데이터가 존재하지 않아 차트가 렌더링되지 않습니다.

### 현재 상황

```bash
# API 응답 상태
GET /api/kr/stocks/005930/chart?period=6mo
Response: {
  "ticker": "005930",
  "period": "6mo",
  "data": [],           # 빈 배열
  "total_points": 0     # 데이터 0건
}
```

---

## 2. 원인 분석

### 2.1 데이터베이스 데이터 부족

```sql
-- DB 확인 쿼리 (실행 필요)
SELECT ticker, COUNT(*), MAX(date) as latest_date
FROM daily_prices
GROUP BY ticker
ORDER BY ticker;
```

**예상 결과:** 데이터 0건 또는 최신 데이터 부족

### 2.2 가능한 원인

1. **Celery worker가 실행 중이 아님**
   - Docker 컨테이너 상태 확인 필요
   - `docker ps | grep celery`

2. **데이터 수집 태스크가 실행되지 않음**
   - `collect_daily_prices` 태스크 스케줄링 확인
   - Celery beat 설정 확인

3. **KRX 수집기 연결 문제**
   - KRX API 연결 상태 확인
   - 에러 로그 확인

---

## 3. 요청 작업

### Phase 1: 인프라 상태 확인

```bash
# 1. Docker 컨테이너 상태 확인
docker ps | grep -E "(celery|postgres|api-gateway)"

# 2. Celery 로그 확인
docker logs ralph-stock-celery-worker-1 --tail 50

# 3. DB 데이터 확인
docker exec -it ralph-stock-postgres-1 psql -U postgres -d ralph_stock -c "
SELECT ticker, COUNT(*), MAX(date) as latest_date
FROM daily_prices
GROUP BY ticker
ORDER BY ticker;
"
```

### Phase 2: 데이터 수집 태스크 실행

```bash
# Celery worker가 실행 중이 아니면 시작
docker compose up -d celery-worker celery-beat

# 데이터 수집 태스크 수동 실행 (API 통해)
curl -X POST http://localhost:5111/api/kr/collect/daily-prices

# 또는 Python 직접 실행
docker exec -it ralph-stock-api-gateway-1 python -c "
from src.tasks.collection_tasks import collect_daily_prices
collect_daily_prices.delay()
"
```

### Phase 3: 스케줄링 확인

```python
# tasks/celery_app.py에서 beat 스케줄 확인
# app.conf.beat_schedule에 collect_daily_prices가 있는지 확인

# 예상 설정:
app.conf.beat_schedule = {
    'collect-daily-prices': {
        'task': 'src.tasks.collection_tasks.collect_daily_prices',
        'schedule': crontab(hour='9', minute='30'),  # 매일 09:30
    },
}
```

---

## 4. 검증 단계

데이터 수집 후 다음 API로 확인:

```bash
# 데이터 수집 후 확인
curl http://localhost:5111/api/kr/stocks/005930/chart?period=6mo

# 기대 응답:
{
  "ticker": "005930",
  "period": "6mo",
  "data": [
    {
      "date": "2025-08-01",
      "open": 75000,
      "high": 76000,
      "low": 74500,
      "close": 75500,
      "volume": 15000000
    },
    ...
  ],
  "total_points": 120
}
```

---

## 5. 관련 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| Celery App | `tasks/celery_app.py` | Celery 설정 및 스케줄 |
| Collection Tasks | `src/tasks/collection_tasks.py` | 데이터 수집 태스크 |
| KRX Collector | `src/collectors/krx_collector.py` | KRX 데이터 수집기 |
| Daily Price Repo | `src/repositories/daily_price_repository.py` | DB 저장 로직 |

---

## 6. 프론트엔드 수정 완료 사항 (참고)

프론트엔드에서 이미 다음 수정이 완료되었습니다:

1. **API 파라미터 통합** (P1 - 완료)
   - `days` → `period` 파라미터로 변경
   - 백엔드와 동일한 파라미터 사용 ("1mo", "3mo", "6mo", "1y")

2. **에러 처리 개선** (P2 - 완료)
   - 데이터 없음 안내 메시지 추가
   - 재시도 버튼 제공
   - 로딩 상태 개선

---

## 7. 우선순위 및 예상 소요시간

| 우선순위 | 작업 | 예상 소요시간 |
|----------|------|---------------|
| P0 | Celery worker 상태 확인 및 시작 | 30분 |
| P0 | 데이터 수집 태스크 실행 | 30분 |
| P1 | 스케줄링 설정 확인 및 수정 | 1시간 |
| P2 | 모니터링 알림 추가 | 2시간 |

---

## 8. 연락처

질문 사항이 있으면 프론트엔드 팀에 문의 바랍니다.

---

*문서 작성: 프론트엔드 팀*
*참고 문서: `docs/report/chart_page_analysis_20260202.md`*
