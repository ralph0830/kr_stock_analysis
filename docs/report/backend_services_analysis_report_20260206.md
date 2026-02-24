# 백엔드 서비스 분석 보고서

**작성일:** 2026-02-06
**분석 범위:** API Gateway, VCP Scanner, Signal Engine, Chatbot, Daytrading Scanner
**작성자:** Claude (Python Expert)

---

## 1. 서비스별 현재 상태

### 1.1 API Gateway (Port 5111)

**파일:** `/services/api_gateway/main.py`

#### 주요 기능
- 마이크로서비스 프록시 (Service Registry 기반)
- WebSocket 서버 연동
- Kiwoom REST API 연동
- 통합 API 엔드포인트 제공

#### API 엔드포인트 구조

| 카테고리 | 엔드포인트 | 설명 |
|----------|-----------|------|
| Health | `/health`, `/api/health` | 헬스 체크 |
| Signals | `/api/kr/signals` | VCP 시그널 조회 (VCP Scanner 프록시) |
| Signals | `/api/kr/jongga-v2/latest` | 종가베팅 V2 시그널 (Signal Engine 프록시) |
| Market | `/api/kr/market-gate` | Market Gate 상태 조회 |
| Stocks | `/api/kr/stocks/{ticker}` | 종목 상세 정보 |
| Stocks | `/api/kr/stocks/{ticker}/chart` | 차트 데이터 (OHLCV) |
| Stocks | `/api/kr/stocks/{ticker}/flow` | 수급 데이터 (외국인/기관) |
| Stocks | `/api/kr/stocks/{ticker}/signals` | 종목 시그널 히스토리 |
| Realtime | `/api/kr/realtime-prices` | 실시간 가격 일괄 조회 |
| Metrics | `/metrics`, `/api/metrics` | Prometheus 메트릭 |
| Internal | `/internal/prices` | 실시간 가격 캐시 (내부용) |

#### 데이터베이스 연동
- **세션 관리:** `get_db_session()` (Dependency Injection), `get_db_session_sync()` (Context Manager)
- **주요 의존 모델:** `MarketStatus`, `DailyPrice`, `Stock`, `Signal`
- **Repository 사용:** `StockRepository`, `SignalRepository`, `BacktestRepository`

#### 의존성
- `service_registry.py`: 서비스 디스커버리
- `src/websocket/server.py`: WebSocket 연결 관리
- `src/kiwoom/rest_api.py`: Kiwoom REST API 클라이언트
- `src/middleware/`: 요청 로깅, 메트릭, Request ID 미들웨어

---

### 1.2 VCP Scanner (Port 5112)

**파일:** `/services/vcp_scanner/main.py`

#### 주요 기능
- VCP (Volatility Contraction Pattern) 패턴 스캐닝
- SmartMoney 수급 분석 (외국인/기관 5일 순매수)
- DB 저장 및 WebSocket 브로드캐스트

#### API 엔드포인트 구조

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 헬스 체크 |
| `/signals` | GET | 활성 VCP 시그널 조회 (DB에서) |
| `/scan` | POST | VCP 패턴 스캔 실행 |
| `/analyze/{ticker}` | GET | 단일 종목 VCP 분석 |

#### 데이터베이스 연동
- **세션 관리:** `get_db_session_sync()` (Context Manager)
- **저장 모델:** `Signal` (signal_type="VCP")
- **Repository:** `VCPSignalRepository`

#### 등급 계산 로직
```python
def _get_grade_from_score(total_score: float) -> str:
    if total_score >= 80: return "S"  # 20% 목표수익률
    elif total_score >= 65: return "A"  # 15%
    elif total_score >= 50: return "B"  # 10%
    return "C"  # 5%
```

---

### 1.3 Signal Engine (Port 5113)

**파일:** `/services/signal_engine/main.py`

#### 주요 기능
- 종가베팅 V2 시그널 생성 (12점 스코어링)
- 뉴스, 거래량, 차트, 캔들, 기간, 수급 점수 계산

#### API 엔드포인트 구조

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 헬스 체크 |
| `/signals/latest` | GET | 최신 종가베팅 시그널 조회 (DB에서) |
| `/generate` | POST | 시그널 생성 실행 |
| `/analyze` | POST | 단일 종목 시그널 분석 |

#### 데이터베이스 연동
- **세션 관리:** `get_db_session_sync()` (Context Manager)
- **저장 모델:** `Signal` (signal_type="JONGGA_V2")
- **점수 저장 필드:** `news_score`, `volume_score`, `chart_score`, `candle_score`, `period_score`, `supply_score`

---

### 1.4 Chatbot (Port 5114)

**파일:** `/services/chatbot/main.py`

#### 주요 기능
- RAG 기반 AI 챗봇
- 세션 기반 대화 관리 (Redis)
- Gemini LLM 연동
- 종목 추천 서비스

#### API 엔드포인트 구조

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 헬스 체크 |
| `/chat` | POST | 채팅 요청 처리 |
| `/context` | GET | 세션 대화 기록 조회 |
| `/context` | POST | 질문에 대한 컨텍스트 검색 |
| `/context/{session_id}` | DELETE | 세션 삭제 |
| `/session/{session_id}` | GET/DELETE | 세션 관리 |
| `/recommendations` | GET | 종목 추천 조회 |

#### 의존성
- `session_manager.py`: Redis 기반 세션 관리
- `retriever.py`: RAG 컨텍스트 검색
- `llm_client.py`: Gemini API 클라이언트
- `recommender.py`: VCP/종가베팅 기반 추천

---

### 1.5 Daytrading Scanner (Port 5115)

**파일:** `/services/daytrading_scanner/main.py`

#### 주요 기능
- 단타 매매 기회 스캐닝 (7가지 체크리스트)
- 실시간 가격 연동
- WebSocket 브로드캐스트

#### API 엔드포인트 구조

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 헬스 체크 |
| `/api/daytrading/scan` | POST | 장중 단타 후보 스캔 |
| `/api/daytrading/signals` | GET | 활성 단타 매수 신호 조회 |
| `/api/daytrading/analyze` | POST | 종목별 단타 점수 분석 |

#### 체크리스트 항목
1. 거래량 폭증
2. 모멘텀 돌파
3. 박스권 탈출
4. 5일선 위
5. 기관 매수
6. 낙폭 과대
7. 섹터 모멘텀

---

## 2. 발견된 이슈 목록

### 2.1 Critical (즉시 조치 필요)

#### 이슈 #1: WebSocket HTTP/2 Upgrade 문제 해결 필요

**위치:** `src/websocket/server.py`, Frontend WebSocket 연결

**현상:**
- Nginx Proxy Manager를 통한 Reverse Proxy 환경에서 WebSocket 연결 실패
- HTTP/2 → WebSocket Upgrade 시 문제 발생

**해결 방안:**
```nginx
# NPM Custom Nginx Configuration 추가
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;

# Cache 비활성화 (실시간 데이터)
add_header Cache-Control "no-store, no-cache, must-revalidate";
add_header Pragma "no-cache";
```

**검증 결과:** ✅ 해결됨

---

#### 이슈 #2: Repository Pattern 미사용으로 인한 중복 코드

**위치:** `services/vcp_scanner/main.py`, `services/signal_engine/main.py`

**현상:**
- DB 직접 쿼리로 인한 Repository Layer 우회
- `save_vcp_signals_to_db()`, `save_jongga_signals_to_db()` 함수에서 직접 SQLAlchemy 사용

**현재 코드:**
```python
# VCP Scanner (main.py:194-199)
db.execute(
    delete(Signal).where(
        Signal.signal_type == "VCP",
        Signal.signal_date == signal_date
    )
)
```

**개선 제안:**
```python
# Repository Pattern 적용
class SignalRepository:
    def delete_by_type_and_date(self, signal_type: str, signal_date: date) -> int:
        """시그널 타입과 날짜로 삭제"""
        result = self.db.execute(
            delete(self.model)
            .where(
                self.model.signal_type == signal_type,
                self.model.signal_date == signal_date
            )
        )
        return result.rowcount

    def upsert_signals(self, signals: List[Signal]) -> int:
        """시그널 일괄 저장 (갱신 로직 포함)"""
        saved_count = 0
        for signal in signals:
            # 기존 시그너 확인 및 업데이트 또는 생성
            # ...
        return saved_count
```

---

#### 이슈 #3: 에러 처리가 일관되지 않음

**위치:** 전체 서비스

**현상:**
- 일부 서비스에서 에러 발생 시 빈 리스트 반환 vs HTTPException 발생 혼재
- Chatbot `/recommendations` 엔드포인트: 에러 시 빈 리스트 반환 (서비스 중단 방지)

**현재 코드:**
```python
# chatbot/main.py:436-439
except Exception as e:
    logger.error(f"추천 종목 조회 실패: {e}")
    return []  # 빈 리스트 반환 (서비스 중단 방지)
```

**개선 제안:**
```python
# 표준 에러 응답 모델 도입
class ErrorResponse(BaseModel):
    status: str = "error"
    code: int
    detail: str
    path: Optional[str] = None

# 일관된 에러 처리
@app.exception_handler(ServiceUnavailableException)
async def service_unavailable_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "code": 503,
            "detail": f"Service temporarily unavailable: {exc.service_name}",
            "retry_after": exc.retry_after_seconds,
        }
    )
```

---

### 2.2 High (조기 개선 필요)

#### 이슈 #4: 데이터베이스 세션 관리 혼재

**위치:** 전체 서비스

**현상:**
- `get_db_session()` (Dependency Injection)와 `get_db_session_sync()` (Context Manager) 혼용
- API Gateway에서 두 방식 모두 사용

**개선 제안:**
```python
# 통일된 세션 관리 방식 도입
from src.database.session import get_db_session

# FastAPI Endpoint: Dependency Injection 사용
@app.get("/api/endpoint")
async def get_endpoint(db: Session = Depends(get_db_session)):
    repo = StockRepository(db)
    return repo.get_all()

# Background Task/Celery: Context Manager 사용
def background_task():
    with get_db_session_sync() as db:
        repo = StockRepository(db)
        return repo.get_all()
```

---

#### 이슈 #5: Magic Number 사용

**위치:** 각 서비스의 등급 계산, 점수 계산

**현상:**
- 하드코딩된 등급 기준값 (80, 65, 50)
- 목표수익률 하드코딩 (0.20, 0.15, 0.10, 0.05)

**개선 제안:**
```python
# config/constants.py로 이동
from dataclasses import dataclass
from typing import Dict

@dataclass
class GradeConfig:
    """등급별 설정"""
    s_min_score: int = 80
    a_min_score: int = 65
    b_min_score: int = 50

    target_profit_rates: Dict[str, float] = None

    def __post_init__(self):
        if self.target_profit_rates is None:
            self.target_profit_rates = {
                "S": 0.20,
                "A": 0.15,
                "B": 0.10,
                "C": 0.05,
            }

    def get_grade(self, score: float) -> str:
        """점수에 따른 등급 반환"""
        if score >= self.s_min_score:
            return "S"
        elif score >= self.a_min_score:
            return "A"
        elif score >= self.b_min_score:
            return "B"
        return "C"

# 전역 설정 인스턴스
GRADE_CONFIG = GradeConfig()
```

---

#### 이슈 #6: 직접 import 대신 Service Registry 활용 부족

**위치:** `services/api_gateway/main.py`

**현상:**
- 일부 서비스에서 직접 httpx로 외부 호출
- Service Registry를 통한 헬스 체크 후 호출이 필요

**개선 제안:**
```python
# 현재: 직접 httpx 호출
async with httpx.AsyncClient() as client:
    response = await client.get(url, timeout=10.0)

# 개선: Service Registry 활용
from services.api_gateway.service_registry import get_registry
from src.utils.http_client import resilient_http_client

registry = get_registry()
service = registry.get_service("vcp-scanner")
if not service:
    raise HTTPException(status_code=503, detail="VCP Scanner not available")

async with resilient_http_client() as client:
    response = await client.get(
        f"{service['url']}/signals",
        timeout=service.get('timeout', 10.0)
    )
```

---

### 2.3 Medium/Low (개선 권장)

#### 이슈 #7: 로깅 수준 통일 필요

**위치:** 전체 서비스

**현상:**
- `print()`와 `logger` 혼용
- 일부 서비스에서 `logging.basicConfig()` 중복 호출

**개선 제안:**
```python
# src/utils/logging_config.py로 중앙화
import logging
import sys
from datetime import datetime

class CustomFormatter(logging.Formatter):
    """커스텀 로그 포맷터"""

    def format(self, record):
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_color = {
            "INFO": "\033[92m",    # GREEN
            "WARNING": "\033[93m", # YELLOW
            "ERROR": "\033[91m",   # RED
            "DEBUG": "\033[94m",   # BLUE
        }.get(record.levelname, "")
        reset = "\033[0m"

        return f"{log_time} [{level_color}{record.levelname}{reset}] {record.name}: {record.getMessage()}"

def setup_logging(service_name: str, level: str = "INFO"):
    """로깅 설정 초기화"""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomFormatter())
    logger.addHandler(handler)

    return logger
```

---

#### 이슈 #8: 테스트 커버리지 부족

**위치:** 각 서비스

**현상:**
- E2E 테스트만 존재 (`tests/e2e/test_service_health.py`)
- 단위 테스트 부족

**개선 제안:**
```python
# tests/unit/services/test_vcp_scanner.py
import pytest
from unittest.mock import Mock, patch
from services.vcp_scanner.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    """헬스 체크 엔드포인트 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "vcp-scanner"

@patch("services.vcp_scanner.main.VCPAnalyzer")
def test_scan_vcp_patterns(mock_analyzer_class, client):
    """VCP 스캔 엔드포인트 테스트"""
    # Mock 설정
    mock_analyzer = Mock()
    mock_analyzer.scan_market = AsyncMock(return_value=[])
    mock_analyzer_class.return_value = mock_analyzer

    response = client.post("/scan", json={"market": "KOSPI", "top_n": 10})
    assert response.status_code == 200
```

---

## 3. WebSocket 문제 해결 방안

### 3.1 원인 분석

**문제:** HTTP/2 → WebSocket Upgrade 실패

**원인:**
1. Nginx Proxy Manager에서 HTTP/2 사용 시 WebSocket Upgrade 헤더 처리 문제
2. `proxy_set_header` 설정 누락
3. Cache 설정으로 인한 WebSocket 연결 유지 실패

### 3.2 적용한 해결책

#### Nginx 설정 (NPM Custom Configuration)
```nginx
# WebSocket Headers
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;

# Cache 비활성화 (실시간 데이터)
add_header Cache-Control "no-store, no-cache, must-revalidate";
add_header Pragma "no-cache";
```

#### WebSocket Route 등록
```python
# api_gateway/main.py
if WEBSOCKET_AVAILABLE:
    app.include_router(websocket_router)

# src/websocket/routes.py
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_json()
            # 메시지 처리
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
```

### 3.3 검증 결과

| 항목 | 결과 |
|------|------|
| WebSocket 연결 | ✅ 성공 |
| 메시지 송수신 | ✅ 성공 |
| 재연결 처리 | ✅ 성공 |
| Pub/Sub 브로드캐스트 | ✅ 성공 |

---

## 4. 개선 우선순위

### Phase 1 (즉시 실행): Critical 이슈

| 작업 | 예상 시간 | 담당자 |
|------|----------|--------|
| WebSocket Nginx 설정 완료 | 완료됨 | DevOps |
| Repository Pattern 표준화 | 4시간 | Backend |
| 에러 처리 일관화 | 3시간 | Backend |

### Phase 2 (1-2주 내): High 이슈

| 작업 | 예상 시간 | 담당자 |
|------|----------|--------|
| DB 세션 관리 통합 | 2시간 | Backend |
| Magic Number 제거 (Config 분리) | 2시간 | Backend |
| Service Registry 활용 확대 | 3시간 | Backend |
| 테스트 커버리지 70% 목표 | 8시간 | QA |

### Phase 3 (2-4주 내): Medium/Low 이슈

| 작업 | 예상 시간 | 담당자 |
|------|----------|--------|
| 로깅 시스템 중앙화 | 2시간 | Backend |
| API 문서 자동화 (Redoc/OpenAPI) | 4시간 | Backend |
| 모니터링 대시보드 강화 | 6시간 | DevOps |
| 성능 최적화 (캐싱, 쿼리 튜닝) | 8시간 | Backend |

---

## 5. 구체적 개선 제안

### 5.1 Repository Pattern 표준화

**Base Repository 추상화:**
```python
# src/repositories/base.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType], ABC):
    """베이스 Repository 추상 클래스"""

    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def get(self, id: int) -> Optional[ModelType]:
        """ID로 조회"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, limit: int = 100) -> List[ModelType]:
        """전체 조회"""
        return self.db.query(self.model).limit(limit).all()

    def create(self, obj: ModelType) -> ModelType:
        """생성"""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        """업데이트"""
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int) -> bool:
        """삭제"""
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False
```

**Signal Repository 구현:**
```python
# src/repositories/signal_repository.py
from src.repositories.base import BaseRepository
from src.database.models import Signal
from datetime import date
from typing import List, Optional

class SignalRepository(BaseRepository[Signal]):
    """시그널 Repository"""

    def get_by_type_and_date(
        self, signal_type: str, signal_date: date
    ) -> List[Signal]:
        """시그널 타입과 날짜로 조회"""
        return (
            self.db.query(self.model)
            .filter(
                self.model.signal_type == signal_type,
                self.model.signal_date == signal_date
            )
            .all()
        )

    def delete_by_type_and_date(
        self, signal_type: str, signal_date: date
    ) -> int:
        """시그널 타입과 날짜로 삭제"""
        from sqlalchemy import delete
        result = self.db.execute(
            delete(self.model)
            .where(
                self.model.signal_type == signal_type,
                self.model.signal_date == signal_date
            )
        )
        self.db.commit()
        return result.rowcount

    def upsert_signals(
        self, signals: List[Signal], signal_type: str, signal_date: date
    ) -> int:
        """시그널 일괄 저장 (기존 데이터 삭제 후 생성)"""
        # 기존 시그널 삭제
        self.delete_by_type_and_date(signal_type, signal_date)

        # 새 시그널 저장
        for signal in signals:
            signal.signal_type = signal_type
            signal.signal_date = signal_date
            self.db.add(signal)

        self.db.commit()
        return len(signals)

    def get_active_signals(
        self, signal_type: Optional[str] = None, limit: int = 20
    ) -> List[Signal]:
        """활성 시그널 조회"""
        query = (
            self.db.query(self.model)
            .filter(self.model.status == "OPEN")
        )

        if signal_type:
            query = query.filter(self.model.signal_type == signal_type)

        return query.order_by(self.model.score.desc()).limit(limit).all()
```

### 5.2 에러 처리 개선안

**커스텀 예외 클래스:**
```python
# src/exceptions.py
class RalphStockException(Exception):
    """베이스 예외 클래스"""
    def __init__(self, detail: str, code: int = 500):
        self.detail = detail
        self.code = code
        super().__init__(detail)

class ServiceUnavailableException(RalphStockException):
    """서비스 사용 불가 예외"""
    def __init__(self, service_name: str, retry_after: int = 30):
        super().__init__(
            detail=f"Service {service_name} is unavailable",
            code=503
        )
        self.service_name = service_name
        self.retry_after_seconds = retry_after

class DatabaseException(RalphStockException):
    """데이터베이스 예외"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, code=500)

class ValidationException(RalphStockException):
    """검증 예외"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, code=422)
```

**예외 핸들러 등록:**
```python
# services/api_gateway/main.py
from src.exceptions import (
    ServiceUnavailableException,
    DatabaseException,
    ValidationException,
)

@app.exception_handler(ServiceUnavailableException)
async def service_unavailable_handler(request, exc: ServiceUnavailableException):
    return JSONResponse(
        status_code=exc.code,
        content={
            "status": "error",
            "code": exc.code,
            "detail": exc.detail,
            "service": exc.service_name,
            "retry_after": exc.retry_after_seconds,
        }
    )

@app.exception_handler(DatabaseException)
async def database_exception_handler(request, exc: DatabaseException):
    logger.error(f"Database error: {exc.detail}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "detail": "Database error occurred" if not DEBUG else exc.detail,
        }
    )
```

### 5.3 HTTP Client 래퍼 (서비스 간 통신)

```python
# src/utils/http_client.py
import httpx
from typing import Optional, Dict, Any
from src.exceptions import ServiceUnavailableException
import asyncio

class ResilientHttpClient:
    """회복 탄력적 HTTP 클라이언트 (재시도, 타임아웃 포함)"""

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def get(
        self, url: str, service_name: str, **kwargs
    ) -> Dict[str, Any]:
        """GET 요청 (재시도 포함)"""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, **kwargs)
                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    raise ServiceUnavailableException(
                        service_name=service_name,
                        retry_after=int(self.retry_delay * (attempt + 1))
                    )
                await asyncio.sleep(self.retry_delay * (attempt + 1))

            except httpx.RequestError:
                if attempt == self.max_retries - 1:
                    raise ServiceUnavailableException(service_name=service_name)
                await asyncio.sleep(self.retry_delay)

    async def post(self, url: str, service_name: str, **kwargs) -> Dict[str, Any]:
        """POST 요청 (재시도 포함)"""
        # GET과 동일한 재시도 로직
        ...
```

---

## 6. 요약

### 6.1 현황 요약

| 항목 | 현황 |
|------|------|
| **서비스 수** | 5개 (Gateway, VCP, Signal, Chatbot, Daytrading) |
| **API 엔드포인트** | 50+ |
| **WebSocket** | ✅ 동작 (Nginx 설정 완료) |
| **Repository Pattern** | 부분 적용 (개선 필요) |
| **에러 처리** | 일관성 부족 |
| **테스트 커버리지** | E2E 위주 (단위 테스트 부족) |

### 6.2 주요 성과

1. **WebSocket 연결 안정화:** Nginx 설정으로 HTTP/2 → WebSocket Upgrade 문제 해결
2. **마이크로서비스 아키텍처:** Service Registry 기반 서비스 디스커버리 구현
3. **실시간 데이터 브로드캐스트:** Kiwoom API + DB 폴백 백엔 구현

### 6.3 다음 단계

1. **Repository Pattern 전면 도입** (4시간)
2. **에러 처리 표준화** (3시간)
3. **단위 테스트 작성** (8시간)
4. **API 문서 자동화** (4시간)

---

**보고서 종료**
