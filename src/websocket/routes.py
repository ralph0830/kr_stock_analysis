"""
WebSocket 라우터
FastAPI WebSocket 엔드포인트

kiwoom_stock_telegram 패턴 적용:
- 타임아웃 처리 (wait_for)
- 빈 메시지 처리
- 명확한 예외 처리
"""

import asyncio
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from src.websocket.server import connection_manager, price_broadcaster, signal_broadcaster, get_heartbeat_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Phase 3: 하트비트 관리자 레퍼런스
_heartbeat_manager = get_heartbeat_manager()

# WebSocket 설정
WS_RECV_TIMEOUT = 120  # 메시지 수신 타임아웃 (초) - 60→120 증가 (keepalive 개선)

# CORS 허용_origin 목록 (main.py의 CORSMiddleware와 동기화 필요)
ALLOWED_WS_ORIGINS = [
    "http://localhost:5110",
    "http://127.0.0.1:5110",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ralphpark.com",
    "http://ralphpark.com",
    "https://ralphpark.com:5110",
    "http://ralphpark.com:5110",
    "https://stock.ralphpark.com",
    "http://stock.ralphpark.com",
    "null",  # 로컬 파일에서 접근하는 경우
]

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    subscribe: Optional[str] = Query(None, description="구독할 토픽 (콤마로 구분)"),
):
    """
    WebSocket 엔드포인트

    kiwoom_stock_telegram 패턴 적용:
    - 타임아웃 처리로 무한 대기 방지
    - 빈 메시지 처리
    - 명확한 예외 처리 및 로깅
    - CORS origin 검사 (WebSocket handshake)

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

    # WebSocket CORS origin 검사 (개발 환경 친화적)
    origin = websocket.headers.get("origin", "").lower()
    client_host = websocket.client.host

    logger.info(f"[WebSocket] Connection attempt from {client_host}:{websocket.client.port}, origin: {origin or '(none)'}")

    # 개발 환경에서는 localhost/127.0.0.1 연결 무조건 허용
    # (같은 머신에서 실행되는 frontend ↔ backend 통신)
    is_local_connection = client_host in ["localhost", "127.0.0.1", "::1", "0.0.0.0"]

    if is_local_connection:
        # 로컬 개발 환경 - 허용 (origin이 없어도 OK)
        logger.info(f"[WebSocket] Local connection allowed for {client_host}")
    elif origin:
        # origin이 있는 경우 허용 목록 확인
        origin_allowed = any(
            allowed.lower() == origin or
            allowed.lower() == origin.replace("https://", "http://") or
            (origin.startswith("http://localhost") and allowed.startswith("http://localhost")) or
            (origin.startswith("http://127.0.0.1") and allowed.startswith("http://127.0.0.1")) or
            origin == "null"  # 로컬 파일
            for allowed in ALLOWED_WS_ORIGINS
        )

        if not origin_allowed:
            logger.warning(f"[WebSocket] Connection rejected: origin not allowed ({origin})")
            await websocket.close(code=1008, reason="Origin not allowed")
            return
    else:
        # origin이 없고 로컬 연결도 아닌 경우 거부
        logger.warning(f"[WebSocket] Connection rejected: no origin and not local connection")
        await websocket.close(code=1008, reason="Origin required")
        return

    # 연결 수락 (명시적으로 accept 호출)
    await websocket.accept()
    logger.info(f"[WebSocket] Connection accepted for {client_id}")

    # ConnectionManager에 등록
    connection_manager.active_connections[client_id] = websocket
    logger.info(f"[WebSocket] Client {client_id} registered with manager")

    # 초기 구독 처리
    if subscribe:
        topics = subscribe.split(",")
        for topic in topics:
            topic = topic.strip()
            if topic:
                connection_manager.subscribe(client_id, topic)
                try:
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "message": f"Subscribed to {topic}",
                    })
                except Exception as e:
                    logger.error(f"[WebSocket] Failed to send subscribe confirmation: {e}")

    # 환영 메시지
    try:
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "WebSocket connection established",
        })
        logger.info(f"[WebSocket] Welcome message sent to {client_id}")
    except Exception as e:
        logger.error(f"[WebSocket] Failed to send welcome message: {e}")
        await connection_manager.disconnect(client_id)
        return

    # 연결 추적용 변수 (keepalive 모니터링)
    connection_start_time = time.time()
    last_ping_time = time.time()
    last_pong_time = time.time()

    # 메시지 수신 루프 (kiwoom_stock_telegram 패턴 적용)
    while True:
        try:
            # 타임아웃 설정으로 메시지 대기
            # receive_json()을 사용하되, 타임아웃은 asyncio.wait_for로 처리
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=float(WS_RECV_TIMEOUT)
            )

            message_type = data.get("type")
            current_time = time.time()
            print(f"[WS ROUTER] Received message from {client_id}: type={message_type}, data={data}")
            logger.debug(f"[WebSocket] Received from {client_id}: {message_type}")

            # 메시지 타입별 처리
            if message_type == "subscribe":
                topic = data.get("topic")
                print(f"[WS ROUTER] Processing subscribe request for topic: {topic}")
                if topic:
                    connection_manager.subscribe(client_id, topic)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "message": f"Subscribed to {topic}",
                    })
                    print(f"[WS ROUTER] Sent subscribed confirmation for {topic}")

            elif message_type == "unsubscribe":
                topic = data.get("topic")
                if topic:
                    connection_manager.unsubscribe(client_id, topic)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "topic": topic,
                        "message": f"Unsubscribed from {topic}",
                    })

            elif message_type == "ping":
                # 핑/퐁 응답 (kiwoom_stock_telegram 패턴: 그대로 돌려보냄)
                await websocket.send_json({"type": "pong"})
                round_trip_ms = (current_time - last_ping_time) * 1000
                logger.debug(f"[WebSocket] Ping/Pong exchanged with {client_id}, "
                              f"round-trip: {round_trip_ms:.0f}ms")
                last_ping_time = current_time

            elif message_type == "pong":
                # Phase 3: Pong 수신 시간 기록 및 ping-pong 간격 모니터링
                if _heartbeat_manager:
                    _heartbeat_manager.record_pong(client_id)
                last_pong_time = current_time
                time_since_last_ping = (current_time - last_ping_time)
                logger.debug(f"[WebSocket] Pong received from {client_id}, "
                              f"ping-pong gap: {time_since_last_ping:.1f}s")

                # 너무 오래된 pong 경고 (60초 이상)
                if time_since_last_ping > 60:
                    logger.warning(f"[WebSocket] Large ping-pong gap ({time_since_last_ping:.1f}s) "
                                    f"for client {client_id}")

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                })

        except asyncio.TimeoutError:
            # 타임아웃 시에도 연결 유지 (kiwoom_stock_telegram 패턴)
            logger.debug(f"[WebSocket] No message from {client_id} for {WS_RECV_TIMEOUT}s, keeping connection alive")
            continue

        except WebSocketDisconnect as e:
            # 정상/비정상 종료 처리 (kiwoom_stock_telegram 패턴)
            duration = time.time() - connection_start_time
            if e.code == 1000:
                logger.info(f"[WebSocket] Client {client_id} disconnected normally (duration: {duration:.1f}s)")
            else:
                logger.warning(
                    f"[WebSocket] Client {client_id} disconnected abnormally | "
                    f"code={e.code}, reason='{e.reason}', duration: {duration:.1f}s"
                )
            # 하트비트 관리자에서 클라이언트 제거
            if _heartbeat_manager:
                _heartbeat_manager.remove_client(client_id)
            # ConnectionManager.disconnect() 호출 - subscriptions에서도 제거
            connection_manager.disconnect(client_id, code=e.code, reason=e.reason)
            break

        except Exception as e:
            # 기타 예외 처리
            import traceback
            duration = time.time() - connection_start_time
            logger.error(
                f"[WebSocket] Error for {client_id} (duration: {duration:.1f}s): {type(e).__name__}: {e}\n"
                f"Traceback: {traceback.format_exc()[-500:]}"
            )
            # 하트비트 관리자에서 클라이언트 제거
            if _heartbeat_manager:
                _heartbeat_manager.remove_client(client_id)
            # ConnectionManager.disconnect() 호출 - subscriptions에서도 제거
            connection_manager.disconnect(client_id)
            break


@router.get("/ws/stats")
async def websocket_stats():
    """
    WebSocket 연결 통계 엔드포인트 (모든 구독 토픽 동적 반환)

    Returns:
        연결 수, 모든 구독 토픽의 구독자 수 등의 통계 정보
    """
    from src.websocket.kiwoom_bridge import get_kiwoom_ws_bridge

    ws_bridge = get_kiwoom_ws_bridge()
    bridge_running = ws_bridge is not None and ws_bridge.is_running()
    bridge_tickers = list(ws_bridge.get_active_tickers()) if ws_bridge else []

    # 모든 구독 토픽 동적으로 수집 (하드코딩된 목록 제거)
    all_subscriptions = connection_manager.subscriptions.copy()

    # 구독자 수만 추출하여 반환
    subscriptions_dict = {
        topic: len(subscribers)
        for topic, subscribers in all_subscriptions.items()
    }

    # active_tickers를 bridge와 broadcaster의 합집합으로 반환
    # KiwoomWebSocketBridge가 running이면 bridge_tickers를 포함
    active_tickers = set(price_broadcaster.get_active_tickers())
    if bridge_running and ws_bridge:
        active_tickers.update(ws_bridge.get_active_tickers())

    stats = {
        "active_connections": connection_manager.get_connection_count(),
        "subscriptions": subscriptions_dict,  # 모든 구독 토픽 반환
        "bridge_running": bridge_running,
        "bridge_tickers": bridge_tickers,
        "broadcaster_running": price_broadcaster.is_running(),
        "active_tickers": list(active_tickers),  # bridge + broadcaster 합집합
        # Phase 3: 하트비트 상태
        "heartbeat_running": _heartbeat_manager.is_running() if _heartbeat_manager else False,
        # VCP 시그널 브로드캐스터 상태
        "signal_broadcaster_running": signal_broadcaster.is_running(),
        "recv_timeout": WS_RECV_TIMEOUT,
    }

    return stats


@router.post("/ws/subscribe/{ticker}")
async def subscribe_ticker(ticker: str):
    """
    종목 가격 구독 추가 (ELW 지원)

    Args:
        ticker: 종목코드 (6자리, ELW 포함)

    Returns:
        성공 메시지
    """
    # 종목코드 형식 검증 (KOSPI/KOSDAQ 6자리 숫자 또는 ELW 6자리)
    if not ticker or len(ticker) != 6:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 6-digit code.")

    # ELW 형식 검증 (숫자+알파벳 조합)
    is_valid = ticker.isdigit() or (
        any(c.isdigit() for c in ticker) and any(c.isalpha() for c in ticker)
    )
    if not is_valid:
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


@router.get("/ws/status")
async def get_websocket_status():
    """
    WebSocket 연결 상태 조회

    Returns:
        WebSocket 연결 상태 정보
    """
    from src.websocket.server import get_heartbeat_manager

    heartbeat_mgr = get_heartbeat_manager()

    # 활성 연결 수
    active_connections = len(connection_manager.active_connections)

    # 활성 토픽 수 (구독자가 있는 토�)
    active_topics = len([t for t, subs in connection_manager.subscriptions.items() if subs])

    # 전체 구독 수 (중복 포함)
    total_subscriptions = sum(len(subs) for subs in connection_manager.subscriptions.values())

    # 하트비트 상태
    heartbeat_running = heartbeat_mgr.is_running() if heartbeat_mgr else False

    # 가격 브로드캐스터 상태
    broadcaster_running = price_broadcaster.is_running()
    broadcaster_active_tickers = list(price_broadcaster.get_active_tickers())

    return {
        "websocket": {
            "active_connections": active_connections,
            "active_topics": active_topics,
            "total_subscriptions": total_subscriptions,
        },
        "heartbeat": {
            "running": heartbeat_running,
        },
        "price_broadcaster": {
            "running": broadcaster_running,
            "active_tickers": broadcaster_active_tickers,
            "ticker_count": len(broadcaster_active_tickers),
        },
        "timestamp": connection_manager.get_last_activity(),
    }
