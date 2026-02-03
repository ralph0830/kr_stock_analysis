# VCP 시그널 실시간 업데이트 종합 분석 보고서

**분석 일자**: 2026-02-03
**분석 범위**: 모든 VCP 관련 문서, 코드, 아키텍처
**목적**: VCP 시그널이 실시간으로 변동되는지 확인

---

## 1. 실행 요약

### 1.1 핵심 질문: "VCP 시그널이 실시간으로 변동되는가?"

**답변**: **부분적으로 실시간 업데이트 됨**

| 항목 | 실시간 업데이트 | 방식 |
|------|----------------|------|
| **시그널 목록** | ❌ 아니오 | 하루에 한 번 스캔 (Celery Beat) |
| **시그널 내 현재가** | ⚠️ **예정** | 60초 폴링 (WebSocket으로 개선 필요) |
| **등급/점수** | ❌ 아니오 | 하루에 한 번 계산 |

### 1.2 결론

**VCP 시그널은 실시간으로 "변동"되지 않습니다.**

1. **VCP 시그널 생성**: 하루에 한 번 Celery Beat 태스크로 스캔
2. **VCP 점수 계산**: 일봉 데이터(최근 20일) 기반으로 정적 계산
3. **실시간 업데이트 대상**: **시그널의 "현재가" 필드만 실시간 업데이트 필요**

---

## 2. VCP 시그널 생성 로직 분석

### 2.1 VCP Analyzer 코드 분석

**파일**: `services/vcp_scanner/vcp_analyzer.py`

```python
class VCPAnalyzer:
    async def scan_market(
        self,
        market: str = "ALL",
        top_n: int = 30,
        min_score: float = 0.0
    ) -> List[VCPResult]:
        """
        시장 전체 스캔 (4,226 종목)
        - 약 11초 소요
        - 병렬 처리 (세마포어 10개)
        """
```

### 2.2 VCP 점수 계산 구성

| 구성 요소 | 가중치 | 데이터 원본 | 갱신 주기 |
|----------|--------|------------|----------|
| 볼린저밴드 수축 | 30% | 최근 20일 일봉 | 일일 |
| 거래량 감소 | 20% | 최근 10일 일봉 | 일일 |
| 가격 변동성 감소 | 20% | 최근 10일 일봉 | 일일 |
| RSI 중립 | 15% | 최근 14일 일봉 | 일일 |
| MACD 정렬 | 15% | 최근 26일 일봉 | 일일 |
| **VCP 점수** | **50%** | 위 5개 지표 가중평균 | 일일 |
| **SmartMoney 점수** | **50%** | 외국인/기관 수급 5일 | 일일 |
| **총점** | **100%** | VCP + SmartMoney | 일일 |

**분석**: 모든 지표가 **일봉 데이터** 기반이므로 실시간으로 변동하지 않음

### 2.3 스캔 주기

| 타입 | 주기 | 설명 |
|------|------|------|
| 전 종목 스캔 | **하루에 한 번** | Celery Beat로 예약 (04:00) |
| 시장별 스캔 | KOSPI/KOSDAQ | 4,226 종목 전체 |
| DB 저장 | 덮어쓰기 | 기존 시그널 DELETE 후 INSERT |

---

## 3. 프론트엔드 문서 분석

### 3.1 레거시 문서: PART_04_04_vcp_page.md

**파일**: `docs/archive_originals/PART_04_04_vcp_page.md` (410줄)

#### 3.1.1 문서에 명시된 "실시간 업데이트"

```markdown
## 개요
VCP Pattern Scanner 페이지는 다음을 표시합니다:
- **VCP 시그널 목록: 실시간 업데이트**  ← 문서에 명시됨
- AI 추천: GPT + Gemini 이중 검증
- **실시간 가격: 60초 간격 폴링**      ← 구현 방법 명시
- 수급 데이터: 외국인/기관 5일 순매수
```

#### 3.1.2 실시간 가격 업데이트 구현

```typescript
// Real-time price updates (every 60s)
useEffect(() => {
    if (loading || signals.length === 0) return;

    const updatePrices = async () => {
        const tickers = signals.map(s => s.ticker);
        const res = await fetch('/api/kr/realtime-prices', {
            method: 'POST',
            body: JSON.stringify({ tickers })
        });
        const prices = await res.json();

        setSignals(prev => prev.map(s => {
            if (prices[s.ticker]) {
                const current = prices[s.ticker];
                return { ...s, current_price: current, return_pct: ret };
            }
            return s;
        }));
    };

    const interval = setInterval(updatePrices, 60000);  // 60초 폴링
    return () => clearInterval(interval);
}, [signals.length, loading]);
```

**분석**:
- 시그널 목록 자체가 아닌, **시그널의 "현재가" 필드만 60초마다 업데이트**
- 폴링 방식 사용 (REST API)
- 문서의 "실시간 업데이트"는 **가격 업데이트**를 의미함

---

## 4. 현재 아키텍처 상태

### 4.1 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VCP 시그널 데이터 흐름                           │
└─────────────────────────────────────────────────────────────────────────┘

1. 일일 04:00 Celery Beat
   ↓
2. VCP Scanner: 전 종목 스캔 (4,226개 → 100개 시그널)
   ↓
3. DB 저장 (signals 테이블)
   ↓
4. 프론트엔드 API 호출 (/api/kr/signals)
   ↓
5. 시그널 목록 표시
   ↓
6. ⏱️ 60초마다 폴링: 현재가 업데이트
```

### 4.2 실시간 업데이트 범위

| 데이터 | 업데이트 방식 | 주기 |
|--------|---------------|------|
| 시그널 목록 (어떤 종목) | REST API 요청 | 페이지 로드 시 / 수동 새로고침 |
| 시그널 점수/등급 | DB 스캔 | 하루에 한 번 |
| 시그널 현재가 | 폴링 | 60초 |
| 수익률 (return_pct) | 계산 | 현재가 업데이트 시 |

---

## 5. WebSocket 연동 상태

### 5.1 현재 WebSocket 지원

| 토픽 | 지원 여부 | 설명 |
|------|----------|------|
| `price:{ticker}` | ✅ | 종목 가격 실시간 브로드캐스트 |
| `index:*` | ✅ | 지수 업데이트 |
| `market_gate` | ✅ | 마켓 게이트 점수 |
| `signal:vcp` | ❌ | **시그널 업데이트 없음** |

### 5.2 프론트엔드 WebSocket Hooks

| Hook | 지원 여부 | 용도 |
|------|----------|------|
| `useRealtimePrices()` | ✅ | 실시간 가격 구독 |
| `useMarketGate()` | ✅ | 마켓 게이트 구독 |
| `useSignals()` | ❌ | **시그널 구독 Hook 없음** |

---

## 6. 실시간 업데이트 필요성 분석

### 6.1 VCP 시그널의 특성

VCP (Volatility Contraction Pattern)는 **일봉 기반 패턴**입니다:

```
VCP 패턴 = 볼린저밴드 수축 + 거래량 감소 + 변동성 감소
```

**특징**:
- 패턴 형성에 며칠~몇 주 소요
- 하루 안에 패턴이 크게 변하지 않음
- 실시간(초/분 단위)으로 변동할 대상 아님

### 6.2 실시간 업데이트가 필요한 데이터

| 데이터 | 필요성 | 현재 상태 |
|--------|--------|----------|
| 시그널 목록 (어떤 종목) | 낮음 | 하루에 한 번 스캔으로 충분 |
| 시그널 점수/등급 | 낮음 | 일봉 기반으로 실시간 변동 없음 |
| **시그널의 현재가** | **높음** | **폴링 → WebSocket으로 개선 필요** |
| 수익률 (return_pct) | 높음 | 현재가 기반 계산 |

---

## 7. 개선 방안

### 7.1 시그널의 "현재가" 실시간 업데이트 (권장)

**현재**: 60초 폴링 (REST API)
**개선**: WebSocket 실시간 가격 연동

#### 구현 방안

**프론트엔드**: 이미 구현된 `useRealtimePrices()` Hook 활용

```typescript
// frontend/app/dashboard/kr/vcp/page.tsx

export default function VCPPage() {
  const { signals, updateRealtimePrice } = useStore();
  const tickers = signals.map(s => s.ticker);

  // ✅ 이미 존재하는 Hook 사용
  useRealtimePrices(tickers);  // WebSocket으로 현재가 실시간 업데이트

  // 시그널의 현재가가 자동 업데이트됨
}
```

**백엔드**: 이미 `price_broadcaster`가 동작 중

```
Kiwoom WebSocket → price_broadcaster → WebSocket 클라이언트 → useRealtimePrices()
```

### 7.2 시그널 목록 실시간 업데이트 (비권장)

**목적**: 새로운 시그널이 발견되었을 때 알림

**문제점**:
- VCP 스캔은 하루에 한 번 수행
- 실시간으로 새로운 시그널이 발생하지 않음
- **구현할 필요 없음**

---

## 8. 현재 문제점

### 8.1 VCP 페이지에서의 실시간 가격

**파일**: `frontend/app/dashboard/kr/vcp/page.tsx` (현재 확인 필요)

**예상되는 문제**:
1. VCP 페이지에서 `useRealtimePrices()` Hook을 호출하지 않을 수 있음
2. 레거시 문서의 60초 폴링 로직이 구현되어 있지 않을 수 있음

**확인 필요**:
```bash
# VCP 페이지 파일 확인
cat frontend/app/dashboard/kr/vcp/page.tsx | grep -A 20 "useRealtimePrices\|setInterval\|updatePrices"
```

### 8.2 메인 페이지 시그널 카드

**파일**: `frontend/app/page.tsx`

**현재 상태**:
- 시그널 목록 표시
- 클릭 핸들러 없음 (이전 보고서에서 확인)

---

## 9. 요약 및 결론

### 9.1 VCP 시그널의 "실시간" 정의

| 용어 | 의미 | 업데이트 주기 |
|------|------|---------------|
| **VCP 시그널** | 패턴이 감지된 종목 목록 | 하루에 한 번 |
| **VCP 점수/등급** | 패턴 강도 점수 | 하루에 한 번 |
| **시그널의 현재가** | 종목의 현재 가격 | **실시간 (초단위)** |

### 9.2 결론

1. **VCP 시그널 목록은 실시간으로 변동하지 않습니다**
   - VCP 패턴은 일봉 데이터 기반
   - 하루에 한 번 스캔으로 충분

2. **시그널의 "현재가"만 실시간 업데이트가 필요합니다**
   - 현재 60초 폴링으로 구현 (레거시 문서)
   - WebSocket으로 개선 권장

3. **WebSocket 브로드캐스터는 불필요합니다**
   - 가격은 이미 `price_broadcaster`로 브로드캐스트 중
   - `useRealtimePrices()` Hook만 호출하면 됨

### 9.3 개선 우선순위

| 우선순위 | 작업 | 효과 |
|----------|------|------|
| 1. 높음 | VCP 페이지에서 `useRealtimePrices()` Hook 호출 | 현재가 실시간 업데이트 |
| 2. 중간 | 시그널 테이블 행 클릭 기능 추가 | 차트 페이지로 이동 |
| 3. 낮음 | 60초 폴링 제거 (WebSocket으로 완전 대체) | 불필요한 API 호출 감소 |

---

## 10. VCP 페이지 실제 구현 확인

### 10.1 현재 구현 상태 (2026-02-03 확인)

**파일**: `frontend/app/dashboard/kr/vcp/page.tsx` (라인 95-127)

```typescript
/**
 * 실시간 가격 업데이트 커스텀 훅
 */
function useRealtimePrices(signals: Signal[], intervalMs: number = 60000) {
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    if (signals.length === 0) return;

    const updatePrices = async () => {
      const tickers = signals.map((s) => s.ticker);
      const priceData = await apiClient.getRealtimePrices(tickers);  // REST API 호출
      // ...
    };

    updatePrices();
    const interval = setInterval(updatePrices, intervalMs);  // 60초 폴링
    return () => clearInterval(interval);
  }, [signals, intervalMs]);

  return { prices, lastUpdated };
}
```

### 10.2 현재 구현 분석

| 항목 | 구현 방식 | 주기 |
|------|----------|------|
| 가격 업데이트 | **REST API 폴링** | 60초 |
| WebSocket 사용 | ❌ 아니오 | - |
| UI 표시 | 현재가, 수익률 | 60초마다 갱신 |

### 10.3 레거시 문서와의 비교

| 항목 | 레거시 문서 | 현재 구현 |
|------|-----------|----------|
| 업데이트 방식 | 60초 폴링 | 60초 폴링 (동일) |
| API 호출 | `/api/kr/realtime-prices` | `apiClient.getRealtimePrices()` (동일) |
| WebSocket | 명시되지 않음 | 사용하지 않음 |

**결론**: VCP 페이지는 이미 **60초 폴링으로 "실시간" 가격 업데이트**를 구현하고 있음

---

## 11. 개선 방안: WebSocket으로 전환

### 11.1 현재 폴링 방식의 문제점

| 문제 | 설명 | 영향 |
|------|------|------|
| 불필요한 API 호출 | 60초마다 HTTP 요청 | 서버 리소스 낭비 |
| 지연 | 60초 대기 | 가격 변화 즉시 반영 안 됨 |
| 연결 상태 무시 | WebSocket 연결되어도 폴링 | 중복 업데이트 |

### 11.2 WebSocket 전환 방안

**현재**:
```typescript
// VCP 페이지 (폴링)
const { prices, lastUpdated } = useRealtimePrices(signals);
```

**개선**:
```typescript
// VCP 페이지 (WebSocket)
import { useRealtimePrices } from "@/hooks/useWebSocket";

const tickers = signals.map(s => s.ticker);
useRealtimePrices(tickers);  // WebSocket으로 실시간 업데이트
```

**장점**:
- 진정한 실시간 업데이트 (초단위)
- 불필요한 API 호출 제거
- 서버 리소스 절약

### 11.3 전환 작업

| 단계 | 작업 | 파일 |
|------|------|------|
| 1 | `useWebSocket.ts`의 `useRealtimePrices()` 사용 | `frontend/app/dashboard/kr/vcp/page.tsx` |
| 2 | 로컬 `useRealtimePrices` Hook 삭제 | `frontend/app/dashboard/kr/vcp/page.tsx` |
| 3 | Store와 연동하여 가격 자동 업데이트 | `frontend/store/index.ts` |

---

## 12. 참조: 관련 파일

### 백엔드
- `services/vcp_scanner/vcp_analyzer.py` - VCP 분석 로직 (529줄)
- `services/vcp_scanner/main.py` - VCP Scanner 서비스
- `services/api_gateway/routes/signals.py` - 시그널 API
- `src/websocket/server.py` - WebSocket 서버

### 프론트엔드
- `frontend/app/dashboard/kr/vcp/page.tsx` - VCP 대시보드 페이지 (481줄) ✅ 확인 완료
- `frontend/app/page.tsx` - 메인 페이지 (시그널 테이블)
- `frontend/hooks/useWebSocket.ts` - WebSocket Hooks
- `frontend/store/index.ts` - 상태 관리

### 문서
- `docs/archive_originals/PART_04_04_vcp_page.md` - VCP 페이지 명세 (410줄)
- `docs/api/API_GUIDE.md` - API 가이드
- `docs/report/vcp_signal_qa_final_detailed.md` - VCP QA 보고서

---

*보고서 작성일: 2026-02-03*
*버전: 1.1 (VCP 페이지 구현 확인 후 업데이트)*
*분석 방법: 문서 분석 + 코드 정적 분석 + 아키텍처 검증*
