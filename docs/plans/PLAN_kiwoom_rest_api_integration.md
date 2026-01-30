# 키움 REST API 실시간 데이터 통합 계획

**상태**: 진행 중
**범위**: Large (6 Phases, 15-25 시간)

> **전체 문서**: `docs/archive_originals/PLAN_kiwoom_rest_api_integration.md` (378줄)

---

## 개요

Windows COM 기반 KOA(Kiwoom Open API) → REST API 기반 전환:
- 멀티 OS 지원
- OAuth2 인증
- WebSocket 실시간 시세

---

## Before vs After

```
Before (Windows COM):        After (REST API):
src/koa/                     src/kiwoom/
├── base.py                  ├── base.py
├── windows.py (COM)         ├── rest_api.py (HTTP + OAuth2)
├── mock.py                  ├── websocket.py (WS)
├── service.py               ├── mock.py
└── pipeline.py              ├── service.py
                             └── pipeline.py
```

---

## Phases

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 기반 구조 및 인터페이스 정의 | ⏳ |
| 2 | Kiwoom REST API 클라이언트 (OAuth2) | ⏳ |
| 3 | Kiwoom WebSocket 클라이언트 | ⏳ |
| 4 | KiwoomRealtimeService 구현 | ⏳ |
| 5 | API Gateway 라우팅 통합 | ⏳ |
| 6 | E2E 테스트 및 배포 | ⏳ |

---

## 주요 API

| API | 설명 |
|-----|------|
| `ka10001` | 현재가 조회 |
| `mempurchase` | 시장가 매수 |
| `memsell` | 시장가 매도 |
| REG 전문 | 실시간 시세 등록 |
