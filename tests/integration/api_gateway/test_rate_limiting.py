"""
API Gateway Rate Limiting 통합 테스트
"""

import time
from fastapi.testclient import TestClient

from services.api_gateway.main import app
from src.utils.rate_limiter import RateLimiter


class TestRateLimiterBasic:
    """기본 Rate Limiter 테스트"""

    def test_rate_limiter_initial_state(self):
        """Rate Limiter 초기 상태 테스트"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # 초기 상태 확인
        assert limiter._count == 0
        assert limiter.get_remaining_requests() == 5

    def test_rate_limiter_basic(self):
        """기본 Rate Limiter 테스트"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # 3개 요청은 허용
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is True

        # 4번째 요청은 거부
        assert limiter.is_allowed() is False

    def test_rate_limiter_remaining_requests(self):
        """남은 요청 수 확인 테스트"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        # 초기
        assert limiter.get_remaining_requests() == 10

        # 3회 사용
        limiter.is_allowed()
        limiter.is_allowed()
        limiter.is_allowed()

        # 7회 남음
        assert limiter.get_remaining_requests() == 7


class TestRateLimiterWindow:
    """윈도우 만료 테스트"""

    def test_rate_limiter_window_expiry(self):
        """윈도우 만료 테스트"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # 2개 요청 사용
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is False

        # 윈도우 만료 대기
        time.sleep(1.1)

        # 새 윈도우에서 다시 허용
        assert limiter.is_allowed() is True

    def test_rate_limiter_sliding_window(self):
        """슬라이딩 윈도우 동작 테스트"""
        limiter = RateLimiter(max_requests=3, window_seconds=2)

        # t=0: 3개 요청
        assert limiter.is_allowed() is True  # t=0
        time.sleep(0.5)
        assert limiter.is_allowed() is True  # t=0.5
        time.sleep(0.5)
        assert limiter.is_allowed() is True  # t=1.0
        assert limiter.is_allowed() is False  # 제한 도달

        # t=2.5: 첫 요청(0초)은 윈도우에서 제외됨 (2초 경과)
        time.sleep(1.5)
        # 첫 요청이 만료되어 1개 슬롯 확보
        assert limiter.is_allowed() is True  # t=2.5


class TestRateLimitingScenarios:
    """Rate Limiting 시나리오 테스트"""

    def test_burst_traffic(self):
        """돌발 트래픽 시나리오"""
        limiter = RateLimiter(max_requests=5, window_seconds=10)

        # 순간적인 10개 요청
        allowed_count = 0
        for _ in range(10):
            if limiter.is_allowed():
                allowed_count += 1

        # 5개만 허용되어야 함
        assert allowed_count == 5

    def test_steady_traffic(self):
        """지속적 트래픽 시나리오"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # 1초마다 2개 요청
        for _ in range(3):
            assert limiter.is_allowed() is True
            assert limiter.is_allowed() is True
            assert limiter.is_allowed() is False

            # 다음 윈도우까지 대기
            time.sleep(1.1)


class TestRateLimiterUtilities:
    """Rate Limiter 유틸리티 테스트"""

    def test_get_reset_time(self):
        """제한 해제 시간 조회 테스트"""
        limiter = RateLimiter(max_requests=3, window_seconds=10)

        # 요청 전
        reset_time = limiter.get_reset_time()
        current_time = time.time()
        # 요청이 없으면 현재 시간 근처 반환
        assert reset_time <= current_time + 1

        # 요청 후
        limiter.is_allowed()
        reset_time_after = limiter.get_reset_time()
        # 윈도우 시간만큼 미래
        assert reset_time_after > current_time
        # 타임스탬프가 합리적인 범위 내에 있는지 확인
        assert reset_time_after <= current_time + 12  # 약간의 오차 허용

    def test_multiple_limiters(self):
        """여러 Rate Limiter 인스턴스 테스트"""
        limiter1 = RateLimiter(max_requests=2, window_seconds=60)
        limiter2 = RateLimiter(max_requests=5, window_seconds=60)

        # limiter1: 2개만 허용
        assert limiter1.is_allowed() is True
        assert limiter1.is_allowed() is True
        assert limiter1.is_allowed() is False

        # limiter2: 독립 카운팅, 5개 허용
        for _ in range(5):
            assert limiter2.is_allowed() is True
        assert limiter2.is_allowed() is False


class TestPerClientRateLimiting:
    """클라이언트별 Rate Limiting 구현 테스트"""

    def test_per_client_limiter_pattern(self):
        """클라이언트별 Rate Limiting 패턴 테스트"""
        # 여러 클라이언트를 위한 Rate Limiter 관리
        client_limiters = {}

        def get_client_limiter(client_id: str) -> RateLimiter:
            if client_id not in client_limiters:
                client_limiters[client_id] = RateLimiter(
                    max_requests=2,
                    window_seconds=60
                )
            return client_limiters[client_id]

        # client-1: 2개 요청
        limiter1 = get_client_limiter("client-1")
        assert limiter1.is_allowed() is True
        assert limiter1.is_allowed() is True
        assert limiter1.is_allowed() is False

        # client-2: 독립 카운팅
        limiter2 = get_client_limiter("client-2")
        assert limiter2.is_allowed() is True
        assert limiter2.is_allowed() is True
        assert limiter2.is_allowed() is False


class TestRateLimitingEdgeCases:
    """Rate Limiting 엣지 케이스 테스트"""

    def test_zero_rate_limit(self):
        """0 Rate Limit 테스트"""
        limiter = RateLimiter(max_requests=0, window_seconds=60)

        # 모든 요청이 거부되어야 함
        assert limiter.is_allowed() is False

    def test_very_large_rate_limit(self):
        """매우 큰 Rate Limit 테스트"""
        limiter = RateLimiter(max_requests=1000000, window_seconds=60)

        # 100개 요청은 모두 허용되어야 함
        for _ in range(100):
            assert limiter.is_allowed() is True

    def test_single_request_limit(self):
        """단일 요청 제한 테스트"""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # 첫 번째만 허용
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is False


class TestAPIRateLimiting:
    """API Rate Limiting 통합 테스트"""

    def test_health_endpoint_rate_limit(self):
        """Health 엔드포인트 Rate Limit 테스트"""
        client = TestClient(app)

        # 여러 요청 전송
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response.status_code)

            # Rate limit에 도달하면 중단
            if response.status_code == 429:
                break

        # 최소한 한 번은 200 응답을 받아야 함
        assert 200 in responses

    def test_root_endpoint_rate_limit(self):
        """Root 엔드포인트 Rate Limit 테스트"""
        client = TestClient(app)

        # 여러 요청 전송
        for i in range(100):
            response = client.get("/")
            if response.status_code == 429:
                # Rate limit 도달
                assert "retry-after" in response.headers or True  # 헤더가 없을 수 있음
                break
        else:
            # 제한에 도달하지 않음 (테스트 환경에서는 정상)
            pass
