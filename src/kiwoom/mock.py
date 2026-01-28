"""
키움 Mock Bridge 구현

테스트 및 개발용 Mock으로 실제 API 연결 없이
실시간 데이터를 시뮬레이션합니다.
"""

import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from collections import defaultdict

from src.kiwoom.base import (
    KiwoomConfig,
    KiwoomEventType,
    RealtimePrice,
    OrderBook,
    IKiwoomBridge,
)


logger = logging.getLogger(__name__)


# 기종별 기준 가격 (Mock 데이터 생성용)
BASE_PRICES = {
    "005930": 72500,  # 삼성전자
    "000660": "현재가 확인 필요",  # SK하이닉스
    "035420": "현재가 확인 필요",  # NAVER
    "066570": "현재가 확인 필요",  # LG전자
    "005380": "현재가 확인 필요",  # 현대차
}


class MockKiwoomBridge(IKiwoomBridge):
    """
    키움 Mock Bridge

    실제 API 연결 없이 테스트용 데이터를 제공합니다.
    """

    def __init__(self, config: KiwoomConfig, seed: Optional[int] = None):
        """
        초기화

        Args:
            config: 키움 API 설정
            seed: 랜덤성 제어를 위한 시드값
        """
        self._config = config
        self._seed = seed

        # 랜덤성 제어
        if seed is not None:
            random.seed(seed)
            self._random = random.Random(seed)
        else:
            self._random = random

        # 연결 상태
        self._connected = False
        self._authenticated = False

        # 구독 관리
        self._subscribed_tickers = set()

        # 이벤트 핸들러
        self._event_handlers: Dict[KiwoomEventType, List[Callable]] = defaultdict(list)

        # 실시간 데이터 저장 (호가용)
        self._current_prices: Dict[str, RealtimePrice] = {}
        self._order_books: Dict[str, OrderBook] = {}

        # Mock 데이터 생성기
        self._price_generators: Dict[str, float] = {}

        # 백그라운드 태스크 추적 (cleanup용)
        self._background_tasks: List[asyncio.Task] = []

    @classmethod
    def from_env(cls) -> 'MockKiwoomBridge':
        """환경변수에서 설정 로드"""
        config = KiwoomConfig.from_env()
        return cls(config)

    # ==================== 연결 관리 ====================

    async def connect(self, access_token: Optional[str] = None) -> bool:
        """
        Mock 연결

        실제 API 연결 없이 즉시 성공 반환합니다.

        Args:
            access_token: OAuth2 액세스 토큰 (Mock에서는 무시됨)
        """
        self._connected = True
        self._authenticated = True
        logger.info("Mock Kiwoom Bridge connected")
        return True

    async def disconnect(self) -> None:
        """연결 해제"""
        self._connected = False
        self._authenticated = False
        self._subscribed_tickers.clear()
        self._event_handlers.clear()

        # 백그라운드 태스크 정리
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        self._background_tasks.clear()

        logger.info("Mock Kiwoom Bridge disconnected")

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected

    def has_valid_token(self) -> bool:
        """유효한 토큰 보유 여부"""
        return self._authenticated

    async def refresh_token(self) -> bool:
        """토큰 갱신 (Mock은 항상 성공)"""
        return True

    # ==================== 이벤트 관리 ====================

    def register_event(self, event_type: KiwoomEventType, callback: Callable) -> None:
        """이벤트 핸들러 등록"""
        if callback not in self._event_handlers[event_type]:
            self._event_handlers[event_type].append(callback)

    def unregister_event(self, event_type: KiwoomEventType, callback: Callable) -> None:
        """이벤트 핸들러 해제"""
        if callback in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(callback)

    def _emit_event(self, event_type: KiwoomEventType, data: Any) -> None:
        """이벤트 발생"""
        for handler in self._event_handlers.get(event_type, []):
            try:
                result = handler(data)
                # coroutine인 경우 asyncio.create_task로 스케줄링
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    # ==================== 실시간 시세 ====================

    async def subscribe_realtime(
        self,
        ticker: str
    ) -> bool:
        """
        실시간 시세 등록

        Mock은 별도의 스레드에서 실시간 데이터를 시뮬레이션합니다.
        """
        if not self._connected:
            return False

        self._subscribed_tickers.add(ticker)

        # 초기 가격 생성
        self._price_generators[ticker] = self._get_base_price(ticker)

        # 실시간 데이터 생성 시작 (백그라운드)
        task = asyncio.create_task(self._simulate_realtime_data(ticker))
        self._background_tasks.append(task)

        logger.info(f"Mock: Subscribed to realtime data for {ticker}")
        return True

    async def unsubscribe_realtime(self, ticker: str) -> bool:
        """실시간 시세 해제"""
        if ticker in self._subscribed_tickers:
            self._subscribed_tickers.remove(ticker)
            if ticker in self._price_generators:
                del self._price_generators[ticker]
            logger.info(f"Mock: Unsubscribed from realtime data for {ticker}")
            return True
        return False

    def get_subscribe_list(self) -> List[str]:
        """현재 등록된 실시간 시세 종목 리스트"""
        return list(self._subscribed_tickers)

    async def get_current_price(self, ticker: str) -> Optional[RealtimePrice]:
        """
        현재가 조회

        Mock은 랜덤하게 변동하는 가격을 반환합니다.
        """
        if not self._connected:
            return None

        # 기준 가격 가져오기
        if ticker not in self._price_generators:
            self._price_generators[ticker] = self._get_base_price(ticker)

        base_price = self._price_generators[ticker]

        # 랜덤 가격 변동 (-1% ~ +1%)
        change_rate = self._random.uniform(-0.01, 0.01)
        price = base_price * (1 + change_rate)
        change = price - base_price

        # 호가 생성
        spread = self._random.randint(10, 100)  # 1원 ~ 10원 스프레드

        return RealtimePrice(
            ticker=ticker,
            price=round(price, 0),
            change=round(change, 0),
            change_rate=round(change_rate * 100, 2),
            volume=self._random.randint(100000, 10000000),
            bid_price=round(price - spread, 0),
            ask_price=round(price + spread, 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _get_base_price(self, ticker: str) -> float:
        """종목별 기준 가격 가져오기"""
        if ticker in BASE_PRICES:
            price = BASE_PRICES[ticker]
            if isinstance(price, str):
                # 실제 가격 조회 또는 기본값 사용
                # 여기서는 간단히 기본값 반환
                return 70000.0
            return float(price)
        return 70000.0

    async def _simulate_realtime_data(self, ticker: str) -> None:
        """
        실시간 데이터 시뮬레이션

        백그라운드로 주기적으로 가격 변동을 생성합니다.
        """
        try:
            while self._connected and ticker in self._subscribed_tickers:
                # 1~3초마다 가격 업데이트
                await asyncio.sleep(self._random.uniform(1.0, 3.0))

                # 가격 생성
                price = await self.get_current_price(ticker)
                if price:
                    # 현재가 업데이트
                    self._current_prices[ticker] = price

                    # 이벤트 발생
                    self._emit_event(KiwoomEventType.RECEIVE_REAL_DATA, price)
        except asyncio.CancelledError:
            # 태스크 취소됨
            pass

    # ==================== 주문 관련 (Mock) ====================

    async def order_buy_market(self, ticker: str, quantity: int) -> Optional[Dict[str, Any]]:
        """시장가 매수 주문 (Mock)"""
        return await self._mock_order(ticker, "001", quantity, None)

    async def order_sell_market(self, ticker: str, quantity: int) -> Optional[Dict[str, Any]]:
        """시장가 매도 주문 (Mock)"""
        return await self._mock_order(ticker, "002", quantity, None)

    async def order_buy_limit(self, ticker: str, price: int, quantity: int) -> Optional[Dict[str, Any]]:
        """지정가 매수 주문 (Mock)"""
        return await self._mock_order(ticker, "001", quantity, price)

    async def order_sell_limit(self, ticker: str, price: int, quantity: int) -> Optional[Dict[str, Any]]:
        """지정가 매도 주문 (Mock)"""
        return await self._mock_order(ticker, "002", quantity, price)

    async def _mock_order(
        self,
        ticker: str,
        order_type: str,
        quantity: int,
        price: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """주문 시뮬레이션"""
        if not self._connected:
            return None

        # 주문번호 생성 (타임스탬프)
        order_no = f"{self._random.randint(1000, 9999)}"

        # 체결가 생성 (현재가 근처)
        current_price_data = await self.get_current_price(ticker)
        if current_price_data:
            execution_price = current_price_data.price
        else:
            execution_price = self._get_base_price(ticker)

        if price is not None:
            execution_price = price

        # 주문 결과 반환
        return {
            "order_no": order_no,
            "ticker": ticker,
            "order_type": order_type,
            "price": str(execution_price),
            "quantity": str(quantity),
            "status": "0",  # 접수 완료
        }

    # ==================== 계좌 조회 (Mock) ====================

    async def get_account_balance(self) -> Optional[List[Dict[str, Any]]]:
        """계좌 잔고 조회 (Mock)"""
        if not self._connected:
            return None

        # Mock 잔고 데이터
        return [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": "10",
                "avg_price": "72000",
                "current_price": "72500",
                "pl": "5000",
                "pl_rate": "0.69",
            },
            {
                "ticker": "000660",
                "name": "SK하이닉스",
                "quantity": "5",
                "avg_price": "150000",
                "current_price": "152000",
                "pl": "10000",
                "pl_rate": "1.33",
            },
        ]

    async def get_account_deposit(self) -> Optional[Dict[str, Any]]:
        """예수금 조회 (Mock)"""
        if not self._connected:
            return None

        return {
            "total_deposit": "100000000",
            "withdrawable": "50000000",
            "orderable": "20000000",
            "margin": "0",
        }
