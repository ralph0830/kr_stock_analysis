# Quality Engineer Quick Reference

**역할:** Quality Engineer (ralph-stock-creator 팀)
**마지막 업데이트:** 2026-02-06

---

## 🎯 현재 미션 상태

| 미션 | 상태 | 진행률 |
|------|------|--------|
| 미션 1: 커버리지 분석 및 계획 수립 | ✅ 완료 | 100% |
| 미션 2: Phase 1 실행 (70% 달성) | 🔄 대기 중 | 0% |

---

## 📊 커버리지 현황

### 전체
- **현재:** 55%
- **목표:** 70%
- **격차:** -15%

### 주요 모듈
| 모듈 | 현재 | 목표 | 상태 |
|------|------|------|------|
| DaytradingSignal Repository | 100% | 80% | ✅ 초과 달성 |
| Kiwoom REST API | 50% | 70% | 🟡 진행 필요 |
| WebSocket Server | 60% | 75% | 🟡 진행 필요 |
| Stock Repository | 40% | 70% | 🟡 진행 필요 |

---

## 🧪 테스트 인벤토리

```
총 테스트 파일: 115개
총 테스트 케이스: 1,524개
수집 에러: 0개 ✅
```

### 카테고리별 분포
- 단위 테스트 (unit/): ~70%
- 통합 테스트 (integration/): ~28%
- E2E 테스트 (e2e/): ~2%

---

## 🚀 Phase 1 실행 계획 (11시간)

### Task 1: Kiwoom REST API (4시간)
**파일:** `tests/unit/kiwoom/test_rest_api_chart.py` (신규)

```bash
# 생성할 테스트
- test_get_stock_daily_chart_sorts_ascending
- test_get_stock_daily_chart_with_30_days
- test_get_stock_daily_chart_empty_response
- test_get_stock_daily_chart_api_error
- test_401_error_triggers_token_refresh
- test_network_error_retry
```

**예상 커버리지:** +8% (50% → 58%)

### Task 2: WebSocket 구독 (3시간)
**파일:** `tests/unit/websocket/test_connection_manager.py` (신규)

```bash
# 생성할 테스트
- test_connect_adds_connection
- test_disconnect_removes_connection
- test_subscribe_adds_topic
- test_unsubscribe_removes_topic
- test_broadcast_to_subscribers_only
- test_send_personal_message
```

**예상 커버리지:** +7% (60% → 67%)

### Task 3: WebSocket 하트비트 (2시간)
**파일:** `tests/unit/websocket/test_heartbeat.py` (신규)

```bash
# 생성할 테스트
- test_record_pong_updates_timestamp
- test_is_client_alive_within_timeout
- test_is_client_alive_after_timeout
- test_get_inactive_clients_returns_timed_out
```

**예상 커버리지:** +4% (67% → 71%)

### Task 4: Stock Repository (2시간)
**파일:** `tests/unit/repositories/test_stock_repository.py` (기존 파일에 추가)

```bash
# 추가할 테스트
- test_search_by_name_partial_match
- test_search_by_ticker
- test_list_all_with_market_filter
- test_list_all_with_sector_filter
- test_create_if_not_exists_new_stock
```

**예상 커버리지:** +5% (40% → 70%)

---

## 📝 테스트 작성 가이드

### 네이밍 컨벤션
```python
# 좋은 예 ✅
def test_get_active_signals_returns_only_open_status():
    """활성 신호 조회 - OPEN 상태만 반환"""
    pass

# 나쁜 예 ❌
def test_signal():
    pass
```

### Fixture 활용
```python
# conftest.py
@pytest.fixture
def db_session():
    """테스트용 DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
```

### Mock 사용
```python
from unittest.mock import Mock, AsyncMock, patch

# Mock 생성
mock_websocket = Mock(spec=WebSocket)
mock_websocket.send_json = AsyncMock()

# Patch 사용
with patch('httpx.AsyncClient.get', return_value=mock_response):
    result = await api.get_data()
```

---

## 🔧 테스트 실행 명령어

### 기본 명령어
```bash
# 전체 테스트 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov=./src --cov=./services --cov-report=html

# 상세 출력
uv run pytest -v --tb=short

# 실패한 테스트만 다시 실행
uv run pytest --lf
```

### 필터링
```bash
# 특정 모듈
uv run pytest tests/unit/kiwoom/

# 마커 필터링
uv run pytest -m "unit"
uv run pytest -m "integration"
uv run pytest -m "not slow"

# 특정 파일
uv run pytest tests/unit/repositories/test_daytrading_signal_repository.py
```

### 커버리지 확인
```bash
# 전체 커버리지
uv run pytest --cov=./src --cov=./services --cov-report=term-missing

# 특정 모듈 커버리지
uv run pytest tests/unit/kiwoom/ --cov=src/kiwoom/rest_api --cov-report=term-missing

# HTML 리포트
uv run pytest --cov=./src --cov-report=html
open htmlcov/index.html
```

---

## ✅ 체크리스트

### Phase 1 시작 전
- [ ] DaytradingSignal Repository 테스트 확인 ✅
- [ ] 테스트 수집 에러 확인 (0개) ✅
- [ ] 커버리지 기록: 55%

### Task 1: Kiwoom REST API
- [ ] test_rest_api_chart.py 파일 생성
- [ ] 6개 테스트 작성
- [ ] 커버리지 58% 달성 확인

### Task 2: WebSocket 구독
- [ ] test_connection_manager.py 파일 생성
- [ ] 6개 테스트 작성
- [ ] 커버리지 67% 달성 확인

### Task 3: WebSocket 하트비트
- [ ] test_heartbeat.py 파일 생성
- [ ] 4개 테스트 작성
- [ ] 커버리지 71% 달성 확인

### Task 4: Stock Repository
- [ ] test_stock_repository.py에 테스트 추가
- [ ] 5개 테스트 작성
- [ ] 커버리지 70% 최종 달성 확인

---

## 📚 관련 문서

### 보고서
1. **미션 1 완료 보고서**
   - `docs/report/quality_engineer_summary_20260206.md`
   - 전체 분석 및 계획 요약

2. **커버리지 분석 보고서**
   - `docs/report/quality_engineer_mission_1_report_20260206.md`
   - 상세 분석 (20페이지+)

3. **Phase 1 실행 계획**
   - `docs/report/quality_phase1_execution_plan_20260206.md`
   - 구체적인 테스트 코드 예시 포함

### 기존 문서
- `tests/coverage_analysis_report.md`
- `tests/coverage_analysis_summary.md`

---

## 🎓 학습 리소스

### pytest 공식 문서
- [pytest 사용법](https://docs.pytest.org/)
- [Fixture 가이드](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [마커 사용법](https://docs.pytest.org/en/stable/how-to/mark.html)

### 테스트 모범 사례
- [Effective Python Testing with Pytest](https://realpython.com/pytest-python-testing/)
- [Test Coverage in Python](https://coverage.readthedocs.io/)

### CI/CD
- [GitHub Actions for Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)
- [Codecov Integration](https://codecov.com/)

---

## 🔍 문제 해결

### 테스트 수집 에러
```bash
# 에러 확인
uv run pytest --collect-only

# import 에러 확인
uv run pytest --collect-only 2>&1 | grep ERROR
```

### 느린 테스트 찾기
```bash
# 가장 느린 10개 테스트
uv run pytest --durations=10

# slow 마커 추가
@pytest.mark.slow
def test_slow_operation():
    pass
```

### Mock 동작 확인
```python
# Mock이 호출되었는지 확인
mock_websocket.send_json.assert_called_once_with(message)

# 호출 횟수 확인
assert mock_websocket.send_json.call_count == 3

# 호출 인자 확인
mock_websocket.send_json.assert_called_with({"type": "ping"})
```

---

## 📞 연락처

### 팀
- **팀:** ralph-stock-creator
- **역할:** Quality Engineer

### 슬랙 채널 (예정)
- #quality-engineering
- #test-coverage

### 코드 리뷰
- PR 생성 후 팀원들에게 요청

---

*마지막 업데이트: 2026-02-06*
*다음 리뷰: Phase 1 완료 후*
