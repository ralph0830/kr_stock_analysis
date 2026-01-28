"""
Chatbot Service Schemas
챗봇 서비스의 Request/Response 모델 정의
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ============================================================================
# Request Models
# ============================================================================

class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    message: str = Field(..., min_length=1, description="사용자 메시지")
    session_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="세션 ID (없으면 자동 생성)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "삼성전자 추천해줘",
                    "session_id": "user-session-123"
                }
            ]
        }
    }


# ============================================================================
# Response Models
# ============================================================================

class ChatResponse(BaseModel):
    """채팅 응답 모델"""

    reply: str = Field(..., description="봇 응답 메시지")
    suggestions: List[str] = Field(
        default_factory=list,
        description="추천 질문 리스트"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="세션 ID"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="응답 시간"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reply": "삼성전자(005930)을 추천합니다. VCP 패턴이 감지되었습니다.",
                    "suggestions": [
                        "삼성전자 재무제표",
                        "삼성전자 최신 뉴스",
                        "삼성전자 목표가"
                    ],
                    "session_id": "user-session-123",
                    "timestamp": "2026-01-28T10:00:00"
                }
            ]
        }
    }


class ContextResponse(BaseModel):
    """대화 컨텍스트 응답 모델"""

    session_id: str = Field(..., description="세션 ID")
    history: List[dict] = Field(
        default_factory=list,
        description="대화 기록"
    )
    message_count: int = Field(
        default=0,
        description="메시지 수"
    )


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""

    status: str = Field(default="healthy", description="서비스 상태")
    service: str = Field(default="chatbot", description="서비스명")
    version: str = Field(default="1.0.0", description="버전")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="응답 시간"
    )


# ============================================================================
# Session Models
# ============================================================================

class SessionMessage(BaseModel):
    """세션 메시지 모델"""

    role: str = Field(..., description="user 또는 assistant")
    content: str = Field(..., description="메시지 내용")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="메시지 시간"
    )


class SessionInfo(BaseModel):
    """세션 정보 모델"""

    session_id: str = Field(..., description="세션 ID")
    created_at: str = Field(..., description="생성 시간")
    message_count: int = Field(default=0, description="메시지 수")
    last_activity: str = Field(..., description="마지막 활동 시간")
