"""
키움 REST API 기반 인터페이스 정의

KOA (Windows COM) 기반 인터페이스를 REST API 기반으로 재정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class KiwoomEventType(Enum):
    """키움 이벤트 타입"""
    # 실시간 시세
    RECEIVE_REAL_DATA = "OnReceiveRealData"          # 실시간 체결가
    RECEIVE_MT_REAL_DATA = "OnReceiveMTRealData"     # 실시간 호가

    # WebSocket 이벤트
    WS_CONNECTED = "WebSocketConnected"              # WebSocket 연결 완료
    WS_DISCONNECTED = "WebSocketDisconnected"        # WebSocket 연결 해제
    WS_LOGIN_SUCCESS = "WebSocketLoginSuccess"        # WebSocket 로그인 성공
    WS_LOGIN_FAILED = "WebSocketLoginFailed"          # WebSocket 로그인 실패

    # 연결 상태
    API_TOKEN_EXPIRED = "APITokenExpired"            # API 토큰 만료
    API_TOKEN_REFRESHED = "APITokenRefreshed"        # API 토큰 갱신됨


@dataclass
class RealtimePrice:
    """실시간 체결가 데이터"""
    ticker: str
    price: float           # 체결가
    change: float          # 전일대비
    change_rate: float     # 등락률 (%)
    volume: int            # 누적거래량
    bid_price: float       # 매수호가
    ask_price: float       # 매도호가
    timestamp: str         # 수신 시간 (ISO 8601)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "change": self.change,
            "change_rate": self.change_rate,
            "volume": self.volume,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "timestamp": self.timestamp,
        }


@dataclass
class OrderBook:
    """호가 데이터"""
    ticker: str
    bids: List[tuple]      # 매수호가 [(가격, 수량), ...]
    asks: List[tuple]      # 매도호가 [(가격, 수량), ...]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "ticker": self.ticker,
            "bids": self.bids,
            "asks": self.asks,
            "timestamp": self.timestamp,
        }


@dataclass
class KiwoomConfig:
    """키움 API 설정"""
    # API 키
    app_key: str
    secret_key: str

    # 서버 URL
    base_url: str           # 실전: https://api.kiwoom.com
    ws_url: str             # wss://api.kiwoom.com:10000/api/dostk/websocket

    # 모드 설정
    use_mock: bool = False   # Mock 모드 여부
    debug_mode: bool = False

    # WebSocket 설정
    ws_ping_interval: Optional[int] = None
    ws_ping_timeout: Optional[int] = None
    ws_recv_timeout: int = 60

    @classmethod
    def from_env(cls) -> 'KiwoomConfig':
        """환경변수에서 설정 로드"""
        import os
        from dotenv import load_dotenv

        load_dotenv()

        use_mock = os.getenv("USE_MOCK", "false").lower() == "true"

        if use_mock:
            app_key = os.getenv("KIWOOM_MOCK_APP_KEY")
            secret_key = os.getenv("KIWOOM_MOCK_SECRET_KEY")
            base_url = "https://mockapi.kiwoom.com"
        else:
            app_key = os.getenv("KIWOOM_APP_KEY")
            secret_key = os.getenv("KIWOOM_SECRET_KEY")
            base_url = "https://api.kiwoom.com"

        if not app_key or not secret_key:
            raise ValueError("키움 API KEY가 설정되지 않았습니다")

        return cls(
            app_key=app_key,
            secret_key=secret_key,
            base_url=base_url,
            ws_url=f"{base_url.replace('https', 'wss')}:10000/api/dostk/websocket",
            use_mock=use_mock,
            debug_mode=os.getenv("DEBUG", "false").lower() == "true",
            ws_ping_interval=None,
            ws_ping_timeout=None,
            ws_recv_timeout=int(os.getenv("WS_RECV_TIMEOUT", "60")),
        )


class IKiwoomBridge(ABC):
    """
    키움 브리지 인터페이스

    REST API와 WebSocket을 통합한 추상화 계층입니다.
    """

    @abstractmethod
    async def connect(self, access_token: Optional[str] = None) -> bool:
        """
        키움 API 연결

        Args:
            access_token: OAuth2 액세스 토큰 (실제 WebSocket의 경우 필요)

        Returns:
            연결 성공 여부
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """연결 해제"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        pass

    @abstractmethod
    def has_valid_token(self) -> bool:
        """유효한 토큰 보유 여부"""
        pass

    @abstractmethod
    async def refresh_token(self) -> bool:
        """토큰 갱신"""
        pass

    @abstractmethod
    def register_event(self, event_type: KiwoomEventType, callback: Callable) -> None:
        """
        이벤트 핸들러 등록

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        pass

    @abstractmethod
    def unregister_event(self, event_type: KiwoomEventType, callback: Callable) -> None:
        """이벤트 핸들러 해제"""
        pass

    @abstractmethod
    async def subscribe_realtime(
        self,
        ticker: str
    ) -> bool:
        """
        실시간 시세 등록

        Args:
            ticker: 종목코드 (6자리)

        Returns:
            등록 성공 여부
        """
        pass

    @abstractmethod
    async def unsubscribe_realtime(self, ticker: str) -> bool:
        """
        실시간 시세 해제

        Args:
            ticker: 종목코드

        Returns:
            해제 성공 여부
        """
        pass

    @abstractmethod
    def get_subscribe_list(self) -> List[str]:
        """현재 등록된 실시간 시세 종목 리스트"""
        pass

    @abstractmethod
    async def get_current_price(self, ticker: str) -> Optional[RealtimePrice]:
        """
        현재가 조회

        Args:
            ticker: 종목코드

        Returns:
            현재가 정보 또는 None
        """
        pass
