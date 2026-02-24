# WebSocket 통합 테스트 계획 (Phase 2)

## 문서 정보
- **작성일**: 2026-02-06
- **버전**: 1.0
- **테스트 대상**: WebSocket 서버 (`/ws` 엔드포인트)
- **테스트 범위**: 연결 관리, 메시지 송수신, 하트비트, 구독/브로드캐스트

---

## 1. 테스트 개요

### 1.1 테스트 목표
WebSocket 서버의 통합 테스트를 통해 다음 기능을 검증합니다:
- WebSocket 연결 수립 및 해제
- CORS origin 검증
- 메시지 송수신 (JSON 형식)
- 토픽 구독/구독 취소
- 핑/퐁 메커니즘
- 하트비트 관리
- 다중 클라이언트 지원
- 타임아웃 처리

### 1.2 테스트 대상 컴포넌트

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| WebSocket 라우터 | `src/websocket/routes.py` | `/ws` 엔드포인트 핸들러 |
| Connection Manager | `src/websocket/server.py` | 연결 및 구독 관리 |
| Price Broadcaster | `src/websocket/server.py` | 가격 업데이트 브로드캐스트 |
| Heartbeat Manager | `src/websocket/server.py` | 핑/퐁 하트비트 관리 |

### 1.3 테스트 범위 (Phase 2)

**포함:**
- WebSocket 프로토콜 수준 테스트
- 메시지 형식 검증
- 연결 상태 관리
- 타임아웃 및 오류 처리
- 다중 클라이언트 시나리오

**제외 (Phase 3+):**
- Kiwoom WebSocket Bridge 실제 연동
- Redis Pub/Sub 실제 연동
- 부하 테스트 (성능)
- 보안 취약점 스캔

---

## 2. 테스트 케이스 정의

### 2.1 연결 관리 (Connection Management)

#### TC-WS-001: 연결 성공 (정상 origin)
- **설명**: 유효한 origin으로 WebSocket 연결 시도
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. `ws://localhost:5111/ws`로 연결 시도 (origin: `http://localhost:5110`)
  2. 연결 수락 확인
  3. `connected` 메시지 수신 확인
  4. `client_id` 할당 확인
- **예상 결과**: 연결 성공, `connected` 메시지 수신
- **우선순위**: P0 (필수)

#### TC-WS-002: 연결 거부 (invalid origin)
- **설명**: 허용되지 않은 origin으로 연결 시도
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. `ws://localhost:5111/ws`로 연결 시도 (origin: `http://evil.com`)
  2. 연결 거부 확인
  3. 종료 코드 1008 확인
- **예상 결과**: 연결 거부, close code 1008
- **우선순위**: P0 (필수)

#### TC-WS-003: 로컬 연결 허용 (localhost)
- **설명**: origin이 없는 로컬 연결 허용
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. localhost에서 origin 없이 연결
  2. 연결 수락 확인
- **예상 결과**: 연결 성공
- **우선순위**: P0 (필수)

#### TC-WS-004: 연결 종료 (정상)
- **설명**: 클라이언트 정상 종료
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. 연결 상태에서 close() 호출
  2. 서버에서 연결 제거 확인
- **예상 결과**: 정상 종료 (code 1000)
- **우선순위**: P0 (필수)

#### TC-WS-005: 연결 종료 (비정상)
- **설명**: 네트워크 오류 등 비정상 종료
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. 강제 연결 종료 시뮬레이션
  2. 서버에서 연결 정리 확인
- **예상 결과**: 서버가 연결을 정리하고 리소스 해제
- **우선순위**: P1 (중요)

### 2.2 메시지 송수신 (Message Exchange)

#### TC-WS-010: subscribe 메시지 처리
- **설명**: 토픽 구독 요청 처리
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. `{"type": "subscribe", "topic": "price:005930"}` 전송
  2. `subscribed` 응답 수신 확인
  3. 구독 목록에 추가 확인
- **예상 결과**: `subscribed` 메시지 수신, 구독 완료
- **우선순위**: P0 (필수)

#### TC-WS-011: unsubscribe 메시지 처리
- **설명**: 토픽 구독 취소 처리
- **前置 조건**: 구독된 상태
- **테스트 단계**:
  1. `{"type": "unsubscribe", "topic": "price:005930"}` 전송
  2. `unsubscribed` 응답 수신 확인
  3. 구독 목록에서 제거 확인
- **예상 결과**: `unsubscribed` 메시지 수신, 구독 취소 완료
- **우선순위**: P0 (필수)

#### TC-WS-012: ping 메시지 처리
- **설명**: 핑 메시지에 퐁 응답
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. `{"type": "ping"}` 전송
  2. `{"type": "pong"}` 응답 수신
- **예상 결과**: 퐁 메시지 수신
- **우선순위**: P0 (필수)

#### TC-WS-013: pong 메시지 처리
- **설명**: 퐁 메시지 수신 시 하트비트 갱신
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. `{"type": "pong"}` 전송
  2. 하트비트 관리자에서 last_pong_time 갱신 확인
- **예상 결과**: 하트비트 타임스탬프 갱신
- **우선순위**: P1 (중요)

#### TC-WS-014: 알 수 없는 메시지 타입 처리
- **설명**: 지원하지 않는 메시지 타입 전송
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. `{"type": "unknown_type"}` 전송
  2. 에러 응답 수신 확인
- **예상 결과**: `{"type": "error", "message": "Unknown message type: ..."}`
- **우선순위**: P1 (중요)

#### TC-WS-015: 초기 구독 (쿼리 파라미터)
- **설명**: 연결 시 쿼리 파라미터로 구독
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. `ws://localhost:5111/ws?subscribe=price:005930,price:000660` 연결
  2. 두 개의 `subscribed` 메시지 수신 확인
- **예상 결과**: 연결 후 자동 구독 완료
- **우선순위**: P1 (중요)

### 2.3 브로드캐스트 (Broadcast)

#### TC-WS-020: 단일 토픽 브로드캐스트
- **설명**: 특정 토픽 구독자에게만 브로드캐스트
- **前置 조건**: 두 클라이언트 연결, client1만 구독
- **테스트 단계**:
  1. client1: `price:005930` 구독
  2. client2: 구독 없음
  3. `price:005930` 토픽으로 브로드캐스트
  4. client1만 수신 확인
- **예상 결과**: client1만 메시지 수신
- **우선순위**: P0 (필수)

#### TC-WS-021: 전체 브로드캐스트
- **설명**: 모든 연결된 클라이언트에게 브로드캐스트
- **前置 조건**: 두 클라이언트 연결
- **테스트 단계**:
  1. 토픽 없이 브로드캐스트
  2. 모든 클라이언트 수신 확인
- **예상 결과**: 모든 클라이언트 수신
- **우선순위**: P1 (중요)

#### TC-WS-022: 가격 업데이트 브로드캐스트
- **설명**: 가격 업데이트 메시지 형식 확인
- **前置 조건**: 클라이언트 구독 중
- **테스트 단계**:
  1. `price:005930` 구독
  2. 가격 브로드캐스트 트리거
  3. 메시지 형식 확인
- **예상 결과**:
  ```json
  {
    "type": "price_update",
    "ticker": "005930",
    "data": {
      "price": 80500,
      "change": 500,
      "change_rate": 0.62,
      "volume": 1000000,
      "bid_price": 80490,
      "ask_price": 80510
    },
    "timestamp": "2026-02-06T..."
  }
  ```
- **우선순위**: P0 (필수)

### 2.4 하트비트 (Heartbeat)

#### TC-WS-030: 핑/퐁 라운드트립
- **설명**: 서버→클라이언트 핑, 클라이언트→서버 퐁
- **前置 조건**: 연결된 상태, 하트비트 실행 중
- **테스트 단계**:
  1. 서버에서 ping 전송 (30초 간격)
  2. 클라이언트에서 pong 응답
  3. 하트비트 관리자에서 기록 확인
- **예상 결과**: 정상 라운드트립
- **우선순위**: P1 (중요)

#### TC-WS-031: 타임아웃된 클라이언트 연결 해제
- **설명**: pong이 없는 클라이언트 연결 해제
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. 클라이언트 연결
  2. pong 미응답 (90초 초과)
  3. 서버에서 연결 해제 확인
- **예상 결과**: 타임아웃 클라이언트 연결 해제
- **우선순위**: P1 (중요)

### 2.5 다중 클라이언트 (Multiple Clients)

#### TC-WS-040: 다중 클라이언트 연결
- **설명**: 여러 클라이언트 동시 연결
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. 10개 클라이언트 동시 연결
  2. 모든 연결 성공 확인
  3. 각각 고유 client_id 확인
- **예상 결과**: 모든 클라이언트 연결 성공
- **우선순위**: P1 (중요)

#### TC-WS-041: 다중 클라이언트 구독 격리
- **설명**: 클라이언트별 구독 독립성
- **前置 조건**: 두 클라이언트 연결
- **테스트 단계**:
  1. client1: `price:005930` 구독
  2. client2: `price:000660` 구독
  3. `price:005930` 브로드캐스트
  4. client1만 수신 확인
- **예상 결과**: 구독 격리 유지
- **우선순위**: P1 (중요)

#### TC-WS-042: 클라이언트 연결 해제 시 구독 정리
- **설명**: 클라이언트 해제 시 구독 자동 제거
- **前置 조건**: 클라이언트 구독 중
- **테스트 단계**:
  1. client가 토픽 구독
  2. client 연결 해제
  3. 서버에서 구독 제거 확인
- **예상 결과**: 구독 자동 정리
- **우선순위**: P1 (중요)

### 2.6 타임아웃 및 오류 처리 (Timeout & Error Handling)

#### TC-WS-050: 수신 타임아웃 (연결 유지)
- **설명**: 메시지 없이 타임아웃 시간 경과
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. 120초간 메시지 없음
  2. 연결 유지 확인
- **예상 결과**: 연결 유지 (타임아웃으로 연결 끊기지 않음)
- **우선순위**: P1 (중요)

#### TC-WS-051: 잘못된 JSON 처리
- **설명**: 잘못된 형식의 메시지 전송
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. 유효하지 않은 JSON 전송
  2. 연결 유지 또는 적절한 에러 처리
- **예상 결과**: 연결 유지, 에러 로깅
- **우선순위**: P2 (낮음)

#### TC-WS-052: 빈 메시지 처리
- **설명**: 빈 문자열 메시지 전송
- **前置 조건**: 연결된 상태
- **테스트 단계**:
  1. 빈 메시지 전송
  2. 연결 유지 확인
- **예상 결과**: 연결 유지
- **우선순위**: P2 (낮음)

### 2.7 엔드포인트 (REST API)

#### TC-WS-060: /ws/stats 엔드포인트
- **설명**: WebSocket 통계 조회
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. GET `/ws/stats` 요청
  2. 응답 구조 확인
- **예상 결과**:
  ```json
  {
    "active_connections": 1,
    "subscriptions": {"price:005930": 1},
    "bridge_running": false,
    "broadcaster_running": true,
    "active_tickers": ["005930"],
    "heartbeat_running": false,
    "recv_timeout": 120
  }
  ```
- **우선순위**: P0 (필수)

#### TC-WS-061: /ws/subscribe/{ticker} POST
- **설명**: 종목 구독 추가
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. POST `/ws/subscribe/005930`
  2. active_tickers에 추가 확인
- **예상 결과**: 구독 성공
- **우선순위**: P1 (중요)

#### TC-WS-062: /ws/subscribe/{ticker} DELETE
- **설명**: 종목 구독 제거
- **前置 조건**: 구독된 상태
- **테스트 단계**:
  1. DELETE `/ws/subscribe/005930`
  2. active_tickers에서 제거 확인
- **예상 결과**: 구독 취소 성공
- **우선순위**: P1 (중요)

#### TC-WS-063: /ws/status 엔드포인트
- **설명**: WebSocket 상태 조회
- **前置 조건**: 서버 실행 중
- **테스트 단계**:
  1. GET `/ws/status` 요청
  2. 상태 정보 확인
- **예상 결과**: 상태 정보 반환
- **우선순위**: P1 (중요)

---

## 3. 테스트 데이터

### 3.1 Mock 종목 데이터
```python
MOCK_STOCKS = {
    "005930": {"name": "삼성전자", "base_price": 80000},
    "000660": {"name": "SK하이닉스", "base_price": 150000},
    "035420": {"name": "NAVER", "base_price": 250000},
    "005380": {"name": "현대차", "base_price": 240000},
    "028260": {"name": "삼성물산", "base_price": 140000},
}
```

### 3.2 Mock 가격 데이터
```python
MOCK_PRICE_UPDATE = {
    "type": "price_update",
    "ticker": "005930",
    "data": {
        "price": 80500,
        "change": 500,
        "change_rate": 0.62,
        "volume": 1000000,
        "bid_price": 80490,
        "ask_price": 80510
    },
    "timestamp": "2026-02-06T00:00:00Z"
}
```

---

## 4. 테스트 환경 설정

### 4.1 필요한 의존성
```toml
[tool.pytest.ini_options]
dependencies = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-timeout>=2.1",
    "websockets>=11.0",
]
```

### 4.2 환경 변수
```bash
# 테스트용 설정
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/ralph_stock_test
REDIS_URL=redis://localhost:6381/0
USE_KIWOOM_REST=false
```

### 4.3 테스트 실행 명령
```bash
# 전체 WebSocket 테스트
uv run pytest tests/integration/websocket/ -v

# 빠른 테스트만
uv run pytest tests/integration/websocket/ -m "fast" -v

# 특정 테스트
uv run pytest tests/integration/websocket/test_websocket_integration.py::TestWebSocketConnection::test_connection_success -v
```

---

## 5. 성공 기준

### 5.1 Coverage 목표
- **전체 Coverage**: 80% 이상
- **Critical Path Coverage**: 100%
  - 연결/연결 해제
  - 메시지 송수신
  - 구독/브로드캐스트

### 5.2 테스트 통과 기준
- P0 테스트: 100% 통과
- P1 테스트: 90% 이상 통과
- P2 테스트: 70% 이상 통과

---

## 6. 일정

| 단계 | 작업 | 예상 소요 시간 |
|------|------|---------------|
| Phase 2.1 | 테스트 코드 스텁 작성 | 2시간 |
| Phase 2.2 | Mock 서버 구현 | 1시간 |
| Phase 2.3 | 연결/메시지 테스트 구현 | 3시간 |
| Phase 2.4 | 브로드캐스트/하트비트 테스트 | 2시간 |
| Phase 2.5 | 통합 테스트 실행 및 버그 수정 | 2시간 |

---

## 7. 부록

### 7.1 WebSocket 클라이언트 테스트 도구
- Python: `websockets` 라이브러리
- JavaScript: `WebSocket` API
- GUI: `wscat`, `Postman`

### 7.2 참고 문서
- RFC 6455: WebSocket Protocol
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
