# Phase 1 실행 계획: Prometheus + Grafana 구축

**작성일**: 2026-02-06
**작성자**: DevOps Architect (Claude Code Agent)
**예상 기간**: 1주 (5-7일)

---

## 1. 개요

### 1.1 목표
- Prometheus로 전체 시스템 메트릭 수집
- Grafana로 실시간 모니터링 대시보드 구축
- AlertManager로 장애 알림 시스템 구축
- 핵심 Exporter 배포 (Node, cAdvisor, PostgreSQL, Redis)

### 1.2 범위
| 작업 | 예상 시간 | 우선순위 |
|------|-----------|----------|
| Docker Compose 설정 | 2시간 | P0 |
| Prometheus 설치/설정 | 2시간 | P0 |
| Grafana 설치/설정 | 2시간 | P0 |
| AlertManager 설치/설정 | 2시간 | P0 |
| Exporter 배포 | 3시간 | P0 |
| Alert 규칙 작성 | 4시간 | P0 |
| Grafana Dashboard 생성 | 5시간 | P0 |
| Slack 연동 | 1시간 | P1 |
| **총계** | **21시간** | - |

---

## 2. Day-by-Day 계획

### Day 1: 인프라 설치
- [ ] Docker Compose에 모니터링 스택 추가
- [ ] Prometheus 컨테이너 시작
- [ ] Grafana 컨테이너 시작
- [ ] AlertManager 컨테이너 시작
- [ ] 기본 동작 확인

### Day 2: Exporter 배포
- [ ] Node Exporter 배포
- [ ] cAdvisor 배포
- [ ] PostgreSQL Exporter 배포
- [ ] Redis Exporter 배포
- [ ] Prometheus 타겟 등록
- [ ] 메트릭 수집 확인

### Day 3: Alert 규칙
- [ ] Service Health Alert 작성
- [ ] Resource Usage Alert 작성
- [ ] Database Alert 작성
- [ ] Celery Alert 작성
- [ ] Alert 테스트

### Day 4: Grafana Dashboard
- [ ] System Overview Dashboard
- [ ] Service Health Dashboard
- [ ] API Performance Dashboard
- [ ] Database Dashboard
- [ ] Celery Dashboard

### Day 5: 알림 연동
- [ ] AlertManager Slack 연동
- [ ] Email 알림 설정
- [ ] 알림 테스트
- [ ] 문서화

---

## 3. 파일 구조

```
docker/compose/
├── config/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts/
│   │       ├── services.yml
│   │       ├── resources.yml
│   │       ├── database.yml
│   │       └── celery.yml
│   ├── alertmanager/
│   │   └── alertmanager.yml
│   └── grafana/
│       └── provisioning/
│           ├── dashboards/
│           │   └── dashboard.yml
│           └── datasources/
│               └── prometheus.yml
└── services/
    └── monitoring.yml
```

---

## 4. 설정 파일

### 4.1 docker-compose 통합

```bash
# docker-compose.yml 수정 필요
# 기존 파일에 include 추가:
# compose:
#   - docker-compose.yml
#   - infra.yml
#   - services/monitoring.yml  # <-- 추가
```

### 4.2 환경 변수 (.env)

```bash
# Monitoring
GRAFANA_ADMIN_PASSWORD=admin
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERT_EMAIL=admin@ralphpark.com
```

### 4.3 Nginx Proxy Manager 설정

| 경로 | 포워드 | 설명 |
|------|--------|------|
| `/grafana` | `localhost:3000` | Grafana 대시보드 |
| `/prometheus` | `localhost:9090` | Prometheus (선택) |
| `/alertmanager` | `localhost:9093` | AlertManager (선택) |

---

## 5. 실행 절차

### Step 1: 파일 생성
```bash
# 1. 디렉토리 생성
mkdir -p docker/compose/config/{prometheus/alerts,alertmanager,grafana/provisioning/{dashboards,datasources}}

# 2. 설정 파일 복사 (이 문서에서 작성)

# 3. 환경 변수 추가
echo "GRAFANA_ADMIN_PASSWORD=admin" >> .env
echo "SLACK_WEBHOOK_URL=YOUR_WEBHOOK_URL" >> .env
```

### Step 2: Docker Compose 시작
```bash
# 기존 서비스 중지
docker compose --profile dev down

# 모니터링 스택 포함하여 시작
docker compose --profile dev --profile monitoring up -d

# 로그 확인
docker compose logs -f prometheus grafana alertmanager
```

### Step 3: 동작 확인
```bash
# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# AlertManager
curl http://localhost:9093/-/healthy

# Exporter 목록
curl http://localhost:9100/metrics  # Node Exporter
curl http://localhost:9187/metrics  # PostgreSQL Exporter
curl http://localhost:9121/metrics  # Redis Exporter
```

### Step 4: Prometheus 타겟 확인
1. http://localhost:9090 접속
2. Status → Targets 메뉴
3. 모든 타겟이 "UP" 상태인지 확인

### Step 5: Grafana 접속
1. http://localhost:3000 접속
2. 기본 로그인: admin / admin (또는 환경 변수에서 설정한 비밀번호)
3. Data Source 확인 (Prometheus 연동 확인)
4. Dashboard 확인

---

## 6. 검증 체크리스트

### 6.1 Prometheus
- [ ] Prometheus 컨테이너 실행 중
- [ ] /-/healthy 엔드포인트 응답
- [ ] 모든 Exporter가 UP 상태
- [ ] 메트릭 수집 중 (PromQL 쿼리로 확인)
- [ ] Alert 규칙 로딩됨
- [ ] AlertManager 연결됨

### 6.2 Grafana
- [ ] Grafana 컨테이너 실행 중
- [ ] /api/health 엔드포인트 응답
- [ ] Prometheus Data Source 연결됨
- [ ] Dashboard 자동 로딩됨 (Provisioning)
- [ ] Panel에 데이터 표시됨
- [ ] 쿼리 실행 가능

### 6.3 AlertManager
- [ ] AlertManager 컨테이너 실행 중
- [ ] /-/healthy 엔드포인트 응답
- [ ] Slack으로 알림 전송 테스트 성공
- [ ] Email 알림 테스트 성공 (선택사항)

### 6.4 Exporter
- [ ] Node Exporter: 시스템 메트릭 수집
- [ ] cAdvisor: 컨테이너 메트릭 수집
- [ ] PostgreSQL Exporter: DB 메트릭 수집
- [ ] Redis Exporter: Redis 메트릭 수집

---

## 7. 알림 테스트 시나리오

### 7.1 서비스 다운 알림
```bash
# API Gateway 중지
docker compose stop api-gateway

# 1분 후 Alert 발생 예상
# Slack으로 알림 전송 확인

# 복구
docker compose start api-gateway
```

### 7.2 높은 CPU 사용률 알림
```bash
# CPU 부하 테스트
docker run --rm --name stress -d progrium/stress --cpu 2 --timeout 300s

# 10분 후 Alert 발생 예상
# Slack으로 알림 전송 확인
```

### 7.3 디스크 공간 부족 알림
```bash
# 디스크 공간 채우기 테스트 (주의!)
# 실제 환경에서는 테스트하지 않을 것을 권장
```

---

## 8. 트러블슈팅

### 8.1 Prometheus가 메트릭을 수집하지 않음
**증상**: Targets 페이지에서 "DOWN" 상태
**원인**: 네트워크 연결 문제 또는 Exporter 다운
**해결**:
```bash
# 네트워크 확인
docker network inspect ralph-network

# Exporter 로그 확인
docker logs node-exporter
docker logs postgres-exporter

# 직접 접속 테스트
docker exec prometheus wget -O- http://node-exporter:9100/metrics
```

### 8.2 Grafana에서 데이터가 표시되지 않음
**증상**: Dashboard Panel이 "No Data"
**원인**: Data Source 연결 문제 또는 쿼리 오류
**해결**:
1. Configuration → Data Sources → Prometheus
2. "Test" 버튼 클릭
3. 쿼리 직접 실행: `up{job="api-gateway"}`

### 8.3 Alert가 Slack으로 전송되지 않음
**증상**: Alert는 발생하지만 Slack 알림 없음
**원인**: Webhook URL 오류 또는 Slack 설정 문제
**해결**:
```bash
# AlertManager 로그 확인
docker logs alertmanager

# Webhook 테스트
curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"Test message"}'

# AlertManager 설정 재로드
docker exec alertmanager kill -HUP 1
```

---

## 9. 운영 가이드

### 9.1 모니터링 확인 (일일)
- [ ] Grafana Dashboard 확인
- [ ] Alert 발생 여부 확인
- [ ] 디스크 용량 확인 (Prometheus, Elasticsearch)
- [ ] Exporter 상태 확인

### 9.2 주간 작업
- [ ] Alert 규칙 튜닝
- [ ] Dashboard 개선
- [ ] 메트릭 보관 기간 확인
- [ ] 알림 설정 검토

### 9.3 월간 작업
- [ ] Prometheus 데이터 보관 정책 검토
- [ ] Grafana Dashboard 백업
- [ ] Alert 규칙 전체 검토
- [ ] Exporter 버전 업데이트

---

## 10. 다음 단계 (Phase 2)

Phase 1 완료 후:
1. **ELK Stack** 구축 (로그 집계)
2. **고급 Dashboard** (비즈니스 메트릭)
3. **Jaeger** (분산 추적 - 선택사항)
4. **PagerDuty** 연동 (선택사항)

---

## 11. 완료 기준

Phase 1 완료 기준:
- ✅ Prometheus가 11개 서비스 메트릭 수집
- ✅ Grafana Dashboard 5개 이상 생성
- ✅ Alert 규칙 10개 이상 작성
- ✅ Slack 알림 동작 확인
- ✅ Exporter 4개 배포 완료
- ✅ Health Check 전체 동작

---

*이 계획서는 DevOps Architect에 의해 작성되었습니다.*
