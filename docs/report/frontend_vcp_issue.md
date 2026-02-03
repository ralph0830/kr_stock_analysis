# VCP 시그널 로직 QA 분석 보고서

**분석 일자:** 2026-02-02
**분석 대상:** https://stock.ralphpark.com
**분석 범위:** VCP 시그널 생성 로직, 프론트엔드 표시, 백엔드 API

---

## 1. 결론 요약

### 핵심 발견

**전 종목 스캔 로직은 올바르게 구현되어 있습니다.**

- ✅ KOSPI/KOSDAQ 전 종목 대상 스캔
- ✅ 관리종목 제외 로직
- ✅ 병렬 비동기 분석 (세마포어 동시 제어)

**하지만 데이터 연동에 심각한 문제가 있습니다.**

- ❌ 외국인/기관 수급 데이터가 **하드코딩된 0**으로 저장됨
- ❌ VCP 수축률(contraction_ratio)이 `null`로 표시됨
- ❌ 실제 SmartMoney 점수가 시그널에 반영되지 않음

---

## 2. 실제 사이트 데이터 검증

### 2.1 프론트엔드 표시 데이터

**URL:** `https://stock.ralphpark.com` (메인 페이지)

| 티커 | 종목명 | 등급 | 점수 | 수축률 | 외국인 5D | 기관 5D |
|------|--------|------|------|--------|----------|--------|
| 005380 | 현대차 | B | 55.5 | - | 0 | 0 |
| 028260 | 삼성물산 | B | 50.3 | - | 0 | 0 |
| 035420 | NAVER | C | 49.8 | - | 0 | 0 |
| 005930 | 삼성전자 | C | 46.0 | - | 0 | 0 |
| 000660 | SK하이닉스 | C | 37.3 | - | 0 | 0 |
| 000020 | 동화약품 | C | 25.0 | - | 0 | 0 |

### 2.2 API 응답 데이터

**엔드포인트:** `GET /api/kr/signals/vcp?limit=20`

```json
{
  "count": 6,
  "generated_at": "2026-02-02T03:21:59.250904",
  "signals": [
    {
      "ticker": "005380",
      "name": "현대차",
      "score": 55.5,
      "grade": "B",
      "contraction_ratio": null,
      "foreign_5d": 0,
      "inst_5d": 0
    },
    ...
  ]
}
```

**문제점:**
- `contraction_ratio: null` - VCP 수축률 데이터 없음
- `foreign_5d: 0` - 외국인 수급 데이터 없음
- `inst_5d: 0` - 기관 수급 데이터 없음

---

## 3. 코드 분석 상세

### 3.1 VCP 스캔 로직 (정상)

**파일:** `services/vcp_scanner/vcp_analyzer.py`

#### 전 종목 조회 로직
```python
# 436-456행: fetch_stocks()
def fetch_stocks() -> List[tuple]:
    """동기 DB 작업을 스레드에서 실행"""
    session = SessionLocal()
    try:
        query = select(Stock)
        # 시장 필터
        if market == "KOSPI":
            query = query.where(Stock.market == "KOSPI")
        elif market == "KOSDAQ":
            query = query.where(Stock.market == "KOSDAQ")
        # ALL인 경우 필터 없이 전체 조회

        # 관리종목 제외
        query = query.where(or_(Stock.is_admin == False, Stock.is_admin.is_(None)))

        result = session.execute(query)
        stocks = result.scalars().all()
        return [(s.ticker, s.name) for s in stocks]
    finally:
        session.close()
```

**✅ 정상 작동:**
- DB의 `stocks` 테이블에서 전체 종목 조회
- `market` 파라미터로 KOSPI/KOSDAQ/ALL 필터링
- 관리종목(`is_admin=True`) 제외

#### 병렬 분석 로직
```python
# 464-474행: analyze_with_semaphore()
semaphore = asyncio.Semaphore(10)  # 최대 10개 동시 분석

async def analyze_with_semaphore(ticker_name: tuple) -> Optional[VCPResult]:
    async with semaphore:
        ticker, name = ticker_name
        return await self.analyze(ticker, name)

# 전체 종목 비동기 분석
tasks = [analyze_with_semaphore(ticker_name) for ticker_name in stock_list]
analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
```

**✅ 정상 작동:**
- 전체 종목 목록을 병렬로 분석
- 세마포어로 최대 10개 동시 분석 제어

---

### 3.2 SmartMoney 점수 계산 (정상)

**파일:** `services/vcp_scanner/vcp_analyzer.py:313-414`

```python
async def _calculate_smartmoney_score(self, ticker: str) -> float:
    """
    SmartMoney 점수 계산 (0-100)
    - 외국인 수급 (40%)
    - 기관 수급 (30%)
    - 수급 종합 점수 (30%)
    """
```

**✅ 정상 작동:**
- `InstitutionalFlow` 테이블에서 수급 데이터 조회
- 외국인/기관 순매수 금액 기반 점수 계산
- 정상적으로 계산된 점수가 `VCPResult`에 포함됨

---

### 3.3 DB 저장 로직 (문제 발생)

**파일:** `services/vcp_scanner/main.py:178-196`

```python
# 새 시그널 저장
for result in results:
    grade = _get_grade_from_score(result.total_score)

    # Signal 레코드 생성
    signal = Signal(
        ticker=result.ticker,
        signal_type="VCP",
        status="OPEN",
        score=result.total_score,
        grade=grade,
        contraction_ratio=result.vcp_score / 100 if result.vcp_score else None,
        signal_date=signal_date,
        entry_price=int(result.current_price) if result.current_price else None,
        foreign_net_5d=0,  # TODO: 수급 데이터 연동  ← 문제!
        inst_net_5d=0,     # ← 문제!
    )
    db.add(signal)
    saved_count += 1
```

**❌ 문제점:**
1. `foreign_net_5d=0` - 하드코딩된 0값
2. `inst_net_5d=0` - 하드코딩된 0값
3. `contraction_ratio=result.vcp_score / 100` - 이것은 VCP score를 100으로 나눈 것이지 실제 수축률이 아님
4. TODO 주석: `# TODO: 수급 데이터 연동` - 구현되지 않음

### 3.4 API Gateway 응답 로직 (문제 발생)

**파일:** `services/api_gateway/routes/triggers.py:236-256`

```python
# VCPSignalItem 형식으로 변환
signal_items = []
for r in results:
    item = VCPSignalItem(
        ticker=r.get("ticker"),
        name=r.get("name"),
        market="KOSPI",  # 기본값
        signal_type="VCP",
        score=r.get("total_score", 0),
        grade=_get_grade_from_score(r.get("total_score", 0)),
        signal_date=analysis_date,
        entry_price=r.get("current_price"),
        target_price=None,
        current_price=r.get("current_price"),
        contraction_ratio=None,  # ← None으로 설정
        foreign_5d=0,            # ← 0으로 설정
        inst_5d=0,               # ← 0으로 설정
        created_at=datetime.utcnow().isoformat(),
    )
    signal_items.append(item.model_dump())
```

**❌ 문제점:**
- API Gateway에서도 하드코딩된 값으로 응답 생성

---

## 4. 자동화 스케줄 분석

**파일:** `tasks/celery_app.py:78-81`

```python
# 테스트용: 30분 간격
"scan-vcp-test": {
    "task": "tasks.sync_tasks.trigger_vcp_scan_via_api",
    "schedule": 30 * 60,  # 30분 간격
},
```

**파일:** `tasks/sync_tasks.py:134-166`

```python
@celery_app.task(name="tasks.sync_tasks.trigger_vcp_scan_via_api")
def trigger_vcp_scan_via_api():
    """VCP 스캔 트리거 태스크 (API Gateway 호출)"""
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{api_url}/api/kr/scan/vcp",
            params={
                "market": "ALL",  # ← 전체 시장 스캔
                "sync_stocks": False,
            },
        )
```

**✅ 정상 작동:**
- 30분 간격으로 자동 실행
- `market: "ALL"` 파라미터로 전체 종목 스캔 요청

---

## 5. 프론트엔드 코드 분석

### 5.1 메인 페이지

**파일:** `frontend/app/page.tsx:15-18, 29-34`

```typescript
const {
    signals,
    loadingSignals,
    fetchSignals,
} = useStore();

// 실시간 가격 모니터링할 종목 목록 (시그널 종목 중 상위 6개)
const realtimeTickers = useMemo(() => {
    return signals.slice(0, 6).map((signal) => ({  // ← 상위 6개만 표시
        ticker: signal.ticker,
        name: signal.name,
    }));
}, [signals]);
```

**✅ 정상 작동:**
- `signals` 배열에서 상위 6개만 표시
- API에서 받은 전체 시그널 중 상위 6개 선택

### 5.2 VCP 페이지

**파일:** `frontend/app/dashboard/kr/vcp/page.tsx:156-157`

```typescript
// VCP 시그널 조회 (상위 10개)
const vcpResponse = await apiClient.getVCPSignals(10);
```

**파일:** `frontend/lib/api-client.ts:174-184`

```typescript
// 활성 VCP 시그널 상위 N개 조회 (상위 10개)
async getVCPSignals(limit: number = 10, market?: string): Promise<{
    signals: Signal[];
    count: number;
    generated_at?: string;
}> {
    const params: any = { limit };
    if (market) params.market = market;
    const response = await api.get("/api/kr/signals/vcp", { params });
    return response.data;
}
```

**✅ 정상 작동:**
- 프론트엔드는 API 응답을 정상적으로 표시
- 문제는 백엔드에서 넘겨주는 데이터 자체

---

## 6. 데이터베이스 조회 로직

### 6.1 VCP Signal Repository

**파일:** `src/repositories/vcp_signal_repository.py:33-66`

```python
def get_active_vcp_signals(
    self,
    limit: int = 10,
    market: Optional[str] = None
) -> List[Signal]:
    """활성 VCP 시그널 조회 (상위 N개)"""
    query = select(Signal).join(
        Stock, Signal.ticker == Stock.ticker
    ).where(
        and_(
            Signal.signal_type == "VCP",
            Signal.status == "OPEN"
        )
    )

    # 시장 필터
    if market:
        query = query.where(Stock.market == market)

    # 점수 내림차순 정렬
    query = query.order_by(desc(Signal.score)).limit(limit)

    result = self.session.execute(query)
    return list(result.scalars().all())
```

**✅ 정상 작동:**
- DB에서 저장된 VCP 시그널 조회
- 점수순 정렬
- 문제는 저장된 데이터 자체에 수급 정보가 없음

---

## 7. 문제 요약

| 항목 | 기대 동작 | 실제 동작 | 상태 |
|------|----------|----------|------|
| **스캔 대상** | 코스피/코스닥 전 종목 | 전 종목 스캔 (DB `stocks` 테이블 전체) | ✅ 정상 |
| **관리종목 제외** | 제외됨 | `is_admin=False` 필터 적용 | ✅ 정상 |
| **병렬 분석** | 동시 처리 | `asyncio.gather()` + 세마포어(10) | ✅ 정상 |
| **VCP 점수 계산** | 볼린저밴드, 거래량, 변동성 등 | 정상 계산됨 | ✅ 정상 |
| **SmartMoney 점수** | 외국인/기관 수급 반영 | 정상 계산됨 | ✅ 정상 |
| **총점 산출** | VCP(50%) + SmartMoney(50%) | 정상 계산됨 | ✅ 정상 |
| **DB 저장 - 수축률** | 실제 볼린저밴드 수축률 | `vcp_score / 100` (null 반환) | ❌ 오류 |
| **DB 저장 - 외국인 수급** | 5일 순매수 합계 | **하드코딩 0** | ❌ 누락 |
| **DB 저장 - 기관 수급** | 5일 순매수 합계 | **하드코딩 0** | ❌ 누락 |
| **자동화 스케줄** | 주기적 실행 | 30분 간격 Celery Beat | ✅ 정상 |
| **프론트엔드 표시** | API 데이터 표시 | 정상 표시 | ✅ 정상 |

---

## 8. 원인 분석

### 8.1 직접적 원인

**하드코딩된 수급 데이터:**

`services/vcp_scanner/main.py`에서 시그널을 DB에 저장할 때:
```python
foreign_net_5d=0,  # TODO: 수급 데이터 연동
inst_net_5d=0,
```

VCP 분석 과정에서 SmartMoney 점수는 정상적으로 계산되지만, DB 저장 시 **점수만 저장되고 수급 데이터는 누락**됩니다.

### 8.2 근본적 원인

1. **VCPResult 모델과 Signal 모델의 불일치**
   - `VCPResult`에는 수급 관련 필드가 없음
   - `Signal` 모델에는 `foreign_net_5d`, `inst_net_5d` 필드가 존재
   - 하지만 저장 시 연결 로직이 구현되지 않음

2. **수축률 계산 로직 오류**
   - `contraction_ratio = result.vcp_score / 100`는 VCP 점수를 100으로 나눈 것
   - 실제 볼린저밴드 수축률 계산 로직이 별도로 필요함

---

## 9. 개선 권장 사항

### 9.1 즉시 수정 필요

**1. 수급 데이터 연동 (우선순위: 높음)**

`services/vcp_scanner/vcp_analyzer.py`의 `VCPResult` 모델에 수급 필드 추가:
```python
@dataclass
class VCPResult:
    # ... 기존 필드 ...
    foreign_net_5d: Optional[float] = None  # 추가
    inst_net_5d: Optional[float] = None      # 추가
```

`_calculate_smartmoney_score()`에서 수급 데이터 반환:
```python
async def _calculate_smartmoney_score(self, ticker: str) -> Tuple[float, Optional[float], Optional[float]]:
    # ... 기존 로직 ...
    # (total_score, foreign_net_5d, inst_net_5d) 반환
```

`services/vcp_scanner/main.py`에서 DB 저장 시 연동:
```python
signal = Signal(
    # ...
    foreign_net_5d=result.foreign_net_5d or 0,  # 실제 값 사용
    inst_net_5d=result.inst_net_5d or 0,         # 실제 값 사용
)
```

**2. 수축률 계산 로직 수정**

실제 볼린저밴드 수축률을 계산하여 저장:
```python
# 볼린저밴드 상단/하단 간격 / 중심가 (SMA)
bb_width = (upper_band - lower_band) / sma * 100
contraction_ratio = bb_width / 100  # 0-1 사이 값
```

### 9.2 장기 개선 사항

1. **데이터 검증 로직 추가**
   - 수급 데이터가 없는 경우 시그널 생성 제외
   - 최소 데이터 기준 미달 시 경고

2. **로그 및 모니터링**
   - VCP 스캔 실행 로그 상세화
   - 수급 데이터 연동 실패 시 알림

3. **테스트 케이스 추가**
   - 수급 데이터 연동 테스트
   - 전 종목 스캔 통합 테스트

---

## 10. 부록: 관련 파일 목록

### VCP 스캐너
- `services/vcp_scanner/main.py` - VCP Scanner 서비스 메인
- `services/vcp_scanner/vcp_analyzer.py` - VCP 분석 로직

### API Gateway
- `services/api_gateway/routes/triggers.py` - VCP 스캔 트리거 엔드포인트
- `services/api_gateway/routes/signals.py` - 시그널 조회 엔드포인트

### Repository
- `src/repositories/vcp_signal_repository.py` - VCP 시그널 DB 조회
- `src/repositories/signal_repository.py` - 시그널 DB CRUD

### 태스크
- `tasks/scan_tasks.py` - Celery VCP 스캔 태스크
- `tasks/sync_tasks.py` - Celery 종목 동기화 태스크
- `tasks/celery_app.py` - Celery 설정 및 스케줄

### 프론트엔드
- `frontend/app/page.tsx` - 메인 페이지 (시그널 표시)
- `frontend/app/dashboard/kr/vcp/page.tsx` - VCP 전용 페이지
- `frontend/lib/api-client.ts` - API 클라이언트
- `frontend/store/index.ts` - 전역 상태 관리

---

*보고서 작성: Claude (QA 전문가 모드)*
*분석 방법: Playwright 자동화 테스트 + 코드 정적 분석*
