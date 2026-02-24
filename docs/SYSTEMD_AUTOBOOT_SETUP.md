# 서버 재부팅 시 자동 시작 설정 가이드

## 개요

서버 재부팅 시 Docker Compose 서비스가 자동으로 시작되도록 systemd 서비스를 설정하는 방법입니다.

## 문제 해결 내용

### 1. systemd 서비스 등록
- 재부팅 시 `docker compose --profile prod up -d` 자동 실행
- Docker 서비스 의존성 설정
- 자동 재시작 정책

### 2. NPM 네트워크 연결
- Nginx Proxy Manager 컨테이너를 `ralph-network`에 연결
- Docker Compose 서비스와 NPM 간 통신 가능

## 파일 구조

```
systemd/
└── ralph-stock.service          # systemd 서비스 유닛 파일

scripts/
├── deploy_systemd_service.sh    # 자동 배포 스크립트
├── connect_npm_network.sh       # NPM 네트워크 연결 스크립트
└── verify_deployment.sh         # 배포 검증 스크립트
```

## 배포 절차

### 1단계: systemd 서비스 설치

```bash
# 자동 배포 스크립트 실행 (모든 작업 자동화)
sudo bash scripts/deploy_systemd_service.sh
```

이 스크립트는 다음을 수행합니다:
1. systemd 서비스 파일을 `/etc/systemd/system/`에 복사
2. systemd 데몬 재로드
3. Docker 네트워크 생성/확인
4. NPM 컨테이너를 ralph-network에 연결
5. 서비스 자동 시작 활성화
6. 서비스 시작

### 2단계: 배포 검증

```bash
# 배포 상태 확인
bash scripts/verify_deployment.sh
```

## 수동 설정 (필요시)

### systemd 서비스 수동 설치

```bash
# 1. 서비스 파일 복사
sudo cp systemd/ralph-stock.service /etc/systemd/system/

# 2. systemd 재로드
sudo systemctl daemon-reload

# 3. 자동 시작 활성화
sudo systemctl enable ralph-stock.service

# 4. 서비스 시작
sudo systemctl start ralph-stock.service
```

### NPM 네트워크 수동 연결

```bash
# 자동 스크립트 실행
sudo bash scripts/connect_npm_network.sh

# 또는 수동 연결
sudo docker network connect ralph-network <npm-container-name>
```

## 서비스 관리 명령어

| 명령어 | 설명 |
|--------|------|
| `sudo systemctl status ralph-stock` | 서비스 상태 확인 |
| `sudo systemctl start ralph-stock` | 서비스 시작 |
| `sudo systemctl stop ralph-stock` | 서비스 중지 |
| `sudo systemctl restart ralph-stock` | 서비스 재시작 |
| `sudo systemctl disable ralph-stock` | 자동 시작 비활성화 |
| `sudo journalctl -u ralph-stock -f` | 실시간 로그 보기 |
| `docker compose --profile prod logs -f` | Docker Compose 로그 보기 |

## 서비스 파일 상세

`systemd/ralph-stock.service` 주요 설정:

```ini
[Unit]
After=docker.service                    # Docker 시작 후 실행
Wants=docker.service                    # Docker 의존성

[Service]
Type=oneshot                            # 한 번만 실행
RemainAfterExit=yes                     # 프로세스 종료 후에도 활성 상태 유지
ExecStart=/usr/bin/docker compose --profile prod up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure                      # 실패 시 재시작

[Install]
WantedBy=multi-user.target             # 멀티유저 모드에서 시작
```

## 문제 해결

### 서비스가 시작되지 않을 때

```bash
# 로그 확인
sudo journalctl -u ralph-stock -n 50

# Docker 상태 확인
sudo systemctl status docker

# 네트워크 확인
docker network ls | grep ralph-network
```

### NPM 연결 문제

```bash
# NPM 컨테이너 이름 찾기
docker ps | grep -i npm

# 네트워크 연결 확인
docker network inspect ralph-network

# 수동 연결
sudo docker network connect ralph-network <npm-container-name>
```

### 502 Bad Gateway

1. 로컬 접속 확인:
   ```bash
   curl http://localhost:5110  # Frontend
   curl http://localhost:5111  # API Gateway
   ```

2. Docker 컨테이너 상태 확인:
   ```bash
   docker ps
   docker compose --profile prod ps
   ```

3. NPM 프록시 설정 확인 (NPM 웹 UI 접속)

## 검증 체크리스트

- [ ] systemd 서비스가 실행 중 (`systemctl status ralph-stock`)
- [ ] Docker 컨테이너가 실행 중 (`docker ps`)
- [ ] 포트 5110, 5111이 listening (`ss -tuln`)
- [ ] NPM이 ralph-network에 연결됨 (`docker network inspect ralph-network`)
- [ ] 로컬 접속 가능 (`curl http://localhost:5110`)
- [ ] 외부 접속 가능 (`curl https://stock.ralphpark.com`)

## 관련 문서

- [DOCKER_COMPOSE.md](./DOCKER_COMPOSE.md) - Docker Compose Profiles 설정
- [NGINX_PROXY_SETUP.md](./NGINX_PROXY_SETUP.md) - Nginx Proxy Manager 설정
