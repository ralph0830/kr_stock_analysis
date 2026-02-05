# 스키마 통합 분석 보고서

**작성일:** 2026-02-05
**범위:** 메인 대시보드(VCP) vs 단타 추천(Daytrading) 스키마 비교

---

## 1. 개요

단타 추천 페이지가 메인 대시보드의 백엔드 인프라를 그대로 사용하기 위해 두 시스템 간의 스키마 차이를 분석하고 통합 방안을 제안합니다.

**원칙:** 메인 대시보드가 표준 (Standard), 단타 추천이 따라야 함 (Follow)

---

## 2. DB 스키마 비교

### 2.1 메인 대시보드 - Signal 모델

**테이블:** `signals`

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | Integer | PK |
| `ticker` | String(6) | FK → stocks.ticker |
| `signal_type` | String(20) | VCP, JONGGA_V2 |
| `status` | String(20) | OPEN, CLOSED |
| `score` | Float | **VCP 점수** |
| `grade` | String(10) | S, A, B, C |
| `total_score` | Integer | **종가베팅 점수** |
| `entry_price` | Float | 진입가 |
| `stop_price` | Float | 손절가 |
| `target_price` | Float | 목표가 |
| `foreign_net_5d` | Integer | 외국인 5일 순매수 |
| `inst_net_5d` | Integer | 기관 5일 순매수 |
| `signal_date` | Date | 시그널 날짜 |
| `created_at` | DateTime | 생성일시 |

### 2.2 단타 추천 - DaytradingSignal 모델

**테이블:** `daytrading_signals`

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | Integer | PK |
| `ticker` | String(6) | **FK 없음 (독립)** |
| `name` | String(100) | **중복 저장** |
| `market` | String(10) | **중복 저장** |
| `total_score` | Integer | **총 점수** |
| `grade` | String(10) | S, A, B, C |
| `volume_score` | Integer | 거래량 폭증 점수 |
| `momentum_score` | Integer | 모멘텀 돌파 점수 |
| `box_score` | Integer | 박스권 탈출 점수 |
| `ma5_score` | Integer | 5일선 위 점수 |
| `institution_score` | Integer | 기관 매수 점수 |
| `oversold_score` | Integer | 낙폭 과대 점수 |
| `sector_score` | Integer | 섹터 모멘텀 점수 |
| `checks` | JSON | 체크리스트 배열 |
| `entry_price` | Integer | 진입가 |
| `target_price` | Integer | 목표가 |
| `stop_loss` | Integer | **손절가** |
| `status` | String(20) | OPEN, CLOSED |
| `signal_date` | Date | 시그널 날짜 |
| `created_at` | DateTime | 생성일시 |

### 2.3 스키마 차이점

| 구분 | 메인 대시보드 | 단타 추천 | 비고 |
|------|-------------|----------|------|
| 점수 필드명 | `score` (Float) | `total_score` (Integer) | **이름 다름** |
| 손절가 필드명 | `stop_price` | `stop_loss` | **이름 다름** |
| Stock 참조 | FK 존재 | **FK 없음** | 단순화 필요 |
| 체크리스트 | 개별 컬럼 없음 | `checks` JSON + 개별 컬럼 | **중복 저장** |
| 데이터 중복 | 최소화 | name, market 중복 | **정규화 필요** |

---

## 3. API 응답 구조 비교

### 3.1 메인 대시보드 API

**엔드포인트:** `GET /api/kr/signals`

```typescript
// format=object 시
{
  signals: VCPSignalItem[],
  count: number,
  vcp_count: number,
  jongga_count: number,
  generated_at: string
}

// format=list (기본) 시
VCPSignalItem[]  // 리스트 직접 반환
```

**VCPSignalItem:**
```typescript
{
  ticker: string,
  name: string,
  market: string,
  signal_type: string,      // "VCP" | "JONGGA_V2"
  score: number,            // ✅ score
  grade: string,
  signal_date: string,
  entry_price?: number,
  target_price?: number,
  current_price?: number,
  contraction_ratio?: number,
  foreign_5d: number,
  inst_5d: number,
  created_at: string        // ✅ created_at
}
```

### 3.2 단타 추천 API

**엔드포인트:** `GET /api/daytrading/signals`

```typescript
{
  success: boolean,
  data: {
    signals: IDaytradingSignal[],
    count: number,
    generated_at?: string
  }
}
```

**IDaytradingSignal:**
```typescript
{
  ticker: string,
  name: string,
  market: "KOSPI" | "KOSDAQ",
  total_score: number,      // ⚠️ total_score (차이)
  grade: "S" | "A" | "B" | "C",
  checks: IDaytradingCheck[],
  signal_type: DaytradingSignalType,  // "STRONG_BUY" | "BUY" | "WATCH"
  current_price?: number,
  entry_price?: number,
  target_price?: number,
  stop_loss?: number,       // ⚠️ stop_loss (차이)
  detected_at?: string      // ⚠️ detected_at (차이)
}
```

### 3.3 API 차이점

| 구분 | 메인 대시보드 | 단타 추천 | 통합 제안 |
|------|-------------|----------|----------|
| 응답 래퍼 | `format` 파라미터로 유연 | 항상 `{ success, data }` | 단타 → 메인 방식 |
| 점수 필드 | `score` | `total_score` | → `score` |
| 손절가 | `stop_loss` (FE) / `stop_price` (DB) | `stop_loss` | → `stop_loss` |
| 생성일시 | `created_at` | `detected_at` | → `created_at` |
| 캐싱 | 없음 | Redis 5분 TTL | → 메인도 캐싱 추가 |

---

## 4. 프론트엔드 타입 비교

### 4.1 메인 대시보드 - Signal 인터페이스

```typescript
// frontend/types/index.ts
export interface Signal {
  ticker: string;
  name: string;
  signal_type: string;          // "VCP" | "JONGGA_V2"
  score: number | ScoreDetail;  // ✅ score
  grade: string;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;           // ✅ stop_loss
  position_size?: number;
  reasons?: string[];
  created_at: string;           // ✅ created_at
}
```

### 4.2 단타 추천 - IDaytradingSignal 인터페이스

```typescript
// frontend/types/index.ts
export interface IDaytradingSignal {
  ticker: string;
  name: string;
  market: "KOSPI" | "KOSDAQ";
  total_score: number;          // ⚠️ total_score
  grade: "S" | "A" | "B" | "C";
  checks: IDaytradingCheck[];    // ✅ 체크리스트 배열
  signal_type: DaytradingSignalType;  // "STRONG_BUY" | "BUY" | "WATCH"
  current_price?: number;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;           // ✅ stop_loss
  detected_at?: string;         // ⚠️ detected_at
}
```

---

## 5. 통합 방안 (메인 대시보드 기준)

### 5.1 필드 이름 표준화

| 현재 (단타) | 표준 (메인) | 변경 범위 |
|-------------|------------|----------|
| `total_score` | `score` | DB, API, FE |
| `detected_at` | `created_at` | API, FE |
| `stop_loss` | `stop_loss` | 이미 일치 ✅ |
| `checks[]` | 유지 (확장성) | 신규 추가 |

### 5.2 DB 스키마 변경 (DaytradingSignal)

```python
# 변경 전
total_score = Column(Integer, nullable=False)
stop_loss = Column(Integer, nullable=True)

# 변경 후
score = Column(Integer, nullable=False)  # total_score → score
stop_loss = Column(Integer, nullable=True)  # 유지

# 추가
# Stock FK 추가 (데이터 중복 제거)
ticker = Column(String(6), ForeignKey("stocks.ticker"), ...)
```

### 5.3 API 응답 구조 통일

```python
# 단타 API 변경 제안
@router.get("/signals")
async def get_daytrading_signals(
    min_score: int = 0,
    market: Optional[str] = None,
    limit: int = 50,
    format: str = "list"  # ✅ 메인과 동일한 format 파라미터
):
    # ...
    if format == "object":
        return {
            "signals": signals,
            "count": len(signals),
            "generated_at": now
        }
    return signals  # 기본: 리스트 직접 반환
```

### 5.4 프론트엔드 타입 통일

```typescript
// 통합 제안
export interface ISignal {
  // 공통 필드
  ticker: string;
  name: string;
  market: string;
  score: number;           // ✅ 표준화
  grade: "S" | "A" | "B" | "C";
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;      // ✅ 표준화
  created_at: string;      // ✅ 표준화

  // VCP 전용
  signal_type?: "VCP" | "JONGGA_V2";
  contraction_ratio?: number;
  foreign_5d?: number;
  inst_5d?: number;

  // 단타 전용
  checks?: ICheck[];
}
```

---

## 7. WebSocket 비교

### 7.1 토픽 구독 현황

| 토픽 | 메인 대시보드 | 단타 추천 | 백엔드 지원 |
|------|-------------|----------|-------------|
| `price:{ticker}` | ✅ | ✅ | ✅ |
| `market-gate` | ✅ | ❌ | ✅ |
| `signal:vcp` | ✅ | ❌ | ✅ |
| `signal:daytrading` | ❌ | ⚠️ 프론트엔드만 | ❌ 미구현 |

### 7.2 WebSocket 메시지 타입

| 메시지 타입 | 메인 대시보드 | 단타 추천 | 공통 |
|-------------|-------------|----------|------|
| `connected` | ✅ | ✅ | 공통 |
| `price_update` | ✅ | ✅ | 공통 |
| `market_gate_update` | ✅ | ❌ | 메인 전용 |
| `signal_update` | ✅ (VCP) | ⚠️ FE만 정의 | 데이터 구조 다름 |

### 7.3 프론트엔트 Hook 불일치

**버그:** API 응답 접근 오류

```typescript
// hooks/useWebSocket.ts (현재 버그)
apiClient.getDaytradingSignals()
  .then((response) => {
    setSignals(response.data.signals);  // ❌ response.data.data.signals여야 함
  })

// store/daytradingStore.ts (동일 버그)
signals: response.data.signals,  // ❌ response.data.data.signals
```

**수정 필요한 4곳:**
1. `hooks/useWebSocket.ts:842`
2. `store/daytradingStore.ts:58`
3. `store/daytradingStore.ts:80`
4. `store/daytradingStore.ts:99`

---

## 8. 우선순위 및 작업량

### Phase 1: API 응답 접근 수정 (긴급, 버그)

- [ ] `response.data.signals` → `response.data.data.signals` (4곳 수정)
- [ ] 단타 시그널 정상 표시 확인

**작업량:** 30분

### Phase 2: API 응답 구조 통일

- [ ] 단타 API에 `format` 파라미터 추가
- [ ] 응답을 `{ success, data }` → `format`에 따라 유연하게 변경
- [ ] 프론트엔드 apiClient 수정

**작업량:** 2-3시간

### Phase 3: 프론트엔드 타입 통일

- [ ] `IDaytradingSignal.total_score` → `score`
- [ ] `IDaytradingSignal.detected_at` → `created_at`
- [ ] 공통 인터페이스 `ISignal` 정의

**작업량:** 1-2시간

### Phase 4: WebSocket 백엔드 구현

- [ ] `DaytradingSignalBroadcaster` 구현
- [ ] Daytrading Scanner 스캔 시 WebSocket 브로드캐스트
- [ ] `signal:daytrading` 토픽 방송

**작업량:** 2-3시간

### Phase 5: DB 스키마 통일 (마이그레이션 필요)

- [ ] `DaytradingSignal.total_score` → `score`
- [ ] Stock FK 추가
- [ ] 데이터 마이그레이션 스크립트

**작업량:** 3-4시간

---

## 9. 결론

단타 추천 시스템이 메인 대시보드의 백엔드 인프라를 통합하여 사용하기 위해서는 다음 변경이 필요합니다:

### 주요 발견

1. **API 응답 접근 버그**: `response.data.signals` → `response.data.data.signals` (4곳 수정 필요)
2. **WebSocket 백엔드 미구현**: `signal:daytrading` 토픽 방송 기능 없음
3. **필드명 불일치**: `total_score` vs `score`, `detected_at` vs `created_at`

### 통합 방향

1. **필드 이름 통일**: `total_score` → `score`, `detected_at` → `created_at`
2. **API 응답 구조**: `format` 파라미터 지원으로 유연하게 처리
3. **데이터 정규화**: Stock FK 추가로 중복 제거
4. **프론트엔드 타입**: 공통 인터페이스 정의로 코드 재사용성 향상
5. **WebSocket 실시간 업데이트**: 백엔드 브로드캐스터 구현

**총 작업량 예상:** 9-13시간 (버그 수정 + WebSocket + DB 마이그레이션)

---

## 10. 프론트엔드 코드 공유 분석

### 10.1 이미 공유 중인 컴포넌트/유틸리티 ✅

| 공유 항목 | 메인 대시보드 | 단타 추천 | 상태 |
|----------|-------------|----------|------|
| **ShadCN UI Components** | Button, Card, Badge, Table, Skeleton | 동일 사용 | ✅ 공유 완료 |
| **API Client** | `lib/api-client.ts` | 동일 인스턴스 | ✅ 공유 완료 |
| **WebSocket Client** | `lib/websocket.ts` | 동일 클라이언트 | ✅ 공유 완료 |
| **Format Utils** | `formatPrice`, `formatPercent`, `formatNumber` | 동일 사용 | ✅ 공유 완료 |
| **RealtimePriceCard** | 실시간 가격 카드 | 동일 사용 | ✅ 공유 완료 |

### 10.2 중복 구현 발견 (통합 필요) ⚠️

#### 10.2.1 Grade Color (등급 색상) - **색상이 다름!**

| 등급 | 메인 대시보드 (`getGradeColor`) | 단타 추천 (`GRADE_COLORS`) | 비고 |
|------|-------------------------------|--------------------------|------|
| **S** | `bg-red-100 text-red-700` | `bg-yellow-500 text-white` | ❌ 다름 |
| **A** | `bg-orange-100 text-orange-700` | `bg-green-500 text-white` | ❌ 다름 |
| **B** | `bg-yellow-100 text-yellow-700` | `bg-blue-500 text-white` | ❌ 다름 |
| **C** | `bg-blue-100 text-blue-700` | `bg-gray-500 text-white` | ❌ 다름 |
| **Dark Mode** | ✅ 지원 (`dark:bg-red-900/30`) | ❌ 미지원 | 메인 우선 |

**위치:**
- 메인: `frontend/lib/utils.ts:58-71` → `getGradeColor()` 함수
- 단타: `frontend/components/DaytradingSignalTable.tsx:45-50` → `GRADE_COLORS` 상수

**표준:** 메인 대시보드의 `getGradeColor()` 함수 사용 (Dark Mode 지원)

#### 10.2.2 Signal Type 인터페이스 - **필드명 불일치**

| 필드 | 메인 대시보드 (`Signal`) | 단타 추천 (`IDaytradingSignal`) |
|------|------------------------|-------------------------------|
| 점수 | `score` | `total_score` ⚠️ |
| 생성일시 | `created_at` | `detected_at` ⚠️ |
| 시그널 타입 | `signal_type: "VCP" \| "JONGGA_V2"` | `signal_type: "STRONG_BUY" \| "BUY" \| "WATCH"` |
| 체크리스트 | 없음 | `checks: IDaytradingCheck[]` ✅ (확장) |

**위치:** `frontend/types/index.ts`

#### 10.2.3 State Management (Zustand Store)

| Store | 파일 | 목적 |
|-------|------|------|
| `useStore()` | `store/index.ts` | 메인 대시보드 상태 (signals, filters) |
| `useDaytradingStore()` | `store/daytradingStore.ts` | 단타 추천 상태 (signals, filters, actions) |

**통합 가능:** 공통 Signal 인터페이스로 단일화

#### 10.2.4 WebSocket Hooks

| Hook | 파일 | 토픽 |
|------|------|------|
| `useSignals()` | `hooks/useWebSocket.ts` | `signal:vcp` |
| `useDaytradingSignals()` | `hooks/useWebSocket.ts` | `signal:daytrading` |

**통합 가능:** `useSignals(signalType: "vcp" | "daytrading")` 패턴

### 10.3 통합 우선순위

#### Phase 1: Grade Color 통일 (긴급)

- [ ] `DaytradingSignalTable.tsx`의 `GRADE_COLORS` 삭제
- [ ] `lib/utils.ts`의 `getGradeColor()` 사용으로 변경
- [ ] Dark Mode 지원 확인

**작업량:** 30분

#### Phase 2: 타입 정의 통일

- [ ] `ISignalBase` 베이스 인터페이스 정의
- [ ] `IVCPSignal`, `IDaytradingSignal` 확장
- [ ] 필드명 통일 (`total_score` → `score`, `detected_at` → `created_at`)

**작업량:** 1-2시간

#### Phase 3: State Management 통합

- [ ] 단일 Store 구조 검토
- [ ] `useSignals(signalType)` 패턴 구현

**작업량:** 2-3시간

---

## 11. 참고 파일

- DB 모델: `src/database/models/models.py`, `src/database/models/daytrading_signal.py`
- API 라우터: `services/api_gateway/routes/signals.py`, `services/api_gateway/routes/daytrading.py`
- WebSocket 서버: `src/websocket/server.py`, `src/websocket/routes.py`
- 프론트엔드 타입: `frontend/types/index.ts`
- 프론트엔드 API: `frontend/lib/api-client.ts`
- 프론트엔드 WebSocket: `frontend/hooks/useWebSocket.ts`
- 프론트엔드 Store: `frontend/store/daytradingStore.ts`

### 관련 보고서

- `code_sharing_analysis_20260205.md` - 프론트엔드 코드 공유 분석 ✅ 신규
- `websocket_backend_20260205.md` - WebSocket 백엔드 상세 분석
- `websocket_frontend_20260205.md` - WebSocket 프론트엔드 상세 분석
