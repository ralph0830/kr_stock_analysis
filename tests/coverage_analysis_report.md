# 테스트 커버리지 분석 보고서

**분석일:** 2026-02-06
**대상:** tests/ 디렉토리 전체 및 주요 모듈

---

## 1. 현재 테스트 현황

### 1.1 전체 통계

| 항목 | 수치 |
|------|------|
| 전체 테스트 수 | 1,430개 |
| 수집 에러 | 3개 |
| 통합 테스트 | 30+ 파일 |
| 단위 테스트 | 40+ 파일 |
| 서비스별 테스트 | 10+ 파일 |

### 1.2 테스트 수집 에러

1. `tests/integration/e2e/test_vcp_smartmoney_integration.py` - 수집 에러
2. `tests/unit/services/test_daytrading_scanner.py` - 수집 에러
3. `tests/unit/utils/test_circuit_breaker.py` - 수집 에러

---

## 2. 테스트 커버리지 현황

### 2.1 잘 커버되는 모듈 ✅

| 모듈 | 커버리지 | 비고 |
|------|----------|------|
| `src/cache/cache_client.py` | 높음 | `tests/unit/cache/test_cache.py` 존재 |
| `src/resilience/circuit_breaker.py` | 높음 | `tests/unit/resilience/test_circuit_breaker.py` 존재 |
| `src/tasks/collection_tasks.py` | 높음 | `tests/unit/tasks/test_collection_tasks.py` 존재 |
| `src/tasks/signal_tasks.py` | 높음 | `tests/unit/tasks/test_signal_tasks.py` 존재 |
| `src/monitoring/resource_monitor.py` | 중간 | `tests/unit/monitoring/test_resource_monitor.py` 존재 |
| `services/vcp_scanner/` | 높음 | 서비스 전용 테스트 폴더 존재 |
| `services/chatbot/` | 높음 | LLM, retriever, API 테스트 존재 |
| `services/signal_engine/` | 높음 | scorer, API 테스트 존재 |

### 2.2 테스트가 부족한 모듈 ⚠️

| 모듈 | 우선순위 | 필요한 테스트 |
|------|----------|--------------|
| `src/kiwoom/rest_api.py` | **P0 (높음)** | API 호출, 토큰 관리, 차트 조회 |
| `src/websocket/server.py` | **P0 (높음)** | WebSocket 연결, 브로드캐스트, 하트비트 |
| `src/repositories/stock_repository.py` | **P1 (중간)** | CRUD 작업, 쿼리 로직 |
| `src/repositories/daytrading_signal_repository.py` | **P1 (중간)** | 신호 저장, 조회, 상태 업데이트 |
| `services/daytrading_scanner/scanner.py` | **P0 (높음)** | 시장 스캔, 점수 계산 |
| `services/daytrading_scanner/models/scoring.py` | **P1 (중간)** | 개별 점수 계산 로직 |
| `src/middleware/` | **P2 (낮음)** | 인증, rate limiting, logging |
| `src/analysis/` | **P2 (낮음)** | VCP, 센티먼트, 섹터 분석 |

### 2.3 테스트가 없는 모듈 ❌

| 모듈 | 우선순위 | 이유 |
|------|----------|------|
| `src/utils/validation.py` | P1 | 입력 검증 로직 |
| `src/clients/api_client.py` | P1 | 외부 API 호출 |
| `src/clients/websocket_client.py` | P2 | WebSocket 클라이언트 |
| `src/collectors/yonhap_collector.py` | P2 | 뉴스 수집 |
| `src/collectors/krx_collector.py` | P2 | KRX 데이터 수집 |
| `src/health/health_checker.py` | P2 | 헬스체크 |
| `src/config/` | P3 | 설정 관리 |

---

## 3. 핵심 로직 분석

### 3.1 시그널 생성 로직

**모듈:** `services/daytrading_scanner/models/scoring.py`

**핵심 함수:**
- `calculate_daytrading_score()` - 종합 점수 계산
- `calculate_volume_spike_score()` - 거래량 폭증 (15점)
- `calculate_momentum_breakout_score()` - 모멘텀 돌파 (15점)
- `calculate_box_breakout_score()` - 박스권 탈출 (15점)
- `calculate_ma5_above_score()` - 5일선 위 (15점)
- `calculate_institution_buy_score()` - 기관 매수 (15점)
- `calculate_oversold_bounce_score()` - 낙폭 과대 반등 (15점)
- `calculate_sector_momentum_score_from_db()` - 섹터 모멘텀 (15점)

**현재 커버리지:** 일부 테스트 존재 (`test_daytrading_scoring_real_data.py`)

**부족한 부분:**
- 경계값 테스트 (0점/8점/15점 기준)
- 에러 케이스 (데이터 부족, None 처리)
- 섹터 모멘텀 DB 조회 로직

### 3.2 스캐닝 로직

**모듈:** `services/daytrading_scanner/scanner.py`

**핵심 함수:**
- `scan_market()` - 시장 스캔
- `_get_suspended_stocks()` - 거래정지 종목 조회
- `_is_trading_suspended()` - 거래정지 확인
- `_convert_chart_to_daily_prices()` - 차트 데이터 변환
- `_save_signal()` - 시그널 DB 저장

**현재 커버리지:** 통합 테스트 존재하지만 Mock 의존도 높음

**부족한 부분:**
- Kiwoom API 호출 실패 시 fallback 로직
- 캐시 무효화 동작
- 거래정지 필터링 로직

### 3.3 Kiwoom REST API

**모듈:** `src/kiwoom/rest_api.py`

**핵심 함수:**
- `issue_token()` - 토큰 발급
- `ensure_token_valid()` - 토큰 유효성 확인
- `get_stock_daily_chart()` - 일봉 차트 조회
- `get_daily_trade_detail()` - 일별거래상세 조회
- `get_suspended_stocks()` - 거래정지 종목 조회

**현재 커버리지:** 테스트 없음

**필요한 테스트:**
- 토큰 만료/갱신 시나리오
- API 호출 실패/재시도 로직
- Rate limiting 처리

### 3.4 WebSocket 서버

**모듈:** `src/websocket/server.py`

**핵심 클래스:**
- `ConnectionManager` - 연결 관리
- `PriceUpdateBroadcaster` - 가격 브로드캐스트
- `SignalBroadcaster` - 시그널 브로드캐스트
- `HeartbeatManager` - 하트비트 관리
- `RedisSubscriber` - Redis Pub/Sub

**현재 커버리지:** 단위 테스트 부족 (`test_websocket_elw.py`만 존재)

**필요한 테스트:**
- 연결/연결 해제 시나리오
- 토픽 구독/구독 취소
- 브로드캐스트 필터링
- 하트비트 타임아웃 처리

---

## 4. 통합 테스트 필요성

### 4.1 서비스 간 연동 테스트

| 시나리오 | 관련 서비스 | 우선순위 |
|----------|-------------|----------|
| 시장 스캔 → 시그널 저장 → 브로드캐스트 | Daytrading Scanner → DB → WebSocket | P0 |
| Kiwoom API → 가격 업데이트 → WebSocket | Kiwoom REST → Price Broadcaster → WebSocket | P0 |
| VCP 스캔 → SmartMoney 분석 → 종합 점수 | VCP Scanner → SmartMoney Analyzer | P1 |
| 뉴스 수집 → 센티먼트 분석 → AI 추천 | News Collector → Sentiment Analyzer → Chatbot | P2 |

### 4.2 E2E 테스트

| 시나리오 | 설명 | 우선순위 |
|----------|------|----------|
| 사용자 요청 → 시장 스캔 → 결과 반환 | API Gateway → Scanner → DB → 응답 | P0 |
| WebSocket 연결 → 실시간 가격 수신 | WebSocket → Price Broadcaster → 클라이언트 | P1 |
| 뉴스 기사 수집 → 분석 → 저장 | Collector → Analyzer → DB | P2 |

---

## 5. 추가가 필요한 테스트 케이스

### 5.1 Daytrading Scoring (P0)

```python
# tests/unit/services/daytrading/test_scoring_edge_cases.py

class TestScoringEdgeCases:
    """점수 계산 경계값 테스트"""

    def test_volume_spike_exact_2x_returns_15(self):
        """거래량이 정확히 2배면 15점"""
        ...

    def test_volume_spike_1_5x_returns_8(self):
        """거래량이 1.5배면 8점"""
        ...

    def test_volume_spike_below_1_5x_returns_0(self):
        """거래량이 1.5배 미만이면 0점"""
        ...

    def test_zero_avg_volume_returns_0(self):
        """평균 거래량이 0이면 0점"""
        ...

    def test_momentum_new_high_returns_15(self):
        """신고가 갱신 시 15점"""
        ...

    def test_momentum_2_percent_above_returns_15(self):
        """직전 고가 +2% 돌파 시 15점"""
        ...

    def test_momentum_1_percent_above_returns_8(self):
        """직전 고가 +1% 돌파 시 8점"""
        ...

    def test_institution_100_billion_returns_15(self):
        """기관 매수 100억 이상 시 15점"""
        ...

    def test_institution_50_billion_returns_8(self):
        """기관 매수 50억 이상 시 8점"""
        ...

    def test_oversold_big_drop_bounce_returns_15(self):
        """-3% 이상 하락 후 +2% 반등 시 15점"""
        ...
```

### 5.2 Kiwoom REST API (P0)

```python
# tests/unit/kiwoom/test_rest_api.py

class TestKiwoomRestAPI:
    """Kiwoom REST API 테스트"""

    @pytest.mark.asyncio
    async def test_issue_token_success(self):
        """토큰 발급 성공"""
        ...

    @pytest.mark.asyncio
    async def test_issue_token_failure(self):
        """토큰 발급 실패"""
        ...

    @pytest.mark.asyncio
    async def test_token_expiry_detection(self):
        """토큰 만료 감지"""
        ...

    @pytest.mark.asyncio
    async def test_token_refresh_on_401(self):
        """401 응답 시 토큰 갱신"""
        ...

    @pytest.mark.asyncio
    async def test_get_stock_daily_chart_success(self):
        """일봉 차트 조회 성공"""
        ...

    @pytest.mark.asyncio
    async def test_get_daily_trade_detail_success(self):
        """일별거래상세 조회 성공"""
        ...

    @pytest.mark.asyncio
    async def test_get_suspended_stocks_filters_correctly(self):
        """거래정지 종목 필터링"""
        ...
```

### 5.3 WebSocket Server (P0)

```python
# tests/unit/websocket/test_server.py

class TestConnectionManager:
    """ConnectionManager 테스트"""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self):
        """연결 추가"""
        ...

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """연결 제거"""
        ...

    @pytest.mark.asyncio
    async def test_subscribe_adds_topic(self):
        """토픽 구독"""
        ...

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_subscribers_only(self):
        """구독자에게만 브로드캐스트"""
        ...


class TestPriceUpdateBroadcaster:
    """PriceUpdateBroadcaster 테스트"""

    @pytest.mark.asyncio
    async def test_fetch_prices_from_kiwoom(self):
        """Kiwoom API에서 가격 조회"""
        ...

    @pytest.mark.asyncio
    async def test_fetch_prices_from_db_fallback(self):
        """Kiwoom 실패 시 DB fallback"""
        ...


class TestHeartbeatManager:
    """HeartbeatManager 테스트"""

    @pytest.mark.asyncio
    async def test_ping_sends_to_all_connections(self):
        """모든 연결에 ping 전송"""
        ...

    def test_record_pong_updates_timestamp(self):
        """pong 수신 시간 기록"""
        ...

    def test_is_client_alive_timeout_detection(self):
        """클라이언트 타임아웃 감지"""
        ...
```

### 5.4 Repository Layer (P1)

```python
# tests/unit/repositories/test_stock_repository.py

class TestStockRepository:
    """StockRepository 테스트"""

    def test_get_by_ticker_found(self):
        """종목 코드로 조회 - 발견"""
        ...

    def test_get_by_ticker_not_found(self):
        """종목 코드로 조회 - 미발견"""
        ...

    def test_list_all_with_market_filter(self):
        """시장 필터링 목록 조회"""
        ...

    def test_search_by_name(self):
        """이름으로 검색"""
        ...

    def test_search_by_ticker(self):
        """티커로 검색"""
        ...

    def test_create_if_not_exists_new(self):
        """신규 종목 생성"""
        ...

    def test_create_if_not_exists_existing(self):
        """기존 종목 반환"""
        ...


class TestDaytradingSignalRepository:
    """DaytradingSignalRepository 테스트"""

    def test_create_signal(self):
        """신호 생성"""
        ...

    def test_get_active_signals(self):
        """활성 신호 조회"""
        ...

    def test_get_by_min_score(self):
        """최소 점수 이상 신호 조회"""
        ...

    def test_update_status(self):
        """상태 업데이트"""
        ...

    def test_delete_by_date(self):
        """날짜별 신호 삭제"""
        ...
```

---

## 6. 우선순위별 작업 계획

### Phase 1: P0 (긴급) - 핵심 로직

1. **Daytrading Scoring 경계값 테스트** - `tests/unit/services/daytrading/test_scoring_edge_cases.py`
2. **Kiwoom REST API 단위 테스트** - `tests/unit/kiwoom/test_rest_api.py`
3. **WebSocket Server 단위 테스트** - `tests/unit/websocket/test_server.py`
4. **Daytrading Scanner 통합 테스트 개선** - `tests/integration/services/test_daytrading_scanner.py` 수정

### Phase 2: P1 (중간) - 데이터 계층

1. **Stock Repository 테스트** - `tests/unit/repositories/test_stock_repository.py`
2. **Daytrading Signal Repository 테스트** - `tests/unit/repositories/test_daytrading_signal_repository.py`
3. **API 클라이언트 테스트** - `tests/unit/clients/test_api_client.py`
4. **유틸리티 함수 테스트** - `tests/unit/utils/test_validation.py`

### Phase 3: P2 (낮음) - 주변 로직

1. **미들웨어 테스트** - `tests/unit/middleware/`
2. **컬렉터 테스트** - `tests/unit/collectors/`
3. **헬스체크 테스트** - `tests/unit/health/test_health_checker.py`

---

## 7. 테스트 수집 에러 수정

### 7.1 수정 필요한 파일

1. `tests/integration/e2e/test_vcp_smartmoney_integration.py`
2. `tests/unit/services/test_daytrading_scanner.py`
3. `tests/unit/utils/test_circuit_breaker.py`

### 7.2 pytest.mark 등록

`pytest.ini` 또는 `pyproject.toml`에 마커 등록 필요:

```toml
[tool.pytest.ini_options]
markers = [
    "red: Red phase TDD test (not yet implemented)",
    "green: Green phase TDD test (implemented)",
    "refactor: Refactor phase TDD test (optimized)",
    "slow: Marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: Integration test",
    "unit: Unit test",
]
```

---

## 8. 커버리지 목표

| 모듈 | 현재 | 목표 | 우선순위 |
|------|------|------|----------|
| `services/daytrading_scanner/` | 40% | 80% | P0 |
| `src/kiwoom/rest_api.py` | 0% | 70% | P0 |
| `src/websocket/server.py` | 20% | 75% | P0 |
| `src/repositories/` | 30% | 80% | P1 |
| `src/middleware/` | 10% | 60% | P2 |
| `src/collectors/` | 20% | 60% | P2 |
| **전체** | **~35%** | **70%** | - |

---

## 9. 결론

현재 프로젝트는 기본 테스트 구조가 잘 갖춰져 있으나, 핵심 비즈니스 로직인 **시그널 생성**, **스캐닝**, **API 호출** 부분의 테스트가 부족합니다.

특히:
1. **Kiwoom REST API** 테스트가 전혀 없음
2. **WebSocket 서버** 연결/브로드캐스트 로직 테스트 부족
3. **Repository 계층** CRUD 작업 테스트 부족
4. **점수 계산** 경계값/에러 케이스 테스트 부족

우선순위대로 테스트를 추가하고, 테스트 수집 에러를 수정하여 안정적인 테스트 스위트를 구축해야 합니다.
