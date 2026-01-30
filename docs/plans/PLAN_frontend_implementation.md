# 프론트엔드 미구현 기능 구현 계획

> **작성일**: 2026-01-30
> **범위**: MEDIUM (4-5 Phases, 10-20 hours)
> **목표**: 아카이브 문서(docs/archive_originals/)에 기록된 설계대로 프론트엔드 기능 구현

---

## 개요

아카이브 문서에 기록된 원래 설계와 현재 프론트엔드 구현 상태를 비교 분석한 결과, **핵심 페이지와 UI 컴포넌트가 누락**되었습니다. 이 플랜에서는 아카이브 문서에 설계된 기능을 단계별로 구현합니다.

### 현재 구현 상태

| 페이지/기능 | 경로 | 상태 | 비고 |
|------------|------|------|------|
| 통합 대시보드 | `/dashboard/page.tsx` | ✅ 구현됨 | Market Gate, 시스템 상태, 시그널 테이블 |
| 종가베팅 V2 시그널 | `/signals/page.tsx` | ✅ 구현됨 | 등급별 필터링, 점수 상세 |
| AI 챗봇 페이지 | `/chatbot/page.tsx` | ✅ 구현됨 | ChatbotWidget 연동 |
| 차트 페이지 | `/chart/page.tsx` | ✅ 구현됨 | 기본 차트 |
| 종목 상세 | `/stock/[ticker]/page.tsx` | ✅ 구현됨 | 상세 정보 |
| **VCP Signals 페이지** | `/dashboard/kr/vcp/page.tsx` | ❌ 누락 | AI 추천 뱃지, 실시간 업데이트 |
| **KR Market Overview** | `/dashboard/kr/page.tsx` | ❌ 누락 | 원형 프로그레스, 섹터 그리드 |
| **Closing Bet V2** | `/dashboard/kr/closing-bet/page.tsx` | ❌ 누락 | 차트 모달, 날짜 선택 |
| **네이버 차트 위젯** | 컴포넌트 | ❌ 누락 | 정적 차트 이미지 연동 |
| **Apple Dark 모드** | globals.css | ❌ 누락 | Glassmorphism, 애니메이션 |

---

## Phase 1: VCP Signals 전용 페이지 (1-2 hours)

### 목표
아카이브 문서 `PART_04_04_vcp_page.md`에 설계된 대로 VCP 시그널 전용 페이지 구현

### 구현 내용
- **실시간 가격 업데이트**: 60초 간격 자동 갱신
- **AI 추천 뱃지**: GPT + Gemini 이중 검증 표시
- **수급 데이터 시각화**: 외국인/기관 5일 순매수 (억/만 단위 포맷)
- **VCP 수축률 표시**: 0.6 이하 초록색 강조

### 품질 게이트 (Quality Gates)
- [ ] 페이지 빌드: `npm run build` 에러 없음
- [ ] 라이팅: `npm run lint` 통과
- [ ] 타입 체크: `npx tsc --noEmit` 통과
- [ ] API 연동: `/api/kr/signals` 데이터 정상 표시
- [ ] 실시간 업데이트: 60초마다 가격 갱신

### 작업 항목
1. **페이지 생성**: `frontend/app/dashboard/kr/vcp/page.tsx`
2. **컴포넌트**: AI 추천 뱃지 (`getAIBadge` 함수)
3. **유틸리티**: `formatFlow()` - 수급 포맷 (억/만)
4. **API 통합**: `krAPI.getSignals()`, `krAPI.getAIAnalysis()`

---

## Phase 2: KR Market Overview 페이지 (1-2 hours)

### 목표
아카이브 문서 `PART_05_01_kr_overview.md`에 설계된 대로 한국 주식 시장 개요 페이지 구현

### 구현 내용
- **Market Gate 원형 프로그레스**: SVG 기반 원형 게이지
- **섹터 그리드**: KOSPI 200 섹터별 bullish/bearish 카드
- **KPI 카드 4종**: 오늘 시그널, VCP 성과, Closing Bet 성과, 리프레시
- **백테스트 요약**: `/api/kr/backtest-summary` 연동

### 품질 게이트
- [ ] 페이지 빌드 성공
- [ ] 라이핑/타입 체크 통과
- [ ] Market Gate 데이터 연동 (`/api/kr/market-gate`)
- [ ] 백테스트 데이터 표시 (`/api/kr/backtest-summary`)
- [ ] 색안 최적화 (다크 모드)

### 작업 항목
1. **페이지 생성**: `frontend/app/dashboard/kr/page.tsx`
2. **컴포넌트**: 원형 프로그레스 SVG, 섹터 카드
3. **백테스트 상태**: Accumulating 상태 처리
4. **API 통합**: `krAPI.getMarketGate()`, 백테스트 API

---

## Phase 3: Closing Bet V2 페이지 (2-3 hours)

### 목표
아카이브 문서 `PART_05_02_closing_bet.md`에 설계된 대로 종가베팅 V2 전용 페이지 구현

### 구현 내용
- **날짜 선택기**: latest + 특정 날짜 선택 (`/api/kr/jongga-v2/dates`)
- **차트 모달**: 네이버 금융 차트 위젯 연동
- **점수 바 컴포넌트**: 뉴스/수급/차트/거래대금/캔들 기간별 시각화
- **체크리스트 표시**: 뉴스 있음, 수급 양호, 신고가 등 뱃지
- **엔진 실행 버튼**: `/api/kr/jongga-v2/run` POST 요청

### 품질 게이트
- [ ] 페이지 빌드 성공
- [ ] 라이핑/타입 체크 통과
- [ ] jongga-v2 API 연동 (latest, dates, history)
- [ ] 차트 모달 정상 작동
- [ ] 엔진 실행 기능 테스트

### 작업 항목
1. **페이지 생성**: `frontend/app/dashboard/kr/closing-bet/page.tsx`
2. **컴포넌트**: `ChartModal`, `NaverChartWidget`, `ScoreBar`
3. **날짜 선택 드롭다운**: 동적 날짜 목록 로딩
4. **API 통합**: jongga-v2 관련 모든 엔드포인트

---

## Phase 4: Apple Dark 모드 디자인 시스템 (1-2 hours)

### 목표
아카이브 문서에 기록된 Apple Dark Mode 디자인 시스템 적용

### 구현 내용
- **globals.css 업데이트**: Apple Dark Mode 팔레트, Glassmorphism 효과
- **애니메이션**: fadeIn, pulse-glow 키프레임 정의
- **스크롤바**: 커스텀 스타일 (webkit-scrollbar)
- **유�리티 클래스**: `.glass-card`, `.apple-glass`, `.text-xxs`

### 품질 게이트
- [ ] 빌드 성공
- [ ] 라이팅/타입 체크 통과
- [ ] 다크 모드 전환 정상 작동
- [ **모든** 페이지에 일관된 디자인 적용
- [ ] 애니메이션 부드럽게 작동

### 작업 항목
1. **CSS 업데이트**: `frontend/app/globals.css`에 Apple 스타일 추가
2. **유틸티 클래스**: Tailwind config 확장 또는 커스텀 클래스
3. **다크 모드 전환**: `ThemeToggle.tsx` 개선

---

## Phase 5: 네이버 차트 위젯 통합 (1 hour)

### 목표
종가베팅 V2 페이지에서 네이버 금융 차트 이미지를 모달로 표시

### 구현 내용
- **정적 차트 이미지**: `https://ssl.pstatic.net/imgfinance/chart/item/candle/day/{symbol}.png`
- **인터랙티브 차트 링크**: 네이버 모바일 주식 차트로 이동
- **모달 컴포넌트**: ESC 키 닫기, 배경 클릭 닫기

### 품질 게이트
- [ ] 빌드 성공
- [ ] 라이핑/타입 체크 통과
- [ ] 차트 이미지 정상 로딩
- [ ] 모달 열기/닫기 정상 작동
- [ ] 반응형 디자인 (모바일 호환)

### 작업 항목
1. **NaverChartWidget 컴포넌트**: `frontend/components/NaverChartWidget.tsx`
2. **ChartModal 컴포넌트**: `frontend/components/ChartModal.tsx`
3. **Closing Bet 페이지에 통합**: 차트 버튼 클릭 시 모달 오픈

---

## 아키텍처 의사 결정

### 페이지 구조
```
frontend/app/
├── dashboard/
│   ├── page.tsx (기존 통합 대시보드)
│   └── kr/
│       ├── page.tsx (NEW - KR Market Overview)
│       ├── vcp/
│       │   └── page.tsx (NEW - VCP Signals)
│       └── closing-bet/
│           └── page.tsx (NEW - 종가베팅 V2)
```

### API 엔드포인트 연동 상태
| 엔드포인트 | 상태 | 사용 위치 |
|-----------|------|----------|
| `GET /api/kr/signals` | ✅ 구현됨 | VCP 페이지 |
| `GET /api/kr/market-gate` | ✅ 구현됨 | KR Overview |
| `GET /api/kr/ai-analysis` | ✅ 구현됨 | VCP AI 추천 |
| `GET /api/kr/jongga-v2/latest` | ✅ 구현됨 | Closing Bet V2 |
| `GET /api/kr/jongga-v2/dates` | ✅ 구현됨 | Closing Bet 날짜 선택 |
| `GET /api/kr/jongga-v2/history/{date}` | ✅ 구현됨 | 특정 날짜 조회 |
| `POST /api/kr/jongga-v2/run` | ✅ 구현됨 | 엔진 실행 |
| `GET /api/kr/backtest-summary` | ✅ 구현됨 | 백테스트 KPI |
| `POST /api/kr/realtime-prices` | ✅ 구현됨 | 실시간 가격 |

---

## 리스크 평가

| 리스크 | 확률 | 영향 | 완화 전략 |
|------|------|------|----------|
| API 연동 실패 | Medium | High | apiClient.ts 이미 구현됨, 에러 핸들링 확인 |
| 네이버 차트 이미지 로딩 | Low | Medium | 타임스탬프 파라미터로 캐시 방지 |
| 다크 모드 깨짐 | Low | Low | 기존 ThemeToggle.tsx 유지 |
| 타입 충돌 | Medium | Medium | 기존 types/index.ts와 호환성 확인 |

---

## 롤백 전략

각 Phase는 독립적으로 롤백 가능:
- **코드 삭제**: 새로 생성한 페이지/컴포넌트 삭제
- **API 변경**: 기존 apiClient.ts는 수정하지 않음
- **경로 변경: 기존 `/dashboard/page.tsx`는 유지

---

## 진행 상태

**Last Updated**: 2026-01-30

### Phase 진행률
- [x] Phase 1: VCP Signals 페이지 (100%)
- [x] Phase 2: KR Market Overview (100%)
- [x] Phase 3: Closing Bet V2 (100%)
- [x] Phase 4: Apple Dark 모드 (100%)
- [x] Phase 5: 네이버 차트 위젯 (100%)

### 완료된 페이지/컴포넌트
1. **VCP Signals 페이지**: `/dashboard/kr/vcp/page.tsx`
   - AI 추천 뱃지 (GPT + Gemini)
   - 실시간 가격 업데이트 (60s 간격)
   - 수급 데이터 포맷 (억/만 단위)
   - VCP 수축률 표시

2. **KR Market Overview 페이지**: `/dashboard/kr/page.tsx`
   - Market Gate 원형 프로그레스
   - 섹터별 bullish/bearish 카드
   - 백테스트 KPI 표시
   - 실시간 데이터 갱신

3. **Closing Bet V2 페이지**: `/dashboard/kr/closing-bet/page.tsx`
   - 날짜 선택기
   - 점수 바 컴포넌트 (12점 스코어링)
   - 체크리스트 뱃지
   - 네이버 차트 모달
   - 엔진 실행 버튼

4. **Apple Dark Mode 디자인 시스템**: `app/globals.css`
   - Apple 스타일 다크 모드 팔레트
   - Glassmorphism 효과
   - 커스텀 스크롤바
   - 애니메이션 (fadeIn, pulse-glow, shimmer)

5. **네이버 차트 위젯**: `components/NaverChartWidget.tsx`
   - NaverChartWidget 컴포넌트
   - NaverChartButton 컴포넌트
   - ChartModal 컴포넌트 (ESC 키 지원)

---

## 학습 노트

구현 진행 중 발견된 이슈나 개선사항을 여기에 기록합니다.
