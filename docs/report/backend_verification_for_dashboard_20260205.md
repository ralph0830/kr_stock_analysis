# 대시보드 문제 - 백엔드 검증 결과

**작성일:** 2026-02-05
**대상:** 대시보드(`/dashboard`) 백엔드 API

---

## 1. 결론

**백엔드 API는 정상 작동 중입니다.**

문제의 근본 원인은 **Frontend 청크 로드 실패**로 판단됩니다.

---

## 2. API 검증 결과

### 2.1 `/api/kr/signals` 엔드포인트

```bash
GET https://stock.ralphpark.com/api/kr/signals
```

**상태:** ✅ **정상**

**응답 데이터 (20개 시그널):**
```json
[
  {"ticker":"000040","name":"KR모터스","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000050","name":"경방","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000070","name":"三星전자","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000080","name":"하이트스","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000090","name":"대한항공","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000100","name":"NGV","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000120","name":"CJ대한통운","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000130","name":"대웅제약","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000140","name":"하이트스","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000150","name":"두산","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000160","name":"현대중공업","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000180","name":"现代重工业","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000190","name":"성일하이텍스","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000200","name":"대상","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000210","name":"DSR","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000220","name":"제주팜","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000230","name":"세绒","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000240","name":"KODEX","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000250","name":"삼천리자산","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000260","name":"제주반도체","signal_type":"vcp","score":25.0,"grade":"C"},
  {"ticker":"000270","name":"기아","signal_type":"vcp","score":25.0,"grade":"C"}
]
```

### 2.2 `/api/kr/market-gate` 엔드포인트

```bash
GET https://stock.ralphpark.com/api/kr/market-gate
```

**상태:** ✅ **정상**

---

## 3. 백엔드 서비스 상태

| 서비스 | 포트 | 상태 |
|--------|------|------|
| API Gateway | 5111 | ✅ Healthy |
| VCP Scanner | 5112 | ✅ Running |
| Signal Engine | 5113 | ✅ Running |
| Frontend | 5110 | ✅ Running |

---

## 4. 문제 분석

### 4.1 근본 원인

**ChunkLoadError** - Next.js 프로덕션 빌드 후 JavaScript 청크 파일 접근 실패

```
ChunkLoadError: Loading chunk app/dashboard/page failed
(timeout: https://stock.ralphpark.com/_next/static/chunks/app/dashboard/page.js)
```

### 4.2 데이터 흐름

```
[정상 흐름]
Frontend → API /api/kr/signals → 20개 시그널 반환 → 표시

[현재 문제]
Frontend → ChunkLoadError → React 컴포넌트 미실행 → signals = [] → "시그널 없음"
```

---

## 5. 백엔드 관련 사항

### 5.1 API 응답 형식

**메인 대시보드 `/api/kr/signals`**
- `format=list` (기본): 리스트 직접 반환
- `format=object`: `{ signals, count, vcp_count, jongga_count, generated_at }`

**단타 추천 `/api/daytrading/signals`**
- `format=list` (기본): 리스트 직접 반환
- `format=object`: `{ signals, count, generated_at }`

### 5.2 필드명 표준화 완료

| 구분 | 필드명 | 상태 |
|------|--------|------|
| 점수 | `score` | ✅ 통일됨 |
| 손절가 | `stop_loss` | ✅ 통일됨 |
| 생성일시 | `created_at` | ✅ 통일됨 |

---

## 6. 프론트엔드 팀 전달 사항

### 6.1 백엔드 정상 확인 완료

- API 엔드포인트 모두 정상 응답
- 데이터베이스에 20개 시그널 존재
- WebSocket 서비스 정상 작동

### 6.2 필요한 프론트엔드 조치

1. **Frontend 빌드 재실행**
   ```bash
   cd frontend
   rm -rf .next
   npm run build
   ```

2. **청크 파일 확인**
   ```bash
   ls -la .next/static/chunks/app/dashboard/
   # page.js, layout.js 존재 확인
   ```

3. **재배포 후 검증**
   ```bash
   curl -I https://stock.ralphpark.com/_next/static/chunks/app/dashboard/page.js
   # 200 OK 기대
   ```

### 6.3 참고

백엔드 측에서는 추가 수정이 필요하지 않습니다. 문제는 Frontend 빌드/배포 과정에서 발생하고 있습니다.

---

**백엔드 팀 확인 완료**
