# 테스트 가이드

**버전:** 1.0.0
**최종 수정:** 2026-02-03

---

## 목차

1. [개요](#1-개요)
2. [pytest 설정](#2-pytest-설정)
3. [테스트 실행](#3-테스트-실행)
4. [커버리지](#4-커버리지)
5. [테스트 구조](#5-테스트-구조)

---

## 1. 개요

이 프로젝트는 pytest를 사용하여 단위/통합/E2E 테스트를 관리합니다.

### 1.1 테스트 통계

- **전체 테스트:** 622 passed
- **스킵:** 20 skipped
- **커버리지:** 목표 80%+

---

## 2. pytest 설정

### 2.1 설정 파일

```ini
# pyproject.toml 또는 pytest.ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

### 2.2 fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.session import Base

@pytest.fixture
def test_db():
    """테스트용 DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    yield session
    session.close()
```

---

## 3. 테스트 실행

### 3.1 전체 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 상세 출력
pytest tests/ -vv

# 에러가 멈추면 멈춤
pytest tests/ -x
```

### 3.2 특정 테스트만 실행

```bash
# 단위 테스트만 (인프라 제외)
pytest tests/unit/ -v

# 통합 테스트만
pytest tests/integration/ -v

# E2E 테스트만
pytest tests/e2e/ -v

# 특정 파일
pytest tests/unit/api_gateway/test_stocks_routes.py -v

# 특정 테스트 함수
pytest tests/unit/test_stock_repository.py::test_get_by_ticker -v
```

### 3.3 마커로 필터링

```bash
# slow 마커가 있는 테스트 제외
pytest tests/ -v -m "not slow"

# smoke 테스트만
pytest tests/ -v -m "smoke"

# 여러 마커
pytest tests/ -v -m "unit and not slow"
```

---

## 4. 커버리지

### 4.1 커버리지 실행

```bash
# HTML 리포트 생성
pytest tests/ --cov=src --cov-report=html

# 터미널 리포트
pytest tests/ --cov=src --cov-report=term-missing

# 특정 모듈만
pytest tests/unit/repositories/ --cov=src/repositories
```

### 4.2 커버리지 확인

```bash
# HTML 리포트 열기
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## 5. 테스트 구조

```
tests/
├── unit/                  # 단위 테스트 (인프라 X)
│   ├── api_gateway/       # API Gateway 라우터 테스트
│   ├── collectors/        # 데이터 수집기 테스트
│   ├── repositories/      # Repository 테스트
│   └── websocket/         # WebSocket 테스트
├── integration/           # 통합 테스트 (DB 포함)
│   └── api/               # API 통합 테스트
├── e2e/                   # E2E 테스트
│   └── test_service_health.py
└── conftest.py            # 공통 fixtures
```

---

## 관련 문서

- [Open Architecture](OPEN_ARCHITECTURE.md) - 전체 아키텍처
