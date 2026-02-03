"""
WebSocket ConnectionManager ELW 지원 테스트

ELW(상장지수증권) 종목 코드 형식 지원을 검증합니다.
"""
import pytest

from src.websocket.server import ConnectionManager
from src.websocket.kiwoom_bridge import KiwoomWebSocketBridge


class TestConnectionManagerELW:
    """ConnectionManager ELW 지원 테스트"""

    def test_is_valid_ticker_kospi(self):
        """KOSPI 종목 코드 검증 (6자리 숫자)"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("005930") is True  # 삼성전자
        assert manager._is_valid_ticker("000660") is True  # SK하이닉스
        assert manager._is_valid_ticker("035420") is True  # NAVER

    def test_is_valid_ticker_elw(self):
        """ELW 종목 코드 검증 (6자리 숫자+알파벳)"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("0015N0") is True  # 아로마티카 ELW
        assert manager._is_valid_ticker("0004V0") is True  # 엔비알모션 ELW
        assert manager._is_valid_ticker("0120X0") is True  # 유진챔피언 ELW

    def test_is_valid_ticker_elw_with_digits(self):
        """숫자만 포함된 ELW 종목 코드 (isdigit() 통과하지만 ELW)"""
        manager = ConnectionManager()
        # 숫자로만 구성된 ELW도 6자리면 통과
        assert manager._is_valid_ticker("493330") is True  # 지에프아이
        assert manager._is_valid_ticker("217590") is True  # 티엠씨
        assert manager._is_valid_ticker("491000") is True  # 리브스메드

    def test_is_valid_ticker_invalid(self):
        """잘못된 종목 코드"""
        manager = ConnectionManager()
        assert manager._is_valid_ticker("12345") is False  # 5자리
        assert manager._is_valid_ticker("1234567") is False  # 7자리
        assert manager._is_valid_ticker("ABCDEF") is False  # 알파벳만
        assert manager._is_valid_ticker("") is False  # 빈 문자열
        assert manager._is_valid_ticker(None) is False  # None
        # "12345A"는 유효한 ELW 형식 (6자리, 숫자+알파벳) - 테스트 케이스 제거

    def test_subscribe_elw_ticker(self):
        """ELW 종목 구독 테스트"""
        manager = ConnectionManager()
        client_id = "test_client"

        # ELW 종목 구독
        manager.subscribe(client_id, "price:0015N0")

        # 구독 확인
        assert "price:0015N0" in manager.subscriptions
        assert client_id in manager.subscriptions["price:0015N0"]

    def test_unsubscribe_elw_ticker(self):
        """ELW 종목 구독 취소 테스트"""
        manager = ConnectionManager()
        client_id = "test_client"

        # 구독 후 취소
        manager.subscribe(client_id, "price:0015N0")
        manager.unsubscribe(client_id, "price:0015N0")

        # 구독 제거 확인
        assert "price:0015N0" not in manager.subscriptions


class TestKiwoomWebSocketBridgeELW:
    """KiwoomWebSocketBridge ELW 지원 테스트"""

    def test_is_valid_ticker_kospi(self):
        """KOSPI 종목 코드 검증"""
        bridge = KiwoomWebSocketBridge()
        assert bridge._is_valid_ticker("005930") is True
        assert bridge._is_valid_ticker("000660") is True

    def test_is_valid_ticker_elw(self):
        """ELW 종목 코드 검증"""
        bridge = KiwoomWebSocketBridge()
        assert bridge._is_valid_ticker("0015N0") is True
        assert bridge._is_valid_ticker("0004V0") is True

    def test_is_valid_ticker_invalid(self):
        """잘못된 종목 코드"""
        bridge = KiwoomWebSocketBridge()
        assert bridge._is_valid_ticker("12345") is False
        assert bridge._is_valid_ticker("ABCDEF") is False

    @pytest.mark.asyncio
    async def test_add_elw_ticker(self):
        """ELW 종목 추가 테스트"""
        bridge = KiwoomWebSocketBridge()

        # ELW 종목 추가
        result = await bridge.add_ticker("0015N0")
        assert result is True
        assert "0015N0" in bridge.get_active_tickers()

    @pytest.mark.asyncio
    async def test_add_invalid_ticker(self):
        """잘못된 종목 코드 추가 거부 테스트"""
        bridge = KiwoomWebSocketBridge()

        # 잘못된 종목 코드
        result = await bridge.add_ticker("12345")
        assert result is False
        assert "12345" not in bridge.get_active_tickers()

    @pytest.mark.asyncio
    async def test_remove_elw_ticker(self):
        """ELW 종목 제거 테스트"""
        bridge = KiwoomWebSocketBridge()

        # 추가 후 제거
        await bridge.add_ticker("0015N0")
        await bridge.remove_ticker("0015N0")

        assert "0015N0" not in bridge.get_active_tickers()
