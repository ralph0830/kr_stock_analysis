# Chatbot Service 엔드포인트 수정 계획

> **마지막 업데이트**: 2026-01-30
> **상태**: ✅ 완료

---

## 개요

### 문제 설명 (해결 완료)

API Gateway와 Chatbot 서비스 간 엔드포인트 불일치로 503/404 에러가 발생하는 문제를 해결했습니다.

| 문제 | 해결 상태 | 구현 위치 |
|------|----------|----------|
| `/recommendations` | ✅ 완료 | `services/chatbot/main.py:328~389` |
| GET `/session/{id}` | ✅ 완료 | `services/chatbot/main.py:396~446` |
| POST `/context` | ✅ 완료 | `services/chatbot/main.py:200~252` |
| DELETE `/session/{id}` | ✅ 완료 | `services/chatbot/main.py:289~321` |

### 해결 방향

1. ✅ **Chatbot 서비스 엔드포인트 표준화** - 완료
2. ✅ **API Gateway 라우팅 수정** - 완료
3. ✅ **통합 테스트 및 문서화** - 완료

---

## Phase Breakdown

### Phase 1: Chatbot 서비스 누락 엔드포인트 구현 ✅

**구현 완료된 엔드포인트:**
- GET `/recommendations` - 종목 추천 조회 (main.py:328~389)
  - 파라미터: `strategy` (vcp, jongga, both), `limit` (기본 5)
  - 응답: ticker, name, signal_type, grade, score, position_size

- GET `/session/{session_id}` - 세션 정보 조회 (main.py:396~446)
  - 응답: session_id, created_at, updated_at, message_count, messages

### Phase 2: POST `/context` 추가 ✅

**구현 완료:**
- POST `/context` - 질문 기반 컨텍스트 검색 (main.py:200~252)
  - 요청: `{"query": "..."}`
  - 응답: query, query_type, stocks, signals, news, market_status

### Phase 3: DELETE 경로 표준화 ✅

**구현 완료:**
- DELETE `/session/{session_id}` - 세션 삭제 (main.py:289~321)
- DELETE `/context/{session_id}` - 레거시 경로 (별칭)

### Phase 4: API Gateway 라우팅 수정 ✅

**API Gateway 프록시 엔드포인트:**
- POST `/api/kr/chatbot/chat` → Chatbot Service POST `/chat`
- POST `/api/kr/chatbot/context` → Chatbot Service POST `/context`
- GET `/api/kr/chatbot/recommendations` → Chatbot Service GET `/recommendations`
- GET `/api/kr/chatbot/session/{id}` → Chatbot Service GET `/session/{id}`
- DELETE `/api/kr/chatbot/session/{id}` → Chatbot Service DELETE `/session/{id}`

### Phase 5: 통합 테스트 및 문서화 ✅

**문서 업데이트 완료:**
- `docs/legacy/PART_06_02_chatbot_core.md` - 챗봇 서비스 상세 문서
- `docs/plans/PLAN_chatbot_api.md` - API 구현 계획 (완료 상태로 업데이트)
- `docs/api/API_GUIDE.md` - API 가이드 챗봇 섹션 업데이트

---

## Progress Tracking

### Phase Status

| Phase | Status | Completed | Last Updated |
|-------|--------|-----------|--------------|
| Phase 1 | ✅ 완료 | 5/5 tasks | 2026-01-30 |
| Phase 2 | ✅ 완료 | 3/3 tasks | 2026-01-30 |
| Phase 3 | ✅ 완료 | 4/4 tasks | 2026-01-30 |
| Phase 4 | ✅ 완료 | 4/4 tasks | 2026-01-30 |
| Phase 5 | ✅ 완료 | 3/3 tasks | 2026-01-30 |

### Overall Progress

- [x] Phase 1: Chatbot 서비스 누락 엔드포인트 구현
- [x] Phase 2: POST `/context` 추가
- [x] Phase 3: DELETE 경로 표준화
- [x] Phase 4: API Gateway 라우팅 수정
- [x] Phase 5: 통합 테스트 및 문서화

---

## Notes & Learnings

### Date: 2026-01-29
- Initial plan created
- Identified 4 major endpoint inconsistencies
- Frontend types already defined (no changes needed)

### Date: 2026-01-30
- 모든 엔드포인트가 이미 `services/chatbot/main.py`에 구현되어 있음을 확인
- 별도의 수정 작업 없이 문서만 업데이트하여 완료 처리
- 챗봇 서비스는 포트 5114에서 정상 동작 중

---

## Validation Commands

```bash
# Run all chatbot tests
pytest tests/unit/services/test_chatbot*.py -v

# Run integration tests
pytest tests/integration/test_kiwoom_chatbot_integration.py -v

# Check coverage
pytest tests/unit/services/test_chatbot*.py --cov=services/chatbot --cov-report=term-missing

# Start chatbot service for manual testing
.venv/bin/python -m uvicorn services.chatbot.main:app --host 0.0.0.0 --port 5114 --reload

# Test endpoints manually
curl -X GET "http://localhost:5114/health"
curl -X GET "http://localhost:5114/recommendations?strategy=both&limit=5"
curl -X GET "http://localhost:5114/session/test-session-123"
curl -X POST "http://localhost:5111/api/kr/chatbot/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "삼성전자 현재가 알려줘"}'
```

---

## References

- `services/chatbot/main.py` (577줄) - Chatbot FastAPI service
- `services/chatbot/schemas.py` (124줄) - Pydantic 모델
- `services/chatbot/recommender.py` (205줄) - StockRecommender class
- `services/chatbot/session_manager.py` (346줄) - SessionManager class
- `services/chatbot/retriever.py` (404줄) - KnowledgeRetriever class
- `services/api_gateway/routes/chatbot.py` - API Gateway routes
- `frontend/lib/api-client.ts` - Frontend API client
- `frontend/types/index.ts` - TypeScript type definitions
- `frontend/components/ChatbotWidget.tsx` (258줄) - 챗봇 UI 위젯
