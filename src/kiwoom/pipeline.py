"""
키움 Pipeline Manager 구현

REST API + WebSocket + Redis를 통합한 파이프라인 관리자입니다.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

from src.kiwoom.base import (
    KiwoomConfig,
    IKiwoomBridge,
)
from src.kiwoom.mock import MockKiwoomBridge
from src.kiwoom.websocket import KiwoomWebSocket
from src.kiwoom.service import KiwoomRealtimeService


logger = logging.getLogger(__name__)


class KiwoomPipelineManager:
    """
    키움 Pipeline Manager

    KOA 파이프라인과 호환되는 인터페이스로
    REST API + WebSocket + Redis를 통합 관리합니다.
    """

    def __init__(
        self,
        config: Optional[KiwoomConfig] = None,
        bridge: Optional[IKiwoomBridge] = None,
        redis_client: Optional[Any] = None,
        auto_start: bool = False,
    ):
        """
        초기화

        Args:
            config: 키움 API 설정 (bridge 없을 때 사용)
            bridge: Kiwoom Bridge 인스턴스 (선택)
            redis_client: Redis 클라이언트 (선택)
            auto_start: 생성 후 자동 시작 여부
        """
        self._config = config

        if bridge is not None:
            # 외부에서 제공된 Bridge가 있으면 Service에 포함
            self._service = KiwoomRealtimeService(bridge, redis_client)
        elif config is not None:
            # Config에서 Service 생성 (from_config 사용하여 REST API도 생성)
            logger.info("Creating KiwoomRealtimeService from config")
            self._service = KiwoomRealtimeService.from_config(config)
            # Redis 클라이언트 설정
            if redis_client:
                self._service._redis_client = redis_client
        else:
            raise ValueError("config 또는 bridge 중 하나는 필수입니다.")

        self._running = False
        self._auto_start = auto_start

        # 자동 시작
        if auto_start:
            asyncio.create_task(self._auto_start_async())

    @property
    def _bridge(self) -> IKiwoomBridge:
        """Bridge 인스턴스 (Service의 Bridge 접근)"""
        return self._service._bridge

    async def _auto_start_async(self) -> None:
        """비동기 자동 시작"""
        await asyncio.sleep(0)
        try:
            await self.start()
        except Exception as e:
            logger.error(f"Auto-start failed: {e}")

    # ==================== 라이프사이클 관리 ====================

    async def start(self) -> None:
        """
        Pipeline 시작

        Service를 시작합니다.
        """
        if self._running:
            logger.warning("Pipeline already running")
            return

        await self._service.start()
        self._running = True
        # Service의 내부 상태도 동기화
        self._service._running = True
        logger.info("Kiwoom Pipeline Manager started")

    async def stop(self) -> None:
        """
        Pipeline 중지

        Service를 중지합니다.
        """
        if not self._running:
            return

        await self._service.stop()
        self._running = False
        # Service의 내부 상태도 동기화
        self._service._running = False
        logger.info("Kiwoom Pipeline Manager stopped")

    def is_running(self) -> bool:
        """Pipeline 실행 상태 확인"""
        return self._running

    # ==================== 구독 관리 ====================

    async def subscribe(self, ticker: str) -> bool:
        """
        종목 구독

        Args:
            ticker: 종목코드 (6자리)

        Returns:
            구독 성공 여부
        """
        if not self._running:
            logger.warning("Cannot subscribe: pipeline not running")
            return False
        return await self._service.subscribe(ticker)

    async def subscribe_many(self, tickers: List[str]) -> List[bool]:
        """
        여러 종목 구독

        Args:
            tickers: 종목코드 리스트

        Returns:
            각 종목별 구독 결과 리스트
        """
        return await self._service.subscribe_many(tickers)

    async def unsubscribe(self, ticker: str) -> bool:
        """
        종목 구독 해제

        Args:
            ticker: 종목코드

        Returns:
            해제 성공 여부
        """
        return await self._service.unsubscribe(ticker)

    def get_subscribed_tickers(self) -> List[str]:
        """현재 구독 중인 종목 리스트"""
        return self._service.get_subscribed_tickers()

    # ==================== 이벤트 핸들러 관리 ====================

    def register_event_handler(
        self,
        event_type,
        callback,
    ) -> None:
        """
        이벤트 핸들러 등록

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        self._service.register_event_handler(event_type, callback)

    def unregister_event_handler(
        self,
        event_type,
        callback,
    ) -> None:
        """
        이벤트 핸들러 해제

        Args:
            event_type: 이벤트 타입
            callback: 콜백 함수
        """
        self._service.unregister_event_handler(event_type, callback)

    # ==================== Health Check ====================

    def health_check(self) -> Dict[str, Any]:
        """
        Health Check

        Returns:
            상태 정보 딕셔너리
        """
        if not self._running:
            return {
                "status": "stopped",
                "connected": False,
                "has_token": False,
                "subscribed_count": 0,
            }

        status = self._service.get_status()

        # 상태 판정
        if status["connected"] and status["has_token"]:
            health_status = "healthy"
        else:
            health_status = "unhealthy"

        return {
            "status": health_status,
            "connected": status["connected"],
            "has_token": status["has_token"],
            "subscribed_count": status["subscribed_count"],
        }

    # ==================== KOA 호환 인터페이스 ====================

    async def add_ticker(self, ticker: str) -> bool:
        """KOA 호환: 종목 추가 (구독)"""
        return await self.subscribe(ticker)

    async def remove_ticker(self, ticker: str) -> bool:
        """KOA 호환: 종목 제거 (구독 해제)"""
        return await self.unsubscribe(ticker)

    def get_tickers(self) -> List[str]:
        """KOA 호환: 구독 종목 리스트"""
        return self.get_subscribed_tickers()
