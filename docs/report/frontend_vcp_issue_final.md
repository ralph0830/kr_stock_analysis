# VCP 시그널 QA 최종 보고서

**분석 일자:** 2026-02-02
**분석 대상:** https://stock.ralphpark.com
**분석 범위:** VCP 시그널 생성 로직, 프론트엔드 표시, 백엔드 API, DB 상태

---

## 1. 결론 요약

### 핵심 발견

**전 종목 스캔 로직은 정상입니다.** 하지만 **종목 동기화 실패**로 인해 DB에 6개 종목만 저장되어 있습니다.

### 원인

1. **Kiwoom API 키 미설정** → 종목 동기화 실패
2. DB `stocks` 테이블에 **6개 종목만 존재**
3. VCP 스캔은 DB에 있는 종목만 스캔 → 6개 시그널만 생성

---

## 2. DB 실제 상태 확인

### 2.1 stocks 테이블

```sql
SELECT market, COUNT(*) FROM stocks GROUP BY market;
```

| market | count |
|--------|-------|
| KOSPI  | 5     |
| KOSDAQ | 1     |
| **total** | **6** |

### 2.2 저장된 종목 목록

| 티커 | 종목명 | 시장 |
|------|--------|------|
| 000020 | 동화약품 | KOSDAQ |
| 000660 | SK하이닉스 | KOSPI |
| 005380 | 현대차 | KOSPI |
| 005930 | 삼성전자 | KOSPI |
| 028260 | 삼성물산 | KOSPI |
| 035420 | NAVER | KOSPI |

### 2.3 VCP 시그널

```sql
SELECT ticker, score, grade FROM signals WHERE signal_type = 'VCP' AND status = 'OPEN';
```

| 티커 | 점수 | 등급 |
|------|------|------|
| 005930 | 61.0 | B |
| 005380 | 58.5 | B |
| 028260 | 56.5 | B |
| 035420 | 51.5 | B |
| 000660 | 48.5 | C |
| 000020 | 25.0 | C |

**DB의 6개 종목과 VCP 시그널 6개가 정확히 일치합니다!**

---

## 3. 원인 분석

### 3.1 종목 동기화 실패 로그

**Celery Worker 로그:**
```
[2026-02-02 06:30:49,085: INFO/ForkPoolWorker-4]
Task tasks.sync_tasks.sync_stock_list[...] retry: Retry in 60s:
Exception('Kiwoom API keys not configured')

[2026-02-02 06:32:49,119: ERROR/ForkPoolWorker-4]
Task tasks.sync_tasks.sync_stock_list[...] raised unexpected:
Exception('Kiwoom API keys not configured')
```

### 3.2 종목 동기화 코드

**파일:** `tasks/sync_tasks.py:61-67`

```python
# Kiwoom API 설정
app_key = os.getenv("KIWOOM_APP_KEY")
secret_key = os.getenv("KIWOOM_SECRET_KEY")

if not app_key or not secret_key:
    raise Exception("Kiwoom API keys not configured")
```

### 3.3 실제 시장 종목 수

| 시장 | DB 종목 수 | 실제 종목 수 | 차이 |
|------|-----------|-------------|------|
| KOSPI | 5 | 약 900+ | **-895** |
| KOSDAQ | 1 | 약 1,600+ | **-1,599** |
| **합계** | **6** | **약 2,500+** | **-2,494** |

---

## 4. VCP 스캔 로직 분석

### 4.1 스캔 대상 확인

**파일:** `services/vcp_scanner/vcp_analyzer.py:448-471`

```python
def fetch_stocks() -> List[tuple]:
    """DB에서 전체 종목 조회"""
    session = SessionLocal()
    try:
        query = select(Stock)
        if market == "KOSPI":
            query = query.where(Stock.market == "KOSPI")
        elif market == "KOSDAQ":
            query = query.where(Stock.market == "KOSDAQ")
        # ALL인 경우 필터 없이 전체 조회

        # 관리종목 제외
        query = query.where(or_(Stock.is_admin == False, Stock.is_admin.is_(None)))

        result = session.execute(query)
        stocks = result.scalars().all()
        return [(s.ticker, s.name) for s in stocks]
    finally:
        session.close()

# 스레드 풀에서 DB 작업 실행
stock_list = await asyncio.to_thread(fetch_stocks)
self.logger.info(f"VCP 스캔 시작: {market} 시장, {len(stock_list)} 종목")
```

**✅ 로직은 정상**
- DB의 `stocks` 테이블에서 전체 종목을 조회
- 관리종목 제외
- 병렬 비동기 분석

### 4.2 실제 동작

1. DB 조회 → 6개 종목 반환
2. 6개 종목 VCP 분석 실행
3. 6개 시그널 생성 및 DB 저장
4. 프론트엔드에 6개 시그널 표시

---

## 5. API 응답 데이터 (최종 확인)

**엔드포인트:** `GET /api/kr/signals/vcp?limit=50`

```json
{
  "count": 6,
  "generated_at": "2026-02-02T07:18:13.019802",
  "signals": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "score": 61,
      "grade": "B",
      "contraction_ratio": 0.72,
      "foreign_5d": 0,
      "inst_5d": 0
    },
    {
      "ticker": "005380",
      "name": "현대차",
      "score": 58.5,
      "grade": "B",
      "contraction_ratio": 0.67,
      "foreign_5d": 0,
      "inst_5d": 0
    },
    ...
  ]
}
```

---

## 6. 문제 요약

| 항목 | 기대 동작 | 실제 동작 | 상태 |
|------|----------|----------|------|
| **종목 동기화** | Kiwoom API로 전체 종목 수집 | **API 키 미설정으로 실패** | ❌ 실패 |
| **DB 종목 수** | KOSPI 900+, KOSDAQ 1600+ | **총 6개** | ❌ 문제 |
| **VCP 스캔 대상** | DB에 저장된 전체 종목 | DB의 6개 종목만 스캔 | ✅ 로직 정상 |
| **VCP 스캔 로직** | 전 종목 병렬 분석 | 6개 종목 병렬 분석 | ✅ 로직 정상 |
| **VCP 점수 계산** | 정상 계산 | 정상 계산됨 | ✅ 정상 |
| **수축률** | 볼린저밴드 기반 계산 | 정상 계산됨 | ✅ 정상 |
| **외국인/기관 수급** | 5일 순매수 합계 | **`institutional_flows` 테이블 데이터 부족으로 0** | ⚠️ 데이터 부족 |
| **프론트엔드 표시** | API 데이터 표시 | 정상 표시 | ✅ 정상 |

---

## 7. 근본 원인

### 7.1 Docker 환경 변수 전달 문제 (진짜 원인)

**`.env` 파일에는 Kiwoom API 키가 존재합니다:**

```bash
# .env 파일 (프로젝트 루트)
KIWOOM_APP_KEY=K7D9YzK-NqHHuW7UJJHTKxvP_u3aww7mmFzz2SFbzU8
KIWOOM_SECRET_KEY=Za6a5FSbUwrr26kKLvya9uzTi87Ny_N0J0hB4JSBT8w
KIWOOM_BASE_URL=https://api.kiwoom.com
KIWOOM_WS_URL=wss://api.kiwoom.com:10000/api/dostk/websocket
USE_KIWOOM_REST=true
```

**하지만 Docker 컨테이너별 환경 변수 상태:**

| 컨테이너 | Kiwoom 환경 변수 | 상태 |
|----------|------------------|------|
| `api-gateway` | ✅ 있음 | 정상 |
| `celery-worker` | ❌ **없음** | **문제** |
| `celery-beat` | ❌ 없음 | 문제 가능 |

**확인 명령어:**
```bash
docker exec api-gateway printenv | grep kiwoom
# KIWOOM_APP_KEY=... ✅

docker exec celery-worker printenv | grep kiwoom
# (출력 없음) ❌
```

**원인: `docker-compose.yml`에 `env_file` 설정 누락**

```yaml
# docker-compose.yml
api-gateway:
  profiles: [dev, prod]
  build:
    context: .
    dockerfile: services/api_gateway/Dockerfile
  # env_file 설정 없음!

celery-worker:
  profiles: [dev, prod]
  build:
    context: .
    dockerfile: Dockerfile.worker
  # env_file 설정 없음!
```

### 7.2 종목 동기화 실패 로직

**Celery Worker 로그:**
```
[2026-02-02 06:30:49,085: INFO/ForkPoolWorker-4]
Task tasks.sync_tasks.sync_stock_list[...] retry: Retry in 60s:
Exception('Kiwoom API keys not configured')
```

**파일:** `tasks/sync_tasks.py:61-67`

```python
# Kiwoom API 설정
app_key = os.getenv("KIWOOM_APP_KEY")
secret_key = os.getenv("KIWOOM_SECRET_KEY")

if not app_key or not secret_key:
    raise Exception("Kiwoom API keys not configured")
```

`celery-worker` 컨테이너에 환경 변수가 없어서 `os.getenv()`가 `None`을 반환하고 예외가 발생합니다.

### 7.3 2차적 원인 (수급 데이터)

**`institutional_flows` 테이블 데이터 부족**

- 외국인/기관 수급 데이터를 수집하는 태스크가 실행되지 않거나 실패
- `foreign_net_5d`, `inst_net_5d`가 0으로 표시됨

### 7.4 영향도

1. **종목 동기화 실패** → DB에 6개 종목만 저장
2. **VCP 스캔은 정상** → 하지만 6개 종목만 스캔
3. **사용자 경험** → 6개 시그널만 표시 (하드코딩처럼 보임)

---

## 8. 개선 권장 사항

### 8.1 즉시 조치 (필수) - docker-compose.yml 수정

**문제:** `docker-compose.yml`에 `env_file` 설정이 없어서 `.env` 파일이 컨테이너에 전달되지 않음

**해결 방법 1: env_file 추가 (권장)**

```yaml
# docker-compose.yml
services:
  api-gateway:
    profiles: [dev, prod]
    build:
      context: .
      dockerfile: services/api_gateway/Dockerfile
    env_file:
      - .env  # 추가

  celery-worker:
    profiles: [dev, prod]
    build:
      context: .
      dockerfile: Dockerfile.worker
    env_file:
      - .env  # 추가

  celery-beat:
    profiles: [dev, prod]
    build:
      context: .
      dockerfile: Dockerfile.worker
    env_file:
      - .env  # 추가

  # 기타 서비스도 동일하게 추가
  vcp-scanner:
    env_file:
      - .env
```

**해결 방법 2: environment 변수 직접 설정 (대안)**

```yaml
# docker-compose.yml
services:
  celery-worker:
    environment:
      - KIWOOM_APP_KEY=${KIWOOM_APP_KEY}
      - KIWOOM_SECRET_KEY=${KIWOOM_SECRET_KEY}
      - KIWOOM_BASE_URL=${KIWOOM_BASE_URL}
      - KIWOOM_WS_URL=${KIWOOM_WS_URL}
```

**적용 후 재시작:**

```bash
# 1. 컨테이너 재생성
docker compose down
docker compose up -d

# 2. 환경 변수 확인
docker exec celery-worker printenv | grep KIWOOM

# 3. 종목 동기화 수동 실행
docker exec celery-worker celery -A tasks.celery_app call tasks.sync_tasks.sync_stock_list '["KOSPI", "KOSDAQ"]'
```

**4. DB 상태 확인**

```sql
-- 종목 수 확인
SELECT market, COUNT(*) FROM stocks GROUP BY market;

-- 정상적이라면 KOSPI 900+, KOSDAQ 1600+여야 함
```

### 8.2 2차 개선 사항

**1. 수급 데이터 수집 태스크 확인**

- `institutional_flows` 테이블에 데이터가 수집되고 있는지 확인
- 수급 데이터 수집 태스크가 정상 실행되는지 확인

**2. 에러 알림 설정**

- 종목 동기화 실패 시 알림 추가
- API 키 미설정 경고 메시지 개선

**3. 하드코딩 오해 방지**

- 프론트엔드에 "DB에 N개 종목만 저장됨" 안메시지 추가
- 관리자 페이지에서 종목 동기화 상태 표시

---

## 9. 하드코딩 여부 결론

### ❌ 하드코딩 아님

**증거:**

1. **DB에 6개 종목이 저장**되어 있고, 이것이 VCP 시그널 6개와 정확히 일치함
2. **VCP 스캔 로직은 DB에서 종목을 조회** (`select(Stock)`)
3. **로그에 VCP 스캔 시작 메시지** (`VCP 스캔 시작: ALL 시장, 6 종목`)
4. **`docker-compose.yml`에 `env_file` 누락**으로 `celery-worker`에 환경 변수 전달 실패

### ✅ 종목 동기화 실패로 인한 부작용

- 사용자가 보기에는 "하드코딩된 6개"처럼 보이지만, 실제로는 **종목 동기화 실패**로 DB에 6개만 저장된 상태
- 코드 로직은 정상적으로 전 종목 스캔을 수행함

---

## 10. 부록: 관련 파일

### 종목 동기화
- `tasks/sync_tasks.py` - 종목 동기화 Celery 태스크
- `tasks/celery_app.py` - Celery 설정 및 스케줄

### VCP 스캔
- `services/vcp_scanner/vcp_analyzer.py` - VCP 분석 로직
- `services/vcp_scanner/main.py` - VCP Scanner 서비스
- `services/api_gateway/routes/triggers.py` - VCP 스캔 트리거

### Repository
- `src/repositories/stock_repository.py` - 종목 DB CRUD
- `src/repositories/vcp_signal_repository.py` - VCP 시그널 DB 조회

### 프론트엔드
- `frontend/app/page.tsx` - 메인 페이지
- `frontend/app/dashboard/kr/vcp/page.tsx` - VCP 페이지
- `frontend/lib/api-client.ts` - API 클라이언트

---

*보고서 작성: Claude (QA 전문가 모드)*
*분석 방법: Playwright 자동화 테스트 + 코드 정적 분석 + DB 직접 조회*
