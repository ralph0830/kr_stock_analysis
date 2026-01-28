"""
Chatbot Service Unit Tests
챗봇 서비스의 기본 기능을 테스트합니다.
"""

import pytest
from pydantic import ValidationError


# ============================================================================
# Test Data
# ============================================================================

VALID_CHAT_REQUEST = {
    "message": "삼성전자 추천해줘",
    "session_id": "test-session-123",
}

VALID_CHAT_REQUEST_NO_SESSION = {
    "message": "오늘의 추천종목은?",
}

MINIMAL_CHAT_RESPONSE = {
    "reply": "네, 말씀하세요.",
    "suggestions": [],
}

HEALTH_CHECK_RESPONSE = {
    "status": "healthy",
    "service": "chatbot",
    "version": "1.0.0",
}


# ============================================================================
# Schema Tests (RED Phase)
# ============================================================================

class TestChatbotSchemas:
    """챗봇 스키마 모델 테스트"""

    def test_import_schemas(self):
        """스키마 모듈 import 테스트"""
        from services.chatbot.schemas import (
            ChatRequest,
            ChatResponse,
            HealthCheckResponse,
        )
        assert ChatRequest is not None
        assert ChatResponse is not None
        assert HealthCheckResponse is not None

    def test_chat_request_valid(self):
        """유효한 ChatRequest 모델 생성"""
        from services.chatbot.schemas import ChatRequest

        req = ChatRequest(**VALID_CHAT_REQUEST)
        assert req.message == "삼성전자 추천해줘"
        assert req.session_id == "test-session-123"

    def test_chat_request_without_session(self):
        """session_id 없는 ChatRequest 모델 생성"""
        from services.chatbot.schemas import ChatRequest

        req = ChatRequest(**VALID_CHAT_REQUEST_NO_SESSION)
        assert req.message == "오늘의 추천종목은?"
        # session_id는 자동 생성됨
        assert req.session_id is not None
        assert len(req.session_id) > 0

    def test_chat_request_empty_message_raises_error(self):
        """빈 메시지는 ValidationError 발생"""
        from services.chatbot.schemas import ChatRequest

        with pytest.raises(ValidationError):
            ChatRequest(message="", session_id="test")

    def test_chat_response_valid(self):
        """유효한 ChatResponse 모델 생성"""
        from services.chatbot.schemas import ChatResponse

        resp = ChatResponse(**MINIMAL_CHAT_RESPONSE)
        assert resp.reply == "네, 말씀하세요."
        assert resp.suggestions == []

    def test_chat_response_with_suggestions(self):
        """추천 질문이 포함된 ChatResponse"""
        from services.chatbot.schemas import ChatResponse

        resp = ChatResponse(
            reply="삼성전자를 추천합니다.",
            suggestions=["삼성전자 재무제표", "삼성전자 최신 뉴스"]
        )
        assert len(resp.suggestions) == 2

    def test_health_check_response(self):
        """HealthCheckResponse 모델 생성"""
        from services.chatbot.schemas import HealthCheckResponse

        resp = HealthCheckResponse(**HEALTH_CHECK_RESPONSE)
        assert resp.status == "healthy"
        assert resp.service == "chatbot"
        assert resp.version == "1.0.0"


# ============================================================================
# Main App Tests (GREEN Phase)
# ============================================================================

class TestChatbotMain:
    """챗봇 메인 앱 테스트"""

    def test_import_main(self):
        """메인 모듈 import 테스트"""
        from services.chatbot.main import app
        assert app is not None

    def test_app_title(self):
        """앱 타이틀 확인"""
        from services.chatbot.main import app

        assert app.title == "Chatbot Service"

    def test_app_version(self):
        """앱 버전 확인"""
        from services.chatbot.main import app

        assert app.version == "1.0.0"


# ============================================================================
# Health Check Endpoint Tests
# ============================================================================

class TestHealthCheck:
    """헬스 체크 엔드포인트 테스트"""

    @pytest.fixture
    def test_client(self):
        """테스트용 FastAPI 클라이언트"""
        from fastapi.testclient import TestClient
        from services.chatbot.main import app

        return TestClient(app)

    def test_health_check_returns_200(self, test_client):
        """헬스 체크 200 응답"""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, test_client):
        """헬스 체크 응답 구조 확인"""
        response = test_client.get("/health")

        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data

    def test_health_check_values(self, test_client):
        """헬스 체크 값 확인"""
        response = test_client.get("/health")

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "chatbot"
        assert data["version"] == "1.0.0"


# ============================================================================
# Chat Endpoint Tests
# ============================================================================

class TestChatEndpoint:
    """채팅 엔드포인트 테스트"""

    @pytest.fixture
    def test_client(self):
        """테스트용 FastAPI 클라이언트"""
        from fastapi.testclient import TestClient
        from services.chatbot.main import app

        return TestClient(app)

    def test_chat_endpoint_returns_200(self, test_client):
        """채팅 엔드포인트 200 응답"""
        response = test_client.post("/chat", json=VALID_CHAT_REQUEST)
        assert response.status_code == 200

    def test_chat_response_structure(self, test_client):
        """채팅 응답 구조 확인"""
        response = test_client.post("/chat", json=VALID_CHAT_REQUEST)

        data = response.json()
        assert "reply" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_chat_generates_session_id(self, test_client):
        """session_id가 없으면 자동 생성"""
        response = test_client.post("/chat", json=VALID_CHAT_REQUEST_NO_SESSION)

        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_chat_preserves_session_id(self, test_client):
        """기존 session_id 유지"""
        response = test_client.post("/chat", json=VALID_CHAT_REQUEST)

        data = response.json()
        assert data["session_id"] == VALID_CHAT_REQUEST["session_id"]

    def test_chat_empty_message_raises_error(self, test_client):
        """빈 메시지는 422 에러"""
        response = test_client.post(
            "/chat",
            json={"message": "", "session_id": "test"}
        )
        assert response.status_code == 422


# ============================================================================
# Context Endpoint Tests
# ============================================================================

class TestContextEndpoint:
    """컨텍스트 엔드포인트 테스트"""

    @pytest.fixture
    def test_client(self):
        """테스트용 FastAPI 클라이언트"""
        from fastapi.testclient import TestClient
        from services.chatbot.main import app

        return TestClient(app)

    def test_context_returns_200(self, test_client):
        """컨텍스트 엔드포인트 200 응답"""
        response = test_client.get("/context?session_id=test-session")
        assert response.status_code == 200

    def test_context_response_structure(self, test_client):
        """컨텍스트 응답 구조 확인"""
        response = test_client.get("/context?session_id=test-session")

        data = response.json()
        assert "session_id" in data
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_context_empty_history(self, test_client):
        """새 세션은 빈 히스토리"""
        response = test_client.get("/context?session_id=new-session")

        data = response.json()
        assert len(data["history"]) == 0
