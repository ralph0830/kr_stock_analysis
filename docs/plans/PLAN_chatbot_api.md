# Chatbot API 구현 계획서

**상태**: ✅ 완료 (2026-01-27)
**서비스 포트**: 5114

> **참고**: 상세 구현 내용은 `docs/legacy/PART_06_02_chatbot_core.md` 참고

---

## 개요

RAG(Retrieval-Augmented Generation) 기반 AI 주식 분석 챗봇 서비스

**주요 기능:**
- FastAPI Chatbot Service (포트 5114)
- 종목 데이터, 시그널, 뉴스 검색 기반 답변
- 대화 기록 저장 (Redis, 24시간 TTL)
- Kiwoom REST API 연동 실시간 가격
- Gemini 3.0 Flash LLM 연동

---

## Phases 완료 상태

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | Chatbot Service 기본 구조 | ✅ |
| 2 | 대화 기록 관리 (Redis) | ✅ |
| 3 | RAG 기반 질의응답 엔진 | ✅ |
| 4 | 종목 추천 로직 | ✅ |
| 5 | API Gateway 라우팅 | ✅ |
| 6 | 프론트엔드 UI 통합 | ✅ |

---

## 아키텍처

```
Frontend (Next.js)
      ↓
API Gateway (5111) → Chatbot Service (5114)
                              ↓
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              Gemini   Redis   Kiwoom
              3.0 API  Session  REST API
```

---

## 구현된 엔드포인트

### Chatbot Service (5114)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서비스 헬스 체크 |
| POST | `/chat` | 채팅 요청 처리 |
| GET | `/context` | 세션 기반 컨텍스트 조회 |
| POST | `/context` | 질문 기반 컨텍스트 검색 |
| DELETE | `/context/{session_id}` | 세션 삭제 |
| GET | `/session/{session_id}` | 세션 정보 조회 |
| GET | `/recommendations` | 종목 추천 조회 |

### API Gateway (5111)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/kr/chatbot/chat` | 채팅 프록시 |
| GET | `/api/kr/chatbot/recommendations` | 추천 프록시 |
| GET | `/api/kr/chatbot/session/{id}` | 세션 조회 프록시 |
| DELETE | `/api/kr/chatbot/session/{id}` | 세션 삭제 프록시 |

---

## 핵심 모듈

| 모듈 | 파일 | 기능 |
|------|------|------|
| 메인 서버 | `main.py` (577줄) | FastAPI 엔드포인트 |
| 스키마 | `schemas.py` (124줄) | Pydantic 모델 |
| 세션 관리 | `session_manager.py` (346줄) | Redis 세션 저장 |
| RAG 검색 | `retriever.py` (404줄) | 컨텍스트 검색 |
| 추천 시스템 | `recommender.py` (205줄) | 종목 추천 |
| LLM 클라이언트 | `llm_client.py` (185줄) | Gemini API |
| 프롬프트 | `prompts.py` (245줄) | 시스템 프롬프트 |
| Kiwoom 연동 | `kiwoom_integration.py` (242줄) | 실시간 가격 |

---

## 프론트엔드

| 파일 | 기능 |
|------|------|
| `app/chatbot/page.tsx` | 챗봇 페이지 (73줄) |
| `components/ChatbotWidget.tsx` | 채팅 위젯 (258줄) |
| `lib/api-client.ts` | API 클라이언트 |
| `types/index.ts` | TypeScript 타입 |
