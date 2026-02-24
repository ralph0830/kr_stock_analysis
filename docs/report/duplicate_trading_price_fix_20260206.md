# "매매 기준가" 중복 표시 버그 수정 보고서

**수정 일시:** 2026-02-06 14:01
**문제 발생 위치:** https://stock.ralphpark.com/custom-recommendation
**영향 받는 컴포넌트:** `DaytradingSignalTable.tsx`

---

## 1. 문제 요약

| 항목 | 내용 |
|------|------|
| **문제 유형** | UI 중복 렌더링 버그 |
| **증상** | 각 종목 카드마다 "매매 기준가" 섹션이 2번 표시됨 |
| **원인** | 코드 중복 (Copy-Paste 오류) |
| **상태** | ✅ 수정 완료 |

---

## 2. 문제 분석

### 2.1 발견 경로

사용자가 신고한 예시:
```
매매 기준가
진입: 20,150원 / 목표: 21,157원 / 손절: 19,545원

매매 기준가  ← 동일한 내용이 반복됨
진입: 20,150원 / 목표: 21,157원 / 손절: 19,545원
```

### 2.2 코드 분석

**파일:** `/home/ralph/work/python/kr_stock_analysis/frontend/components/DaytradingSignalTable.tsx`

**문제 코드:** 라인 247-299

```tsx
{/* 매매 기준가 */}   // ← 첫 번째 (정상)
{(signal.entry_price || signal.target_price || signal.stop_loss) && (
  <div className="border-t pt-3">
    <h4 className="text-sm font-medium mb-2">매매 기준가</h4>
    <div className="flex gap-4 text-sm">
      {signal.entry_price && (
        <div>
          <span className="text-gray-500">진입: </span>
          <span className="font-medium">{signal.entry_price.toLocaleString()}원</span>
        </div>
      )}
      {signal.target_price && (
        <div>
          <span className="text-gray-500">목표: </span>
          <span className="font-medium text-green-600">{signal.target_price.toLocaleString()}원</span>
        </div>
      )}
      {signal.stop_loss && (
        <div>
          <span className="text-gray-500">손절: </span>
          <span className="font-medium text-red-600">{signal.stop_loss.toLocaleString()}원</span>
        </div>
      )}
    </div>
  </div>
)}

{/* 매매 기준가 */}   // ← 두 번째 (중복)
{(signal.entry_price || signal.target_price || signal.stop_loss) && (
  <div className="border-t pt-3">
    <h4 className="text-sm font-medium mb-2">매매 기준가</h4>
    {/* ... 완전히 동일한 코드 ... */}
  </div>
)}
```

**분석 결과:**
- 247-272번 라인: 첫 번째 "매매 기준가" 섹션
- **274-299번 라인: 두 번째 "매매 기준가" 섹션 (중복)**
- 두 섹션은 **완전히 동일한 코드**로 구성됨

---

## 3. 원인 추정

**가장 유력한 원인:**
1. **Copy-Paste 실수:** 개발 중 코드를 복사하여 붙여넣은 후 삭제하지 않음
2. **Merge 충돌 미해결:** 브랜치 병합 시 충돌이 제대로 해결되지 않음
3. **Undo/Redo 오류:** 편집 과정에서 실수로 중복 생성

**현재 상황으로 판단:**
- 코드가 **완전히 동일**한 점으로 보아 **단순 Copy-Paste 실수**일 가능성이 가장 높음

---

## 4. 수정 내용

### 4.1 수정 전

```tsx
{/* 매매 기준가 */}
{...코드...}

{/* 매매 기준가 */}
{...동일한 코드...}

{/* 실시간 현재가 */}
```

### 4.2 수정 후

```tsx
{/* 매매 기준가 */}
{...코드...}

{/* 실시간 현재가 */}
```

### 4.3 수정 방법

```bash
# 파일 직접 편집
Edit tool을 사용하여 274-299번 라인의 중복 코드 삭제
```

---

## 5. 수정 확인

### 5.1 Playwright 테스트

| 항목 | 결과 |
|------|------|
| **페이지 접속** | ✅ 성공 |
| **중복 확인** | ✅ 해결됨 |
| **정상 표시** | ✅ 각 종목당 1번만 표시 |

### 5.2 수정 후 UI 스크린샷

**파일:** `~/Downloads/daytrading-ui-after-fix-2026-02-06T06-00-02-368Z.png`

**확인된 종목들:**
- 흥국화재 (000540): 진입 3,130원 / 목표 3,286원 / 손절 3,036원
- 삼성화재우 (000815): 진입 190,300원 / 목표 199,815원 / 손절 184,591원
- 하이트진로 (000080): 진입 20,150원 / 목표 21,157원 / 손절 19,545원
- 그 외 47개 종목 모두 정상 표시 확인

---

## 6. 검증 체크리스트

- [x] 문제 코드 위치 식별
- [x] 중복 코드 삭제
- [x] 브라우저 테스트로 수정 확인
- [x] 모든 종목 카드에 대해 동일한 수정 적용 확인
- [x] 보고서 작성

---

## 7. 최종 결론

**✅ 버그 수정 완료**

1. **원인:** `DaytradingSignalTable.tsx` 파일에서 "매매 기준가" 섹션이 2번 중복으로 작성됨
2. **해결:** 274-299번 라인의 중복 코드 삭제
3. **검증:** Playwright 브라우저 테스트를 통해 모든 종목에서 1번만 표시되는 것 확인

---

**작성자:** Claude Code
**문서 경로:** `/home/ralph/work/python/kr_stock_analysis/docs/report/duplicate_trading_price_fix_20260206.md`
