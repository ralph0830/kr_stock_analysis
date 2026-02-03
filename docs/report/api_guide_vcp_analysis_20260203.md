# API_GUIDE.md 기반 VCP 시그널 실시간 업데이트 분석 보고서

**분석 일자**: 2026-02-03
**분석 대상**: API_GUIDE.md (전체 1076줄)
**목적**: API 문서에 명시된 VCP 시그널 및 실시간 업데이트 명세 확인

---

## 1. 실행 요약

### 1.1 API 문서 확인 결과

| 항목 | API 문서 명세 | 설명 |
|------|-------------|------|
| VCP 시그널 조회 | `GET /api/kr/signals` | 정적 데이터 (VCP Scanner 프록시) |
| 실시간 가격 조회 | `POST /api/kr/realtime-prices` | Kiwoom REST API |
| 실시간 가격 WebSocket | `/ws` | Kiwoom WebSocket 0B TR |
| VCP 스캔 트리거 | `POST /api/kr/scan/vcp` | 수동 스캔 실행 |

### 1.2 핵심 발견

1. **VCP 시그널은 정적 데이터**
   - API가 VCP Scanner 서비스로 프록시
   - `created_at` 타임스탬프로 생성 시점 기록
   - 실시간 업데이트 없음

2. **실시간 업데이트는 가격 데이터만 해당**
   - WebSocket은 Kiwoom 0B TR (주식체결) 데이터만 브로드캐스트
   - `price_update` 메시지 타입만 존재
   - `signal_update` 메시지 타입 없음

3. **VCP 페이지에서 WebSocket 연동 필요**
   - API 문서는 WebSocket 사용을 권장
   - 현재 VCP 페이지는 폴링 방식 사용
   - WebSocket으로 전환 권장

---

## 2. API 문서 분석

### 2.1 VCP 시그널 조회 API

**엔드포인트**: `GET /api/kr/signals?limit=20`

**API 문서 설명** (라인 193-222):
```http
GET /api/kr/signals?limit=20
```

> VCP Scanner 서비스로 프록시하여 활성 시그널 목록을 반환합니다.

**응답**:
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "signal_type": "vcp",
    "score": 85.5,
    "grade": "A",
    "entry_price": null,
    "target_price": null,
    "created_at": "2026-01-29T09:00:00"  // 생성 시점 타임스탬프
  }
]
```

**분석**:
- `created_at` 필드로 시그널 생성 시점 기록
- 실시간 업데이트를 위한 메커니즘 없음
- 정적인 스냅샷 데이터 반환

### 2.2 실시간 가격 API

**엔드포인트**: `POST /api/kr/realtime-prices`

**API 문서 설명** (라인 514-551):
```http
POST /api/kr/realtime-prices
```

> Kiwoom REST API를 통해 복수 종목의 실시간 가격을 조회합니다.

**요청**:
```json
{
  "tickers": ["005930", "000660", "035420"]
}
```

**응답**:
```json
{
  "prices": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "price": 160600,
      "change": 1800,
      "change_rate": 1.13,
      "volume": 15234567,
      "timestamp": "2026-01-29T12:00:00"
    }
  ]
}
```

**중요 참고** (라인 551):
> **참고**: 실시간 가격 업데이트는 **WebSocket을 통해서도 받을 수 있습니다**. `/ws` WebSocket 엔드포인트를 통해 Kiwoom WebSocket 0B TR 데이터를 실시간으로 수신할 수 있습니다.

**분석**:
- API 문서가 **WebSocket 사용을 권장**
- REST API 폴링보다 WebSocket이 효율적임

### 2.3 WebSocket 명세

**연결** (라인 868-894):
```javascript
const ws = new WebSocket('ws://localhost:5111/ws');

ws.onopen = () => {
  // 종목 구독
  ws.send(JSON.stringify({
    type: 'subscribe',
    topic: 'price:005930'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'price_update') {
    console.log(`${data.ticker}: ${data.data.price}원`);
  }
};
```

**메시지 형식** (라인 896-915):
```json
{
  "type": "price_update",
  "ticker": "005930",
  "data": {
    "price": 160600,
    "change": 1800,
    "change_rate": 1.13,
    "volume": 15234567
  },
  "timestamp": "2026-01-29T12:00:00",
  "source": "kiwoom_ws"
}
```

**WebSocket 엔드포인트** (라인 917-984):

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/ws/stats` | GET | WebSocket 연결 통계 조회 |
| `/ws/subscribe/{ticker}` | POST | 종목 실시간 가격 브로드캐스트에 추가 |
| `/ws/subscribe/{ticker}` | DELETE | 종목 실시간 가격 브로드캐스트에서 제거 |
| `/ws/tickers` | GET | 활성화된 종목 목록 조회 |

**기본 구독 종목** (라인 1068-1075):
```
실시간 가격 데이터를 제공하는 기본 종목:
- 005930 (삼성전자)
- 000660 (SK하이닉스)
- 035420 (NAVER)
- 005380 (현대차)
```

**Kiwoom WebSocket 0B TR 데이터 필드** (라인 1055-1067):

| 필드 | 설명 |
|------|------|
| `10` | 현재가 |
| `11` | 전일대비 |
| `12` | 등락율 (%) |
| `13` | 누적거래량 |
| `15` | 거래량 |
| `20` | 체결시간 (HHMMSS) |
| `27` | 매도호가 |
| `28` | 매수호가 |

### 2.4 VCP 스캔 트리거

**엔드포인트**: `POST /api/kr/scan/vcp`

**API 문서 설명** (라인 727-762):
```http
POST /api/kr/scan/vcp?market=KOSPI&min_score=70&min_grade=A
```

> VCP (Volatility Contraction Pattern) 스캔을 실행합니다.

**쿼리 파라미터**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| market | string | No | 시장 (KOSPI, KOSDAQ, ALL) |
| min_score | float | No | 최소 점수 (0-100) |
| min_grade | string | No | 최소 등급 (S, A, B, C) |
| top_n | integer | No | 상위 N개 종목만 스캔 (기본 30) |

**응답**:
```json
{
  "status": "completed",
  "scanned_count": 2500,
  "found_signals": 15,
  "started_at": "2026-01-29T10:00:00",
  "completed_at": "2026-01-29T10:02:30",
  "signals": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "score": 85.5,
      "grade": "A",
      "vcp_score": 82.0,
      "smartmoney_score": 75.5
    }
  ]
}
```

**분석**:
- 수동으로 VCP 스캔 실행 가능
- 스캔은 일회성 작업 (실시간 업데이트 아님)

---

## 3. VCP 시그널 데이터 흐름 (API 관점)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     API 문서 기반 VCP 시그널 데이터 흐름                   │
└─────────────────────────────────────────────────────────────────────────┘

1. VCP Scanner 스캔 (Celery Beat 또는 수동 트리거)
   ↓
2. VCP Scanner 서비스: 전 종목 분석 → 시그널 생성
   ↓
3. DB 저장 (signals 테이블)
   ↓
4. API Gateway: GET /api/kr/signals
   ↓
5. 프론트엔드: 시그널 목록 수신 (정적 데이터)
   ↓
6. 실시간 가격 업데이트 별도 처리
   ├─ REST API 폴링: POST /api/kr/realtime-prices (60초)
   └─ WebSocket 권장: /ws → price_update 메시지
```

---

## 4. API 문서에 명시된 실시간 업데이트 방법

### 4.1 권장 방법: WebSocket

**API 문서 라인 868-894**:
```javascript
const ws = new WebSocket('ws://localhost:5111/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    topic: 'price:005930'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'price_update') {
    console.log(`${data.ticker}: ${data.data.price}원`);
  }
};
```

### 4.2 WebSocket 메시지 타입

API 문서에 명시된 메시지 타입:
| 메시지 타입 | 설명 | 소스 |
|------------|------|------|
| `price_update` | 가격 업데이트 | Kiwoom WebSocket 0B TR |
| `connected` | 연결 성공 | WebSocket 서버 |
| `subscribed` | 구독 성공 | WebSocket 서버 |
| `unsubscribed` | 구독 해제 | WebSocket 서erver |

**없는 메시지 타입**:
| 메시지 타입 | 설명 |
|------------|------|
| `signal_update` | 시그널 업데이트 (❌ 없음) |

### 4.3 WebSocket vs 폴링 비교

| 방식 | API 문서 권장 | 장점 | 단점 |
|------|---------------|------|------|
| WebSocket | ✅ 권장 | 실시간, 서버 리소스 절약 | 연결 유지 필요 |
| REST API 폴링 | 가능 | 구현 간단 | 불필요한 API 호출, 지연 |

---

## 5. VCP 페이지 구현 가이드 (API 문서 기반)

### 5.1 권장 아키텍처

```typescript
// VCP 페이지
import { useRealtimePrices } from "@/hooks/useWebSocket";

export default function VCPPage() {
  const [signals, setSignals] = useState<Signal[]>([]);

  // 1. 시그널 목록 로드 (페이지 로드 시 한 번)
  useEffect(() => {
    const loadSignals = async () => {
      const response = await fetch('/api/kr/signals?limit=10');
      const data = await response.json();
      setSignals(data);
    };
    loadSignals();
  }, []);

  // 2. 실시간 가격 구독 (WebSocket)
  const tickers = signals.map(s => s.ticker);
  useRealtimePrices(tickers);  // WebSocket으로 현재가 업데이트

  return (
    // ... UI ...
  );
}
```

### 5.2 WebSocket 구독 Flow

```
1. 페이지 로드
   ↓
2. 시그널 API 호출 → 시그널 목록 수신
   ↓
3. 시그널 종목 추출 → tickers 배열
   ↓
4. WebSocket 연결 → ws://localhost:5111/ws
   ↓
5. 종목별 구독 → topic: price:{ticker}
   ↓
6. price_update 메시지 수신 → 현재가 자동 업데이트
```

---

## 6. 결론

### 6.1 API 문서 확인 결과

1. **VCP 시그널은 정적 데이터**
   - API 문서에 명시된 대로 VCP 시그널은 스캔 시점의 스냅샷
   - `created_at` 타임스탬프로 생성 시점 기록
   - 실시간으로 변동하지 않음

2. **실시간 업데이트는 가격만 해당**
   - API 문서는 WebSocket을 통한 실시간 가격 업데이트 권장
   - `price_update` 메시지 타입만 정의됨
   - `signal_update` 메시지 타입 없음

3. **WebSocket 사용 권장**
   - API 문서 라인 551: "실시간 가격 업데이트는 WebSocket을 통해서도 받을 수 있습니다"
   - 폴링보다 WebSocket이 효율적

### 6.2 VCP 시그널이 "실시간으로 변동"하는가?

| 구분 | 답변 | 설명 |
|------|------|------|
| 시그널 목록 | ❌ 아니오 | 하루에 한 번 스캔으로 생성 |
| 시그널 점수/등급 | ❌ 아니오 | 일봉 데이터 기반으로 정적 계산 |
| 시그널의 현재가 | ✅ 예 | WebSocket으로 실시간 업데이트 가능 |

### 6.3 개선 필요 사항

| 항목 | 현재 상태 | 권장 방안 |
|------|----------|----------|
| VCP 페이지 현재가 업데이트 | 60초 폴링 | WebSocket으로 전환 |
| 시그널 목록 갱신 | 페이지 로드 시 | 수동 새로고침 (정적 데이터) |
| WebSocket 연동 | 미사용 | `useRealtimePrices()` Hook 사용 |

---

## 7. 참조

### 7.1 API 문서 위치

| 파일 | 경로 | 라인 수 |
|------|------|--------|
| 요약본 | `docs/api/API_GUIDE.md` | 240줄 |
| 전체본 | `docs/archive_originals/API_GUIDE.md` | **1076줄** |

### 7.2 관련 API 엔드포인트

| 엔드포인트 | 라인 | 설명 |
|-----------|------|------|
| `GET /api/kr/signals` | 193-222 | VCP 시그널 목록 조회 |
| `POST /api/kr/realtime-prices` | 514-551 | 실시간 가격 조회 |
| `WebSocket /ws` | 868-984 | WebSocket 연결 |
| `POST /api/kr/scan/vcp` | 727-762 | VCP 스캔 트리거 |

### 7.3 WebSocket 데이터 필드 (Kiwoom 0B TR)

| 필드 | 설명 | 라인 |
|------|------|------|
| `10` | 현재가 | 1059 |
| `12` | 등락율 (%) | 1061 |
| `20` | 체결시간 (HHMMSS) | 1064 |

---

*보고서 작성일: 2026-02-03*
*분석 기반: API_GUIDE.md (전체 1076줄)*
*버전: 1.0*
