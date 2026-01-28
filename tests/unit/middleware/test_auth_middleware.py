"""
API 인증 및 Rate Limiting 테스트
"""

import time

from src.utils.api_auth import (
    APIKeyManager,
    APIKeyStatus,
    api_key_manager,
    init_default_api_keys,
)
from src.utils.rate_limiter import (
    RateLimiter,
    RateLimiterRegistry,
    RateLimitExceeded,
)


class TestAPIKeyManager:
    """APIKeyManager 테스트"""

    def test_create_key(self):
        """API 키 생성 테스트"""
        manager = APIKeyManager()

        api_key = manager.create_key(
            name="test_user",
            rate_limit=1000,
        )

        assert api_key.startswith("krsk_")
        assert len(api_key) > 10

    def test_verify_valid_key(self):
        """유효한 키 검증 테스트"""
        manager = APIKeyManager()

        api_key = manager.create_key("test_user")
        key_info = manager.verify_key(api_key)

        assert key_info is not None
        assert key_info.name == "test_user"
        assert key_info.status == APIKeyStatus.ACTIVE

    def test_verify_invalid_key(self):
        """유효하지 않은 키 검증 테스트"""
        manager = APIKeyManager()

        key_info = manager.verify_key("invalid_key")
        assert key_info is None

    def test_revoke_key(self):
        """키 폐기 테스트"""
        manager = APIKeyManager()

        api_key = manager.create_key("test_user")
        key_info = manager.verify_key(api_key)
        assert key_info is not None

        # 폐기
        key_id = key_info.key_id
        manager.revoke_key(key_id)

        # 검증 실패
        key_info = manager.verify_key(api_key)
        assert key_info is None

    def test_disable_and_enable_key(self):
        """키 비활성화/활성화 테스트"""
        manager = APIKeyManager()

        api_key = manager.create_key("test_user")
        key_info = manager.verify_key(api_key)
        key_id = key_info.key_id

        # 비활성화
        manager.disable_key(key_id)
        key_info = manager.verify_key(api_key)
        assert key_info is None

        # 활성화
        manager.enable_key(key_id)
        key_info = manager.verify_key(api_key)
        assert key_info is not None

    def test_list_keys(self):
        """키 목록 조회 테스트"""
        manager = APIKeyManager()

        manager.create_key("user1")
        manager.create_key("user2")
        manager.create_key("user3")

        all_keys = manager.list_keys()
        assert len(all_keys) == 3

        active_keys = manager.list_keys(status=APIKeyStatus.ACTIVE)
        assert len(active_keys) == 3

    def test_update_rate_limit(self):
        """Rate Limit 업데이트 테스트"""
        manager = APIKeyManager()

        api_key = manager.create_key("test_user", rate_limit=100)
        key_info = manager.verify_key(api_key)
        key_id = key_info.key_id

        assert key_info.rate_limit == 100

        # 업데이트
        manager.update_rate_limit(key_id, 500)

        key_info = manager.get_key_info(key_id)
        assert key_info.rate_limit == 500

    def test_key_metadata(self):
        """키 메타데이터 테스트"""
        manager = APIKeyManager()

        metadata = {"environment": "production", "team": "data"}
        api_key = manager.create_key("test_user", metadata=metadata)

        key_info = manager.verify_key(api_key)
        assert key_info.metadata == metadata


class TestRateLimiter:
    """RateLimiter 테스트"""

    def test_basic_rate_limiting(self):
        """기본 Rate Limiting 테스트"""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        # 5회 허용
        for _ in range(5):
            assert limiter.is_allowed() is True

        # 6회부터 제한
        assert limiter.is_allowed() is False

    def test_window_expiry(self):
        """윈도우 만료 테스트"""
        limiter = RateLimiter(max_requests=3, window_seconds=1)

        # 3회 사용
        for _ in range(3):
            assert limiter.is_allowed() is True

        # 제한
        assert limiter.is_allowed() is False

        # 1.1초 대기 (윈도우 만료)
        time.sleep(1.1)

        # 다시 허용
        assert limiter.is_allowed() is True

    def test_remaining_requests(self):
        """남은 요청 수 테스트"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        assert limiter.get_remaining_requests() == 10

        # 3회 사용
        for _ in range(3):
            limiter.is_allowed()

        assert limiter.get_remaining_requests() == 7

    def test_reset_time(self):
        """제한 해제 시간 테스트"""
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        # 2회 사용
        limiter.is_allowed()
        limiter.is_allowed()

        reset_time = limiter.get_reset_time()
        now = time.time()

        # 제한 해제 시간이 현재 시간 + 10초보다 크거나 같아야 함
        assert reset_time >= now + 9  # 약간의 오차 허용

    def test_reset(self):
        """리셋 테스트"""
        limiter = RateLimiter(max_requests=3)

        # 3회 사용
        for _ in range(3):
            limiter.is_allowed()

        assert limiter.is_allowed() is False

        # 리셋
        limiter.reset()

        # 다시 허용
        assert limiter.is_allowed() is True


class TestRateLimiterRegistry:
    """RateLimiterRegistry 테스트"""

    def test_multiple_clients(self):
        """여러 클라이언트 테스트"""
        registry = RateLimiterRegistry(default_max_requests=3)

        # 클라이언트 1
        for _ in range(3):
            assert registry.is_allowed("client1") is True
        assert registry.is_allowed("client1") is False

        # 클라이언트 2 (독립적인 제한)
        assert registry.is_allowed("client2") is True

    def test_custom_rate_limit(self):
        """커스텀 Rate Limit 테스트"""
        registry = RateLimiterRegistry(default_max_requests=5)

        # 기본 제한
        for _ in range(5):
            assert registry.is_allowed("client1") is True
        assert registry.is_allowed("client1") is False

        # 커스텀 제한
        for _ in range(10):
            assert registry.is_allowed("client2", max_requests=10) is True

    def test_remaining_requests(self):
        """남은 요청 수 조회 테스트"""
        registry = RateLimiterRegistry(default_max_requests=10)

        registry.is_allowed("client1")
        registry.is_allowed("client1")

        remaining = registry.get_remaining_requests("client1")
        assert remaining == 8

    def test_reset_client(self):
        """클라이언트 리셋 테스트"""
        registry = RateLimiterRegistry(default_max_requests=3)

        for _ in range(3):
            registry.is_allowed("client1")

        assert registry.is_allowed("client1") is False

        # 리셋
        registry.reset("client1")

        assert registry.is_allowed("client1") is True

    def test_reset_all(self):
        """전체 리셋 테스트"""
        registry = RateLimiterRegistry(default_max_requests=2)

        registry.is_allowed("client1")
        registry.is_allowed("client1")
        registry.is_allowed("client2")
        registry.is_allowed("client2")

        assert registry.is_allowed("client1") is False
        assert registry.is_allowed("client2") is False

        # 전체 리셋
        registry.reset_all()

        assert registry.is_allowed("client1") is True
        assert registry.is_allowed("client2") is True


class TestAPIKeyAuthIntegration:
    """API Key 인증 통합 테스트"""

    def test_global_manager(self):
        """전역 관리자 테스트"""
        # 초기화
        test_key = init_default_api_keys()

        # 검증
        key_info = api_key_manager.verify_key(test_key)
        assert key_info is not None
        assert key_info.name == "test_key"


class TestRateLimitExceeded:
    """RateLimitExceeded 예외 테스트"""

    def test_exception_message(self):
        """예외 메시지 테스트"""
        exc = RateLimitExceeded(retry_after=60)
        assert "Rate limit exceeded" in str(exc)
        assert "60.0 seconds" in str(exc)
        assert exc.retry_after == 60
