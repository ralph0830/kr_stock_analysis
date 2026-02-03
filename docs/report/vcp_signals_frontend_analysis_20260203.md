# 활성 VCP 시그널 프론트엔드 분석 보고서

**분석 일자**: 2026-02-03
**분석자**: Claude Code QA
**테스트 방법**: Playwright Browser Automation

---

## 1. 문제 개요

### 1.1 사용자 보고

> "활성 VCP 시그널 (20개) 동작하지 않는데"

### 1.2 현재 상태

| 항목 | 상태 | 설명 |
|------|------|------|
| VCP 시그널 표시 | ✅ 정상 | 20개 종목 표시됨 |
| API 데이터 수신 | ✅ 정상 | `/api/kr/signals`에서 데이터 정상 반환 |
| 테이블 렌더링 | ✅ 정상 | hover 효과 작동 |
| **클릭 기능** | ❌ **없음** | 행 클릭 시 아무 동작 없음 |

---

## 2. 프론트엔드 코드 분석

### 2.1 VCP 시그널 테이블 구현

**파일**: `frontend/app/page.tsx` (라인 198-249)

```tsx
{/* VCP Signals (간단 버전) */}
{!showDashboard && signals.length > 0 && (
  <section>
    <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
      활성 VCP 시그널 ({signals.length}개)
    </h2>
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th>티커</th>
              <th>종목명</th>
              <th>등급</th>
              <th>점수</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {signals.map((signal) => (
              <tr key={signal.ticker} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                {/* ❌ onClick 핸들러 없음 */}
                <td>{signal.ticker}</td>
                <td>{signal.name}</td>
                <td>{signal.grade}</td>
                <td>{signal.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </section>
)}
```

### 2.2 문제점

| 문제 | 코드 위치 | 설명 |
|------|----------|------|
| 클릭 핸들러 없음 | 라인 225 | `<tr>` 태그에 `onClick` 없음 |
| 네비게이션 없음 | - | 행 클릭 시 페이지 이동 없음 |
| 상세 정보 없음 | - | 종목 상세/차트 페이지로 이동 없음 |

---

## 3. 비교: 정상 작동하는 요소

### 3.1 챗봇 섹션 (정상)

```tsx
<a
  href="/chatbot"
  className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
>
  챗봇 시작하기
</a>
```

✅ `href` 속성으로 클릭 시 `/chatbot` 페이지로 이동

### 3.2 차트 시각화 링크 (정상)

```tsx
<a
  href="/chart"
  className="text-blue-600 dark:text-blue-400 hover:underline"
>
  차트 페이지로 이동
</a>
```

✅ `href` 속성으로 클릭 시 `/chart` 페이지로 이동

---

## 4. 개선 방안

### 4.1 VCP 시그널 테이블 클릭 기능 추가

**옵션 1: 종목 상세 페이지로 이동**

```tsx
import Link from 'next/link';

// ...
<tbody className="divide-y divide-gray-200 dark:divide-gray-700">
  {signals.map((signal) => (
    <tr
      key={signal.ticker}
      className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
      onClick={() => router.push(`/dashboard/kr/${signal.ticker}`)}
    >
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600 dark:text-blue-400">
        {signal.ticker}
      </td>
      <td>{signal.name}</td>
      <td>{signal.grade}</td>
      <td>{signal.score}</td>
    </tr>
  ))}
</tbody>
```

**옵션 2: 차트 페이지로 이동**

```tsx
onClick={() => router.push(`/chart?ticker=${signal.ticker}`)}
```

**옵션 3: Modal로 상세 정보 표시**

```tsx
const [selectedSignal, setSelectedSignal] = useState(null);

// 클릭 시 Modal 열기
onClick={() => setSelectedSignal(signal)}
```

### 4.2 전체 시그널 테이블에도 동일 적용

"전체 보기" 클릭 시 표시되는 확장 버전 테이블(라인 252-320)에도 동일한 클릭 기능 추가 필요

---

## 5. 테스트 결과

| 테스트 케이스 | 예상 동작 | 실제 결과 | 상태 |
|-------------|----------|----------|------|
| VCP 시그널 표시 | 20개 종목 표시 | 20개 종목 표시 | ✅ |
| 행 hover 효과 | 배경색 변경 | 정상 작동 | ✅ |
| 행 클릭 | 페이지 이동/상세 표시 | **아무 동작 없음** | ❌ |

---

## 6. API 확인

### 6.1 시그널 API 정상 작동

```bash
curl http://localhost:5111/api/kr/signals

{
  "signals": [
    {
      "ticker": "0015N0",
      "name": "아로마티카",
      "market": "KOSDAQ",
      "signal_type": "VCP",
      "score": 59.25,
      "grade": "B",
      ...
    },
    ...
  ]
}
```

✅ 데이터 정상 반환

---

## 7. 요약

### 7.1 문제

VCP 시그널 테이블의 행 클릭 시 아무런 동작이 발생하지 않음

### 7.2 원인

프론트엔드 코드에 `<tr>` 태그에 `onClick` 이벤트 핸들러가 구현되어 있지 않음

### 7.3 해결 방안

1. `useRouter` 또는 `Link` 컴포넌트 사용하여 페이지 이동 추가
2. 종목 클릭 시 차트 페이지(`/chart?ticker=xxx`) 또는 상세 페이지로 이동
3. 또는 Modal 팝업으로 상세 정보 표시

### 7.4 수정 필요 파일

- `frontend/app/page.tsx`

---

*보고서 작성일: 2026-02-03*
*버전: 1.0*
