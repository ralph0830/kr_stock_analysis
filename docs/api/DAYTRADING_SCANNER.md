# Daytrading Scanner API Documentation

## Overview (개요)

단타 매매 기회를 실시간으로 포착하는 FastAPI 마이크로서비스입니다.

### Service Info
- **Name**: Daytrading Scanner
- **Port**: 5115
- **Health Check**: `GET /health`
- **Service Registry Name**: `daytrading-scanner`

---

## Scoring System (점수 체계)

### 7-Point Checklist (각 15점, 총 105점 만점)

| 체크리스트 | 조건 | 점수 |
|-----------|------|------|
| 거래량 폭증 | 평균 거래량의 2배 이상 | 15점 |
| | 평균 거래량의 1.5배 이상 | 8점 |
| | 미만 | 0점 |
| 모멘텀 돌파 | 신고가 갱신 또는 직전고가 2%+ 돌파 | 15점 |
| | 직전고가 1%+ 돌파 | 8점 |
| | 미달 | 0점 |
| 박스권 탈출 | 박스권 상단 돌파 | 15점 |
| | 박스권 중간~상단 | 8점 |
| | 미만 | 0점 |
| 5일선 위 | 현재가 > MA5 | 15점 |
| | MA5 ±1% 이내 | 8점 |
| | MA5 < -1% | 0점 |
| 기관 매수 | 순매수 100억+ | 15점 |
| | 순매수 50억+ | 8점 |
| | 미만 | 0점 |
| 낙폭 과대 | 3%+ 하락 후 반등 | 15점 |
| | 1%+ 하락 후 반등 | 8점 |
| | 없음 | 0점 |
| 섹터 모멘텀 | 섹터 상위 20% | 15점 |
| | 섹터 상위 40% | 8점 |
| | 하위 40% | 0점 |

### Grade Assignment (등급 부여)

| 점수 | 등급 |
|------|------|
| 90-105 | S |
| 75-89 | A |
| 60-74 | B |
| 0-59 | C |

---

## API Endpoints

### 1. Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "daytrading-scanner",
  "version": "1.0.0",
  "timestamp": "2026-02-04T12:00:00.000000"
}
```

---

### 2. Scan Market (장중 스캔)

```http
POST /api/daytrading/scan
Content-Type: application/json
```

**Request Body:**
```json
{
  "market": "KOSPI",    // KOSPI or KOSDAQ (default: KOSPI)
  "limit": 50           // 1-100 (default: 50)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "price": 75000,
        "change_rate": 2.5,
        "volume": 20000000,
        "avg_volume": 10000000,
        "volume_ratio": 2.0,
        "total_score": 90,
        "grade": "S"
      }
    ],
    "scan_time": "2026-02-04T12:00:00.000000",
    "count": 1
  }
}
```

---

### 3. Get Signals (신호 조회)

```http
GET /api/daytrading/signals?min_score=60&market=KOSPI&limit=50
```

**Query Parameters:**
| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| min_score | int | 0-105 | 최소 점수 필터 |
| market | str | KOSPI/KOSDAQ | 시장 필터 |
| limit | int | 1-100 | 최대 반환 개수 |

**Response:**
```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "total_score": 90,
        "grade": "S",
        "checks": [
          {"name": "거래량 폭증", "status": "passed", "points": 15},
          {"name": "모멘텀 돌파", "status": "passed", "points": 15},
          {"name": "박스권 탈출", "status": "passed", "points": 15},
          {"name": "5일선 위", "status": "passed", "points": 15},
          {"name": "기관 매수", "status": "passed", "points": 15},
          {"name": "낙폭 과대", "status": "passed", "points": 15},
          {"name": "섹터 모멘텀", "status": "passed", "points": 15}
        ],
        "signal_type": "STRONG_BUY",
        "entry_price": 75000,
        "target_price": 80000,
        "stop_loss": 72000,
        "reasons": ["거래량 폭증", "모멘텀 돌파", "5일선 위", "섹터 모멘텀"]
      }
    ],
    "count": 1,
    "generated_at": "2026-02-04T12:00:00.000000"
  }
}
```

---

### 4. Analyze Stocks (종목 분석)

```http
POST /api/daytrading/analyze
Content-Type: application/json
```

**Request Body:**
```json
{
  "tickers": ["005930", "000270", "066570"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "total_score": 90,
        "grade": "S",
        "checks": [
          {"name": "거래량 폭증", "status": "passed", "points": 15},
          {"name": "모멘텀 돌파", "status": "passed", "points": 15},
          {"name": "박스권 탈출", "status": "passed", "points": 15},
          {"name": "5일선 위", "status": "passed", "points": 15},
          {"name": "기관 매수", "status": "passed", "points": 15},
          {"name": "낙폭 과대", "status": "passed", "points": 15},
          {"name": "섹터 모멘텀", "status": "passed", "points": 0}
        ],
        "entry_price": null,
        "target_price": null,
        "stop_loss": null
      }
    ],
    "count": 1,
    "analyzed_at": "2026-02-04T12:00:00.000000"
  }
}
```

---

## Error Responses

### Validation Error (422)
```json
{
  "status": "error",
  "code": 422,
  "detail": [
    {
      "loc": ["body", "limit"],
      "msg": "ensure this value is greater than 0",
      "type": "greater_than"
    }
  ]
}
```

### HTTP Error (400/404/500)
```json
{
  "status": "error",
  "code": 400,
  "detail": "tickers cannot be empty"
}
```

---

## WebSocket Topics

### Available Topics
- `daytrading_signals`: 단타 신호 브로드캐스트
- `daytrading_scan`: 스캔 진행률 및 결과

### Message Format
```json
{
  "type": "signal_created",
  "data": {
    "id": 123,
    "ticker": "005930",
    "grade": "S",
    "total_score": 90
  },
  "timestamp": "2026-02-04T10:00:00+09:00"
}
```

---

## Database Schema

### Table: `daytrading_signals`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary Key |
| ticker | String(6) | 종목 코드 |
| name | String(100) | 종목명 |
| market | String(10) | KOSPI/KOSDAQ |
| total_score | Integer | 총 점수 (0-105) |
| grade | String(10) | S/A/B/C |
| volume_score | Integer | 거래량 점수 |
| momentum_score | Integer | 모멘텀 점수 |
| box_score | Integer | 박스권 점수 |
| ma5_score | Integer | 5일선 점수 |
| institution_score | Integer | 기관 매수 점수 |
| oversold_score | Integer | 낙폭 과대 점수 |
| sector_score | Integer | 섹터 모멘텀 점수 |
| checks | JSON | 체크리스트 상세 |
| entry_price | Integer | 진입가 |
| target_price | Integer | 목표가 |
| stop_loss | Integer | 손절가 |
| status | String(20) | OPEN/CLOSED |
| signal_date | Date | 신호 날짜 |
| entry_time | DateTime | 진입 시간 |
| exit_time | DateTime | 청산 시간 |
| exit_reason | String(50) | 청산 사유 |

---

## Usage Examples

### curl
```bash
# Health check
curl http://localhost:5115/health

# Scan KOSPI
curl -X POST http://localhost:5115/api/daytrading/scan \
  -H "Content-Type: application/json" \
  -d '{"market": "KOSPI", "limit": 10}'

# Get signals (score >= 60)
curl "http://localhost:5115/api/daytrading/signals?min_score=60&limit=20"

# Analyze specific stocks
curl -X POST http://localhost:5115/api/daytrading/analyze \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["005930", "000270"]}'
```

### Python
```python
import httpx

async def scan_daytrading():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:5115/api/daytrading/scan",
            json={"market": "KOSPI", "limit": 10}
        )
        return response.json()

result = await scan_daytrading()
print(result["data"]["candidates"])
```

### JavaScript/TypeScript
```typescript
const response = await fetch('http://localhost:5115/api/daytrading/scan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ market: 'KOSPI', limit: 10 })
});
const data = await response.json();
console.log(data.data.candidates);
```

---

*Last Updated: 2026-02-04*
