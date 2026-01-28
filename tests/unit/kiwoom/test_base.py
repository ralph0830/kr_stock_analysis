"""
키움 기반 구조 테스트

TDD RED 단계: 테스트를 먼저 작성하고, 실패를 확인합니다.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import asdict
from datetime import datetime, timezone

from src.kiwoom.base import (
    RealtimePrice,
    OrderBook,
    KiwoomConfig,
    IKiwoomBridge
)
from src.kiwoom.base import KiwoomEventType


class TestKiwoomEventType:
    """KiwoomEventType Enum 테스트"""

    def test_event_type_values(self):
        """이벤트 타입 값 확인"""
        assert KiwoomEventType.RECEIVE_REAL_DATA.value == "OnReceiveRealData"
        assert KiwoomEventType.RECEIVE_MT_REAL_DATA.value == "OnReceiveMTRealData"
        assert KiwoomEventType.WS_CONNECTED.value == "WebSocketConnected"
        assert KiwoomEventType.WS_DISCONNECTED.value == "WebSocketDisconnected"
        assert KiwoomEventType.API_TOKEN_EXPIRED.value == "APITokenExpired"


class TestRealtimePrice:
    """RealtimePrice 데이터 클래스 테스트"""

    def test_create_realtime_price(self):
        """RealtimePrice 생성 테스트"""
        price = RealtimePrice(
            ticker="005930",
            price=85000.0,
            change=500.0,
            change_rate=0.59,
            volume=1000000,
            bid_price=84990.0,
            ask_price=85010.0,
            timestamp="2024-01-26T10:30:00Z"
        )

        assert price.ticker == "005930"
        assert price.price == 85000.0
        assert price.change == 500.0
        assert price.change_rate == 0.59
        assert price.volume == 1000000
        assert price.bid_price == 84990.0
        assert price.ask_price == 85010.0

    def test_realtime_price_to_dict(self):
        """RealtimePrice to_dict 테스트"""
        price = RealtimePrice(
            ticker="005930",
            price=85000.0,
            change=500.0,
            change_rate=0.59,
            volume=1000000,
            bid_price=84990.0,
            ask_price=85010.0,
            timestamp="2024-01-26T10:30:00Z"
        )

        data = price.to_dict()

        assert data["ticker"] == "005930"
        assert data["price"] == 85000.0
        assert data["change"] == 500.0
        assert data["change_rate"] == 0.59
        assert data["volume"] == 1000000
        assert data["bid_price"] == 84990.0
        assert data["ask_price"] == 85010.0
        assert data["timestamp"] == "2024-01-26T10:30:00Z"

    def test_realtime_price_with_negative_change(self):
        """전일대비 마이너스 테스트"""
        price = RealtimePrice(
            ticker="000660",
            price=91000.0,
            change=-1000.0,
            change_rate=-1.08,
            volume=5000000,
            bid_price=90990.0,
            ask_price=91010.0,
            timestamp="2024-01-26T10:30:00Z"
        )

        assert price.change == -1000.0
        assert price.change_rate == -1.08

    def test_realtime_price_immutability(self):
        """데이터 클래스 불변성 테스트 (frozen=False)"""
        price = RealtimePrice(
            ticker="005930",
            price=85000.0,
            change=500.0,
            change_rate=0.59,
            volume=1000000,
            bid_price=84990.0,
            ask_price=85010.0,
            timestamp="2024-01-26T10:30:00Z"
        )

        # 데이터 수정 가능 (frozen 아님)
        price.price = 86000.0
        assert price.price == 86000.0


class TestOrderBook:
    """OrderBook 데이터 클래스 테스트"""

    def test_create_orderbook(self):
        """OrderBook 생성 테스트"""
        orderbook = OrderBook(
            ticker="005930",
            bids=[(84990, 100), (84980, 200)],
            asks=[(85010, 150), (85020, 300)],
            timestamp="2024-01-26T10:30:00Z"
        )

        assert orderbook.ticker == "005930"
        assert len(orderbook.bids) == 2
        assert len(orderbook.asks) == 2
        assert orderbook.bids[0] == (84990, 100)
        assert orderbook.asks[0] == (85010, 150)

    def test_orderbook_to_dict(self):
        """OrderBook to_dict 테스트"""
        orderbook = OrderBook(
            ticker="005930",
            bids=[(84990, 100), (84980, 200)],
            asks=[(85010, 150), (85020, 300)],
            timestamp="2024-01-26T10:30:00Z"
        )

        data = orderbook.to_dict()

        assert data["ticker"] == "005930"
        assert data["bids"] == [(84990, 100), (84980, 200)]
        assert data["asks"] == [(85010, 150), (85020, 300)]
        assert data["timestamp"] == "2024-01-26T10:30:00Z"

    def test_orderbook_empty(self):
        """빈 OrderBook 테스트"""
        orderbook = OrderBook(
            ticker="005930",
            bids=[],
            asks=[],
            timestamp="2024-01-26T10:30:00Z"
        )

        assert len(orderbook.bids) == 0
        assert len(orderbook.asks) == 0


class TestKiwoomConfig:
    """KiwoomConfig 설정 클래스 테스트"""

    def test_create_config_manually(self):
        """수동 설정 생성 테스트"""
        config = KiwoomConfig(
            app_key="test_app_key",
            secret_key="test_secret",
            base_url="https://api.kiwoom.com",
            ws_url="wss://api.kiwoom.com:10000/api/dostk/websocket",
            use_mock=False,
            debug_mode=False,
            ws_ping_interval=None,
            ws_ping_timeout=None,
            ws_recv_timeout=60
        )

        assert config.app_key == "test_app_key"
        assert config.secret_key == "test_secret"
        assert config.base_url == "https://api.kiwoom.com"
        assert config.ws_url == "wss://api.kiwoom.com:10000/api/dostk/websocket"
        assert config.use_mock is False
        assert config.debug_mode is False
        assert config.ws_ping_interval is None
        assert config.ws_recv_timeout == 60

    @patch.dict('os.environ', {
        'KIWOOM_APP_KEY': 'real_app_key',
        'KIWOOM_SECRET_KEY': 'real_secret',
        'USE_MOCK': 'false',
        'DEBUG': 'false',
        'WS_RECV_TIMEOUT': '30'
    })
    def test_config_from_env_real(self):
        """실전투자 모드 환경변수 로드 테스트"""
        config = KiwoomConfig.from_env()

        assert config.app_key == "real_app_key"
        assert config.secret_key == "real_secret"
        assert config.base_url == "https://api.kiwoom.com"
        assert config.use_mock is False
        assert config.ws_recv_timeout == 30

    @patch.dict('os.environ', {
        'KIWOOM_MOCK_APP_KEY': 'mock_app_key',
        'KIWOOM_MOCK_SECRET_KEY': 'mock_secret',
        'USE_MOCK': 'true',
        'DEBUG': 'true',
        'WS_RECV_TIMEOUT': '120'
    })
    def test_config_from_env_mock(self):
        """모의투자 모드 환경변수 로드 테스트"""
        config = KiwoomConfig.from_env()

        assert config.app_key == "mock_app_key"
        assert config.secret_key == "mock_secret"
        assert config.base_url == "https://mockapi.kiwoom.com"
        assert config.use_mock is True
        assert config.debug_mode is True
        assert config.ws_recv_timeout == 120

    def test_config_from_env_missing_keys(self):
        """필수 환경변수 누락 시 예외 테스트"""
        # .env 파일이 없고 환경변수도 없는 경우
        # KiwoomConfig.from_env() 내부에서 dotenv 로드 후
        # 키가 없으면 ValueError 발생해야 함
        with patch.dict('os.environ', {
            'USE_MOCK': 'true',
            'DEBUG': 'false',
            'WS_RECV_TIMEOUT': '60'
        }):
            # KIWOOM_MOCK_APP_KEY와 KIWOOM_MOCK_SECRET_KEY가 없으므로
            # ValueError 발생해야 함
            with pytest.raises(ValueError):
                KiwoomConfig.from_env()


class TestIKiwoomBridge:
    """IKiwoomBridge 추상 인터페이스 테스트"""

    def test_abstract_methods(self):
        """추상 메서드 존재 확인 테스트"""
        abstract_methods = IKiwoomBridge.__abstractmethods__

        # Python 3.12+에서 __abstractmethods__는 문자열 frozenset을 반환
        assert "connect" in abstract_methods
        assert "disconnect" in abstract_methods
        assert "is_connected" in abstract_methods
        assert "has_valid_token" in abstract_methods
        assert "refresh_token" in abstract_methods
        assert "register_event" in abstract_methods
        assert "unregister_event" in abstract_methods
        assert "subscribe_realtime" in abstract_methods
        assert "unsubscribe_realtime" in abstract_methods
        assert "get_subscribe_list" in abstract_methods
        assert "get_current_price" in abstract_methods

    def test_cannot_instantiate_abstract_class(self):
        """추상 클래스 직접 인스턴스화 불가 테스트"""
        with pytest.raises(TypeError):
            IKiwoomBridge()

    def test_concrete_class_must_implement_all_methods(self):
        """구현 클래스가 모든 추상 메서드를 구현해야 함 테스트"""

        # 미구현 클래스로 테스트
        class IncompleteBridge(IKiwoomBridge):
            async def connect(self) -> bool:
                return True

            def is_connected(self) -> bool:
                return True

            # 나머지 메서드 미구현

        with pytest.raises(TypeError):
            IncompleteBridge()
