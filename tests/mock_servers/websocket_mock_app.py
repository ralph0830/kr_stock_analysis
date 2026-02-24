"""
Mock WebSocket Server Application
==================================

WebSocket Mock 서버의 메인 애플리케이션
"""

import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from tests.mock_servers.websocket_mock_server import websocket_endpoint, mock_ws_server

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Mock WebSocket Server",
    description="실시간 데이터 전송용 Mock WebSocket 서버",
    version="1.0.0",
)


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "service": "Mock WebSocket Server",
        "status": "running",
        "connections": len(mock_ws_server.active_connections),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
async def health():
    """헬스 체크 (Docker healthcheck용)"""
    return {
        "status": "healthy",
        "connections": len(mock_ws_server.active_connections),
    }


@app.get("/stats")
async def stats():
    """서버 통계"""
    return {
        "active_connections": len(mock_ws_server.active_connections),
        "broadcasting": mock_ws_server._running,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    await websocket_endpoint(websocket, mock_ws_server)


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 브로드캐스팅 시작"""
    import asyncio
    logger.info("Mock WebSocket Server 시작")

    # 백그라운드에서 브로드캐스팅 시작
    asyncio.create_task(mock_ws_server.start_broadcasting(interval=2.0))


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 브로드캐스팅 중지"""
    logger.info("Mock WebSocket Server 종료")
    mock_ws_server.stop_broadcasting()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5117,
        log_level="info",
    )
