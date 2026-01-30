# Chatbot API 구현 계획서

> **생성일**: 2026-01-28
> **상태**: Pending Approval
> **추정 시간**: 6시간
> **Scope**: Medium

---

## CRITICAL INSTRUCTIONS

After completing each phase:
1. ✅ Check off completed task checkboxes
2. 🧪 Run all quality gate validation commands
3. ⚠️ Verify ALL quality gate items pass
4. 📅 Update "Last Updated" date
5. 📝 Document learnings in Notes section
6. ➡️ Only then proceed to next phase

⛔ DO NOT skip quality gates or proceed with failing checks

---

## 개요

주식 분석 시스템에 RAG(Retrieval-Augmented Generation) 기반 AI 챗봇 서비스를 추가합니다. 사용자는 자연어로 종목 추천, 시장 분석, 투자 전략 등을 질문할 수 있습니다.

### 목표

1. **FastAPI Chatbot Service** (포트 5114): 독립된 마이크로서비스로 챗봇 로직 구현
2. **RAG 기반 질의응답**: 종목 데이터, 시그널, 뉴스 등 검색해서 답변 생성
3. **종목 추천 로직**: VCP/종가베팅 시그널 기반 자동 종목 추천
4. **대화 기록 저장**: Redis에 세션별 대화 기록 저장
5. **API Gateway 라우팅**: `/api/kr/chatbot` 엔드포인트 통합

---

## 아키텍처

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Client    │─────▶│ API Gateway  │─────▶│ Chatbot Service │
│   (Next.js) │      │  (FastAPI)   │      │   (FastAPI)     │
└─────────────┘      │   Port 5111  │      │   Port 5114     │
                     └──────────────┘      └─────────────────┘
                            │                       │
                            │                       ▼
                            │              ┌─────────────────┐
                            │              │  LLM API         │
                            │              │  (Gemini/GPT)   │
                            ▼              └─────────────────┘
                     ┌──────────────┐              │
                     │  Redis       │◀─────────────┘
                     │  (Sessions)  │
                     └──────────────┘
```

---

## Phase 1: Chatbot Service 기본 구조

### 목표
FastAPI 기반 Chatbot Service를 생성하고 기본 엔드포인트를 구현합니다.

### Test Strategy
- **Unit Tests**: Health check, request/response models
- **Integration Tests**: HTTP endpoint 테스트
- **Coverage Target**: 80%

### Tasks

#### RED (Tests First)
- [ ] `tests/unit/services/test_chatbot.py` 작성
  - [ ] HealthCheckResponse 모델 테스트
  - [ ] ChatRequest/ChatResponse 모델 테스트
  - [ ] Session 관련 모델 테스트

#### GREEN (Implementation)
- [ ] `services/chatbot/main.py` 생성
  - [ ] FastAPI app 구조 (포트 5114)
  - [ ] `GET /health` 엔드포인트
  - [ ] `POST /chat` 엔드포인트 (기본 응답)
  - [ ] `GET /context` 엔드포인트 (빈 응답)
- [ ] `services/chatbot/schemas.py` 생성
  - [ ] `ChatRequest` 모델 (message, session_id)
  - [ ] `ChatResponse` 모델 (reply, suggestions)
  - [ ] `HealthCheckResponse` 모델
- [ ] `services/chatbot/__init__.py` 생성

#### REFACTOR
- [ ] 코드 구조 검토 및 개선
- [ ] 타입 힌트 추가
- [ ] docstring 완성

### Quality Gate
- [ ] `pytest tests/unit/services/test_chatbot.py` 통과
- [ ] `ruff check services/chatbot/` 통과
- [ ] `mypy services/chatbot/` 통과
- [ ] 서비스 시작 확인: `.venv/bin/python -m uvicorn services.chatbot.main:app --port 5114`

### Dependencies
- FastAPI 설치됨 (기존)
- Pydantic 설치됨 (기존)

### Rollback Strategy
```bash
# 서비스 중지
pkill -f "services.chatbot.main"

# 파일 삭제
rm -rf services/chatbot/
rm tests/unit/services/test_chatbot.py
```

---

## Phase 2: 대화 기록 관리 (Redis)

### 목표
Redis에 세션별 대화 기록을 저장하고 관리합니다.

### Test Strategy
- **Unit Tests**: SessionManager 클래스 테스트
- **Integration Tests**: Redis 연동 테스트
- **Coverage Target**: 85%

### Tasks

#### RED (Tests First)
- [ ] `tests/unit/services/test_chatbot_session.py` 작성
  - [ ] 세션 생성 테스트
  - [ ] 메시지 추가 테스트
  - [ ] 세션 조회 테스트
  - [ ] 세션 삭제 테스트
  - [ ] Mock Redis 사용

#### GREEN (Implementation)
- [ ] `services/chatbot/session_manager.py` 생성
  - [ ] `SessionManager` 클래스
  - [ ] `create_session()` - 세션 생성
  - [ ] `add_message()` - 메시지 추가
  - [ ] `get_history()` - 대화 기록 조회
  - [ ] `clear_session()` - 세션 삭제
  - [ ] `list_sessions()` - 전체 세션 목록
- [ ] `services/chatbot/main.py` 업데이트
  - [ ] SessionManager 초기화
  - [ ] `GET /context` 엔드포인트 구현
  - [ ] `DELETE /context/{session_id}` 엔드포인트 추가

#### REFACTOR
- [ ] TTL (Time To Live) 설정 추가 (세션 만료)
- [ ] 에러 처리 개선
- [ ] 로깅 추가

### Quality Gate
- [ ] `pytest tests/unit/services/test_chatbot_session.py` 통과
- [ ] Redis 연결 확인
- [ ] 세션 CRUD 동작 확인

### Dependencies
- Phase 1 완료
- Redis 실행 중 (포트 6380)

### Rollback Strategy
```bash
# Redis에서 챗봇 관련 키 삭제
redis-cli -p 6380 KEYS "chatbot:*" | xargs redis-cli -p 6380 DEL

# 파일 삭제
rm services/chatbot/session_manager.py
```

---

## Phase 3: RAG 기반 질의응답 엔진

### 목표
종목 데이터, 시그널, 뉴스 등을 검색하여 LLM에 컨텍스트를 제공합니다.

### Test Strategy
- **Unit Tests**: Retriever 클래스 테스트 (Mock DB)
- **Integration Tests**: 실제 DB 조회 테스트
- **Coverage Target**: 80%

### Tasks

#### RED (Tests First)
- [ ] `tests/unit/services/test_chatbot_retriever.py` 작성
  - [ ] 종목 검색 테스트
  - [ ] 시그널 검색 테스트
  - [ ] 뉴스 검색 테스트
  - [ ] Mock DB 사용

#### GREEN (Implementation)
- [ ] `services/chatbot/retriever.py` 생성
  - [ ] `KnowledgeRetriever` 클래스
  - [ ] `search_stocks()` - 종목명/티커 검색
  - [ ] `search_signals()` - 활성 시그널 검색
  - [ ] `search_news()` - 뉴스 검색 (AI Analysis)
  - [ ] `get_market_status()` - Market Gate 상태
- [ ] `services/chatbot/prompts.py` 생성
  - [ ] RAG 프롬프트 템플릿
  - [ ] 시스템 프롬프트 정의
- [ ] `services/chatbot/main.py` 업데이트
  - [ ] Retriever 초기화
  - [ ] `POST /chat` 엔드포인트에 RAG 로직 연결

#### REFACTOR
- [ ] 검색 결과 랭킹 알고리즘 추가
- [ ] 캐싱 추가 (자주 묻는 질문)
- [ ] 에러 메시지 개선

### Quality Gate
- [ ] `pytest tests/unit/services/test_chatbot_retriever.py` 통과
- [ ] 종목 검색 동작 확인
- [ ] 시그널 검색 동작 확인
- [ ] 뉴스 검색 동작 확인

### Dependencies
- Phase 2 완료
- Database에 종목/시그널 데이터 존재
- AI Analysis 데이터 존재

### Rollback Strategy
```bash
# 파일 삭제
rm services/chatbot/retriever.py
rm services/chatbot/prompts.py
```

---

## Phase 4: LLM 연동 및 답변 생성

### 목표
Gemini API를 연동하여 RAG 결과 기반 답변을 생성합니다.

### Test Strategy
- **Unit Tests**: LLM 클라이언트 테스트 (Mock API)
- **Integration Tests**: 실제 LLM API 호출 테스트 (선택)
- **Coverage Target**: 75%

### Tasks

#### RED (Tests First)
- [ ] `tests/unit/services/test_chatbot_llm.py` 작성
  - [ ] 답변 생성 테스트 (Mock)
  - [ ] 프롬프트 빌드 테스트
  - [ ] 에러 처리 테스트

#### GREEN (Implementation)
- [ ] `services/chatbot/llm_client.py` 생성
  - [ ] `LLMClient` 클래스
  - [ ] `generate_reply()` - 답변 생성
  - [ ] `build_prompt()` - RAG 컨텍스트 포함 프롬프트 생성
  - [ ] Gemini API 연동
  - [ ] Fallback to mock when API unavailable
- [ ] `services/chatbot/main.py` 업데이트
  - [ ] LLMClient 초기화
  - [ ] `POST /chat` 엔드포인트에 LLM 연결
  - [ ] 추천 질문(suggestions) 추가

#### REFACTOR
- [ ] 스트리밍 응답 지원 (선택)
- [ ] 재시도 로직 추가 (API 실패 시)
- [ ] 속도 최적화

### Quality Gate
- [ ] `pytest tests/unit/services/test_chatbot_llm.py` 통과
- [ ] 답변 생성 동작 확인
- [ ] Gemini API 연동 확인 (또는 Mock 동작)
- [ ] 추천 질문 반환 확인

### Dependencies
- Phase 3 완료
- `GEMINI_API_KEY` 환경 변수 (선택 - 없으면 Mock)

### Rollback Strategy
```bash
# 파일 삭제
rm services/chatbot/llm_client.py
```

---

## Phase 5: 종목 추천 로직

### 목표
VCP/종가베팅 시그널 기반 자동 종목 추천 기능을 구현합니다.

### Test Strategy
- **Unit Tests**: 추천 로직 테스트
- **Integration Tests**: 실제 시그널 기반 추천 테스트
- **Coverage Target**: 80%

### Tasks

#### RED (Tests First)
- [ ] `tests/unit/services/test_chatbot_recommendation.py` 작성
  - [ ] VCP 기반 추천 테스트
  - [ ] 종가베팅 기반 추천 테스트
  - [ ] 필터링 로직 테스트

#### GREEN (Implementation)
- [ ] `services/chatbot/recommender.py` 생성
  - [ ] `StockRecommender` 클래스
  - [ ] `recommend_by_vcp()` - VCP 시그널 기반 추천
  - [ ] `recommend_by_jongga()` - 종가베팅 기반 추천
  - [ ] `get_top_picks()` - 종합 추천
- [ ] `services/chatbot/main.py` 업데이트
  - [ ] 추천 질문 처리 로직 추가
  - [ ] "오늘의 추천종목" 응답

#### REFACTOR
- [ ] 위험도 분류 추가 (보수/공격)
- [ ] 섹터 분산 로직 추가
- [ ] 사용자 프로필 기반 추천 (TODO)

### Quality Gate
- [ ] `pytest tests/unit/services/test_chatbot_recommendation.py` 통과
- [ ] 추천 종목 반환 확인
- [ ] 등급별 필터링 확인

### Dependencies
- Phase 4 완료
- VCP 시그널 데이터 존재
- 종가베팅 시그널 데이터 존재

### Rollback Strategy
```bash
# 파일 삭제
rm services/chatbot/recommender.py
```

---

## Phase 6: API Gateway 라우팅

### 목표
API Gateway에 챗봇 관련 라우트를 추가하고 통합합니다.

### Test Strategy
- **Integration Tests**: API Gateway 엔드포인트 테스트
- **E2E Tests**: 전체 흐름 테스트
- **Coverage Target**: 70%

### Tasks

#### RED (Tests First)
- [ ] `tests/integration/test_chatbot_api.py` 작성
  - [ ] `POST /api/kr/chatbot` 테스트
  - [ ] `GET /api/kr/chatbot/welcome` 테스트
  - [ ] `GET /api/kr/chatbot/memory` 테스트
  - [ ] `POST /api/kr/chatbot/memory` 테스트
  - [ ] `DELETE /api/kr/chatbot/memory` 테스트
  - [ ] `GET /api/kr/chatbot/history` 테스트
  - [ ] `DELETE /api/kr/chatbot/history` 테스트

#### GREEN (Implementation)
- [ ] `services/api_gateway/routes/chatbot.py` 생성
  - [ ] `POST /api/kr/chatbot` - 채팅 요청
  - [ ] `GET /api/kr/chatbot/welcome` - 웰컴 메시지
  - [ ] `GET /api/kr/chatbot/memory` - 세션 메모리 조회
  - [ ] `POST /api/kr/chatbot/memory` - 세션 메모리 저장
  - [ ] `DELETE /api/kr/chatbot/memory` - 세션 메모리 삭제
  - [ ] `GET /api/kr/chatbot/history` - 대화 기록 조회
  - [ ] `DELETE /api/kr/chatbot/history` - 대화 기록 삭제
- [ ] `services/api_gateway/main.py` 업데이트
  - [ ] Chatbot 라우터 등록
  - [ ] OpenAPI 태그 추가
- [ ] `services/api_gateway/service_registry.py` 업데이트
  - [ ] Chatbot 서비스 등록

#### REFACTOR
- [ ] 에러 처리 일관성
- [ ] 응답 포맷 통합
- [ ] CORS 설정 확인

### Quality Gate
- [ ] `pytest tests/integration/test_chatbot_api.py` 통과
- [ ] API Gateway에서 챗봇 엔드포인트 동작 확인
- [ ] Swagger UI에 챗봇 섹션 표시 확인

### Dependencies
- Phase 5 완료
- API Gateway 실행 중
- Chatbot Service 실행 중

### Rollback Strategy
```bash
# 라우터 등록 해제
# services/api_gateway/main.py에서 라우터 등록 코드 삭제
# 파일 삭제
rm services/api_gateway/routes/chatbot.py
```

---

## Phase 7: 프론트엔드 연동 (선택)

### 목표
Next.js 프론트엔드에 챗봇 UI를 추가합니다.

### Test Strategy
- **Component Tests**: 챗봇 컴포넌트 테스트
- **E2E Tests**: 채팅 흐름 테스트
- **Coverage Target**: 70%

### Tasks

#### RED (Tests First)
- [ ] `frontend/components/__tests__/ChatbotWidget.test.tsx` 작성
  - [ ] 렌더링 테스트
  - [ ] 메시지 전송 테스트
  - [ ] 응답 수신 테스트

#### GREEN (Implementation)
- [ ] `frontend/components/ChatbotWidget.tsx` 생성
  - [ ] 채팅 UI
  - [ ] 메시지 입력/전송
  - [ ] 응답 표시
  - [ ] 추천 질문 버튼
- [ ] `frontend/lib/api-client.ts` 업데이트
  - [ ] `chat(message, sessionId)` 메서드
  - [ ] `getChatbotWelcome()` 메서드
  - [ ] `getChatbotMemory()` 메서드
  - [ ] `setChatbotMemory()` 메서드
  - [ ] `deleteChatbotMemory()` 메서드
- [ ] `frontend/app/chatbot/page.tsx` 생성 (선택)
  - [ ] 전체 챗봇 페이지

#### REFACTOR
- [ ] 애니메이션 추가
- [ ] 로딩 상태 개선
- [ ] 반응형 디자인

### Quality Gate
- [ ] 컴포넌트 테스트 통과
- [ ] 채팅 동작 확인
- [ ] 반응형 동작 확인

### Dependencies
- Phase 6 완료
- Frontend 실행 중

### Rollback Strategy
```bash
# 파일 삭제
rm frontend/components/ChatbotWidget.tsx
rm frontend/app/chatbot/page.tsx
# api-client.ts 변경 사항 되돌리기
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Gemini API rate limit | Medium | Medium | Fallback to mock, request queuing |
| Redis connection failure | Low | High | Reconnection logic, error messages |
| LLM hallucination | High | Medium | RAG constraints, disclaimer |
| Session data loss | Low | Low | Redis persistence, backup |
| Frontend integration delay | Low | Low | API-first approach |

---

## API Endpoints Summary

### Chatbot Service (Port 5114)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Chat with bot |
| GET | `/context` | Get session context |
| DELETE | `/context/{session_id}` | Clear session |

### API Gateway (Port 5111)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kr/chatbot/welcome` | Welcome message |
| POST | `/api/kr/chatbot` | Send message |
| GET | `/api/kr/chatbot/memory` | Get session memory |
| POST | `/api/kr/chatbot/memory` | Save session memory |
| DELETE | `/api/kr/chatbot/memory` | Delete session memory |
| GET | `/api/kr/chatbot/history` | Get chat history |
| DELETE | `/api/kr/chatbot/history` | Delete chat history |

---

## Environment Variables

```bash
# Chatbot Service
CHATBOT_PORT=5114
GEMINI_API_KEY=your_gemini_api_key  # Optional (uses mock if not set)

# Redis (기존 사용)
REDIS_URL=redis://localhost:6380/0
```

---

## Progress Tracking

- [ ] Phase 1: Chatbot Service 기본 구조
- [ ] Phase 2: 대화 기록 관리 (Redis)
- [ ] Phase 3: RAG 기반 질의응답 엔진
- [ ] Phase 4: LLM 연동 및 답변 생성
- [ ] Phase 5: 종목 추천 로직
- [ ] Phase 6: API Gateway 라우팅
- [ ] Phase 7: 프론트엔드 연동 (선택)

---

## Notes & Learnings

*Update this section as you progress through each phase.*

---

## Last Updated

2026-01-28
