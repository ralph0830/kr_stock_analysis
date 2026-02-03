# 실시간 OHLC 수집 가이드

**버전:** 1.0.0
**최종 수정:** 2026-02-03

---

## 목차

1. [개요](#1-개요)
2. [구조](#2-구조)
3. [사용법](#3-사용법)
4. [Kiwoom WebSocket TR](#4-kiwoom-websocket-tr)
5. [데이터 흐름](#5-데이터-흐름)

---

## 1. 개요

Kiwoom WebSocket을 통해 실시간 체결 데이터를 수집하고 OHLC 형태로 집계합니다.

### 1.1 파일 구조

| 파일 | 설명 |
|------|------|
| `src/kiwoom/ohlc_collector.py` | OHLC 수집기 모듈 |
| `tasks/ohlc_tasks.py` | Celery 백그라운드 태스크 |
| `scripts/test_ohlc_collector.py` | 테스트 스크립트 |

---

## 2. 구조

### 2.1 아키텍처

```
Kiwoom WebSocket (0B TR)
    ↓ 실시간 체결 데이터
OHLCCollector._on_receive_real_data()
    ↓ OHLC 바 집계 (초/분 단위)
DailyPriceRepository.update_realtime_bar()
    ↓ DB 저장 (Upsert)
daily_prices 테이블 (OHLCV)
```

### 2.2 OHLCCollectorConfig

```python
@dataclass
class OHLCCollectorConfig:
    tickers: list[str]           # 수집할 종목 리스트
    save_interval: int = 60     # DB 저장 간격 (초)
    bar_interval: int = 60       # 바 생성 간격 (초)
```

---

## 3. 사용법

### 3.1 직접 실행 (테스트)

```bash
# 기본 5종목 60초 수집
python scripts/test_ohlc_collector.py

# 종목 지정
python scripts/test_ohlc_collector.py --tickers 005930 000660

# 수집 시간 지정
python scripts/test_ohlc_collector.py --duration 300

# 간단 모드 (최소 출력)
python scripts/test_ohlc_collector.py --simple
```

### 3.2 Celery 태스크

```python
from tasks.ohlc_tasks import start_ohlc_collection, stop_ohlc_collection

# 수집 시작 (기본: KOSPI 상위 종목)
result = start_ohlc_collection.delay(
    tickers=["005930", "000660"],
    duration_seconds=3600
)

# 수집 중지
stop_ohlc_collection.delay()

# 상태 조회
from tasks.ohlc_tasks import get_ohlc_status
status = get_ohlc_status.delay()
print(status.get())
```

### 3.3 Python 코드에서 직접 사용

```python
import asyncio
from src.kiwoom.ohlc_collector import OHLCCollector, OHLCCollectorConfig
from src.kiwoom.base import KiwoomConfig

async def main():
    config = KiwoomConfig.from_env()
    collector_config = OHLCCollectorConfig(
        tickers=["005930", "000660"],
        save_interval=60,  # 1분마다 DB 저장
    )

    collector = OHLCCollector(config, collector_config)

    # 수집 시작
    await collector.start()

    # 1시간 수집
    await asyncio.sleep(3600)

    # 중지
    await collector.stop()

asyncio.run(main())
```

---

## 4. Kiwoom WebSocket TR

### 4.1 0B TR (실시간 시세)

| 필드 | 설명 | 타입 |
|------|------|------|
| 10 | 현재가 (체결가) | Number |
| 13 | 누적거래량 | Number |
| 15 | 거래량 (+: 매수체결, -: 매도체결) | Number |
| 20 | 체결시간 (HHMMSS) | String |

### 4.2 TR 구독

```python
# Kiwoom WebSocket으로 TR 구독
await kiwoom_pipeline.subscribe(ticker)  # 종목별 시세
await kiwoom_pipeline.subscribe_index(code)  # 지수 (001: KOSPI, 201: KOSDAQ)
```

---

## 5. 데이터 흐름

### 5.1 수집 과정

```
1. Kiwoom WebSocket으로부터 체결 데이터 수신
2. 현재 시간대의 바에 데이터 추가
3. save_interval 경과 시 DB에 Upsert
4. TimescaleDB daily_prices 테이블에 저장
```

### 5.2 DB 스키마

```sql
-- daily_prices 테이블 (TimescaleDB Hypertable)
CREATE TABLE daily_prices (
    ticker VARCHAR(6) PRIMARY KEY,
    date DATE PRIMARY KEY,
    open_price FLOAT,
    high_price FLOAT,
    low_price FLOAT,
    close_price FLOAT NOT NULL,
    volume BIGINT NOT NULL,
    foreign_net_buy INTEGER DEFAULT 0,
    inst_net_buy INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 관련 문서

- [Open Architecture](OPEN_ARCHITECTURE.md) - 전체 아키텍처
- [WebSocket 설정](WEBSOCKET.md) - WebSocket 연결 설정
