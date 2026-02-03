# Nginx Proxy Manager 설정 가이드

**버전:** 1.0.0
**최종 수정:** 2026-02-03

---

## 목차

1. [개요](#1-개요)
2. [도메인 구성](#2-도메인-구성)
3. [자동화 스크립트](#3-자동화-스크립트)
4. [수동 설정](#4-수동-설정)
5. [DNS 설정](#5-dns-설정)

---

## 1. 개요

시스템은 Nginx Proxy Manager(NPM)를 통해 역프록시를 제공합니다.

---

## 2. 도메인 구성

| 도메인 | 포트 | 백엔드 | WebSocket |
|--------|------|--------|-----------|
| ralphpark.com | 5111 | API Gateway | ✅ |
| stock.ralphpark.com | 80/443 | API Gateway (5111) | ✅ |

---

## 3. 자동화 스크립트

### 3.1 스크립트 사용

`scripts/setup_npm_proxy.py`를 사용하여 NPM에 프록시 호스트를 자동으로 설정할 수 있습니다:

```bash
# .env.npm 설정 확인
cat .env.npm
# NPM_URL=http://112.219.120.75:81
# NPM_EMAIL=your-email@example.com
# NPM_PASSWORD=your-password

# 스크립트 실행
python scripts/setup_npm_proxy.py
```

### 3.2 스크립트 기능

| 기능 | 설명 |
|------|------|
| NPM API 인증 | 이메일/비밀번호로 로그인 |
| 프록시 호스트 생성/업데이트 | `stock.ralphpark.com` |
| Custom Location 설정 | `/ws` 경로 WebSocket 지원 |
| CORS 헤더 자동 구성 | 필요한 헤더 추가 |

---

## 4. 수동 설정

### 4.1 Proxy Host 추가

1. **Proxy Hosts** → **Add Proxy Host**
2. **Domain Names**: `stock.ralphpark.com`
3. **Scheme**: `http`
4. **Forward Hostname**:
   - Docker: `172.18.0.1` (Docker 게이트웨이)
   - 또는 서버 IP
5. **Forward Port**: `5111`

### 4.2 Custom Location (WebSocket)

**Custom Locations** 탭에서 `/ws` 경로 추가:

```nginx
location /ws {
    proxy_pass http://172.18.0.1:5111;
    proxy_http_version 1.1;

    # WebSocket 업그레이드 헤더
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # 기본 헤더
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 타임아웃 설정
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

### 4.3 WebSocket 지원 체크

- **Enable Websocket Support**: ✅ 체크

---

## 5. DNS 설정

각 도메인에 대한 DNS A 레코드가 필요합니다:

```
ralphpark.com          A → 112.219.120.75
stock.ralphpark.com    A → 112.219.120.75
```

### 5.1 DNS 확인

```bash
# DNS 레코드 확인
dig stock.ralphpark.com A
nslookup stock.ralphpark.com
```

---

## 관련 문서

- [Open Architecture](OPEN_ARCHITECTURE.md) - 전체 아키텍처
- [WebSocket 설정](WEBSOCKET.md) - WebSocket 연결 설정
