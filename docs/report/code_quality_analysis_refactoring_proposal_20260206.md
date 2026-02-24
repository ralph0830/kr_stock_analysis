# 코드 품질 분석 및 리팩토링 제안 보고서

**작성일:** 2026-02-06
**분석 범위:** Backend 서비스 (services/*), Core 모듈 (src/*), Frontend (frontend/*)
**분석 대상 파일:** 441개 Python/TypeScript 파일

---

## 1. 코드 품질 개요

### 1.1 전체 품질 평가

| 항목 | 점수 | 설명 |
|------|------|------|
| **테스트 커버리지** | 8/10 | 622개 테스트 통과, 20개 스킵 |
| **모듈화** | 7/10 | 마이크로서비스 구조 잘 정의되어 있으나 일부 중복 존재 |
| **코드 복잡도** | 6/10 | 일부 함수 100+ 라인, cyclomatic complexity 높음 |
| **일관성** | 7/10 | 전반적으로 일관되나 예외 처리 패턴 불균형 |
| **문서화** | 6/10 | docstring 존재하나 TODO 주석 다수 |
| **종합 점수** | **6.8/10** | 양호한 수준이나 개선 여지 있음 |

### 1.2 주요 강점

1. **마이크로서비스 아키텍처**: 서비스별 명확한 분리 (API Gateway, VCP Scanner, Signal Engine, Daytrading Scanner, Chatbot)
2. **테스트 인프라**: pytest 기반 통합/단위 테스트 체계 구축
3. **Repository 패턴**: 데이터 접근 계층 일관되게 적용
4. **WebSocket 실시간 연동**: 실시간 가격/시그널 브로드캐스팅 구조 확립
5. **Zustand 상태관리**: Frontend 상태관리 깔끔하게 구현

### 1.3 주요 약점

1. **중복 코드**: 가격 조회, 시그널 변환 로직 등 여러 곳에서 중복
2. **긴 함수/메서드**: `main.py` 등 핵심 파일 200+ 라인, `useWebSocket.ts` 940+ 라인
3. **TODO 주석 미해결**: 40+개 TODO 주식 미구현 상태
4. **에러 처리 불균형**: 일부 곳은 상세한 에러 처리, 다른 곳은 `pass` 또는 기본값 반환
5. **Magic Number**: 점수 계산, 등급 기준 등 하드코딩된 상수 다수

---

## 2. 리팩토링 후보 목록 (우선순위별)

### 🔴 Priority 1: 높은 복잡도 + 중복 코드

#### 2.1 `services/api_gateway/main.py` (2,050 라인)

**현재 문제점:**
- 단일 파일에 헬스체크, 메트릭, 시그널 조회, 백테스트 KPI 등 다양한 엔드포인트 혼재
- lifespan 함수 240+ 라인 (Kiwoom 연동, 브로드캐스터 시작, 하트비트 등)
- CORS origin 리스트 20+개 하드코딩

**개선 방안:**
```python
# 리팩토링 제안
services/api_gateway/
├── main.py (초기화, 라우터 등록만, ~200라인)
├── routes/
│   ├── health.py (헬스체크)
│   ├── metrics.py (메트릭)
│   ├── kr_signals.py (한국 시그널)
│   └── ...
├── lifespan/
│   ├── __init__.py
│   ├── kiwoom_integration.py (Kiwoom 연동)
│   ├── broadcaster_setup.py (브로드캐스터 설정)
│   └── heartbeat_setup.py (하트비트 설정)
└── config/
    └── cors.py (CORS 설정 중앙화)
```

**예상 효과:**
- 파일 크기 2000라인 → 200라인 (90% 감소)
- 유지보수성 향상
- 테스트 용이성 개선

**작업 난이도:** 중간 (1-2일)

---

#### 2.2 `src/kiwoom/rest_api.py` (1,679 라인)

**현재 문제점:**
- 단일 클래스에 30+개 메서드
- 토큰 관리, 가격 조회, 차트 조회, 주문, 계좌 조회 등 다양한 책임
- 일봉 데이터 조회 로직 중복 (`get_daily_prices`, `get_stock_daily_chart`, `get_index_daily_chart`)

**개선 방안:**
```python
# 리팩토링 제안
src/kiwoom/
├── rest_api.py (클라이언트 초기화, 토큰 관리만, ~300라인)
├── api/
│   ├── __init__.py
│   ├── price.py (현재가, 실시간 가격)
│   ├── chart.py (일봉, 분봉, 지수 차트)
│   ├── order.py (주문)
│   └── account.py (계좌, 잔고)
└── models/
    └── responses.py (API 응답 모델)
```

**예상 효과:**
- 단일 책임 원칙 준수
- 테스트 용이성 개선 (각 API 모듈 독립 테스트)
- 코드 재사용성 향상

**작업 난이도:** 중간 (2-3일)

---

#### 2.3 `src/websocket/server.py` (1,102 라인)

**현재 문제점:**
- ConnectionManager, PriceUpdateBroadcaster, SignalBroadcaster, HeartbeatManager, RedisSubscriber 등 5개 클래스 혼재
- 전역 인스턴스(`connection_manager`, `price_broadcaster`, `signal_broadcaster`, `_heartbeat_manager`, `_redis_subscriber`) 다수

**개선 방안:**
```python
# 리팩토링 제안
src/websocket/
├── server.py (FastAPI 라우팅만, ~100라인)
├── managers/
│   ├── __init__.py
│   ├── connection.py (ConnectionManager)
│   ├── price_broadcaster.py (PriceUpdateBroadcaster)
│   ├── signal_broadcaster.py (SignalBroadcaster)
│   ├── heartbeat.py (HeartbeatManager)
│   └── redis_subscriber.py (RedisSubscriber)
└── factory.py (매니저 팩토리)
```

**예상 효과:**
- 모듈별 책임 명확
- 순환 의존성 감소
- 테스트 더블 작성 용이

**작업 난이도:** 낮음 (1일)

---

### 🟡 Priority 2: 중복 코드 제거

#### 2.4 가격 데이터 변환 로직 중복

**중복 위치:**
- `services/daytrading_scanner/scanner.py::_convert_chart_to_daily_prices()`
- `services/daytrading_scanner/scanner.py::_get_recent_prices()`
- `src/websocket/server.py::_fetch_prices_from_db()`
- `frontend/hooks/useWebSocket.ts` (API 응답 변환)

**개선 방안:**
```python
# 새로운 공통 모듈 생성
src/kiwoom/
├── dto.py (데이터 전송 객체)
└── converters.py (Kiwoom API → 내부 모델 변환기)

# 예시
class DailyPriceConverter:
    @staticmethod
    def from_chart_data(ticker: str, chart_data: List[Dict]) -> List[DailyPrice]:
        """Kiwoom 차트 데이터 → DailyPrice 리스트 변환"""
        ...

    @staticmethod
    def to_frontend_format(price: DailyPrice) -> dict:
        """DailyPrice → 프론트엔드 응답 형식 변환"""
        ...
```

**예상 효과:**
- 중복 코드 제거 (약 200-300라인)
- 데이터 변환 로직 일관성 확보
- 버그 수정 시 단일 지점 수정

**작업 난이도:** 낮음 (1일)

---

#### 2.5 시그널 변환 로직 중복 (Frontend)

**중복 위치:**
- `frontend/store/utils/daytradingNormalizer.ts`
- `frontend/hooks/useWebSocket.ts` (VCP 시그널 변환)
- `services/api_gateway/main.py` (시그널 변환)

**개선 방안:**
```typescript
// 공통 타입 정의 및 변환기
frontend/types/
├── signals.ts (통합 시그널 타입)
└── converters.ts (시그널 변환기)

// 변환기 예시
export class SignalConverter {
  static toDaytradingSignal(data: unknown): IDaytradingSignal {
    // 백엔드 응답 → IDaytradingSignal 변환
  }

  static toVCPSignal(data: unknown): IVcpSignal {
    // 백엔드 응답 → IVcpSignal 변환
  }
}
```

**예상 효과:**
- 프론트엔드에서 변환 로직 단일화
- 타입 안정성 확보

**작업 난이도:** 낮음 (0.5일)

---

### 🟢 Priority 3: 하드코딩된 상수 및 Magic Number

#### 2.6 점수 계산 상수 중앙화

**현재 문제점:**
- `services/daytrading_scanner/models/scoring.py`에 하드코딩된 점수 기준 다수
  - `volume_ratio >= 2.0 → 15점`
  - `volume_ratio >= 1.5 → 8점`
  - `percentile <= 0.2 → 15점` (상위 20%)
- `services/signal_engine/scorer.py`에도 유사한 점수 로직

**개선 방안:**
```python
# 점수 기준 설정 파일 생성
src/scoring/
├── __init__.py
├── constants.py (점수 기준 상수)
└── config.py (환경별 점수 설정)

# 예시
@dataclass
class VolumeSpikeConfig:
    HIGH_THRESHOLD: float = 2.0  # 평균 거래량 대비 2배
    HIGH_SCORE: int = 15
    MEDIUM_THRESHOLD: float = 1.5
    MEDIUM_SCORE: int = 8

@dataclass
class DaytradingScoreConfig:
    volume_spike: VolumeSpikeConfig = field(default_factory=VolumeSpikeConfig)
    momentum: MomentumConfig = field(default_factory=MomentumConfig)
    ...
```

**예상 효과:**
- 점수 기준 변경 시 설정 파일만 수정
- 백테스트를 통한 최적화 용이
- A/B 테스트 지원

**작업 난이도:** 낮음 (1일)

---

#### 2.7 WebSocket 하드코딩된 URL/토픽

**현재 문제점:**
- `frontend/hooks/useWebSocket.ts`에 `process.env.NEXT_PUBLIC_WS_URL` 중복 사용
- 토픽 문자열 (`"price:"`, `"market:"`, `"signal:"`) 하드코딩

**개선 방안:**
```typescript
// 토픽 상수 정의
frontend/constants/
└── websocket.ts

export const WS_TOPICS = {
  PRICE_PREFIX: 'price:',
  MARKET_PREFIX: 'market:',
  SIGNAL_PREFIX: 'signal:',
  MARKET_GATE: 'market-gate',
} as const

export const WS_CONFIG = {
  RECONNECT_INTERVAL: 5000,
  PING_INTERVAL: 30000,
  PONG_TIMEOUT: 90000,
} as const
```

**예상 효과:**
- 오타 오류 방지
- 설정 중앙 관리

**작업 난이도:** 매우 낮음 (0.5일)

---

### 🔵 Priority 4: TODO 주석 해결

**40+개 TODO 주석 미해결:**

| 파일 | TODO 내용 | 우선순위 |
|------|-----------|----------|
| `services/daytrading_scanner/main.py:175` | 실제 평균 거래량 계산 | 중간 |
| `services/api_gateway/main.py:1292-1293` | 전일 대비 등락률 계산 | 낮음 |
| `services/api_gateway/main.py:1616` | Data Service 또는 VCP Scanner로 프록시 | 높음 |
| `services/api_gateway/routes/jongga_v2.py:173-174` | 포지션 사이즈/사유 생성 로직 | 중간 |
| `tests/unit/repositories/test_daily_price_repository.py` | 구현 필요 메서드 | 높음 |

**개선 방안:**
1. 각 TODO를 이슈 트래커에 등록
2. 기능 구현 또는 제거 결정
3. 데드라인 설정 및 추적

**작업 난이도:** 다양 (TODO 내용에 따라)

---

## 3. 각 후보별 상세 분석

### 3.1 거래정지 종목 필터링 로직 중복

**중복 위치:**
- `src/kiwoom/rest_api.py:1628-1652` (`TRADING_SUSPENDED_KEYWORDS`, `is_trading_suspended()`, `get_suspended_stocks()`)
- `services/daytrading_scanner/scanner.py:200-247` (동일한 로직 재구현)

**개선 방안:**
```python
# 공통 필터 모듈
src/filters/
├── __init__.py
└── trading_filters.py

class TradingSuspensionFilter:
    TRADING_SUSPENDED_KEYWORDS = [
        "관리종목", "증거금100%", "투자유의환기종목",
        "정리매매", "거래정지", "시장주의", "불매가", "매매거부",
    ]

    @classmethod
    def is_suspended(cls, state: str) -> bool:
        return any(keyword in state for keyword in cls.TRADING_SUSPENDED_KEYWORDS)

    @classmethod
    async def get_suspended_stocks(cls, kiwoom_api, market: str = "ALL") -> Dict[str, str]:
        """거래정지 종목 목록 조회 (캐싱 포함)"""
        ...
```

**예상 효과:**
- 중복 제거 (약 50라인)
- 비즈니스 로직 단일화

---

### 3.2 Mock 데이터 생성 로직 중복

**중복 위치:**
- `services/daytrading_scanner/scanner.py:385-392` (`_get_mock_flow_data()`)
- `src/websocket/server.py:581-616` (`_generate_mock_price_updates()`)
- 다수 테스트 파일

**개선 방안:**
```python
# 테스트 데이터 팩토리
tests/factories/
├── __init__.py
├── price_factory.py
├── signal_factory.py
└── flow_factory.py

class FlowDataFactory:
    @staticmethod
    def create_mock(ticker: str, foreign_net: int = 0, inst_net: int = 0):
        """Mock 수급 데이터 생성"""
        ...
```

**예상 효과:**
- 테스트 코드 간결화
- 일관된 Mock 데이터

---

## 4. 리팩토링 로드맵

### Phase 1: 저수준 리팩토링 (1-2주)

**목표:** 이름 개선, 중복 제거, 상수 추출

| 작업 | 파일 | 예상 시간 | 난이도 |
|------|------|-----------|--------|
| 상수 추출 (WebSocket 토픽, 점수 기준) | 다수 | 1일 | 낮음 |
| 중복 코드 제거 (가격 변환, Mock 데이터) | 다수 | 2일 | 낮음 |
| TODO 주석 해결 (단순 것들) | 다수 | 2일 | 다양 |
| 변수명/함수명 개선 | 다수 | 1일 | 낮음 |

**합계:** 약 6일 작업

---

### Phase 2: 중간 수준 리팩토링 (2-3주)

**목표:** 함수 분리, 모듈화

| 작업 | 파일 | 예상 시간 | 난이도 |
|------|------|-----------|--------|
| API Gateway main.py 분리 | `services/api_gateway/main.py` | 2일 | 중간 |
| Kiwoom REST API 모듈화 | `src/kiwoom/rest_api.py` | 3일 | 중간 |
| WebSocket 서버 분리 | `src/websocket/server.py` | 1일 | 낮음 |
| Repository 공통 메서드 추출 | `src/repositories/*.py` | 2일 | 중간 |
| Frontend 정규화 로직 통합 | `frontend/store/utils/` | 1일 | 낮음 |

**합계:** 약 9일 작업

---

### Phase 3: 고수준 리팩토링 (3-4주)

**목표:** 아키텍처 개선

| 작업 | 설명 | 예상 시간 | 난이도 |
|------|------|-----------|--------|
| 이벤트 기반 아키텍처 도입 | 서비스 간 느슨한 결합 | 1주 | 높음 |
| CQRS 패턴 적용 | 읽기/쓰기 분리 (시그널 생성/조회) | 1주 | 높음 |
| 의존성 주입 프레임워크 | FastAPI Depends 활용 확대 | 3일 | 중간 |
| 메시지 큐 도입 | Celery → RabbitMQ/Redis Streams | 1주 | 높음 |

**합계:** 약 4주 작업

---

## 5. 리팩토링 원칙 및 가이드라인

### 5.1 리팩토링 시 준수 사항

1. **테스트 보장:** 모든 리팩토링은 기존 테스트 통과를 전제
2. **점진적 변경:** 한 번에 하나의 모듈만 리팩토링
3. **기능 보존:** 리팩토링 전후 기능 동일성 보장
4. **커밋 단위:** 리팩토링별 별도 커밋 (롤백 용이)

### 5.2 코드 품질 기준

```python
# 함수 길이: 50라인 이하 권장
# 클래스 길이: 300라인 이하 권장
# 파일 길이: 500라인 이하 권장
# cyclomatic complexity: 10 이하 권장
```

### 5.3 코드 리뷰 체크리스트

- [ ] 함수가 단일 책임을 가지는가?
- [ ] 중복 코드가 없는가?
- [ ] Magic Number가 상수로 추출되었는가?
- [ ] 에러 처리가 적절한가?
- [ ] 테스트가 작성되었는가?
- [ ] 문서(docstring)가 추가되었는가?

---

## 6. 결론 및 다음 단계

### 6.1 요약

본 프로젝트는 전반적으로 양호한 코드 품질을 보이나, 일부 모듈에서 과도한 복잡도와 중복 코드가 확인되었습니다. 특히 `main.py` 계열 파일들이 기능 집중도가 높아 모듈 분리가 시급합니다.

### 6.2 우선 추천 작업

1. **단주 첫 주:** `services/api_gateway/main.py` 분리
2. **단주 둘째 주:** `src/kiwoom/rest_api.py` 모듈화
3. **단주 셋째 주:** 가격 변환 로직 중복 제거

### 6.3 성과 지표

리팩토링 완료 시 기대되는 성과:

| 항목 | 현재 | 목표 |
|------|------|------|
| 평균 파일 크기 | ~800라인 | ~300라인 |
| 코드 중복륨 | ~15% | ~5% |
| cyclomatic complexity | ~15 | ~8 |
| 테스트 커버리지 | 85% | 90% |

---

**보고서 작성자:** Claude (Refactoring Expert Mode)
**승인자:** _____________
**검토자:** _____________
