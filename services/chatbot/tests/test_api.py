"""
Chatbot API 테스트 (TDD RED Phase)

FastAPI 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock


class TestHealthEndpoint:
    """헬스체크 엔드포인트 테스트"""

    def test_health_endpoint(self):
        """/health 엔드포인트 테스트"""
        from services.chatbot.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "chatbot"


class TestChatEndpoint:
    """채팅 엔드포인트 테스트"""

    @patch('services.chatbot.main.get_session_manager')
    @patch('services.chatbot.main.get_retriever')
    @patch('services.chatbot.main.get_llm_client')
    def test_chat_endpoint(self, mock_llm, mock_retriever, mock_session):
        """/chat 엔드포인트 테스트"""
        from services.chatbot.main import app
        from services.chatbot.schemas import ChatResponse
        from services.chatbot.llm_client import LLMResponse

        # Mock 설정
        mock_session_mgr = Mock()
        mock_session_mgr.create_session.return_value = "test-session-123"
        mock_session_mgr.add_message.return_value = None
        mock_session_mgr.get_history_formatted.return_value = []
        mock_session.return_value = mock_session_mgr

        mock_ret = Mock()
        mock_ret.retrieve_context.return_value = {"stocks": [], "signals": [], "news": []}
        mock_ret.enrich_with_kiwoom_data = AsyncMock(return_value={"stocks": []})
        mock_retriever.return_value = mock_ret

        mock_llm_client = Mock()
        mock_llm_client.generate_reply.return_value = LLMResponse(
            reply="테스트 응답입니다.",
            suggestions=["추천 종목", "시장 현황"]
        )
        mock_llm.return_value = mock_llm_client

        client = TestClient(app)
        response = client.post(
            "/chat",
            json={"message": "안녕하세요"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "session_id" in data

    @patch('services.chatbot.main.get_session_manager')
    @patch('services.chatbot.main.get_retriever')
    @patch('services.chatbot.main.get_llm_client')
    def test_chat_with_existing_session(self, mock_llm, mock_retriever, mock_session):
        """기존 세션 ID로 채팅 테스트"""
        from services.chatbot.main import app
        from services.chatbot.llm_client import LLMResponse

        # Mock 설정
        mock_session_mgr = Mock()
        mock_session_mgr.add_message.return_value = None
        mock_session_mgr.get_history_formatted.return_value = [
            {"role": "user", "content": "이전 메시지"}
        ]
        mock_session.return_value = mock_session_mgr

        mock_ret = Mock()
        mock_ret.retrieve_context.return_value = {"stocks": [], "signals": [], "news": []}
        mock_ret.enrich_with_kiwoom_data = AsyncMock(return_value={"stocks": []})
        mock_retriever.return_value = mock_ret

        mock_llm_client = Mock()
        mock_llm_client.generate_reply.return_value = LLMResponse(
            reply="세션 유지 응답",
            suggestions=[]
        )
        mock_llm.return_value = mock_llm_client

        client = TestClient(app)
        response = client.post(
            "/chat",
            json={"message": "추천해줘", "session_id": "existing-session-456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session-456"


class TestContextEndpoint:
    """컨텍스트 엔드포인트 테스트"""

    @patch('services.chatbot.main.get_session_manager')
    def test_get_context(self, mock_session):
        """세션 컨텍스트 조회 테스트"""
        from services.chatbot.main import app

        mock_session_mgr = Mock()
        mock_session_mgr.get_history_formatted.return_value = [
            {"role": "user", "content": "안녕"},
            {"role": "assistant", "content": "안녕하세요!"}
        ]
        mock_session_mgr.get_message_count.return_value = 2
        mock_session.return_value = mock_session_mgr

        client = TestClient(app)
        response = client.get("/context?session_id=test-session")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert data["message_count"] == 2
        assert len(data["history"]) == 2

    @patch('services.chatbot.main.get_session_manager')
    def test_delete_context(self, mock_session):
        """세션 삭제 테스트"""
        from services.chatbot.main import app

        mock_session_mgr = Mock()
        mock_session_mgr.clear_session.return_value = True
        mock_session.return_value = mock_session_mgr

        client = TestClient(app)
        response = client.delete("/context/test-session")

        assert response.status_code == 200
        data = response.json()
        # "삭제되었습니다" 또는 "deleted" 확인 (한글/영문 모두 지원)
        message = data["message"].lower()
        assert "삭제" in message or "deleted" in message

    @patch('services.chatbot.main.get_session_manager')
    def test_delete_context_not_found(self, mock_session):
        """없는 세션 삭제 시 404 반환"""
        from services.chatbot.main import app

        mock_session_mgr = Mock()
        mock_session_mgr.clear_session.return_value = False
        mock_session.return_value = mock_session_mgr

        client = TestClient(app)
        response = client.delete("/context/non-existent-session")

        assert response.status_code == 404


class TestRecommendationsEndpoint:
    """추천 엔드포인트 테스트"""

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations(self, mock_recommender):
        """종목 추천 조회 테스트"""
        from services.chatbot.main import app

        mock_rec = Mock()
        mock_rec.get_top_picks.return_value = [
            {"ticker": "005930", "name": "삼성전자", "signal_type": "vcp", "grade": "A", "score": 85},
            {"ticker": "000660", "name": "SK하이닉스", "signal_type": "vcp", "grade": "B", "score": 72},
        ]
        mock_rec.get_position_size.side_effect = lambda g: 12.0 if g == "A" else 8.0
        mock_recommender.return_value = mock_rec

        client = TestClient(app)
        response = client.get("/recommendations?strategy=vcp&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["ticker"] == "005930"

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_empty(self, mock_recommender):
        """추천 종목 없을 때 빈 리스트 반환"""
        from services.chatbot.main import app

        mock_rec = Mock()
        mock_rec.get_top_picks.return_value = []
        mock_recommender.return_value = mock_rec

        client = TestClient(app)
        response = client.get("/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestSessionEndpoint:
    """세션 엔드포인트 테스트"""

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session(self, mock_session):
        """세션 정보 조회 테스트"""
        from services.chatbot.main import app

        mock_session_mgr = Mock()
        mock_session_mgr.get_session_info.return_value = {
            "created_at": "2026-01-31T10:00:00",
            "last_activity": "2026-01-31T10:05:00",
            "message_count": 3
        }
        mock_session_mgr.get_history_formatted.return_value = [
            {"role": "user", "content": "메시지"}
        ]
        mock_session.return_value = mock_session_mgr

        client = TestClient(app)
        response = client.get("/session/test-session")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert data["message_count"] == 3

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session_not_found(self, mock_session):
        """없는 세션 조회 시 404 반환"""
        from services.chatbot.main import app

        mock_session_mgr = Mock()
        mock_session_mgr.get_session_info.return_value = None
        mock_session.return_value = mock_session_mgr

        client = TestClient(app)
        response = client.get("/session/non-existent")

        assert response.status_code == 404


class TestQueryContextEndpoint:
    """쿼리 기반 컨텍스트 엔드포인트 테스트"""

    @patch('services.chatbot.main.get_retriever')
    def test_query_context(self, mock_retriever):
        """질문에 대한 컨텍스트 조회 테스트"""
        from services.chatbot.main import app

        mock_ret = Mock()
        mock_ret.retrieve_context.return_value = {
            "query": "삼성전자 추천해줘",
            "query_type": "stock",
            "stocks": [{"ticker": "005930", "name": "삼성전자"}],
            "signals": [],
            "news": [],
            "market_status": None,
            "timestamp": "2026-01-31T10:00:00",
        }
        mock_retriever.return_value = mock_ret

        client = TestClient(app)
        response = client.post(
            "/context",
            json={"query": "삼성전자 추천해줘"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "삼성전자 추천해줘"
        assert data["query_type"] == "stock"
        assert len(data["stocks"]) == 1

    def test_query_context_missing_query(self):
        """query 필드 없으면 422 반환"""
        from services.chatbot.main import app

        client = TestClient(app)
        response = client.post("/context", json={})

        assert response.status_code == 422
