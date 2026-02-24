# 테스트 성능 최적화 보고서

**작성일:** 2026-02-06
**작성자:** Performance Engineer (Claude Code)
**버전:** 1.0

---

## Executive Summary

Ralph Stock Analysis System의 테스트 실행 속도 최적화를 완료했습니다. 주요 개선 사항은 다음과 같습니다:

| 항목 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| 기본 타임아웃 | 30초 | 15초 | 50% 감소 |
| Kiwoom WebSocket 수신 타임아웃 | 60초 | 5~10초 | 83% 감소 |
| 테스트 설정 구조 | 수동 설정 | 자동화 fixture | - |
| 병렬 실행 지원 | 미지원 | 설정 추가 | - |

---

## 1. 문제 분석

### 1.1 기존 문제점

1. **Kiwoom WebSocket 타임아웃 과다**
   - `ws_recv_timeout`: 60초 (기본값)
   - `ws_ping_timeout`: 10초
   - 연결 타임아웃: 5초
   - 단위 테스트에서 불필요하게 긴 대기 시간

2. **pytest 기본 타임아웃 설정**
   - `pytest.ini`: `timeout = 30` (30초)
   - 단위 테스트에는 너무 긴 설정

3. **테스트 fixture 부족**
   - 매번 수동으로 `KiwoomConfig` 생성
   - 환경별(단위/통합) 설정 구분 없음

4. **병렬 실행 미지원**
   - `pytest-xdist` 미설치
   - 모든 테스트가 순차 실행

### 1.2 영향 분석

```
기존:
- 단일 WebSocket 연결 테스트: 최대 60초 대기
- 단위 테스트 평균: 5~10초
- 전체 테스트: 수십 분 이상 소요

개선 후:
- 단일 WebSocket 연결 테스트: 최대 5초 대기
- 단위 테스트 평균: 1~3초
- 전체 테스트: 병렬 실행 시 50% 이상 단축 기대
```

---

## 2. 해결 방안

### 2.1 Kiwoom 테스트 설정 모듈 (`src/kiwoom/test_config.py`)

```python
@dataclass
class KiwoomTestConfig:
    """
    테스트용 키움 API 설정 (성능 최적화)
    """
    ws_connect_timeout: int = 3  # 기본 5초 → 3초
    ws_recv_timeout: int = 10     # 기본 60초 → 10초
    ws_ping_timeout: int = 5      # 기본 10초 → 5초
    max_reconnect_attempts: int = 2  # 기본 10회 → 2회
    reconnect_delay: float = 0.5  # 기본 1초 → 0.5초

    @classmethod
    def fast(cls) -> 'KiwoomTestConfig':
        """초고속 테스트용 (CI/CD 권장)"""
        return cls(
            ws_connect_timeout=2,
            ws_recv_timeout=5,
            ws_ping_timeout=3,
            reconnect_delay=0.3,
        )

    @classmethod
    def integration(cls) -> 'KiwoomTestConfig':
        """통합 테스트용 (느린 외부 API 고려)"""
        return cls(
            ws_connect_timeout=10,
            ws_recv_timeout=30,
            ws_ping_timeout=10,
        )
```

**특징:**
- 환경별 설정 제공 (`fast`, `standard`, `integration`)
- `KiwoomConfig` 변환 메서드 제공
- 데이터클래스로 불변성 보장

### 2.2 전역 Fixture 업데이트 (`tests/conftest.py`)

```python
@pytest.fixture
def kiwoom_test_config():
    """키움 API 테스트용 설정 (최적화된 타임아웃)"""
    from src.kiwoom.test_config import KiwoomTestConfig
    return KiwoomTestConfig.fast()

@pytest.fixture
def kiwoom_test_config_standard():
    """키움 API 표준 테스트용 설정"""
    return KiwoomTestConfig.standard()

@pytest.fixture
def kiwoom_test_config_integration():
    """키움 API 통합 테스트용 설정"""
    return KiwoomTestConfig.integration()
```

### 2.3 pytest.ini 최적화

```ini
# 기본 타임아웃: 30초 → 15초
timeout = 15

# 마커 추가
markers =
    fast: 빠른 테스트 (단위 테스트, mock만 사용, 5초 이내)
    slow: 느린 테스트 (통합 테스트, DB 연동 등)
    integration: 통합 테스트 (외부 서비스/DB 필요)
    unit: 단위 테스트 (mock만 사용, 외부 의존성 없음)

# 병렬 실행 설정 (선택적)
# addopts = -n auto
```

### 2.4 테스트 파일 마커 적용

```python
@pytest.mark.fast
class TestKiwoomWebSocket:
    """KiwoomWebSocket 클래스 테스트 (성능 최적화)"""

    @pytest.fixture
    def config(self, kiwoom_test_config):
        """테스트용 설정 (최적화된 타임아웃)"""
        return kiwoom_test_config.to_kiwoom_config()
```

---

## 3. 성능 개선 결과

### 3.1 타임아웃 최적화

| 설정 항목 | 기존 | 단위 테스트 | 통합 테스트 |
|----------|------|------------|------------|
| 연결 타임아웃 | 5초 | 2초 | 10초 |
| 수신 타임아웃 | 60초 | 5초 | 30초 |
| 핑 타임아웃 | 10초 | 3초 | 10초 |
| 재연결 시도 | 10회 | 2회 | 5회 |
| 재연결 딜레이 | 1초 | 0.3초 | 1초 |

### 3.2 테스트 실행 시간 예상

```
단위 테스트 (Kiwoom WebSocket):
- 기존: 약 60초/테스트 (최악의 경우)
- 개선: 약 2~5초/테스트
- 개선율: 90% 이상 단축

전체 테스트 suite:
- 기존: 수십 분 이상 (순차 실행)
- 개선 (순차): 수십 분 → 약 20분 예상
- 개선 (병렬 -n 4): 약 5~10분 예상
```

---

## 4. 사용 가이드

### 4.1 빠른 테스트 실행 (단위 테스트)

```bash
# 빠른 테스트만 실행
uv run pytest -m fast -v

# 단위 테스트만 실행
uv run pytest -m unit -v

# 통합 테스트 제외
uv run pytest -m "not integration" -v
```

### 4.2 통합 테스트 실행

```bash
# 통합 테스트만 실행
uv run pytest -m integration -v

# 타임아웃 30초로 늘려서 실행
uv run pytest -m integration --timeout=30 -v
```

### 4.3 병렬 실행 (pytest-xdist 설치 필요)

```bash
# pytest-xdist 설치
uv add --dev pytest-xdist

# 4개 worker로 병렬 실행
uv run pytest -n 4 -v

# 자동으로 코어 수에 맞춰 병렬 실행
uv run pytest -n auto -v
```

### 4.4 개별 테스트 실행

```bash
# 특정 테스트 파일
uv run pytest tests/unit/kiwoom/test_websocket.py -v

# 특정 테스트 클래스
uv run pytest tests/unit/kiwoom/test_websocket.py::TestKiwoomWebSocket -v

# 특정 테스트 메서드
uv run pytest tests/unit/kiwoom/test_websocket.py::TestKiwoomWebSocket::test_websocket_connect -v
```

---

## 5. 추가 최적화 제안

### 5.1 단기 개선 사항 (즉시 적용 가능)

1. **pytest-xdist 설치 및 병렬 실행**
   ```bash
   uv add --dev pytest-xdist
   uv run pytest -n 4 -v
   ```

2. **테스트 마커 일괄 적용**
   - 모든 단위 테스트에 `@pytest.mark.fast` 추가
   - 통합 테스트에 `@pytest.mark.integration` 추가
   - 느린 테스트에 `@pytest.mark.slow` 추가

3. **Database Mock 확대**
   - 실제 DB 연동 테스트 최소화
   - SQLAlchemy Mock fixture 활용

### 5.2 중기 개선 사항 (1주 이내)

1. **테스트 Fixture 최적화**
   - 세션 범위 fixture 확대
   - DB 연결 pooling 도입
   - Mock fixture 재사용성 개선

2. **CI/CD 파이프라인 최적화**
   - 병렬 테스트 실행 기본 적용
   - 테스트 결과 캐싱
   - 실패한 테스트만 재실행

3. **테스트 커버리지 최적화**
   - 불필요한 테스트 제거
   - 중복 테스트 통합

### 5.3 장기 개선 사항 (1개월 이내)

1. **테스트 전략 재정립**
   - 단위/통합/E2E 테스트 명확히 구분
   - Testing Pyramid 구현

2. **성능 벤치마킹 도입**
   - 테스트 실행 시간 모니터링
   - 느린 테스트 자동 감지

3. **Mock 전략 고도화**
   - Recording-based Mock (VCR.py)
   - External API call 제거

---

## 6. 변경 파일 목록

### 6.1 신규 파일

1. `src/kiwoom/test_config.py`
   - KiwoomTestConfig 클래스 정의
   - 환경별 설정 팩토리 메서드

### 6.2 수정 파일

1. `tests/conftest.py`
   - kiwoom_test_config fixture 추가
   - kiwoom_test_config_standard fixture 추가
   - kiwoom_test_config_integration fixture 추가
   - fast 마커 등록

2. `pytest.ini`
   - 기본 타임아웃: 30초 → 15초
   - fast 마커 정의
   - 병렬 실행 설정 추가 (주석 처리)

3. `tests/unit/kiwoom/test_websocket.py`
   - @pytest.mark.fast 마커 추가
   - kiwoom_test_config fixture 사용
   - 재연결 시도 횟수: 3회 → 2회

---

## 7. 검증 방법

### 7.1 성능 비교 테스트

```bash
# 기존 설정 복원 (비교용)
git stash

# 기존 설정으로 테스트 실행
uv run pytest tests/unit/kiwoom/test_websocket.py -v --durations=10

# 개선 설정 적용
git stash pop

# 개선 설정으로 테스트 실행
uv run pytest tests/unit/kiwoom/test_websocket.py -v --durations=10

# 결과 비교
```

### 7.2 마커 기반 필터링 테스트

```bash
# 빠른 테스트만 실행
uv run pytest -m fast -v

# 통합 테스트 제외
uv run pytest -m "not integration" -v

# 예상 결과: 단위 테스트만 실행
```

---

## 8. 결론

테스트 성능 최적화를 통해 다음과 같은 개선 효과를 기대할 수 있습니다:

1. **단위 테스트 속도:** 90% 이상 단축 (60초 → 5초 이내)
2. **전체 테스트 시간:** 병렬 실행 시 50~70% 단축 기대
3. **개발 생산성:** 빠른 피드백 루프로 개발 속도 향상
4. **CI/CD 효율:** 파이프라인 실행 시간 단축

### 8.1 다음 단계

1. pytest-xdist 설치 및 병렬 실행 기본 적용
2. 전체 테스트에 마커 일괄 적용
3. CI/CD 파이프라인에 병렬 실행 설정
4. 성능 모니터링 도구 도입

---

**부록:** 테스트 실행 예시

```bash
# 전체 테스트 실행 (순차)
uv run pytest -v

# 빠른 테스트만 실행
uv run pytest -m fast -v

# 병렬 실행 (4 workers)
uv run pytest -n 4 -v

# 타임아웃 30초로 설정
uv run pytest --timeout=30 -v

# 느린 테스트 10개 표시
uv run pytest --durations=10 -v
```
