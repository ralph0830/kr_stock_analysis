"""
httpx Circuit Breaker Client Wrapper
httpx 클라이언트용 서킷 브레이커 래퍼
"""

import httpx
from src.utils.circuit_breaker import CircuitBreakerState, CircuitBreakerError, circuit_breaker_registry


class CircuitBreakerClientWrapper:
    """
    서킷 브레이커가 적용된 httpx 클라이언트 래퍼

    Usage:
        wrapper = CircuitBreakerClientWrapper("external_api")
        response = wrapper.get("http://example.com")
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        async_client: bool = False,
    ):
        """
        Args:
            name: 서킷 브레이커 이름
            failure_threshold: 실패 임계값
            recovery_timeout: 복구 대기 시간
            async_client: 비동기 클라이언트 여부
        """
        self._circuit_breaker = circuit_breaker_registry.get_or_create(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=(httpx.HTTPError, OSError),
        )
        self._async_client = async_client

        if async_client:
            self._client = httpx.AsyncClient()
        else:
            self._client = httpx.Client()

    def _check_circuit(self) -> None:
        """서킷 상태 확인"""
        current_state = self._circuit_breaker.state
        if current_state == CircuitBreakerState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN. Last error: {self._circuit_breaker.last_failure_message}"
            )

    def get(self, url: str, **kwargs) -> httpx.Response:
        """GET 요청"""
        self._check_circuit()
        try:
            response = self._client.get(url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except (httpx.HTTPError, OSError) as e:
            self._circuit_breaker.record_failure(str(e))
            raise

    def post(self, url: str, **kwargs) -> httpx.Response:
        """POST 요청"""
        self._check_circuit()
        try:
            response = self._client.post(url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except (httpx.HTTPError, OSError) as e:
            self._circuit_breaker.record_failure(str(e))
            raise

    def put(self, url: str, **kwargs) -> httpx.Response:
        """PUT 요청"""
        self._check_circuit()
        try:
            response = self._client.put(url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except (httpx.HTTPError, OSError) as e:
            self._circuit_breaker.record_failure(str(e))
            raise

    def delete(self, url: str, **kwargs) -> httpx.Response:
        """DELETE 요청"""
        self._check_circuit()
        try:
            response = self._client.delete(url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except (httpx.HTTPError, OSError) as e:
            self._circuit_breaker.record_failure(str(e))
            raise

    async def aget(self, url: str, **kwargs) -> httpx.Response:
        """비동기 GET 요청"""
        self._check_circuit()
        try:
            response = await self._client.get(url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except (httpx.HTTPError, OSError) as e:
            self._circuit_breaker.record_failure(str(e))
            raise

    async def apost(self, url: str, **kwargs) -> httpx.Response:
        """비동기 POST 요청"""
        self._check_circuit()
        try:
            response = await self._client.post(url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except (httpx.HTTPError, OSError) as e:
            self._circuit_breaker.record_failure(str(e))
            raise

    def close(self) -> None:
        """클라이언트 닫기"""
        self._client.close()

    async def aclose(self) -> None:
        """비동기 클라이언트 닫기"""
        await self._client.aclose()


def create_circuit_breaker_client(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    async_client: bool = False,
) -> CircuitBreakerClientWrapper:
    """
    서킷 브레이커가 적용된 httpx 클라이언트 래퍼 생성

    Args:
        name: 서킷 브레이커 이름
        failure_threshold: 실패 임계값
        recovery_timeout: 복구 대기 시간
        async_client: 비동기 클라이언트 여부

    Returns:
        CircuitBreakerClientWrapper

    Usage:
        # 동기 클라이언트
        client = create_circuit_breaker_client("vcp_scanner")
        response = client.get("http://localhost:8001/scan")

        # 비동기 클라이언트
        async_client = create_circuit_breaker_client("vcp_scanner", async_client=True)
        response = await client.aget("http://localhost:8001/scan")
    """
    return CircuitBreakerClientWrapper(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        async_client=async_client,
    )


# 하위 호환성을 위한 별칭
CircuitBreakerTransport = CircuitBreakerClientWrapper
CircuitBreakerAsyncTransport = CircuitBreakerClientWrapper
