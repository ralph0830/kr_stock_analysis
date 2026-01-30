# PLAN: 뉴스 링크 기능 고도화

**CRITICAL INSTRUCTIONS**: After completing each phase:
1. ✅ Check off completed task checkboxes
2. 🧪 Run all quality gate validation commands
3. ⚠️ Verify ALL quality gate items pass
4. 📅 Update "Last Updated" date
5. 📝 Document learnings in Notes section
6. ➡️ Only then proceed to next phase

⛔ DO NOT skip quality gates or proceed with failing checks

---

## Overview

### 목표
1. 실제 뉴스 기사 URL을 크롤링하여 DB 저장
2. 챗봇 응답에 클릭 가능한 뉴스 링크 표시
3. 프론트엔드에서 링크 클릭 시 새 탭에서 뉴스 열기
4. 자동 뉴스 수집 스케줄마다 DB 업데이트

### 현재 문제점
- 네이버 뉴스 크롤링이 실패 (HTML 구조 변경 가능성)
- 실제 뉴스 URL이 아닌 네이버 메인 페이지 링크만 저장됨
- 프론트엔드에서 링크 클릭 시 이동 기능 없음

### 접근 방식
- **범위**: Comprehensive (전체 뉴스 시스템 개편)
- **뉴스 소스**: 국내 (네이버/연합뉴스/ETF관련/등)
- **TDD**: 테스트 주도 개발

---

## Phase Breakdown

### Phase 1: 네이버 뉴스 크롤러 개선

**Goal**: 네이버 금융 뉴스에서 실제 기사 URL 크롤링

**Test Strategy**:
- 단위 테스트: URL 파싱 로직 검증
- 통합 테스트: 실제 네이버 페이지 요청
- 커버리지: 80%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/unit/collectors/test_news_collector_url.py` 작성
  - [ ] `test_extract_naver_article_url()` - 실제 기사 URL 추출
  - [ ] `test_naver_news_has_valid_url()` - URL 형식 검증
  - [ ] `test_multiple_articles_unique_urls()` - 중복 URL 확인

#### GREEN (구현)
- [ ] `src/collectors/news_collector.py` 크롤링 로직 수정
  - [ ] HTML 파서 업데이트 (최신 네이버 구조 반영)
  - [ ] `article_url`에서 전체 URL 추출 (상대 경로 → 절대 경로)
  - [ ] URL 유효성 검증

#### REFACTOR
- [ ] URL 파싱 로직 모듈화
- [ ] 에러 핸들링 개선

**Quality Gate**:
- [ ] 실제 뉴스 URL이 추출됨
- [ ] URL이 `https://news.naver.com/...` 형식
- [ ] `pytest tests/unit/collectors/test_news_collector_url.py -v`

**Rollback**: 기존 크롤링 로직 복원

---

### Phase 2: 연합뉴스 ETF관련 뉴스 크롤러 추가

**Goal**: 연합뉴스, ETF관련 뉴스 소스 추가

**Test Strategy**:
- 단위 테스트: 새로운 소스 파싱 로직
- 통합 테스트: 실제 사이트 요청
- 커버리지: 75%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/unit/collectors/test_yonhap_collector.py` 작성
  - [ ] `test_yonhap_rss_parsing()` - RSS 파싱
  - [ ] `test_extract_article_urls()` - URL 추출
- [ ] `tests/unit/collectors/test_etfnews_collector.py` 작성
  - [ ] `test_etf_news_parsing()` - ETF 뉴스 파싱

#### GREEN (구현)
- [ ] `src/collectors/yonhap_collector.py` 생성
  - [ ] 연합뉴스 RSS 피드 파싱
  - [ ] 기사 URL 추출
- [ ] `src/collectors/etfnews_collector.py` 생성
  - [ ] ETF관련 뉴스 크롤링

#### REFACTOR
- [ ] NewsCollector 기반 클래스로 리팩토링
- [ ] 공통 인터페이스 정의

**Quality Gate**:
- [ ] 연합뉴스 뉴스 수집 성공
- [ ] ETF 뉴스 수집 성공
- [ ] `pytest tests/unit/collectors/test_yonhap_collector.py -v`

**Rollback**: 새 파일 삭제

---

### Phase 3: AI 저장 시 뉴스 URL 자동 저장

**Goal**: 뉴스 수집/분석 시 실제 URL을 DB에 자동 저장

**Test Strategy**:
- 통합 테스트: 수집 → 저장 → 조회 흐름
- 커버리지: 80%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/integration/news/test_news_url_persistence.py` 작성
  - [ ] `test_news_collection_saves_urls()` - 수집 시 URL 저장
  - [ ] `test_retriever_returns_urls()` - retriever에서 URL 반환
  - [ ] `test_chatbot_shows_urls()` - 챗봇 응답에 URL 포함

#### GREEN (구현)
- [ ] `src/repositories/ai_analysis_repository.py` 업데이트 완료
- [ ] 뉴스 수집 태스크 수정 (`tasks/news_tasks.py`)
  - [ ] `news_pipeline_task`에서 뉴스 URL 추출
  - [ ] `save_analysis` 호출 시 news_urls 전달
- [ ] 감성 분석 시 수집된 articles의 URL 추출

#### REFACTOR
- [ ] 뉴스 수집 파이프라인 정리
- [ ] URL 저장 로직 캡�화화

**Quality Gate**:
- [ ] 뉴스 수집 시 DB에 실제 URL 저장됨
- [ ] 챗봇에서 조회된 데이터에 URL 포함
- [ ] `pytest tests/integration/news/test_news_url_persistence.py -v`

**Rollback**: 기존 태스크 로직 복원

---

### Phase 4: 프론트엔드 링크 클릭 이동 기능

**Goal**:

### Phase 4: 프론트엔드 링크 클릭 이동 기능

**Goal**: 챗봇 응답의 뉴스 링크를 클릭하면 새 탭에서 뉴스 열기

**Test Strategy**:
- E2E 테스트: Playwright로 링크 클릭 및 탭 이동 확인
- 커버리지: 70%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/e2e/chatbot/test_news_link_click.spec.ts` 작성
  - [ ] `test_news_link_click_opens_new_tab()` - 링크 클릭 시 새 탭
  - [ ] `test_news_link_has_correct_url()` - URL이 올바른지
  - [ ] `test_multiple_news_links_clickable()` - 여러 링크 모두 클릭 가능

#### GREEN (구현)
- [ ] 프롬프트에서 마크다운 링크 형식 유지
- [ ] 챗봇 응답 렌더링 시 링크에 `target="_blank"` 추가
- [ ] `rel="noopener noreferrer"` 보안 속성 추가

#### REFACTOR
- [ ] 링크 컴포넌트 생성 (재사용성)
- [ ] 외부 링크 vs 내부 링크 구분

**Quality Gate**:
- [ ] 응답의 뉴스 링크가 클릭 가능
- [ ] 클릭 시 새 탭에서 열림
- - `playwright test tests/e2e/chatbot/test_news_link_click.spec.ts`

**Rollback**: 프롬프트 수정 사항 제거

---

### Phase 5: 자동 뉴스 수집 스케줄

**Goal**: Celery Beat로 주기적 뉴스 수집 및 DB 업데이트

**Test Strategy**:
- 통합 테스트: 스케줄러 실행 테스트
- API 테스트: 수집 엔드포인트 테스트
- 커버리지: 70%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/integration/news/test_scheduled_collection.py` 작성
  - [ ] `test_daily_news_collection()` - 일일 수집 실행
  - [ ] `test_news_urls_updated()` - URL 업데이트 확인
- [ ] `tests/unit/tasks/test_news_tasks.py` 작성
  - [ ] `test_collect_and_save_task()` - 태스크 동작 확인

#### GREEN (구현)
- [ ] `tasks/news_tasks.py` 수정
  - [ ] `collect_and_save_task`에서 URL 저장 추가
  - [ ] Celery Beat 스케줄 추가 (`celeryconfig.py`)
  - [ ] 매일 오전 9시, 오후 3시 뉴스 수집
  - [ ] 수집된 뉴스 DB 저장 로직

#### REFACTOR
- [ ] 수집 주기 조정
- [ ] 중복 뉴스 처리 로직
- [ ] 실패 시 재시도 정책

**Quality Gate**:
- [ ] 스케줄러가 뉴스를 주기적으로 수집
- [ ] 수집된 뉴스에 실제 URL이 포함
- [ ] `celery -A tasks.celery beat` 스케줄 확인

**Rollback**: 스케줄 제거, 기존 태스크 유지

---

### Phase 6: 뉴스 API 엔드포트

**Goal**: 프론트엔드에서 직접 뉴스 조회 API 제공

**Test Strategy**:
- API 테스트: 엔드포트 응답 검증
- 커버리지: 75%

**Tasks**:

#### RED (테스트 작성)
- [ ] `tests/integration/api_gateway/test_news_api.py` 작성
  - [ ] `test_get_news_by_ticker()` - 종목별 뉴스 조회
  - [ ] `test_get_news_includes_urls()` - URL 포함 확인
  - [ ] `test_news_pagination()` - 페이지네이션

#### GREEN (구현)
- [ ] `services/api_gateway/routes/news.py` 생성
  - [ ] `GET /api/kr/news/{ticker}` - 종목별 뉴스
  - [ ] `GET /api/kr/news/latest` - 최신 뉴스
  - [ 응답 포맷: title, url, source, published_at

#### REFACTOR
- [ ] 캐시 레이어 적용
- [ ] 필터링 파라미터 (date, source)

**Quality Gate**:
- [ ] API에서 뉴스 목록 반환
- [ ] 각 뉴스에 실제 URL 포함
- [ ] `pytest tests/integration/api_gateway/test_news_api.py -v`

**Rollback**: 라우팅 파일 삭제

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 네이버 HTML 구조 변경 | Medium | High | 유연 보수 캐싱, CSS 선택자 다중 사용 |
| 크롤링 차단 (IP 밴) | High | Medium | 프록시/회전 사용, 여러 소스 분산 |
| 수집 데이터 부재 | Medium | Medium | Fallback 메커니즘, 빈 결과 반환 |
| DB 용량 초과 | Low | Medium | TTL 정책, 오래 데이터 정기 삭제 |

---

## Rollback Strategy

| Phase | Rollback 방법 |
|-------|---------------|
| Phase 1 | 기존 `_fetch_naver_news()` 로직 복원 |
| Phase 2 | 새로운 collector 파일 삭제 |
| Phase 3 | `news_pipeline_task` 이전 버전 유지 |
| Phase 4 | 프롬프트 수정 사항 제거 |
| Phase 5 | Celery Beat 설정 제거 |
| Phase 6 | 라우팅 파일 삭제 |

---

## Progress Tracking

### Last Updated
2026-01-30

### Phase Status
- [ ] Phase 1: 네이버 뉴스 크롤러 개선
- [ ] Phase 2: 연합뉴스 ETF관련 뉴스 크�롤러 추가
- [ ] Phase 3: AI 저장 시 뉴스 URL 자동 저장
- [ ] Phase 4: 프론트엔드 링크 클릭 이동 기능
- [ ] Phase 5: 자동 뉴스 수집 스케줄
- [ ] Phase 6: 뉴스 API 엔드포인트

---

## Notes

### Learnings
(Update after each phase)

### Issues Found
- 네이버 뉴스 크롤링 HTML 구조 확인 필요
- 현재 뉴스 수집 결과 0건 (실제 서비스 환경에서)

### Decisions Made
- TDD 방식으로 개발
- 국내 뉴스 소스 우선 (안정성, 크롤링 용이)
- Celery Beat로 주기적 수집 (매일 2회)
- 클라이언트에서 `target="_blank"`로 새 탭 오픈
