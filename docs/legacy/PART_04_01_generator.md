# PART 04-1: SignalGenerator (시그널 생성기)

> **파일**: `engine/generator.py`
> **용도**: 종가베팅 V2 시그널 생성 메인 엔진
> **의존**: config, models, collectors, scorer, position_sizer, llm_analyzer

---

## 개요

`SignalGenerator`는 종가베팅 V2 시스템의 핵심 엔진으로, 다음 작업을 수행합니다:

1. **시장 스크리닝**: KOSPI/KOSDAQ 상승률 상위 종목 추출
2. **개별 종목 분석**: 차트, 뉴스, 수급 데이터 수집
3. **LLM 분석**: Gemini API로 뉴스 감성 분석
4. **점수 계산**: 12점 만점 시스템으로 종목 평가
5. **시그널 생성**: 등급(S/A/B/C)과 포지션 사이징

---

## 클래스 구조

```python
class SignalGenerator:
    """종가베팅 시그널 생성기 (v2)"""

    def __init__(
        self,
        config: SignalConfig = None,
        capital: float = 10_000_000,
    ):
        """
        Args:
            capital: 총 자본금 (기본 5천만원)
            config: 설정 (기본 설정 사용)
        """
```

---

## 비동기 컨텍스트 매니저

```python
async def __aenter__(self):
    self._collector = KRXCollector(self.config)
    await self._collector.__aenter__()

    self._news = EnhancedNewsCollector(self.config)
    await self._news.__aenter__()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self._collector:
        await self._collector.__aexit__(exc_type, exc_val, exc_tb)
    if self._news:
        await self._news.__aexit__(exc_type, exc_val, exc_tb)
```

---

## 주요 메서드

### 1. `generate()` - 시그널 생성

```python
async def generate(
    self,
    target_date: date = None,
    markets: List[str] = None,
    top_n: int = 30,
) -> List[Signal]:
    """
    시그널 생성

    Args:
        target_date: 대상 날짜 (기본: 오늘)
        markets: 대상 시장 (기본: KOSPI, KOSDAQ)
        top_n: 상승률 상위 N개 종목

    Returns:
        Signal 리스트 (등급순 정렬)
    """
```

**실행 흐름:**
```
1. 시장별 상승률 상위 종목 조회 (top_n개)
2. 각 종목별 분석 실행 (_analyze_stock)
3. 등급순 정렬 (S > A > B > C)
4. 최대 포지션 수 제한 (max_positions)
5. C등급 제외
```

---

### 2. `_analyze_stock()` - 개별 종목 분석

```python
async def _analyze_stock(
    self,
    stock: StockData,
    target_date: date
) -> Optional[Signal]:
    """개별 종목 분석"""
```

**분석 단계:**

| 단계 | 작업 | 설명 |
|-----|------|------|
| 1 | 상세 정보 조회 | 52주 고가 등 보완 데이터 |
| 2 | 차트 데이터 조회 | 60일 OHLCV 데이터 |
| 3 | 뉴스 조회 | 최신 3개 뉴스 (본문 포함) |
| 4 | LLM 분석 | Gemini API 호재 점수 산출 (Rate Limit: 2초) |
| 5 | 수급 데이터 | 5일 누적 외국인/기관 순매수 |
| 6 | 점수 계산 | Scorer.calculate() |
| 7 | 등급 결정 | S/A/B/C 판정 |
| 8 | 포지션 계산 | PositionSizer.calculate() |

---

### 3. `get_summary()` - 시그널 요약

```python
def get_summary(self, signals: List[Signal]) -> Dict:
    """시그널 요약 정보"""
    summary = {
        "total": len(signals),
        "by_grade": {g.value: 0 for g in Grade},
        "by_market": {},
        "total_position": 0,
        "total_risk": 0,
    }
    ...
```

---

## 간편 함수

### `run_screener()` - 스크리너 실행

```python
async def run_screener(
    capital: float = 50_000_000,
    markets: List[str] = None,
) -> ScreenerResult:
    """
    스크리너 실행 (간편 함수)
    """
```

**반환:**
- `ScreenerResult`: 날짜, 총 후보, 필터링된 수, 시그널 목록, 등급별, 시장별, 처리시간

**저장:**
- `data/jongga_v2_results_{YYYYMMDD}.json`
- `data/jongga_v2_latest.json`

---

### `analyze_single_stock_by_code()` - 단일 종목 재분석

```python
async def analyze_single_stock_by_code(
    code: str,
    capital: float = 50_000_000,
) -> Optional[Signal]:
    """
    단일 종목 재분석 및 결과 JSON 업데이트
    """
```

**동작:**
1. 기존 JSON에서 종목 정보 복원
2. 재분석 실행
3. JSON 데이터 업데이트 (Latest + Daily)

---

## 저장 함수

### `save_result_to_json()` - 결과 저장

```python
def save_result_to_json(result: ScreenerResult):
    """결과 JSON 저장 (Daily + Latest)"""
```

**저장 위치:**
```
data/
├── jongga_v2_results_{YYYYMMDD}.json  # 날짜별
└── jongga_v2_latest.json              # 최신
```

**JSON 구조:**
```json
{
  "date": "2026-01-27",
  "total_candidates": 60,
  "filtered_count": 5,
  "signals": [...],
  "by_grade": {"S": 1, "A": 2, "B": 2, "C": 0},
  "by_market": {"KOSPI": 3, "KOSDAQ": 2},
  "processing_time_ms": 15432,
  "updated_at": "2026-01-27T15:30:00"
}
```

---

## 테스트용 메인

```python
async def main():
    """테스트 실행"""
    print("=" * 60)
    print("종가베팅 시그널 생성기 v2 (Live Entity)")
    print("=" * 60)

    capital = 50_000_000
    print(f"\n자본금: {capital:,}원")
    print(f"R값: {capital * 0.005:,.0f}원 (0.5%)")

    result = await run_screener(capital=capital)

    print(f"\n처리 시간: {result.processing_time_ms:.0f}ms")
    print(f"생성된 시그널: {len(result.signals)}개")
    print(f"등급별: {result.by_grade}")
    ...
```

---

## 실행 예시

```bash
# 직접 실행
python engine/generator.py

# 또는 스크립트에서
async def main():
    async with SignalGenerator(capital=50_000_000) as generator:
        signals = await generator.generate(markets=["KOSPI"])
        for signal in signals:
            print(f"{signal.stock_name}: {signal.grade.value}급")
```

---

## Rate Limiting

- **LLM API 호출**: 2초 딜레이 (Gemini 3.0 유료 모델 기준)
- **API 과부하 방지**: `await asyncio.sleep(2)`

---

## 의존 모듈

| 모듈 | 용도 |
|-----|------|
| `engine.config` | SignalConfig, Grade |
| `engine.models` | StockData, Signal, ScoreDetail, etc. |
| `engine.collectors` | KRXCollector, EnhancedNewsCollector |
| `engine.scorer` | Scorer (점수 계산) |
| `engine.position_sizer` | PositionSizer (포지션 계산) |
| `engine.llm_analyzer` | LLMAnalyzer (Gemini API) |
