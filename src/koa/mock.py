"""
Mock KOA Bridge for Testing
테스트 및 개발용 Mock 키움 KOA 구현
"""

import random
import time
import asyncio
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime, timezone

from src.koa.base import (
    KOABaseBridge,
    KOAEventType,
    RealtimePrice,
    OrderBook,
    DEFAULT_REALTIME_FIDS
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Mock 기준 가격 (테스트용)
MOCK_PRICES = {
    "005930": 84000,   # 삼성전자
    "000660": 180000,  # SK하이닉스
    "035420": 220000,  # NAVER
    "005380": 240000,  # 현대차
    "028260": 150000,  # 삼성물산
    "006400": 90000,   # LG전자
    "068270": 75000,   # 셀트리온
    "105560": 65000,   # KB금융
}


class MockKOABridge(KOABaseBridge):
    """
    Mock KOA Bridge

    실제 키움 HTS 없이 테스트하기 위한 Mock 구현입니다.
    랜덤한 실시간 데이터를 생성하여 실제 KOA와 유사하게 동작합니다.
    """

    def __init__(self, auto_update: bool = True, update_interval: float = 1.0):
        """
        Args:
            auto_update: 자동 가격 업데이트 여부
            update_interval: 업데이트 간격 (초)
        """
        super().__init__()
        self._auto_update = auto_update
        self._update_interval = update_interval
        self._update_task = None
        self._current_prices: Dict[str, float] = MOCK_PRICES.copy()
        self._running = False

        # Mock 상태
        self._market_open = True  # 장 운영 상태

    def connect(self) -> bool:
        """모의 연결"""
        logger.info("[Mock KOA] Connecting...")
        time.sleep(0.5)  # 연결 지연 시뮬레이션
        self._connected = True
        self._emit_event(KOAEventType.EVENT_CONNECT, True)
        logger.info("[Mock KOA] Connected")
        return True

    def disconnect(self) -> None:
        """연결 해제"""
        logger.info("[Mock KOA] Disconnecting...")
        self._running = False
        self._connected = False
        self._logged_in = False
        self._emit_event(KOAEventType.RECEIVE_DISCONNECTED)
        logger.info("[Mock KOA] Disconnected")

    def login(
        self,
        user_id: str,
        password: str,
        cert_passwd: str = ""
    ) -> bool:
        """모의 로그인"""
        if not self._connected:
            logger.warning("[Mock KOA] Not connected")
            return False

        logger.info(f"[Mock KOA] Logging in as {user_id}...")
        time.sleep(0.3)  # 로그인 지연 시뮬레이션

        # 비밀번호 길이만 검증
        if len(password) < 4:
            logger.error("[Mock KOA] Invalid password")
            return False

        self._logged_in = True
        logger.info("[Mock KOA] Logged in successfully")
        return True

    def subscribe_realtime(
        self,
        ticker: str,
        fid_list: Optional[List[str]] = None
    ) -> bool:
        """
        실시간 시레 등록 (Mock)

        Mock 데이터 생성을 시작합니다.
        """
        if not self._logged_in:
            logger.warning("[Mock KOA] Not logged in")
            return False

        ticker = ticker.zfill(6)

        # 기준 가격이 없으면 랜덤 생성
        if ticker not in self._current_prices:
            self._current_prices[ticker] = random.randint(50000, 200000)

        self._subscribed_tickers.add(ticker)
        logger.info(f"[Mock KOA] Subscribed to {ticker}")

        # 자동 업데이트 시작
        if self._auto_update and not self._running:
            self._start_auto_update()

        return True

    def unsubscribe_realtime(self, ticker: str) -> bool:
        """실시간 시레 해제"""
        ticker = ticker.zfill(6)
        if ticker in self._subscribed_tickers:
            self._subscribed_tickers.remove(ticker)
            logger.info(f"[Mock KOA] Unsubscribed from {ticker}")
            return True
        return False

    def request_market_state(self) -> Optional[Dict[str, Any]]:
        """장 운영 상태 조회 (Mock)"""
        return {
            "market_status": "OPEN" if self._market_open else "CLOSE",
            "market_time": datetime.now(timezone.utc).isoformat(),
            "is_trading": self._market_open,
        }

    def _start_auto_update(self) -> None:
        """자동 가격 업데이트 시작"""
        if self._running:
            return

        self._running = True
        logger.info("[Mock KOA] Starting auto update loop")

        # 별도 스레드에서 업데이트 루프 실행
        import threading
        self._update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self._update_thread.start()

    def _update_loop(self) -> None:
        """가격 업데이트 루프"""
        while self._running and self._subscribed_tickers:
            for ticker in list(self._subscribed_tickers):
                if not self._running:
                    break

                # 랜덤 가격 변동 생성
                price_data = self._generate_price_update(ticker)

                # 실시간 데이터 이벤트 발생
                self._emit_event(
                    KOAEventType.RECEIVE_REAL_DATA,
                    ticker,
                    price_data
                )

            time.sleep(self._update_interval)

    def _generate_price_update(self, ticker: str) -> RealtimePrice:
        """
        랜덤 가격 업데이트 생성

        실제 시장과 유사한 변동성을 모사합니다.
        """
        import random

        # 현재 가격
        current_price = self._current_prices.get(ticker, 50000)

        # 랜덤 변동 (-0.3% ~ +0.3%)
        change_rate = random.uniform(-0.3, 0.3)
        change_amount = current_price * (change_rate / 100)

        # 새로운 가격
        new_price = current_price + change_amount
        new_price = round(new_price)  # 원 단위

        # 가격 업데이트
        self._current_prices[ticker] = new_price

        # 전일 대비 (가정)
        prev_price = current_price - change_amount
        change = new_price - prev_price
        change_pct = (change / prev_price * 100) if prev_price > 0 else 0

        # 호가 스프레드 생성
        spread = random.randint(10, 50)
        bid_price = new_price - spread
        ask_price = new_price + spread

        # 거래량 (누적)
        volume = random.randint(100000, 10000000)

        return RealtimePrice(
            ticker=ticker,
            price=new_price,
            change=round(change, 2),
            change_rate=round(change_pct, 2),
            volume=volume,
            bid_price=bid_price,
            ask_price=ask_price,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def set_market_open(self, open: bool) -> None:
        """장 운영 상태 설정 (테스트용)"""
        self._market_open = open
        logger.info(f"[Mock KOA] Market {'opened' if open else 'closed'}")

    def set_price(self, ticker: str, price: float) -> None:
        """특정 종목 가격 설정 (테스트용)"""
        ticker = ticker.zfill(6)
        self._current_prices[ticker] = price
        logger.debug(f"[Mock KOA] Set {ticker} price to {price}")


class AsyncMockKOABridge:
    """
    비동기 Mock KOA Bridge

    asyncio 기반 환경에서 사용하기 위한 비동기 버전입니다.
    """

    def __init__(self, update_interval: float = 1.0):
        self._bridge = MockKOABridge(auto_update=False, update_interval=update_interval)
        self._update_task = None
        self._running = False

    async def connect(self) -> bool:
        """비동기 연결"""
        return await asyncio.to_thread(self._bridge.connect)

    async def disconnect(self) -> None:
        """비동기 연결 해제"""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        await asyncio.to_thread(self._bridge.disconnect)

    async def login(self, user_id: str, password: str) -> bool:
        """비동기 로그인"""
        return await asyncio.to_thread(
            self._bridge.login, user_id, password
        )

    async def subscribe_realtime(self, ticker: str) -> bool:
        """비동기 실시간 시레 등록"""
        result = await asyncio.to_thread(self._bridge.subscribe_realtime, ticker)

        # 비동기 업데이트 시작
        if result and not self._running:
            self._running = True
            self._update_task = asyncio.create_task(self._async_update_loop())

        return result

    async def unsubscribe_realtime(self, ticker: str) -> bool:
        """비동기 실시간 시레 해제"""
        return await asyncio.to_thread(self._bridge.unsubscribe_realtime, ticker)

    def register_event(self, event_type: KOAEventType, callback: Callable) -> None:
        """이벤트 핸들러 등록"""
        self._bridge.register_event(event_type, callback)

    def unregister_event(self, event_type: KOAEventType, callback: Callable) -> None:
        """이벤트 핸들러 해제"""
        self._bridge.unregister_event(event_type, callback)

    async def _async_update_loop(self) -> None:
        """비동기 업데이트 루프"""
        while self._running and self._bridge._subscribed_tickers:
            for ticker in list(self._bridge._subscribed_tickers):
                if not self._running:
                    break

                # 가격 업데이트 생성
                price_data = self._bridge._generate_price_update(ticker)

                # 이벤트 발생
                self._bridge._emit_event(
                    KOAEventType.RECEIVE_REAL_DATA,
                    ticker,
                    price_data
                )

            await asyncio.sleep(self._bridge._update_interval)
