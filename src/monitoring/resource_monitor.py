"""
시스템 리소스 모니터링 모듈

CPU, 메모리 사용량을 실시간으로 모니터링하고
임계값 초과 시 알림을 발송합니다.
"""

import asyncio
import psutil
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryStats:
    """메모리 통계"""
    total: int           # 전체 메모리 (bytes)
    available: int       # 사용 가능한 메모리 (bytes)
    used: int            # 사용 중인 메모리 (bytes)
    percent: float       # 사용률 (%)


@dataclass
class ResourceUsage:
    """리소스 사용량"""
    cpu_percent: float
    memory: MemoryStats
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_total": self.memory.total,
            "memory_used": self.memory.used,
            "memory_available": self.memory.available,
            "memory_percent": self.memory.percent,
            "timestamp": self.timestamp.isoformat(),
        }


class ResourceMonitor:
    """
    시스템 리소스 모니터

    CPU, 메모리 사용량을 주기적으로 측정하고
    임계값 초과 시 알림 콜백을 호출합니다.

    Args:
        check_interval_seconds: 모니터링 주기 (기본값: 60초)
        cpu_threshold_percent: CPU 경고 임계값 (기본값: 80%)
        memory_threshold_percent: 메모리 경고 임계값 (기본값: 80%)

    Usage:
        monitor = ResourceMonitor()

        # 알림 콜백 등록
        monitor.on_alert(lambda usage: logger.warning(f"High resource usage: {usage}"))

        # 모니터링 시작
        await monitor.start()

        # 현재 사용량 조회
        usage = monitor.get_current_usage()

        # 모니터링 중지
        await monitor.stop()
    """

    def __init__(
        self,
        check_interval_seconds: int = 60,
        cpu_threshold_percent: float = 80.0,
        memory_threshold_percent: float = 80.0,
    ):
        """
        리소스 모니터 초기화

        Args:
            check_interval_seconds: 모니터링 주기 (초)
            cpu_threshold_percent: CPU 경고 임계값 (%)
            memory_threshold_percent: 메모리 경고 임계값 (%)
        """
        self._check_interval = check_interval_seconds
        self._cpu_threshold = cpu_threshold_percent
        self._memory_threshold = memory_threshold_percent

        # 상태 관리
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # 현재 사용량 캐시
        self._current_usage: Optional[ResourceUsage] = None

        # 알림 콜백
        self._alert_callbacks: list[Callable[[ResourceUsage], None]] = []

        # 모니터링 통계
        self._total_checks = 0
        self._total_alerts = 0

    def get_current_usage(self) -> ResourceUsage:
        """
        현재 리소스 사용량 조회

        Returns:
            ResourceUsage 객체
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)

        memory = psutil.virtual_memory()
        memory_stats = MemoryStats(
            total=memory.total,
            available=memory.available,
            used=memory.used,
            percent=memory.percent,
        )

        usage = ResourceUsage(
            cpu_percent=cpu_percent,
            memory=memory_stats,
        )

        self._current_usage = usage
        return usage

    def on_alert(self, callback: Callable[[ResourceUsage], None]) -> None:
        """
        알림 콜백 등록

        Args:
            callback: 리소스 사용량 초과 시 호출할 함수
        """
        self._alert_callbacks.append(callback)

    def _check_alerts(self, usage: ResourceUsage) -> None:
        """
        임계값 초과 시 알림 발송

        Args:
            usage: 현재 리소스 사용량
        """
        alerted = False

        if usage.cpu_percent >= self._cpu_threshold:
            logger.warning(
                f"CPU usage alert: {usage.cpu_percent:.1f}% >= {self._cpu_threshold}%"
            )
            alerted = True

        if usage.memory.percent >= self._memory_threshold:
            logger.warning(
                f"Memory usage alert: {usage.memory.percent:.1f}% >= {self._memory_threshold}%"
            )
            alerted = True

        if alerted:
            self._total_alerts += 1
            for callback in self._alert_callbacks:
                try:
                    callback(usage)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")

    async def _monitor_loop(self) -> None:
        """모니터링 루프"""
        logger.info(
            f"Resource monitor started (interval: {self._check_interval}s, "
            f"CPU threshold: {self._cpu_threshold}%, "
            f"Memory threshold: {self._memory_threshold}%)"
        )

        while self._is_running:
            try:
                self._total_checks += 1
                usage = self.get_current_usage()
                self._check_alerts(usage)

                # 주기적 요약 로그 (매 10회 체크마다)
                if self._total_checks % 10 == 0:
                    logger.info(
                        f"Resource monitor summary (checks: {self._total_checks}, "
                        f"alerts: {self._total_alerts}, "
                        f"CPU: {usage.cpu_percent:.1f}%, "
                        f"Memory: {usage.memory.percent:.1f}%)"
                    )

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            await asyncio.sleep(self._check_interval)

        logger.info("Resource monitor stopped")

    async def start(self) -> None:
        """모니터링 시작"""
        if self._is_running:
            logger.warning("Resource monitor is already running")
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """모니터링 중지"""
        if not self._is_running:
            return

        self._is_running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Resource monitor stopped")

    def is_running(self) -> bool:
        """실행 중 여부 반환"""
        return self._is_running

    def get_stats(self) -> Dict[str, Any]:
        """
        모니터링 통계 반환

        Returns:
            통계 정보 딕셔너리
        """
        return {
            "is_running": self._is_running,
            "total_checks": self._total_checks,
            "total_alerts": self._total_alerts,
            "cpu_threshold_percent": self._cpu_threshold,
            "memory_threshold_percent": self._memory_threshold,
            "check_interval_seconds": self._check_interval,
            "current_usage": self._current_usage.to_dict() if self._current_usage else None,
        }


# 전역 모니터 인스턴스
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """
    전역 리소스 모니터 인스턴스 반환 (싱글톤)

    Returns:
        ResourceMonitor 인스턴스
    """
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor
