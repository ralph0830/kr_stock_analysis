# 단타 추천 페이지 실시간 데이터 백엔드 요구사항

**작성일:** 2026-02-06
**목적:** custom-recommendation 페이지 실시간 데이터 연동을 위한 백엔드 구현 가이드

---

## 1. 개요

프론트엔드는 실시간 가격 연동 기능을 구현 완료했습니다. 백엔드에서는 다음 WebSocket 메시지를 브로드캐스트해야 합니다.

---

## 2. 백엔드 구현 필요 사항

### 2.1 실시간 가격 브로드캐스트 (WebSocket)

**토픽:** `price:{ticker}`

**메시지 형식:**
```json
{
  "type": "price_update",
  "ticker": "005930",
  "data": {
    "price": 75500,
    "change": 500,
    "change_rate": 0.66,
    "volume": 15000000
  },
  "timestamp": "2026-02-06T03:00:00Z"
}
```

**구독 토픽 예시:**
- `price:005930` - 삼성전자 실시간 가격
- `price:000270` - 기아 실시간 가격
- `price:066570` - LG전자 실시간 가격

**브로드캐스트 주기:**
- 최소 1초 간격 권장
- 가격 변동이 있을 때 즉시 전송 권장

### 2.2 실시간 시그널 업데이트 (WebSocket)

**토픽:** `signal:daytrading`

**메시지 형식:**
```json
{
  "type": "signal_update",
  "data": {
    "count": 3,
    "signals": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "grade": "S",
        "total_score": 90,
        "signal_type": "strong_buy",
        "entry_price": 75000,
        "target_price": 80000,
        "stop_loss": 73000,
        "current_price": 75500,
        "checks": [...]
      }
    ],
    "timestamp": "2026-02-06T03:00:00Z"
  }
}
```

---

## 3. 프론트엔드 구현 완료 사항

### 3.1 실시간 가격 Hook 통합
- `useRealtimePrices()` Hook을 사용하여 시그널 목록의 ticker들로 실시간 가격 구독
- `price:{ticker}` 토픽 자동 구독

### 3.2 실시간 가격 표시
- 현재가, 등락, 등락률 표시
- 상승: 빨간색 (`text-red-600`)
- 하락: 파란색 (`text-blue-600`)
- 실시간 상태 배지 표시

### 3.3 가격 변경 하이라이트
- 가격 변경 시 1초간 플래시 효과
- 상승: 녹색 배경 (`bg-green-50`)
- 하락: 빨간 배경 (`bg-red-50`)

### 3.4 실시간 연결 상태 표시
- 헤더에 "시그널 실시간", "가격 실시간" 배지 표시
- 연결 안됨 시 "연결 안됨" 표시

---

## 4. 테스트 확인 사항

**프론트엔드 콘솔 로그 확인:**
```
[log] [useRealtimePrices] Subscribing to price:005930
[log] [useRealtimePrices] Subscribing to price:000270
[log] [useRealtimePrices] Subscribing to price:066570
```

**브라우저 네트워크 탭 확인:**
- WebSocket 연결: `wss://stock.ralphpark.com/ws`
- WebSocket 메시지 수신 확인

---

## 5. 참고 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| 페이지 컴포넌트 | `frontend/app/custom-recommendation/page.tsx` | useRealtimePrices Hook 사용 |
| 테이블 컴포넌트 | `frontend/components/DaytradingSignalTable.tsx` | 실시간 가격 표시 |
| WebSocket Hook | `frontend/hooks/useWebSocket.ts` | useRealtimePrices 구현 |

---

## 6. 백엔드 구현 예시 (Python/FastAPI)

```python
# WebSocket 핸들러에서 가격 업데이트 브로드캐스트
async def broadcast_price_update(ticker: str, price_data: dict):
    message = {
        "type": "price_update",
        "ticker": ticker,
        "data": {
            "price": price_data["price"],
            "change": price_data["change"],
            "change_rate": price_data["change_rate"],
            "volume": price_data.get("volume", 0)
        },
        "timestamp": datetime.now().isoformat()
    }
    await websocket_manager.broadcast(f"price:{ticker}", message)

# Kiwoom REST API에서 가격 수신 후 브로드캐스트
async def on_price_received(ticker: str, price: int, change: int, change_rate: float):
    await broadcast_price_update(ticker, {
        "price": price,
        "change": change,
        "change_rate": change_rate
    })
```

---

*마지막 수정: 2026-02-06*
