# PART 06-2: Chatbot Service (챗봇 서비스)

> **상태**: ✅ 완료 (P1-7 Phase)
> **서비스 포트**: 5114
> **마이그레이션 완료일**: 2026-01-27

---

## 개요

RAG(Retrieval-Augmented Generation) 기반 AI 주식 분석 챗봇 서비스입니다.

**주요 기능:**
- **RAG 기반 채팅**: 종목/시그널/뉴스/시장 상태 검색 기반 AI 응답
- **세션 관리**: Redis 기반 대화 기록 저장 (24시간 TTL)
- **실시간 데이터**: Kiwoom REST API 연동 실시간 가격 제공
- **종목 추천**: VCP/종가베팅 시그널 기반 추천 시스템
- **Gemini 3.0 Flash**: Google Gemini API 연동

---

## 아키텍처

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Frontend   │────▶│ API Gateway  │────▶│ Chatbot Service │
│  (Next.js)  │     │   (5111)     │     │    (5114)       │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                 │
                           ┌─────────────────────┼─────────────────────┐
                           ▼                     ▼                     ▼
                    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                    │   Gemini    │      │   Redis     │      │   Kiwoom    │
                    │  3.0 Flash  │      │  (Session)  │      │  REST API   │
                    └─────────────┘      └─────────────┘      └─────────────┘
```

---

## 모듈 구조

### 서비스 파일 (`services/chatbot/`)

| 파일 | 라인수 | 설명 |
|------|--------|------|
| `main.py` | 577 | FastAPI 메인 서버, 엔드포인트 정의 |
| `schemas.py` | 124 | Pydantic Request/Response 모델 |
| `session_manager.py` | 346 | Redis 기반 세션 관리 |
| `retriever.py` | 404 | RAG 컨텍스트 검색 엔진 |
| `recommender.py` | 205 | 종목 추천 로직 |
| `llm_client.py` | 185 | Gemini API 클라이언트 |
| `prompts.py` | 245 | 시스템 프롬프트 템플릿 |
| `kiwoom_integration.py` | 242 | Kiwoom REST API 연동 |

---

## API 엔드포인트

### 챗봇 서비스 (5114)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서비스 헬스 체크 |
| POST | `/chat` | 채팅 요청 처리 |
| GET | `/context` | 세션 기반 컨텍스트 조회 |
| POST | `/context` | 질문 기반 컨텍스트 검색 |
| DELETE | `/context/{session_id}` | 세션 삭제 |
| GET | `/session/{session_id}` | 세션 정보 조회 |
| DELETE | `/session/{session_id}` | 세션 삭제 (별칭) |
| GET | `/recommendations` | 종목 추천 조회 |

### API Gateway 프록시 (5111)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/kr/chatbot/chat` | 채팅 프록시 |
| POST | `/api/kr/chatbot/context` | 컨텍스트 프록시 |
| GET | `/api/kr/chatbot/recommendations` | 추천 프록시 |
| GET | `/api/kr/chatbot/session/{id}` | 세션 조회 프록시 |
| DELETE | `/api/kr/chatbot/session/{id}` | 세션 삭제 프록시 |
| GET | `/api/kr/chatbot/health` | 헬스 체크 프록시 |

---

## Request/Response 모델

### ChatRequest
```python
{
    "message": str,           # 사용자 메시지 (필수)
    "session_id": str | None  # 세션 ID (없으면 자동 생성)
}
```

### ChatResponse
```python
{
    "reply": str,             # 봇 응답 메시지
    "suggestions": List[str], # 추천 질문 리스트
    "session_id": str,        # 세션 ID
    "timestamp": str          # 응답 시간
}
```

### ContextResponse
```python
{
    "session_id": str,        # 세션 ID
    "history": List[dict],    # 대화 기록
    "message_count": int      # 메시지 수
}
```

---

## 프론트엔드 통합

### 페이지 (`frontend/app/chatbot/page.tsx`)
- 챗봇 전용 페이지
- 안내 문구 및 예시 질문 표시
- 다크 모드 지원

### 컴포넌트 (`frontend/components/ChatbotWidget.tsx`)
- 채팅 인터페이스 (258줄)
- 실시간 메시지 전송/수신
- 티커 자동 링크 변환 (6자리 숫자)
- 제안 질문 버튼
- 세션 관리 (새 대화 버튼)

### API 클라이언트 (`frontend/lib/api-client.ts`)
```typescript
// 챗봇 API 메서드 (377~414줄)
apiClient.chat({ message, session_id })
apiClient.getContext(session_id)
apiClient.getRecommendations({ strategy, limit })
apiClient.getChatSession(sessionId)
apiClient.deleteChatSession(sessionId)
```

---

## 핵심 기능 상세

### 1. RAG 컨텍스트 검색 (`retriever.py`)
- 종목 정보 검색 (티커/종목명)
- 시그널 데이터 검색 (VCP/종가베팅)
- 뉴스 감성 분석 검색
- 시장 상태 (Market Gate) 조회
- Kiwoom 실시간 가격 연동

### 2. 세션 관리 (`session_manager.py`)
- Redis 기반 대화 기록 저장
- TTL 24시간 자동 만료
- Fallback 모드 (Redis 없음)
- 메시지 수 제한 없음

### 3. 종목 추천 (`recommender.py`)
- 전략: vcp, jongga, both
- 등급별 포지션 사이즈:
  - S 등급: 15%
  - A 등급: 12%
  - B 등급: 10%
  - C 등급: 5%

### 4. LLM 연동 (`llm_client.py`)
- Gemini 3.0 Flash API
- Mock 모드 지원 (API 키 없음)
- 추천 질문 추출 기능

---

## 환경 변수

```bash
# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Redis (세션 저장)
REDIS_URL=redis://localhost:6380/0

# Kiwoom REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
USE_KIWOOM_REST=true
```

---

## 실행 방법

```bash
# 챗봇 서비스 시작
.venv/bin/python -m uvicorn services.chatbot.main:app --host 0.0.0.0 --port 5114 --reload

# API Gateway를 통한 접근
curl -X POST http://localhost:5111/api/kr/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "삼성전자 현재가 알려줘"}'
```
