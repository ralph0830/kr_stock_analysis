"""
Request ID Middleware

요청 추적 ID 생성 및 전파
"""
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    요청 ID 미들웨어

    각 요청에 고유 ID를 부여하고 응답 헤더에 포함합니다.

    ## 사용법
    ```python
    app.add_middleware(RequestIDMiddleware)
    ```
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 기존 요청 ID 확인 (헤더에서)
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            # 새 요청 ID 생성
            request_id = str(uuid.uuid4())

        # 요청 상태에 저장
        request.state.request_id = request_id

        # 요청 처리
        response = await call_next(request)

        # 응답 헤더에 요청 ID 추가
        response.headers["X-Request-ID"] = request_id

        return response
