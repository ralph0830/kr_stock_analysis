"""
Chatbot Routes
API Gateway에서 Chatbot 서비스로 라우팅
"""

from fastapi import APIRouter, HTTPException, status
import httpx


router = APIRouter(prefix="/api/kr/chatbot", tags=["chatbot"])

# Chatbot 서비스 URL (직접 연결용)
CHATBOT_SERVICE_URL = "http://localhost:5114"


@router.post(
    "/chat",
    summary="챗봇 대화",
    description="사용자 메시지를 처리하여 AI 응답을 생성합니다. RAG 기반으로 종목/시그널/뉴스 정보를 활용합니다.",
    responses={
        200: {"description": "응답 생성 성공"},
        503: {"description": "챗봇 서비스 unavailable"},
    },
)
async def chat(request: dict):
    """
    챗봇 대화 요청

    ## 설명
    사용자 메시지를 처리하여 AI 응답을 생성합니다.

    ## Request Body
    - **message**: 사용자 메시지
    - **session_id**: 세션 ID (선택, 자동 생성)

    ## Returns
    - **reply**: AI 응답
    - **suggestions**: 후속 질문 제안
    - **session_id**: 세션 ID
    - **timestamp**: 응답 시간

    ## Example
    ```bash
    curl -X POST "http://localhost:5111/api/kr/chatbot/chat" \\
      -H "Content-Type: application/json" \\
      -d '{"message": "삼성전자 현재가 알려줘"}'
    ```
    """
    try:
        # Chatbot 서비스로 프록시
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CHATBOT_SERVICE_URL}/chat",
                json=request,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Chatbot service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot service unavailable: {str(e)}",
        )


@router.post(
    "/context",
    summary="대화 컨텍스트 조회",
    description="사용자 질문에서 추출한 종목, 시그널, 뉴스 등의 컨텍스트를 반환합니다.",
)
async def get_context(request: dict):
    """
    질문에 대한 컨텍스트 조회

    ## 설명
    사용자 질문에서 추출한 종목, 시그널, 뉴스 등의 컨텍스트를 반환합니다.

    ## Request Body
    - **query**: 사용자 질문

    ## Returns
    - **stocks**: 관련 종목 리스트
    - **signals**: 관련 시그널 리스트
    - **news**: 관련 뉴스 리스트
    - **market_status**: 시장 상태
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CHATBOT_SERVICE_URL}/context",
                json=request,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Chatbot service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot service unavailable: {str(e)}",
        )


@router.get(
    "/health",
    summary="챗봇 서비스 헬스 체크",
    description="챗봇 서비스의 가용성을 확인합니다.",
)
async def health_check():
    """
    챗봇 서비스 헬스 체크

    ## Returns
    - **status**: 서비스 상태
    - **service**: 서비스명
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CHATBOT_SERVICE_URL}/health",
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        return {
            "status": "unavailable",
            "service": "chatbot",
            "error": str(e),
        }


@router.get(
    "/recommendations",
    summary="종목 추천 조회",
    description="VCP/종가베팅 시그널 기반 종목 추천을 반환합니다. 등급별 포지션 비중을 제안합니다.",
)
async def get_recommendations(
    strategy: str = "both",
    limit: int = 5,
):
    """
    종목 추천 조회

    ## 설명
    VCP/종가베팅 시그널 기반 종목 추천을 반환합니다.

    ## Parameters
    - **strategy**: 전략 (vcp, jongga, both)
    - **limit**: 최대 추천 수

    ## Returns
    - 추천 종목 리스트 (티커, 이름, 등급, 점수, 포지션 비중)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CHATBOT_SERVICE_URL}/recommendations",
                params={"strategy": strategy, "limit": limit},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Chatbot service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot service unavailable: {str(e)}",
        )


@router.get(
    "/session/{session_id}",
    summary="세션 정보 조회",
    description="특정 세션의 대화 기록을 반환합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "세션을 찾을 수 없음"},
    },
)
async def get_session(session_id: str):
    """
    세션 정보 조회

    ## 설명
    특정 세션의 대화 기록을 반환합니다.

    ## Parameters
    - **session_id**: 세션 ID

    ## Returns
    - **session_id**: 세션 ID
    - **messages**: 대화 기록
    - **created_at**: 생성 시간
    - **updated_at**: 업데이트 시간
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CHATBOT_SERVICE_URL}/session/{session_id}",
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Chatbot service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot service unavailable: {str(e)}",
        )


@router.delete(
    "/session/{session_id}",
    summary="세션 삭제",
    description="특정 세션을 삭제합니다.",
)
async def delete_session(session_id: str):
    """
    세션 삭제

    ## 설명
    특정 세션을 삭제합니다.

    ## Parameters
    - **session_id**: 세션 ID

    ## Returns
    - **message**: 삭제 완료 메시지
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{CHATBOT_SERVICE_URL}/session/{session_id}",
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Chatbot service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot service unavailable: {str(e)}",
        )
