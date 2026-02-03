# 프론트엔드 복구 보고서

**작성 일자**: 2026-02-03
**목적**: stock.ralphpark.com 프론트엔드 문제 분석 및 복구 방안

---

## 1. 문제 요약

### 1.1 발생한 문제

| 문제 | 상태 | 영향 |
|------|------|------|
| VCP 페이지 시그널 0개 | ❌ | 데이터 미표시 |
| 차트 페이지 데이터 미로딩 | ❌ | 차트 미작동 |
| WebSocket 연결 404 | ❌ | 실시간 업데이트 불가 |
| Next.js 빌드 오류 | ⚠️ | 404 페이지 렌더링 실패 |

### 1.2 정상 작동하는 부분

| 기능 | 상태 |
|------|------|
| 메인 페이지 로딩 | ✅ |
| API 엔드포인트 (`/api/kr/signals/vcp`) | ✅ 200, 데이터 반환 |
| 프론트엔드 개발 서버 | ✅ |

---

## 2. 원인 분석

### 2.1 VCP 페이지 시그널 0개 문제

**증상**:
- 페이지 표시: "시그널: 0개"
- 서버 로그: `[VCP DEBUG] Sorted signals: 0 []`
- 브라우저 콘솔: API 요청 로그 없음

**원인**:

1. **`useSignals()` Hook의 초기 데이터 로드 실패**
   ```typescript
   // useSignals 내부
   apiClient.getSignals()  // /api/kr/signals 호출
     .then((initialSignals) => {
       setSignals(initialSignals);  // 이 데이터가 wsSignals로 설정됨
     })
   ```

2. **VCP 페이지의 데이터 로드 조건 불일치**
   ```typescript
   // VCP 페이지
   const [signals, setSignals] = useState<VCPSignal[]>([]);

   // WebSocket 시그널 업데이트 처리
   useEffect(() => {
     if (wsSignals.length > 0) {  // ← wsSignals가 비어있으면 실행 안됨!
       setSignals(vcpSignals);
     }
   }, [wsSignals]);

   // 데이터 로드 (WebSocket 연결되지 않았거나 초기 로드 시)
   useEffect(() => {
     if (signalsRealtime) {
       return;  // WebSocket이 "연결됨"으로 잘못 판단되면 스킵!
     }
     loadData();  // ← 이 함수가 호출되지 않음
   }, [signalsRealtime]);
   ```

3. **`signalsRealtime` 값이 `true`로 설정되는 문제**
   - WebSocket 연결이 실패했음에도 `isRealtime`이 `true`가 됨
   - 이로 인해 API 폴백이 실행되지 않음

### 2.2 WebSocket 404 문제

**원인**: Nginx Proxy Manager에서 `/ws` 경로에 대한 Custom Location 미설정

**영향**:
- 실시간 가격 업데이트 불가
- 시그널 브로드캐스트 수신 불가

### 2.3 Next.js 빌드 오류

**에러 메시지**:
```
Error: <Html> should not be imported outside of pages/_document.
```

**원인**: Next.js 15와 App Router 호환성 문제 (사전 존재)

---

## 3. 변경 사항 복구 필요 여부

### 3.1 이전 대화에서 수정한 파일

| 파일 | 변경 사항 | 롤백 필요 |
|------|----------|----------|
| `frontend/app/dashboard/kr/vcp/page.tsx` | 로컬 `useRealtimePrices` → WebSocket | ⚠️ 검토 필요 |
| `frontend/components/RealtimePriceCard.tsx` | TypeScript 타입 수정 | ✅ 유지 |
| `src/kiwoom/rest_api.py` | ETF 키워드 추가 | ✅ 유지 |

### 3.2 VCP 페이지 변경 사항 분석

**변경 내용**:
```typescript
// 변경 전: 로컬 폴링 함수
function useRealtimePrices(signals: Signal[], intervalMs: number = 60000) {
  const interval = setInterval(updatePrices, intervalMs);
  return { prices, lastUpdated };
}

// 변경 후: WebSocket 기반
import { useRealtimePrices } from "@/hooks/useWebSocket";
const tickers = useMemo(() => signals.map((s) => s.ticker), [signals]);
const { prices, getPrice } = useRealtimePrices(tickers);
```

**문제점**:
1. `signals`가 초기에 비어있으면 `tickers`도 비어있음
2. `useRealtimePrices([])` 호출 시 구독할 종목이 없음
3. 하지만 이는 "실시간 가격 업데이트" 문제일 뿐, "시그널 0개" 문제와는 별개

**결론**: WebSocket 변경은 시그널 로딩 문제의 직접적 원인이 아님

---

## 4. 복구 방안

### 4.1 우선순위 1: VCP 페이지 시그널 로딩 복구

**옵션 A: API 폴백 강화** (권장)

`frontend/app/dashboard/kr/vcp/page.tsx`의 `useEffect` 의존성 수정:

```typescript
// 데이터 로드 (WebSocket 연결되지 않았거나 초기 로드 시)
useEffect(() => {
  // WebSocket으로 데이터를 받고 있고, 이미 시그널가 있으면 스킵
  if (signalsRealtime && wsSignals.length > 0) {
    return;
  }

  const loadData = async () => {
    setLoading(true);
    try {
      const vcpResponse = await apiClient.getVCPSignals(10);
      // ... 기존 코드 ...
      setSignals(vcpSignals);
    } catch (error) {
      console.error("Failed to load VCP data:", error);
    } finally {
      setLoading(false);
    }
  };

  loadData();
}, [signalsRealtime, wsSignals.length]);  // wsSignals.length 추가
```

**옵션 B: `useSignals` Hook 수정**

`frontend/hooks/useWebSocket.ts`의 `useSignals`에서 VCP 전용 시그널 요청:

```typescript
// 초기 데이터 로드 (fallback)
useEffect(() => {
  if (signals.length === 0 && !isRealtime) {
    // VCP 시그널 API 호출
    apiClient.getVCPSignals(20)  // VCP 전용 엔드포인트
      .then((response) => {
        console.log("[useSignals] Loaded initial VCP signals:", response.signals.length);
        setSignals(response.signals);  // response.signals 배열 전달
      })
      .catch((error) => {
        console.error("[useSignals] Failed to load initial signals:", error);
      });
  }
}, [signals.length, isRealtime]);
```

### 4.2 우선순위 2: WebSocket 복구

**Nginx Proxy Manager 설정**:

```bash
# 자동화 스크립트 실행
python scripts/setup_npm_proxy.py
```

또는 수동으로 Nginx Proxy Manager UI에서:
1. Proxy Hosts → `stock.ralphpark.com` 선택
2. Custom Locations 탭
3. Location: `/ws`
4. Advanced Config:
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

### 4.3 우선순위 3: Next.js 빌드 오류 수정

**`next.config.js` 설정 추가**:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

module.exports = nextConfig;
```

---

## 5. 롤백 계획 (코드 변경 없이 테스트만 수행)

**주의**: 사용자가 "코드 변경하지 말고" 요청했으므로, 현재 단계에서는 분석만 진행하고 실제 코드 수정은 제안만 합니다.

### 5.1 이전 변경 사항 요약

| 파일 | 변경 내용 | 영향 |
|------|----------|------|
| `vcp/page.tsx` | `useRealtimePrices` WebSocket 전환 | 실시간 가격 업데이트 |
| `RealtimePriceCard.tsx` | TypeScript 타입 수정 | 빌드 오류 수정 |

### 5.2 복구 필요 여부 판단

1. **VCP 페이지 시그널 0개**:
   - 원인: `useSignals` Hook과 VCP 페이지 간 데이터 흐름 불일치
   - 복구: `useEffect` 의존성 배열 수정 필요

2. **WebSocket 404**:
   - 원인: Nginx Proxy Manager 설정 누락
   - 복구: NPM 설정 필요 (인프라 문제)

3. **TypeScript 오류**:
   - 이미 수정 완료

---

## 6. 권장 조치 순서

1. **VCP 페이지 데이터 로딩 수정** (코드 변경 필요)
   - `useEffect` 의존성 배열에 `wsSignals.length` 추가

2. **WebSocket Nginx 설정** (인프라 변경 필요)
   - NPM에서 `/ws` Custom Location 추가

3. **Next.js 빌드 설정** (선택 사항)
   - `eslint.ignoreDuringBuilds: true` 추가

---

## 7. 테스트 결과 상세

### 7.1 API 엔드포인트 테스트

| 엔드포인트 | 상태 | 응답 |
|-----------|------|------|
| `GET /api/kr/signals?limit=3` | ✅ 200 | `[{...}]` (3개) |
| `GET /api/kr/signals/vcp?limit=3` | ✅ 200 | `{signals: [...], count: 3}` (3개) |
| `POST /api/kr/realtime-prices` | ✅ 200 | 가격 데이터 반환 |
| `WSS /ws` | ❌ 404 | `{"detail":"Not Found"}` |

### 7.2 브라우저 테스트 결과

```javascript
{
  "pageReady": true,
  "reactRoot": false,  // ⚠️ Next.js App Router 특성
  "vcpApiStatus": 200,
  "vcpApiSignalCount": 5  // ✅ API는 정상 작동
}
```

---

## 8. 결론

### 8.1 문제의 본질

**프론트엔드가 완전히 망가진 것이 아니라, 부분적으로 작동하지 않음:**
- API 백엔드는 정상 작동
- WebSocket만 제외하면 REST API로 데이터 가져오기 가능
- React 컴포넌트 마운트 및 상태 관리 로직에 문제

### 8.2 복구를 위한 최소 변경 사항

1. **VCP 페이지 `useEffect` 의존성 수정** (1줄 변경)
2. **Nginx Proxy Manager `/ws` 경로 설정** (인프라, UI 작업)

### 8.3 롤백 대신 수정 권장

이전 변경 사항(`useRealtimePrices` WebSocket 전환)은 올바른 방향이었으나, WebSocket이 연결되지 않는 환경에서의 폴백 처리가 미흡했습니다. WebSocket 연결이 복구되면 이 변경 사항이 유효해질 것입니다.

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
