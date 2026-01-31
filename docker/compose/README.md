# Docker Compose 가이드

Ralph Stock Analysis 시스템의 Docker Compose profiles 기반 실행 가이드입니다.

---

## 빠른 시작

### 1. 개발 환경 시작

```bash
# Makefile 사용 (권장)
make dev

# 또는 직접 docker compose 사용
docker compose --profile dev up -d
```

### 2. 운영 환경 시작

```bash
# Makefile 사용
make prod

# 또는 직접 docker compose 사용
docker compose --profile prod up -d
```

### 3. 서비스 중지

```bash
make stop
# 또는
docker compose down
```

---

## 접속 URL

| 서비스 | URL | 설명 |
|--------|-----|------|
| Frontend | http://localhost:5110 | Next.js 웹 UI |
| API Gateway | http://localhost:5111/docs | FastAPI API 문서 |
| VCP Scanner | http://localhost:5112/docs | VCP 패턴 스캐너 |
| Signal Engine | http://localhost:5113/docs | 시그널 엔진 |
| Chatbot | http://localhost:5114/docs | AI 챗봇 |
| Flower | http://localhost:5555 | Celery 모니터링 |

---

## Makefile 명령어

### Profiles 기반 실행

| 명령어 | 설명 |
|--------|------|
| `make dev` | 개발 환경 시작 (hot reload) |
| `make prod` | 운영 환경 시작 (optimized) |
| `make stop` | 모든 서비스 중지 |

### Docker 명령어

| 명령어 | 설명 |
|--------|------|
| `make up` | 전체 서비스 시작 (dev profile) |
| `make down` | 전체 서비스 중지 |
| `make up-infra` | 인프라만 시작 (PostgreSQL, Redis) |
| `make restart` | 전체 서비스 재시작 |
| `make status` | 서비스 상태 확인 |
| `make build` | 이미지 재빌드 |
| `make clean` | 전체 삭제 (볼륨 포함) |

### 로그 보기

| 명령어 | 설명 |
|--------|------|
| `make logs` | 전체 로그 보기 |
| `make logs-api` | API Gateway 로그 |
| `make logs-vcp` | VCP Scanner 로그 |
| `make logs-signal` | Signal Engine 로그 |
| `make logs-chatbot` | Chatbot 로그 |
| `make logs-db` | PostgreSQL 로그 |
| `make logs-celery` | Celery 로그 |
| `make logs-frontend` | Frontend 로그 |

### 개발 명령어

| 명령어 | 설명 |
|--------|------|
| `make shell` | API Gateway 컨테이너 bash 접속 |
| `make db-shell` | PostgreSQL 접속 |
| `make redis-shell` | Redis 접속 |
| `make test` | 테스트 실행 |
| `make lint` | 코드 검사 |
| `make format` | 코드 포맷 |

---

## 환경별 차이점

### 개발 환경 (dev)

- **Hot Reload**: 소스 코드 변경 시 자동 재시작
- **Volume Mount**: 소스 코드를 컨테이너에 마운트
- **Debug Mode**: 상세 로그 출력
- **개발용 포트**: 5110-5114, 5555

### 운영 환경 (prod)

- **최적화된 빌드**: production target 사용
- **리소스 제한**: CPU/Memory 제한 설정
- **Health Check**: 엄격한 헬스체크
- **로그 관리**: json-file 드라이버, 로테이션

---

## 환경 변수

환경 변수는 `docker/compose/` 디렉토리에 관리됩니다:

| 파일 | 용도 |
|------|------|
| `.env.example` | 환경 변수 예시/참조 |
| `.env.dev` | 개발용 기본값 |
| `.env.prod.template` | 운영용 템플릿 |

### 개발용 환경 변수 설정

```bash
# .env.local 파일 생성 (gitignored)
cp docker/compose/.env.dev .env.local

# 필요한 경우 API 키 추가
echo "GEMINI_API_KEY=your_key" >> .env.local
```

### 운영용 환경 변수 설정

```bash
# 템플릿 복사
cp docker/compose/.env.prod.template .env.prod

# 값 수정 (에디터로 열어서)
vi .env.prod

# 운영 시작
docker compose --env-file .env.prod --profile prod up -d
```

---

## 문제 해결

### 포트 충돌

이미 사용 중인 포트가 있을 경우:

```bash
# 포트 사용 중인 프로세스 확인
sudo lsof -ti:5111

# 프로세스 종료
sudo kill -9 $(sudo lsof -ti:5111)
```

### 컨테이너 재빌드

캐시 문제로 빌드 실패 시:

```bash
# 빌드 캐시 삭제 후 재빌드
docker compose build --no-cache
```

### 볼륨 초기화

데이터를 완전히 삭제하고 처음부터 다시 시작:

```bash
make clean
make dev
```

### 로그 확인

문제 발생 시 로그 확인:

```bash
# 전체 로그
make logs

# 특정 서비스 로그
make logs-api
make logs-db
```

---

## 파일 구조

```
docker/compose/
├── services/              # 서비스 정의 파일
│   ├── api-gateway.yml
│   ├── vcp-scanner.yml
│   ├── signal-engine.yml
│   ├── chatbot.yml
│   ├── frontend.yml
│   └── celery.yml
├── infra.yml             # 인프라 정의 (postgres, redis)
├── .env.example          # 환경 변수 예시
├── .env.dev              # 개발용 기본값
├── .env.prod.template    # 운영용 템플릿
├── README.md             # 이 파일
└── tests/                # Compose 설정 테스트
```

---

## 추가 도움

- 전체 프로젝트 README: [`../../README.md`](../../README.md)
- API 가이드: [`../../docs/api/API_GUIDE.md`](../../docs/api/API_GUIDE.md)
- 진행 상황: [`../../PROGRESS.md`](../../PROGRESS.md)
