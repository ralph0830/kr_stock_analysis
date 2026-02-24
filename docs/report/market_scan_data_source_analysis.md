# 시장 스캔 데이터 소스 분석 보고서

**분석 일시:** 2026-02-06  
**분석 대상:** https://stock.ralphpark.com/custom-recommendation 페이지 "시장 스캔" 기능  
**분석 방법:** Playwright 브라우저 자동화, 백엔드 코드 분석, 데이터베이스 확인

---

## 1. 시장 스캔 작동 여부

### 1.1 기능 상태: PARTIAL (부분 작동)

| 항목 | 상태 | 설명 |
|------|------|------|
| API 호출 | 성공 | `POST /api/daytrading/scan` 정상 응답 |
| 프론트엔드 UI | 정상 | 시장 스캔 버튼 클릭 시 로딩 표시 |
| 데이터 반환 | 성공 | 응답 200 OK, 데이터 포함 |
| **데이터 소스** | **Mock** | **실제 데이터가 아닌 하드코딩된 Mock 데이터 반환** |

### 1.2 실제 테스트 결과

**요청:**
```bash
POST https://stock.ralphpark.com/api/daytrading/scan
{"market": "KOSPI", "limit": 10}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "price": 75000,
        "change_rate": 2.5,
        "volume": 20000000,
        "avg_volume": 10000000,
        "volume_ratio": 2.0,
        "total_score": 90,
        "grade": "S"
      },
      {
        "ticker": "000270",
        "name": "기아",
        "price": 120000,
        "change_rate": 1.8,
        "volume": 15000000,
        "avg_volume": 8000000,
        "volume_ratio": 1.88,
        "total_score": 75,
        "grade": "A"
      }
    ],
    "scan_time": "2026-02-06T05:08:19.848302",
    "count": 2
  }
}
```

---

## 2. 데이터 소스 분석 (핵심 발견)

### 2.1 Docker 컨테이너 vs 로컬 소스 코드 불일치

**MD5 해시값 비교:**
```
Docker 컨테이너: fabda1fd4178c756e0c3448c8c992289
로컬 소스 코드:  7f560dd1ff53cf541f8c17f05d9d24c1
```

**결론:** Docker 컨테이너가 **구버전 코드**로 실행 중

### 2.2 Docker 컨테이너 내부 코드 (Mock 데이터)

`/app/services/daytrading_scanner/main.py` 내용:

```python
# TODO: Phase 4에서 실제 데이터 조회 구현
# 현재는 Mock 데이터 반환
candidates = [
    CandidateDataWithScore(
        ticker="005930",
        name="삼성전자",
        price=75000,
        change_rate=2.5,
        volume=20000000,
        avg_volume=10000000,
        volume_ratio=2.0,
        total_score=90,
        grade="S"
    ),
    CandidateDataWithScore(
        ticker="000270",
        name="기아",
        price=120000,
        change_rate=1.8,
        volume=15000000,
        avg_volume=8000000,
        volume_ratio=1.88,
        total_score=75,
        grade="A"
    ),
    # ... 더 많은 Mock 데이터
]
```

### 2.3 로컬 소스 코드 (실제 스캔 로직 구현됨)

`/services/daytrading_scanner/main.py`:

```python
@app.post("/api/daytrading/scan")
async def scan_market(request: ScanRequest):
    """장중 단타 후보 종목 스캔"""
    from services.daytrading_scanner.scanner import DaytradingScanner
    from src.database.session import get_db_session_sync

    # 실제 스캔 실행
    scanner = DaytradingScanner()

    with get_db_session_sync() as db:
        score_results = await scanner.scan_market(
            {"market": request.market, "limit": request.limit},
            db
        )
    # ... 실제 점수 계산 로직
```

---

## 3. 데이터베이스 상태 분석

### 3.1 일봉 데이터 부족 (근본 원인)

| 테이블 | 레코드 수 | 상태 |
|--------|-----------|------|
| `stocks` | 4,227건 | 정상 |
| `daily_prices` | **0건** | **문제** |
| `daytrading_signals` | 0건 | 빈 상태 |

### 3.2 스캐너 로직 분석

`/services/daytrading_scanner/scanner.py`:

```python
def _get_recent_prices(self, db, ticker: str, days: int = 20):
    """최근 일봉 데이터 조회"""
    # ...
    query = select(DailyPriceModel).where(
        DailyPriceModel.ticker == ticker,
        DailyPriceModel.date >= since_date
    ).order_by(DailyPriceModel.date.desc()).limit(days)
    
    result = db.execute(query)
    return list(result.scalars().all())
```

**문제점:**
- `daily_prices` 테이블에 데이터가 없으면 `_get_recent_prices()`가 빈 리스트 반환
- 빈 리스트로 인해 `calculate_daytrading_score()`에서 "데이터 부족" 처리됨
- 결과적으로 스캔이 0건 반환

### 3.3 점수 계산 로직 분석

`/services/daytrading_scanner/models/scoring.py`:

```python
def calculate_daytrading_score(stock, prices, flow, db: Session = None):
    """단타 종목 종합 점수 계산"""
    if not prices or len(prices) < 2:
        # 데이터 부족
        return DaytradingScoreResult(
            ticker=stock.ticker,
            name=stock.name,
            total_score=0,
            grade="C",
            checks=[DaytradingCheck("데이터 부족", "failed", 0)]
        )
    # ... 실제 점수 계산 (7개 체크리스트)
```

---

## 4. 스캐너 로직 분석

### 4.1 7개 체크리스트 점수 체계 (총 105점)

| 체크리스트 | 배점 | 계산 로직 상태 |
|-----------|------|---------------|
| 거래량 폭증 | 15점 | 구현됨 (volume_ratio >= 2.0시 15점) |
| 모멘텀 돌파 | 15점 | 구현됨 (신고가 갱신 시 15점) |
| 박스권 탈출 | 15점 | 구현됨 (박스 상단 돌파 시 15점) |
| 5일선 위 | 15점 | 구현됨 (MA5 기준) |
| 기관 매수 | 15점 | 구현됨 (외국인+기관 순매수 100억+ 시 15점) |
| 낙폭 과대 | 15점 | 구현됨 (전일 -1%+ 이후 당일 반등 시) |
| 섹터 모멘텀 | 15점 | 구현됨 (섹터 내 상위 20% 시 15점) |

### 4.2 수급 데이터 Fallback 로직

```python
def _get_flow_data(self, db: Session, ticker: str, days: int = 5):
    """실제 수급 데이터 조회 (DailyPrice 테이블 활용)"""
    try:
        prices = price_repo.get_by_ticker_and_date_range(ticker, start_date, end_date)
        
        if not prices or len(prices) < 3:
            # 데이터 부족 시 Mock 반환
            return self._get_mock_flow_data(ticker)
        # ... 실제 계산
    except Exception as e:
        logger.warning(f"Error fetching flow data for {ticker}: {e}, using mock")
        return self._get_mock_flow_data(ticker)

def _get_mock_flow_data(self, ticker: str):
    """Mock 수급 데이터 (fallback용)"""
    class MockFlow:
        def __init__(self):
            self.foreign_net_buy = 0
            self.inst_net_buy = 0
    return MockFlow()
```

---

## 5. 문제 원인 요약

### 5.1 근본 원인

1. **Docker 컨테이너 코드 불일치**
   - 컨테이너: 구버전 (Mock 데이터 반환)
   - 로컬: 신버전 (실제 스캔 로직 구현됨)

2. **데이터베이스 일봉 데이터 누락**
   - `daily_prices` 테이블: 0건
   - Kiwoom REST API 수집이 제대로 작동하지 않거나, 데이터 수집 스크립트 실행되지 않음

3. **키움API 데이터 미사용**
   - 현재 시장 스캔은 키움API를 직접 호출하지 않음
   - DB에 저장된 데이터만 조회 (하지만 DB가 비어있음)

### 5.2 데이터 흐름도

```
[프론트엔드] 
    ↓ POST /api/daytrading/scan
[API Gateway (5111)] 
    ↓ 프록시
[Daytrading Scanner (5115)] 
    ↓ Docker 컨테이너 (구버전)
    ↓ Mock 데이터 반환
[응답] 삼성전자(005930), 기아(000270) 하드코딩된 값
```

**예상되는 정상 흐름:**
```
[프론트엔드]
    ↓ POST /api/daytrading/scan
[API Gateway]
    ↓ 프록시
[Daytrading Scanner]
    ↓ DaytradingScanner.scan_market()
    ↓ _get_recent_prices() ← DB 조회 (daily_prices)
    ↓ calculate_daytrading_score() ← 7개 체크리스트 계산
    ↓ _save_signal() ← DB 저장 (daytrading_signals)
[응답] 실제 스캔된 종목들
```

---

## 6. 개선 방안

### 6.1 단기: Docker 컨테이너 재빌드 (긴급)

```bash
# 1. 구버전 컨테이너 중지 및 삭제
docker compose stop daytrading-scanner
docker compose rm -f daytrading-scanner

# 2. 이미지 재빌드
docker compose build daytrading-scanner

# 3. 컨테이너 재시작
docker compose up -d daytrading-scanner
```

### 6.2 중기: 일봉 데이터 수집

**Kiwoom REST API를 통한 데이터 수집:**

```python
# src/kiwoom/rest_api.py 또는 src/tasks/collection_tasks.py 실행
# 일봉 데이터 수집 태스크
```

**데이터 수집 스크립트 실행:**
```bash
# 방법 1: 수동 스크립트 실행
uv run python scripts/collect_daily_prices.py

# 방법 2: Celery Task 실행
celery -A tasks.celery_app call tasks.collection_tasks.collect_daily_prices_for_all
```

### 6.3 장기: 키움API 실시간 연동

1. **장중 실시간 데이터 연동**
   - Kiwoom REST API 실시간 가격 조회 기능 활성화
   - WebSocket을 통한 실시간 가격 업데이트

2. **데이터 수집 자동화**
   - Celery Beat 스케줄러 등록 (매일 장마감 후 수집)
   - 수집 실패 시 재시도 로직 추가

3. **모니터링 및 알림**
   - 데이터 수집 상태 모니터링
   - `daily_prices` 테이블 데이터 부족 시 알림

### 6.4 점수 계산 로직 개선

1. **모멘텀 돌파 계산 개선**
   - 현재: `calculate_momentum_breakout_score(current_price, 0, current_price, True)` → 항상 15점
   - 개선: 실제 20일 고가 계산

2. **박스권 탈출 계산 개선**
   - 현재: `calculate_box_breakout_score(current_price, current_price, current_price - 5000)` → 항상 15점
   - 개선: 실제 20일 고가/저가 계산

3. **MA5 계산 개선**
   - 현재: 최근 5일 종가 합계 / 5
   - 개선: 20일 이동평균 추가 등

---

## 7. 검증 체크리스트

- [ ] Docker 컨테이너 재빌드 후 로컬 소스 코드와 일치 확인
- [ ] `daily_prices` 테이블에 데이터 수집 확인
- [ ] Kiwoom REST API 연동 상태 확인
- [ ] 시장 스캔 시 실제 종목들 반환되는지 확인
- [ ] 점수 계산이 실제 데이터 기반으로 동작하는지 확인
- [ ] `daytrading_signals` 테이블에 시그널 저장되는지 확인

---

## 8. 결론

1. **현재 상태:** 시장 스캔 기능은 작동하지만 **Mock 데이터**를 반환하고 있음
2. **근본 원인:** Docker 컨테이너가 구버전 코드로 실행 중 + DB에 일봉 데이터 없음
3. **필요 조치:** 
   - Docker 컨테이너 재빌드 (최신 코드 적용)
   - 일봉 데이터 수집 (Kiwoom REST API 또는 KRX 수집)
4. **기대 효과:** 실제 시장 데이터 기반의 단타 추천 종목 제공

---

**작성자:** Claude Code (Full-Stack Integration Specialist)  
**문서 경로:** `/home/ralph/work/python/kr_stock_analysis/docs/report/market_scan_data_source_analysis.md`
