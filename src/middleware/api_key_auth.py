"""
API Key Authentication Middleware

X-API-Key 헤더를 통한 API 인증
"""
import logging
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.database.session import get_db_session
from src.database.models_api_key import APIKey

logger = logging.getLogger(__name__)

# 인증이 필요 없는 경로
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/system/health",
}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 인증 미들웨어

    X-API-Key 헤더를 검증하여 API 접근을 제어합니다.

    ## 사용법
    ```python
    app.add_middleware(
        APIKeyAuthMiddleware,
        excluded_paths={"/health", "/docs"},
    )
    ```
    """

    def __init__(
        self,
        app,
        excluded_paths: Optional[set[str]] = None,
        require_auth: bool = False,  # True면 모든 경로 인증 필요
    ):
        super().__init__(app)
        self._excluded_paths = excluded_paths or PUBLIC_PATHS
        self._require_auth = require_auth

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # 공개 경로는 인증 스킵
        if self._is_public_path(path):
            return await call_next(request)

        # API 키 확인
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            if self._require_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API Key required. Include X-API-Key header.",
                )
            else:
                # 인증이 선택사항인 경우 계속 진행
                return await call_next(request)

        # API 키 검증
        key_validity = await self._validate_api_key(api_key)

        if not key_validity["valid"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=key_validity["error"],
            )

        # 요청 상태에 권한 정보 저장
        request.state.api_key = key_validity["key"]
        request.state.api_scope = key_validity["scope"]

        # 마지막 사용 시간 업데이트 (비동기로 처리하여 지연 방지)
        # await self._update_last_used(api_key)

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """공개 경로 확인"""
        # 정확히 일치하는 경로
        if path in self._excluded_paths:
            return True

        # 접두사로 확인 (예: /docs로 시작하는 모든 경로)
        for public_path in self._excluded_paths:
            if path.startswith(public_path):
                return True

        return False

    async def _validate_api_key(self, api_key: str) -> dict:
        """
        API 키 검증

        Returns:
            {"valid": bool, "key": APIKey, "scope": str, "error": str}
        """
        try:
            db = next(get_db_session())

            try:
                key_obj = db.query(APIKey).filter(
                    APIKey.key == api_key
                ).first()

                if not key_obj:
                    return {
                        "valid": False,
                        "error": "Invalid API Key",
                    }

                if not key_obj.is_valid():
                    return {
                        "valid": False,
                        "error": "API Key is inactive or expired",
                    }

                return {
                    "valid": True,
                    "key": key_obj,
                    "scope": key_obj.scope,
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"API Key validation error: {e}")
            return {
                "valid": False,
                "error": "Authentication failed",
            }

    async def _update_last_used(self, api_key: str) -> None:
        """마지막 사용 시간 업데이트"""
        try:
            db = next(get_db_session())

            try:
                key_obj = db.query(APIKey).filter(
                    APIKey.key == api_key
                ).first()

                if key_obj:
                    key_obj.update_last_used()
                    db.commit()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to update last_used: {e}")


def require_scope(required_scope: str):
    """
    태스크 권한 확인 데코레이터

    ## 사용법
    ```python
    @app.get("/api/admin/settings")
    @require_scope("admin")
    async def admin_settings(request: Request):
        return {"settings": {...}}
    ```
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            user_scope = getattr(request.state, "api_scope", "read")

            # admin은 모든 권한 가짐
            if user_scope == "admin":
                return await func(request, *args, **kwargs)

            # write는 read 권한도 가짐
            if user_scope == "write" and required_scope == "read":
                return await func(request, *args, **kwargs)

            # 권한 부족
            if user_scope != required_scope:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_scope}",
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
