"""
키움 WebSocket 클라이언트 (실전 트레이딩 프로토콜)

키움증권 REST API WebSocket을 통한 실시간 시세 데이터 수신
참조: https://github.com/ralph0830/kiwoom_stock_telegram
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosed

from src.kiwoom.base import (
    KiwoomConfig,
    KiwoomEventType,
    RealtimePrice,
    IKiwoomBridge
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class KiwoomWebSocket(IKiwoomBridge):
    """
    키움 WebSocket 클라이언트 (실전 트레이딩)

    키움증권 REST API WebSocket 프로토콜을 사용하여 실시간 시세를 수신합니다.
    """

    # 실시간 데이터 타입
    TYPE_STOCK_QUOTE = "0A"  # 주식기세 (체결없이 가격변경)
    TYPE_STOCK_TRADE = "0B"  # 주식체결 (실제 체결)

    # 기본 설정
    DEFAULT_PING_INTERVAL = None  # 키움은 ping/pong을 지원하지 않음 (서버가 PING 전송)
    DEFAULT_PING_TIMEOUT = None
    DEFAULT_RECV_TIMEOUT = 60  # 60초 타임아웃
    DEFAULT_MAX_RECONNECT_ATTEMPTS = 5
    DEFAULT_RECONNECT_DELAY = 2.0

    def __init__(self, config: KiwoomConfig, debug_mode: bool = False):
        """
        초기화

        Args:
            config: 키움 API 설정
            debug_mode: 디버그 모드 (상세 로그 출력)
        """
        self._config = config
        self._debug_mode = debug_mode

        # 연결 상태
        self._connected: bool = False
        self._authenticated: bool = False
        self._ws: Optional[Any] = None

        # 액세스 토큰
        self._access_token: Optional[str] = None

        # 구독 관리
        self._subscribed_tickers: Set[str] = set()

        # 이벤트 핸들러
        self._event_handlers: Dict[KiwoomEventType, List[Callable]] = {}

        # 현재가 캐시
        self._current_prices: Dict[str, RealtimePrice] = {}

        # 재연결 설정
        self._max_reconnect_attempts = self.DEFAULT_MAX_RECONNECT_ATTEMPTS
        self._reconnect_delay = self.DEFAULT_RECONNECT_DELAY
        self._reconnect_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

        # 종료 플래그
        self._stop_requested = False

        # WebSocket 타임아웃 설정
        self._ws_ping_interval = config.ws_ping_interval or self.DEFAULT_PING_INTERVAL
        self._ws_ping_timeout = config.ws_ping_timeout or self.DEFAULT_PING_TIMEOUT
        self._ws_recv_timeout = config.ws_recv_timeout or self.DEFAULT_RECV_TIMEOUT

    async def connect(self, access_token: Optional[str] = None) -> bool:
        """
        WebSocket 연결 및 로그인 (키움 프로토콜)

        Args:
            access_token: OAuth2 액세스 토큰 (없으면 REST API에서 발급)

        Returns:
            연결 성공 여부
        """
        if self._connected:
            logger.warning("WebSocket already connected")
            return True

        self._stop_requested = False

        # 액세스 토큰이 없으면 REST API에서 발급 시도
        if access_token is None:
            from src.kiwoom.rest_api import KiwoomRestAPI
            rest_api = KiwoomRestAPI(self._config)
            try:
                await rest_api.issue_token()
                access_token = rest_api._access_token
                logger.info("Token obtained from REST API")
            except Exception as e:
                logger.warning(f"Failed to get token from REST API: {e}")
                logger.warning("Attempting WebSocket connection without token (may fail)")
                # 토큰 없이 연결 시도 - WebSocket 서버에서 에러 반환 확인용

        self._access_token = access_token

        try:
            logger.info(f"Connecting to Kiwoom WebSocket: {self._config.ws_url}")

            # 키움 WebSocket 연결 (인증 헤더 없이 연결, 로그인 패킷으로 인증)
            self._ws = await websockets.connect(
                self._config.ws_url,
                ping_interval=self._ws_ping_interval,  # None: 클라이언트 자동 ping 비활성화
                ping_timeout=self._ws_ping_timeout,
                close_timeout=self._ws_recv_timeout,
            )

            logger.info("WebSocket connection established")

            # 키움 로그인 전문 전송 (trnm 형식)
            # 토큰이 없으면 빈 문자열로 전송 (서버에서 에러 반환 확인용)
            login_message = {
                "trnm": "LOGIN",
                "token": access_token or ""
            }
            await self._ws.send(json.dumps(login_message))
            logger.debug("Login request sent (trnm: LOGIN)")

            # 로그인 응답 대기
            response = await asyncio.wait_for(
                self._ws.recv(),
                timeout=5.0
            )

            data = json.loads(response)
            logger.debug(f"Login response: {data}")

            # 로그인 성공 확인 (return_code == 0)
            if data.get("return_code") == 0:
                self._connected = True
                self._authenticated = True

                # WS 연결 완료 이벤트 발생
                self._emit_event(KiwoomEventType.WS_CONNECTED, {"token": self._access_token})

                logger.info("Kiwoom WebSocket login successful")

                # 메시지 수신 루프 시작
                self._receive_task = asyncio.create_task(self._receive_loop())

                return True
            else:
                logger.error(f"Login failed: {data.get('return_msg', 'Unknown error')}")
                return False

        except asyncio.TimeoutError:
            logger.error("WebSocket connection timeout")
            return False
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """연결 해제"""
        if not self._connected:
            return

        self._stop_requested = True
        self._connected = False
        self._authenticated = False

        # 수신 태스크 취소
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # WebSocket 연결 종료
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")

        # WS 연결 해제 이벤트 발생
        self._emit_event(KiwoomEventType.WS_DISCONNECTED, {})

        logger.info("WebSocket disconnected")

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected

    def has_valid_token(self) -> bool:
        """유효한 토큰 보유 여부"""
        return self._authenticated and self._access_token is not None

    async def refresh_token(self) -> bool:
        """
        토큰 갱신 (WebSocket은 재연결로 처리)

        Returns:
            갱신 성공 여부
        """
        # WebSocket은 토큰 만료 시 재연결을 통해 토큰 재발급
        if self._access_token is None:
            return False

        try:
            # 기존 연결 종료
            if self._connected:
                await self.disconnect()

            # 재연결 (새 토큰 발급됨)
            return await self.connect()

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False

    def register_event(self, event_type: KiwoomEventType, callback: Callable) -> None:
        """
        이벤트 핸들러 등록

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(callback)

    def unregister_event(self, event_type: KiwoomEventType, callback: Callable) -> None:
        """
        이벤트 핸들러 해제

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        if event_type in self._event_handlers:
            if callback in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(callback)

    async def subscribe_realtime(self, ticker: str) -> bool:
        """
        실시간 시세 등록 (키움 프로토콜)

        Args:
            ticker: 종목코드 (6자리)

        Returns:
            등록 성공 여부
        """
        if not self._connected or not self._authenticated:
            logger.warning("Cannot subscribe: not connected or authenticated")
            return False

        try:
            # 키움 실시간 시세 등록 전문 (trnm: REG)
            # 0A: 주식기세 (가격변동, 체결없이), 0B: 주식체결
            reg_request = {
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",  # 기존 유지
                "data": [{
                    "item": [ticker],
                    "type": [self.TYPE_STOCK_QUOTE, self.TYPE_STOCK_TRADE]
                }]
            }
            await self._ws.send(json.dumps(reg_request))

            self._subscribed_tickers.add(ticker)
            logger.info(f"Subscribed to real-time data: {ticker} (types: 0A, 0B)")
            return True

        except Exception as e:
            logger.error(f"Subscribe failed for {ticker}: {e}")
            return False

    async def unsubscribe_realtime(self, ticker: str) -> bool:
        """
        실시간 시세 해제 (키움 프로토콜)

        Args:
            ticker: 종목코드

        Returns:
            해제 성공 여부
        """
        if not self._connected:
            return False

        try:
            # 키움 실시간 시세 해제 전문 (trnm: REMOVE)
            unreg_request = {
                "trnm": "REMOVE",
                "grp_no": "1",
                "data": [{
                    "item": [ticker],
                    "type": [self.TYPE_STOCK_QUOTE, self.TYPE_STOCK_TRADE]
                }]
            }
            await self._ws.send(json.dumps(unreg_request))

            self._subscribed_tickers.discard(ticker)
            logger.info(f"Unsubscribed from real-time data: {ticker}")
            return True

        except Exception as e:
            logger.error(f"Unsubscribe failed for {ticker}: {e}")
            return False

    def get_subscribe_list(self) -> List[str]:
        """현재 등록된 실시간 시세 종목 리스트"""
        return list(self._subscribed_tickers)

    async def get_current_price(self, ticker: str) -> Optional[RealtimePrice]:
        """
        현재가 조회

        Args:
            ticker: 종목코드

        Returns:
            현재가 정보 또는 None
        """
        return self._current_prices.get(ticker)

    # ==================== 내부 메서드 ====================

    def _emit_event(self, event_type: KiwoomEventType, data: Any) -> None:
        """
        이벤트 발생

        Args:
            event_type: 이벤트 타입
            data: 이벤트 데이터
        """
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    result = handler(data)
                    # coroutine인 경우 asyncio.create_task로 스케줄링
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

    async def _receive_loop(self) -> None:
        """
        메시지 수신 루프 (자동 재연결 지원)
        """
        reconnect_delay = self._reconnect_delay

        while not self._stop_requested:
            try:
                # 연결된 상태에서만 메시지 수신
                while self._connected and not self._stop_requested:
                    try:
                        # 타임아웃 설정하여 메시지 대기
                        message = await asyncio.wait_for(
                            self._ws.recv(),
                            timeout=float(self._ws_recv_timeout)
                        )
                        await self._handle_message(message)

                    except asyncio.TimeoutError:
                        # 타임아웃 시에도 연결 유지 (정상 동작)
                        if self._debug_mode:
                            logger.debug("WebSocket receive timeout (waiting for message)")
                        continue

                    except ConnectionClosed as e:
                        logger.warning(f"WebSocket connection closed (code: {e.code})")
                        self._connected = False
                        break

                    except Exception as e:
                        logger.error(f"Error in receive loop: {e}")
                        self._connected = False
                        break

                # 연결이 끊기고 재연결 시도
                if not self._stop_requested and not self._connected:
                    logger.info(f"Connection lost, attempting reconnect in {reconnect_delay}s...")
                    await asyncio.sleep(reconnect_delay)

                    # 기존 콜백/구독 정보 백업
                    saved_tickers = self._subscribed_tickers.copy()

                    # 재연결 시도
                    if await self._reconnect():
                        # 종목 재등록
                        for ticker in saved_tickers:
                            await self.subscribe_realtime(ticker)
                        logger.info("Reconnection and subscription restoration complete")

            except Exception as e:
                logger.error(f"Fatal error in receive loop: {e}")
                self._connected = False

            # 종료 요청이 있으면 루프 종료
            if self._stop_requested:
                break

    async def _reconnect(self) -> bool:
        """
        재연결 시도

        Returns:
            재연결 성공 여부
        """
        if not self._access_token:
            logger.error("Cannot reconnect: no access token")
            return False

        try:
            # 이전 연결 정리
            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass

            self._connected = False
            self._authenticated = False

            # 재연결
            return await self.connect(self._access_token)

        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    async def _handle_message(self, message: str) -> None:
        """
        수신 메시지 처리 (키움 프로토콜)

        Args:
            message: JSON 메시지
        """
        try:
            data = json.loads(message)
            trnm = data.get("trnm", "")

            # PING 메시지 처리 (서버 heartbeat)
            if trnm == "PING":
                # PING을 그대로 돌려보내서 연결 유지
                await self._ws.send(message)
                if self._debug_mode:
                    logger.debug("PING response sent (connection keep-alive)")
                return

            # 실시간 데이터 (trnm: REAL)
            if trnm == "REAL":
                await self._on_receive_real_data(data)
                return

            # SYSTEM 메시지 처리 (연결 종료 등)
            if trnm == "SYSTEM":
                code = data.get("code")
                msg = data.get("message", "")
                logger.warning(f"SYSTEM message: [{code}] {msg}")

                # R10001: 중복 접속 - 연결 종료
                if code == "R10001":
                    logger.warning("Duplicate connection detected - closing connection")
                    self._connected = False
                return

            # 로그인 응답 (재연결 시)
            if trnm == "LOGIN":
                if data.get("return_code") == 0:
                    self._authenticated = True
                    logger.info("Re-authenticated successfully")
                return

            # 기타 메시지
            if self._debug_mode:
                logger.debug(f"Other WebSocket message: {trnm}, data: {data}")

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _on_receive_real_data(self, data: Dict[str, Any]) -> None:
        """
        실시간 체결가 수신 처리 (키움 0B TR 프로토콜)

        0B TR (주식체결) 필드:
        - 10: 현재가 (음수는 하락)
        - 11: 전일대비 (가격 차이)
        - 12: 등락율 (%)
        - 13: 누적거래량
        - 15: 거래량 (+는 매수체결, -는 매도체결)
        - 20: 체결시간 (HHMMSS)
        - 27: (최우선)매도호가
        - 28: (최우선)매수호가

        Args:
            data: TR 데이터 (trnm: REAL)
        """
        try:
            data_list = data.get("data", [])

            for item in data_list:
                type_code = item.get("type")  # 0A (주식기세) 또는 0B (주식체결)
                ticker = item.get("item")  # 종목코드
                values = item.get("values", {})  # 실시간 데이터 값

                # 0A 또는 0B만 처리
                if type_code not in [self.TYPE_STOCK_QUOTE, self.TYPE_STOCK_TRADE]:
                    continue

                if not values:
                    continue

                # 현재가 (10번 필드) - +/- 기호가 포함될 수 있음
                current_price_str = values.get("10", "0")
                # +/- 기호와 공백 제거
                current_price_str = current_price_str.replace("+", "").replace("-", "").replace(" ", "")
                current_price = float(current_price_str) if current_price_str else 0

                # 전일대비 (11번 필드)
                # 전일대비 (11번 필드) - 부호 유지 (+는 제거, -는 유지)
                change_str = values.get("11", "0")
                change_str = change_str.replace("+", "").replace(" ", "")
                change = float(change_str) if change_str else 0

                # 등락율 (12번 필드) - 이미 %로 계산됨, 부호 유지
                change_rate_str = values.get("12", "0")
                change_rate_str = change_rate_str.replace("+", "").replace(" ", "")
                change_rate = float(change_rate_str) if change_rate_str else 0

                # 누적거래량 (13번 필드)
                cumulative_volume_str = values.get("13", "0")
                cumulative_volume = int(cumulative_volume_str) if cumulative_volume_str.isdigit() else 0

                # 거래량 (15번 필드) - +는 매수체결, -는 매도체결
                volume_str = values.get("15", "0")
                volume = int(volume_str) if volume_str.lstrip("+-").isdigit() else 0

                # 호가 (27: 매도호가, 28: 매수호가)
                bid_price_str = values.get("28", "0")  # 매수호가 (bid)
                bid_price_str = bid_price_str.replace("+", "").replace("-", "").replace(" ", "")
                bid_price = float(bid_price_str) if bid_price_str else 0

                ask_price_str = values.get("27", "0")  # 매도호가 (ask)
                ask_price_str = ask_price_str.replace("+", "").replace("-", "").replace(" ", "")
                ask_price = float(ask_price_str) if ask_price_str else 0

                if current_price > 0:
                    price_data = RealtimePrice(
                        ticker=ticker,
                        price=current_price,
                        change=change,
                        change_rate=change_rate,
                        volume=cumulative_volume,  # 누적거래량 사용
                        bid_price=bid_price,
                        ask_price=ask_price,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )

                    # 캐시 저장
                    self._current_prices[ticker] = price_data

                    # 이벤트 발생
                    self._emit_event(KiwoomEventType.RECEIVE_REAL_DATA, price_data)

                    if self._debug_mode:
                        logger.info(
                            f"Real-time [{type_code}] {ticker}: {current_price:,}원 "
                            f"({change:+,}원, {change_rate:+.2f}%) "
                            f"매수:{bid_price:,} / 매도:{ask_price:,}"
                        )

        except Exception as e:
            logger.error(f"Error processing real data: {e}, data: {data}")
