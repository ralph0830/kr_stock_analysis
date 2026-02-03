# 백엔드 ELW 필터 삭제 보고서

**작성 일자**: 2026-02-03
**대상 파일**: `services/api_gateway/main.py`, `services/api_gateway/schemas.py`
**작성자**: Claude Code QA

---

## 1. 개요

### 1.1 문제 정의

현재 백엔드 코드는 **"알파벳이 포함된 6자리 코드 = ELW"**라는 부정확한 필터 조건을 사용하고 있습니다. 이 조건은 실제 ELW 종목 분류와 일치하지 않으므로 삭제가 필요합니다.

### 1.2 영향 범위

| 파일 | 라인 | 영향 |
|------|------|------|
| `services/api_gateway/main.py` | 1167-1175 | `_is_elw_ticker()` 함수 |
| `services/api_gateway/main.py` | 1177-1178 | `is_elw`, `ticker_category` 변수 |
| `services/api_gateway/main.py` | 1190-1191 | 응답 객체에 필드 전달 |
| `services/api_gateway/schemas.py` | 143-144 | `is_elw`, `ticker_category` 필드 정의 |

---

## 2. 현재 코드 분석

### 2.1 `_is_elw_ticker()` 함수 (`main.py` 라인 1167-1175)

```python
def _is_elw_ticker(ticker_code: str) -> bool:
    """ELW 종목 코드 여부 확인 (숫자+알파벳 조합)"""
    if not ticker_code or len(ticker_code) != 6:
        return False
    # 전체 숫자이면 통과 (KOSPI/KOSDAQ 일반 종목)
    if ticker_code.isdigit():
        return False
    # 알파벳이 포함되면 ELW
    return any(c.isalpha() for c in ticker_code)
```

**문제점**:
- 알파벳 포함 여부만으로 ELW를 판단하는 것은 부정확함
- 실제 ELW는 종목 분류 체계에 따라 결정되어야 함

### 2.2 ELW 변수 사용 (`main.py` 라인 1177-1193)

```python
is_elw = _is_elw_ticker(ticker)
ticker_category = "elw" if is_elw else "stock"

# 응답 생성
return StockDetailResponse(
    ticker=stock.ticker,
    name=stock.name,
    market=stock.market,
    sector=stock.sector,
    current_price=latest_price.close_price if latest_price else None,
    price_change=None,  # TODO: Calculate from previous day
    price_change_pct=None,  # TODO: Calculate from previous day
    volume=latest_price.volume if latest_price else None,
    is_elw=is_elw,              # ← 응답에 포함
    ticker_category=ticker_category,  # ← 응답에 포함
    updated_at=latest_price.date if latest_price else None,
)
```

**문제점**:
- API 응답에 부정확한 ELW 정보를 포함
- 프론트엔드가 이 정보를 사용하여 ELW 관련 로직을 수행

### 2.3 Schema 정의 (`schemas.py` 라인 143-144)

```python
class StockDetailResponse(BaseModel):
    ticker: str
    name: str
    market: Optional[str] = None
    sector: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    is_elw: bool = False  # ELW(상장지수증권) 여부
    ticker_category: str = "stock"  # stock, elw (프론트엔드 분류용)
    updated_at: Optional[datetime] = None
```

**문제점**:
- `is_elw`와 `ticker_category` 필드가 불필요함
- ELW 판별 로직이 부정확함

---

## 3. 삭제 방안

### 3.1 Schema 수정 (`schemas.py`)

**대상**: 라인 138-145

**변경 전**:
```python
class StockDetailResponse(BaseModel):
    ticker: str
    name: str
    market: Optional[str] = None
    sector: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    is_elw: bool = False  # ELW(상장지수증권) 여부
    ticker_category: str = "stock"  # stock, elw (프론트엔드 분류용)
    updated_at: Optional[datetime] = None
```

**변경 후**:
```python
class StockDetailResponse(BaseModel):
    ticker: str
    name: str
    market: Optional[str] = None
    sector: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    updated_at: Optional[datetime] = None
```

### 3.2 `_is_elw_ticker()` 함수 삭제 (`main.py`)

**대상**: 라인 1167-1175

```python
# === 삭제 전체 ===
def _is_elw_ticker(ticker_code: str) -> bool:
    """ELW 종목 코드 여부 확인 (숫자+알파벳 조합)"""
    if not ticker_code or len(ticker_code) != 6:
        return False
    # 전체 숫자이면 통과 (KOSPI/KOSDAQ 일반 종목)
    if ticker_code.isdigit():
        return False
    # 알파벳이 포함되면 ELW
    return any(c.isalpha() for c in ticker_code)
```

### 3.3 ELW 변수 삭제 및 응답 수정 (`main.py`)

**대상**: 라인 1167-1193 (전체 엔드포인트 함수)

**변경 전**:
```python
@app.get(
    "/api/kr/stocks/{ticker}",
    tags=["signals"],
    response_model=StockDetailResponse,
    # ...
)
async def get_kr_stock_detail(ticker: str, db: Session = Depends(get_db_session_sync)):
    # ... 주식 조회 로직 ...

    # ELW 여부 계산 (6자리 코드 중 알파벳이 포함되면 ELW)
    def _is_elw_ticker(ticker_code: str) -> bool:
        """ELW 종목 코드 여부 확인 (숫자+알파벳 조합)"""
        if not ticker_code or len(ticker_code) != 6:
            return False
        # 전체 숫자이면 통과 (KOSPI/KOSDAQ 일반 종목)
        if ticker_code.isdigit():
            return False
        # 알파벳이 포함되면 ELW
        return any(c.isalpha() for c in ticker_code)

    is_elw = _is_elw_ticker(ticker)
    ticker_category = "elw" if is_elw else "stock"

    # 응답 생성
    return StockDetailResponse(
        ticker=stock.ticker,
        name=stock.name,
        market=stock.market,
        sector=stock.sector,
        current_price=latest_price.close_price if latest_price else None,
        price_change=None,  # TODO: Calculate from previous day
        price_change_pct=None,  # TODO: Calculate from previous day
        volume=latest_price.volume if latest_price else None,
        is_elw=is_elw,
        ticker_category=ticker_category,
        updated_at=latest_price.date if latest_price else None,
    )
```

**변경 후**:
```python
@app.get(
    "/api/kr/stocks/{ticker}",
    tags=["signals"],
    response_model=StockDetailResponse,
    # ...
)
async def get_kr_stock_detail(ticker: str, db: Session = Depends(get_db_session_sync)):
    # ... 주식 조회 로직 ...

    # 응답 생성 (ELW 필드 제거)
    return StockDetailResponse(
        ticker=stock.ticker,
        name=stock.name,
        market=stock.market,
        sector=stock.sector,
        current_price=latest_price.close_price if latest_price else None,
        price_change=None,  # TODO: Calculate from previous day
        price_change_pct=None,  # TODO: Calculate from previous day
        volume=latest_price.volume if latest_price else None,
        updated_at=latest_price.date if latest_price else None,
    )
```

---

## 4. 영향도 분석

### 4.1 API 응답 변경

| 필드 | 변경 전 | 변경 후 |
|------|----------|---------|
| `is_elw` | `true`/`false` | **삭제됨** |
| `ticker_category` | `"stock"`/`"elw"` | **삭제됨** |

### 4.2 엔드포인트 영향

| 엔드포인트 | 영향 |
|-----------|------|
| `GET /api/kr/stocks/{ticker}` | 응답에서 `is_elw`, `ticker_category` 필드 제거 |

### 4.3 프론트엔드 영향

| 항목 | 현재 | 변경 후 |
|------|------|---------|
| API 응답 사용 | `is_elw`, `ticker_category` 참조 | 필드 없음 (무시) |
| ELW 판별 | 백엔드 응답 의존 가능성 | 프론트엔드 자체 판별 (삭제 예정) |

---

## 5. 관련 코드 검토

### 5.1 다른 파일에서의 ELW 관련 코드

#### `src/collectors/news_collector.py`

```python
# 뉴스 수집기의 ELW 처리 로직 검토 필요
```

#### `services/chatbot/ticker_parser.py`

```python
# 챗봇 티커 파서의 ELW 처리 로직 검토 필요
```

**확인 필요**: 이 파일들도 ELW 판별 로직을 사용하는지 확인 후 필요시 수정

---

## 6. 수정 후 전체 코드

### 6.1 Schema (`schemas.py`)

```python
class StockDetailResponse(BaseModel):
    """한국 주식 상세 정보 응답"""
    ticker: str
    name: str
    market: Optional[str] = None  # KOSPI, KOSDAQ
    sector: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    updated_at: Optional[datetime] = None
```

### 6.2 엔드포인트 (`main.py`)

```python
@app.get(
    "/api/kr/stocks/{ticker}",
    tags=["signals"],
    response_model=StockDetailResponse,
    responses={
        200: {"description": "주식 상세 정보 반환"},
        404: {"description": "종목 찾기 실패"},
    },
)
async def get_kr_stock_detail(
    ticker: str,
    db: Session = Depends(get_db_session_sync),
) -> StockDetailResponse:
    """
    한국 주식 상세 정보 조회

    Args:
        ticker: 종목코드 (6자리)
        db: 데이터베이스 세션

    Returns:
        StockDetailResponse: 주식 상세 정보
    """
    # 주식 정보 조회
    stock = db.execute(
        select(Stock)
        .where(Stock.ticker == ticker)
    ).scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    # 최신 가격 정보 조회
    latest_price = db.execute(
        select(DailyPrice)
        .where(DailyPrice.ticker == ticker)
        .order_by(desc(DailyPrice.date))
        .limit(1)
    ).scalar_one_or_none()

    # 응답 생성
    return StockDetailResponse(
        ticker=stock.ticker,
        name=stock.name,
        market=stock.market,
        sector=stock.sector,
        current_price=latest_price.close_price if latest_price else None,
        price_change=None,  # TODO: Calculate from previous day
        price_change_pct=None,  # TODO: Calculate from previous day
        volume=latest_price.volume if latest_price else None,
        updated_at=latest_price.date if latest_price else None,
    )
```

---

## 7. 테스트 시나리오

### 7.1 API 테스트 케이스

| 케이스 | 종목 코드 | 예상 응답 |
|--------|----------|----------|
| TC-01 | 0015N0 | `is_elw` 필드 없음 |
| TC-02 | 0004V0 | `is_elw` 필드 없음 |
| TC-03 | 0120X0 | `is_elw` 필드 없음 |
| TC-04 | 005930 | `is_elw` 필드 없음 |
| TC-05 | 000660 | `is_elw` 필드 없음 |

### 7.2 검증 항목

1. [ ] API 응답에 `is_elw` 필드가 없음
2. [ ] API 응답에 `ticker_category` 필드가 없음
3. [ ] 다른 필드들은 정상적으로 반환됨
4. [ ] 200 상태 코드로 정상 응답

---

## 8. 롤백 계획

### 8.1 롤백 시나리오

만약 ELW 필드 삭제 후 문제가 발생할 경우:

1. **Schema 복원**: `is_elw`, `ticker_category` 필드 다시 추가
2. **함수 복원**: `_is_elw_ticker()` 함수 다시 추가
3. **응답 복원**: `is_elw`, `ticker_category` 값을 다시 전달

### 8.2 롤백 명령어

```bash
# Git으로 롤백
git checkout HEAD~1 services/api_gateway/main.py services/api_gateway/schemas.py

# 또는 수동으로 복원 후
docker compose restart api-gateway
```

---

## 9. 배포 계획

### 9.1 변경 순서

1. **백엔드 변경 우선**:
   - `schemas.py` 수정
   - `main.py` 수정
   - 컨테이너 재시작

2. **프론트엔드 변경 추후**:
   - `RealtimePriceCard.tsx` 수정
   - 빌드 및 배포

### 9.2 배포 후 확인

```bash
# API 응답 확인
curl http://localhost:5111/api/kr/stocks/0015N0 | jq .

# 예상 응답 (is_elw, ticker_category 없음)
{
  "ticker": "0015N0",
  "name": "아로마티카",
  "market": "KOSDAQ",
  "current_price": 9580.0,
  ...
}
```

---

## 10. 요약

### 10.1 삭제 항목

1. `schemas.py`: `is_elw`, `ticker_category` 필드
2. `main.py`: `_is_elw_ticker()` 함수
3. `main.py`: `is_elw`, `ticker_category` 변수 및 응답 전달

### 10.2 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `services/api_gateway/schemas.py` | 필드 2개 삭제 |
| `services/api_gateway/main.py` | 함수 삭제, 변수 삭제, 응답 수정 |

### 10.3 예상 효과

- 부정확한 ELW 판별 로직 제거
- API 응답 간소화
- 프론트엔드에서 자체 ELW 판별 의존 제거

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
