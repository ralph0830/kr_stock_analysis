"""
API Key 인증 시스템
API 키 생성, 검증, 관리
"""

import secrets
import time
import hashlib
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum


class APIKeyStatus(Enum):
    """API 키 상태"""
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


@dataclass
class APIKey:
    """API 키 정보"""
    key_id: str  # 고유 ID (접두사 + 해시)
    name: str  # API 키 이름 (사용자 식별용)
    key_hash: str  # 키 값의 해시 (실제 키는 저장하지 않음)
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    rate_limit: int = 100  # 시간당 최대 요청 수
    rate_window: int = 3600  # 제한 시간 윈도우 (초)
    metadata: Dict = field(default_factory=dict)


class APIKeyManager:
    """
    API 키 관리자

    Usage:
        manager = APIKeyManager()

        # API 키 생성
        api_key = manager.create_key("user1", rate_limit=1000)

        # API 키 검증
        key_info = manager.verify_key(api_key)
    """

    # 키 접두사
    KEY_PREFIX = "krsk_"

    def __init__(self):
        # key_id -> APIKey 매핑
        self._keys: Dict[str, APIKey] = {}
        # key_hash -> key_id 매핑 (검증용)
        self._key_hash_to_id: Dict[str, str] = {}

    def create_key(
        self,
        name: str,
        rate_limit: int = 100,
        rate_window: int = 3600,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        API 키 생성

        Args:
            name: API 키 이름 (사용자 식별용)
            rate_limit: 시간당 최대 요청 수
            rate_window: 제한 시간 윈도우 (초)
            metadata: 추가 메타데이터

        Returns:
            생성된 API 키 (실제 키 값)
        """
        # 실제 키 값 생성 (32바이트 무작위)
        key_bytes = secrets.token_bytes(32)
        key_value = self.KEY_PREFIX + key_bytes.hex()

        # 키 해시 생성 (SHA-256)
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()

        # 키 ID 생성 (접두사 + 해시 앞부분)
        key_id = self.KEY_PREFIX + key_hash[:16]

        # APIKey 객체 생성
        api_key = APIKey(
            key_id=key_id,
            name=name,
            key_hash=key_hash,
            status=APIKeyStatus.ACTIVE,
            rate_limit=rate_limit,
            rate_window=rate_window,
            metadata=metadata or {},
        )

        # 저장
        self._keys[key_id] = api_key
        self._key_hash_to_id[key_hash] = key_id

        return key_value

    def verify_key(self, key_value: str) -> Optional[APIKey]:
        """
        API 키 검증

        Args:
            key_value: 검증할 API 키 값

        Returns:
            APIKey 객체 (검증 실패 시 None)
        """
        # 접두사 확인
        if not key_value.startswith(self.KEY_PREFIX):
            return None

        # 해시 계산
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()

        # key_id 조회
        key_id = self._key_hash_to_id.get(key_hash)
        if not key_id:
            return None

        # APIKey 조회
        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        # 상태 확인
        if api_key.status != APIKeyStatus.ACTIVE:
            return None

        # 마지막 사용 시간 업데이트
        api_key.last_used = datetime.now(timezone.utc)

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """
        API 키 폐기

        Args:
            key_id: 폐기할 키 ID

        Returns:
            성공 여부
        """
        api_key = self._keys.get(key_id)
        if api_key:
            api_key.status = APIKeyStatus.REVOKED
            return True
        return False

    def disable_key(self, key_id: str) -> bool:
        """
        API 키 비활성화

        Args:
            key_id: 비활성화할 키 ID

        Returns:
            성공 여부
        """
        api_key = self._keys.get(key_id)
        if api_key:
            api_key.status = APIKeyStatus.DISABLED
            return True
        return False

    def enable_key(self, key_id: str) -> bool:
        """
        API 키 활성화

        Args:
            key_id: 활성화할 키 ID

        Returns:
            성공 여부
        """
        api_key = self._keys.get(key_id)
        if api_key:
            api_key.status = APIKeyStatus.ACTIVE
            return True
        return False

    def get_key_info(self, key_id: str) -> Optional[APIKey]:
        """
        API 키 정보 조회

        Args:
            key_id: 조회할 키 ID

        Returns:
            APIKey 객체 (없으면 None)
        """
        return self._keys.get(key_id)

    def list_keys(self, status: Optional[APIKeyStatus] = None) -> List[APIKey]:
        """
        API 키 목록 조회

        Args:
            status: 필터링할 상태 (None이면 전체)

        Returns:
            APIKey 리스트
        """
        keys = list(self._keys.values())
        if status:
            keys = [k for k in keys if k.status == status]
        return keys

    def update_rate_limit(self, key_id: str, rate_limit: int) -> bool:
        """
        Rate Limit 업데이트

        Args:
            key_id: 키 ID
            rate_limit: 새로운 rate limit

        Returns:
            성공 여부
        """
        api_key = self._keys.get(key_id)
        if api_key:
            api_key.rate_limit = rate_limit
            return True
        return False


# 전역 API 키 관리자 인스턴스
api_key_manager = APIKeyManager()


def init_default_api_keys():
    """기본 API 키 초기화 (개발용)"""
    # 개발용 테스트 키 생성
    test_key = api_key_manager.create_key(
        name="test_key",
        rate_limit=1000,
        metadata={"environment": "development"},
    )
    return test_key
