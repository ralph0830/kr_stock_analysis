# 프론트엔드 ELW 필터 삭제 보고서

**작성 일자**: 2026-02-03
**대상 파일**: `frontend/components/RealtimePriceCard.tsx`
**작성자**: Claude Code QA

---

## 1. 개요

### 1.1 문제 정의

현재 프론트엔드 코드는 **"알파벳이 포함된 6자리 코드 = ELW"**라는 부정확한 필터 조건을 사용하고 있습니다. 이 조건은 실제 ELW 종목 분류와 일치하지 않으므로 삭제가 필요합니다.

### 1.2 영향 범위

| 파일 | 라인 | 영향 |
|------|------|------|
| `RealtimePriceCard.tsx` | 28-31 | `isELW()` 함수 |
| `RealtimePriceCard.tsx` | 36-55 | `getTickerCategory()` 함수 |
| `RealtimePriceCard.tsx` | 77 | `category`, `realtimeSupported` 사용 |
| `RealtimePriceCard.tsx` | 98 | `realtimeSupported` 조건부 폴링 |
| `RealtimePriceCard.tsx` | 144 | `useEffect` 의존성 |
| `RealtimePriceCard.tsx` | 237-240 | ELW 안내 메시지 (대기 상태) |
| `RealtimePriceCard.tsx` | 319-321 | `realtimeSupported` 메시지 |
| `RealtimePriceCard.tsx` | 327-332 | ELW 안내 메시지 (데이터 상태) |

---

## 2. 현재 코드 분석

### 2.1 `isELW()` 함수 (라인 28-31)

```typescript
/**
 * ELW 종목 여부 확인
 * ELW: 알파벳이 포함된 6자리 코드 (예: 0015N0, 0004V0)
 */
function isELW(ticker: string): boolean {
  // 6자리 코드이고 알파벳이 포함되어 있으면 ELW
  return ticker.length === 6 && /[A-Za-z]/.test(ticker);
}
```

**문제점**:
- 알파벳 포함 여부만으로 ELW를 판단하는 것은 부정확함
- 실제 ELW는 종목 분류 체계에 따라 결정되어야 함

### 2.2 `getTickerCategory()` 함수 (라인 36-55)

```typescript
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "ELW" | "UNKNOWN";
  realtimeSupported: boolean;
} {
  if (isELW(ticker)) {
    return { category: "ELW", realtimeSupported: false };
  }

  // K-OTC: 10자리
  if (ticker.length === 10) {
    return { category: "OTC", realtimeSupported: false };
  }

  // KOSPI/KOSDAQ 구분 (0으로 시작하면 KOSPI)
  if (ticker.startsWith("0") || ticker.startsWith("00") || ticker.startsWith("000")) {
    return { category: "KOSPI", realtimeSupported: true };
  }

  return { category: "KOSDAQ", realtimeSupported: true };
}
```

**문제점**:
- `isELW()` 호출로 잘못된 분류 수행
- ELW로 판단되면 `realtimeSupported: false`로 설정하여 WebSocket 사용 제한

### 2.3 `useEffect` 폴링 로직 (라인 95-144)

```typescript
// 폴링 Fallback: WebSocket 데이터가 없거나 ELW 종목인 경우 폴링 시도
useEffect(() => {
  // WebSocket이 지원되고 연결된 경우 폴링 스킵
  if (realtimeSupported && connected) {
    return;
  }
  // ... 폴링 로직
}, [ticker, realtimeSupported, connected, realtimePrice]);
```

**문제점**:
- `realtimeSupported`가 `false`인 ELW 종목은 무조건 폴링 시도
- 실제로는 WebSocket을 통해 실시간 데이터를 받을 수 있음

### 2.4 ELW 안내 메시지 (라인 237-240, 327-332)

```typescript
{/* ELW 안내 메시지 - 대기 상태 */}
{isELW(ticker) && (
  <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2">
    ⚠️ ELW 종목은 폴링으로 업데이트됩니다 (15초 간격)
  </p>
)}

{/* ELW 안내 메시지 - 데이터 상태 */}
{isELW(ticker) && (
  <div className="mt-2 pt-2 border-t border-yellow-200 dark:border-yellow-800">
    <p className="text-xs text-yellow-600 dark:text-yellow-400">
      ⚠️ ELW 종목은 실시간 WebSocket 지원이 제한됩니다. 폴링으로 업데이트됩니다.
    </p>
  </div>
)}
```

**문제점**:
- 부정확한 ELW 판단으로 잘못된 경고 메시지 표시
- 사용자에게 혼란을 야기

---

## 3. 삭제 방안

### 3.1 `isELW()` 함수 삭제

**대상**: 라인 23-31

```typescript
// === 삭제 ===
/**
 * ELW 종목 여부 확인
 * ELW: 알파벳이 포함된 6자리 코드 (예: 0015N0, 0004V0)
 */
function isELW(ticker: string): boolean {
  // 6자리 코드이고 알파벳이 포함되어 있으면 ELW
  return ticker.length === 6 && /[A-Za-z]/.test(ticker);
}
```

### 3.2 `getTickerCategory()` 함수 간소화

**대상**: 라인 35-55

**변경 전**:
```typescript
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "ELW" | "UNKNOWN";
  realtimeSupported: boolean;
} {
  if (isELW(ticker)) {
    return { category: "ELW", realtimeSupported: false };
  }

  // K-OTC: 10자리
  if (ticker.length === 10) {
    return { category: "OTC", realtimeSupported: false };
  }

  // KOSPI/KOSDAQ 구분 (0으로 시작하면 KOSPI)
  if (ticker.startsWith("0") || ticker.startsWith("00") || ticker.startsWith("000")) {
    return { category: "KOSPI", realtimeSupported: true };
  }

  return { category: "KOSDAQ", realtimeSupported: true };
}
```

**변경 후**:
```typescript
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "OTC" | "UNKNOWN";
  realtimeSupported: boolean;
} {
  // K-OTC: 10자리
  if (ticker.length === 10) {
    return { category: "OTC", realtimeSupported: false };
  }

  // KOSPI/KOSDAQ 구분 (0으로 시작하면 KOSPI)
  if (ticker.startsWith("0") || ticker.startsWith("00") || ticker.startsWith("000")) {
    return { category: "KOSPI", realtimeSupported: true };
  }

  return { category: "KOSDAQ", realtimeSupported: true };
}
```

### 3.3 `category`, `realtimeSupported` 사용 유지 (변경 없음)

**대상**: 라인 77

```typescript
const { category, realtimeSupported } = useMemo(() => getTickerCategory(ticker), [ticker]);
```

**설명**: 변수 사용은 유지하되, `getTickerCategory()`에서 ELW를 제거하면 정상 동작

### 3.4 ELW 안내 메시지 삭제

**대상 1**: 라인 236-241 (대기 상태 메시지)

```typescript
// === 삭제 ===
{/* ELW 안내 메시지 */}
{isELW(ticker) && (
  <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2">
    ⚠️ ELW 종목은 폴링으로 업데이트됩니다 (15초 간격)
  </p>
)}
```

**대상 2**: 라인 326-332 (데이터 상태 메시지)

```typescript
// === 삭제 ===
{/* ELW 안내 메시지 */}
{isELW(ticker) && (
  <div className="mt-2 pt-2 border-t border-yellow-200 dark:border-yellow-800">
    <p className="text-xs text-yellow-600 dark:text-yellow-400">
      ⚠️ ELW 종목은 실시간 WebSocket 지원이 제한됩니다. 폴링으로 업데이트됩니다.
    </p>
  </div>
)}
```

### 3.5 `realtimeSupported` 메시지 수정

**대상**: 라인 316-322

**변경 전**:
```typescript
{dataSource === "polling" && (
  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
    <p className="text-xs text-gray-500 dark:text-gray-400">
      {realtimeSupported
        ? "현재 실시간 연결이 없습니다. 15초마다 업데이트됩니다."
        : `${category} 종목은 폴링으로 업데이트됩니다 (15초 간격).`}
    </p>
  </div>
)}
```

**변경 후**:
```typescript
{dataSource === "polling" && (
  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
    <p className="text-xs text-gray-500 dark:text-gray-400">
      현재 실시간 연결이 없습니다. 15초마다 업데이트됩니다.
    </p>
  </div>
)}
```

---

## 4. 수정 후 전체 코드

### 4.1 함수 부분 (라인 23-55)

```typescript
/**
 * 종목 코드 분류 (KOSPI/KOSDAQ/OTC)
 */
function getTickerCategory(ticker: string): {
  category: "KOSPI" | "KOSDAQ" | "OTC" | "UNKNOWN";
  realtimeSupported: boolean;
} {
  // K-OTC: 10자리
  if (ticker.length === 10) {
    return { category: "OTC", realtimeSupported: false };
  }

  // KOSPI/KOSDAQ 구분 (0으로 시작하면 KOSPI)
  if (ticker.startsWith("0") || ticker.startsWith("00") || ticker.startsWith("000")) {
    return { category: "KOSPI", realtimeSupported: true };
  }

  return { category: "KOSDAQ", realtimeSupported: true };
}
```

### 4.2 렌더링 부분 변경 사항

1. ELW 안내 메시지 2개 삭제
2. `realtimeSupported` 조건부 메시지 단일화

---

## 5. 영향도 분석

### 5.1 기능 영향

| 항목 | 현재 | 변경 후 | 영향 |
|------|------|---------|------|
| ELW 판별 | 알파벳 포함 6자리 | 없음 | ✅ 부정확한 판별 제거 |
| 종목 분류 | KOSPI/KOSDAQ/ELW/OTC | KOSPI/KOSDAQ/OTC | ✅ 간소화 |
| 실시간 지원 | ELW는 항상 false | 모든 종목 true (OTC 제외) | ✅ 실시간 데이터 수신 가능 |
| 폴링 동작 | ELW는 무조건 폴링 | WebSocket 실패 시에만 폴링 | ✅ 불필요한 폴링 감소 |
| 경고 메시지 | ELW 종목 경고 표시 | 경고 없음 | ✅ 혼란 제거 |

### 5.2 UI 영향

| 요소 | 현재 | 변경 후 |
|------|------|---------|
| ELW 뱃지 (• ELW) | 표시됨 | 표시 안 됨 |
| ELW 경고 메시지 | 2곳에 표시 | 삭제됨 |
| 폴링 메시지 | 종목별 다름 | 단일 메시지 |

---

## 6. 테스트 시나리오

### 6.1 테스트 케이스

| 케이스 | 종목 코드 | 예상 동작 |
|--------|----------|----------|
| TC-01 | 0015N0 | KOSPI로 분류, 실시간 지원, ELW 메시지 없음 |
| TC-02 | 0004V0 | KOSPI로 분류, 실시간 지원, ELW 메시지 없음 |
| TC-03 | 0120X0 | KOSPI로 분류, 실시간 지원, ELW 메시지 없음 |
| TC-04 | 493330 | KOSDAQ로 분류, 실시간 지원 |
| TC-05 | 217590 | KOSDAQ로 분류, 실시간 지원 |
| TC-06 | 005930 | KOSPI로 분류, 실시간 지원 |

### 6.2 검증 항목

1. [ ] 알파벳 포함 종목이 ELW로 표시되지 않음
2. [ ] 모든 종목에서 ELW 경고 메시지가 표시되지 않음
3. [ ] WebSocket 연결 시 모든 종목이 실시간 데이터를 수신
4. [ ] 폴링은 WebSocket 실패 시에만 실행

---

## 7. 요약

### 7.1 삭제 항목

1. `isELW()` 함수 (라인 23-31) ✅ 완료
2. `getTickerCategory()` 내부 ELW 분기 (라인 40-42) ✅ 완료
3. ELW 안내 메시지 2개 (라인 236-241, 326-332) ✅ 완료
4. `realtimeSupported` 조건부 메시지 단일화 (라인 316-322) ✅ 완료
5. 폴링 useEffect에서 `realtimeSupported` 조건 제거 ✅ 완료

### 7.2 변경 파일

- `frontend/components/RealtimePriceCard.tsx` ✅ 수정 완료

### 7.3 예상 효과

- 부정확한 ELW 판별 로직 제거 ✅
- 모든 종목이 WebSocket을 통한 실시간 데이터 수신 가능 ✅
- 사용자 혼란 감소 ✅
- 코드 간소화 ✅

### 7.4 수정 완료 내역

| 항목 | 수정 전 | 수정 후 |
|------|---------|---------|
| `isELW()` 함수 | 존재 | 삭제됨 |
| `getTickerCategory()` | ELW 분기 포함 | KOSPI/KOSDAQ/OTC만 분류 |
| ELW 안내 메시지 (대기) | 표시됨 | 삭제됨 |
| ELW 안내 메시지 (데이터) | 표시됨 | 삭제됨 |
| 폴링 조건 | `realtimeSupported && connected` | `connected && realtimePrice` |
| 폴링 안내 메시지 | 종목별 다름 | 단일 메시지 |

---

*보고서 작성일: 2026-02-03*
*수정 완료일: 2026-02-03*
*버전: 1.1*
