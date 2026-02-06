"""
Daytrading 브로드캐스터

실시간 시그널과 가격 업데이트를 WebSocket으로 브로드캐스트합니다.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def broadcast_daytrading_signals(
    signals: List[Dict[str, Any]],
    connection_manager,
) -> None:
    """
    단타 시그널 브로드캐스트

    Args:
        signals: 시그널 데이터 리스트
        connection_manager: WebSocket ConnectionManager 인스턴스
    """
    if not connection_manager:
        logger.warning("ConnectionManager not available, skipping broadcast")
        return

    # 메시지 생성
    message = {
        "type": "signal_update",
        "data": {
            "count": len(signals),
            "signals": signals,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

    # 브로드캐스트 (signal:daytrading 토픽)
    topic = "signal:daytrading"
    await connection_manager.broadcast(message, topic=topic)

    logger.info(f"Broadcasted {len(signals)} daytrading signals to topic '{topic}'")


async def broadcast_price_update(
    ticker: str,
    price_data: Dict[str, Any],
    connection_manager,
) -> None:
    """
    종목 가격 업데이트 브로드캐스트

    Args:
        ticker: 종목 코드
        price_data: 가격 데이터 (price, change, change_rate, volume)
        connection_manager: WebSocket ConnectionManager 인스턴스
    """
    if not connection_manager:
        logger.warning("ConnectionManager not available, skipping broadcast")
        return

    # 메시지 생성
    message = {
        "type": "price_update",
        "ticker": ticker,
        "data": {
            "price": price_data.get("price"),
            "change": price_data.get("change"),
            "change_rate": price_data.get("change_rate"),
            "volume": price_data.get("volume", 0)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 브로드캐스트 (price:{ticker} 토픽)
    topic = f"price:{ticker}"
    await connection_manager.broadcast(message, topic=topic)

    logger.debug(f"Broadcasted price update for {ticker} to topic '{topic}'")


class DaytradingBroadcaster:
    """
    단타 브로드캐스터

    실시간 시그널과 가격 업데이트를 관리합니다.
    """

    def __init__(self, connection_manager=None):
        """
        초기화

        Args:
            connection_manager: WebSocket ConnectionManager 인스턴스 (선택)
        """
        self._connection_manager = connection_manager

    async def broadcast_signals(self, signals: List[Dict[str, Any]]) -> None:
        """
        시그널 브로드캐스트

        Args:
            signals: 시그널 데이터 리스트
        """
        await broadcast_daytrading_signals(signals, self._connection_manager)

    async def broadcast_price(
        self,
        ticker: str,
        price_data: Dict[str, Any]
    ) -> None:
        """
        가격 업데이트 브로드캐스트

        Args:
            ticker: 종목 코드
            price_data: 가격 데이터
        """
        await broadcast_price_update(ticker, price_data, self._connection_manager)
