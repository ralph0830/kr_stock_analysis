"""
KR Stock WebSocket Client
실시간 가격 업데이트를 위한 WebSocket 클라이언트
"""

import asyncio
import json
from typing import Callable, Optional, Set, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosedError
import logging

logger = logging.getLogger(__name__)


class PriceUpdate:
    """가격 업데이트 데이터 모델"""

    def __init__(
        self,
        ticker: str,
        price: float,
        change: float,
        change_percent: float,
        volume: int,
        timestamp: str,
    ):
        self.ticker = ticker
        self.price = price
        self.change = change
        self.change_percent = change_percent
        self.volume = volume
        self.timestamp = timestamp

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PriceUpdate":
        """딕셔너리에서 PriceUpdate 객체 생성"""
        return cls(
            ticker=data.get("ticker", ""),
            price=data.get("price", 0.0),
            change=data.get("change", 0.0),
            change_percent=data.get("change_percent", 0.0),
            volume=data.get("volume", 0),
            timestamp=data.get("timestamp", ""),
        )

    def __repr__(self):
        return (
            f"PriceUpdate(ticker={self.ticker}, price={self.price}, "
            f"change={self.change}%, volume={self.volume})"
        )


class WebSocketClient:
    """
    KR Stock WebSocket 클라이언트

    실시간 가격 업데이트를 수신하고 구독 관리를 합니다.

    사용 예:
        async def on_price(update: PriceUpdate):
            print(f"Received: {update}")

        client = WebSocketClient("ws://localhost:5111/ws/price")
        await client.connect()

        # 종목 구독
        await client.subscribe("005930")  # 삼성전자
        await client.subscribe("000660")  # SK하이닉스

        # 콜백 등록
        client.on_price_update(on_price)

        # 메시지 수신 대기
        await client.listen()
    """

    def __init__(
        self,
        uri: str,
        reconnect_interval: float = 5.0,
        ping_interval: float = 20.0,
    ):
        """
        WebSocket 클라이언트 초기화

        Args:
            uri: WebSocket 서버 URI (예: ws://localhost:5111/ws/price)
            reconnect_interval: 재연결 시도 간격 (초)
            ping_interval: 핑 전송 간격 (초)
        """
        self.uri = uri
        self.reconnect_interval = reconnect_interval
        self.ping_interval = ping_interval

        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._subscriptions: Set[str] = set()
        self._callbacks: list[Callable[[PriceUpdate], None]] = []
        self._listening = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """
        WebSocket 서버에 연결

        Raises:
            ConnectionError: 연결 실패 시
        """
        try:
            logger.info(f"Connecting to WebSocket server: {self.uri}")
            self._websocket = await websockets.connect(
                self.uri,
                ping_interval=self.ping_interval,
                ping_timeout=10.0,
            )
            logger.info("WebSocket connected successfully")

            # 연결 성공 후 기존 구독 재등록
            if self._subscriptions:
                await self._resubscribe_all()

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

    async def disconnect(self) -> None:
        """WebSocket 연결 종료"""
        self._listening = False

        # 태스크 취소
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()

        # WebSocket 종료
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        logger.info("WebSocket disconnected")

    async def subscribe(self, ticker: str) -> None:
        """
        종목 가격 구독

        Args:
            ticker: 종목코드 (6자리)
        """
        if not self._websocket:
            raise ConnectionError("Not connected to WebSocket server")

        # 구독 요청 전송
        message = {
            "action": "subscribe",
            "topic": f"price:{ticker}",
        }
        await self._websocket.send(json.dumps(message))

        self._subscriptions.add(ticker)
        logger.info(f"Subscribed to price updates for {ticker}")

    async def unsubscribe(self, ticker: str) -> None:
        """
        종목 가격 구독 취소

        Args:
            ticker: 종목코드
        """
        if not self._websocket:
            raise ConnectionError("Not connected to WebSocket server")

        # 구독 취소 요청 전송
        message = {
            "action": "unsubscribe",
            "topic": f"price:{ticker}",
        }
        await self._websocket.send(json.dumps(message))

        self._subscriptions.discard(ticker)
        logger.info(f"Unsubscribed from price updates for {ticker}")

    async def _resubscribe_all(self) -> None:
        """모든 기존 구독 재등록"""
        for ticker in list(self._subscriptions):
            message = {
                "action": "subscribe",
                "topic": f"price:{ticker}",
            }
            await self._websocket.send(json.dumps(message))
            logger.info(f"Resubscribed to {ticker}")

    def on_price_update(self, callback: Callable[[PriceUpdate], None]) -> None:
        """
        가격 업데이트 콜백 등록

        Args:
            callback: 가격 업데이트 시 호출할 함수
        """
        self._callbacks.append(callback)
        logger.info(f"Registered price update callback: {callback.__name__}")

    async def listen(self) -> None:
        """
        WebSocket 메시지 수신 대기

        서버로부터 메시지를 수신하고 등록된 콜백을 호출합니다.
        연결이 끊어지면 자동으로 재연결을 시도합니다.
        """
        self._listening = True

        while self._listening:
            try:
                if not self._websocket:
                    await self.connect()

                async for message in self._websocket:
                    try:
                        data = json.loads(message)
                        update = PriceUpdate.from_dict(data)

                        # 콜백 호출
                        for callback in self._callbacks:
                            try:
                                callback(update)
                            except Exception as e:
                                logger.error(
                                    f"Error in price update callback: {e}"
                                )

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON received: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            except ConnectionClosedError:
                logger.warning("WebSocket connection closed, reconnecting...")
                self._websocket = None
                await asyncio.sleep(self.reconnect_interval)

            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(self.reconnect_interval)

    async def listen_once(self, timeout: float = 10.0) -> Optional[PriceUpdate]:
        """
        단일 메시지 수신 대기

        Args:
            timeout: 대기 타임아웃 (초)

        Returns:
            수신한 가격 업데이트 또는 None
        """
        if not self._websocket:
            raise ConnectionError("Not connected to WebSocket server")

        try:
            message = await asyncio.wait_for(
                self._websocket.recv(),
                timeout=timeout,
            )
            data = json.loads(message)
            return PriceUpdate.from_dict(data)

        except asyncio.TimeoutError:
            logger.warning(f"No message received within {timeout} seconds")
            return None
        except ConnectionClosedError:
            logger.error("Connection closed while waiting for message")
            return None

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._websocket is not None and not self._websocket.closed

    @property
    def subscriptions(self) -> Set[str]:
        """현재 구독 목록"""
        return self._subscriptions.copy()


class WebSocketClientPool:
    """
    여러 WebSocket 연결을 관리하는 풀

    여러 서버나 여러 토픽에 연결해야 할 때 사용합니다.
    """

    def __init__(self):
        self._clients: Dict[str, WebSocketClient] = {}

    async def create_client(
        self,
        name: str,
        uri: str,
        reconnect_interval: float = 5.0,
    ) -> WebSocketClient:
        """
        새 WebSocket 클라이언트 생성 및 연결

        Args:
            name: 클라이언트 고유 이름
            uri: WebSocket 서버 URI
            reconnect_interval: 재연결 시도 간격

        Returns:
            WebSocket 클라이언트 인스턴스
        """
        if name in self._clients:
            return self._clients[name]

        client = WebSocketClient(uri, reconnect_interval)
        await client.connect()
        self._clients[name] = client

        logger.info(f"Created WebSocket client: {name}")
        return client

    def get_client(self, name: str) -> Optional[WebSocketClient]:
        """
        이름으로 클라이언트 조회

        Args:
            name: 클라이언트 이름

        Returns:
            WebSocket 클라이언트 또는 None
        """
        return self._clients.get(name)

    async def close_all(self) -> None:
        """모든 클라이언트 종료"""
        for name, client in self._clients.items():
            try:
                await client.disconnect()
                logger.info(f"Closed WebSocket client: {name}")
            except Exception as e:
                logger.error(f"Error closing client {name}: {e}")

        self._clients.clear()

    async def __aenter__(self):
        """Async context manager 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager 종료"""
        await self.close_all()


# 유틸리티 함수
async def subscribe_to_tickers(
    uri: str,
    tickers: list[str],
    callback: Callable[[PriceUpdate], None],
    reconnect_interval: float = 5.0,
) -> WebSocketClient:
    """
    여러 종목을 구독하는 WebSocket 클라이언트 생성 및 시작

    Args:
        uri: WebSocket 서버 URI
        tickers: 구독할 종목코드 목록
        callback: 가격 업데이트 콜백
        reconnect_interval: 재연결 시도 간격

    Returns:
        WebSocket 클라이언트 인스턴스
    """
    client = WebSocketClient(uri, reconnect_interval)
    await client.connect()

    # 종목 구독
    for ticker in tickers:
        await client.subscribe(ticker)

    # 콜백 등록
    client.on_price_update(callback)

    logger.info(f"Subscribed to {len(tickers)} tickers")
    return client
