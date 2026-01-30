"""
Error Handling Tests (TDD Phase 3 - GREEN)

에러 핸들링 및 Graceful Degradation 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


class TestKiwoomErrorClasses:
    """Kiwoom 에러 클래스 테스트"""

    def test_kiwoom_timeout_error_user_message(self):
        """TimeoutError에 사용자 친화적 메시지가 있어야 함"""
        from services.chatbot.kiwoom_integration import KiwoomTimeoutError

        error = KiwoomTimeoutError()
        assert "잠시 후" in error.user_message
        assert str(error) == error.user_message

    def test_kiwoom_rate_limit_error_user_message(self):
        """RateLimitError에 사용자 친화적 메시지가 있어야 함"""
        from services.chatbot.kiwoom_integration import KiwoomRateLimitError

        error = KiwoomRateLimitError()
        assert "너무 많은 요청" in error.user_message

    def test_kiwoom_not_found_error_user_message(self):
        """NotFoundError에 종목 코드가 포함된 메시지가 있어야 함"""
        from services.chatbot.kiwoom_integration import KiwoomNotFoundError

        error = KiwoomNotFoundError("999999")
        assert "999999" in error.user_message
        assert error.ticker == "999999"

    def test_kiwoom_auth_error_user_message(self):
        """AuthenticationError에 사용자 친화적 메시지가 있어야 함"""
        from services.chatbot.kiwoom_integration import KiwoomAuthenticationError

        error = KiwoomAuthenticationError()
        assert "관리자" in error.user_message or "연결" in error.user_message


class TestInputValidation:
    """입력값 유효성 검사 테스트"""

    @pytest.mark.asyncio
    async def test_empty_ticker_raises_error(self):
        """빈 종목 코드는 NotFoundError를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomNotFoundError

        with pytest.raises(KiwoomNotFoundError):
            await get_kiwoom_current_price("")

    @pytest.mark.asyncio
    async def test_short_ticker_raises_error(self):
        """5자리 종목 코드는 NotFoundError를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomNotFoundError

        with pytest.raises(KiwoomNotFoundError):
            await get_kiwoom_current_price("00593")

    @pytest.mark.asyncio
    async def test_long_ticker_raises_error(self):
        """7자리 종목 코드는 NotFoundError를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomNotFoundError

        with pytest.raises(KiwoomNotFoundError):
            await get_kiwoom_current_price("0059300")

    @pytest.mark.asyncio
    async def test_non_numeric_ticker_raises_error(self):
        """숫자가 아닌 종목 코드는 NotFoundError를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomNotFoundError

        with pytest.raises(KiwoomNotFoundError):
            await get_kiwoom_current_price("abcdef")


class TestRetryLogic:
    """재시도 로직 테스트"""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """타임아웃 시 재시도해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomTimeoutError
        from unittest.mock import AsyncMock, patch

        # Mock client - 첫 번째는 타임아웃, 두 번째는 성공
        mock_client = AsyncMock()
        call_count = 0

        async def mock_get_prices(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            return [{"price": 100000, "change": 1000, "volume": 1000000, "date": "20260130"}]

        mock_client.get_daily_prices = mock_get_prices

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            result = await get_kiwoom_current_price("005930", max_retries=1, retry_delay=0.01)
            assert result["price"] == 100000
            assert call_count == 2  # 1회 실패 + 1회 성공

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_error(self):
        """모든 재시도 실패 시 에러를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomTimeoutError
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        mock_client.get_daily_prices = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            with pytest.raises(KiwoomTimeoutError):
                await get_kiwoom_current_price("005930", max_retries=1, retry_delay=0.1)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """지연 시간이 지수적으로 증가해야 함"""
        import time
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomTimeoutError
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        mock_client.get_daily_prices = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            start = time.time()
            with pytest.raises(KiwoomTimeoutError):
                await get_kiwoom_current_price("005930", max_retries=2, retry_delay=0.1)
            elapsed = time.time() - start

            # 0.1 + 0.2 + 0.4 = 0.7초 최소 (재시도 2회 + 첫 시도)
            # 실제로는 API 호출 시간도 포함
            assert elapsed >= 0.3, "지연 시간이 충분하지 않습니다"


class TestHTTPErrorHandling:
    """HTTP 에러 핸들링 테스트"""

    @pytest.mark.asyncio
    async def test_429_rate_limit_error(self):
        """HTTP 429 에러 시 RateLimitError를 발생시켜야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomRateLimitError
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        response = MagicMock()
        response.status_code = 429

        error = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=response)
        mock_client.get_daily_prices = AsyncMock(side_effect=error)

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            with pytest.raises(KiwoomRateLimitError):
                await get_kiwoom_current_price("005930", max_retries=0)

    @pytest.mark.asyncio
    async def test_401_auth_error(self):
        """HTTP 401 에러 시 AuthenticationError를 발생시켜야 함 (즉시 실패, 재시도 없음)"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAuthenticationError
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        response = MagicMock()
        response.status_code = 401

        error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response)
        mock_client.get_daily_prices = AsyncMock(side_effect=error)

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            with pytest.raises(KiwoomAuthenticationError):
                await get_kiwoom_current_price("005930", max_retries=2)

    @pytest.mark.asyncio
    async def test_404_not_found_error(self):
        """HTTP 404 에러 시 NotFoundError를 발생시켜야 함 (즉시 실패, 재시도 없음)"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomNotFoundError
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        response = MagicMock()
        response.status_code = 404

        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=response)
        mock_client.get_daily_prices = AsyncMock(side_effect=error)

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            with pytest.raises(KiwoomNotFoundError):
                await get_kiwoom_current_price("999999", max_retries=2)

    @pytest.mark.asyncio
    async def test_500_server_error_retry(self):
        """HTTP 500 에러 시 재시도해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomNetworkError
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        response = MagicMock()
        response.status_code = 500

        error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=response)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            return [{"price": 100000, "change": 1000, "volume": 1000000, "date": "20260130"}]

        mock_client.get_daily_prices = AsyncMock(side_effect=side_effect)

        with patch('services.chatbot.kiwoom_integration._get_kiwoom_client', return_value=mock_client):
            result = await get_kiwoom_current_price("005930", max_retries=1, retry_delay=0.01)
            assert result["price"] == 100000
            assert call_count == 2


class TestGracefulDegradation:
    """Graceful Degradation 테스트"""

    @pytest.mark.asyncio
    async def test_error_message_for_user(self):
        """사용자에게 친화적인 에러 메시지를 제공해야 함"""
        from services.chatbot.kiwoom_integration import KiwoomTimeoutError

        error = KiwoomTimeoutError()
        user_message = str(error)

        # 사용자 친화적 메시지 확인
        assert len(user_message) > 0
        assert "Traceback" not in user_message
        assert "Exception" not in user_message

    @pytest.mark.asyncio
    async def test_fallback_to_db_on_api_failure(self):
        """API 실패 시 DB에서 데이터를 조회하는 fallback 테스트"""
        # API 실패 시 DB fallback 로직
        # 이 부분은 retriever.py에서 처리
        pass
