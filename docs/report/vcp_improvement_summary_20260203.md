# VCP 스캐너 개선 보고서

**작성 일자**: 2026-02-03
**목적**: 코스피/코스닥 일반주식만 스캔하도록 개선

---

## 1. 실행 요약

### 1.1 개선 완료 사항

| 항목 | 상태 | 설명 |
|------|------|------|
| ELW 필터링 | ✅ 완료 | 티커 내 알파벳 포함 여부로 필터링 |
| ETF/ETN 키워드 추가 | ✅ 완료 | "1Q", "마이티", "액티브", "크레딧" 추가 |
| VCP 스캔 테스트 | ✅ 완료 | 일반주식만 스캔 확인 |
| WebSocket 브로드캐스트 | ✅ 작동 | VCP 시그널 실시간 전송 |

### 1.2 개선 전후 비교

**개선 전:**
```
0103T0 - 1Q K소버린AI ❌ ETF
0120X0 - 유진 챔피언중단기크레딧 X클래스 ❌ ETX
0131V0 - 1Q 미국우주항공테크 ❌ ETF
0150K0 - KoAct 수소전력ESS인프라액티브 ❌ ETF
```

**개선 후:**
```
005380 - 현대차 ✅ 일반주식
006400 - 삼성SDI ✅ 일반주식
068270 - 셀트리온 ✅ 일반주식
230360 - 에코마케팅 ✅ 일반주식
```

---

## 2. 구현된 개선 사항

### 2.1 VCP Scanner ELW 필터링

**파일**: `services/vcp_scanner/vcp_analyzer.py` (라인 497-498)

```python
# ELW 필터링: 종목 코드에 알파벳이 포함되면 제외
if not s.ticker.isdigit():
    continue
```

**효과**:
- 250개의 ELW/ETF/ETN (비숫자 티커) 자동 제외
- 한국 ELW 티커 패턴: `XXXXN0`, `XXXXS0`, `XXXXT0` 등

### 2.2 ETF/ETN 키워드 추가

**파일**: `src/kiwoom/rest_api.py` (라인 1377-1382)

**변경 전**:
```python
excluded_prefixes = ["TIGER ", "SOL ", "ACE ", "KIWOOM ", "KODEX ", "TREF ", ...]
excluded_keywords = ["ETN", "인버스", "TOP10", "TOP5", "레버리지", "리츠"]
```

**변경 후**:
```python
excluded_prefixes = ["TIGER ", "SOL ", ..., "1Q ", "마이티 ", "메리츠"]
excluded_keywords = ["ETN", "인버스", "TOP10", "TOP5", "TOP3", "레버리지", "리츠", "ETF", "액티브", "크레딧"]
```

**추가된 키워드**:
- `"1Q "` - 1Q ETF 제공자
- `"마이티 "` - Mighty ETF 제공자
- `"메리츠"` - Meritz ETF
- `"TOP3"` - TOP3 인버스 ETF
- `"ETF"` - ETF 키워드
- `"액티브"` - 액티브 ETF
- `"크레딧"` - 크레딧 ETX

---

## 3. 테스트 결과

### 3.1 VCP 스캔 결과 (2026-02-03 07:42)

```json
{
  "status": "completed",
  "scanned_count": 100,
  "found_signals": 100,
  "started_at": "2026-02-03T07:42:06.015134",
  "completed_at": "2026-02-03T07:42:13.257606"
}
```

### 3.2 상위 시그널 (일반주식만)

| 티커 | 종목명 | 시장 | 등급 | 점수 |
|------|--------|------|------|------|
| 230360 | 에코마케팅 | KOSDAQ | A | 71.25 |
| 221980 | 케이디켐 | KOSDAQ | A | 68.25 |
| 263690 | 디알젬 | KOSDAQ | A | 66.25 |
| 228850 | 레이언스 | KOSDAQ | A | 65.25 |
| 005380 | 현대차 | KOSPI | B | 55.50 |
| 006400 | 삼성SDI | KOSPI | B | 55.50 |
| 068270 | 셀트리온 | KOSPI | B | 55.25 |

### 3.3 필터링 검증

**DB 분석 결과**:
| 티커 타입 | 개수 | 필터링 여부 |
|-----------|------|-----------|
| HAS_ALPHA (ELW/ETF) | 250개 | ✅ 제외됨 |
| NUMERIC_ONLY (일반주식) | 3,978개 | ✅ 스캔 대상 |

---

## 4. 추가 개선 제안

### 4.1 WebSocket 실시간 가격 업데이트 (권장)

**현재 상태**:
- VCP 페이지: 60초 폴링 (REST API)
- WebSocket PriceBroadcaster: 작동 중
- `useRealtimePrices()` Hook: 존재하지만 VCP 페이지에서 미사용

**개선 방안**:
```typescript
// frontend/app/dashboard/kr/vcp/page.tsx
import { useRealtimePrices } from "@/hooks/useWebSocket";

const tickers = signals.map(s => s.ticker);
useRealtimePrices(tickers);  // WebSocket으로 실시간 업데이트
```

**효과**:
- 진정한 실시간 가격 업데이트 (초단위)
- 불필요한 API 호출 제거

### 4.2 VCP 시그널 테이블 행 클릭 기능

**현재 상태**:
- VCP 시그널 테이블 행 클릭 시 동작 없음

**개선 방안**:
```typescript
<tr
  key={signal.ticker}
  className="hover:bg-gray-50 cursor-pointer"
  onClick={() => router.push(`/chart?ticker=${signal.ticker}`)}
>
```

### 4.3 Kiwoom API marketCode 활용 강화

**현재 상태**:
- 종목 동기화 시 `marketCode` 필드에 저장하지 않음
- Kiwoom API는 `0`=KOSPI, `10`=KOSDAQ, `3`=ELW, `8`=ETF, `60`=ETN 제공

**개선 방안**:
```python
# DB에 marketCode 저장
{
    "market_code": item.get("marketCode"),  # "0", "10", "3", "8", "60"
}

# VCP Scanner에서 marketCode로 직접 필터링
query = query.where(Stock.market_code.in_(["0", "10"]))
```

### 4.4 Celery Beat 스케줄 최적화

**현재 설정**:
- 운영: 매일 16:00 (crontab)
- 테스트: 30분 간격

**제안**:
| 시간대 | 간격 | 이유 |
|--------|------|------|
| 장 시작 전 (08:00) | 1회 | 장 시작 전 시그널 갱신 |
| 장 중 (09:30-15:30) | 30분 | 실시간성 확보 |
- 장 마감 후 (15:30) | 1회 | 마감 후 시그널 확정

---

## 5. 롤백 계획

| 변경 사항 | 롤백 명령 |
|----------|----------|
| rest_api.py ETF 키워드 | `git checkout HEAD~1 src/kiwoom/rest_api.py` |
| VCP Analyzer ELW 필터 | `git checkout HEAD~1 services/vcp_scanner/vcp_analyzer.py` |

---

## 6. 결론

### 6.1 완료된 개선

1. ✅ ELW 필터링: `s.ticker.isdigit()`로 비숫자 티커 제외
2. ✅ ETF/ETN 키워드: "1Q", "마이티" 등 신규 ETF 제공자 추가
3. ✅ VCP 스캔 테스트: 일반주식만 정상 스캔 확인

### 6.2 권장后续 개선

1. WebSocket 실시간 가격 업데이트 (높음)
2. VCP 시그널 테이블 행 클릭 기능 (중간)
3. Kiwoom API marketCode 활용 (중간)

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
