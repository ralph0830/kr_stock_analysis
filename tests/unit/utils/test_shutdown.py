"""
Graceful Shutdown 테스트
"""

import pytest
import asyncio
from unittest.mock import patch

from fastapi import FastAPI

from src.utils.shutdown import (
    GracefulShutdown,
    ShutdownManager,
    ShutdownMixin,
    get_shutdown_manager,
    is_shutting_down,
    register_shutdown_handler,
    trigger_shutdown,
    setup_shutdown_signals,
    lifespan_with_shutdown,
    create_shutdown_handler,
)


class TestGracefulShutdown:
    """GracefulShutdown 테스트"""

    @pytest.fixture
    def app(self):
        return FastAPI()

    @pytest.fixture
    def shutdown(self, app):
        return GracefulShutdown(app, timeout=5.0)

    def test_initialization(self, shutdown):
        """초기화 테스트"""
        assert shutdown.timeout == 5.0
        assert not shutdown.is_shutting_down()
        assert shutdown._shutdown_tasks == []
        assert shutdown._background_tasks == set()

    def test_register_shutdown_task(self, shutdown):
        """종료 태스크 등록 테스트"""
        async def mock_task():
            pass

        shutdown.register_shutdown_task(mock_task)
        assert len(shutdown._shutdown_tasks) == 1

    @pytest.mark.asyncio
    async def test_shutdown_basic(self, shutdown):
        """기본 종료 테스트"""
        assert not shutdown.is_shutting_down()

        await shutdown.shutdown()

        assert shutdown.is_shutting_down()
        assert shutdown.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_with_tasks(self, shutdown):
        """종료 태스크와 함께 종료 테스트"""
        executed = []

        async def task1():
            executed.append("task1")

        async def task2():
            executed.append("task2")

        shutdown.register_shutdown_task(task1)
        shutdown.register_shutdown_task(task2)

        await shutdown.shutdown()

        assert "task1" in executed
        assert "task2" in executed

    @pytest.mark.asyncio
    async def test_shutdown_with_failing_task(self, shutdown):
        """실패하는 태스크가 있는 경우 테스트"""
        async def failing_task():
            raise ValueError("Task failed")

        async def success_task():
            return "success"

        shutdown.register_shutdown_task(failing_task)
        shutdown.register_shutdown_task(success_task)

        # 예외가 발생해도 종료는 계속됨
        await shutdown.shutdown()

        assert shutdown.is_shutting_down()

    @pytest.mark.asyncio
    async def test_add_background_task(self, shutdown):
        """백그라운드 태스크 추가 테스트"""
        async def dummy_task():
            await asyncio.sleep(0.1)

        task = asyncio.create_task(dummy_task())
        shutdown.add_background_task(task)

        assert task in shutdown._background_tasks

        # 태스크 완료 후 자동 제거
        await task
        assert task not in shutdown._background_tasks

    @pytest.mark.asyncio
    async def test_double_shutdown_protection(self, shutdown):
        """이중 종료 방지 테스트"""
        await shutdown.shutdown()
        assert shutdown.is_shutting_down()

        # 두 번째 종료는 무시됨
        await shutdown.shutdown()
        assert shutdown.is_shutting_down()


class TestShutdownManager:
    """ShutdownManager 테스트"""

    def test_singleton(self):
        """싱글톤 패턴 테스트"""
        manager1 = get_shutdown_manager()
        manager2 = get_shutdown_manager()

        assert manager1 is manager2

    def test_initial_state(self):
        """초기 상태 테스트"""
        manager = ShutdownManager()
        assert not manager.is_shutting_down()
        assert not manager.get_event().is_set()

    def test_set_shutdown(self):
        """종료 설정 테스트"""
        manager = ShutdownManager()
        manager.set_shutdown()

        assert manager.is_shutting_down()
        assert manager.get_event().is_set()

    def test_register_handler(self):
        """핸들러 등록 테스트"""
        manager = ShutdownManager()

        def handler():
            pass

        manager.register_handler(handler)
        assert len(manager._shutdown_handlers) == 1

    @pytest.mark.asyncio
    async def test_trigger_shutdown(self):
        """종료 트리거 테스트"""
        manager = ShutdownManager()

        executed = []

        def handler():
            executed.append("handler")

        manager.register_handler(handler)
        await manager.trigger_shutdown()

        assert manager.is_shutting_down()
        assert "handler" in executed

    @pytest.mark.asyncio
    async def test_global_functions(self):
        """전역 함수 테스트"""
        # 초기 상태
        assert not is_shutting_down()

        # 핸들러 등록
        executed = []

        def handler():
            executed.append("global_handler")

        register_shutdown_handler(handler)

        # 종료 트리거
        await trigger_shutdown()

        assert is_shutting_down()
        assert "global_handler" in executed


class TestShutdownMixin:
    """ShutdownMixin 테스트"""

    @pytest.mark.asyncio
    async def test_run_with_shutdown_check_normal_completion(self):
        """정상 완료 테스트"""
        mixin = ShutdownMixin()

        async def quick_task():
            return "done"

        result = await mixin.run_with_shutdown_check(quick_task(), check_interval=0.1)
        assert result == "done"

    @pytest.mark.asyncio
    async def test_run_with_shutdown_check_cancellation(self):
        """종료에 의한 취소 테스트"""
        from src.utils.shutdown import get_shutdown_manager

        manager = get_shutdown_manager()

        async def long_task():
            await asyncio.sleep(10)
            return "done"

        mixin = ShutdownMixin()

        # 종료 이벤트 설정
        manager.set_shutdown()

        # 종료 상태에서는 태스크가 즉시 취소됨
        with pytest.raises((asyncio.CancelledError, asyncio.TimeoutError)):
            await asyncio.wait_for(
                mixin.run_with_shutdown_check(long_task(), check_interval=0.01),
                timeout=1.0,
            )


class TestLifespanWithShutdown:
    """lifespan_with_shutdown 테스트"""

    @pytest.fixture
    def app(self):
        return FastAPI()

    @pytest.mark.asyncio
    async def test_lifespan_with_startup_tasks(self, app):
        """Startup 태스크 실행 테스트"""
        executed = []

        def sync_task():
            executed.append("sync")

        async def async_task():
            executed.append("async")

        async with lifespan_with_shutdown(
            app,
            startup_tasks=[sync_task, async_task],
            shutdown_tasks=[],
        ):
            assert "sync" in executed
            assert "async" in executed

    @pytest.mark.asyncio
    async def test_lifespan_with_shutdown_tasks(self, app):
        """Shutdown 태스크 실행 테스트"""
        executed = []

        async def cleanup_task():
            executed.append("cleanup")

        async with lifespan_with_shutdown(
            app,
            startup_tasks=[],
            shutdown_tasks=[cleanup_task],
        ):
            executed.append("running")

        assert "running" in executed
        assert "cleanup" in executed

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_manager(self, app):
        """ShutdownManager 반환 테스트"""
        async with lifespan_with_shutdown(app) as manager:
            assert manager is not None
            assert isinstance(manager, GracefulShutdown)
            assert not manager.is_shutting_down()


class TestCreateShutdownHandler:
    """create_shutdown_handler 테스트"""

    @pytest.fixture
    def app(self):
        return FastAPI()

    def test_returns_lifespan(self, app):
        """lifespan 함수 반환 테스트"""
        handler = create_shutdown_handler(app)

        # callable이어야 함
        assert callable(handler)

        # 호출하면 async context manager (__aenter__, __aexit__)를 반환
        ctx = handler(app)
        assert hasattr(ctx, "__aenter__")
        assert hasattr(ctx, "__aexit__")

    @pytest.mark.asyncio
    async def test_custom_shutdown_handler(self, app):
        """사용자 정의 종료 핸들러 테스트"""
        executed = []

        async def custom_cleanup():
            executed.append("custom")

        handler = create_shutdown_handler(app, on_shutdown=custom_cleanup)

        async with handler(app):
            executed.append("running")

        assert "running" in executed
        assert "custom" in executed


class TestSetupShutdownSignals:
    """setup_shutdown_signals 테스트"""

    def test_sets_signal_handlers(self):
        """시그널 핸들러 설정 테스트"""
        from src.utils.shutdown import GracefulShutdown

        app = FastAPI()
        shutdown_handler = GracefulShutdown(app)

        with patch("signal.signal") as mock_signal:
            setup_shutdown_signals(shutdown_handler)

            # SIGINT, SIGTERM에 대해 호출되었는지 확인
            assert mock_signal.call_count == 2
