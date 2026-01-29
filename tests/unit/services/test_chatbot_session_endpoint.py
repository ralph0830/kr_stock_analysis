"""
Chatbot Session Endpoint Tests (TDD: RED Phase)
GET /session/{session_id} 엔드포인트 테스트
먼저 실패하는 테스트를 작성하고, 그 후에 구현합니다.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient


# ============================================================================
# Test Data
# ============================================================================

MOCK_SESSION_ID = "test-session-123"

MOCK_SESSION_INFO = {
    "created_at": "2026-01-29T10:00:00",
    "message_count": 3,
    "last_activity": "2026-01-29T10:05:00",
}

MOCK_MESSAGES = [
    {
        "role": "user",
        "content": "삼성전자 추천해줘",
        "timestamp": "2026-01-29T10:01:00",
    },
    {
        "role": "assistant",
        "content": "삼성전자(005930)을 추천합니다...",
        "timestamp": "2026-01-29T10:01:01",
    },
    {
        "role": "user",
        "content": "현재가는?",
        "timestamp": "2026-01-29T10:05:00",
    },
]


# ============================================================================
# GET /session/{session_id} Endpoint Tests (RED Phase)
# ============================================================================

class TestSessionEndpoint:
    """GET /session/{session_id} 엔드포인트 테스트"""

    def test_import_app(self):
        """FastAPI app import 테스트"""
        from services.chatbot.main import app
        assert app is not None

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session_found(self, mock_get_session_manager):
        """세션 조회 성공 테스트"""
        from services.chatbot.main import app

        # Mock session manager - MagicMock 사용
        mock_manager = MagicMock()
        mock_manager.get_session_info.return_value = MOCK_SESSION_INFO
        mock_manager.get_history_formatted.return_value = MOCK_MESSAGES
        mock_get_session_manager.return_value = mock_manager

        client = TestClient(app)
        response = client.get(f"/session/{MOCK_SESSION_ID}")

        # 이 테스트는 현재 실패해야 합니다 (RED Phase)
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == MOCK_SESSION_ID
        assert data["created_at"] == MOCK_SESSION_INFO["created_at"]
        assert data["message_count"] == MOCK_SESSION_INFO["message_count"]
        assert data["messages"] == MOCK_MESSAGES
        mock_manager.get_session_info.assert_called_once_with(MOCK_SESSION_ID)
        mock_manager.get_history_formatted.assert_called_once_with(MOCK_SESSION_ID)

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session_not_found(self, mock_get_session_manager):
        """세션을 찾을 수 없을 때 테스트"""
        from services.chatbot.main import app

        mock_manager = MagicMock()
        mock_manager.get_session_info.return_value = None
        mock_get_session_manager.return_value = mock_manager

        client = TestClient(app)
        response = client.get(f"/session/{MOCK_SESSION_ID}")

        # 404 Not Found
        assert response.status_code == 404
        assert "detail" in response.json()

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session_with_empty_messages(self, mock_get_session_manager):
        """메시지가 없는 세션 조회 테스트"""
        from services.chatbot.main import app

        mock_manager = MagicMock()
        mock_manager.get_session_info.return_value = MOCK_SESSION_INFO
        mock_manager.get_history_formatted.return_value = []
        mock_get_session_manager.return_value = mock_manager

        client = TestClient(app)
        response = client.get(f"/session/{MOCK_SESSION_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["message_count"] == 3  # 메타데이터는 정상

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session_response_structure(self, mock_get_session_manager):
        """응답 구조 검증 테스트"""
        from services.chatbot.main import app

        mock_manager = MagicMock()
        mock_manager.get_session_info.return_value = MOCK_SESSION_INFO
        mock_manager.get_history_formatted.return_value = MOCK_MESSAGES
        mock_get_session_manager.return_value = mock_manager

        client = TestClient(app)
        response = client.get(f"/session/{MOCK_SESSION_ID}")

        assert response.status_code == 200
        data = response.json()

        # 응답 구조 검증
        assert "session_id" in data
        assert "created_at" in data
        assert "updated_at" in data or "last_activity" in data
        assert "message_count" in data
        assert "messages" in data

        # 메시지 구조 검증
        for msg in data["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg

    @patch('services.chatbot.main.get_session_manager')
    def test_get_session_exception_handling(self, mock_get_session_manager):
        """예외 처리 테스트"""
        from services.chatbot.main import app

        mock_manager = MagicMock()
        mock_manager.get_session_info.side_effect = Exception("Redis error")
        mock_get_session_manager.return_value = mock_manager

        client = TestClient(app)
        response = client.get(f"/session/{MOCK_SESSION_ID}")

        # 500 Internal Server Error
        assert response.status_code == 500
        assert "detail" in response.json()
