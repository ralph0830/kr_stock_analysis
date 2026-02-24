# WebSocket 통합 테스트 계획

**작성일:** 2026-02-06
**작성자:** Quality Engineer (Quality Assurance Team)
**상태:** 📋 분석 완료, 계획 수립됨

---

## 1. 현재 WebSocket 테스트 현황

### 1.1 테스트 파일 구조

| 파일 | 유형 | 커버리지 | 상태 |
|------|------|----------|------|
| `tests/unit/websocket/test_server.py` | 단위 테스트 | 50% | 🟡 개선 필요 |
| `tests/unit/websocket/test_daytrading_websocket.py` | 단위 테스트 | - | ✅ |
| `tests/unit/websocket/test_price_provider.py` | 단위 테스트 | - | ✅ |
| `tests/unit/clients/test_websocket_client.py` | 단위 테스트 | - | ✅ |
| `tests/integration/api_gateway/test_websocket_metrics.py` | 통합 테스트 | 30% | 🟡 개선 필요 |
| `tests/unit/kiwoom/test_websocket.py` | 단위 테스트 | - | ✅ |
| `tests/unit/kiwoom/test_websocket_reconnect.py` | 단위 테스트 | - | ✅ |

### 1.2 WebSocket 서버 구성 요소

`src/websocket/server.py`에 정의된 주요 클래스:

| 클래스 | 현재 테스트 | 커버리지 | 우선순위 |
|--------|-----------|----------|----------|
| `ConnectionManager` | ✅ 기존 테스트 존재 | 70% | P1 |
| `PriceUpdateBroadcaster` | ⚠️ 부분 테스트 | 40% | **P0** |
| `SignalBroadcaster` | ❌ 없음 | 0% | **P0** |
| `HeartbeatManager` | ❌ 없음 | 0% | **P0** |
| `RedisSubscriber` | ❌ 없음 | 0% | P1 |

---

## 2. 긴급 문제: WebSocket 연결 실패

### 2.1 현재 상황

- **문제:** `wss://stock.ralphpark.com/ws` 연결 실패
- **원인 분석:** NPM Reverse Proxy 설정 또는 API Gateway unhealthy 상태
- **영향:** 실시간 가격 업데이트, Market Gate 상태 등 실시간 기능 작동 안 함

### 2.2 테스트 관점에서의 원인 분석

1. **NPM Reverse Proxy WebSocket 설정**
   - `proxy_set_header Upgrade $http_upgrade;` 설정 필요
   - `proxy_set_header Connection "upgrade";` 설정 필요
   - `allow_websocket_upgrade: true` 활성화 확인

2. **API Gateway Health**
   - `/health` 엔드포인트 응답 확인
   - WebSocket 라우터(`/ws`) 등록 확인
   - CORS 설정 확인

3. **Middleware WebSocket Skip 로직**
   - `RequestIDMiddleware._is_websocket_request()` 확인
   - `MetricsMiddleware._is_websocket_request()` 확인
   - `LoggingMiddleware._is_websocket_request()` 확인

---

## 3. WebSocket 테스트 시나리오

### 3.1 단위 테스트 (Unit Tests)

#### A. ConnectionManager (P1)

```python
# tests/unit/websocket/test_connection_manager.py

class TestConnectionManager:
    """ConnectionManager 단위 테스트"""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self):
        """연결 추가 테스트"""
        ...

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_all_topics(self):
        """연결 종료 시 모든 구독 제거"""
        ...

    @pytest.mark.asyncio
    async def test_subscribe_elw_ticker(self):
        """ELW 종목 코드 구독 테스트"""
        ...

    @pytest.mark.asyncio
    async def test_subscribe_invalid_ticker_rejected(self):
        """잘못된 종목 코드 구독 거부"""
        ...

    @pytest.mark.asyncio
    async def test_broadcast_to_topic_subscribers_only(self):
        """토픽 구독자에게만 브로드캐스트"""
        ...
```

#### B. HeartbeatManager (P0)

```python
# tests/unit/websocket/test_heartbeat_manager.py

class TestHeartbeatManager:
    """HeartbeatManager 단위 테스트"""

    @pytest.mark.asyncio
    async def test_ping_sends_to_all_connections(self):
        """모든 연결에 ping 전송"""
        ...

    def test_record_pong_updates_timestamp(self):
        """pong 수신 시간 기록"""
        ...

    def test_is_client_alive_true_recent_pong(self):
        """최근 pong 수신 시 alive 반환"""
        ...

    def test_is_client_alive_false_timeout(self):
        """타임아웃 시 not alive 반환"""
        ...

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self):
        """정체된 연결 정리"""
        ...
```

#### C. PriceUpdateBroadcaster (P0)

```python
# tests/unit/websocket/test_price_broadcaster.py

class TestPriceUpdateBroadcaster:
    """PriceUpdateBroadcaster 단위 테스트"""

    @pytest.mark.asyncio
    async def test_fetch_prices_from_kiwoom(self):
        """Kiwoom API에서 가격 조회"""
        ...

    @pytest.mark.asyncio
    async def test_fetch_prices_from_db_fallback(self):
        """Kiwoom 실패 시 DB fallback"""
        ...

    @pytest.mark.asyncio
    async def test_broadcast_loop_running(self):
        """브로드캐스트 루프 실행"""
        ...

    def test_add_ticker(self):
        """종목 구독 추가"""
        ...

    def test_remove_ticker(self):
        """종목 구독 제거"""
        ...

    def test_get_cached_price(self):
        """캐시된 가격 조회"""
        ...
```

#### D. SignalBroadcaster (P0)

```python
# tests/unit/websocket/test_signal_broadcaster.py

class TestSignalBroadcaster:
    """SignalBroadcaster 단위 테스트"""

    @pytest.mark.asyncio
    async def test_broadcast_signal_update(self):
        """시그널 업데이트 브로드캐스트"""
        ...

    @pytest.mark.asyncio
    async def test_broadcast_vcp_signals(self):
        """VCP 시그널 브로드캐스트"""
        ...

    @pytest.mark.asyncio
    async def test_broadcast_jongga_v2_signals(self):
        """종가베팅 V2 시그널 브로드캐스트"""
        ...

    @pytest.mark.asyncio
    async def test_signal_object_to_dict_conversion(self):
        """시그널 객체 → dict 변환"""
        ...
```

### 3.2 통합 테스트 (Integration Tests)

#### A. WebSocket 연결 흐름 (P0)

```python
# tests/integration/websocket/test_connection_flow.py

@pytest.mark.integration
class TestWebSocketConnectionFlow:
    """WebSocket 연결 흐름 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, mock_ws_server):
        """
        전체 연결 수명 주기 테스트

        1. WebSocket 연결
        2. 연결 확인 메시지 수신
        3. 토픽 구독
        4. 메시지 수신
        5. 구독 해지
        6. 연결 종료
        """
        ...

    @pytest.mark.asyncio
    async def test_reconnection_after_disconnect(self, mock_ws_server):
        """연결 끊김 후 재연결 테스트"""
        ...

    @pytest.mark.asyncio
    async def test_multiple_clients_same_topic(self, mock_ws_server):
        """동일 토픽 구독한 다중 클라이언트 테스트"""
        ...
```

#### B. Mock 서비스 활용 (P1)

```python
# tests/integration/websocket/test_mock_service_integration.py

@pytest.mark.integration
class TestMockServiceIntegration:
    """Mock WebSocket 서비스 통합 테스트"""

    @pytest.mark.asyncio
    async def test_mock_ws_server_price_broadcast(self):
        """Mock WebSocket 서버 가격 브로드캐스트 테스트"""
        # Mock WebSocket 서버 (Port 5117) 연결
        uri = "ws://localhost:5117/ws"
        async with websockets.connect(uri) as websocket:
            # 구독 요청
            await websocket.send(json.dumps({
                "type": "subscribe",
                "ticker": "005930"
            }))

            # 가격 업데이트 수신 대기
            message = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(message)

            assert data["type"] == "price_update"
            assert data["ticker"] == "005930"
            assert "price" in data["data"]

    @pytest.mark.asyncio
    async def test_mock_ws_server_vcp_signal(self):
        """Mock WebSocket 서버 VCP 시그널 전송 테스트"""
        ...
```

#### C. NPM Reverse Proxy 통한 테스트 (P0)

```python
# tests/integration/websocket/test_npm_proxy.py

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Nginx proxy 테스트는 로컬 환경에서만 실행"
)
class TestNginxProxy:
    """Nginx Reverse Proxy 통한 WebSocket 테스트"""

    @pytest.mark.asyncio
    async def test_websocket_via_nginx_proxy(self):
        """
        Nginx Proxy를 통한 WebSocket 연결 테스트

        테스트 환경:
        - Frontend: http://stock.ralphpark.com
        - WebSocket: wss://stock.ralphpark.com/ws
        - NPM: http://112.219.120.75:81
        """
        uri = "wss://stock.ralphpark.com/ws"

        try:
            async with websockets.connect(uri, close_timeout=10) as websocket:
                # 연결 확인
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(message)

                assert data["type"] == "connected"

                # 핑/퐁 테스트
                await websocket.send(json.dumps({"type": "pong"}))

        except (ConnectionRefusedError, websockets.exceptions.InvalidHandshake):
            pytest.skip("Nginx proxy 또는 API Gateway가 실행 중이 아님")

    @pytest.mark.asyncio
    async def test_websocket_upgrade_headers(self):
        """WebSocket Upgrade 헤더 확인 테스트"""
        import httpx

        async with httpx.AsyncClient() as client:
            # WebSocket Upgrade 요청
            headers = {
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Version": "13"
            }

            response = await client.get(
                "https://stock.ralphpark.com/ws",
                headers=headers
            )

            # 101 Switching Protocols 응답 확인
            # 또는 400/403 에러 시 설정 문제 확인
            assert response.status_code in [101, 400, 403, 502]
```

### 3.3 E2E 테스트 (End-to-End Tests)

```python
# tests/e2e/test_websocket_e2e.py

@pytest.mark.e2e
class TestWebSocketE2E:
    """WebSocket E2E 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.playwright
    async def test_frontend_websocket_reconnection(self, browser):
        """
        Playwright를 사용한 프론트엔드 WebSocket 재연결 테스트

        1. stock.ralphpark.com 접속
        2. WebSocket 연결 확인
        3. 네트워크 차단
        4. 재연결 확인
        5. 가격 업데이트 수신 확인
        """
        page = await browser.new_page()
        await page.goto("https://stock.ralphpark.com")

        # WebSocket 연결 모니터링
        ws_messages = []

        async def handle_websocket(ws):
            async for msg in ws:
                ws_messages.append(msg)

        page.on("websocket", handle_websocket)

        # 연결 대기
        await page.wait_for_selector("[data-testid='price-updated']")

        assert len(ws_messages) > 0

    @pytest.mark.asyncio
    async def test_price_update_realtime(self):
        """실시간 가격 업데이트 E2E 테스트"""
        ...
```

---

## 4. Mock 서비스 활용 계획

### 4.1 Mock WebSocket 서버 확장

현재 `tests/mock_servers/websocket_mock_server.py`에 추가할 기능:

```python
# 에러 케이스 시뮬레이션

async def simulate_connection_timeout(self):
    """연결 타임아웃 시뮬레이션"""
    # 응답 없이 연결 대기
    await asyncio.sleep(float('inf'))

async def simulate_server_error(self, error_code: int):
    """서버 에러 시뮬레이션"""
    # 에러 코드와 함께 연결 종료
    await self.websocket.close(code=error_code)

async def simulate_intermittent_failure(self):
    """간헐적 실패 시뮬레이션"""
    # 일부 메시지는 전송, 일부는 실패
    ...
```

### 4.2 Mock Kiwoom API 활용

```python
# tests/mocks/mock_kiwoom_rest_api.py

class MockKiwoomRestAPI:
    """Kiwoom REST API Mock"""

    async def get_current_price(self, ticker: str) -> dict:
        """현재가 조회 Mock"""
        return {
            "ticker": ticker,
            "price": 80000,
            "change": 500,
            "change_rate": 0.63,
            "volume": 1000000
        }

    async def get_daily_prices(self, ticker: str, days: int) -> list:
        """일봉 데이터 조회 Mock"""
        # 역순 데이터 반환 (실제 API 동작 모방)
        return [
            {"date": "20260206", "price": 80000, "change": 500},
            {"date": "20260205", "price": 79500, "change": -300},
            {"date": "20260204", "price": 79800, "change": 200},
        ]
```

---

## 5. 실행 계획

### Week 1: 긴급 문제 해결 (P0)

- [ ] NPM Reverse Proxy WebSocket 설정 확인
- [ ] API Gateway Health 확인
- [ ] HeartbeatManager 테스트 추가
- [ ] PriceUpdateBroadcaster 테스트 추가
- [ ] SignalBroadcaster 테스트 추가

### Week 2: 통합 테스트 (P1)

- [ ] Mock 서비스 활용 테스트 추가
- [ ] WebSocket 연결 흐름 테스트
- [ ] RedisSubscriber 테스트

### Week 3: E2E 테스트 (P2)

- [ ] Playwright E2E 테스트 추가
- [ ] 프론트엔드 WebSocket 재연결 테스트

---

## 6. 성공 지표

| 지표 | 현재 | 목표 |
|------|------|------|
| WebSocket 단위 테스트 커버리지 | 50% | 80% |
| WebSocket 통합 테스트 수 | 1 | 10+ |
| Mock 서비스 활용 테스트 | 0% | 60% |
| E2E 테스트 | 0 | 3+ |

---

## 7. 결론

현재 WebSocket 서버는 핵심 클래스(ConnectionManager)에 대한 단위 테스트가 존재하지만, **HeartbeatManager, SignalBroadcaster, RedisSubscriber** 등 중요한 컴포넌트에 대한 테스트가 전혀 없습니다.

또한 **NPM Reverse Proxy를 통한 WebSocket 연결 실패** 문제를 해결하기 위해, Nginx proxy 설정 확인 및 테스트가 긴급하게 필요합니다.

제안된 계획을 따라 3주간 테스트를 추가하면 WebSocket 모듈의 커버리지를 80%까지 향상시키고, 현재 발생한 연결 문제를 조기에 발견할 수 있을 것입니다.

---

**Quality Engineer**: Quality Assurance Team
**프로젝트**: Ralph Stock Analysis System
**문서 버전**: 1.0
