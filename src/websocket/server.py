"""
WebSocket 서버
실시간 가격 업데이트 및 이벤트 브로드캐스트
"""

import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket
from datetime import datetime, timezone

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    WebSocket 연결 관리자

    Usage:
        manager = ConnectionManager()

        # 클라이언트 연결
        await manager.connect(websocket, "client_1")

        # 메시지 전송
        await manager.send_personal_message({"data": "value"}, "client_1")
        await manager.broadcast({"data": "value"})

        # 연결 종료
        manager.disconnect("client_1")
    """

    def __init__(self):
        # client_id -> WebSocket 매핑
        self.active_connections: Dict[str, WebSocket] = {}

        # topic -> Set[client_id] 매핑 (구독 관리)
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        클라이언트 연결

        Args:
            websocket: WebSocket 연결 객체
            client_id: 클라이언트 ID
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str) -> None:
        """
        클라이언트 연결 종료

        Args:
            client_id: 클라이언트 ID
        """
        # 모든 구독에서 클라이언트 제거
        for topic in list(self.subscriptions.keys()):
            self.unsubscribe(client_id, topic)

        # 연결 제거
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str) -> bool:
        """
        특정 클라이언트에게 메시지 전송

        Args:
            message: 전송할 메시지 (dict)
            client_id: 수신 클라이언트 ID

        Returns:
            전송 성공 여부
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
            self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict, topic: Optional[str] = None) -> None:
        """
        메시지 브로드캐스트

        Args:
            message: 전송할 메시지 (dict)
            topic: 토픽 (지정 시 해당 토픽 구독자에게만 전송)
        """
        # 수신자 결정
        if topic:
            recipients = self.subscriptions.get(topic, set())
        else:
            recipients = set(self.active_connections.keys())

        # 연결된 클라이언트에게 전송
        for client_id in recipients:
            if client_id in self.active_connections:
                await self.send_personal_message(message, client_id)

    def subscribe(self, client_id: str, topic: str) -> None:
        """
        토픽 구독

        Args:
            client_id: 클라이언트 ID
            topic: 구독할 토픽
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()

        self.subscriptions[topic].add(client_id)
        logger.info(f"Client {client_id} subscribed to {topic}")

    def unsubscribe(self, client_id: str, topic: str) -> None:
        """
        토픽 구독 취소

        Args:
            client_id: 클라이언트 ID
            topic: 구독 취소할 토픽
        """
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

            # 구독자가 없으면 토픽 삭제
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]

            logger.info(f"Client {client_id} unsubscribed from {topic}")

    def get_subscriptions(self, client_id: str) -> Set[str]:
        """
        클라이언트의 구독 목록 조회

        Args:
            client_id: 클라이언트 ID

        Returns:
            구독 중인 토픽 집합
        """
        topics = set()
        for topic, subscribers in self.subscriptions.items():
            if client_id in subscribers:
                topics.add(topic)
        return topics

    def get_connection_count(self) -> int:
        """현재 연결 수 반환"""
        return len(self.active_connections)

    def get_subscriber_count(self, topic: str) -> int:
        """토픽별 구독자 수 반환"""
        return len(self.subscriptions.get(topic, set()))


# 전역 연결 관리자 인스턴스
connection_manager = ConnectionManager()


class PriceUpdateBroadcaster:
    """
    가격 업데이트 브로드캐스터

    일정 주기로 가격 데이터를 수집하여 브로드캐스트

    Usage:
        broadcaster = PriceUpdateBroadcaster()

        # 브로드캐스팅 시작
        await broadcaster.start()

        # 브로드캐스팅 중지
        await broadcaster.stop()
    """

    def __init__(self, interval_seconds: int = 5):
        """
        Args:
            interval_seconds: 브로드캐스트 주기 (초)
        """
        self.interval_seconds = interval_seconds
        self._broadcast_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def _broadcast_loop(self):
        """브로드캐스트 루프"""
        while self._is_running:
            try:
                # TODO: 실제 가격 데이터 조회 (DB 또는 외부 API)
                # 현재는 Mock 데이터
                price_updates = self._generate_mock_price_updates()

                # 브로드캐스트
                for ticker, data in price_updates.items():
                    await connection_manager.broadcast(
                        {
                            "type": "price_update",
                            "ticker": ticker,
                            "data": data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        topic=f"price:{ticker}",
                    )

                logger.debug(f"Broadcasted price updates for {len(price_updates)} tickers")

            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")

            # 대기
            await asyncio.sleep(self.interval_seconds)

    def _generate_mock_price_updates(self) -> Dict[str, dict]:
        """Mock 가격 업데이트 생성 (테스트용)"""
        # TODO: 실제 데이터로 교체 필요
        return {
            "005930": {
                "price": 82500,
                "change": 500,
                "change_rate": 0.61,
                "volume": 15000000,
            },
            "000660": {
                "price": 92000,
                "change": -1000,
                "change_rate": -1.08,
                "volume": 8000000,
            },
        }

    async def start(self):
        """브로드캐스팅 시작"""
        if self._is_running:
            logger.warning("Broadcaster is already running")
            return

        self._is_running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("Price update broadcaster started")

    async def stop(self):
        """브로드캐스팅 중지"""
        if not self._is_running:
            return

        self._is_running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        logger.info("Price update broadcaster stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._is_running


# 전역 브로드캐스터 인스턴스
price_broadcaster = PriceUpdateBroadcaster(interval_seconds=5)
