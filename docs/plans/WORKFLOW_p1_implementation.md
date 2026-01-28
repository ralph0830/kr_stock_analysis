# P1 핵심 기능 구현 워크플로우

> Open Architecture 마이그레이션 완료 후 실제 기능 구현 계획
> 생성일: 2026-01-23
> 상태: 진행 중

---

## 📊 개요

### 현재 상태
- ✅ 7/7 Phase 마이그레이션 완료 (100%)
- ✅ 테스트: 47 passed, 12 skipped (3.65s)
- ✅ 인프라: PostgreSQL + TimescaleDB, Redis 구축 완료
- ✅ 데이터 수집: KRXCollector 기본 구조 완료
- ✅ 분석 모듈: SentimentAnalyzer, NewsScorer 기본 구조 완료

### 구현 목표
1. **LLM 뉴스 분석 연동** (Gemini API)
   - 뉴스 크롤링 또는 API 연동
   - 감성 분석 프롬프트 작성
   - 종가베팅 뉴스 점수화

2. **VCP 패턴 분석 개선**
   - 실제 차트 데이터 기반 분석
   - 볼린저밴드, 수축률 계산
   - SmartMoney 수급 분석

---

## 🎯 Milestones

### Milestone 1: LLM 뉴스 분석 연동 (1주)
- Week 1: API 설정 + 뉴스 수집 + 감성 분석 통합

### Milestone 2: VCP 패턴 분석 개선 (1주)
- Week 2: 실제 데이터 기반 분석 + 백테스팅 검증

---

## 📋 작업 목록 (Task List)

### 1. LLM 뉴스 분석 연동 - Gemini API 설정
**파일**: `.env`, `scripts/test_gemini_api.py`

**작업 내용**:
- [ ] GEMINI_API_KEY 환경 변수 설정
- [ ] API 연결 테스트 스크립트 작성
- [ ] Rate Limiting 전략 수립 (분당 15 요청 제한)
- [ ] Fallback 메커니즘 확인 (목업 분석)

**검증 기준**: API 호출 성공률 100%

**예상 시간**: 2-3시간

---

### 2. 뉴스 수집기 구현 - NewsCollector
**파일**: `src/collectors/news_collector.py`, `tests/unit/collectors/test_news_collector.py`

**작업 내용**:
- [ ] NewsCollector 클래스 구현
- [ ] 네이버 뉴스 RSS/크롤링 구현
- [ ] 다음 금융 뉴스 연동
- [ ] 연합뉴스 경제 뉴스 연동
- [ ] robots.txt 준수 및 요청 간격 설정 (1초 이상)
- [ ] 단위 테스트 작성

**검증 기준**: 종목별 일일 뉴스 10건 이상 수집

**예상 시간**: 4-5시간

---

### 3. 뉴스 감성 분석 파이프라인 구축
**파일**: `src/analysis/sentiment_analyzer.py`, `tests/integration/analysis/test_sentiment_pipeline.py`

**작업 내용**:
- [ ] SentimentAnalyzer Gemini API 실제 연동
- [ ] NewsCollector → SentimentAnalyzer 연결
- [ ] 배치 처리 구현 (여러 뉴스 동시 분석)
- [ ] 결과 캐싱 (Redis)
- [ ] 통합 테스트 작성

**검증 기준**: 뉴스 분석 평균 응답 시간 < 2초

**예상 시간**: 2-3시간

---

### 4. 종가베팅 뉴스 점수화 통합
**파일**: `services/signal_engine/scorer.py`, `tasks/signal_tasks.py`

**작업 내용**:
- [ ] SignalEngine Scorer에 NewsScorer 통합
- [ ] 일일 뉴스 점수 집계 태스크 구현
- [ ] Celery Beat 스케줄 등록 (2시간마다)
- [ ] 종가베팅 시그널 생성 태스크와 연결

**검증 기준**: 뉴스 점수가 시그널 생성에 반영됨

**예상 시간**: 2-3시간

---

### 5. VCP 패턴 분석 개선 - 실제 데이터 기반
**파일**: `services/vcp_scanner/vcp_analyzer.py`, `tests/integration/services/test_vcp_analyzer.py`

**작업 내용**:
- [ ] 실제 차트 데이터 기반 볼린저밴드 계산
- [ ] 20일 이동평균, 2표준편차 설정
- [ ] 수축률 계산 로직 개선 (현재/평균 밴드폭)
- [ ] 거래량 감소율 계산 (최근 5일 vs 이전 20일)
- [ ] 단위 테스트 작성 (과거 데이터 기반)

**검증 기준**: 볼린저밴드 계산 정확도 100%

**예상 시간**: 3-4시간

---

### 6. SmartMoney 수급 분석 개선
**파일**: `services/vcp_scanner/vcp_analyzer.py`

**작업 내용**:
- [ ] 외국인 순매수 5일 추향 계산
- [ ] 기관 순매수 5일 추향 계산
- [ ] 연기금 순매수 추향 반영
- [ ] 외국인 지분율 반영
- [ ] 점수 가중치 튜닝 (외국인 40%, 기관 30%)
- [ ] 백테스팅 검증

**검증 기준**: 수급 분석 정확도 70% 이상

**예상 시간**: 2-3시간

---

### 7. Celery 뉴스 태스크 구현
**파일**: `tasks/news_tasks.py`, `tasks/celery_app.py`

**작업 내용**:
- [ ] `collect_news()`: 종목 뉴스 수집 (1시간마다)
- [ ] `analyze_sentiment()`: 감성 분석 (2시간마다)
- [ ] `calculate_news_scores()`: 일일 뉴스 점수 집계
- [ ] 태스크 체이닝: collect → analyze → score → signal
- [ ] 에러 핸들링 및 재시도 정책

**검증 기준**: 태스크 실행 성공률 95% 이상

**예상 시간**: 2-3시간

---

### 8. 통합 테스트 및 검증
**파일**: `tests/integration/e2e/test_full_pipeline.py`

**작업 내용**:
- [ ] 뉴스 수집 → 감성 분석 → 점수화 → 시그널 생성 E2E 테스트
- [ ] VCP 스캔 → SmartMoney 분석 → 시그널 생성 E2E 테스트
- [ ] 부하 테스트 (Locust)
- [ ] 데이터베이스 성능 테스트
- [ ] 캐시 효율성 측정

**검증 기준**: 전체 테스트 통과, 응답 시간 p95 < 200ms

**예상 시간**: 3-4시간

---

## 🔧 기술적 고려사항

### Gemini API 연동
- **API Key 관리**: `.env` 파일에 `GEMINI_API_KEY` 설정
- **Rate Limiting**: 분당 15 요청 제한 (Free Tier)
- **Fallback 전략**: API 실패 시 키워드 기반 목업 분석 사용
- **비용 관리**: 토큰 수 추적, 일일 사용량 모니터링

### 뉴스 수집
- **크롤링 정책**: robots.txt 준수, 요청 간격 1초 이상
- **다중 소스**: 네이버, 다음, 연합뉴스 (RSS 우선)
- **User-Agent**: 식별 가능한 User-Agent 설정
- **에러 핸들링**: HTTP 429 (Too Many Requests) 처리

### VCP 분석
- **볼린저밴드**: 20일 이동평균, 2표준편차
- **수축률**: 현재 밴드폭 / 20일 평균 밴드폭
- **거래량**: 최근 5일 평균 / 이전 20일 평균
- **SmartMoney**: 외국인 40%, 기관 30%, 기술적 20%, 펀더멘털 10%

---

## 📁 파일 구조

```
kr_stock/
├── src/
│   ├── collectors/
│   │   ├── base.py                    # ✅ 기존
│   │   ├── krx_collector.py           # ✅ 기존
│   │   └── news_collector.py          # 🆕 신규
│   └── analysis/
│       ├── sentiment_analyzer.py      # ✅ 기존 (API 연동 필요)
│       ├── news_scorer.py             # ✅ 기존
│       └── vcp_analyzer_improved.py   # 🆕 신규 (또는 기존 파일 수정)
├── tasks/
│   ├── celery_app.py                  # ✅ 기존 (스케줄 추가)
│   ├── news_tasks.py                  # 🆕 신규
│   ├── signal_tasks.py                # ✅ 기존 (연결 필요)
│   ├── scan_tasks.py                  # ✅ 기존
│   └── market_tasks.py                # ✅ 기존
├── scripts/
│   ├── test_gemini_api.py             # 🆕 신규
│   ├── test_news_collection.py        # 🆕 신규
│   └── test_vcp_analysis.py           # 🆕 신규
└── tests/
    ├── unit/
    │   ├── collectors/
    │   │   └── test_news_collector.py  # 🆕 신규
    │   └── analysis/
    │       └── test_sentiment_analyzer.py  # 🆕 신규
    └── integration/
        ├── analysis/
        │   └── test_sentiment_pipeline.py  # 🆕 신규
        └── e2e/
            └── test_full_pipeline.py    # 🆕 신규
```

---

## 🧪 테스트 전략

### Unit Tests (단위 테스트)
- Gemini API 호출 Mock (테스트용 목업 응답)
- 뉴스 파서 테스트 (HTML → 기사 파싱)
- VCP 계산 로직 검증 (볼린저밴드, 수축률)
- 감성 분석 결과 검증

### Integration Tests (통합 테스트)
- 뉴스 수집 → 감성 분석 → 점수화 파이프라인
- KRX 데이터 → VCP 분석 → 시그널 생성
- 실제 데이터베이스 연동 테스트

### E2E Tests (엔드투엔드 테스트)
- 전체 파이프라인 통합 테스트
- 부하 테스트 (Locust)
- 성능 테스트

---

## ⚠️ 리스크 완화

| 리스크 | 완화 전략 |
|--------|----------|
| Gemini API Rate Limit 초과 | 캐싱 + 배치 처리 + 요청 간격 제어 |
| 뉴스 소스 차단 | 다중 소스 + RSS 활용 + User-Agent 관리 |
| VCP 정확도 낮음 | 파라미터 튜닝 + 백테스팅 + 과거 데이터 검증 |
| 감성 분석 신뢰도 낮음 | 레이블링된 데이터로 검증 + 프롬프트 개선 |
| 데이터베이스 성능 | 인덱스 최적화 + 캐싱 + TimescaleDB 활용 |

---

## 📊 진행 현황

### 작업 상태
- [ ] Task 1: Gemini API 설정
- [ ] Task 2: 뉴스 수집기 구현
- [ ] Task 3: 감성 분석 파이프라인
- [ ] Task 4: 뉴스 점수화 통합
- [ ] Task 5: VCP 분석 개선
- [ ] Task 6: SmartMoney 분석 개선
- [ ] Task 7: Celery 뉴스 태스크
- [ ] Task 8: 통합 테스트

### 전체 진행률
- **Milestone 1**: 0% (0/4 tasks)
- **Milestone 2**: 0% (0/4 tasks)
- **전체**: 0% (0/8 tasks)

---

## 🚀 다음 단계

1. **Task 1 시작**: Gemini API 설정 및 테스트
2. **환경 변수 설정**: `.env` 파일에 `GEMINI_API_KEY` 추가
3. **API 연결 테스트**: `scripts/test_gemini_api.py` 실행

---

**마지막 업데이트**: 2026-01-23
**다음 리뷰**: Task 1 완료 후
