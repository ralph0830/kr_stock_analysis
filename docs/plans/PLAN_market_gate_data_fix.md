# Market Gate KOSPI/KOSDAQ 데이터 표시 수정 계획

**작성일**: 2026-01-30
**우선순위**: P1 (대시보드 핵심 기능)
**예상 시간**: 2-3시간

---

## 📋 개요

대시보드 Market Gate 상태에서 KOSPI/KOSDAQ 지수 데이터가 "데이터 없음"으로 표시되는 문제를 해결합니다.

### 현재 상태
- Market Gate 레벨 50 (YELLOW) - 정상 표시
- KOSPI: "데이터 없음" ❌
- KOSDAQ: "데이터 없음" ❌

### 원인 분석
1. **DB `market_status` 테이블이 비어있음** (0건)
2. **API Gateway 컬럼명 불일치**: `kospi_close` → `kospi`, `kosdaq_close` → `kosdaq`

---

## 🎯 목표

1. Kiwoom REST API를 사용하여 KOSPI/KOSDAQ 지수 실시간 데이터 수집
2. 섹터별 ETF 데이터도 함께 표시 (반도체, 2차전지 등)
3. 데이터베이스 `market_status` 테이블에 데이터 저장
4. API Gateway 컬럼명 버그 수정

---

## 📝 Phase 구분

### Phase 1: API Gateway 컬럼명 수정 (버그 수정)
- **목표**: 컬럼명 불일치 버그 수정
- **파일**: `services/api_gateway/main.py`
- **작업**:
  - [ ] `kospi_close` → `kospi`로 수정
  - [ ] `kosdaq_close` → `kosdaq`로 수정
- **Quality Gate**: API 호출 시 응답 정상 반환

### Phase 2: Kiwoom REST API로 지수 데이터 수집
- **목표**: KOSPI/KOSDAQ 실시간 지수 데이터 수집
- **파일**: `src/kiwoom/rest_api.py` (기존 확장)
- **작업**:
  - [ ] `get_index_price(ticker)` 메서드 구현 (KOSPI: "001", KOSDAQ: "201")
  - [ ] Market Status 생성/업데이트 Repository 메서드 구현
  - [ ] Celery 태스크로 주기적 업데이트 (1시간마다)
- **Quality Gate**: DB에 데이터 저장 확인

### Phase 3: 섹터별 데이터 수집
- **목표**: 섹터 ETF/지수 데이터 수집
- **파일**: `src/kiwoom/rest_api.py`
- **작업**:
  - [ ] 주요 섹터 ETF ticker 정의 (반도체, 2차전지, 자동차, 바이오 등)
  - [ ] 섹터 데이터 수집 및 `sector_scores` JSON 필드에 저장
  - [ ] API 응답에 섹터 데이터 포함
- **Quality Gate**: 프론트엔드에 섹터별 현황 표시

---

## 🔧 기술 세부사항

### Kiwoom REST API 지수 ticker
- KOSPI: `001`
- KOSDAQ: `201`

### 섹터 ETF ticker (예시)
- 반도체: `069500` (KODEX 반도체)
- 2차전지: `305720` (KODEX 2차전지)
- 자동차: `116380` (KODEX 자동차)
- 바이오: `327610` (KODEX 바이오)

### DB 모델 참고 (`MarketStatus`)
```python
class MarketStatus(Base):
    date = Column(Date, unique=True, nullable=False)
    kospi = Column(Float, nullable=True)           # KOSPI 종가
    kospi_change_pct = Column(Float, default=0.0)  # KOSPI 변동률
    kosdaq = Column(Float, nullable=True)          # KOSDAQ 종가
    kosdaq_change_pct = Column(Float, default=0.0) # KOSDAQ 변동률
    gate = Column(String(10))                       # GREEN, YELLOW, RED
    gate_score = Column(Integer, default=50)
    sector_scores = Column(JSON, nullable=True)     # 섹터 점수
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## ✅ 체크리스트

### Phase 1
- [ ] `services/api_gateway/main.py` 컬럼명 수정
- [ ] API 테스트: `GET /api/kr/market-gate`
- [ ] 응답 필드명 확인

### Phase 2
- [ ] `src/kiwoom/rest_api.py`에 `get_index_price()` 메서드 구현
- [ ] `src/repositories/market_repository.py` 생성 (또는 기존 repo 확장)
- [ ] `tasks/market_tasks.py`에 `update_market_status()` 태스크 구현
- [ ] Celery Beat 스케줄 등록 (1시간마다)
- [ ] DB에 데이터 저장 확인

### Phase 3
- [ ] 섹터 ETF ticker 리스트 정의
- [ ] 섹터 데이터 수집 로직 구현
- [ ] `sector_scores` JSON 형식으로 저장
- [ ] 프론트엔드 섹터 카드 표시 확인

---

## 🔄 롤백 계획

- Phase 1: 코드 변경만 있으므로 git revert로 롤백
- Phase 2: DB 데이터만 추가되므로 코드만 revert
- Phase 3: Phase 2에 의존하므로 함께 롤백

---

## 📝 진행 상황

- [ ] Phase 1: API Gateway 컬럼명 수정
- [ ] Phase 2: Kiwoom REST API 지수 데이터 수집
- [ ] Phase 3: 섹터별 데이터 수집
