"""
FastAPI 인증 및 Rate Limiting 미들웨어
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Optional

from src.utils.api_auth import api_key_manager, APIKey
from src.utils.rate_limiter import rate_limiter_registry, RateLimitExceeded


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 인증 미들웨어

    Usage:
        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware)
    """

    # 인증이 필요 없는 경로
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # 경로 확인 (인증 제외 경로)
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # API Key 추출
        api_key = self._extract_api_key(request)
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "API Key missing. Provide X-API-Key header."},
            )

        # API Key 검증
        key_info = api_key_manager.verify_key(api_key)
        if not key_info:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API Key."},
            )

        # 요청에 API Key 정보 저장
        request.state.api_key = key_info

        return await call_next(request)

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """요청에서 API Key 추출"""
        # 헤더에서 추출 (X-API-Key)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # 쿼리 파라미터에서 추출 (?api_key=xxx)
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting 미들웨어

    Usage:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)
    """

    # Rate Limiting 제외 경로
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # 경로 확인 (Rate Limiting 제외 경로)
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # 클라이언트 식별자 추출
        client_id = self._get_client_id(request)

        # API Key가 있는 경우 해당 키의 Rate Limit 사용
        key_info = getattr(request.state, "api_key", None)
        if key_info:
            max_requests = key_info.rate_limit
            window_seconds = key_info.rate_window
            client_id = f"key:{key_info.key_id}"  # API Key별 제한
        else:
            # IP별 제한 (기본값)
            max_requests = None  # 레지스트리 기본값 사용
            window_seconds = None

        # Rate Limit 확인
        allowed = rate_limiter_registry.is_allowed(
            client_id,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not allowed:
            # 재시도 가능 시간 계산
            reset_time = rate_limiter_registry.get_reset_time(client_id)
            retry_after = int(reset_time - time.time()) if reset_time else 60

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests or 100),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                },
            )

        # 응답에 Rate Limit 헤더 추가
        response = await call_next(request)
        remaining = rate_limiter_registry.get_remaining_requests(client_id)
        reset_time = rate_limiter_registry.get_reset_time(client_id)

        response.headers["X-RateLimit-Limit"] = str(max_requests or 100)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if reset_time:
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))

        return response

    def _get_client_id(self, request: Request) -> str:
        """클라이언트 식별자 추출 (IP 또는 API Key)"""
        # X-Forwarded-For 헤더 확인 (프록시 환경)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # 직접 연결 IP
        if request.client:
            return request.client.host

        return "unknown"


def require_api_key(request: Request) -> APIKey:
    """
    API Key 필수 의존성 함수

    Usage:
        @app.get("/protected")
        async def protected_endpoint(request: Request, api_key: APIKey = Depends(require_api_key)):
            return {"message": f"Hello, {api_key.name}"}
    """
    api_key = getattr(request.state, "api_key", None)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
        )
    return api_key
