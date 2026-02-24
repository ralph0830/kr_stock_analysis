# Kiwoom REST API 리팩토링 제안 보고서

**분석 일시:** 2026-02-06
**대상 파일:** `/home/ralph/work/python/kr_stock_analysis/src/kiwoom/rest_api.py`
**현재 라인 수:** 1,623줄

---

## 1. 요약

| 항목 | 현재 | 리팩토링 후 | 개선폭 |
|------|------|-------------|--------|
| 전체 라인 수 | 1,623줄 | ~1,150줄 | **-29%** |
| 중복 코드 | ~350줄 | ~50줄 | **-85%** |
| API 호출 패턴 | 14개 메서드 | 1개 헬퍼 | **-93%** |

---

## 2. 발견된 중복 패턴

### 2.1 헤더 생성 중복 (8개 위치)

모든 API 메서드에서 동일한 헤더 생성 코드가 반복됨:

```python
# 8개 메서드에서 반복
headers = {
    "Authorization": f"Bearer {self._access_token}",
    "api-id": "ka10001",  # 또는 ka10060, ka10081, ka20006 등
    "Content-Type": "application/json;charset=UTF-8",
    "cont-yn": "N",
    "next-key": "",
}
```

**발생 위치:**
- `get_current_price()` (434-437줄)
- `get_investor_chart()` (515-523줄)
- `get_index_price()` (954-960줄)
- `get_stock_daily_chart()` (1053-1059줄)
- `get_index_daily_chart()` (1148-1152줄)
- `get_daily_trade_detail()` (1472-1476줄)
- `get_sector_daily_chart()` (1567-1571줄)
- `get_stock_list()` (1313-1320줄)

### 2.2 API 호출 및 응답 검증 중복

```python
# 14개 메서드에서 반복
await self.ensure_token_valid()
client = await self._get_client()
response = await client.post(url, json=request_data, headers=headers)
response.raise_for_status()
result = response.json()

# return_code 확인
return_code = result.get("return_code", -1)
if return_code != 0:
    logger.warning(f"API returned code {return_code}: {result.get('return_msg')}")
    return None
```

### 2.3 JSON-RPC 2.0 요청 중복 (4개 위치)

```python
request_data = {
    "jsonrpc": "2.0",
    "method": "t0414",  # 또는 t1102, t0424, t0425
    "params": {
        "t0414InBlock": { ... }
    },
    "id": 1,
}
```

**발생 위치:**
- `get_current_price()`
- `_place_order()`
- `get_account_balance()`
- `get_account_deposit()`

### 2.4 에러 처리 중복

```python
except HTTPStatusError as e:
    logger.error(f"... failed: {e.response.status_code}")
    return None
except Exception as e:
    logger.error(f"... error: {e}")
    return None
```

### 2.5 차트 데이터 파싱 중복 (4개 메서드)

| 메서드 | API ID | 응답 필드 | 파싱 로직 |
|--------|--------|-----------|----------|
| `get_stock_daily_chart()` | ka10081 | `stk_dt_pole_chart_qry` | OHLCV 파싱 |
| `get_index_daily_chart()` | ka10081 | `dtal_1` | OHLCV 파싱 |
| `get_sector_daily_chart()` | ka20006 | `inds_dt_pole_qry` | OHLCV 파싱 |
| `get_daily_prices()` | ka10060 | `stk_invsr_orgn_chart` | 가격 파싱 |

---

## 3. 리팩토링 제안

### 3.1 Phase 1: 헬퍼 메서드 추출 (저위험, 즉시 실행)

#### 1) API 헤더 생성 헬퍼

```python
def _build_headers(
    self,
    api_id: str,
    cont_yn: str = "N",
    next_key: str = ""
) -> Dict[str, str]:
    """
    API 요청 헤더 생성

    Args:
        api_id: Kiwoom API ID (예: ka10001, ka10081)
        cont_yn: 연속조회 여부
        next_key: 연속조회 키

    Returns:
        요청 헤더 딕셔너리
    """
    headers = {
        "Authorization": f"Bearer {self._access_token}",
        "api-id": api_id,
        "Content-Type": "application/json;charset=UTF-8",
    }
    if cont_yn == "Y" and next_key:
        headers["cont-yn"] = "Y"
        headers["next-key"] = next_key
    return headers
```

**적용 예시:**
```python
# 기존
headers = {
    "Authorization": f"Bearer {self._access_token}",
    "api-id": "ka10081",
    "Content-Type": "application/json;charset=UTF-8",
}

# 리팩토링 후
headers = self._build_headers("ka10081")
```

#### 2) JSON-RPC 요청 헬퍼

```python
def _build_jsonrpc_request(
    self,
    method: str,
    in_block: Dict[str, Any]
) -> Dict[str, Any]:
    """
    JSON-RPC 2.0 요청 생성

    Args:
        method: TR 코드 (예: t0414, t1102)
        in_block: InBlock 데이터

    Returns:
        JSON-RPC 2.0 요청 딕셔너리
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": {
            f"{method}InBlock": in_block
        },
        "id": 1,
    }
```

#### 3) 통합 API 호출 헬퍼

```python
async def _call_kiwoom_api(
    self,
    api_id: str,
    endpoint: str,
    request_data: Dict[str, Any],
    result_key: Optional[str] = None,
    cont_yn: str = "N",
    next_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Kiwoom API 통합 호출 메서드

    Args:
        api_id: API ID (예: ka10081)
        endpoint: 엔드포인트 경로
        request_data: 요청 데이터
        result_key: 응답 데이터 키 (None이면 전체 반환)
        cont_yn: 연속조회 여부
        next_key: 연속조회 키

    Returns:
        API 응답 데이터 또는 None
    """
    try:
        await self.ensure_token_valid()
        client = await self._get_client()

        headers = self._build_headers(api_id, cont_yn, next_key)
        url = f"{self._config.base_url}{endpoint}"

        response = await client.post(url, json=request_data, headers=headers)
        response.raise_for_status()
        result = response.json()

        # return_code 검증
        return_code = result.get("return_code", -1)
        if return_code != 0:
            logger.warning(f"API {api_id} returned code {return_code}: {result.get('return_msg')}")
            return None

        return result.get(result_key, result) if result_key else result

    except HTTPStatusError as e:
        logger.error(f"API {api_id} HTTP error: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"API {api_id} error: {e}")
        return None
```

#### 4) OHLCV 차트 파싱 헬퍼

```python
def _parse_ohlc_item(
    self,
    item: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    차트 아이템을 표준 OHLCV 형식으로 변환

    Args:
        item: API 응답 아이템
        field_mapping: 필드명 매핑 (기본값: 주식용)

    Returns:
        표준화된 OHLCV 데이터
    """
    # 기본 필드 매핑 (주식)
    mapping = {
        "date": "dt",
        "open": "open_pric",
        "high": "high_pric",
        "low": "low_pric",
        "close": "cur_prc",
        "volume": "trde_qty",
    }

    if field_mapping:
        mapping.update(field_mapping)

    def safe_get(key: str, default=0, converter=float):
        val = item.get(mapping.get(key, key), "")
        if val == "" or val is None:
            return default
        try:
            return converter(val)
        except (ValueError, TypeError):
            return default

    return {
        "date": item.get(mapping["date"], ""),
        "open": safe_get("open", 0.0),
        "high": safe_get("high", 0.0),
        "low": safe_get("low", 0.0),
        "close": safe_get("close", 0.0),
        "volume": safe_get("volume", 0, converter=int),
    }
```

### 3.2 Phase 2: 차트 조회 메서드 통합 (중간 난이도)

#### 통합 차트 조회 메서드

```python
async def _get_chart_data(
    self,
    code: str,
    api_id: str,
    base_date: Optional[str] = None,
    days: int = 20,
    code_type: str = "stock",  # stock, index, sector
    result_key: str = "stk_dt_pole_chart_qry",
) -> Optional[List[Dict[str, Any]]]:
    """
    통합 차트 데이터 조회

    Args:
        code: 종목/지수/업종 코드
        api_id: API ID
        base_date: 기준일자
        days: 조회 일수
        code_type: 코드 타입
        result_key: 응답 데이터 키

    Returns:
        차트 데이터 리스트
    """
    from datetime import datetime

    if base_date is None:
        base_date = datetime.now().strftime("%Y%m%d")

    # 요청 데이터 구성
    if code_type == "stock":
        request_data = {
            "stk_cd": code,
            "base_dt": base_date,
            "upd_stkpc_tp": "1",  # 수정주가
        }
    elif code_type == "index":
        request_data = {
            "stk_cd": code,
            "inq_strt_dt": (datetime.now() - timedelta(days=days*2)).strftime("%Y%m%d"),
            "inq_end_dt": base_date,
            "data_tp": "01",
            "isu_cd_tp": "02",  # 지수
        }
    else:  # sector
        request_data = {
            "inds_cd": code,
            "base_dt": base_date,
        }

    # API 호출
    endpoint = "/api/dostk/ka10081" if code_type in ["stock", "index"] else "/api/dostk/chart"
    result = await self._call_kiwoom_api(api_id, endpoint, request_data, result_key)

    if not result:
        return []

    # 파싱
    parsed = [self._parse_ohlc_item(item) for item in result]
    return parsed[-days:] if len(parsed) > days else parsed
```

**사용 예시:**
```python
# 기존 3개 메서드를 하나로 통합
async def get_stock_daily_chart(self, ticker: str, days: int = 60):
    return await self._get_chart_data(
        ticker, "ka10081", days=days, code_type="stock",
        result_key="stk_dt_pole_chart_qry"
    )

async def get_index_daily_chart(self, index_code: str, days: int = 5):
    return await self._get_chart_data(
        index_code, "ka10081", days=days, code_type="index",
        result_key="dtal_1"
    )

async def get_sector_daily_chart(self, sector_code: str, days: int = 20):
    return await self._get_chart_data(
        sector_code, "ka20006", days=days, code_type="sector",
        result_key="inds_dt_pole_qry"
    )
```

### 3.3 Phase 3: Configuration-Driven 아키텍처 (고난이도, 선택사항)

```python
@dataclass
class APISpec:
    """API 사양 정의"""
    api_id: str
    endpoint: str
    result_key: str
    request_builder: Callable[[str, Any], Dict]
    response_parser: Callable[[Dict], Any]

# API 레지스트리
_CHART_APIS = {
    "stock": APISpec(
        api_id="ka10081",
        endpoint="/api/dostk/chart",
        result_key="stk_dt_pole_chart_qry",
        request_builder=lambda code, date: {"stk_cd": code, "base_dt": date, "upd_stkpc_tp": "1"},
        response_parser=lambda data: [_parse_ohlc_item(item) for item in data],
    ),
    "index": APISpec(
        api_id="ka10081",
        endpoint="/api/dostk/ka10081",
        result_key="dtal_1",
        request_builder=lambda code, date: {"stk_cd": code, "inq_strt_dt": date, "isu_cd_tp": "02"},
        response_parser=lambda data: [_parse_ohlc_item(item, INDEX_FIELD_MAPPING) for item in data],
    ),
    # ...
}

async def get_chart(self, chart_type: str, code: str, **kwargs) -> Optional[List[Dict]]:
    """범용 차트 조회"""
    spec = _CHART_APIS.get(chart_type)
    if not spec:
        raise ValueError(f"Unknown chart type: {chart_type}")

    request_data = spec.request_builder(code, kwargs.get("base_date"))
    result = await self._call_kiwoom_api(spec.api_id, spec.endpoint, request_data, spec.result_key)

    return spec.response_parser(result) if result else []
```

---

## 4. 리팩토링 우선순위

### P0 (즉시 실행) - 헬퍼 메서드 추출

| 헬퍼 메서드 | 영향 메서드 수 | 코드 감소 | 위험도 |
|-------------|---------------|-----------|--------|
| `_build_headers()` | 8개 | ~40줄 | 낮음 |
| `_build_jsonrpc_request()` | 4개 | ~20줄 | 낮음 |
| `_parse_ohlc_item()` | 4개 | ~30줄 | 낮음 |
| `_call_kiwoom_api()` | 14개 | ~100줄 | 중간 |

**합계:** ~190줄 감소, 낮은 위험으로 빠른 개선 가능

### P1 (단기) - 차트 조회 통합

| 작업 | 영향 메서드 | 코드 감소 |
|------|-------------|-----------|
| `_get_chart_data()` 통합 메서드 | 3개 | ~80줄 |

### P2 (중기) - 지수 조회 통합

| 작업 | 영향 메서드 | 코드 감소 |
|------|-------------|-----------|
| 지수 관련 메서드 통합 | 3개 | ~60줄 |

---

## 5. 중복 함수 정리

### 제안할 병합

| 원본 함수 1 | 원본 함수 2 | 원본 함수 3 | 통합 함수명 |
|-------------|-------------|-------------|-------------|
| `get_stock_daily_chart()` | `get_index_daily_chart()` | `get_sector_daily_chart()` | `_get_chart_data()` |
| `get_index_price()` | `get_index_price_from_chart()` | - | `get_index_price()` (하나로 통합) |
| `is_token_valid()` | `has_valid_token()` | `is_connected()` | `is_token_valid()` (중복 제거) |

### 제안할 삭제

| 함수 | 삭제 사유 | 대안 |
|------|----------|------|
| `has_valid_token()` | `is_token_valid()`과 중복 | `is_token_valid()`만 사용 |
| `is_connected()` | `is_token_valid()`과 중복 | `is_token_valid()`만 사용 |
| `get_daily_prices()` | `get_stock_daily_chart()`로 대체 가능 | `get_stock_daily_chart()` 사용 |
| `get_investor_chart()` | `get_daily_trade_detail()`로 대체 가능 | `get_daily_trade_detail()` 사용 |

---

## 6. 최종 제안 리팩토링 코드 구조

```python
# 리팩토링后的 구조 (제안)

class KiwoomRestAPI:
    """
    키움 REST API 클라이언트 (리팩토링 버전)
    """

    # ========== 상수 ==========
    TOKEN_URL = "/oauth2/token"

    # ========== 헬퍼 메서드 ==========
    def _build_headers(self, api_id: str, cont_yn: str = "N", next_key: str = "") -> Dict:
        """API 요청 헤더 생성"""

    def _build_jsonrpc_request(self, method: str, in_block: Dict) -> Dict:
        """JSON-RPC 요청 생성"""

    def _parse_ohlc_item(self, item: Dict, field_mapping: Optional[Dict] = None) -> Dict:
        """OHLCV 아이템 파싱"""

    async def _call_kiwoom_api(self, api_id: str, endpoint: str,
                             request_data: Dict, result_key: Optional[str] = None,
                             cont_yn: str = "N", next_key: str = "") -> Optional[Dict]:
        """통합 API 호출"""

    def _get_chart_data(self, code: str, api_id: str, base_date: str,
                       days: int, code_type: str, result_key: str) -> Optional[List]:
        """통합 차트 조회"""

    # ========== 토큰 관리 ==========
    async def issue_token(self) -> bool:
        """토큰 발급"""

    async def ensure_token_valid(self) -> None:
        """유효한 토큰 보장"""

    def is_token_valid(self) -> bool:
        """토큰 유효성 확인"""

    # ========== 공개 API (토큰 불필요) ==========
    async def get_current_price(self, ticker: str) -> Optional[RealtimePrice]:
        """현재가 조회 (ka10001)"""

    async def get_stock_daily_chart(self, ticker: str, days: int = 60) -> Optional[List]:
        """주식 일봉 차트 (ka10081)"""

    async def get_index_daily_chart(self, index_code: str, days: int = 5) -> Optional[List]:
        """지수 일봉 차트 (ka10081)"""

    async def get_sector_daily_chart(self, sector_code: str, days: int = 20) -> Optional[List]:
        """업종 일봉 차트 (ka20006)"""

    async def get_daily_trade_detail(self, ticker: str, start_date: str) -> Optional[List]:
        """일별거래상세 조회 (ka10015)"""

    async def get_stock_list(self, market: str = "ALL") -> List:
        """종목정보 리스트 조회 (ka10099)"""

    # ========== 인증 API (토큰 필요) ==========
    async def order_buy_market(self, ticker: str, quantity: int) -> Optional[Dict]:
        """시장가 매수"""

    async def order_sell_market(self, ticker: str, quantity: int) -> Optional[Dict]:
        """시장가 매도"""

    async def get_account_balance(self) -> Optional[List]:
        """계좌 잔고 조회"""

    async def get_account_deposit(self) -> Optional[Dict]:
        """예수금 조회"""

    # ========== 연결 관리 ==========
    async def connect(self) -> bool:
        """API 연결"""

    async def close(self) -> None:
        """연결 종료"""
```

---

## 7. 검증 체크리스트

리팩토링 전후 검증 항목:

- [ ] 헬퍼 메서드 추가 (`_build_headers`, `_parse_ohlc_item`, `_call_kiwoom_api`)
- [ ] 기존 메서드들이 헬퍼를 사용하도록 수정
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] API 호출 결과 동일성 확인
- [ ] 성능 저하 없음 확인

---

## 8. 결론

### 핵심 발견

1. **헤더 생성 코드가 8개 위치에서 중복** → `_build_headers()` 헬퍼로 통합
2. **API 호출 패턴이 14개 메서드에서 반복** → `_call_kiwoom_api()` 헬퍼로 통합
3. **차트 파싱 로직이 4개 메서드에서 중복** → `_parse_ohlc_item()` 헬퍼로 통합
4. **일부 함수가 서로 대체 가능** → `get_daily_prices()`, `get_investor_chart()` 삭제 가능

### 리팩토링 효과

| 항목 | 개선폭 |
|------|--------|
| 코드 라인 | -29% (1,623줄 → 1,150줄) |
| 중복 코드 | -85% (350줄 → 50줄) |
| 유지보수성 | 대폭 개선 (헬퍼 메서드 중앙화) |
| 테스트 용이성 | 개선 (헬퍼 메서드 단위 테스트) |

### 실행 제안

1. **Phase 1 (1-2시간):** 헬퍼 메서드 추가 및 기존 메서드 수정
2. **Phase 2 (2-3시간):** 차트 조회 메서드 통합
3. **Phase 3 (선택):** Configuration-Driven 아키텍처 (필요시)

---

**작성자:** Claude Code (Refactoring Specialist)
**문서 경로:** `/home/ralph/work/python/kr_stock_analysis/docs/report/kiwoom_rest_api_refactoring_proposal.md`
