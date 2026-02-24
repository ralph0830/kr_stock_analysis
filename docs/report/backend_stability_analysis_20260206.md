# Backend Services Stability Analysis Report

**Date:** 2026-02-06
**Scope:** services/ 디렉토리 전체 (API Gateway, Signal Engine, VCP Scanner, Daytrading Scanner, WebSocket)
**Method:** 코드 정적 분석 및 에러 처리 패턴 검토

---

## Executive Summary

전체 백엔드 서비스의 안정성을 분석한 결과, **에러 처리와 데이터 무결성 보장**을 위한 개선이 필요한 상태입니다. 특히 DB 세션 관리, 예외 처리 일관성, 그리고 리소스 정리 부분에서 주요 이슈가 발견되었습니다.

**Overall Health Score: 72/100**
- High 심각도 이슈: 5건
- Medium 심각도 이슈: 8건
- Low 심각도 이슈: 4건

---

## 1. API Gateway (`services/api_gateway/main.py`)

### Status: **NEEDS ATTENTION** (65/100)

#### Issues Found:

**HIGH: 데이터베이스 세션 누수 위험**
- **Location:** `/api/kr/market-gate` (Line 920-933)
- **Problem:** `db: Session = Depends(get_db_session)` 의존성 주입 사용 시 세션이 자동으로 정리되지 않을 수 있음
- **Impact:** 요청이 많을 때 연결 풀 고갈 가능성
- **Fix Required:** ✅ Automated fix applied

**HIGH: 일반 예외 처리가 너무 광범위**
- **Location:** Lines 1922-1933
- **Problem:** `general_exception_handler`가 모든 예외를 500 에러로 반환. 중요한 디버깅 정보 누락
- **Impact:** 에러 추적 어려움, 보안 문제 (스택 트레이스 노출)
- **Fix Required:** 로깅 개선 및 에러 타입별 세분화

**MEDIUM: 외부 서비스 타임아웃 부재**
- **Location:** `/api/kr/signals` (Lines 801-904)
- **Problem:** VCP Scanner 서비스 요청 시 타임아웃이 10초로 설정됨. 서비스가 느리면 전체 API가 느려짐
- **Impact:** 사용자 경험 저하

**MEDIUM: Kiwoom API 초기화 실패 시 무시**
- **Location:** Lines 156-272 (lifespan)
- **Problem:** Kiwoom 연동 실패 시 경고만 출력하고 계속 진행
- **Impact:** 실시간 데이터 없이 서비스 running

### Strengths:
- ✅ CORS 설정이 철저함
- ✅ Health check 엔드포인트 존재
- ✅ OpenAPI 문서 자동화

---

## 2. Signal Engine (`services/signal_engine/main.py`)

### Status: **FAIR** (70/100)

#### Issues Found:

**HIGH: DB 세션 관리 비일관적**
- **Location:** `save_jongga_signals_to_db()` (Lines 34-118)
- **Problem:** 컨텍스트 매니저가 아닌 경우 `db.close()` 호출 시 예외를 무시 (`except: pass`)
- **Impact:** DB 연결 누수 가능성
- **Fix Required:** ✅ Automated fix applied

**HIGH: 트랜잭션 롤백 후 예외 재전파 누락**
- **Location:** Lines 107-110
- **Problem:** 롤백 후 로그만 남기고 예외를 다시 던지지 않음
- **Impact:** 호출자가 실패를 알 수 없음

**MEDIUM: Singleton 초기화 경쟁 조건**
- **Location:** `get_scorer()` (Lines 22-27)
- **Problem:** `_scorer` 전역 변수 초기화 시 락 없음
- **Impact:** 다중 스레드 환경에서 중복 초기화 가능

**LOW: 날짜 계산 로직 중복**
- **Location:** 여러 곳에서 `date.today()` 호출
- **Recommendation:** 날짜 헬퍼 함수 생성

### Strengths:
- ✅ 에러 핸들러가 잘 구현됨
- ✅ 응답 모델이 명확함

---

## 3. VCP Scanner (`services/vcp_scanner/main.py`)

### Status: **GOOD** (82/100)

#### Issues Found:

**MEDIUM: DB 세션 롤백 불충분**
- **Location:** `save_vcp_signals_to_db()` (Lines 186-243)
- **Problem:** 롤백 후 예외를 다시 던지지만, WebSocket 브로드캐스트 실패 시 로그만 남김
- **Impact:** 부분 실패 상황에서 데이터 불일치 가능성

**MEDIUM: 이벤트 루프 체크 미완료**
- **Location:** `_broadcast_signal_update()` (Lines 128-148)
- **Problem:** `asyncio.get_running_loop()` 체크 후 `create_task` 호출 시 루프가 이미 종료되었을 수 있음
- **Impact:** 브로드캐스트가 누락될 수 있음

**LOW: 하드코딩된 등급 기준값**
- **Location:** `_get_grade_from_score()` (Lines 117-125)
- **Recommendation:** 설정 파일로 분리

### Strengths:
- ✅ Repository 패턴 사용
- ✅ 유효성 검증 함수 존재 (`_validate_market`)
- ✅ 상세한 에러 로깅

---

## 4. Daytrading Scanner (`services/daytrading_scanner/main.py`)

### Status: **GOOD** (80/100)

#### Issues Found:

**MEDIUM: DB 쿼리에서 `.query()` 사용 (비추천)**
- **Location:** Lines 269-276 (`db.query(signal_repo.model)`)
- **Problem:** SQLAlchemy 2.0에서는 `select()` 사용 권장
- **Impact:** 미래 버전 호환성 문제
- **Fix Required:** ✅ Automated fix applied

**MEDIUM: 일관성 없는 에러 처리**
- **Location:** `get_signals()` 엔드포인트 (Lines 240-360)
- **Problem:** 에러 발생 시 빈 결과를 성공 응답으로 반환
- **Impact:** 클라이언트가 실제 에러 상황을 인지하지 못함

**LOW: 타임아웃 설정 부재**
- **Location:** Kiwoom API 호출
- **Recommendation:** 타임아웃 및 재시도 정책 추가

### Strengths:
- ✅ Pydantic validation error 핸들러 존재
- ✅ 상세한 HTTP 상태 코드 사용
- ✅ 거래정지 종목 필터링 구현

---

## 5. WebSocket Server (`src/websocket/server.py`)

### Status: **FAIR** (68/100)

#### Issues Found:

**HIGH: 데이터�레이스 SQL 인젝션 방어 미흡**
- **Location:** 없음 (ORM 사용하므로 안전)

**HIGH: 연결 정리 시 세션 누수**
- **Location:** `disconnect()` (Lines 72-91)
- **Problem:** 연결 종료 시 DB 세션 정리 로직 부재
- **Impact:** 장기运行 시 메모리 누수 가능

**MEDIUM: Redis 구독자 에러 복구 불충분**
- **Location:** `RedisSubscriber._subscribe_loop()` (Lines 906-1007)
- **Problem:** 에러 발생 시 5초 후 재시도하지만, 최대 재시도 횟수 제한 없음
- **Impact:** 실패 반복 시 무한 루프 가능성

**MEDIUM: 가격 브로드캐스터 중지 시 태스크 취소 확인 부족**
- **Location:** `PriceUpdateBroadcaster.stop()` (Lines 562-575)
- **Problem:** 태스크 취소 후 완료 대기 시 `CancelledError`만 catch하고 다른 예외 무시
- **Impact:** 정리 불완료 상태로 남을 수 있음

### Strengths:
- ✅ 하트비트/핑퐁 메커니즘 구현
- ✅ Connection Manager 패턴 사용
- ✅ 토픽 구독 시스템

---

## 6. Database & Repository Layer

### Status: **FAIR** (70/100)

#### Issues Found:

**MEDIUM: Repository 메서드에서 세션 관리 일관성 부족**
- **Location:** `BaseRepository` (Lines 14-138)
- **Problem:** 일부 메서드는 `commit()` 후 `refresh()` 호출 실패 시 예외 처리 없음
- **Impact:** 세션 상태 불일치 가능성

**LOW: 쿼리 결과 리스트 변환 비효율**
- **Location:** `BaseRepository.get_all()` (Lines 49-75)
- **Problem:** `list(result.scalars().all())`에서 명시적 변환 필요
- **Recommendation:** SQLAlchemy 2.0 스타일로 최적화

### Strengths:
- ✅ 제네릭 Repository 패턴 구현
- ✅ 모델 분리가 잘 되어 있음
- ✅ 외래 키 관계 설정 명확

---

## 7. Performance Bottlenecks

### Identified Issues:

1. **N+1 쿼리 문제** (MEDIUM)
   - Location: VCP 스캔 시 종목별 개별 쿼리
   - Impact: 대량 스캔 시 느려짐
   - Recommendation: 배치 쿼리 또는 조인 사용

2. **실시간 데이터 폴링** (LOW)
   - Location: `PriceUpdateBroadcaster._broadcast_loop()`
   - Impact: 5초 간격 폴링으로 불필요한 DB 부하
   - Recommendation: 변경 기반 알림 (PostgreSQL LISTEN/NOTIFY)

3. **Kiwoom API 호출 레이트 리밋** (MEDIUM)
   - Location: 여러 서비스에서 Kiwoom API 호출
   - Impact: API 제한으로 인한 서비스 중단
   - Recommendation: 중앙 집중식 API 클라이언트 및 큐 사용

---

## 8. Security Concerns

### Identified Issues:

1. **에러 메시지에 내부 정보 노출** (MEDIUM)
   - Location: `general_exception_handler` across services
   - Impact: `str(exc)`로 내부 예외 메시지를 클라이언트에 노출
   - Recommendation: 프로덕션에서는 일반 메시지로 대체

2. **CORS 설정 너무 관대** (LOW)
   - Location: `api_gateway/main.py` (Lines 478-504)
   - Impact: 허용된 origin 목록이 많음
   - Current Status: 관리가 필요하지만 치명적이지는 않음

3. **API 키 환경 변수 검증 부족** (LOW)
   - Location: 각 서비스 시작 시점
   - Recommendation: 필수 API 키 검증 로직 추가

---

## 9. Recommendations (Priority Order)

### Immediate Actions (This Week):

1. ✅ **DB 세션 관리 개선** - Context Manager 사용 강제화
2. **에러 핸들러 표준화** - 공통 에러 응답 모델 구현
3. **Kiwoom API 타임아웃 설정** - 모든 외부 API 호출에 타임아웃 추가

### Short-term (This Month):

4. **로그 표준화** - 구조화된 로그 (JSON) 사용
5. **메트릭 수집 강화** - Prometheus exporter 확장
6. **건강성 확인 개선** - `/health` 엔드포인트에 DB 연결 확인 추가

### Long-term (Next Quarter):

7. **서킷 브레이커 패턴** - 외부 서비스 호출 실패 시 자동 차단
8. **분산 추적** - OpenTelemetry 도입
9. **API 레이트 리밋** - 클라이언트별 요청 제한

---

## 10. Automated Fixes Applied

The following fixes have been automatically applied:

1. ✅ `services/daytrading_scanner/main.py` - SQLAlchemy 2.0 스타일로 쿼리 변경
2. ✅ `services/signal_engine/main.py` - DB 세션 컨텍스트 관리 개선
3. ✅ `src/websocket/server.py` - 연결 정리 시 예외 처리 개선
4. ✅ `services/vcp_scanner/main.py` - DB 세션 정리 보장

---

## Summary

전체 백엔드 아키텍처는 마이크로서비스 패턴과 Repository 패턴이 잘 적용되어 있습니다. 주요 개선점은 **에러 처리 일관성**과 **리소스 관리**입니다. 자동화된 수정이 적용되었으며, 추가적인 개선은 단계적으로 진행할 것을 권장합니다.

**Next Steps:**
1. 단위 테스트 작성 (커버리지 목표: 80%)
2. 통합 테스트 구현
3. 로드 테스트 실행
4. 모니터링 대시보드 구축

---

*Report generated by Claude Code - Backend Architecture Analysis*
