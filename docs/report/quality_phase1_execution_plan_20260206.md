# Phase 1: 테스트 커버리지 70% 달성 실행 계획

**작성일:** 2026-02-06
**목표:** 전체 커버리지 55% → 70% (예상 1주)
**담당:** Quality Engineer Agent

---

## 실행 개요

### 목표 커버리지
| 모듈 | 현재 | 목표 | 증가 |
|------|------|------|------|
| 전체 | 55% | 70% | **+15%** |
| Kiwoom REST API | 50% | 70% | +20% |
| WebSocket Server | 60% | 75% | +15% |
| Stock Repository | 40% | 70% | +30% |

### 작업 분류
- **P0 (긴급):** 핵심 비즈니스 로직 (7시간)
- **P1 (중요):** 데이터 계층 (4시간)
- **총 예상 시간:** 11시간

---

## Task 1: Kiwoom REST API 고급 테스트 (P0, 4시간)

### 1.1 일봉 차트 역순 정렬 테스트

**파일:** `tests/unit/kiwoom/test_rest_api_chart.py` (신규)

```python
"""
키움 REST API 일봉 차트 조회 테스트
Kiwoom API는 최신 순으로 반환하므로 오름차순 정렬 검증
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from src.kiwoom.base import KiwoomConfig
from src.kiwoom.rest_api import KiwoomRestAPI


class TestStockDailyChart:
    """일봉 차트 조회 테스트"""

    @pytest.fixture
    def api(self):
        config = KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )
        api = KiwoomRestAPI(config)
        api._access_token = "test_token"
        api._token_expires_at = (datetime.now(timezone.utc).timestamp() + 3600)
        return api

    @pytest.mark.asyncio
    async def test_get_stock_daily_chart_sorts_ascending(self, api):
        """일봉 차트 오름차순 정렬 테스트"""
        # Kiwoom API는 최신 순으로 반환 (역순)
        mock_response_data = [
            {"date": "20260206", "open": 80000, "high": 81000, "low": 79500, "close": 80500, "volume": 1000000},
            {"date": "20260205", "open": 79500, "high": 80500, "low": 79000, "close": 80000, "volume": 900000},
            {"date": "20260204", "open": 79000, "high": 80000, "low": 78500, "close": 79500, "volume": 800000},
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            "return_code": 0,
            "return_msg": "OK",
            "result": {"output": mock_response_data}
        })

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await api.get_stock_daily_chart("005930", days=3)

            # 오름차순 정렬 검증 (과거 → 현재)
            assert len(result) == 3
            assert result[0]["date"] == "20260204"  # 가장 오래된 데이터
            assert result[2]["date"] == "20260206"  # 최신 데이터

    @pytest.mark.asyncio
    async def test_get_stock_daily_chart_with_30_days(self, api):
        """30일 일봉 데이터 조회"""
        # 30일치 데이터 생성
        mock_data = []
        for i in range(30):
            date_str = (datetime.now() - timedelta(days=29-i)).strftime("%Y%m%d")
            mock_data.append({
                "date": date_str,
                "open": 80000 + i * 100,
                "high": 81000 + i * 100,
                "low": 79000 + i * 100,
                "close": 80500 + i * 100,
                "volume": 1000000
            })

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            "return_code": 0,
            "result": {"output": mock_data}
        })

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await api.get_stock_daily_chart("005930", days=30)

            assert len(result) == 30
            # 첫 번째가 가장 오래된 날짜
            assert result[0]["date"] < result[-1]["date"]

    @pytest.mark.asyncio
    async def test_get_stock_daily_chart_empty_response(self, api):
        """빈 응답 처리"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            "return_code": 0,
            "result": {"output": []}
        })

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await api.get_stock_daily_chart("005930", days=10)

            assert result == []

    @pytest.mark.asyncio
    async def test_get_stock_daily_chart_api_error(self, api):
        """API 에러 처리"""
        from httpx import HTTPStatusError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=HTTPStatusError("Server Error", request=None, response=None))

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with pytest.raises(HTTPStatusError):
                await api.get_stock_daily_chart("005930", days=10)
```

**예상 커버리지:** +5%

---

### 1.2 토큰 갱신 및 에러 처리 테스트

**파일:** `tests/unit/kiwoom/test_rest_api_auth.py` (추가)

```python
# 기존 test_rest_api.py에 추가할 테스트 케이스

class TestTokenRefreshAndErrorHandling:
    """토큰 갱신 및 에러 처리 테스트"""

    @pytest.fixture
    def config(self):
        return KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
        )

    @pytest.mark.asyncio
    async def test_401_error_triggers_token_refresh(self, config):
        """401 에러 시 자동 토큰 갱신"""
        from httpx import HTTPStatusError

        api = KiwoomRestAPI(config)
        api._access_token = "expired_token"
        api._refresh_token = "valid_refresh_token"

        # 첫 번째 호출: 401 에러
        mock_401_response = Mock()
        mock_401_response.status_code = 401
        mock_401_response.raise_for_status = Mock(
            side_effect=HTTPStatusError("Unauthorized", request=None, response=mock_401_response)
        )

        # 토큰 갱신 응답
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json = Mock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        })

        # 두 번째 호출: 성공
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json = Mock(return_value={"return_code": 0, "result": {}})

        call_count = [0]

        async def mock_post(*args, **kwargs):
            if "/oauth2/token" in args[0]:
                return mock_token_response
            return mock_401_response

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise HTTPStatusError("Unauthorized", request=None, response=mock_401_response)
            return mock_success_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            with patch('httpx.AsyncClient.get', side_effect=mock_get):
                # 첫 번째 실패 후 토큰 갱신 → 재시도 → 성공
                # 이 로직은 실제 API 호출 메서드에서 구현되어야 함
                pass

    @pytest.mark.asyncio
    async def test_network_error_retry(self, config):
        """네트워크 에러 시 재시도"""
        from httpx import RequestError

        api = KiwoomRestAPI(config)
        api._access_token = "test_token"

        call_count = [0]

        async def mock_get_with_retry(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RequestError("Network error")
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"return_code": 0})
            return mock_response

        # 최대 3회 재시도 로직이 구현되어야 함
        with patch('httpx.AsyncClient.get', side_effect=mock_get_with_retry):
            # API 호출이 3번째에 성공해야 함
            pass
```

**예상 커버리지:** +3%

---

## Task 2: WebSocket 구독 시스템 테스트 (P0, 3시간)

### 2.1 ConnectionManager 구독 테스트

**파일:** `tests/unit/websocket/test_connection_manager.py` (신규)

```python
"""
WebSocket ConnectionManager 테스트
연결, 구독, 브로드캐스트 로직 검증
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import WebSocket

from src.websocket.server import ConnectionManager


@pytest.fixture
def connection_manager():
    """ConnectionManager 인스턴스"""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket 연결"""
    ws = Mock(spec=WebSocket)
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestConnectionManagement:
    """연결 관리 테스트"""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self, connection_manager, mock_websocket):
        """연결 추가 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")

        assert "client_1" in connection_manager.active_connections
        assert connection_manager.active_connections["client_1"] == mock_websocket

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, connection_manager, mock_websocket):
        """연결 제거 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")
        connection_manager.disconnect("client_1")

        assert "client_1" not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_with_code_and_reason(self, connection_manager, mock_websocket):
        """종료 코드와 사유 전달 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")

        connection_manager.disconnect("client_1", code=1000, reason="Normal closure")

        assert "client_1" not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_multiple_clients(self, connection_manager):
        """여러 클라이언트 연결 테스트"""
        ws1 = Mock(spec=WebSocket)
        ws2 = Mock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await connection_manager.connect(ws1, "client_1")
        await connection_manager.connect(ws2, "client_2")

        assert len(connection_manager.active_connections) == 2


class TestSubscriptionSystem:
    """구독 시스템 테스트"""

    @pytest.mark.asyncio
    async def test_subscribe_adds_topic(self, connection_manager, mock_websocket):
        """토픽 구독 추가 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")
        connection_manager.subscribe("client_1", "price:005930")

        assert "price:005930" in connection_manager.subscriptions
        assert "client_1" in connection_manager.subscriptions["price:005930"]

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_topic(self, connection_manager, mock_websocket):
        """토픽 구독 취소 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")
        connection_manager.subscribe("client_1", "price:005930")
        connection_manager.unsubscribe("client_1", "price:005930")

        assert "client_1" not in connection_manager.subscriptions["price:005930"]

    @pytest.mark.asyncio
    async def test_client_can_subscribe_multiple_topics(self, connection_manager, mock_websocket):
        """여러 토픽 구독 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")

        connection_manager.subscribe("client_1", "price:005930")
        connection_manager.subscribe("client_1", "signal:005930")
        connection_manager.subscribe("client_1", "price:000270")

        assert len(connection_manager.subscriptions) == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_all_topics(self, connection_manager, mock_websocket):
        """연결 해제 시 모든 구독 제거 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")

        connection_manager.subscribe("client_1", "price:005930")
        connection_manager.subscribe("client_1", "signal:005930")

        connection_manager.disconnect("client_1")

        # disconnect()가 모든 구독에서 클라이언트를 제거하는지 확인
        all_subscribers = set()
        for topic_subscribers in connection_manager.subscriptions.values():
            all_subscribers.update(topic_subscribers)

        assert "client_1" not in all_subscribers


class TestBroadcasting:
    """브로드캐스트 테스트"""

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self, connection_manager):
        """모든 연결에 브로드캐스트 테스트"""
        ws1 = Mock(spec=WebSocket)
        ws2 = Mock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await connection_manager.connect(ws1, "client_1")
        await connection_manager.connect(ws2, "client_2")

        message = {"type": "price", "ticker": "005930", "price": 80000}
        await connection_manager.broadcast(message)

        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_subscribers_only(self, connection_manager):
        """구독자에게만 브로드캐스트 테스트"""
        ws1 = Mock(spec=WebSocket)
        ws2 = Mock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await connection_manager.connect(ws1, "client_1")
        await connection_manager.connect(ws2, "client_2")

        # client_1만 구독
        connection_manager.subscribe("client_1", "price:005930")

        message = {"type": "price", "ticker": "005930"}
        await connection_manager.broadcast_to_topic("price:005930", message)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_personal_message(self, connection_manager, mock_websocket):
        """개인 메시지 전송 테스트"""
        await connection_manager.connect(mock_websocket, "client_1")

        message = {"type": "error", "message": "Invalid request"}
        await connection_manager.send_personal_message(message, "client_1")

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_to_nonexistent_client(self, connection_manager):
        """존재하지 않는 클라이언트 전송 테스트 (에러 없이 False 반환)"""
        result = await connection_manager.send_personal_message(
            {"data": "test"},
            "nonexistent_client"
        )

        assert result is False
```

**예상 커버리지:** +7%

---

## Task 3: WebSocket 하트비트 테스트 (P1, 2시간)

### 3.1 HeartbeatManager 테스트

**파일:** `tests/unit/websocket/test_heartbeat.py` (신규)

```python
"""
WebSocket HeartbeatManager 테스트
하트비트 타임아웃 감지 및 비활성 연결 정리
"""

import pytest
import time
from unittest.mock import Mock
from datetime import datetime, timezone

from src.websocket.server import HeartbeatManager


@pytest.fixture
def heartbeat_manager():
    """HeartbeatManager 인스턴스 (타임아웃 5초)"""
    return HeartbeatManager(timeout=5)


class TestHeartbeatTracking:
    """하트비트 추적 테스트"""

    def test_record_pong_updates_timestamp(self, heartbeat_manager):
        """pong 수신 시간 기록 테스트"""
        client_id = "client_1"

        heartbeat_manager.record_pong(client_id)

        assert client_id in heartbeat_manager.last_pong
        assert isinstance(heartbeat_manager.last_pong[client_id], float)

    def test_record_pong_multiple_clients(self, heartbeat_manager):
        """여러 클라이언트 pong 기록 테스트"""
        clients = ["client_1", "client_2", "client_3"]

        for client in clients:
            heartbeat_manager.record_pong(client)

        assert len(heartbeat_manager.last_pong) == 3

    def test_is_client_alive_within_timeout(self, heartbeat_manager):
        """타임아웃 내 클라이언트 활성 상태 테스트"""
        client_id = "client_1"

        heartbeat_manager.record_pong(client_id)

        # 방금 기록됨 → 활성 상태
        assert heartbeat_manager.is_client_alive(client_id) is True

    def test_is_client_alive_after_timeout(self, heartbeat_manager):
        """타임아웃 경과 후 클라이언트 비활성 상태 테스트"""
        client_id = "client_1"

        # 6초 전에 기록 (타임아웃 5초)
        old_timestamp = time.time() - 6
        heartbeat_manager.last_pong[client_id] = old_timestamp

        assert heartbeat_manager.is_client_alive(client_id) is False

    def test_is_client_alive_unknown_client(self, heartbeat_manager):
        """알 수 없는 클라이언트 활성 확인 (False 반환)"""
        assert heartbeat_manager.is_client_alive("unknown_client") is False


class TestTimeoutDetection:
    """타임아웃 감지 테스트"""

    def test_get_inactive_clients_returns_timed_out(self, heartbeat_manager):
        """비활성 클라이언트 목록 반환 테스트"""
        # 활성 클라이언트
        heartbeat_manager.record_pong("client_1")

        # 비활성 클라이언트 (6초 전)
        old_timestamp = time.time() - 6
        heartbeat_manager.last_pong["client_2"] = old_timestamp

        inactive = heartbeat_manager.get_inactive_clients()

        assert "client_2" in inactive
        assert "client_1" not in inactive

    def test_remove_client_deletes_timestamp(self, heartbeat_manager):
        """클라이언트 제거 테스트"""
        client_id = "client_1"
        heartbeat_manager.record_pong(client_id)

        heartbeat_manager.remove_client(client_id)

        assert client_id not in heartbeat_manager.last_pong


class TestHeartbeatIntegration:
    """하트비트 통합 테스트"""

    @pytest.mark.asyncio
    async def test_ping_all_connected_clients(self):
        """모든 연결된 클라이언트 ping 전송 테스트"""
        from src.websocket.server import ConnectionManager
        from unittest.mock import AsyncMock

        manager = ConnectionManager()
        heartbeat = HeartbeatManager(timeout=5)

        ws1 = Mock()
        ws2 = Mock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, "client_1")
        await manager.connect(ws2, "client_2")

        # ping 전송
        await heartbeat.ping_all(manager)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

        ping_message = ws1.send_json.call_args[0][0]
        assert ping_message["type"] == "ping"
```

**예상 커버리지:** +4%

---

## Task 4: Stock Repository 고급 테스트 (P1, 2시간)

### 4.1 검색 및 페이지네이션 테스트

**파일:** `tests/unit/repositories/test_stock_repository_advanced.py` (기존 파일에 추가)

```python
# 기존 test_stock_repository.py에 추가

class TestStockRepositoryAdvanced:
    """Stock Repository 고급 기능 테스트"""

    @pytest.fixture
    def db_session(self):
        from src.database.session import Base
        from src.database.models.stock import Stock

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        TestingSessionLocal = sessionmaker(bind=engine)
        session = TestingSessionLocal()

        # 샘플 데이터 추가
        stocks = [
            Stock(ticker="005930", name="삼성전자", market="KOSPI", sector="전자"),
            Stock(ticker="005935", name="삼성전자우", market="KOSPI", sector="전자"),
            Stock(ticker="000270", name="기아", market="KOSPI", sector="자동차"),
            Stock(ticker="035420", name="NAVER", market="KOSPI", sector="IT"),
            Stock(ticker="066570", name="LG전자", market="KOSDAQ", sector="전자"),
        ]
        for stock in stocks:
            session.add(stock)
        session.commit()

        yield session
        session.close()

    @pytest.fixture
    def repo(self, db_session):
        from src.repositories.stock_repository import StockRepository
        return StockRepository(db_session)

    def test_search_by_name_partial_match(self, repo):
        """이름 부분 일치 검색"""
        results = repo.search("삼성")

        assert len(results) == 2
        tickers = {s.ticker for s in results}
        assert "005930" in tickers
        assert "005935" in tickers

    def test_search_by_ticker(self, repo):
        """티커 검색"""
        results = repo.search("005930")

        assert len(results) == 1
        assert results[0].ticker == "005930"
        assert results[0].name == "삼성전자"

    def test_search_case_insensitive(self, repo):
        """대소문자 구분 없는 검색"""
        results = repo.search("naver")

        assert len(results) == 1
        assert results[0].name == "NAVER"

    def test_search_empty_string_returns_all(self, repo):
        """빈 문자열 검색 → 전체 반환"""
        results = repo.search("")

        assert len(results) == 5

    def test_list_all_with_market_filter_kospi(self, repo):
        """시장 필터링 (KOSPI)"""
        results = repo.list_all(market="KOSPI")

        assert len(results) == 4
        assert all(s.market == "KOSPI" for s in results)

    def test_list_all_with_market_filter_kosdaq(self, repo):
        """시장 필터링 (KOSDAQ)"""
        results = repo.list_all(market="KOSDAQ")

        assert len(results) == 1
        assert results[0].ticker == "066570"

    def test_list_all_with_sector_filter(self, repo):
        """섹터 필터링"""
        results = repo.list_all(sector="전자")

        assert len(results) == 3
        tickers = {s.ticker for s in results}
        assert "005930" in tickers
        assert "005935" in tickers
        assert "066570" in tickers

    def test_list_all_with_limit(self, repo):
        """limit 파라미터 테스트"""
        results = repo.list_all(limit=2)

        assert len(results) == 2

    def test_create_if_not_exists_new_stock(self, repo):
        """신규 종목 생성"""
        stock = repo.create_if_not_exists(
            ticker="096770",
            name="SK이노베이션",
            market="KOSPI"
        )

        assert stock.id is not None
        assert stock.ticker == "096770"

    def test_create_if_not_exists_existing_stock(self, repo):
        """기존 종목 존재 시 반환만"""
        existing = repo.get_by_ticker("005930")

        stock = repo.create_if_not_exists(
            ticker="005930",
            name="삼성전자",
            market="KOSPI"
        )

        assert stock.id == existing.id

    def test_get_or_create_multiple_sequential(self, repo):
        """연속 호출 시 안정성 테스트"""
        # 첫 번째 호출: 생성
        stock1 = repo.get_or_create("105560", "KB금융", "KOSPI")
        assert stock1.id is not None

        # 두 번째 호출: 기존 반환
        stock2 = repo.get_or_create("105560", "KB금융", "KOSPI")
        assert stock1.id == stock2.id
```

**예상 커버리지:** +5%

---

## 실행 체크리스트

### Day 1-2: Kiwoom REST API (4시간)
- [ ] 일봉 차트 역순 정렬 테스트 작성
- [ ] 토큰 갱신 테스트 작성
- [ ] 에러 처리 및 재시도 테스트 작성
- [ ] 커버리지 확인 (목표: 70%)

### Day 3-4: WebSocket 구독 시스템 (3시간)
- [ ] ConnectionManager 연결/구독 테스트 작성
- [ ] 브로드캐스트 필터링 테스트 작성
- [ ] 다중 클라이언트 시나리오 테스트
- [ ] 커버리지 확인 (목표: 75%)

### Day 5: WebSocket 하트비트 (2시간)
- [ ] HeartbeatManager 타임아웃 테스트 작성
- [ ] 비활성 연결 감지 테스트
- [ ] 통합 테스트 작성

### Day 6-7: Stock Repository (2시간)
- [ ] 검색 기능 고급 테스트 작성
- [ ] 페이지네이션 테스트 작성
- [ ] 필터링 복합 쿼리 테스트

---

## 검증 방법

### 커버리지 확인
```bash
# 전체 커버리지
uv run pytest --cov=./src --cov=./services --cov-report=term-missing

# HTML 리포트
uv run pytest --cov=./src --cov=./services --cov-report=html
open htmlcov/index.html
```

### 특정 모듈 커버리지
```bash
# Kiwoom REST API
uv run pytest tests/unit/kiwoom/ --cov=src/kiwoom/rest_api --cov-report=term-missing

# WebSocket
uv run pytest tests/unit/websocket/ --cov=src/websocket/server --cov-report=term-missing

# Stock Repository
uv run pytest tests/unit/repositories/test_stock_repository.py --cov=src/repositories/stock_repository --cov-report=term-missing
```

### 테스트 실행 시간
```bash
# 빠른 테스트 (단위 테스트만)
uv run pytest tests/unit/ -m "not slow" --durations=10

# 전체 테스트
uv run pytest --durations=20
```

---

## 성공 기준

- [ ] 전체 커버리지 70% 이상 달성
- [ ] Kiwoom REST API 70% 커버리지
- [ ] WebSocket Server 75% 커버리지
- [ ] Stock Repository 70% 커버리지
- [ ] 모든 새로운 테스트 통과
- [ ] 테스트 실행 시간 < 30초 (단위 테스트)
- [ ] CI/CD 파이프라인 통과

---

*계획 작성: Quality Engineer Agent*
*승인: ralph-stock-creator 팀*
*다음 리뷰: Phase 1 완료 후*
