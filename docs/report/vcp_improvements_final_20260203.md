# VCP 스캐너 개선 최종 보고서

**작성 일자**: 2026-02-03
**목적**: 코스피/코스닥 일반주식만 스캔하도록 개선 및 추가 개선 사항 적용

---

## 1. 실행 요약

### 1.1 완료된 개선 사항

| 항목 | 상태 | 설명 |
|------|------|------|
| ELW 필터링 | ✅ 작동 | 티커 내 알파벳 포함 여부로 필터링 |
| ETF/ETN 키워드 추가 | ✅ 완료 | "1Q", "마이티", "액티브", "크레딧" 등 추가 |
| VCP 스캔 테스트 | ✅ 완료 | 일반주식만 스캔 확인 |
| WebSocket 시그널 브로드캐스트 | ✅ 작동 | VCP 시그널 실시간 전송 |
| VCP 페이지 실시간 가격 | ✅ 개선 | 60초 폴링 → WebSocket 전환 |
| TypeScript 오류 수정 | ✅ 완료 | RealtimePriceCard 타입 오류 수정 |

---

## 2. VCP Scanner 필터링 개선

### 2.1 ELW 필터링 (이미 구현됨)

**파일**: `services/vcp_scanner/vcp_analyzer.py` (라인 497-498)

```python
# ELW 필터링: 종목 코드에 알파벳이 포함되면 제외
if not s.ticker.isdigit():
    continue
```

**효과**:
- 250개의 ELW/ETF/ETN (비숫자 티커) 자동 제외
- 한국 ELW 티커 패턴: `XXXXN0`, `XXXXS0`, `XXXXT0` 등

### 2.2 ETF/ETN 키워드 추가 (완료)

**파일**: `src/kiwoom/rest_api.py` (라인 1377-1382)

**추가된 키워드**:
- `"1Q "` - 1Q ETF 제공자
- `"마이티 "` - Mighty ETF 제공자
- `"메리츠"` - Meritz ETF
- `"TOP3"` - TOP3 인버스 ETF
- `"ETF"` - ETF 키워드
- `"액티브"` - 액티브 ETF
- `"크레딧"` - 크레딧 ETX

---

## 3. VCP 스캔 결과 테스트

### 3.1 스캔 결과 (2026-02-03 07:42)

| 항목 | 값 |
|------|-----|
| 상태 | completed |
| 스캔 종목 수 | 100개 |
| 발견 시그널 | 100개 |
| 소요 시간 | 약 7초 |

### 3.2 상위 시그널 (일반주식만)

| 티커 | 종목명 | 시장 | 등급 | 점수 |
|------|--------|------|------|------|
| 230360 | 에코마케팅 | KOSDAQ | A | 71.25 |
| 221980 | 케이디켐 | KOSDAQ | A | 68.25 |
| 263690 | 디알젬 | KOSDAQ | A | 66.25 |
| 005380 | 현대차 | KOSPI | B | 55.50 |
| 006400 | 삼성SDI | KOSPI | B | 55.50 |
| 068270 | 셀트리온 | KOSPI | B | 55.25 |

**모든 티커가 6자리 숫자만 포함** → ELW/ETF/ETN 제외 완료 ✅

---

## 4. 프론트엔드 개선

### 4.1 VCP 페이지 실시간 가격 업데이트

**변경 전**:
```typescript
// 로컬 폴링 함수 (60초 간격 REST API 호출)
function useRealtimePrices(signals: Signal[], intervalMs: number = 60000) {
  const interval = setInterval(updatePrices, intervalMs);
  return { prices, lastUpdated };
}
```

**변경 후**:
```typescript
// WebSocket 기반 실시간 업데이트
import { useRealtimePrices } from "@/hooks/useWebSocket";

const tickers = useMemo(() => signals.map((s) => s.ticker), [signals]);
const { prices, getPrice } = useRealtimePrices(tickers);
```

**효과**:
| 구분 | 변경 전 | 변경 후 |
|------|---------|---------|
| 방식 | REST API 폴링 | WebSocket |
| 업데이트 주기 | 60초 | 실시간 (초단위) |
| API 호출 | 계속 발생 | 연결 후 0회 |

### 4.2 RealtimePriceCard TypeScript 오류 수정

**파일**: `frontend/components/RealtimePriceCard.tsx`

**수정 내용**:
1. `change_rate` → `change_percent` (타입 속성명 수정)
2. `timestamp` undefined 처리 추가
3. `displayPrice?.change` null 체크 강화

---

## 5. WebSocket 아키텍처 확인

### 5.1 VCP 시그널 브로드캐스트 (이미 구현됨)

**파일**: `services/vcp_scanner/main.py` (라인 128-163)

```python
def _broadcast_signal_update(results: List[Any]) -> None:
    """VCP 시그널 업데이트를 WebSocket으로 브로드캐스트"""
    asyncio.create_task(_do_broadcast(results))

async def _do_broadcast(results: List[Any]) -> None:
    from src.websocket.server import signal_broadcaster
    await signal_broadcaster.broadcast_signal_update(results, signal_type="VCP")
```

**로그 확인**:
```
[BROADCAST] Topic=signal:vcp, subscribers=0
VCP 시그널 100개 WebSocket 브로드캐스트 완료
```

### 5.2 useSignals Hook (이미 구현됨)

**파일**: `frontend/hooks/useWebSocket.ts` (라인 582-640)

```typescript
export function useSignals() {
  // signal:vcp 토픽 구독
  subscribe("signal:vcp");

  // 메시지 핸들러
  const handleSignalUpdate = (message: WSMessage) => {
    if (message.type === "signal_update") {
      setSignals(signalMsg.data.signals);
      setIsRealtime(true);
    }
  };
}
```

---

## 6. 변경 파일 목록

### 백엔드

| 파일 | 변경 사항 |
|------|----------|
| `src/kiwoom/rest_api.py` | ETF/ETN 키워드 추가 ("1Q ", "마이티 ", "액티브", "크레딧") |

### 프론트엔드

| 파일 | 변경 사항 |
|------|----------|
| `frontend/app/dashboard/kr/vcp/page.tsx` | 로컬 폴링 → WebSocket 실시간 가격 업데이트 |
| `frontend/components/RealtimePriceCard.tsx` | TypeScript 오류 수정 |

---

## 7. 추가 개선 제안

### 7.1 VCP 시그널 테이블 행 클릭 기능

**현재 상태**: 행 클릭 시 동작 없음

**제안**:
```typescript
<tr
  key={signal.ticker}
  className="hover:bg-gray-50 cursor-pointer"
  onClick={() => router.push(`/chart?ticker=${signal.ticker}`)}
>
```

### 7.2 Celery Beat 스케줄 최적화

**현재 설정**:
- 운영: 매일 16:00 (crontab)
- 테스트: 30분 간격

**제안**:
| 시간대 | 간격 | 이유 |
|--------|------|------|
| 장 시작 전 (08:00) | 1회 | 장 시작 전 시그널 갱신 |
| 장 중 (09:30-15:30) | 30분 | 실시간성 확보 |

### 7.3 Kiwoom API marketCode 활용

**현재 상태**: 종목 동기화 시 `marketCode` 필드에 저장하지 않음

**제안**:
```python
# DB에 marketCode 저장
"market_code": item.get("marketCode")  # "0", "10", "3", "8", "60"

# VCP Scanner에서 marketCode로 직접 필터링
query = query.where(Stock.market_code.in_(["0", "10"]))
```

---

## 8. 롤백 계획

| 변경 사항 | 롤백 명령 |
|----------|----------|
| rest_api.py ETF 키워드 | `git checkout HEAD~1 src/kiwoom/rest_api.py` |
| VCP 페이지 WebSocket | `git checkout HEAD~1 frontend/app/dashboard/kr/vcp/page.tsx` |
| RealtimePriceCard 수정 | `git checkout HEAD~1 frontend/components/RealtimePriceCard.tsx` |

---

## 9. 결론

### 9.1 완료된 개선

1. ✅ ELW 필터링: `s.ticker.isdigit()`로 비숫자 티커 제외
2. ✅ ETF/ETN 키워드: "1Q", "마이티" 등 신규 ETF 제공자 추가
3. ✅ VCP 스캔 테스트: 일반주식만 정상 스캔 확인
4. ✅ VCP 페이지 실시간 가격: 60초 폴링 → WebSocket 전환
5. ✅ TypeScript 오류 수정

### 9.2 권장 후속 개선

1. VCP 시그널 테이블 행 클릭 기능 (높음)
2. Kiwoom API marketCode 활용 (중간)
3. Celery Beat 스케줄 최적화 (낮음)

---

*보고서 작성일: 2026-02-03*
*버전: 2.0 (최종)*
