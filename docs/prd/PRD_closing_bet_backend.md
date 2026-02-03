# 종가 베팅 대시보드 - 백엔드 PRD

> **문서 버전**: 1.0
> **작성일**: 2026-02-03
> **담당 서비스**: API Gateway (Port 5111)

---

## 1. 개요

### 1.1 목적
한국 주식 시장의 종가 베팅(Closing Price Betting) 전략을 위한 실시간 추천 시스템 백엔드 API를 구축합니다.

### 1.2 범위
- 거래대금 상위 종목 스캔 및 점수화
- 7가지 체크리스트 기반 추천 종목 선정
- 실시간 차트 데이터 제공
- 종목 뉴스 크롤링
- 추천 내역 저장 및 조회

### 1.3 기술 스택
- **Framework**: FastAPI
- **Database**: PostgreSQL (TimescaleDB)
- **외부 API**: 키움증권 REST API, 네이버 금융 크롤링
- **Language**: Python 3.11+

---

## 2. API 명세

### 2.1 라우터 구조

```
services/api_gateway/routes/
└── closing_bet.py          # 종가 베팅 전용 라우터
```

### 2.2 엔드포인트 목록

| 메서드 | 경로 | 설명 | 태그 |
|--------|------|------|------|
| GET | `/api/kr/closing-bet/recommendations` | 실시간 추천 종목 TOP 3 | closing-bet |
| GET | `/api/kr/closing-bet/candidates` | 거래대금 상위 후보 종목 리스트 | closing-bet |
| GET | `/api/kr/closing-bet/chart/{ticker}` | 종목별 분봉 차트 데이터 | closing-bet |
| GET | `/api/kr/closing-bet/news/{ticker}` | 종목별 뉴스 크롤링 | closing-bet |
| GET | `/api/kr/closing-bet/history` | 추천 내역 조회 | closing-bet |
| POST | `/api/kr/closing-bet/history` | 추천 내역 저장 | closing-bet |
| GET | `/api/kr/closing-bet/sectors` | 섹터별 현황 | closing-bet |

---

## 3. 상세 API 명세

### 3.1 GET /api/kr/closing-bet/recommendations

실시간 종가 베팅 추천 종목 TOP 3를 반환합니다.

**Request**
```http
GET /api/kr/closing-bet/recommendations
```

**Response**
```json
{
  "success": true,
  "timestamp": "2026-02-03T15:25:30+09:00",
  "market_status": "OPEN",
  "is_recommendation_time": false,
  "recommendations": [
    {
      "code": "005930",
      "name": "삼성전자",
      "price": 85000,
      "change_rate": 2.5,
      "trading_value": 150000000000,
      "score": 85,
      "grade": "A",
      "has_news": true,
      "high": 85500,
      "high52w": 92000,
      "low52w": 68000,
      "open": 84000,
      "volume": 15000000
    }
  ],
  "candidates_count": 50
}
```

**Response Schema**
```python
class ClosingBetStockResponse(BaseModel):
    code: str                    # 종목코드
    name: str                    # 종목명
    price: int                   # 현재가
    change_rate: float           # 등락률 (%)
    trading_value: int           # 거래대금 (원)
    score: int                   # 종가베팅 점수 (0-100)
    grade: str                   # 등급 (S/A/B/C)
    has_news: bool               # 뉴스 존재 여부
    high: Optional[int]          # 당일 고가
    high52w: Optional[int]       # 52주 신고가
    low52w: Optional[int]        # 52주 신저가
    open: Optional[int]          # 당일 시가
    volume: Optional[int]        # 거래량

class ClosingBetRecommendationsResponse(BaseModel):
    success: bool
    timestamp: datetime
    market_status: Literal["OPEN", "CLOSED"]
    is_recommendation_time: bool    # 15:10 이후 여부
    recommendations: List[ClosingBetStockResponse]
    candidates_count: int
```

---

### 3.2 GET /api/kr/closing-bet/candidates

거래대금 상위 후보 종목 리스트를 반환합니다.

**Request**
```http
GET /api/kr/closing-bet/candidates?market=all&limit=50
```

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| market | string | No | KOSPI/KOSDAQ/all (기본값: all) |
| limit | int | No | 최대 개수 (기본값: 50, 최대: 100) |

**Response**
```json
{
  "success": true,
  "market": "all",
  "candidates": [
    {
      "code": "005930",
      "name": "삼성전자",
      "price": 85000,
      "change_rate": 2.5,
      "trading_value": 150000000000,
      "rank": 1
    }
  ],
  "total_count": 50
}
```

---

### 3.3 GET /api/kr/closing-bet/chart/{ticker}

종목별 분봉(1분봉) 차트 데이터를 반환합니다.

**Request**
```http
GET /api/kr/closing-bet/chart/005930?tick=1&limit=60
```

**Path Parameters**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| ticker | string | 종목코드 (6자리) |

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| tick | int | No | 분봉 단위 (기본값: 1) |
| limit | int | No | 반환 개수 (기본값: 60, 최대: 120) |

**Response**
```json
{
  "success": true,
  "ticker": "005930",
  "data": [
    {
      "time": "14:55",
      "open": 84800,
      "high": 85000,
      "low": 84700,
      "close": 84900,
      "volume": 50000
    }
  ],
  "count": 60
}
```

---

### 3.4 GET /api/kr/closing-bet/news/{ticker}

종목별 관련 뉴스를 크롤링하여 반환합니다.

**Request**
```http
GET /api/kr/closing-bet/news/005930
```

**Path Parameters**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| ticker | string | 종목코드 (6자리) |

**Response**
```json
{
  "success": true,
  "ticker": "005930",
  "news": [
    {
      "title": "삼성전자, 반도체 호조로 상승",
      "link": "https://news.naver.com/...",
      "info": "연합뉴스",
      "date": "2026.02.03 14:30"
    }
  ],
  "count": 5
}
```

---

### 3.5 GET /api/kr/closing-bet/history

추천 내역을 조회합니다.

**Request**
```http
GET /api/kr/closing-bet/history?days=30
```

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| days | int | No | 조회 기간 (기본값: 30) |

**Response**
```json
{
  "success": true,
  "history": [
    {
      "date": "2026-02-02",
      "stocks": [
        {
          "code": "005930",
          "name": "삼성전자",
          "buy_price": 84000,
          "next_open": 85000,
          "change_rate": 1.19,
          "score": 85
        }
      ]
    }
  ]
}
```

---

### 3.6 POST /api/kr/closing-bet/history

추천 내역을 저장합니다.

**Request**
```http
POST /api/kr/closing-bet/history
Content-Type: application/json

{
  "date": "2026-02-03",
  "stocks": [
    {
      "code": "005930",
      "name": "삼성전자",
      "buy_price": 85000,
      "score": 85
    }
  ]
}
```

**Response**
```json
{
  "success": true,
  "message": "추천 내역 저장 완료"
}
```

---

### 3.7 GET /api/kr/closing-bet/sectors

섹터별 현황을 반환합니다.

**Request**
```http
GET /api/kr/closing-bet/sectors
```

**Response**
```json
{
  "success": true,
  "timestamp": "2026-02-03T15:25:30+09:00",
  "sectors": [
    {
      "name": "반도체",
      "change_pct": 2.5,
      "signal": "bullish",
      "score": 75,
      "leaders": ["삼성전자", "SK하이닉스"]
    }
  ]
}
```

---

## 4. 비즈니스 로직

### 4.1 종가 베팅 점수화 로직

**점수 계산 (총 100점)**

| 항목 | 만점 | 부분점 | 조건 (만점) | 조건 (부분) |
|------|------|--------|------------|-------------|
| 120일선 위 위치 | 15 | 8 | `price > low52w * 1.3` | `price > low52w * 1.1` |
| 대량 거래대금 | 15 | 8 | `trading_value >= 1조` | `trading_value >= 5000억` |
| 등락률 | 15 | 8 | `change_rate >= 3%` | `change_rate >= 1%` |
| 고가 인근 | 15 | 8 | `price >= high * 0.98` | `price >= high * 0.95` |
| 52주 신고가 근접 | 15 | 8 | `price >= high52w * 0.95` | `price >= high52w * 0.85` |
| 돌파형 | 15 | 8 | `price >= high52w * 0.98` | `price >= high52w * 0.90` |
| 양봉 형태 | 10 | 5 | `change_rate >= 2% and price > open` | `change_rate >= 0` |

**등급 부여 기준**
- **S**: 90점 이상
- **A**: 80점 이상 ~ 90점 미만
- **B**: 70점 이상 ~ 80점 미만
- **C**: 70점 미만

### 4.2 추천 종목 선정 로직

```
1. KOSPI/KOSDAQ 거래대금 상위 50개씩 추출
   └─> 키움 REST API: /api/dostk/rkinfo

2. 종목별 상세 정보 조회
   └─> 키움 REST API: /api/dostk/stkinfo

3. 거래대금 기반 TOP 50 필터링

4. 점수화 (7가지 체크리스트)

5. 상위 20개 + 점수 40점 이상 종목 뉴스 확인
   └─> 네이버 금융 크롤링

6. 최종 TOP 3 선정
   - 우선순위: 뉴스 있음 + 점수 40점 이상
   - 차선: 거래대금 상위
```

### 4.3 마켓 상태 판단

| 시간 | 상태 | is_recommendation_time |
|------|------|------------------------|
| 09:00 ~ 15:30 (평일) | OPEN | false |
| 15:10 ~ 15:30 (평일) | OPEN | **true** |
| 그 외 | CLOSED | false |

---

## 5. 외부 연동

### 5.1 키움증권 REST API

**엔드포인트**
| API ID | 경로 | 설명 |
|--------|------|------|
| ka10032 | /api/dostk/rkinfo | 거래대금 상위 종목 |
| ka10001 | /api/dostk/stkinfo | 종목 현재가 정보 |
| ka10080 | /api/dostk/chart | 분봉 차트 데이터 |

**인증**
- `Authorization: Bearer {access_token}`
- `appkey: {KIWOOM_APP_KEY}`
- `api-id: {API_ID}`

**Rate Limiting**
- 요청 간격: 500ms (API 제한 방지)
- 캐싱: 30초 TTL

### 5.2 네이버 금융 크롤링

**URL**
```
https://finance.naver.com/item/news_news.naver?code={ticker}
```

**파싱 전략**
- CSS Selector: `table.type5 tr`, `.tb_type_news tr`
- 캐싱: 5분 TTL
- 최대 8개 뉴스 반환

---

## 6. 데이터 스키마

### 6.1 Schema 추가 (`services/api_gateway/schemas.py`)

```python
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class ClosingBetStockResponse(BaseModel):
    """종가 베팅 종목 응답"""
    code: str
    name: str
    price: int
    change_rate: float
    trading_value: int
    score: int
    grade: str
    has_news: bool
    high: Optional[int] = None
    high52w: Optional[int] = None
    low52w: Optional[int] = None
    open: Optional[int] = None
    volume: Optional[int] = None

class ClosingBetRecommendationsResponse(BaseModel):
    """종가 베팅 추천 응답"""
    success: bool
    timestamp: datetime
    market_status: Literal["OPEN", "CLOSED"]
    is_recommendation_time: bool
    recommendations: List[ClosingBetStockResponse]
    candidates_count: int

class ChartPoint(BaseModel):
    """차트 데이터 포인트"""
    time: str          # HH:MM
    open: int
    high: int
    low: int
    close: int
    volume: int

class ClosingBetChartResponse(BaseModel):
    """종가 베팅 차트 응답"""
    success: bool
    ticker: str
    data: List[ChartPoint]
    count: int

class NewsItem(BaseModel):
    """뉴스 아이템"""
    title: str
    link: str
    info: str
    date: str

class ClosingBetNewsResponse(BaseModel):
    """종가 베팅 뉴스 응답"""
    success: bool
    ticker: str
    news: List[NewsItem]
    count: int

class HistoryStock(BaseModel):
    """히스토리 종목"""
    code: str
    name: str
    buy_price: int
    next_open: Optional[int] = None
    change_rate: Optional[float] = None
    score: int

class HistoryEntry(BaseModel):
    """히스토리 엔트리"""
    date: str
    stocks: List[HistoryStock]

class ClosingBetHistoryResponse(BaseModel):
    """종가 베팅 히스토리 응답"""
    success: bool
    history: List[HistoryEntry]

class SectorItem(BaseModel):
    """섹터 아이템"""
    name: str
    change_pct: float
    signal: Literal["bullish", "bearish", "neutral"]
    score: float
    leaders: List[str]

class ClosingBetSectorsResponse(BaseModel):
    """종가 베팅 섹터 응답"""
    success: bool
    timestamp: datetime
    sectors: List[SectorItem]
```

### 6.2 DB 저장소 (선택)

**히스토리 저장 방식**
- 방법 1: JSON 파일 (`data/closing_bet_history.json`)
- 방법 2: DB 테이블 (`closing_bet_history`)

```sql
-- DB 사용 시 테이블 구조
CREATE TABLE closing_bet_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    stocks JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. 라우터 구현 개요

```python
"""
services/api_gateway/routes/closing_bet.py
종가 베팅 전용 라우터
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, time

router = APIRouter(
    prefix="/api/kr/closing-bet",
    tags=["closing-bet"],
)

# 캐시
stock_cache = {}
news_cache = {}
CACHE_TTL = 30  # 30초
NEWS_CACHE_TTL = 300  # 5분

def calculate_score(stock: dict) -> int:
    """종가 베팅 점수 계산 (0-100)"""
    score = 0
    checks = [
        # (만점, 부분점, 조건)
        (15, 8, stock.get("low52w") and stock["price"] > stock["low52w"] * 1.3),
        (15, 8, stock.get("trading_value", 0) >= 100000000000),
        (15, 8, stock.get("change_rate", 0) >= 3),
        (15, 8, stock.get("high") and stock["price"] >= stock["high"] * 0.98),
        (15, 8, stock.get("high52w") and stock["price"] >= stock["high52w"] * 0.95),
        (15, 8, stock.get("high52w") and stock["price"] >= stock["high52w"] * 0.98),
        (10, 5, stock.get("change_rate", 0) >= 2 and stock["price"] > stock.get("open", 0)),
    ]
    for full, partial, passed in checks:
        if passed:
            score += full
        elif partial:  # 부분 조건 체크 로직 필요
            score += partial // 2
    return min(score, 100)

def get_grade(score: int) -> str:
    """점수 -> 등급 변환"""
    if score >= 90: return "S"
    if score >= 80: return "A"
    if score >= 70: return "B"
    return "C"

@router.get("/recommendations", response_model=ClosingBetRecommendationsResponse)
async def get_recommendations():
    """실시간 추천 종목 TOP 3"""
    # 1. 거래대금 상위 종목 조회
    # 2. 점수화
    # 3. 뉴스 확인
    # 4. TOP 3 선정
    pass

@router.get("/chart/{ticker}", response_model=ClosingBetChartResponse)
async def get_chart(ticker: str, tick: int = 1, limit: int = 60):
    """분봉 차트 데이터 조회"""
    pass

# ... 엔드포인트별 구현
```

---

## 8. Main.py 라우터 등록

```python
# services/api_gateway/main.py

# 라우터 등록
_include_router("closing_bet", "router", "Closing Bet")
```

---

## 9. 테스트 계획

### 9.1 단위 테스트
- 점수화 로직 검증
- 등급 변환 로직 검증
- 마켓 상태 판단 로직 검증

### 9.2 통합 테스트
- 키움 API 연동 테스트
- 네이버 크롤링 테스트
- 전체 추천 플로우 테스트

---

## 10. 배포 및 모니터링

### 10.1 환경변수
```bash
# 키움증권 REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true

# 종가 베팅 설정
CLOSING_BET_RECOMMENDATION_TIME=15:20
CLOSING_BET_CACHE_TTL=30
CLOSING_BET_NEWS_CACHE_TTL=300
```

### 10.2 모니터링 메트릭
- API 응답 시간
- 키움 API 호출 성공률
- 뉴스 크롤링 성공률
- 캐시 적중률

---

*문서 끝*
