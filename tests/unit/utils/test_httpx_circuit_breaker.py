"""
HTTPX Circuit Breaker Unit Tests
HTTPX 서킷 브레이커 테스트
"""

from unittest.mock import Mock, patch
import httpx


# ============================================================================
# Test Data
# ============================================================================

# Mock responses
SUCCESS_RESPONSE = Mock()
SUCCESS_RESPONSE.status_code = 200
SUCCESS_RESPONSE.json.return_value = {"status": "ok"}

mock_request = Mock(spec=httpx.Request)
mock_response = Mock(spec=httpx.Response)
mock_response.status_code = 503
mock_response.request = mock_request

ERROR_RESPONSE = Mock()
ERROR_RESPONSE.status_code = 503
ERROR_RESPONSE.raise_for_status.side_effect = httpx.HTTPStatusError(
    "Service unavailable",
    request=mock_request,
    response=mock_response
)


# ============================================================================
# CircuitBreakerClientWrapper Tests
# ============================================================================

class TestCircuitBreakerClientWrapper:
    """CircuitBreakerClientWrapper 클래스 테스트"""

    def test_import_circuit_breaker_wrapper(self):
        """CircuitBreakerClientWrapper import 테스트"""
        from src.utils.httpx_circuit_breaker import (
            CircuitBreakerClientWrapper,
            create_circuit_breaker_client,
        )
        assert CircuitBreakerClientWrapper is not None
        assert create_circuit_breaker_client is not None

    def test_circuit_breaker_wrapper_init(self):
        """래퍼 초기화 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper

        wrapper = CircuitBreakerClientWrapper(
            name="test_api",
            failure_threshold=5,
            recovery_timeout=60.0,
            async_client=False,
        )

        assert wrapper._circuit_breaker is not None
        assert wrapper._async_client is False

    def test_circuit_breaker_wrapper_init_async(self):
        """비동기 래퍼 초기화 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper

        wrapper = CircuitBreakerClientWrapper(
            name="test_api_async",
            failure_threshold=3,
            recovery_timeout=30.0,
            async_client=True,
        )

        assert wrapper._circuit_breaker is not None
        assert wrapper._async_client is True

    @patch('src.utils.httpx_circuit_breaker.httpx.Client')
    def test_get_request_success(self, mock_client_class):
        """GET 요청 성공 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper
        from src.utils.circuit_breaker import CircuitBreakerState

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        wrapper = CircuitBreakerClientWrapper(
            name="test_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

        # Mock circuit breaker state to CLOSED
        wrapper._circuit_breaker._state = CircuitBreakerState.CLOSED

        response = wrapper.get("http://example.com")

        assert response == mock_response
        mock_client.get.assert_called_once_with("http://example.com")

    @patch('src.utils.httpx_circuit_breaker.httpx.Client')
    def test_post_request_success(self, mock_client_class):
        """POST 요청 성공 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        wrapper = CircuitBreakerClientWrapper(name="test_api")

        response = wrapper.post("http://example.com", json={"key": "value"})

        assert response == mock_response
        mock_client.post.assert_called_once()

    @patch('src.utils.httpx_circuit_breaker.httpx.Client')
    def test_put_request(self, mock_client_class):
        """PUT 요청 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.put.return_value = mock_response
        mock_client_class.return_value = mock_client

        wrapper = CircuitBreakerClientWrapper(name="test_api")

        response = wrapper.put("http://example.com/update", data={"data": "test"})

        assert response == mock_response

    @patch('src.utils.httpx_circuit_breaker.httpx.Client')
    def test_delete_request(self, mock_client_class):
        """DELETE 요청 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 204
        mock_client.delete.return_value = mock_response
        mock_client_class.return_value = mock_client

        wrapper = CircuitBreakerClientWrapper(name="test_api")

        response = wrapper.delete("http://example.com/resource")

        assert response == mock_response

    def test_close_client(self):
        """클라이언트 닫기 테스트"""
        from src.utils.httpx_circuit_breaker import CircuitBreakerClientWrapper

        mock_client = Mock()
        wrapper = CircuitBreakerClientWrapper(name="test_api")
        wrapper._client = mock_client

        wrapper.close()

        mock_client.close.assert_called_once()


# ============================================================================
# Create Circuit Breaker Client Tests
# ============================================================================

class TestCreateCircuitBreakerClient:
    """create_circuit_breaker_client 함수 테스트"""

    @patch('src.utils.httpx_circuit_breaker.CircuitBreakerClientWrapper')
    def test_create_sync_client(self, mock_wrapper_class):
        """동기 클라이언트 생성 테스트"""
        from src.utils.httpx_circuit_breaker import create_circuit_breaker_client

        mock_instance = Mock()
        mock_wrapper_class.return_value = mock_instance

        client = create_circuit_breaker_client(
            name="test_service",
            failure_threshold=3,
            recovery_timeout=45.0,
            async_client=False,
        )

        mock_wrapper_class.assert_called_once_with(
            name="test_service",
            failure_threshold=3,
            recovery_timeout=45.0,
            async_client=False,
        )
        assert client == mock_instance

    @patch('src.utils.httpx_circuit_breaker.CircuitBreakerClientWrapper')
    def test_create_async_client(self, mock_wrapper_class):
        """비동기 클라이언트 생성 테스트"""
        from src.utils.httpx_circuit_breaker import create_circuit_breaker_client

        mock_instance = Mock()
        mock_wrapper_class.return_value = mock_instance

        client = create_circuit_breaker_client(
            name="async_service",
            async_client=True,
        )

        mock_wrapper_class.assert_called_once_with(
            name="async_service",
            failure_threshold=5,
            recovery_timeout=60.0,
            async_client=True,
        )
        assert client == mock_instance


# ============================================================================
# Circuit Breaker State Tests
# ============================================================================

class TestCircuitBreakerState:
    """서킷 브레이커 상태 관련 테스트"""

    def test_circuit_breaker_states(self):
        """상태 enum 테스트"""
        from src.utils.circuit_breaker import CircuitBreakerState

        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_circuit_breaker_error(self):
        """CircuitBreakerError 예외 테스트"""
        from src.utils.circuit_breaker import CircuitBreakerError

        error = CircuitBreakerError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

class TestBackwardCompatibility:
    """하위 호환성 별칭 테스트"""

    def test_circuit_breaker_transport_alias(self):
        """CircuitBreakerTransport 별칭 테스트"""
        from src.utils.httpx_circuit_breaker import (
            CircuitBreakerClientWrapper,
            CircuitBreakerTransport,
        )

        assert CircuitBreakerTransport == CircuitBreakerClientWrapper

    def test_circuit_breaker_async_transport_alias(self):
        """CircuitBreakerAsyncTransport 별칭 테스트"""
        from src.utils.httpx_circuit_breaker import (
            CircuitBreakerClientWrapper,
            CircuitBreakerAsyncTransport,
        )

        assert CircuitBreakerAsyncTransport == CircuitBreakerClientWrapper
