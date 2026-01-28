"""
Windows 키움증권 KOA 브리지

pywin32를 통해 Windows COM으로 키움 OpenAPI와 통신합니다.
Windows 환경에서만 작동합니다.
"""

from typing import Optional, List, Dict, Any

try:
    import win32com.client as win32_client
    from pythoncom import CoInitialize, CoUninitialize
    import pythoncom
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    win32_client = None
    pythoncom = None

from src.koa.base import (
    KOABaseBridge,
    KOAEventType
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# KOA 실시간 FID 설정
# https://developer.kiwoom.com/docs/docs/realtime.html 참조
REALTIME_FIDS = {
    "체결가": "10",     # 현재가
    "전일대비": "11",   # 전일비
    "등락률": "12",     # 등락률
    "거래량": "13",     # 누적거래량
    "매수호가": "14",   # 매수1호가
    "매도호가": "15",   # 매도1호가
}


class WindowsKOABridge(KOABaseBridge):
    """
    Windows 키움증권 KOA 브리지

    pywin32 COM을 통해 실제 키움 HTS와 통신합니다.
    Windows 환경에서 키움 OpenAPI+가 설치되어 있어야 합니다.
    """

    def __init__(self):
        super().__init__()
        self._kiwoom = None  # Kiwoom COM 객체
        self._event_loop = None  # 이벤트 루프 (백그라운드 스레드)
        self._event_thread = None
        self._script_object = None  # 스크립트 객체 (명령 실행)

        if not WINDOWS_AVAILABLE:
            logger.error("Windows COM not available. "
                           "Windows environment with pywin32 required.")

    def connect(self) -> bool:
        """
        키움 HTS 연결

        Returns:
            연결 성공 여부
        """
        if not WINDOWS_AVAILABLE:
            logger.error("Windows not available")
            return False

        try:
            # COM 초기화
            CoInitialize()

            # Kiwoom COM 객체 생성
            self._kiwoom = win32_client.Dispatch("KHOPENAPI.KHOpenAPICtrl")
            logger.info("Kiwoom COM object created")

            # 연결 상태 확인
            if self._is_connected():
                self._connected = True
                self._start_event_loop()
                logger.info("Windows KOA Bridge connected")
                return True
            else:
                logger.error("Kiwoom not connected")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Kiwoom: {e}")
            return False

    def disconnect(self) -> None:
        """연결 해제"""
        self._running = False

        # 이벤트 루프 중지
        if self._event_loop:
            self._event_loop = None

        # 스크립트 객체 해제
        if self._script_object:
            try:
                # 모든 실시간 등록 해제
                for ticker in list(self._subscribed_tickers):
                    try:
                        self._kiwoom.DisconnectRealData(ticker)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error cleaning up: {e}")

        # COM 객체 해제
        if self._kiwoom:
            try:
                # 로그아웃 (필요시)
                # self._kiwoom.CommConnect(0)  # 0: 로그아웃
                pass
            except Exception:
                pass

        # COM 정리
        try:
            CoUninitialize()
        except Exception:
            pass

        self._connected = False
        self._logged_in = False
        logger.info("Windows KOA Bridge disconnected")

    def login(
        self,
        user_id: str,
        password: str,
        cert_passwd: str = ""
    ) -> bool:
        """
        로그인

        Args:
            user_id: 사용자 ID
            password: 비밀번호
            cert_passwd: 공인인증서 비밀번호

        Returns:
            로그인 성공 여부
        """
        if not self._connected or not self._kiwoom:
            logger.warning("Not connected to Kiwoom")
            return False

        try:
            # 로그인 요청
            # CommConnect(arg1, arg2, arg3, arg4, arg5)
            # arg1: 0 - 로그인, 1 - 로그아웃
            # arg2: 계좌번호 (선택 사항, ""이면 전체)
            # arg3: 비밀번호
            # arg4: 공인인증서 비밀번호 (선택 사항)
            # arg5: 0 - 사용자 입력 대기, 1 - 자동 입력 사용

            result = self._kiwoom.CommConnect(
                0,           # 로그인 모드
                "",          # 전체 계좌
                password,    # 비밀번호
                cert_passwd,  # 공인인증서 비밀번호
                0            # 자동 입력 사용
            )

            # 결과 확인 (0: 성공, 음수: 실패)
            if result == 0:
                self._logged_in = True
                logger.info(f"Kiwoom login successful: {user_id}")
                return True
            else:
                logger.error(f"Kiwoom login failed: result code {result}")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def subscribe_realtime(
        self,
        ticker: str,
        fid_list: Optional[List[str]] = None
    ) -> bool:
        """
        실시간 시세 등록

        Args:
            ticker: 종목코드
            fid_list: 조회할 FID 리스트

        Returns:
            등록 성공 여부
        """
        if not self._logged_in or not self._kiwoom:
            logger.warning("Not logged in")
            return False

        ticker = ticker.zfill(6)

        try:
            # FID 리스트 생성 (기본값 사용)
            if fid_list is None:
                fid_list = ["체결가", "전일대비", "등락률", "거래량",
                             "매수호가", "매도호가"]

            # FID 번호 매핑
            fid_numbers = [REALTIME_FIDS.get(name, "") for name in fid_list
                          if REALTIME_FIDS.get(name, "")]
            fid_str = ";".join(fid_numbers)

            # 실시간 시세 등록
            # SetRealReg(screen_no, code_list, fid_list, opt_type)
            # screen_no: 화면 번호 (0: 미사용)
            # code_list: 종목코드 리스트
            # fid_list: FID 리스트 (세미콜론 구분)
            # opt_type: 0: 실시간, 1: 연속

            result = self._kiwoom.SetRealReg(
                0,           # 화면 번호
                ticker,      # 종목코드
                fid_str,     # FID 리스트
                "0"          # 실시간
            )

            if result == 0:  # 성공
                self._subscribed_tickers.add(ticker)
                logger.info(f"Realtime subscription successful: {ticker}")
                return True
            else:
                logger.error(f"Realtime subscription failed: {ticker}, "
                           f"result code: {result}")
                return False

        except Exception as e:
            logger.error(f"Error subscribing to {ticker}: {e}")
            return False

    def unsubscribe_realtime(self, ticker: str) -> bool:
        """실시간 시레 해제"""
        ticker = ticker.zfill(6)

        if ticker not in self._subscribed_tickers:
            return True

        try:
            result = self._kiwoom.DisconnectRealData(ticker)

            if result == 0:
                self._subscribed_tickers.discard(ticker)
                logger.info(f"Realtime unsubscription successful: {ticker}")
                return True
            else:
                logger.error(f"Realtime unsubscription failed: {ticker}")
                return False

        except Exception as e:
            logger.error(f"Error unsubscribing {ticker}: {e}")
            return False

    def request_market_state(self) -> Optional[Dict[str, Any]]:
        """장 운영 상태 조회"""
        if not self._kiwoom:
            return None

        try:
            # GetMasterCodeInfo(): 마스터 코드 정보
            # 0: 장 운영 상태
            # 0x00: before opening, 0x01: market opening, 0x02: market close

            market_status = self._kiwoom.GetMasterCodeInfo(0)  # 장 운영 상태
            remaining_time = self._kiwoom.GetMasterCodeInfo(1)  # 종료까지 남은 시간

            status_map = {
                0x00: "BEFORE_OPEN",
                0x01: "OPEN",
                0x02: "CLOSE",
            }

            return {
                "market_status": status_map.get(market_status, "UNKNOWN"),
                "remaining_time": remaining_time,
                "is_trading": market_status == 0x01,
            }

        except Exception as e:
            logger.error(f"Error getting market state: {e}")
            return None

    def _is_connected(self) -> bool:
        """연결 상태 확인"""
        try:
            if self._kiwoom:
                # GetConnectState(): 0: 미연결, 1: 연결 완료
                return self._kiwoom.GetConnectState() == 1
            return False
        except Exception:
            return False

    def _start_event_loop(self) -> None:
        """
        이벤트 루프 시작

        백그라운드 스레드에서 KOA 이벤트를 수신합니다.
        """
        import threading

        def event_loop():
            """이벤트 처리 루프"""
            # COM 스레드 초기화
            CoInitialize()

            try:
                while self._running:
                    # 이벤트 대기 (0.1초)
                    pythoncom.PumpWaitingMessages()

                    # KOA 이벤트 처리
                    # 실제 구현에서는 OnReceiveRealData 등의 이벤트 핸들러가
                    # 자동으로 호출되도록 COM 객체 설정 필요
                    # 여기서는 간단한 구현만 합니다

            except Exception as e:
                logger.error(f"Event loop error: {e}")
            finally:
                CoUninitialize()

        self._event_thread = threading.Thread(
            target=event_loop,
            daemon=True,
            name="KOA_EventLoop"
        )
        self._event_thread.start()
        logger.info("KOA event loop started")

    def _emit_event(self, event_type: KOAEventType, *args, **kwargs) -> None:
        """
        이벤트 발생

        KOA에서 받은 이벤트를 등록된 핸들러들에게 전달합니다.
        """
        if event_type in self._event_handlers:
            for callback in self._event_handlers[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler {event_type}: {e}")

    def is_connected(self) -> bool:
        """연결 상태"""
        return self._connected and self._is_connected()

    def get_subscribe_list(self) -> List[str]:
        """현재 등록된 실시간 시레 종목 리스트"""
        return list(self._subscribed_tickers)
