# VCP 스캐너 코스피/코스닥 일반주식만 스캔하도록 개선 방안

**작성 일자**: 2026-02-03
**목적**: VCP 스캐너가 ETF/ETN/ELW/스팩 등을 제외하고 코스피/코스닥 일반주식만 스캔

---

## 1. 현재 상태 분석

### 1.1 VCP Scanner 종목 필터링 로직

**파일**: `services/vcp_scanner/vcp_analyzer.py` (라인 460-482)

```python
# 관리종목, 스팩 종목, 회사채/채권 종목, 제외 ETF/ETN 제외
# NULL 또는 False만 포함
query = query.where(
    or_(
        Stock.is_admin == False,
        Stock.is_admin.is_(None),
    )
).where(
    or_(
        Stock.is_spac == False,
        Stock.is_spac.is_(None),
    )
).where(
    or_(
        Stock.is_bond == False,
        Stock.is_bond.is_(None),
    )
).where(
    or_(
        Stock.is_excluded_etf == False,
        Stock.is_excluded_etf.is_(None),
    )
)
```

### 1.2 DB 모델 필드

**파일**: `src/database/models.py` (라인 23-30)

```python
class Stock(Base):
    sector = Column(String(50), nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    is_etf = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)      # 관리종목
    is_spac = Column(Boolean, default=False)      # 스팩(SPAC) 종목
    is_bond = Column(Boolean, default=False)      # 회사채/채권 종목
    is_excluded_etf = Column(Boolean, default=False)  # 제외할 ETF/ETN
```

### 1.3 문제점

| 문제 | 설명 |
|------|------|
| **의존 필드 의존** | `is_excluded_etf` 등 필터링이 종목 동기화 시 정확히 설정되지 않을 수 있음 |
| **market 필드 미활용** | `market` 필드("KOSPI"/"KOSDAQ")가 있지만 필터링에 활용되지 않음 |
| **하이브리드 방식** | Kiwoom API에서 이미 시장구분 정보를 가져오지만 DB 저장 시 활용 부족 |

---

## 2. Kiwoom API 시장구분 정보

### 2.1 Kiwoom REST API: 종목정보 리스트 조회

**API**: `fn_ka10099` (종목정보 리스트 조회)

**시장구분 코드** (`mrkt_tp`):

| 코드 | 시장 | 설명 |
|------|------|------|
| 0 | KOSPI | 코스피 일반주식 |
| 10 | KOSDAQ | 코스닥 일반주식 |
| 3 | ELW | ELW (상장지수증권) |
| 8 | ETF | ETF |
| 60 | ETN | ETN (상장지수응채권증권) |
| 50 | KONEX | KONEX |
| 4 | K-OTC | 코넥스 |
| 9 | 업종폐업 | 업종폐업 종목 |

### 2.2 Kiwoom API 호출 예시

```python
import requests

def fn_ka10099(token, market_type='0'):
    """종목정보 리스트 조회"""
    host = 'https://api.kiwoom.com'
    endpoint = '/api/dostk/stkinfo'
    url = host + endpoint

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'api-id': 'ka10099',
    }

    data = {
        'mrkt_tp': market_type  # 0=KOSPI, 10=KOSDAQ
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

---

## 3. 현재 종목 동기화 로직 분석

### 3.1 종목 동기화 코드

**파일**: `src/kiwoom/rest_api.py` (라인 1376-1399)

```python
# 제외할 ETF/ETN 패턴 확인
excluded_prefixes = ["TIGER ", "SOL ", "ACE ", "KIWOOM ", "KODEX ", "TREF ",
                   "KOACT ", "ARIRANG ", "HANARO ", "KB ", "TIME ", "PLUS ", "RISE ",
                   "SOURCE ", "MAJOR ", "스팩"]

# 특정 키워드 포함: ETN, 인버스, TOP10
excluded_keywords = ["ETN", "인버스", "TOP10", "TOP5", "레버리지", "리츠"]

is_excluded_etf = any(name.startswith(prefix) for prefix in excluded_prefixes)
is_excluded_etf = is_excluded_etf or any(keyword in name for keyword in excluded_keywords)
```

**문제점**:
- 종목명 패턴 매칭으로 ETF/ETN 식별 → 오류 가능성 있음
- Kiwoom API는 `marketCode`나 `marketName`으로 시장구분을 제공하는데 이를 활용하지 않음

### 3.2 종목 동기화 시 저장되는 필드

**파일**: `tasks/sync_tasks.py` (라인 106-113)

```python
repo.create_if_not_exists(
    ticker=stock_data["ticker"],
    name=stock_data["name"],
    market=stock_data["market"],  # ✅ 시장 정보 저장됨
    sector="",
    market_cap=0,
    is_spac=stock_data.get("is_spac", False),
    is_bond=stock_data.get("is_bond", False),
    is_excluded_etf=stock_data.get("is_excluded_etf", False),  # ✅ ETF/ETN 필드
)
```

---

## 4. 개선 방안

### 4.1 개선 전략

**핵심 아이디어**: DB `market` 필드 활용 + Kiwoom API `marketCode` 활용

| 전략 | 설명 | 우선순위 |
|------|------|----------|
| **A** | VCP Scanner에서 `market` 필드로 직접 필터링 | 높음 |
| **B** | 종목 동기화 시 Kiwoom API `marketCode` 활용 | 높음 |
| **C** | `is_excluded_etf` 필드 폐기 (market 필드로 대체) | 중간 |

### 4.2 개선 방안 A: VCP Scanner에서 market 필드 직접 필터링

**파일**: `services/vcp_scanner/vcp_analyzer.py`

**변경 전**:
```python
# is_admin, is_spac, is_bond, is_excluded_etf 필터 사용
query = query.where(Stock.is_admin == False)
query = query.where(Stock.is_spac == False)
query = query.where(Stock.is_bond == False)
query = query.where(Stock.is_excluded_etf == False)
```

**변경 후**:
```python
# market 필드로 직접 필터링 (KOSPI, KOSDAQ만 포함)
query = query.where(Stock.market.in_(["KOSPI", "KOSDAQ"]))

# 관리종목 추가 제외 (필요시)
query = query.where(
    or_(
        Stock.is_admin == False,
        Stock.is_admin.is_(None),
    )
)

# 스팩 종목 추가 제외 (필요시)
query = query.where(
    or_(
        Stock.is_spac == False,
        Stock.is_spac.is_(None),
    )
)
```

**장점**:
- 간단하고 명확함
- `market` 필드는 종목 동기화 시 Kiwoom API에서 직접 가져옴

### 4.3 개선 방안 B: 종목 동기화 시 marketCode 활용 강화

**파일**: `src/kiwoom/rest_api.py`

**현재 구문석**:
```python
# 종목명 패턴 매칭 (오류 가능성 높음)
excluded_prefixes = ["TIGER ", "SOL ", "ACE ", ...]
excluded_keywords = ["ETN", "인버스", "TOP10", ...]
is_excluded_etf = any(name.startswith(prefix) for prefix in excluded_prefixes)
```

**개선안**:
```python
# Kiwoom API 응답에서 marketCode/marketName 사용
stock_info = item  # Kiwoom API 응답

# 시장구분 코드
market_code = stock_info.get("marketCode", "")  # "0", "10", "3", "8", "60" 등
market_name = stock_info.get("marketName", "")  # "KOSPI", "KOSDAQ", "ELW", "ETF", "ETN" 등

# 일반주식 여부 판단 (코스피, 코스닥만 포함)
is_common_stock = market_code in ["0", "10"]

# 또는 marketName으로 판단
is_common_stock = market_name in ["KOSPI", "KOSDAQ"]

# ETF/ETN 여부
is_etn_or_etf = market_code in ["60", "8"]  # ETN, ETF
is_elw = market_code == "3"  # ELW

# DB 저장 시 market 필드 정확히 설정
# KOSPI -> "KOSPI", KOSDAQ -> "KOSDAQ", 그 외 -> 해당 시장명
```

### 4.4 개선 방안 C: Kiwoom API mrkt_tp 파라미터 활용

**파일**: `src/kiwoom/rest_api.py`의 `get_stock_list()` 메서드

```python
async def get_stock_list(self, market: str = "KOSPI") -> List[Dict]:
    """
    종목 목록 조회

    Args:
        market: "KOSPI" 또는 "KOSDAQ"

    Returns:
        종목 리스트 (일반주식만)
    """
    # Kiwoom API mrkt_tp 파라미터로 시장구분 지정
    market_type_map = {
        "KOSPI": "0",
        "KOSDAQ": "10",
    }

    # fn_ka10099 API 호출로 일반주식만 조회
    params = {
        "mrkt_tp": market_type_map[market]  # "0" or "10"
    }

    # ... API 호출 ...

    # 결과에서 marketCode로 추가 검증
    common_stocks = [
        stock for stock in result['list']
        if stock['marketCode'] in ['0', '10']  # 코스피, 코스닥만
    ]

    return common_stocks
```

---

## 5. 구현 가이드

### 5.1 Phase 1: VCP Scanner 필터링 개선 (즉시 적용 가능)

**파일**: `services/vcp_scanner/vcp_analyzer.py`

```python
def fetch_stocks() -> List[tuple]:
    """동기 DB 작업을 스레드에서 실행"""
    session = SessionLocal()
    try:
        query = select(Stock)

        # ✅ 개선: market 필드로 직접 필터링
        # KOSPI, KOSDAQ 일반주식만 포함
        query = query.where(Stock.market.in_(["KOSPI", "KOSDAQ"]))

        # 관리종목 추가 제외 (선택사항)
        query = query.where(
            or_(
                Stock.is_admin == False,
                Stock.is_admin.is_(None),
            )
        )

        result = session.execute(query)
        stocks = result.scalars().all()
        return [(s.ticker, s.name) for s in stocks]
    finally:
        session.close()
```

### 5.2 Phase 2: 종목 동기화 개선 (중기)

**파일**: `src/kiwoom/rest_api.py`의 종목 동기화 로직

```python
async def get_stock_list(self, market: str = "KOSPI") -> List[Dict]:
    """
    종목 목록 조회 (일반주식만)

    Args:
        market: "KOSPI" 또는 "KOSDAQ"
    """
    # Kiwoom API 호출
    params = {"market": market}
    stocks = await self._call_api("get_stock_list", params)

    # Kiwoom API 응답에서 marketCode 확인
    common_stocks = []
    for stock in stocks:
        market_code = stock.get("marketCode", "")

        # 일반주식만 필터링 (코스피=0, 코스닥=10)
        if market_code in ["0", "10"]:
            common_stocks.append({
                "ticker": stock["code"].zfill(6),
                "name": stock["name"],
                "market": market,  # KOSPI or KOSDAQ
                "sector": "",
                "market_cap": 0,
                # 불리언 필드들은 기본값 사용
                "is_spac": False,
                "is_bond": False,
                "is_excluded_etf": False,
                "is_admin": False,
            })

    logger.info(f"조회된 {market} 일반주식: {len(common_stocks)}개")
    return common_stocks
```

### 5.3 Phase 3: Kiwoom API mrkt_tp 활용 (장기)

**파일**: `src/kiwoom/rest_api.py`에 fn_ka10099 API 직접 호출

```python
async def get_common_stocks_only(self) -> List[Dict]:
    """
    fn_ka10099 API를 사용하여 일반주식만 조회

    Returns:
        KOSPI, KOSDAQ 일반주식 종목 리스트
    """
    # KOSPI 조회
    kospi_params = {"mrkt_tp": "0"}
    kospi_stocks = await self._call_ka10099(kospi_params)

    # KOSDAQ 조회
    kosdaq_params = {"mrkt_tp": "10"}
    kosdaq_stocks = await self._call_ka10099(kosdaq_params)

    # 결과 합치기
    all_common_stocks = []
    for stock_list in [kospi_stocks, kosdaq_stocks]:
        if 'list' in stock_list:
            for stock in stock_list['list']:
                # marketCode 검증 (이중 확인)
                if stock['marketCode'] in ['0', '10']:
                    all_common_stocks.append({
                        "ticker": stock["code"].zfill(6),
                        "name": stock["name"],
                        "market": "KOSPI" if stock['marketCode'] == '0' else "KOSDAQ",
                        # ... 기타 필드
                    })

    return all_common_stocks
```

---

## 6. 롤백 계획

| 변경 사항 | 롤백 방법 |
|----------|----------|
| VCP Scanner 필터링 | `git checkout HEAD~1 services/vcp_scanner/vcp_analyzer.py` |
| 종목 동기화 로직 | `git checkout HEAD~1 src/kiwoom/rest_api.py` |
| DB 스키마 변경 | `ALTER TABLE stocks ALTER COLUMN ...` |

---

## 7. 테스트 시나리오

### 7.1 단위 테스트

| 케이스 | 입력 | 예상 결과 |
|--------|------|----------|
| 코스피만 스캔 | market="KOSPI" | KOSPI 일반주식만 스캔 |
| 코스닥만 스캔 | market="KOSDAQ" | KOSDAQ 일반주식만 스캔 |
| 전체 스캔 | market="ALL" | KOSPI + KOSDAQ 일반주식만 스캔 |
| ETF 필터링 | ETF 포함 종목 | 시그널 목록에서 제외 |
| ELW 필터링 | ELW 포함 종목 | 시그널 목록에서 제외 |

### 7.2 통합 테스트

```python
# 테스트: 일반주식만 필터링 확인
async def test_common_stock_filtering():
    scanner = VCPAnalyzer()

    # KOSPI 스캔
    kospi_results = await scanner.scan_market("KOSPI", top_n=100)
    # 모든 결과의 종목이 KOSPI market 또는 일반주식인지 확인
    for r in kospi_results:
        assert r.ticker.startswith("0")  # KOSPI는 0으로 시작

    # KOSDAQ 스캔
    kosdaq_results = await scanner.scan_market("KOSDAQ", top_n=100)
    for r in kosdaq_results:
        assert not r.ticker.startswith("0")  # KOSDAQ는 0으로 시작 안 함
```

---

## 8. 요약

### 8.1 현재 문제

1. VCP Scanner가 `is_excluded_etf` 필드로 필터링하지만, 이 필드가 정확히 설정되지 않을 수 있음
2. Kiwoom API는 `marketCode`를 제공하지만 종목 동기화 시 이를 완전히 활용하지 않음
3. 종목명 패턴 매칭으로 ETF/ETN을 식별하는 로직은 오류 가능성이 높음

### 8.2 개선 방안 비교

| 방안 | 장점 | 단점 | 추천 |
|------|------|------|------|
| **A: market 필드 직접 필터링** | 구현 간단, 신뢰성 높음 | Kiwoom API 의존 | ✅ **추천** |
| **B: marketCode 활용 강화** | 정확한 분류 가능 | API 호출 추가 필요 | ⚠️ 선택 |
| **C: fn_ka10099 직접 호출** | 가장 정확 | 구현 복잡, API 호출 증가 | ⚠️ 선택 |

### 8.3 최종 권장 사항

1. **즉시 적용**: VCP Scanner에서 `market.in_(["KOSPI", "KOSDAQ"])`로 필터링
2. **중기 개선**: 종목 동기화 시 Kiwoom API `marketCode`를 DB `market` 필드에 정확히 저장
3. **장기 고려**: fn_ka10099 API를 직접 호출하여 일반주식만 동기화

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
