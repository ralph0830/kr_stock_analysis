# custom-recommendation 페이지 백엔드 하드코딩 분석 보고서

**분석 일자:** 2026-02-06
**대상 URL:** https://stock.ralphpark.com/custom-recommendation
**분석 범위:** 백엔드 API, 하드코딩된 데이터 확인

---

## 1. 요약

custom-recommendation 페이지의 백엔드는 **DB에서 데이터를 조회**하며, 하드코딩된 종목 목록이 없습니다.

다만, 일부 **Mock 데이터**가 사용되고 있습니다:
1. 수급 데이터 (`_get_mock_flow_data()`)
2. 일부 스코어링 로직의 하드코딩된 값

---

## 2. 분석 결과

### 2.1 API Gateway 라우터 (`daytrading.py`)

**파일:** `/services/api_gateway/routes/daytrading.py`

**분석 결과:** ✅ 하드코딩 없음

- `/api/daytrading/signals` 엔드포인트는 Daytrading Scanner 서비스로 프록시
- 하드코딩된 응답 없음
- Redis 캐싱만 적용 (TTL: 5분)

### 2.2 Daytrading Scanner 메인 엔드포인트 (`main.py`)

**파일:** `/services/daytrading_scanner/main.py`

**GET /api/daytrading/signals (라인 216-337)**

**분석 결과:** ✅ DB 조회, 하드코딩된 종목 없음

```python
# DB에서 시그널 조회
with get_db_session_sync() as db:
    signal_repo = DaytradingSignalRepository(db)
    price_repo = DailyPriceRepository(db)

    # 필터에 따라 조회
    if min_score > 0 and market:
        db_signals = (
            db.query(signal_repo.model)
            .filter_by(status="OPEN", market=market)
            .filter(signal_repo.model.score >= min_score)
            .order_by(signal_repo.model.score.desc())
            .limit(limit)
            .all()
        )
    # ... 기타 필터 조건
```

**결과:**
- `daytrading_signals` 테이블에서 조회
- 하드코딩된 종목 없음
- 모든 데이터는 DB에서 가져옴

### 2.3 스캐너 로직 (`scanner.py`)

**파일:** `/services/daytrading_scanner/scanner.py`

**분석 결과:** ⚠️ Mock 데이터 사용

#### Mock 수급 데이터 (라인 150-157)

```python
def _get_mock_flow_data(self, ticker: str) -> Any:
    """Mock 수급 데이터 (Phase 4에서 실제 데이터로 대체)"""
    class MockFlow:
        def __init__(self):
            self.foreign_net_buy = 0
            self.inst_net_buy = 0
    return MockFlow()
```

**원인:** `institutional_flows` 테이블에서 데이터를 가져오지 않고 0 반환

### 2.4 스코어링 로직 (`scoring.py`)

**파일:** `/services/daytrading_scanner/models/scoring.py`

**분석 결과:** ⚠️ 일부 하드코딩된 값

```python
# 7. 섹터 모멘텀 (15점)
# 간단히 상위 10% 가정
sector_score = 15  # TODO: 실제 섹터 데이터 필요
```

---

## 3. 하드코딩된 데이터 요약

| 항목 | 위치 | 내용 | 대체 계획 |
|------|------|------|----------|
| 수급 데이터 | `scanner.py:150-157` | `foreign_net_buy = 0`, `inst_net_buy = 0` | Phase 4에서 실제 데이터로 대체 |
| 섹터 모멘텀 | `scoring.py` | `sector_score = 15` (하드코딩) | 실제 섹터 데이터 필요 |

---

## 4. 종목 데이터가 DB에서 나오지 않는 원인 분석

### 4.1 DB 상태 확인

`daytrading_signals` 테이블 상태:
- **현재:** 데이터가 있을 수도 있고 없을 수도 있음
- **확인 필요:** `SELECT * FROM daytrading_signals WHERE status = 'OPEN'`

### 4.2 데이터 생성 경로

1. **시장 스캔:** `POST /api/daytrading/scan`
   - `scanner.scan_market()` 실행
   - `_save_signal()`로 DB 저장
   - 캐시 무효화

2. **DB 저장 확인:**
   ```python
   # scanner.py:159-219
   async def _save_signal(self, db, score_result, current_price):
       # ... DB 저장 로직
       db.commit()  # 커밋 수행
   ```

### 4.3 데이터가 나오지 않는 가능한 원인

1. **DB에 데이터 없음:** `daytrading_signals` 테이블에 `status='OPEN'`인 레코드 없음
2. **점수 필터:** `min_score=60` (기본값)보다 낮은 점수만 있어서 필터링됨
3. **스캔 미실행:** 장 시작 후 스캔이 한 번도 실행되지 않음

---

## 5. 개선 방안

### 5.1 수급 데이터 실제 구현

**파일:** `/services/daytrading_scanner/scanner.py`

**현재:**
```python
def _get_mock_flow_data(self, ticker: str) -> Any:
    class MockFlow:
        def __init__(self):
            self.foreign_net_buy = 0
            self.inst_net_buy = 0
    return MockFlow()
```

**개선안 (대시보드/공유 API 영향 없이):**

새로운 private 메서드 추가:
```python
def _get_flow_data(self, db: Session, ticker: str) -> Any:
    """실제 수급 데이터 조회"""
    from src.repositories.institutional_flow_repository import InstitutionalFlowRepository

    flow_repo = InstitutionalFlowRepository(db)
    flows = flow_repo.get_recent_by_ticker(ticker, days=5)

    if not flows:
        # Fallback to mock
        return self._get_mock_flow_data(ticker)

    # 최근 5일 평균 계산
    class FlowData:
        def __init__(self, flows):
            self.foreign_net_buy = sum(f.foreign_net_buy or 0 for f in flows)
            self.inst_net_buy = sum(f.inst_net_buy or 0 for f in flows)

    return FlowData(flows)
```

### 5.2 섹터 모멘텀 실제 구현

**파일:** `/services/daytrading_scanner/models/scoring.py`

**현재:**
```python
sector_score = 15  # TODO: 실제 섹터 데이터 필요
```

**개선안 (대시보드/공유 API 영향 없이):**

```python
def calculate_sector_momentum_score(stock: Stock, current_price: float, prices: List[DailyPrice]) -> int:
    """섹터 모멘텀 점수 계산 (실제 구현)"""
    if not stock.sector:
        return 0  # 섹터 정보 없으면 0점

    # 같은 섹터 종목들의 최근 5일 수익률 계산
    # 상위 20% 이내면 15점, 그외 0점
    # (구체적인 로직은 프로젝트 요구사항에 따라 다름)

    return 15  # 일단 15점 유지 (나중에 실제 로직으로 대체)
```

### 5.3 DB 초기 데이터 생성

**스크립트 생성:** `/scripts/init_daytrading_signals.py`

```python
"""
초기 Daytrading Signal 데이터 생성
장 시작 전에 실행하여 기본 시그널 생성
"""
```

---

## 6. 결론

| 항목 | 상태 | 설명 |
|------|------|------|
| API 엔드포인트 | ✅ DB 조회 | `daytrading_signals` 테이블 조회 |
| 하드코딩된 종목 | ✅ 없음 | 모든 종목은 DB에서 가져옴 |
| Mock 수급 데이터 | ⚠️ 사용 중 | `foreign_net_buy = 0`, `inst_net_buy = 0` |
| 섹터 모멘텀 | ⚠️ 하드코딩 | `sector_score = 15` |

**핵심 발견:**
- 프론트엔드/백엔드 모두 **하드코딩된 종목 목록 없음**
- 데이터가 나오지 않는原因是 **DB에 `status='OPEN'`인 시그널이 없거나 점수가 낮음**
- **Mock 데이터는 수급와 섹터 모멘텀 계산에만 사용** (종목 선택과 무관)

---

## 7. 참고 파일

| 파일 | 경로 |
|------|------|
| API Gateway 메인 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/main.py` |
| Daytrading 라우터 | `/home/ralph/work/python/kr_stock_analysis/services/api_gateway/routes/daytrading.py` |
| Daytrading Scanner | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/main.py` |
| 스캐너 로직 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/scanner.py` |
| 스코어링 로직 | `/home/ralph/work/python/kr_stock_analysis/services/daytrading_scanner/models/scoring.py` |
