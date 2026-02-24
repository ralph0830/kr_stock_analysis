# 거래정지 종목 필터링 구현 제안서

**작성 일시:** 2026-02-06 14:15
**대상:** 단타 추천 시스템 (Daytrading Scanner)
**문제:** DH오토넥스(000300) 등 거래정지 종목이 스캔 결과에 포함됨

---

## 1. 문제 분석

### 1.1 현재 상황

| 항목 | 내용 |
|------|------|
| **발생 종목** | DH오토넥스 (000300) |
| **종목 상태** | 거래정지 (관리종목) |
| **문제** | 단타 스캔 결과에 거래정지 종목이 포함됨 |
| **영향** | 매매 불가능한 종목이 추천되어 사용자 경험 저하 |

### 1.2 DH오토넥스 상태 확인

```
종목코드: 000300
종목명: DH오토넥스
상태: 거래정지 (관리종목 지정)
사유: [별도 확인 필요]
```

### 1.3 현재 필터링 로직 분석

**파일:** `services/daytrading_scanner/scanner.py:270-294`

```python
def _get_stocks(self, db: Optional[Session], market: Optional[str]) -> List[Stock]:
    """종목 리스트 조회"""
    from src.database.models import Stock as StockModel

    query = select(StockModel).where(
        StockModel.is_etf == False,
        StockModel.is_admin == False,      # ← 관리종목 필터링 있음
        StockModel.is_spac == False,
        StockModel.is_bond == False,
        StockModel.is_excluded_etf == False,
    )
    # ...
```

**분석:**
- `is_admin` 필드로 관리종목을 필터링하도록 되어 있음
- 하지만 DB에 저장된 데이터가 최신 상태가 아닐 수 있음
- 키움 API의 `state` 필드를 활용하여 실시간 필터링 필요

---

## 2. 키움 API 종목 상태 정보

### 2.1 API 응답 필드

**API:** `ka10099` (종목정보 리스트 조회)

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `code` | string | 종목코드 | "000300" |
| `name` | string | 종목명 | "DH오토넥스" |
| `state` | string | 종목상태 | "거래정지", "관리종목", "증거금100%" |

### 2.2 거래정지 관련 상태 키워드

| 키워드 | 설명 |
|--------|------|
| `관리종목` | 투자위험 등으로 관리대상 지정된 종목 |
| `증거금100%` | 증거금 100% 예치 필요한 종목 |
| `투자유의환기종목` | 투자 유의가 필요한 종목 |
| `정리매매` | 정리매매 대상 종목 |
| `거래정지` | 거래가 중지된 종목 |
| `시장주의` | 시장 주의종목 지정 |

---

## 3. 구현 제안

### 3.1 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    거래정지 종목 필터링 흐름                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. DaytradingScanner.scan_market() 실행                               │
│           ↓                                                             │
│  2. DB에서 종목 조회 (기존 필터링 적용)                                 │
│           ↓                                                             │
│  3. Kiwoom API로 종목 상태 실시간 확인 (신규)                           │
│           ↓                                                             │
│  4. 거래정지 종목 필터링 (신규)                                        │
│           ↓                                                             │
│  5. 필터링된 종목만 점수 계산                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 구현 옵션 비교

| 옵션 | 장점 | 단점 | 추천 |
|------|------|------|------|
| **A. DB 컬럼 추가** | 빠름, DB 인덱스 활용 | 동기화 주기 문제 | 2순위 |
| **B. 실시간 API 확인** | 항상 최신 상태 | API 호출 비용 | 1순위 |
| **C. 캐싱 활용** | 성능/최신성 균형 | 복잡도 증가 | 2순위 |

**추천:** 옵션 B (실시간 API 확인) + 옵션 C (캐싱) 혼합

---

## 4. 상세 구현 방안

### 4.1 방법 1: KiwoomRestAPI에 필터링 메서드 추가

**파일:** `src/kiwoom/rest_api.py`

```python
class KiwoomRestAPI:
    # 기존 코드...

    # 거래정지 상태 키워드
    TRADING_SUSPENDED_KEYWORDS = [
        "관리종목",
        "증거금100%",
        "투자유의환기종목",
        "정리매매",
        "거래정지",
        "시장주의",
    ]

    def is_trading_suspended(self, state: str) -> bool:
        """
        종목 상태가 거래정지인지 확인

        Args:
            state: 종목 상태 문자열

        Returns:
            거래정지 여부
        """
        if not state:
            return False
        return any(keyword in state for keyword in self.TRADING_SUSPENDED_KEYWORDS)

    async def get_suspended_stocks(
        self,
        market: str = "ALL"
    ) -> Dict[str, str]:
        """
        거래정지 종목 목록 조회

        Args:
            market: 시장 구분 ("KOSPI", "KOSDAQ", "ALL")

        Returns:
            {종목코드: 종목상태} 딕셔너리
        """
        all_stocks = await self.get_stock_list(market)

        suspended = {}
        for stock in all_stocks:
            state = stock.get("state", "")
            if self.is_trading_suspended(state):
                suspended[stock["ticker"]] = state

        logger.info(f"거래정지 종목 {len(suspended)}개 확인됨")
        return suspended
```

### 4.2 방법 2: DaytradingScanner에 필터링 로직 추가

**파일:** `services/daytrading_scanner/scanner.py`

```python
class DaytradingScanner:
    # 기존 코드...

    # 거래정지 상태 캐시 (1시간 유효)
    _suspended_stocks_cache: Dict[str, str] = {}
    _suspended_cache_time: Optional[float] = None
    _SUSPENDED_CACHE_TTL = 3600  # 1시간

    async def _get_suspended_stocks(self, kiwoom_api) -> Dict[str, str]:
        """
        거래정지 종목 목록 조회 (캐싱 활용)

        Returns:
            {종목코드: 종목상태} 딕셔너리
        """
        import time

        current_time = time.time()

        # 캐시 유효성 확인
        if (self._suspended_cache_time and
            current_time - self._suspended_cache_time < self._SUSPENDED_CACHE_TTL):
            logger.debug("거래정지 종목 캐시 사용")
            return self._suspended_stocks_cache

        # API 호출로 갱신
        try:
            suspended = await kiwoom_api.get_suspended_stocks("ALL")
            self._suspended_stocks_cache = suspended
            self._suspended_cache_time = current_time
            return suspended
        except Exception as e:
            logger.warning(f"거래정지 종목 조회 실패: {e}, 캐시된 데이터 사용")
            return self._suspended_stocks_cache

    def _is_trading_suspended(
        self,
        ticker: str,
        suspended_stocks: Dict[str, str]
    ) -> bool:
        """
        종목이 거래정지인지 확인

        Args:
            ticker: 종목코드
            suspended_stocks: 거래정지 종목 목록

        Returns:
            거래정지 여부
        """
        return ticker in suspended_stocks

    async def _scan_with_db(
        self,
        db: Session,
        market: Optional[str],
        limit: int
    ) -> List[DaytradingScoreResult]:
        """DB 세션을 사용한 실제 스캔 로직"""

        # 종목 조회
        stocks = self._get_stocks(db, market)

        # Kiwoom API 클라이언트 초기화
        kiwoom_api = None
        try:
            from src.kiwoom.rest_api import KiwoomRestAPI
            kiwoom_api = KiwoomRestAPI.from_env()
            await kiwoom_api.issue_token()

            # 거래정지 종목 목록 조회
            suspended_stocks = await self._get_suspended_stocks(kiwoom_api)
            logger.info(f"거래정지 종목 {len(suspended_stocks)}개 필터링 대상")

        except Exception as e:
            logger.warning(f"Kiwoom API initialization failed: {e}")
            suspended_stocks = {}

        # 점수 계산
        results = []
        scanned_count = 0
        suspended_count = 0

        for stock in stocks[:limit]:
            try:
                scanned_count += 1

                # 거래정지 종목 필터링 (신규)
                if kiwoom_api and self._is_trading_suspended(stock.ticker, suspended_stocks):
                    suspended_count += 1
                    state = suspended_stocks.get(stock.ticker, "알 수 없음")
                    logger.info(f"거래정지 종목 제외: {stock.ticker} {stock.name} ({state})")
                    continue

                # 기존 스캔 로직 계속...
                # ...

            except Exception as e:
                logger.error(f"Error scanning {stock.ticker}: {e}")

        logger.info(
            f"스캔 완료: 전체 {scanned_count}개 중 "
            f"거래정지 {suspended_count}개 제외, "
            f"결과 {len(results)}개"
        )

        return results
```

### 4.3 방법 3: DB 스키마 업데이트 (선택 사항)

**파일:** `src/database/models.py`

```python
class Stock(Base):
    __tablename__ = "stocks"

    # 기존 필드...
    is_admin = Column(Boolean, default=False)  # 관리종목

    # 신규 필드 추가
    is_trading_suspended = Column(Boolean, default=False)  # 거래정지 여부
    stock_state = Column(String(50))  # 종목 상태 (관리종목, 거래정지 등)
    state_updated_at = Column(DateTime(timezone=True))  # 상태 업데이트 시간
```

---

## 5. 구현 순서

### Phase 1: KiwoomRestAPI 기능 추가 (우선)

| 단계 | 작업 | 파일 |
|------|------|------|
| 1.1 | `is_trading_suspended()` 메서드 추가 | `src/kiwoom/rest_api.py` |
| 1.2 | `get_suspended_stocks()` 메서드 추가 | `src/kiwoom/rest_api.py` |
| 1.3 | 단위 테스트 작성 | `tests/test_kiwoom_api.py` |

### Phase 2: DaytradingScanner 필터링 로직 추가

| 단계 | 작업 | 파일 |
|------|------|------|
| 2.1 | `_get_suspended_stocks()` 메서드 추가 | `services/daytrading_scanner/scanner.py` |
| 2.2 | `_is_trading_suspended()` 메서드 추가 | `services/daytrading_scanner/scanner.py` |
| 2.3 | `_scan_with_db()`에 필터링 로직 통합 | `services/daytrading_scanner/scanner.py` |
| 2.4 | 통합 테스트 | `tests/test_daytrading_scanner.py` |

### Phase 3: 캐싱 최적화 (선택)

| 단계 | 작업 | 파일 |
|------|------|------|
| 3.1 | Redis 캐시 구현 | `src/cache/cache_client.py` |
| 3.2 | 캐시 만료 정책 설정 | `services/daytrading_scanner/scanner.py` |

---

## 6. 테스트 시나리오

### 6.1 단위 테스트

```python
import pytest
from src.kiwoom.rest_api import KiwoomRestAPI

def test_is_trading_suspended():
    api = KiwoomRestAPI(...)

    # 거래정지 상태
    assert api.is_trading_suspended("관리종목") == True
    assert api.is_trading_suspended("증거금100%") == True
    assert api.is_trading_suspended("정리매매") == True
    assert api.is_trading_suspended("거래정지") == True

    # 정상 상태
    assert api.is_trading_suspended("정상") == False
    assert api.is_trading_suspended("") == False
    assert api.is_trading_suspended(None) == False
```

### 6.2 통합 테스트

```python
@pytest.mark.asyncio
async def test_suspended_stock_filtering():
    scanner = DaytradingScanner()

    # DH오토넥스(000300)이 필터링되는지 확인
    results = await scanner.scan_market({"market": "ALL", "limit": 100})

    # 거래정지 종목이 결과에 없어야 함
    suspended_tickers = ["000300"]  # DH오토넥스
    for ticker in suspended_tickers:
        assert all(r.ticker != ticker for r in results), \
            f"거래정지 종목 {ticker}가 필터링되지 않음"
```

---

## 7. 롤백 계획

| 상황 | 조치 |
|------|------|
| API 호출 실패율 높음 | 캐시된 데이터 사용, 기존 로직으로 롤백 |
| 성능 저하 | 캐시 TTL 조정, 비동기 처리 |
| 필터링 오류 | 로그 확인 후 핫픽스 |

---

## 8. 모니터링 항목

| 항목 | 측정 방법 | 목표 |
|------|-----------|------|
| 거래정지 종목 필터링 수 | 로그 확인 | 100% |
| API 호출 응답 시간 | 메트릭 수집 | <2초 |
| 캐시命中率 | 메트릭 수집 | >90% |

---

## 9. 참고 자료

- 키움증권 REST API 가이드: ka10099 TR
- 기존 코드: `src/kiwoom/rest_api.py:1271-1430`
- 스캐너 코드: `services/daytrading_scanner/scanner.py:270-294`

---

**작성자:** Claude Code
**문서 경로:** `/home/ralph/work/python/kr_stock_analysis/docs/report/trading_suspension_filtering_proposal_20260206.md`
