"""
실시간 데이터 파이프라인 관리자 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.koa.pipeline import (
    RealtimePipelineManager,
    get_pipeline_manager,
    init_pipeline_manager,
    shutdown_pipeline_manager
)
from src.koa.base import RealtimePrice


class TestRealtimePipelineManager:
    """파이프라인 관리자 테스트"""

    def test_initial_state(self):
        """초기 상태 확인"""
        manager = RealtimePipelineManager(
            use_koa=False,
            use_redis=False
        )

        assert manager.is_running() is False
        assert manager._use_koa is False
        assert manager._use_redis is False
        assert manager.get_stats()["running"] is False

    @pytest.mark.asyncio
    async def test_start_with_mock(self):
        """Mock로 시작 테스트"""
        manager = RealtimePipelineManager(
            use_koa=False,  # Mock KOA
            use_redis=False,  # Mock Redis
            update_interval=0.1
        )

        result = await manager.start()

        assert result is True
        assert manager.is_running() is True

        stats = manager.get_stats()
        assert stats["running"] is True
        assert stats["use_koa"] is False
        assert stats["use_redis"] is False

        await manager.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """이미 실행 중일 때 시작 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        await manager.start()
        result = await manager.start()  # 이미 실행 중

        assert result is True  # 이미 실행 중이면 True 반환

        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop(self):
        """중지 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        await manager.start()
        assert manager.is_running() is True

        await manager.stop()
        assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """실행 중이 아닐 때 중지 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        # 예외 없이 처리되어야 함
        await manager.stop()
        assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_subscribe_tickers(self):
        """종목 구독 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        await manager.start()

        results = await manager.subscribe_tickers(["005930", "000660"])

        assert results["005930"] is True
        assert results["000660"] is True

        await manager.stop()

    @pytest.mark.asyncio
    async def test_subscribe_tickers_when_not_running(self):
        """실행 중이 아닐 때 구독 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        results = await manager.subscribe_tickers(["005930"])

        assert results["005930"] is False

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self):
        """모든 구독 해제 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        await manager.start()
        await manager.subscribe_tickers(["005930", "000660"])

        # 예외 없이 처리되어야 함
        await manager.unsubscribe_all()

        await manager.stop()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        # 시작 전
        health = await manager.health_check()
        assert health["pipeline"] == "stopped"

        await manager.start()

        # 시작 후
        health = await manager.health_check()
        assert health["pipeline"] == "running"
        assert health["koa_service"] == "running"
        assert health["redis_publisher"] == "connected"

        await manager.stop()

        # 중지 후
        health = await manager.health_check()
        assert health["pipeline"] == "stopped"

    @pytest.mark.asyncio
    async def test_stats(self):
        """통계 정보 테스트"""
        manager = RealtimePipelineManager(use_koa=False, use_redis=False)

        await manager.start()
        await manager.subscribe_tickers(["005930"])

        stats = manager.get_stats()
        assert stats["running"] is True
        assert "005930" in stats["subscribed_tickers"]

        await manager.stop()

    @pytest.mark.asyncio
    async def test_start_with_redis_connection_failure(self):
        """Redis 연결 실패 시 Mock으로 대체 테스트"""
        manager = RealtimePipelineManager(
            use_koa=False,
            use_redis=True,  # Redis 사용 시도
            update_interval=0.1
        )

        # Redis 연결 실패를 모킹 (실제 Redis 없음)
        # 연결 실패 시 MockRedisPublisher로 대체되어야 함
        result = await manager.start()

        # Mock으로 대체되어 시작 성공해야 함
        assert result is True
        assert manager.is_running() is True

        await manager.stop()


class TestGlobalPipelineManager:
    """전역 파이프라인 관리자 테스트"""

    def test_get_pipeline_manager_initially_none(self):
        """초기에는 None 반환"""
        from src.koa.pipeline import _pipeline_manager
        _pipeline_manager = None
        manager = get_pipeline_manager()
        assert manager is None

    @pytest.mark.asyncio
    async def test_init_pipeline_manager(self):
        """전역 파이프라인 관리자 초기화 테스트"""
        from src.koa.pipeline import _pipeline_manager
        _pipeline_manager = None

        manager = await init_pipeline_manager(
            use_koa=False,
            use_redis=False,
            tickers=["005930"],
            update_interval=0.1
        )

        assert manager is not None
        assert manager.is_running() is True
        assert get_pipeline_manager() is manager

        await shutdown_pipeline_manager()

    @pytest.mark.asyncio
    async def test_shutdown_pipeline_manager(self):
        """전역 파이프라인 관리자 종료 테스트"""
        from src.koa.pipeline import _pipeline_manager
        _pipeline_manager = None

        await init_pipeline_manager(use_koa=False, use_redis=False)
        assert get_pipeline_manager() is not None

        await shutdown_pipeline_manager()
        assert get_pipeline_manager() is None

    @pytest.mark.asyncio
    async def test_init_pipeline_manager_with_env_key_check(self):
        """환경 변수 키 확인 테스트"""
        from src.koa.pipeline import _pipeline_manager
        _pipeline_manager = None

        # KIWOOM_APP_KEY가 없으면 Mock 모드로 전환
        with patch.dict('os.environ', {'KIWOOM_APP_KEY': ''}):
            manager = await init_pipeline_manager(
                use_koa=True,  # 키가 없어도 Mock으로 전환
                use_redis=False,
                update_interval=0.1
            )

            assert manager is not None
            await shutdown_pipeline_manager()


class TestPipelineIntegration:
    """파이프라인 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """전체 파이프라인 흐름 테스트"""
        manager = RealtimePipelineManager(
            use_koa=False,
            use_redis=False,
            update_interval=0.05  # 빠른 업데이트
        )

        # 시작
        assert await manager.start() is True

        # 종목 구독
        results = await manager.subscribe_tickers(["005930", "000660"])
        assert all(results.values())

        # 잠시 대기 (데이터 업데이트 확인)
        await asyncio.sleep(0.2)

        # 통계 확인
        stats = manager.get_stats()
        assert stats["running"] is True
        assert len(stats["subscribed_tickers"]) == 2

        # 헬스 체크
        health = await manager.health_check()
        assert health["pipeline"] == "running"

        # 중지
        await manager.stop()
        assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_restart_pipeline(self):
        """파이프라인 재시작 테스트"""
        manager = RealtimePipelineManager(
            use_koa=False,
            use_redis=False,
            update_interval=0.1
        )

        # 첫 번째 시작
        await manager.start()
        await manager.subscribe_tickers(["005930"])
        await manager.stop()

        # 두 번째 시작
        result = await manager.start()
        assert result is True

        await manager.subscribe_tickers(["000660"])
        stats = manager.get_stats()
        assert "000660" in stats["subscribed_tickers"]

        await manager.stop()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """동시 작업 테스트"""
        manager = RealtimePipelineManager(
            use_koa=False,
            use_redis=False,
            update_interval=0.1
        )

        await manager.start()

        # 동시에 여러 종목 구독
        tickers = [f"{i:06d}" for i in range(10)]
        results = await manager.subscribe_tickers(tickers)

        assert all(results.values())
        assert len(manager.get_stats()["subscribed_tickers"]) == 10

        await manager.stop()
