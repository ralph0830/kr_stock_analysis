"""
WebSocket 라우터
FastAPI WebSocket 엔드포인트
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import uuid

from src.websocket.server import connection_manager, price_broadcaster, get_heartbeat_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Phase 3: 하트비트 관리자 레퍼런스
_heartbeat_manager = get_heartbeat_manager()

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    subscribe: Optional[str] = Query(None, description="구독할 토픽 (콤마로 구분)"),
):
    """
    WebSocket 엔드포인트

    Usage:
        // 기본 연결
        ws://localhost:5111/ws

        // 토픽 구독
        ws://localhost:5111/ws?subscribe=price:005930,price:000660

    Message Format:
        {
            "type": "subscribe",  // 또는 "unsubscribe"
            "topic": "price:005930"
        }
    """
    # 클라이언트 ID 생성
    client_id = str(uuid.uuid4())

    # 연결 수락
    await connection_manager.connect(websocket, client_id)

    # 초기 구독 처리
    if subscribe:
        topics = subscribe.split(",")
        for topic in topics:
            topic = topic.strip()
            if topic:
                connection_manager.subscribe(client_id, topic)
                # price:{ticker} 형식이면 ticker를 price_broadcaster에 추가
                # (ConnectionManager.subscribe() 내부에서 처리됨)
                await websocket.send_json({
                    "type": "subscribed",
                    "topic": topic,
                    "message": f"Subscribed to {topic}",
                })

    # 환영 메시지
    await websocket.send_json({
        "type": "connected",
        "client_id": client_id,
        "message": "WebSocket connection established",
    })

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "subscribe":
                # 토픽 구독
                topic = data.get("topic")
                if topic:
                    connection_manager.subscribe(client_id, topic)
                    # price:{ticker} 형식이면 ticker를 price_broadcaster에 추가
                    # (ConnectionManager.subscribe() 내부에서 처리됨)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "message": f"Subscribed to {topic}",
                    })

            elif message_type == "unsubscribe":
                # 구독 취소
                topic = data.get("topic")
                if topic:
                    connection_manager.unsubscribe(client_id, topic)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "topic": topic,
                        "message": f"Unsubscribed from {topic}",
                    })

            elif message_type == "ping":
                # 핑/퐁응답
                await websocket.send_json({"type": "pong"})

            elif message_type == "pong":
                # Phase 3: Pong 수신 시간 기록
                if _heartbeat_manager:
                    _heartbeat_manager.record_pong(client_id)
                logger.debug(f"Pong received from {client_id}")

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                })

    except WebSocketDisconnect as e:
        # 상세한 종료 정보 로깅 (Phase 1: GREEN)
        logger.info(
            f"WebSocket client disconnected: {client_id} | "
            f"code={e.code}, reason='{e.reason}'"
        )
        # Phase 3: 하트비트 관리자에서 클라이언트 제거
        if _heartbeat_manager:
            _heartbeat_manager.remove_client(client_id)
        # ConnectionManager에 종료 정보 전달
        connection_manager.disconnect(client_id, code=e.code, reason=e.reason)
    except Exception as e:
        # 예외 타입과 메시지 로깅 (Phase 1: GREEN)
        import traceback
        logger.error(
            f"WebSocket error for {client_id}: {type(e).__name__}: {e}\n"
            f"Traceback: {traceback.format_exc()[-500:]}"  # 최근 500자만 로깅
        )
        # Phase 3: 하트비트 관리자에서 클라이언트 제거
        if _heartbeat_manager:
            _heartbeat_manager.remove_client(client_id)
        connection_manager.disconnect(client_id)


@router.get("/ws/stats")
async def websocket_stats():
    """
    WebSocket 연결 통계 엔드포인트

    Returns:
        연결 수, 구독자 수 등의 통계 정보
    """
    stats = {
        "active_connections": connection_manager.get_connection_count(),
        "subscriptions": {
            topic: connection_manager.get_subscriber_count(topic)
            for topic in ["price:005930", "price:000660", "signals", "market-gate"]
        },
        "broadcaster_running": price_broadcaster.is_running(),
        "active_tickers": list(price_broadcaster.get_active_tickers()),
        # Phase 3: 하트비트 상태
        "heartbeat_running": _heartbeat_manager.is_running() if _heartbeat_manager else False,
    }

    return stats


@router.post("/ws/subscribe/{ticker}")
async def subscribe_ticker(ticker: str):
    """
    종목 가격 구독 추가

    Args:
        ticker: 종목코드 (6자리)

    Returns:
        성공 메시지
    """
    # 종목코드 형식 검증 (6자리 숫자)
    if not ticker or not ticker.isdigit() or len(ticker) != 6:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 6-digit code.")

    price_broadcaster.add_ticker(ticker)
    return {
        "status": "subscribed",
        "ticker": ticker,
        "active_tickers": list(price_broadcaster.get_active_tickers()),
    }


@router.delete("/ws/subscribe/{ticker}")
async def unsubscribe_ticker(ticker: str):
    """
    종목 가격 구독 제거

    Args:
        ticker: 종목코드 (6자리)

    Returns:
        성공 메시지
    """
    price_broadcaster.remove_ticker(ticker)
    return {
        "status": "unsubscribed",
        "ticker": ticker,
        "active_tickers": list(price_broadcaster.get_active_tickers()),
    }


@router.get("/ws/tickers")
async def get_active_tickers():
    """
    활성화된 종목 목록 조회

    Returns:
        활성 종목 목록
    """
    return {
        "active_tickers": list(price_broadcaster.get_active_tickers()),
        "default_tickers": list(price_broadcaster.DEFAULT_TICKERS),
    }
