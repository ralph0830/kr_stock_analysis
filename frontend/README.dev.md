# 로컬 개발 환경 설정 (HMR 지원)

Docker 컨테이너 없이 로컬에서 직접 Next.js dev 서버를 실행하여 HMR을 사용합니다.

## 🚀 빠른 시작

```bash
# 1. 의존성 설치
cd frontend
npm install

# 2. .env.local 생성 (백엔드 URL 설정)
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:5111
NEXT_PUBLIC_WS_URL=ws://localhost:5111
EOF

# 3. 개발 서버 시작
npm run dev
```

## 🔧 백엔드 API 연결

백엔드 서비스는 Docker로 실행합니다:

```bash
# 프로젝트 루트에서
docker compose --profile dev up -d postgres redis api-gateway vcp-scanner signal-engine chatbot

# 또는 전체 서비스
docker compose --profile dev up -d
```

## 💻 IDE 설정

### VS Code
1. `frontend` 폴더를 VS Code로 열기
2. 익xtensions: ESLint, Prettier, Tailwind CSS IntelliSense
3. Cmd/Click + 로드: 브레이크포인트 클릭으로 디버깅

### Cursor
1. `docker-compose.yml` 열기
2. Cursor는 자동으로 Docker Compose 서비스를 인식

## 🛠️ 개발 워크플로우

1. **로컬에서 프론트엔드 개발** (`npm run dev`)
2. **코드 수정 시 자동 새로고침 (HMR)**
3. **백엔드는 Docker에서 실행** (`docker compose --profile dev up -d`)

## 📦 전체 빌드 테스트

```bash
# Production 빌드 테스트
cd frontend
npm run build
npm start
```

## 🔍 트러블슈팅

### 문제: `ECONNREFUSED` when calling API
```bash
# 백엔드 서비스가 실행 중인지 확인
curl http://localhost:5111/health
```

### 문제: Port 5110 already in use
```bash
# 이미 실행 중인 프로세스 종료
lsof -ti:5110 | xargs kill -9
```

### 문제: Module not found
```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install
```
