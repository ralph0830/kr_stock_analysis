# 테스트 커버리지 분석 및 확대 계획

**작성일:** 2026-02-06
**작성자:** Quality Engineer (Quality Assurance Team)
**상태:** 📋 분석 완료, 계획 수립됨

---

## 1. 현재 커버리지 현황

### 1.1 전체 통계

| 항목 | 수치 |
|------|------|
| 전체 테스트 수 | 1,430개 |
| 통과 | 622개 (최근 실행 기준) |
| 건너뜀 | 20개 |
| 단위 테스트 파일 | 40+ |
| 통합 테스트 파일 | 30+ |
| E2E 테스트 파일 | 5+ |

### 1.2 테스트 파일 구조

```
tests/
├── unit/
│   ├── api_gateway/ (6개) ✅
│   ├── services/ (12개) ✅
│   ├── kiwoom/ (8개) ✅
│   ├── websocket/ (4개) ⚠️
│   ├── repositories/ (9개) ⚠️
│   ├── chatbot/ (6개) ✅
│   ├── middleware/ (3개) ⚠️
│   ├── clients/ (2개) ❌
│   └── utils/ (5개) ⚠️
├── integration/
│   ├── api_gateway/ (12개) ✅
│   ├── services/ (3개) ⚠️
│   ├── database/ (1개) ⚠️
│   └── chatbot/ (2개) ✅
└── e2e/ (5개) ⚠️
```

### 1.3 모듈별 커버리지 추정

| 모듈 | 현재 커버리지 | 테스트 파일 수 | 상태 |
|------|---------------|----------------|------|
| `services/vcp_scanner/` | 85% | 4 | ✅ 양호 |
| `services/chatbot/` | 80% | 6 | ✅ 양호 |
| `services/signal_engine/` | 75% | 3 | ✅ 양호 |
| `services/daytrading_scanner/` | 60% | 2 | 🟡 개선 필요 |
| `services/api_gateway/` | 70% | 12 | 🟡 양호 |
| `src/cache/cache_client.py` | 80% | 1 | ✅ 양호 |
| `src/resilience/circuit_breaker.py` | 85% | 1 | ✅ 양호 |
| `src/kiwoom/rest_api.py` | 40% | 3 | 🔴 부족 |
| `src/websocket/server.py` | 50% | 1 | 🔴 부족 |
| `src/repositories/` | 45% | 9 | 🟡 개선 필요 |
| `src/middleware/` | 30% | 3 | 🟡 부족 |
| `src/clients/` | 20% | 2 | 🔴 부족 |
| `src/collectors/` | 25% | 3 | 🟡 부족 |
| **전체 평균** | **~55%** | **72** | 🟡 목표 미달 |

---

## 2. 커버리지 격차 분석

### 2.1 P0 - 긴급 (핵심 비즈니스 로직)

| 모듈 | 현재 | 목표 | 격차 | 우선순위 사유 |
|------|------|------|------|---------------|
| `services/daytrading_scanner/scanner.py` | 40% | 80% | -40% | 시장 스캔 핵심 로직 |
| `services/daytrading_scanner/models/scoring.py` | 65% | 90% | -25% | 점수 계산 경계값 |
| `src/kiwoom/rest_api.py` | 40% | 75% | -35% | 데이터 소스 API |
| `src/websocket/server.py` | 50% | 80% | -30% | 실시간 데이터 전송 |
| `src/repositories/daytrading_signal_repository.py` | 30% | 80% | -50% | 신호 저장/조회 |

### 2.2 P1 - 중간 (데이터 계층)

| 모듈 | 현재 | 목표 | 격차 | 우선순위 사유 |
|------|------|------|------|---------------|
| `src/clients/api_client.py` | 20% | 70% | -50% | 외부 API 호출 |
| `src/repositories/stock_repository.py` | 50% | 80% | -30% | 종목 CRUD |
| `src/repositories/daily_price_repository.py` | 40% | 75% | -35% | 가격 데이터 CRUD |
| `src/utils/validation.py` | 0% | 80% | -80% | 입력 검증 |

### 2.3 P2 - 낮음 (주변 기능)

| 모듈 | 현재 | 목표 | 격차 |
|------|------|------|------|
| `src/middleware/` | 30% | 60% | -30% |
| `src/collectors/` | 25% | 60% | -35% |
| `src/health/health_checker.py` | 20% | 70% | -50% |

---

## 3. 테스트 수집 에러

### 현재 발생 중인 에러 (3개)

1. **`tests/integration/e2e/test_vcp_smartmoney_integration.py`**
   - 원인: Import 경로 오류 예상
   - 해결: 모듈 경로 확인 및 수정

2. **`tests/unit/services/test_daytrading_scanner.py`**
   - 원인: 모듈 구조 변경으로 인한 import 실패
   - 해결: services/daytrading_scanner/ 구조 반영

3. **`tests/unit/utils/test_circuit_breaker.py`**
   - 원인: 모듈명 변경 (circuit_breaker_legacy.py)
   - 해결: import 경로 수정 또는 파일명 변경

---

## 4. Mock 서비스 활용 상태

### 4.1 구축 완료된 Mock 서비스 ✅

| 서비스 | 포트 | 상태 | 활용 현황 |
|--------|------|------|-----------|
| Mock Kiwoom API | 5116 | ✅ | 테스트에서 partially 활용 |
| Mock WebSocket | 5117 | ✅ | 테스트에서 partially 활용 |
| postgres-test | 5434 | ✅ | 통합 테스트에서 활용 |
| redis-test | 6381 | ✅ | 통합 테스트에서 활용 |

### 4.2 개선 필요 사항

- **Mock 서비스 활용률**: 약 30%만 활용 중
- **필요 조치**: 단위 테스트에서도 Mock 서비스 활용 확대
- **테스트 데이터**: 더 다양한 에러 케이스 데이터 추가 필요

---

## 5. 테스트 추가 우선순위 목록

### Phase 1: P0 (1-2주) - 핵심 로직

#### 1. Daytrading Scanner Core (예상 15개 테스트)

```
파일: tests/unit/services/daytrading/test_scanner.py
- test_scan_market_success
- test_scan_market_with_trading_suspended_filter
- test_scan_market_kiwoom_api_fallback
- test_scan_market_cache_invalidation
- test_get_suspended_stocks_filters_correctly
- test_convert_chart_to_daily_prices_sorting
- test_save_signal_creates_new_record
- test_save_signal_updates_existing
- test_score_calculation_integration
- test_empty_market_scan_handling
- test_partial_failure_handling
- test_concurrent_scan_prevention
- test_scan_with_valid_token
- test_scan_with_expired_token_refresh
- test_scan_metrics_emission
```

#### 2. Kiwoom REST API (예상 12개 테스트)

```
파일: tests/unit/kiwoom/test_rest_api.py (확장)
- test_issue_token_success
- test_issue_token_invalid_credentials
- test_ensure_token_valid_valid_token
- test_ensure_token_valid_expired_token_refresh
- test_get_stock_daily_chart_success
- test_get_stock_daily_chart_reverse_sorting
- test_get_stock_daily_chart_empty_response
- test_get_daily_trade_detail_success
- test_get_suspended_stocks_parsing
- test_get_suspended_stocks_empty_list
- test_api_call_with_retry
- test_api_call_timeout_handling
```

#### 3. WebSocket Server (예상 18개 테스트)

```
파일: tests/unit/websocket/test_server.py
- ConnectionManager (6개)
  - test_connect_adds_connection
  - test_disconnect_removes_connection
  - test_subscribe_adds_topic
  - test_unsubscribe_removes_topic
  - test_broadcast_sends_to_subscribers_only
  - test_get_connection_count

- PriceUpdateBroadcaster (6개)
  - test_fetch_prices_from_kiwoom
  - test_fetch_prices_from_db_fallback
  - test_broadcast_price_updates
  - test_handle_connection_failure
  - test_handle_subscription_change
  - test_metrics_emission

- HeartbeatManager (6개)
  - test_ping_sends_to_all_connections
  - test_record_pong_updates_timestamp
  - test_is_client_alive_true
  - test_is_client_alive_timeout
  - test_cleanup_stale_connections
  - test_heartbeat_interval_configuration
```

#### 4. DaytradingSignal Repository (예상 10개 테스트)

```
파일: tests/unit/repositories/test_daytrading_signal_repository.py
- test_create_signal
- test_create_signal_duplicate_handling
- test_get_active_signals
- test_get_active_signals_empty
- test_get_by_min_score
- test_get_by_min_score_empty
- test_update_status
- test_delete_by_date
- test_get_latest_by_ticker
- test_bulk_create_signals
```

### Phase 2: P1 (2-3주) - 데이터 계층

#### 1. API Client (예상 8개 테스트)

```
파일: tests/unit/clients/test_api_client.py
- test_get_request_success
- test_post_request_success
- test_get_with_retry_success_after_failure
- test_get_with_retry_max_attempts_exceeded
- test_timeout_handling
- test_connection_error_handling
- test_response_parsing_error
- test_metrics_emission
```

#### 2. Validation Utils (예상 6개 테스트)

```
파일: tests/unit/utils/test_validation.py
- test_validate_ticker_valid
- test_validate_ticker_invalid_format
- test_validate_ticker_empty
- test_validate_date_valid
- test_validate_date_invalid_format
- test_validate_date_future
```

#### 3. Stock Repository (예상 8개 테스트)

```
파일: tests/unit/repositories/test_stock_repository.py (확장)
- test_get_by_ticker_found
- test_get_by_ticker_not_found
- test_list_all_with_market_filter
- test_list_all_pagination
- test_search_by_name_partial_match
- test_search_by_ticker_partial_match
- test_create_if_not_exists_new
- test_create_if_not_exists_existing_update
```

### Phase 3: P2 (3-4주) - 주변 기능

#### 1. Middleware Tests (예상 12개 테스트)

```
파일: tests/unit/middleware/test_auth_middleware.py
파일: tests/unit/middleware/test_rate_limit_middleware.py
파일: tests/unit/middleware/test_logging_middleware.py
```

#### 2. Collector Tests (예상 8개 테스트)

```
파일: tests/unit/collectors/test_yonhap_collector.py
파일: tests/unit/collectors/test_krx_collector.py
```

---

## 6. 테스트 작성 가이드라인

### 6.1 테스트 파일 명명 규칙

```
tests/
├── unit/              # 단위 테스트 (Mock만 사용)
│   └── {module_path}/
│       └── test_{module_name}.py
├── integration/       # 통합 테스트 (DB,外部 서비스 Mock)
│   └── {feature_path}/
│       └── test_{scenario}.py
└── e2e/              # E2E 테스트 (전체 흐름)
    └── test_{user_journey}.py
```

### 6.2 단위 테스트 작성 패턴

```python
# tests/unit/services/daytrading/test_scanner.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.daytrading_scanner.scanner import DaytradingScanner
from services.daytrading_scanner.models.daytrading import DaytradingSignal


class TestDaytradingScanner:
    """DaytradingScanner 단위 테스트"""

    @pytest.fixture
    def scanner(self, mock_db, mock_kiwoom_api, mock_cache):
        """테스트용 Scanner 인스턴스"""
        return DaytradingScanner(
            db=mock_db,
            kiwoom_api=mock_kiwoom_api,
            cache=mock_cache
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scan_market_success(self, scanner):
        """시장 스캔 성공 시나리오"""
        # Given
        scanner.kiwoom_api.get_stock_list.return_value = ["005930", "000660"]
        scanner.kiwoom_api.get_daily_chart.side_effect = [
            {"output": [{"date": "20260206", "close": 80000}]},
            {"output": [{"date": "20260206", "close": 150000}]}
        ]

        # When
        results = await scanner.scan_market()

        # Then
        assert len(results) == 2
        assert results[0].ticker == "005930"
        assert scanner.kiwoom_api.get_daily_chart.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scan_market_with_trading_suspended(self, scanner):
        """거래정지 종목 필터링"""
        # Given
        scanner.kiwoom_api.get_stock_list.return_value = ["005930", "900010"]
        scanner.kiwoom_api.get_suspended_stocks.return_value = ["900010"]
        scanner.kiwoom_api.get_daily_chart.return_value = {
            "output": [{"date": "20260206", "close": 80000}]
        }

        # When
        results = await scanner.scan_market()

        # Then
        assert len(results) == 1
        assert results[0].ticker == "005930"
        # 900010은 거래정지로 스캔 제외되어야 함

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scan_market_kiwoom_api_fallback(self, scanner):
        """Kiwoom API 실패 시 DB fallback"""
        # Given
        scanner.kiwoom_api.get_daily_chart.side_effect = Exception("API Error")
        scanner.db.get_latest_daily_prices.return_value = [
            {"ticker": "005930", "date": "20260206", "close": 80000}
        ]

        # When
        results = await scanner.scan_market()

        # Then
        assert len(results) >= 1  # Fallback으로 최소한 하나는 반환
```

### 6.3 통합 테스트 작성 패턴

```python
# tests/integration/services/test_daytrading_scanner_integration.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestDaytradingScannerIntegration:
    """Daytrading Scanner 통합 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_scan_workflow(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_kiwoom_api_server
    ):
        """전체 스캔 워크플로우 테스트"""
        # Given: DB에 종목 데이터 저장
        await db_session.execute(
            "INSERT INTO stocks (ticker, name, market) VALUES ('005930', '삼성전자', 'KOSPI')"
        )
        await db_session.commit()

        # When: 스캔 API 호출
        response = await async_client.post("/api/daytrading/scan")

        # Then: 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert len(data["signals"]) > 0

        # DB에 시그널이 저장되었는지 확인
        result = await db_session.execute(
            "SELECT * FROM daytrading_signals WHERE date = CURRENT_DATE"
        )
        signals = result.fetchall()
        assert len(signals) > 0
```

### 6.4 Mock 활용 가이드

```python
# Mock Kiwoom API 사용 예시

@pytest.fixture
def mock_kiwoom_api():
    """Kiwoom API Mock"""
    with patch('src.kiwoom.rest_api.KiwoomRestAPI') as mock:
        api = mock.return_value
        api.issue_token.return_value = "mock_token_12345"
        api.get_stock_list.return_value = ["005930", "000660"]
        api.get_daily_chart.return_value = {
            "output": [
                {"date": "20260201", "close": 79000},
                {"date": "20260202", "close": 80000},
            ]
        }
        yield api


@pytest.fixture
def mock_cache():
    """Redis Cache Mock"""
    with patch('src.cache.cache_client.CacheClient') as mock:
        cache = mock.return_value
        cache.get.return_value = None
        cache.set.return_value = True
        yield cache
```

---

## 7. CI/CD 연동 계획

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run unit tests
        run: uv run pytest -m unit -v --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ralph_stock_test
        ports:
          - 5434:5432
      redis:
        image: redis:7
        ports:
          - 6381:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run integration tests
        run: uv run pytest -m integration -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5434/ralph_stock_test
          REDIS_URL: redis://localhost:6381/0

  coverage-check:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check coverage threshold
        run: |
          coverage=$(python -c "import xml.etree.ElementTree as ET; tree=ET.parse('coverage.xml'); root=tree.getroot(); print(root.attrib.get('line-rate', '0'))")
          echo "Coverage: $coverage"
          if (( $(echo "$coverage < 0.70" | bc -l) )); then
            echo "Coverage is below 70%"
            exit 1
          fi
```

### 7.2 커버리지 임계값 설정

```ini
# .coveragerc

[run]
source = src, services
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */.venv/*
    */migrations/*

[report]
precision = 2
show_missing = True
skip_covered = False

# 목표: 70% 커버리지
fail_under = 70.0

[html]
directory = htmlcov
```

---

## 8. 실행 계획

### Week 1-2: P0 핵심 로직

- [ ] Daytrading Scanner 테스트 추가 (15개)
- [ ] Kiwoom REST API 테스트 추가 (12개)
- [ ] 테스트 수집 에러 수정 (3개 파일)

### Week 3-4: P0 계속 + WebSocket

- [ ] WebSocket Server 테스트 추가 (18개)
- [ ] DaytradingSignal Repository 테스트 추가 (10개)
- [ ] 통합 테스트 개선

### Week 5-6: P1 데이터 계층

- [ ] API Client 테스트 추가 (8개)
- [ ] Validation Utils 테스트 추가 (6개)
- [ ] Stock Repository 테스트 확장 (8개)

### Week 7-8: P2 주변 기능 + CI/CD

- [ ] Middleware 테스트 추가 (12개)
- [ ] Collector 테스트 추가 (8개)
- [ ] GitHub Actions Workflow 구성
- [ ] Codecov 통합

---

## 9. 성공 지표

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| 전체 커버리지 | 55% | 70% | pytest-cov |
| 핵심 모듈 커버리지 | 50% | 80% | 모듈별 리포트 |
| 테스트 수집 에러 | 3개 | 0개 | pytest 수집 로그 |
| CI 통과율 | N/A | 95%+ | GitHub Actions |
| 테스트 실행 시간 | N/A | 5분 내 | pytest --durations |

---

## 10. 결론

현재 프로젝트는 **1,430개의 테스트**가 존재하며, 핵심 서비스(VCP Scanner, Chatbot, Signal Engine)의 커버리지는 양호한 상태입니다.

하지만 **핵심 비즈니스 로직**인 Daytrading Scanner, Kiwoom REST API, WebSocket Server의 커버리지가 부족하여, 이들을 **우선적으로 개선**해야 합니다.

제안된 계획을 따라 8주간 테스트를 추가하면 **전체 커버리지 70% 달성**이 가능할 것으로 예상됩니다.

---

**Quality Engineer**: Quality Assurance Team
**프로젝트**: Ralph Stock Analysis System
**문서 버전**: 1.0
