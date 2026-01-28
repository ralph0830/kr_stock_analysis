"""
Graceful Shutdown 유틸리티

애플리케이션이 안전하게 종료되도록 지원합니다.
"""

import asyncio
import signal
import logging
from contextlib import asynccontextmanager
from typing import Callable, List, Optional, Set

from fastapi import FastAPI

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Graceful Shutdown 관리자

    시그널을 받아 안전하게 종료 절차를 수행합니다.
    """

    def __init__(self, app: FastAPI, timeout: float = 30.0):
        """
        Args:
            app: FastAPI 애플리케이션 인스턴스
            timeout: 종료 타임아웃 (초)
        """
        self.app = app
        self.timeout = timeout
        self.shutdown_event = asyncio.Event()
        self._shutdown_tasks: List[Callable] = []
        self._background_tasks: Set[asyncio.Task] = set()
        self._is_shutting_down = False

    def register_shutdown_task(self, task: Callable) -> None:
        """
        종료 시 실행할 태스크 등록

        Args:
            task: 비동기 실행 가능한 Callable
        """
        self._shutdown_tasks.append(task)

    def add_background_task(self, task: asyncio.Task) -> None:
        """
        추적할 백그라운드 태스크 추가

        Args:
            task: 비동기 태스크
        """
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def shutdown(self) -> None:
        """
        Graceful shutdown 수행

        1. 새 요청 수락 거부
        2. 등록된 종료 태스크 실행
        3. 백그라운드 태스크 완료 대기
        4. 리소스 정리
        """
        if self._is_shutting_down:
            return

        self._is_shutting_down = True
        logger.info("Starting graceful shutdown...")

        try:
            # 1. 종료 이벤트 설정
            self.shutdown_event.set()

            # 2. 등록된 종료 태스크 실행
            if self._shutdown_tasks:
                logger.info(f"Running {len(self._shutdown_tasks)} shutdown tasks...")
                shutdown_results = await asyncio.gather(
                    *[task() for task in self._shutdown_tasks],
                    return_exceptions=True,
                )

                for i, result in enumerate(shutdown_results):
                    if isinstance(result, Exception):
                        logger.error(f"Shutdown task {i} failed: {result}")

            # 3. 백그라운드 태스크 완료 대기
            if self._background_tasks:
                logger.info(f"Waiting for {len(self._background_tasks)} background tasks...")
                await asyncio.wait(self._background_tasks, timeout=self.timeout)

            # 4. 추가 정리 작업
            logger.info("Graceful shutdown completed")

        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout exceeded, forcing exit")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def is_shutting_down(self) -> bool:
        """종료 중인지 확인"""
        return self._is_shutting_down


def setup_shutdown_signals(
    shutdown_handler: GracefulShutdown,
    signals: Optional[List] = None,
) -> None:
    """
    시그널 핸들러 설정

    Args:
        shutdown_handler: GracefulShutdown 인스턴스
        signals: 처리할 시그널 리스트 (기본: SIGINT, SIGTERM)
    """

    if signals is None:
        signals = [signal.SIGINT, signal.SIGTERM]

    def handle_signal(signum, frame):
        """시그널 핸들러"""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name} ({signum})")
        shutdown_handler.shutdown_event.set()

    for sig in signals:
        signal.signal(sig, handle_signal)


@asynccontextmanager
async def lifespan_with_shutdown(
    app: FastAPI,
    startup_tasks: Optional[List[Callable]] = None,
    shutdown_tasks: Optional[List[Callable]] = None,
    timeout: float = 30.0,
):
    """
    Graceful shutdown을 지원하는 lifespan 컨텍스트 매니저

    Args:
        app: FastAPI 애플리케이션
        startup_tasks: 시작 시 실행할 태스크 리스트
        shutdown_tasks: 종료 시 실행할 태스크 리스트
        timeout: 종료 타임아웃

    Usage:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with lifespan_with_shutdown(app, ...) as manager:
                # Startup
                ...

                yield manager

                # Shutdown은 자동 처리됨
    """
    shutdown_manager = GracefulShutdown(app, timeout=timeout)

    # 종료 태스크 등록
    if shutdown_tasks:
        for task in shutdown_tasks:
            shutdown_manager.register_shutdown_task(task)

    try:
        # Startup 태스크 실행
        if startup_tasks:
            logger.info(f"Running {len(startup_tasks)} startup tasks...")
            for task in startup_tasks:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()

        yield shutdown_manager

    finally:
        # Shutdown 수행
        await shutdown_manager.shutdown()


async def wait_for_shutdown(timeout: Optional[float] = None) -> None:
    """
    종료 이벤트 대기

    Args:
        timeout: 대기 타임아웃 (None은 무한 대기)
    """
    # 전역 shutdown 이벤트 대기
    from src.utils.shutdown import get_shutdown_event

    event = get_shutdown_event()
    await asyncio.wait_for(event.wait(), timeout=timeout)


class ShutdownManager:
    """
    전역 Shutdown 관리자

    애플리케이션 전체에서 shutdown 상태를 공유합니다.
    """

    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._shutdown_handlers: List[Callable] = []
        self._is_shutting_down = False

    def set_shutdown(self) -> None:
        """종료 이벤트 설정"""
        self._is_shutting_down = True
        self._shutdown_event.set()

    def is_shutting_down(self) -> bool:
        """종료 중인지 확인"""
        return self._is_shutting_down

    def get_event(self) -> asyncio.Event:
        """종료 이벤트 반환"""
        return self._shutdown_event

    def register_handler(self, handler: Callable) -> None:
        """종료 핸들러 등록"""
        self._shutdown_handlers.append(handler)

    async def trigger_shutdown(self) -> None:
        """종료 트리거 및 핸들러 실행"""
        self.set_shutdown()
        logger.info("Shutdown triggered, running handlers...")

        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Shutdown handler failed: {e}", exc_info=True)


# 전역 인스턴스
_shutdown_manager: Optional[ShutdownManager] = None


def get_shutdown_manager() -> ShutdownManager:
    """전역 ShutdownManager 인스턴스 반환"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = ShutdownManager()
    return _shutdown_manager


def get_shutdown_event() -> asyncio.Event:
    """전역 종료 이벤트 반환"""
    return get_shutdown_manager().get_event()


def is_shutting_down() -> bool:
    """종료 중인지 확인"""
    return get_shutdown_manager().is_shutting_down()


def register_shutdown_handler(handler: Callable) -> None:
    """종료 핸들러 등록"""
    get_shutdown_manager().register_handler(handler)


async def trigger_shutdown() -> None:
    """종료 트리거"""
    await get_shutdown_manager().trigger_shutdown()


class ShutdownMixin:
    """
    Shutdown 인식 믹스인 클래스

    백그라운드 태스크에서 종료 신호를 감지할 수 있습니다.
    """

    async def run_with_shutdown_check(
        self,
        coro,
        check_interval: float = 1.0,
    ):
        """
        종료 체크가 포함된 코루틴 실행

        Args:
            coro: 실행할 비동기 함수
            check_interval: 종료 체크 간격 (초)

        Usage:
            async def my_background_task():
                async with ShutdownMixin() as mixin:
                    await mixin.run_with_shutdown_check(long_running_task())
        """
        task = asyncio.create_task(coro)

        while not task.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(task),
                    timeout=check_interval,
                )
                break
            except asyncio.TimeoutError:
                # 타임아웃은 정상, 종료 체크
                if is_shutting_down():
                    logger.info("Shutdown detected, cancelling task...")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info("Task cancelled successfully")
                    raise
                # 계속 실행

        return await task


def create_shutdown_handler(
    app: FastAPI,
    on_shutdown: Optional[Callable] = None,
) -> Callable:
    """
    FastAPI 용 shutdown 핸들러 생성

    Args:
        app: FastAPI 인스턴스
        on_shutdown: 추가 종료 시 실행할 함수

    Returns:
        lifespan 컨텍스트 매니저
    """
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        # Startup
        logger.info("Application starting...")
        yield

        # Shutdown
        logger.info("Application shutting down...")

        # 등록된 핸들러 실행
        manager = get_shutdown_manager()
        await manager.trigger_shutdown()

        # 사용자 정의 종료 함수
        if on_shutdown:
            try:
                if asyncio.iscoroutinefunction(on_shutdown):
                    await on_shutdown()
                else:
                    on_shutdown()
            except Exception as e:
                logger.error(f"Custom shutdown handler failed: {e}", exc_info=True)

        logger.info("Shutdown complete")

    return lifespan
