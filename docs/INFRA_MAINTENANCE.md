# 인프라 유지보수 가이드

**작성일**: 2026-02-05
**목적**: 서버 안정화 및 자동 관리 설정

---

## 1. 개요

본 문서는 Ralph Stock Analysis 서버의 안정적인 운영을 위한 유지보수 절차와 자동화 설정을 포함합니다.

### 문제 원인 분석

| 문제 | 원인 | 영향 |
|------|------|------|
| 디스크 공간 부족 (94%) | 미사용 Docker 이미지/볼륨/빌드 캐시 축적 | 컨테이너 충돌, 서비스 중단 |
| Docker 로그 무한 증가 | 로그 크기 제한 없음 | 디스크 공간 낭비 |
| 수동 재시작 필요 | 부팅 시 자동 시작 미설정 | 재부팅 후 서비스 다운 |
| 주기적 정리 부재 | 수동 정리만 수행 | 디스크 지속적 사용량 증가 |

---

## 2. Docker 리소스 정리

### 2.1 정리 명령어

```bash
# 전체 미사용 리소스 정리 (약 40-44GB 확보)
docker system prune -a --volumes -f

# 이미지만 정리
docker image prune -a -f

# 빌드 캐시 정리
docker builder prune -a -f
```

### 2.2 정리 전후 비교 (2026-02-05)

| 항목 | 정리 전 | 정리 후 | 변화 |
|------|---------|---------|------|
| 디스크 사용량 | 417GB (94%) | 375GB (85%) | **-42GB** |
| 여유 공간 | 29GB | 70GB | **+41GB** |

### 2.3 삭제된 항목

- **이미지**: 50개 이상 (n8n, mssql, old build images 등)
- **볼륨**: 17개 (미사용 데이터 볼륨)
- **빌드 캐시**: 400개 이상
- **네트워크**: 1개 (old compose network)

---

## 3. Docker Log 제한 설정

### 3.1 설정 파일

`/etc/docker/daemon.json`

```json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    },
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
```

### 3.2 설정 의미

| 옵션 | 값 | 설명 |
|------|-----|------|
| max-size | 10m | 각 로그 파일 최대 10MB |
| max-file | 3 | 최대 3개 파일 보관 (총 30MB/컨테이너) |

### 3.3 적용 방법

```bash
# 설정 변경 후 Docker 재시작
sudo systemctl restart docker
```

---

## 4. 자동 정리 Cron 설정

### 4.1 Cron 파일

`/etc/cron.d/docker-cleanup`

```bash
# Docker 리소스 자동 정리 - 매주 일요일 새벽 2시 실행
# 44GB+ 확보 가능한 미사용 리소스 정리

SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 2 * * 0 root docker system prune -a --volumes -f >> /var/log/docker-cleanup.log 2>&1
```

### 4.2 Cron 확인

```bash
# Cron 작업 확인
sudo cat /etc/cron.d/docker-cleanup

# 정리 로그 확인
sudo cat /var/log/docker-cleanup.log

# Cron 로그 확인
sudo grep CRON /var/log/syslog | grep docker-cleanup
```

### 4.3 스케줄 설명

| 필드 | 값 | 의미 |
|------|-----|------|
| 분 | 0 | 0분 |
| 시 | 2 | 새벽 2시 |
| 일 | * | 매일 |
| 월 | * | 매월 |
| 요일 | 0 | 일요일 (0=일요일, 6=토요일) |

---

## 5. Systemd 서비스 (부팅 시 자동 시작)

### 5.1 서비스 파일

`/etc/systemd/system/ralph-stock.service`

```ini
[Unit]
Description=Ralph Stock Analysis - Docker Compose Services
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ralph/work/python/kr_stock_analysis

# 기존 컨테이너가 없으면 infra 시작, 있으면 건너뜀
ExecStart=-/usr/bin/docker compose -f docker/compose/infra.yml up -d
# app 서비스 시작 (이미 실행 중이면 재시작 안 함)
ExecStart=/usr/bin/docker compose -f docker/compose/docker-compose.dev.yml up -d

# 정지 시에는 모두 내림
ExecStop=/usr/bin/docker compose -f docker/compose/docker-compose.dev.yml down
ExecStop=-/usr/bin/docker compose -f docker/compose/infra.yml down

TimeoutStartSec=300
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5.2 서비스 관리 명령어

```bash
# 서비스 상태 확인
sudo systemctl status ralph-stock.service

# 서비스 수동 시작
sudo systemctl start ralph-stock.service

# 서비스 수동 정지
sudo systemctl stop ralph-stock.service

# 서비스 재시작
sudo systemctl restart ralph-stock.service

# 서비스 로그 확인
sudo journalctl -u ralph-stock.service -f

# 부팅 시 자동 시작 활성화
sudo systemctl enable ralph-stock.service

# 부팅 시 자동 시작 비활성화
sudo systemctl disable ralph-stock.service
```

### 5.3 서비스 상태

| 항목 | 값 |
|------|-----|
| 상태 | enabled (부팅 시 자동 시작) |
| Active | active (exited) |
| 타입 | oneshot (한 번 실행 후 유지) |
| 재시작 | on-failure (실패 시 10초 후 재시작) |

---

## 6. Healthcheck 현황

### 6.1 현재 Healthcheck 상태

| 서비스 | Healthcheck | 상태 |
|--------|-------------|------|
| postgres | ✅ pg_isready | healthy |
| redis | ✅ redis-cli ping | healthy |
| api-gateway | ❌ 없음 | - |
| vcp-scanner | ✅ 있음 | healthy |
| signal-engine | ✅ 있음 | healthy |
| chatbot | ✅ 있음 | healthy |
| daytrading-scanner | ✅ 있음 | healthy |
| celery-worker | ⚠️ 있음 (버그) | unhealthy |
| celery-beat | ⚠️ 있음 (버그) | unhealthy |
| frontend | ❌ 없음 | - |

### 6.2 Celery Healthcheck 버그

```yaml
# 현재 설정 (버그 있음)
test: ["CMD-SHELL", "celery -A tasks.celery_app inspect ping -d celery@$$HOSTNAME"]

# 실제로는 정상 작동 중
$ docker exec compose-celery-worker-1 celery -A tasks.celery_app inspect ping
-> celery@xxx: OK
```

**원인**: `$$HOSTNAME` 변수 확장 문제로 Docker healthcheck가 실패하지만, 실제 서비스는 정상 작동 중.

---

## 7. 정기 점검 체크리스트

### 일간 (매일)

- [ ] 컨테이너 상태 확인: `docker ps`
- [ ] 디스크 사용량 확인: `df -h`
- [ ] 서비스 로그 확인: `docker logs compose-api-gateway-1 --tail 50`

### 주간 (매주)

- [ ] Docker 리소스 사용량 확인: `docker system df`
- [ ] 미사용 이미지 확인: `docker images`
- [ ] 정리 로그 확인: `sudo cat /var/log/docker-cleanup.log`

### 월간 (매월)

- [ ] 전체 디스크 사용량 분석
- [ ] 로그 파일 크기 점검
- [ ] 백업 상태 확인

---

## 8. 문제 해결

### 8.1 디스크 공간 부족 (90% 이상)

```bash
# 응급 조치
docker system prune -a --volumes -f

# 사용량 분석
docker system df
du -sh /var/lib/docker/* | sort -rh
```

### 8.2 컨테이너가 계속 재시작됨

```bash
# 컨테이너 로그 확인
docker logs <container-name> --tail 100

# 상세 정보 확인
docker inspect <container-name>
```

### 8.3 서비스가 자동 시작되지 않음

```bash
# 서비스 상태 확인
sudo systemctl status ralph-stock.service

# 서비스 로그 확인
sudo journalctl -u ralph-stock.service -n 50

# 수동 시작 시도
sudo systemctl start ralph-stock.service
```

### 8.4 Docker 데몬이 시작되지 않음

```bash
# Docker 상태 확인
sudo systemctl status docker

# 설정 파일 검증
sudo docker daemon --debug

# 설정 파일 문법 확인
sudo cat /etc/docker/daemon.json | python3 -m json.tool
```

---

## 9. 연관 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| Docker Compose 설정 | `docker/compose/docker-compose.dev.yml` | 개발 환경 Compose |
| 인프라 Compose | `docker/compose/infra.yml` | PostgreSQL, Redis |
| 환경 변수 | `docker/compose/.env.example` | 환경 변수 예시 |
| API 가이드 | `docs/api/API_GUIDE.md` | API 엔드포인트 |

---

## 10. 변경 이력

| 날짜 | 내용 | 작성자 |
|------|------|--------|
| 2026-02-05 | 초안 작성, Docker 정리 (44GB), Log 제한, Cron, Systemd 설정 | Claude |

---

*마지막 업데이트: 2026-02-05*
