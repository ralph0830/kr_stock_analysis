"""
Chatbot Service - FastAPI Main
RAG 기반 주식 분석 AI 챗봇 서비스
"""

# 환경변수 로드 (가장 먼저 실행)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import logging

# 독립 실행을 위한 유연한 import
import sys
import os

# 현재 파일의 디렉토리를 sys.path에 추가
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

try:
    from chatbot.schemas import (
        ChatRequest,
        ChatResponse,
        ContextResponse,
        HealthCheckResponse,
    )
    from chatbot.session_manager import get_session_manager
    from chatbot.retriever import get_retriever
    from chatbot.prompts import build_rag_prompt
    from chatbot.llm_client import get_llm_client
    from chatbot.recommender import get_recommender
except ImportError:
    from services.chatbot.schemas import (
        ChatRequest,
        ChatResponse,
        ContextResponse,
        HealthCheckResponse,
    )
    from services.chatbot.session_manager import get_session_manager
    from services.chatbot.retriever import get_retriever
    from services.chatbot.prompts import build_rag_prompt
    from services.chatbot.llm_client import get_llm_client
    from services.chatbot.recommender import get_recommender

logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Manager
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("🚀 Chatbot Service Starting...")

    # 필수 API 키 체크
    import os

    gemini_key = os.getenv("GEMINI_API_KEY")
    kiwoom_app_key = os.getenv("KIWOOM_APP_KEY")
    kiwoom_secret_key = os.getenv("KIWOOM_SECRET_KEY")
    use_kiwoom = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"

    # Gemini API는 필수
    if not gemini_key:
        logger.error("❌ GEMINI_API_KEY가 설정되지 않았습니다!")
        logger.error("챗봇 서비스를 사용하려면 Gemini API 키가 필요합니다.")
        logger.error("환경 변수 GEMINI_API_KEY를 설정해주세요.")
    else:
        logger.info("✅ GEMINI_API_KEY configured")

    # Kiwoom API는 실시간 가격 조회를 위해 권장
    if not (kiwoom_app_key and kiwoom_secret_key):
        logger.warning("⚠️ Kiwoom API 키가 설정되지 않았습니다.")
        logger.warning("실시간 가격 정보를 위해 Kiwoom API가 권장됩니다.")
        logger.warning("KIWOOM_APP_KEY, KIWOOM_SECRET_KEY를 설정해주세요.")
    elif not use_kiwoom:
        logger.warning("⚠️ USE_KIWOOM_REST=false로 설정되어 있습니다.")
        logger.warning("실시간 가격 조회를 위해 true로 설정해주세요.")
    else:
        logger.info("✅ Kiwoom REST API configured")

    logger.info("✅ Chatbot Service ready")

    yield

    # Shutdown
    logger.info("🛑 Chatbot Service Shutting down...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Chatbot Service",
    description="RAG-based Stock Analysis Chatbot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================================
# Health Check
# ============================================================================

@app.get(
    "/health",
    tags=["health"],
    response_model=HealthCheckResponse,
    responses={
        200: {
            "description": "서비스 정상",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "chatbot",
                        "version": "1.0.0",
                    }
                }
            }
        }
    },
)
async def health_check():
    """
    챗봇 서비스 헬스 체크

    서비스가 정상 동작 중인지 확인합니다.
    """
    return HealthCheckResponse(
        status="healthy",
        service="chatbot",
        version="1.0.0",
    )


# ============================================================================
# Chat Endpoints
# ============================================================================

@app.post(
    "/chat",
    tags=["chat"],
    response_model=ChatResponse,
    responses={
        200: {
            "description": "채팅 응답 성공",
        },
        422: {
            "description": "요청 데이터 유효성 검사 실패",
        }
    },
)
async def chat(request: ChatRequest):
    """
    채팅 요청 처리

    사용자 메시지를 받고 AI 응답을 반환합니다.

    - **message**: 사용자 메시지 (필수)
    - **session_id**: 세션 ID (없으면 자동 생성)
    """
    try:
        session_manager = get_session_manager()
        retriever = get_retriever()
        llm_client = get_llm_client()

        # session_id가 없으면 생성
        session_id = request.session_id or session_manager.create_session()

        # 사용자 메시지 저장
        session_manager.add_message(session_id, "user", request.message)

        # RAG 컨텍스트 검색
        context = retriever.retrieve_context(request.message)

        # 종목 관련 질문이면 Kiwoom 실시간 현재가 추가
        if context.get("stocks"):
            # 비동기로 Kiwoom 데이터 enrich
            context = await retriever.enrich_with_kiwoom_data(context)

        # 대화 기록 조회
        history = session_manager.get_history_formatted(session_id)

        # LLM 프롬프트 빌드
        prompt = build_rag_prompt(request.message, context, history)

        # LLM 답변 생성 (Phase 4)
        llm_response = llm_client.generate_reply(prompt, history)

        # 어시스턴트 메시지 저장
        session_manager.add_message(session_id, "assistant", llm_response.reply)

        return ChatResponse(
            reply=llm_response.reply,
            suggestions=llm_response.suggestions,
            session_id=session_id,
        )

    except Exception as e:
        logger.error(f"채팅 처리 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )


@app.get(
    "/context",
    tags=["chat"],
    response_model=ContextResponse,
    responses={
        200: {
            "description": "컨텍스트 조회 성공",
        }
    },
)
async def get_context(session_id: str):
    """
    대화 컨텍스트 조회 (세션 기반)

    세션 ID에 해당하는 대화 기록을 반환합니다.

    - **session_id**: 세션 ID
    """
    session_manager = get_session_manager()

    # Redis에서 대화 기록 조회
    history = session_manager.get_history_formatted(session_id)
    message_count = session_manager.get_message_count(session_id)

    return ContextResponse(
        session_id=session_id,
        history=history,
        message_count=message_count,
    )


@app.post(
    "/context",
    tags=["chat"],
    responses={
        200: {
            "description": "질문에 대한 컨텍스트 검색 성공",
        }
    },
)
async def query_context(request: Dict[str, Any]):
    """
    질문에 대한 컨텍스트 조회 (쿼리 기반)

    사용자 질문에서 추출한 종목, 시그널, 뉴스 등의 컨텍스트를 반환합니다.

    - **query**: 사용자 질문
    """
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(
                status_code=422,
                detail="query 필드가 필요합니다."
            )

        retriever = get_retriever()

        # 질문에 대한 컨텍스트 검색
        context = retriever.retrieve_context(query)

        return {
            "query": query,
            "query_type": context.get("query_type", "general"),
            "stocks": context.get("stocks", []),
            "signals": context.get("signals", []),
            "news": context.get("news", []),
            "market_status": context.get("market_status"),
            "timestamp": context.get("timestamp"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"컨텍스트 검색 실패: {e}")
        return {
            "query": request.get("query", ""),
            "query_type": "general",
            "stocks": [],
            "signals": [],
            "news": [],
            "market_status": None,
            "timestamp": None,
        }


@app.delete(
    "/context/{session_id}",
    tags=["chat"],
    responses={
        200: {
            "description": "세션 삭제 성공",
        },
        404: {
            "description": "세션을 찾을 수 없음",
        }
    },
)
async def delete_context(session_id: str):
    """
    대화 컨텍스트 삭제

    세션 ID에 해당하는 대화 기록을 삭제합니다.

    - **session_id**: 세션 ID
    """
    session_manager = get_session_manager()

    # 세션 삭제
    success = session_manager.clear_session(session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )

    return {"message": "세션이 삭제되었습니다", "session_id": session_id}


@app.delete(
    "/session/{session_id}",
    tags=["session"],
    responses={
        200: {
            "description": "세션 삭제 성공",
        },
        404: {
            "description": "세션을 찾을 수 없음",
        }
    },
)
async def delete_session(session_id: str):
    """
    세션 삭제 (표준 경로)

    세션 ID에 해당하는 대화 기록을 삭제합니다.
    `/context/{session_id}`의 별칭이지만, API Gateway와의 호환성을 위해 제공됩니다.

    - **session_id**: 세션 ID
    """
    session_manager = get_session_manager()

    # 세션 삭제
    success = session_manager.clear_session(session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )

    return {"message": "세션이 삭제되었습니다", "session_id": session_id}


# ============================================================================
# Recommendations Endpoint
# ============================================================================

@app.get(
    "/recommendations",
    tags=["recommendations"],
    responses={
        200: {
            "description": "종목 추천 성공",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "ticker": "005930",
                            "name": "삼성전자",
                            "signal_type": "vcp",
                            "grade": "A",
                            "score": 85,
                            "position_size": 12.0,
                        }
                    ]
                }
            }
        },
        500: {
            "description": "서버 오류",
        }
    },
)
async def get_recommendations(
    strategy: str = "both",
    limit: int = 5,
):
    """
    종목 추천 조회

    VCP/종가베팅 시그널 기반 종목 추천을 반환합니다.

    - **strategy**: 전략 (vcp, jongga, both)
    - **limit**: 최대 추천 수
    """
    try:
        recommender = get_recommender()

        # 추천 종목 조회
        recommendations = recommender.get_top_picks(strategy=strategy, limit=limit)

        # 종목명 추가 (StockRepository 사용)
        result = []
        for rec in recommendations:
            result.append({
                "ticker": rec.get("ticker"),
                "name": rec.get("name", rec.get("ticker", "")),  # 이름이 없으면 티커 사용
                "signal_type": rec.get("signal_type", ""),
                "grade": rec.get("grade", ""),
                "score": rec.get("score", 0),
                "position_size": recommender.get_position_size(rec.get("grade", "C")),
            })

        return result

    except Exception as e:
        logger.error(f"추천 종목 조회 실패: {e}")
        # 빈 리스트 반환 (서비스 중단 방지)
        return []


# ============================================================================
# Session Endpoint
# ============================================================================

@app.get(
    "/session/{session_id}",
    tags=["session"],
    responses={
        200: {
            "description": "세션 조회 성공",
        },
        404: {
            "description": "세션을 찾을 수 없음",
        }
    },
)
async def get_session(session_id: str):
    """
    세션 정보 조회

    특정 세션의 대화 기록을 반환합니다.

    - **session_id**: 세션 ID
    """
    try:
        session_manager = get_session_manager()

        # 세션 정보 조회
        session_info = session_manager.get_session_info(session_id)

        if session_info is None:
            raise HTTPException(
                status_code=404,
                detail=f"세션을 찾을 수 없습니다: {session_id}"
            )

        # 대화 기록 조회
        messages = session_manager.get_history_formatted(session_id)

        return {
            "session_id": session_id,
            "created_at": session_info.get("created_at", ""),
            "updated_at": session_info.get("last_activity", session_info.get("created_at", "")),
            "message_count": session_info.get("message_count", 0),
            "messages": messages,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"세션 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_rag_reply(
    message: str,
    context: Dict[str, Any],
    history: List[Dict]
) -> str:
    """
    RAG 컨텍스트 기반 응답 생성 (Phase 3)
    Phase 4에서 LLM으로 교체 예정

    Args:
        message: 사용자 메시지
        context: 검색된 RAG 컨텍스트
        history: 대화 기록

    Returns:
        생성된 응답
    """
    query_type = context.get("query_type", "general")

    # 시장 관련 질문
    if query_type == "market" and context.get("market_status"):
        status = context["market_status"]
        return (
            f"현재 Market Gate 상태는 {status['status']} (레벨 {status['level']})입니다. "
            f"KOSPI는 {status['kospi_status']}, KOSDAQ은 {status['kosdaq_status']} 상태입니다. "
            "이 정보는 참고용이며 투자 결정은 신중하시기 바랍니다."
        )

    # 종목 추천 관련 질문
    if query_type == "recommendation":
        if context.get("signals"):
            top_signals = sorted(
                context["signals"],
                key=lambda x: x.get("score", 0),
                reverse=True
            )[:3]

            if top_signals:
                reply = "현재 활성화된 시그널 기반 추천 종목입니다:\n"
                for sig in top_signals:
                    reply += f"\n- {sig['ticker']} ({sig['signal_type']} {sig['grade']}등급, {sig['score']}점)"
                reply += "\n\n각 종목의 리스크를 충분히 고려하시기 바랍니다."
                return reply

        return "현재 추천할 만한 시그널이 없습니다. VCP 스캔을 실행해보세요."

    # 특정 종목 관련 질문
    if query_type == "stock" and context.get("stocks"):
        stock = context["stocks"][0]
        ticker = stock["ticker"]
        name = stock["name"]

        # 해당 종목 시그널 확인
        stock_signals = [s for s in context.get("signals", []) if s["ticker"] == ticker]
        if stock_signals:
            sig = stock_signals[0]
            return (
                f"{name}({ticker})의 현재 시그널: {sig['signal_type']} {sig['grade']}등급 "
                f"({sig['score']}점). "
                "종가베팅 V2 scoring 기반 분석 결과입니다."
            )

        return f"{name}({ticker})에 대한 정보를 찾았습니다. 추가 분석을 원하시면 말씀해주세요."

    # 일본 인사
    if "안녕" in message or "hello" in message.lower():
        return (
            "안녕하세요! Ralph Stock 챗봇입니다. "
            "VCP 패턴, 종가베팅 시그널, Market Gate 등에 대해 질문해주세요."
        )

    # 기본 응답
    return "죄송합니다. 해당 내용에 대해 더 구체적인 질문을 해주시면 도와드리겠습니다."


def _generate_basic_reply(message: str) -> str:
    """기본 응답 생성 (레거시 호환용)"""
    return _generate_rag_reply(message, {}, [])


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "detail": exc.detail,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "detail": str(exc),
        }
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.chatbot.main:app",
        host="0.0.0.0",
        port=5114,
        reload=True,
    )
