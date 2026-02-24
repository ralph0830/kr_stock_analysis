# 시장 스캔 종목 선별 조건 완전 리스트

**작성 일시:** 2026-02-06
**대상:** Daytrading Scanner `/api/daytrading/scan` 엔드포인트
**총 점수:** 105점 만점 (7개 체크리스트 × 15점)

---

## 1. 필수 데이터 요구사항 (선제 조건)

### 1.1 종목 기본 정보 (`stocks` 테이블)

종목이 스캔 대상으로 선정되기 위해 다음 조건을 **모두 만족**해야 함:

| 조건 | 필드 | 값 | 설명 |
|------|------|-----|------|
| ETF 아님 | `is_etf` | `False` | ETF 제외 |
| 관리종목 아님 | `is_admin` | `False` | 관리종목 제외 |
| SPAC 아님 | `is_spac` | `False` | SPAC 제외 |
| 채권 아님 | `is_bond` | `False` | 채권 제외 |
| ETF 제외 대상 아님 | `is_excluded_etf` | `False` | 제외 ETF 아님 |
| [선택] 시장 필터 | `market` | `"KOSPI"` / `"KOSDAQ"` | 시장 필터 적용 시 |

**코드 위치:** `scanner.py:129-138`
```python
query = select(StockModel).where(
    StockModel.is_etf == False,
    StockModel.is_admin == False,
    StockModel.is_spac == False,
    StockModel.is_bond == False,
    StockModel.is_excluded_etf == False,
)
```

### 1.2 일봉 데이터 요구사항 (`daily_prices` 테이블)

| 항목 | 최소 요구사항 | 권장 사항 |
|------|--------------|----------|
| 데이터 개수 | **최소 5일** | 20일 이상 |
| 최신 데이터 | 오늘 날짜 | 최근 2일 이내 |
| 필수 필드 | `close_price`, `volume` | `high_price`, `low_price`, `foreign_net_buy`, `inst_net_buy` |

**코드 위치:** `scanner.py:94-97`
```python
prices = self._get_recent_prices(db, stock.ticker, days=20)
if not prices or len(prices) < 5:
    logger.debug(f"Insufficient price data for {stock.ticker}")
    continue  # ← 종목 스킵
```

**데이터 부족 시:** `"데이터 부족"` 체크리스트와 함께 0점 반환

---

## 2. 7개 체크리스트 상세 조건

### 체크리스트 1: 거래량 폭증 (15점)

| 점수 | 조건 | 계산식 |
|------|------|--------|
| 15점 | `current_volume / avg_volume >= 2.0` | 거래량이 평균의 **2배 이상** |
| 8점 | `current_volume / avg_volume >= 1.5` | 거래량이 평균의 **1.5배 이상** |
| 0점 | 그 외 | - |

**평균 거래량 계산:**
- 20일 데이터 있음: 최근 20일 평균
- 5~19일 데이터: 해당 기간 평균
- 5일 미만: 현재 거래량으로 대체 (0점 확률 높음)

**코드 위치:** `scoring.py:166-188`

---

### 체크리스트 2: 모멘텀 돌파 (15점)

| 점수 | 조건 | 설명 |
|------|------|------|
| 15점 | 신고가 갱신 OR 직전 20일 고가 +2% 돌파 | 강한 상승 모멘텀 |
| 8점 | 직전 20일 고가 +1% 돌파 | 약한 상승 모멘텀 |
| 0점 | 그 외 | - |

**신고가 갱신 정의:**
```python
current_price > max(최근 20일 고가들)
```

**20일 고가 계산:** `scoring.py:59-110`
```python
def _calculate_20d_high_low(prices):
    # DailyPrice.high_price 사용 (없으면 close_price)
    high_20d = max(p.high_price or p.close_price for p in prices[:20])
    return high_20d, low_20d
```

**코드 위치:** `scoring.py:190-220`

---

### 체크리스트 3: 박스권 탈출 (15점)

| 점수 | 조건 | 설명 |
|------|------|------|
| 15점 | `current_price >= box_high` | 박스 상단 돌파 |
| 8점 | `current_price >= (box_high + box_low) / 2` | 박스 중간 이상 |
| 0점 | 그 외 | 박스 하단 근처 |

**박스 권의 정의:**
- `box_high`: 최근 20일 최고가
- `box_low`: 최근 20일 최저가

**코드 위치:** `scoring.py:223-243`

---

### 체크리스트 4: 5일선 위 (15점)

| 점수 | 조건 | 설명 |
|------|------|------|
| 15점 | `current_price > ma5` | 현재가가 5일 이동평균보다 높음 |
| 8점 | `current_price`가 `ma5` ±1% 범위 내 | 5일선 근처 |
| 0점 | 그 외 | 5일선 아래 |

**MA5 계산:**
```python
ma5 = sum(최근 5일 종가) / 5
```

**코드 위치:** `scoring.py:246-267`

---

### 체크리스트 5: 기관 매수 (15점)

| 점수 | 조건 | 설명 |
|------|------|------|
| 15점 | `foreign_net_buy + inst_net_buy >= 100억` | 외국인+기관 순매수 100억 이상 |
| 8점 | `foreign_net_buy + inst_net_buy >= 50억` | 외국인+기관 순매수 50억 이상 |
| 0점 | 그 외 | 순매수 미달 또는 매도 |

**데이터 출처:** `daily_prices` 테이블 (최근 5일 합계)

**필드:**
- `foreign_net_buy`: 외국인 순매수 금액 (원)
- `inst_net_buy`: 기관 순매수 금액 (원)

**Fallback:** 데이터 부족 시 `foreign_net_buy = 0`, `inst_net_buy = 0` (0점)

**코드 위치:** `scoring.py:270-288`, `scanner.py:181-221`

---

### 체크리스트 6: 낙폭 과대 후 반등 (15점)

| 점수 | 조건 | 설명 |
|------|------|------|
| 15점 | 2일전 **-3% 이상 하락** → 당일 **+2% 이상 상승** | 강한 반등 |
| 8점 | 2일전 **-1% 이상 하락** → 당일 **양수** | 약한 반등 |
| 0점 | 그 외 | 반등 없음 |

**계산:**
```python
# 2일 전 등락률
prev_change_rate = (전일종가 - 2일전종가) / 2일전종가 × 100

# 당일 등락률
current_change_rate = (현재가 - 전일종가) / 전일종가 × 100
```

**코드 위치:** `scoring.py:291-315`

---

### 체크리스트 7: 섹터 모멘텀 (15점)

| 점수 | 조건 | 설명 |
|------|------|------|
| 15점 | 섹터 내 **상위 20%** 이내 | 섹터 최상위 |
| 8점 | 섹터 내 **상위 40%** 이내 | 섹터 상위권 |
| 0점 | 그 외 | 섹터 중위권 이하 |

**계산 방식:**

1. 같은 섹터 종목들의 최근 5일 수익률 계산
   ```python
   return_pct = (최신가 - 5일전가) / 5일전가 × 100
   ```

2. 수익률 내림차순 정렬 후 순위 확인

3. 순위 백분위 계산
   ```python
   percentile = rank / total_count
   ```

**필수 조건:**
- 종목의 `sector` 필드가 비어있지 않아야 함
- 섹터 내 최소 5개 종목 있어야 함
- 해당 종목의 5일 수익률 계산 가능해야 함

**Fallback:** 섹터 정보 없거나 계산 불가 시 0점

**코드 위치:** `scoring.py:318-423`

---

## 3. 등급 부여 기준

| 등급 | 점수 범위 | 설명 |
|------|----------|------|
| **S** | 90 ~ 105점 | 최상위 추천 |
| **A** | 75 ~ 89점 | 상위 추천 |
| **B** | 60 ~ 74점 | 중간 추천 |
| **C** | 0 ~ 59점 | 추천 안 함 |

**코드 위치:** `scoring.py:556-573`

---

## 4. 최종 선별 요약

### 4.1 종목이 후보로 선정되기 위한 조건

```
1. [필수] stocks 테이블에 존재
2. [필수] is_etf = False, is_admin = False, is_spac = False, is_bond = False
3. [필수] daily_prices 테이블에 최소 5일 이상 데이터
4. [선택] 시장 필터 (KOSPI/KOSDAQ) 만족
```

### 4.2 점수 계산 가능 여부

| 데이터 | 필수 여부 | 최소 개수 |
|--------|----------|----------|
| 종가 (`close_price`) | ✅ 필수 | 5개 |
| 거래량 (`volume`) | ✅ 필수 | 5개 |
| 고가 (`high_price`) | ⚠️ 권장 | 20개 |
| 저가 (`low_price`) | ⚠️ 권장 | 20개 |
| 외국인 순매수 (`foreign_net_buy`) | ⚠️ 권장 | 3개 |
| 기관 순매수 (`inst_net_buy`) | ⚠️ 권장 | 3개 |
| 섹터 정보 (`sector`) | ⚠️ 선택 | - |

### 4.3 최대 점수 기준

| 체크리스트 | 최대 점수 | 최소 데이터 요구 |
|-----------|----------|------------------|
| 거래량 폭증 | 15 | 종가, 거래량 (20일) |
| 모멘텀 돌파 | 15 | 종가, 고가 (20일) |
| 박스권 탈출 | 15 | 종가, 고가, 저가 (20일) |
| 5일선 위 | 15 | 종가 (5일) |
| 기관 매수 | 15 | 외국인/기관 순매수 (5일) |
| 낙폭 과대 | 15 | 종가 (3일) |
| 섹터 모멘텀 | 15 | 종가 (5일) + 섹터 정보 |
| **합계** | **105** | - |

---

## 5. 현재 시스템 상태

### 5.1 데이터베이스 상태 (2026-02-06 기준)

| 테이블 | 레코드 수 | 상태 |
|--------|-----------|------|
| `stocks` | 4,227건 | ✅ 정상 |
| `daily_prices` | **0건** | ❌ 문제 |
| `daytrading_signals` | 0건 | 빈 상태 |

### 5.2 예상 동작

1. **종목 조회:** 4,227종목에서 최대 200종목 조회
2. **일봉 데이터 확인:** `daily_prices`가 0건이므로 **모든 종목이 "데이터 부족"으로 스킵**
3. **결과:** 0건 반환

### 5.3 해결 방안

**단계 1: 일봉 데이터 수집**
```bash
# Kiwoom REST API 또는 KRX에서 일봉 데이터 수집
uv run python scripts/collect_daily_prices.py
```

**단계 2: 수급 데이터 수집**
```bash
# 외국인/기관 순매수 데이터 수집 (기관 매수 점수 계산용)
```

**단계 3: 섹터 정보 업데이트**
```sql
-- stocks 테이블에 sector 정보 업데이트 (섹터 모멘텀 점수 계산용)
UPDATE stocks SET sector = '반도체' WHERE ticker IN '005930';
```

---

## 6. Kiwoom REST API 구현 방법

### 6.1 API 엔드포인트 목록

| API ID | 엔드포인트 | 설명 | 필드 |
|--------|-----------|------|------|
| `ka10015` | `/api/dostk/stkinfo` | 일별거래상세 조회 | `for_netprps`, `orgn_netprps` (외국인/기관 순매수) |
| `ka10081` | `/api/dostk/chart` | 주식일봉차트 조회 | `close_pric`, `high_pric`, `low_pric`, `trde_qty` |
| `ka20006` | `/api/dostk/chart` | 업종일봉 조회 | 섹터 모멘텀 계산용 |

### 6.2 데이터 수집 구현 코드

```python
"""
Kiwoom REST API - 시장 스캔 데이터 수집
작성 일시: 2026-02-06
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class KiwoomDaytradingDataCollector:
    """
    Kiwoom REST API를 사용한 단타 매매 데이터 수집기

    7개 체크리스트 계산을 위한 데이터 수집
    """

    def __init__(self, access_token: str):
        """
        초기화

        Args:
            access_token: Kiwoom REST API 접근 토큰
        """
        self.access_token = access_token
        self.host = 'https://api.kiwoom.com'
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {access_token}',
        }

    # ==========================================================================
    # 1. 일별거래상세 조회 (외국인/기관 순매수 데이터)
    # ==========================================================================

    def get_daily_trade_detail(
        self,
        stk_cd: str,
        strt_dt: str,
        api_id: str = 'ka10015'
    ) -> List[Dict]:
        """
        일별거래상세 조회

        체크리스트 5 (기관 매수) 계산용

        Args:
            stk_cd: 종목 코드 (예: "005930")
            strt_dt: 시작일 (YYYYMMDD)
            api_id: API ID (기본값: ka10015)

        Returns:
            일별거래상세 리스트
            - for_netprps: 외국인 순매수
            - orgn_netprps: 기관 순매수
            - trde_qty: 거래량
        """
        endpoint = '/api/dostk/stkinfo'
        url = self.host + endpoint

        headers = self.headers.copy()
        headers['api-id'] = api_id

        data = {
            'stk_cd': stk_cd,
            'strt_dt': strt_dt
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get('daly_trde_dtl', [])
            else:
                logger.error(f"API Error ({api_id}): {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching daily trade detail for {stk_cd}: {e}")
            return []

    # ==========================================================================
    # 2. 주식일봉차트 조회 (가격, 거래량 데이터)
    # ==========================================================================

    def get_daily_chart(
        self,
        stk_cd: str,
        base_dt: str,
        api_id: str = 'ka10081'
    ) -> List[Dict]:
        """
        주식일봉차트 조회

        체크리스트 1,2,3,4,6 계산용

        Args:
            stk_cd: 종목 코드 (예: "005930")
            base_dt: 기준일 (YYYYMMDD)
            api_id: API ID (기본값: ka10081)

        Returns:
            일봉 차트 데이터 리스트
            - close_pric: 종가
            - high_pric: 고가
            - low_pric: 저가
            - trde_qty: 거래량
        """
        endpoint = '/api/dostk/chart'
        url = self.host + endpoint

        headers = self.headers.copy()
        headers['api-id'] = api_id

        data = {
            'stk_cd': stk_cd,
            'base_dt': base_dt,
            'upd_stkpc_tp': '1'  # 1: 수정주가 적용
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get('stk_dt_pole_chart_qry', [])
            else:
                logger.error(f"API Error ({api_id}): {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching daily chart for {stk_cd}: {e}")
            return []

    # ==========================================================================
    # 3. 업종일봉 조회 (섹터 모멘텀 계산용)
    # ==========================================================================

    def get_sector_chart(
        self,
        inds_cd: str,
        base_dt: str,
        api_id: str = 'ka20006'
    ) -> List[Dict]:
        """
        업종일봉 조회

        체크리스트 7 (섹터 모멘텀) 계산용

        Args:
            inds_cd: 업종 코드 (예: "001" - 코스피 종합)
            base_dt: 기준일 (YYYYMMDD)
            api_id: API ID (기본값: ka20006)

        Returns:
            업종 일봉 데이터 리스트
            - cur_prc: 현재 지수
            - strt_pric: 시작 지수
            - high_pric: 고가 지수
            - low_pric: 저가 지수
        """
        endpoint = '/api/dostk/chart'
        url = self.host + endpoint

        headers = self.headers.copy()
        headers['api-id'] = api_id

        data = {
            'inds_cd': inds_cd,
            'base_dt': base_dt
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get('inds_dt_pole_qry', [])
            else:
                logger.error(f"API Error ({api_id}): {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching sector chart for {inds_cd}: {e}")
            return []

    # ==========================================================================
    # 4. 체크리스트 계산 함수들
    # ==========================================================================

    def calc_foreign_institution_netbuy(self, daily_data: List[Dict]) -> int:
        """
        외국인+기관 순매수 5일 합계 계산

        체크리스트 5 (기관 매수)

        Args:
            daily_data: 일별거래상세 데이터

        Returns:
            5일 합계 (원)
        """
        total = 0
        count = 0
        # 최신 데이터부터 5일
        for day in daily_data[-5:]:
            try:
                foreign = int(day.get('for_netprps', '0'))
                orgn = int(day.get('orgn_netprps', '0'))
                total += foreign + orgn
                count += 1
            except (ValueError, TypeError):
                continue

        logger.debug(f"Foreign+Inst net buy (5d): {total:,} ({count} days)")
        return total

    def calc_moving_average(self, data: List[Dict], days: int = 5) -> float:
        """
        이동평균 계산

        체크리스트 4 (5일선 위)

        Args:
            data: 일봉 차트 데이터
            days: 이동평균 기간

        Returns:
            이동평균가
        """
        if len(data) < days:
            return 0

        closes = []
        for day in data[-days:]:
            try:
                closes.append(int(day['close_pric']))
            except (ValueError, KeyError, TypeError):
                continue

        return sum(closes) / len(closes) if closes else 0

    def analyze_price_volume(self, data: List[Dict]) -> tuple:
        """
        가격/거래량 분석

        체크리스트 1 (거래량 폭증), 2 (모멘텀 돌파), 3 (박스권 탈출)

        Args:
            data: 일봉 차트 데이터 (최신 20일)

        Returns:
            (avg_volume, max_close, max_high, current_close)
        """
        if not data:
            return 0, 0, 0, 0

        closes = []
        highs = []
        volumes = []

        for day in data:
            try:
                closes.append(int(day['close_pric']))
                if day.get('high_pric'):
                    highs.append(int(day['high_pric']))
                volumes.append(int(day['trde_qty']))
            except (ValueError, KeyError, TypeError):
                continue

        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        max_close = max(closes) if closes else 0
        max_high = max(highs) if highs else 0
        current_close = closes[0] if closes else 0

        return avg_volume, max_close, max_high, current_close

    def check_price_rebound(self, data: List[Dict]) -> tuple:
        """
        낙폭 과대 후 반등 체크

        체크리스트 6 (낙폭 과대)

        Args:
            data: 일봉 차트 데이터 (최소 3일 필요)

        Returns:
            (is_rebound_15, is_rebound_8, drop_rate, rise_rate)
        """
        if len(data) < 3:
            return False, False, 0, 0

        try:
            day_2_before = data[-3]
            day_1_before = data[-2]
            day_0 = data[-1]

            close_2_before = int(day_2_before['close_pric'])
            close_1_before = int(day_1_before['close_pric'])
            close_0 = int(day_0['close_pric'])

            # 2일전 대비 1일전 하락률
            drop_rate = (close_1_before - close_2_before) / close_2_before * 100

            # 1일전 대비 당일 상승률
            rise_rate = (close_0 - close_1_before) / close_1_before * 100

            # 15점: 2일전 -3% 이상 하락, 당일 +2% 이상 반등
            is_rebound_15 = (drop_rate <= -3.0 and rise_rate >= 2.0)

            # 8점: 2일전 -1% 이상 하락, 당일 양수
            is_rebound_8 = (drop_rate <= -1.0 and rise_rate > 0)

            return is_rebound_15, is_rebound_8, drop_rate, rise_rate

        except (ValueError, KeyError, TypeError) as e:
            logger.debug(f"Error checking price rebound: {e}")
            return False, False, 0, 0

    def calc_sector_return(self, sector_data: List[Dict]) -> float:
        """
        섹터 5일 수익률 계산

        체크리스트 7 (섹터 모멘텀)

        Args:
            sector_data: 업종 일봉 데이터

        Returns:
            5일 수익률 (%)
        """
        if len(sector_data) < 5:
            return 0

        try:
            # 최신 5일 데이터
            recent_5d = sector_data[-5:]

            # 첫날과 마지막날의 지수
            start_idx = recent_5d[0].get('cur_pric', 0) or recent_5d[0].get('strt_pric', 0)
            end_idx = recent_5d[-1].get('cur_pric', 0)

            start = int(start_idx)
            end = int(end_idx)

            if start > 0:
                return_pct = (end - start) / start * 100
                return return_pct
        except (ValueError, KeyError, TypeError) as e:
            logger.debug(f"Error calculating sector return: {e}")

        return 0

    # ==========================================================================
    # 5. 종목별 전체 데이터 수집
    # ==========================================================================

    def collect_stock_data(self, stk_cd: str, days: int = 20) -> Dict:
        """
        단일 종목 전체 데이터 수집

        Args:
            stk_cd: 종목 코드
            days: 조회 일수 (기본값: 20)

        Returns:
            수집된 데이터 딕셔너리
        """
        # 날짜 계산
        base_dt = datetime.now().strftime('%Y%m%d')
        start_dt = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        # 1) 일봉 차트 데이터 조회
        chart_data = self.get_daily_chart(stk_cd, base_dt)

        # 2) 일별거래상세 조회
        trade_data = self.get_daily_trade_detail(stk_cd, start_dt)

        if not chart_data:
            logger.warning(f"No chart data for {stk_cd}")
            return {}

        # 3) 계산 수행
        avg_vol, max_close, max_high, current_close = self.analyze_price_volume(chart_data[-20:])
        ma5 = self.calc_moving_average(chart_data, 5)
        net_buy = self.calc_foreign_institution_netbuy(trade_data)
        is_rebound_15, is_rebound_8, drop_rate, rise_rate = self.check_price_rebound(chart_data)

        # 4) 체크리스트 점수 계산
        scores = {}

        # 체크리스트 1: 거래량 폭증
        current_vol = int(chart_data[0]['trde_qty']) if chart_data else 0
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        if vol_ratio >= 2.0:
            scores['volume_spike'] = 15
        elif vol_ratio >= 1.5:
            scores['volume_spike'] = 8
        else:
            scores['volume_spike'] = 0

        # 체크리스트 2: 모멘텀 돌파 (신고가 갱신)
        is_new_high = current_close >= max_close
        if is_new_high:
            scores['momentum'] = 15
        elif current_close >= max_high * 1.02:
            scores['momentum'] = 15
        elif current_close >= max_high * 1.01:
            scores['momentum'] = 8
        else:
            scores['momentum'] = 0

        # 체크리스트 3: 박스권 탈출
        if current_close >= max_high:
            scores['box_breakout'] = 15
        else:
            scores['box_breakout'] = 0

        # 체크리스트 4: 5일선 위
        if current_close > ma5:
            scores['ma5_above'] = 15
        elif abs(current_close - ma5) / ma5 * 100 <= 1.0:
            scores['ma5_above'] = 8
        else:
            scores['ma5_above'] = 0

        # 체크리스트 5: 기관 매수
        net_buy_ek = net_buy / 100000000  # 원 → 억
        if net_buy_ek >= 100:
            scores['institution_buy'] = 15
        elif net_buy_ek >= 50:
            scores['institution_buy'] = 8
        else:
            scores['institution_buy'] = 0

        # 체크리스트 6: 낙폭 과대
        if is_rebound_15:
            scores['oversold_bounce'] = 15
        elif is_rebound_8:
            scores['oversold_bounce'] = 8
        else:
            scores['oversold_bounce'] = 0

        # 체크리스트 7: 섹터 모멘텀 (별도 섹터 데이터 필요)
        scores['sector_momentum'] = 0  # TODO: 섹터 데이터 추가 시 구현

        # 총 점수
        total_score = sum(scores.values())

        return {
            'ticker': stk_cd,
            'current_price': current_close,
            'avg_volume': int(avg_vol),
            'current_volume': current_vol,
            'volume_ratio': round(vol_ratio, 2),
            'ma5': int(ma5),
            'foreign_inst_net_buy_ek': round(net_buy_ek, 2),
            'drop_rate': round(drop_rate, 2),
            'rise_rate': round(rise_rate, 2),
            'is_new_high': is_new_high,
            'scores': scores,
            'total_score': total_score,
            'grade': self._get_grade(total_score),
        }

    def _get_grade(self, score: int) -> str:
        """점수에 따른 등급 반환"""
        if score >= 90:
            return "S"
        elif score >= 75:
            return "A"
        elif score >= 60:
            return "B"
        else:
            return "C"


# =============================================================================
# 6. 메인 실행 예시
# =============================================================================

def main():
    """
    메인 실행 예시

    사용법:
        python kiwoom_daytrading_collector.py
    """
    import os

    # 환경 변수 또는 직접 입력
    ACCESS_TOKEN = os.getenv('KIWOOM_ACCESS_TOKEN', '[접근 토큰]')

    # 수집기 초기화
    collector = KiwoomDaytradingDataCollector(ACCESS_TOKEN)

    # 삼성전자 예시
    STOCK_CODE = '005930'

    # 데이터 수집
    result = collector.collect_stock_data(STOCK_CODE, days=20)

    # 결과 출력
    print(f"\n=== {STOCK_CODE} 분석 결과 ===")
    print(f"현재가: {result['current_price']:,}원")
    print(f"거래량 비율: {result['volume_ratio']:.2f}x")
    print(f"5일 이동평균: {result['ma5']:,}원")
    print(f"외국인+기관 순매수: {result['foreign_inst_net_buy_ek']:.1f}억")
    print(f"신고가 갱신: {result['is_new_high']}")
    print(f"\n=== 체크리스트 점수 ===")
    for name, score in result['scores'].items():
        print(f"{name}: {score}점")
    print(f"\n총점: {result['total_score']}점 ({result['grade']}등급)")

    # 조건 충족 여부
    if result['total_score'] >= 75:
        print(f"\n✅ {STOCK_CODE}은 매수 추천 종목입니다.")
    else:
        print(f"\n❌ {STOCK_CODE}은 조건 미충족입니다.")


if __name__ == '__main__':
    main()
```

### 6.3 DB 저장 연동

```python
"""
DB 저장 연동 예시
"""

def save_to_database(result: Dict, db_session):
    """
    수집된 데이터를 DB에 저장

    Args:
        result: collect_stock_data() 반환값
        db_session: DB 세션
    """
    from src.database.models import DailyPrice
    from datetime import datetime

    # DailyPrice 저장
    daily_price = DailyPrice(
        ticker=result['ticker'],
        date=datetime.now().date(),
        close_price=result['current_price'],
        volume=result['current_volume'],
        # ... 기타 필드
    )
    db_session.add(daily_price)
    db_session.commit()
```

### 6.4 전체 종목 수집 스크립트

```python
"""
전체 종목 데이터 수집 스크립트
파일: scripts/collect_daytrading_data.py
"""

import asyncio
from typing import List
from kiwoom_daytrading_collector import KiwoomDaytradingDataCollector
from src.database.session import get_db_session_sync
from src.repositories.stock_repository import StockRepository


async def collect_all_stocks():
    """
    전체 종목 데이터 수집
    """
    ACCESS_TOKEN = '[접근 토큰]'
    collector = KiwoomDaytradingDataCollector(ACCESS_TOKEN)

    with get_db_session_sync() as db:
        stock_repo = StockRepository(db)

        # 종목 조회
        stocks = stock_repo.get_all_active()  # ETF, 관리종목 제외

        results = []
        for i, stock in enumerate(stocks):
            print(f"[{i+1}/{len(stocks)}] {stock.ticker} {stock.name}")

            # API 호출 (속도 제한 고려)
            result = collector.collect_stock_data(stock.ticker)

            if result and result['total_score'] >= 60:  # 60점 이상만 저장
                results.append(result)

            # Kiwoom API 속도 제한: 0.5초 대기
            await asyncio.sleep(0.5)

        print(f"\n총 {len(results)}개 종목 수집 완료")
        return results


if __name__ == '__main__':
    asyncio.run(collect_all_stocks())
```

---

## 7. 관련 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| 스캐너 로직 | `/services/daytrading_scanner/scanner.py` | 시장 스캔 메인 로직 |
| 점수 계산 | `/services/daytrading_scanner/models/scoring.py` | 7개 체크리스트 점수 계산 |
| DB 모델 | `/src/database/models.py` | Stock, DailyPrice 모델 |
| Kiwoom API | `/src/kiwoom/rest_api.py` | Kiwoom REST API 클라이언트 |

---

**작성자:** Claude Code (Full-Stack Integration Specialist)
**문서 경로:** `/home/ralph/work/python/kr_stock_analysis/docs/report/market_scan_conditions_20260206.md`
