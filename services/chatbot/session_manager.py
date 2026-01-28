"""
Chatbot Session Manager
Redis 기반 세션 및 대화 기록 관리
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

# Redis 연결 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

# Redis 키 Prefix
SESSION_PREFIX = "chatbot:session:"
HISTORY_PREFIX = "chatbot:history:"

# 세션 TTL (초) - 24시간
SESSION_TTL = 86400


class SessionManager:
    """
    세션 관리자

    Redis를 사용하여 세션 정보와 대화 기록을 관리합니다.
    """

    def __init__(self):
        """세션 관리자 초기화"""
        self._redis_client = None
        self._use_fallback = False

    def _get_redis_client(self):
        """동기 Redis 클라이언트 가져오기"""
        if self._redis_client is None and not self._use_fallback:
            try:
                import redis
                # URL 파싱하여 redis 클라이언트 생성
                self._redis_client = redis.from_url(
                    REDIS_URL,
                    decode_responses=False,  # 바이트 그대로 처리
                )
                # 연결 확인
                if self._redis_client.ping():
                    logger.info("✅ Redis connected for session manager")
                else:
                    self._use_fallback = True
                    logger.warning("⚠️ Redis ping failed, using fallback")
            except ImportError:
                self._use_fallback = True
                logger.warning("⚠️ redis package not installed, using fallback")
            except Exception as e:
                self._use_fallback = True
                self._redis_client = None
                logger.warning(f"⚠️ Redis connection failed: {e}, using fallback")

        # fallback 사용 시 None 반환
        if self._use_fallback:
            return None
        return self._redis_client

    @property
    def redis_client(self):
        """Redis 클라이언트 프로퍼티 (호환성 유지)"""
        return self._get_redis_client()

    def create_session(self) -> str:
        """
        새 세션 생성

        Returns:
            생성된 세션 ID
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        redis = self.redis_client
        if redis:
            try:
                # 세션 메타데이터 저장
                session_key = f"{SESSION_PREFIX}{session_id}"
                redis.hset(
                    session_key,
                    mapping={
                        "created_at": now,
                        "message_count": "0",
                        "last_activity": now,
                    }
                )
                # TTL 설정
                redis.expire(session_key, SESSION_TTL)

                # 빈 히스토리 리스트 생성
                history_key = f"{HISTORY_PREFIX}{session_id}"
                redis.expire(history_key, SESSION_TTL)

                logger.debug(f"Created session: {session_id}")
                return session_id

            except Exception as e:
                logger.error(f"Failed to create session: {e}")

        # Fallback: 세션 ID만 반환
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        대화 기록에 메시지 추가

        Args:
            session_id: 세션 ID
            role: "user" 또는 "assistant"
            content: 메시지 내용

        Returns:
            성공 여부
        """
        now = datetime.now().isoformat()
        message = {
            "role": role,
            "content": content,
            "timestamp": now,
        }

        redis = self.redis_client
        if redis:
            try:
                # 히스토리에 추가
                history_key = f"{HISTORY_PREFIX}{session_id}"
                redis.lpush(history_key, json.dumps(message, ensure_ascii=False))
                redis.expire(history_key, SESSION_TTL)

                # 세션 메타데이터 업데이트
                session_key = f"{SESSION_PREFIX}{session_id}"
                redis.hincrby(session_key, "message_count", 1)
                redis.hset(session_key, "last_activity", now)
                redis.expire(session_key, SESSION_TTL)

                logger.debug(f"Added message to session {session_id}: {role}")
                return True

            except Exception as e:
                logger.error(f"Failed to add message: {e}")

        return False

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """
        대화 기록 조회

        Args:
            session_id: 세션 ID
            limit: 최대 조회 수

        Returns:
            메시지 리스트 (최신순)
        """
        redis = self.redis_client
        if redis:
            try:
                history_key = f"{HISTORY_PREFIX}{session_id}"

                # 리스트 길이 확인
                length = redis.llen(history_key)
                if length == 0:
                    return []

                # 최근 N개 조회 (lrange는 역순으로 반환됨)
                raw_messages = redis.lrange(history_key, 0, limit - 1)

                # JSON 파싱
                messages = []
                for raw_msg in raw_messages:
                    try:
                        msg = json.loads(raw_msg)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue

                return messages

            except Exception as e:
                logger.error(f"Failed to get history: {e}")

        return []

    def get_history_formatted(self, session_id: str) -> List[Dict]:
        """
        대화 기록을 시간 순서대로 반환 (오래된 순)

        Args:
            session_id: 세션 ID

        Returns:
            시간 순서대로 정렬된 메시지 리스트
        """
        history = self.get_history(session_id)
        # lrange는 최신순으로 반환하므로 뒤집어야 함
        return list(reversed(history))

    def clear_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        redis = self.redis_client
        if redis:
            try:
                session_key = f"{SESSION_PREFIX}{session_id}"
                history_key = f"{HISTORY_PREFIX}{session_id}"

                # 키 삭제
                redis.delete(session_key, history_key)

                logger.debug(f"Cleared session: {session_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to clear session: {e}")

        return False

    def list_sessions(self, limit: int = 100) -> List[str]:
        """
        전체 세션 목록 조회

        Args:
            limit: 최대 조회 수

        Returns:
            세션 ID 리스트
        """
        redis = self.redis_client
        if redis:
            try:
                pattern = f"{SESSION_PREFIX}*"
                keys = []
                for key in redis.scan_iter(match=pattern, count=limit):
                    # 키에서 세션 ID 추출
                    session_id = key.decode().replace(SESSION_PREFIX, "")
                    keys.append(session_id)

                return keys[:limit]

            except Exception as e:
                logger.error(f"Failed to list sessions: {e}")

        return []

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        세션 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 또는 None
        """
        redis = self.redis_client
        if redis:
            try:
                session_key = f"{SESSION_PREFIX}{session_id}"
                data = redis.hgetall(session_key)

                if not data:
                    return None

                # 바이트를 문자열로 변환
                return {
                    "created_at": data.get(b"created_at", b"").decode(),
                    "message_count": int(data.get(b"message_count", b"0").decode()),
                    "last_activity": data.get(b"last_activity", b"").decode(),
                }

            except Exception as e:
                logger.error(f"Failed to get session info: {e}")

        return None

    def update_activity(self, session_id: str) -> bool:
        """
        세션 활동 시간 업데이트

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        redis = self.redis_client
        if redis:
            try:
                session_key = f"{SESSION_PREFIX}{session_id}"
                now = datetime.now().isoformat()
                redis.hset(session_key, "last_activity", now)
                redis.expire(session_key, SESSION_TTL)

                # 히스토리 TTL도 연장
                history_key = f"{HISTORY_PREFIX}{session_id}"
                redis.expire(history_key, SESSION_TTL)

                return True

            except Exception as e:
                logger.error(f"Failed to update activity: {e}")

        return False

    def get_message_count(self, session_id: str) -> int:
        """
        세션 메시지 수 조회

        Args:
            session_id: 세션 ID

        Returns:
            메시지 수
        """
        info = self.get_session_info(session_id)
        if info:
            return info.get("message_count", 0)
        return 0


# 싱글톤 인스턴스
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """세션 관리자 싱글톤 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
