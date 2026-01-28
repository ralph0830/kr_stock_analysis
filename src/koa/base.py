"""
키움증권 KOA (Kiwoom Open API) 브리지
Windows COM을 통한 키움 HTS 연동
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class KOAEventType(Enum):
    """KOA 이벤트 타입"""
    # 실시간 시세
    RECEIVE_REAL_DATA = "OnReceiveRealData"          # 실시간 체결가
    RECEIVE_MT_REAL_DATA = "OnReceiveMTRealData"     # 실시간 호가
    RECEIVE_REAL_CONDITION = "OnReceiveRealCondition"  # 실시간 조건

    # 장 정보
    RECEIVE_CR_DATA = "OnReceiveCrData"              # 차트 데이터
    RECEIVE_TR_DATA = "OnReceiveTrData"              # 조회 데이터
    RECEIVE_MSG = "OnReceiveMsg"                     # 메시지

    # 연결 상태
    EVENT_CONNECT = "OnEventConnect"                 # 연결 완료
    RECEIVE_DISCONNECTED = "OnReceiveDisconnected"   # 연결 해제

    # 계좌
    RECEIVE_CHK = "OnReceiveChecksum"                # 체결 확인
    RECEIVE_OCCUR = "OnReceiveOccur"                 # 주문 체결


@dataclass
class RealtimePrice:
    """실시간 체결가 데이터"""
    ticker: str
    price: float           # 체결가
    change: float          # 전일대비
    change_rate: float     # 등락률
    volume: int            # 누적거래량
    bid_price: float       # 매수호가
    ask_price: float       # 매도호가
    timestamp: str         # 수신 시간


@dataclass
class OrderBook:
    """호가 데이터"""
    ticker: str
    bids: List[tuple]      # 매수호가 [(가격, 수량), ...]
    asks: List[tuple]      # 매도호가 [(가격, 수량), ...]
    timestamp: str


class IKOABridge(ABC):
    """
    키움 KOA 브리지 인터페이스

    KOA COM 객체와 Python 간 통신을 추상화합니다.
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        키움 HTS 연결

        Returns:
            연결 성공 여부
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """연결 해제"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        pass

    @abstractmethod
    def login(self, user_id: str, password: str, cert_passwd: str = "") -> bool:
        """
        로그인

        Args:
            user_id: 사용자 ID
            password: 비밀번호
            cert_passwd: 공인인증서 비밀번호 (선택)

        Returns:
            로그인 성공 여부
        """
        pass

    @abstractmethod
    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        pass

    @abstractmethod
    def register_event(self, event_type: KOAEventType, callback: Callable) -> None:
        """
        이벤트 핸들러 등록

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        pass

    @abstractmethod
    def unregister_event(self, event_type: KOAEventType, callback: Callable) -> None:
        """이벤트 핸들러 해제"""
        pass

    @abstractmethod
    def subscribe_realtime(
        self,
        ticker: str,
        fid_list: Optional[List[str]] = None
    ) -> bool:
        """
        실시간 시세 등록

        Args:
            ticker: 종목코드
            fid_list: 조회할 FID 리스트 (None이면 기본값)

        Returns:
            등록 성공 여부
        """
        pass

    @abstractmethod
    def unsubscribe_realtime(self, ticker: str) -> bool:
        """
        실시간 시레 해제

        Args:
            ticker: 종목코드

        Returns:
            해제 성공 여부
        """
        pass

    @abstractmethod
    def get_subscribe_list(self) -> List[str]:
        """현재 등록된 실시간 시레 종목 리스트"""
        pass

    @abstractmethod
    def request_market_state(self) -> Optional[Dict[str, Any]]:
        """
        장 운영 상태 조회

        Returns:
            장 상태 정보
        """
        pass


class KOABaseBridge(IKOABridge):
    """
    KOA 브리지 기본 구현

    실제 KOA COM 객체를 사용하는 구현의 기본 클래스입니다.
    Mock KOA도 이 클래스를 상속하여 구현할 수 있습니다.
    """

    def __init__(self):
        self._connected = False
        self._logged_in = False
        self._subscribed_tickers: set = set()
        self._event_handlers: Dict[KOAEventType, List[Callable]] = {}

    # 연결 상태 관리
    def is_connected(self) -> bool:
        return self._connected

    def is_logged_in(self) -> bool:
        return self._logged_in

    def get_subscribe_list(self) -> List[str]:
        return list(self._subscribed_tickers)

    # 이벤트 핸들러 관리
    def register_event(self, event_type: KOAEventType, callback: Callable) -> None:
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(callback)
        logger.debug(f"Registered event handler: {event_type}")

    def unregister_event(self, event_type: KOAEventType, callback: Callable) -> None:
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(callback)
                logger.debug(f"Unregistered event handler: {event_type}")
            except ValueError:
                pass

    def _emit_event(self, event_type: KOAEventType, *args, **kwargs) -> None:
        """등록된 이벤트 핸들러들 호출"""
        if event_type in self._event_handlers:
            for callback in self._event_handlers[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler {event_type}: {e}")


# 기본 FID 설정 (실시간 체결가)
DEFAULT_REALTIME_FIDS = [
    "체결가",       # 현재가
    "전일대비",     # 전일비
    "등락률",       # 등락률
    "거래량",       # 누적거래량
    "매수호가",     # 매수1호가
    "매도호가",     # 매도1호가
]
