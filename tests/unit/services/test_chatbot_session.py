"""
Chatbot Session Manager Unit Tests
세션 관리 기능을 테스트합니다.
"""

from unittest.mock import patch, MagicMock
import json


# ============================================================================
# Test Data
# ============================================================================

TEST_SESSION_ID = "test-session-123"
TEST_USER_MESSAGE = {"role": "user", "content": "삼성전자 추천해줘", "timestamp": "2026-01-28T10:00:00"}
TEST_ASSISTANT_MESSAGE = {"role": "assistant", "content": "삼성전자를 추천합니다.", "timestamp": "2026-01-28T10:00:01"}


# ============================================================================
# SessionManager Tests (RED Phase)
# ============================================================================

class TestSessionManager:
    """SessionManager 클래스 테스트"""

    def test_import_session_manager(self):
        """SessionManager import 테스트"""
        from services.chatbot.session_manager import SessionManager
        assert SessionManager is not None

    @patch('builtins.__import__')
    def test_init_session_manager_with_redis(self, mock_import):
        """SessionManager 초기화 테스트 (Redis 있음)"""
        from services.chatbot.session_manager import SessionManager

        # Redis 모의 설정
        mock_redis_module = MagicMock()
        mock_import.return_value = mock_redis_module

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_module.from_url.return_value = mock_redis_client

        manager = SessionManager()
        client = manager._get_redis_client()

        assert client is not None

    def test_init_session_manager_redis_unavailable(self):
        """SessionManager 초기화 테스트 (Redis 없음)"""
        from services.chatbot.session_manager import SessionManager

        # Redis import 실패
        with patch('builtins.__import__', side_effect=ImportError("No redis module")):
            manager = SessionManager()
            client = manager._get_redis_client()
            assert client is None

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_create_session(self, mock_get_client):
        """세션 생성 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.hset.return_value = 1
        mock_redis.expire.return_value = True
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        session_id = manager.create_session()

        assert session_id is not None
        assert len(session_id) > 0
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_add_user_message(self, mock_get_client):
        """사용자 메시지 추가 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.hset.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.lpush.return_value = 1
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        result = manager.add_message(TEST_SESSION_ID, "user", "삼성전자 추천해줘")

        assert result is True
        mock_redis.lpush.assert_called()

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_add_assistant_message(self, mock_get_client):
        """어시스턴트 메시지 추가 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.lpush.return_value = 1
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        result = manager.add_message(TEST_SESSION_ID, "assistant", "삼성전자를 추천합니다.")

        assert result is True
        mock_redis.lpush.assert_called()

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_get_history_empty(self, mock_get_client):
        """빈 히스토리 조회 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 0
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        history = manager.get_history(TEST_SESSION_ID)

        assert history == []
        mock_redis.llen.assert_called_once()
        mock_redis.lrange.assert_not_called()  # 길이가 0이면 호출 안 함

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_get_history_with_messages(self, mock_get_client):
        """메시지가 있는 히스토리 조회 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 2
        mock_redis.lrange.return_value = [
            json.dumps(TEST_USER_MESSAGE).encode('utf-8'),
            json.dumps(TEST_ASSISTANT_MESSAGE).encode('utf-8')
        ]
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        history = manager.get_history(TEST_SESSION_ID)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_clear_session(self, mock_get_client):
        """세션 삭제 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        result = manager.clear_session(TEST_SESSION_ID)

        assert result is True
        mock_redis.delete.assert_called()

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_list_sessions(self, mock_get_client):
        """전체 세션 목록 조회 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.scan_iter.return_value = [
            b"chatbot:session:session-1",
            b"chatbot:session:session-2"
        ]
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        sessions = manager.list_sessions()

        assert len(sessions) == 2
        assert "session-1" in sessions
        assert "session-2" in sessions

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_get_session_info(self, mock_get_client):
        """세션 정보 조회 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            b"created_at": b"2026-01-28T10:00:00",
            b"message_count": b"5"
        }
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        info = manager.get_session_info(TEST_SESSION_ID)

        assert info is not None
        assert "created_at" in info
        assert info["message_count"] == 5

    @patch('services.chatbot.session_manager.SessionManager._get_redis_client')
    def test_get_message_count(self, mock_get_client):
        """세션 메시지 수 조회 테스트"""
        from services.chatbot.session_manager import SessionManager

        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            b"created_at": b"2026-01-28T10:00:00",
            b"message_count": b"3",
            b"last_activity": b"2026-01-28T10:05:00",
        }
        mock_get_client.return_value = mock_redis

        manager = SessionManager()
        count = manager.get_message_count(TEST_SESSION_ID)

        assert count == 3

    def test_redis_unavailable_fallback(self):
        """Redis 연결 실패 시 fallback 테스트"""
        from services.chatbot.session_manager import SessionManager

        # Redis import 실패 상황
        with patch.dict('sys.modules', {'redis': None}):
            manager = SessionManager()
            manager._use_fallback = True

            # Redis 연결 실패 시에도 에러가 발생하지 않아야 함
            history = manager.get_history(TEST_SESSION_ID)
            assert history == []  # 빈 결과 반환
