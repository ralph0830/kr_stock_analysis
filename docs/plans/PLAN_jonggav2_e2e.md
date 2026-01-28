# 종가베팅 V2 엔드투엔드 구현 계획

> 서버 오픈 후 종가베팅 V2 시그널 엔드투엔드 구현

**생성일:** 2026-01-28
**범위:** Medium (4 Phases, 6-10 hours)
**TDD:** 테스트 우선 (서비스 통합)

---

## 🚨 CRITICAL INSTRUCTIONS

각 Phase 완료 후:
1. ✅ 완료된 작업 체크박스 확인
2. 🧪 품질 게이트 검증 명령어 실행
3. ⚠️ **모든** 품질 게이트 항목 통과 확인
4. 📅 "Last Updated" 날짜 업데이트
5. 📝 Notes 섹션에 학습 내용 기록
6. ➡️ **그 후에만** 다음 Phase 진행

⛔ 실패하는 테스트가 있거나 품질 게이트를 통과하지 못하면 다음 Phase로 진행하지 마세요.

---

## 📋 개요

### 목표
종가베팅 V2 시그널 시스템의 엔드투엔드 구현
- Phase 1: 서비스 실행 (Signal Engine + API Gateway)
- Phase 2: API 통합 검증
- Phase 3: Frontend UI 개선 (종가베팅 V2 시그널)
- Phase 4: Market Gate 섹터 시각화

### 현재 상태
- ✅ SignalScorer 구현 완료 (30개 테스트 통과)
- ✅ PostgreSQL + Redis 실행 중
- ⏳ 마이크로서비스 실행 필요

---

## Phase 1: 서비스 실행

### Goal
Signal Engine Service와 API Gateway를 실행하고 헬스 체크 확인

### Tasks

#### 1.1 서비스 시작
- [ ] Signal Engine Service 시작 (port 5113)
  ```bash
  .venv/bin/python -m uvicorn services.signal_engine.main:app --host 0.0.0.0 --port 5113 --reload
  ```
- [ ] API Gateway 시작 (port 5111)
  ```bash
  .venv/bin/python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111 --reload
  ```
- [ ] Frontend 시작 (port 5110)
  ```bash
  cd frontend && npm run dev
  ```

#### 1.2 헬스 체크
- [ ] Signal Engine 헬스 체크: `curl http://localhost:5113/health`
- [ ] API Gateway 헬스 체크: `curl http://localhost:5111/health`
- [ ] Frontend 접속: `http://localhost:5110`

### Quality Gate
- [ ] Signal Engine `/health` 엔드포인트 응답 확인
- [ ] API Gateway `/health` 엔드포인트 응답 확인
- [ ] Frontend 페이지 렌더링 확인
- [ ] 로그에 에러 없음

---

## Phase 2: API 통합 검증

### Goal
종가베팅 V2 API 엔드포인트 통합 테스트

### Tasks

#### 2.1 종가베팅 V2 시그널 API
- [ ] `/api/kr/jongga-v2/latest` 엔드포인트 테스트
  ```bash
  curl http://localhost:5111/api/kr/jongga-v2/latest
  ```
- [ ] Signal Engine `/signals/latest` 직접 테스트
  ```bash
  curl http://localhost:5113/signals/latest
  ```

#### 2.2 단일 종목 분석 API
- [ ] `/api/kr/jongga-v2/analyze` 엔드포인트 테스트 (API Gateway)
  ```bash
  curl -X POST http://localhost:5111/api/kr/jongga-v2/analyze \
    -H "Content-Type: application/json" \
    -d '{"ticker":"005930","name":"삼성전자","price":80000}'
  ```
- [ ] Signal Engine `/analyze` 직접 테스트
  ```bash
  curl -X POST http://localhost:5113/analyze \
    -H "Content-Type: application/json" \
    -d '{"ticker":"005930","name":"삼성전자","price":80000}'
  ```

#### 2.3 응답 구조 검증
- [ ] 시그널 응답에 score.detail 필드 포함 확인
- [ ] grade (S/A/B/C) 정확성 확인
- [ ] position_size 계산 확인

### Quality Gate
- [ ] API 응답 200 OK 확인
- [ ] 응답 JSON 구조 올바름
- [ ] Signal Engine → API Gateway 프록시 동작

---

## Phase 3: Frontend UI 개선 (종가베팅 V2)

### Goal
종가베팅 V2 시그널 상세 페이지 UI 개선

### Tasks

#### 3.1 시그널 상세 정보 표시
- [ ] `frontend/app/signals/page.tsx`에 score.detail 표시 추가
  - News 점수 (0-3)
  - Volume 점수 (0-3)
  - Chart 점수 (0-2)
  - Candle 점수 (0-1)
  - Period 점수 (0-1)
  - Flow 점수 (0-2)
- [ ] 점수별 프로그레스 바/색상 표시

#### 3.2 매매 사유 표시
- [ ] reasons 배열 표시 컴포넌트 추가
- [ ] reasons 목록을 태그 형태로 표시

#### 3.3 포지션 사이징 정보
- [ ] position_size (주식 수) 표시
- [ ] 목표가/손절가 표시 강화

### Quality Gate
- [ ] Frontend 빌드 성공: `npm run build`
- [ ] Linting 통과: `npm run lint`
- [ ] 브라우저에서 시그널 상세 확인

---

## Phase 4: Market Gate 섹터 시각화

### Goal
Market Gate 섹터별 점수 시각화

### Tasks

#### 4.1 섹터 점수 API
- [ ] API Gateway에 `/api/kr/market-gate/sectors` 엔드포인트 추가
- [ ] 섹터별 종가베팅 V2 점수 집계 로직

#### 4.2 섹터 그리드 컴포넌트
- [ ] `frontend/components/MarketGateSectors.tsx` 생성
- [ ] 섹터별 카드 그리드 레이아웃

#### 4.3 섹터 상세 페이지
- [ ] 섹터 클릭 시 해당 섹터 종목만 필터링
- [ ] 섹터별 평균 점수 표시

### Quality Gate
- [ ] API 응답 확인
- [ ] Frontend 렌더링 확인
- [ ] 섹터 필터링 동작 확인

---

## 📊 Risk Assessment

| Risk | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| DB 데이터 부족 | Medium | High | Mock 데이터 폴백 |
| 포트 충돌 | Low | Medium | 포트 설정 확인 |
| CORS 오류 | Low | Low | API Gateway CORS 설정 |

---

## 진행 상황

| Phase | 상태 | 완료일 | Notes |
|-------|------|--------|-------|
| Phase 1 | ✅ Complete | 2026-01-28 | 서비스 실행 완료 |
| Phase 2 | ✅ Complete | 2026-01-28 | API 통합 검증 완료 |
| Phase 3 | ✅ Complete | 2026-01-28 | Frontend UI 개선 완료 |
| Phase 4 | ⏳ Pending | - | Market Gate 섹터 시각화 (선택사항) |
| **DB Data Collection** | ✅ Complete | 2026-01-28 | Kiwoom API로 80개 데이터 수집 |
| **Signal Scoring** | ✅ Complete | 2026-01-28 | flow_score, volume_score 구현 완료 |
| **거래대금 점수 기준 수정** | ✅ Complete | 2026-01-28 | TDD로 기준 수정 (5,000억/1,000억/300억) |

---

**Last Updated:** 2026-01-28
**다음 작업:** Phase 4 선택 또는 완료

## 📝 Notes

### 2026-01-28
- ✅ Phase 1 완료: 서비스 실행
  - Signal Engine (5113) ✅
  - API Gateway (5111) ✅
  - Frontend (5110) ✅
- ✅ Phase 2 완료: API 통합 검증
  - `/api/kr/jongga-v2/latest` 프록시 동작 확인
  - `/api/kr/jongga-v2/analyze` 단일 종목 분석 API 추가
  - score.detail 포함하여 응답 반환
- ✅ Phase 3 완료: Frontend UI 개선
  - score.detail 표시 (확장 행)
  - reasons 표시
  - target_price, stop_loss, position_size 표시
  - TypeScript 타입 안정성 확보
  - 빌드 성공 확인
- ✅ DB 데이터 수집 완료
  - Kiwoom REST API 토큰 발급 테스트 성공
  - 4개 종목 20일치 데이터 수집 (총 80개 daily_prices, 80개 institutional_flows)
  - SK하이닉스, NAVER, 현대차, 삼성전자 데이터 저장
- ✅ SignalScorer 수정 완료
  - SessionLocal() 사용 수정 (get_session() 버그 수정)
  - flow_score 구현 (외국인+기관 동시 순매수 감지)
  - 점수 계산 작동 확인 (삼성전자: 4점, NAVER: 3점)
- ✅ 거래대금 점수 기준 수정 (TDD)
  - 문제점: 단위 오류 (500억 → 5,000억)
  - 수정: 3점(5,000억+), 2점(1,000억+), 1점(300억+)
  - RED: 4개 실패 → GREEN: 7개 전체 통과
