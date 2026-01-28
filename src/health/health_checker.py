"""
서비스 헬스체크 시스템

모든 서비스의 상태를 확인하고 상세 정보를 제공합니다.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx


class HealthStatus(str, Enum):
    """헬스 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """개별 서비스 헬스 정보"""

    name: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "name": self.name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "message": self.message,
            "details": self.details,
            "last_check": self.last_check.isoformat(),
        }


@dataclass
class SystemHealth:
    """시스템 전체 헬스 정보"""

    status: HealthStatus
    services: Dict[str, ServiceHealth] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "status": self.status.value,
            "services": {name: health.to_dict() for name, health in self.services.items()},
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """
    헬스체크 코디네이터

    모든 서비스의 헬스체크를 수행하고 집계합니다.
    """

    def __init__(self, start_time: float, timeout: float = 5.0):
        """
        Args:
            start_time: 애플리케이션 시작 시간 (time.time())
            timeout: 외부 서비스 체크 타임아웃 (초)
        """
        self.start_time = start_time
        self.timeout = timeout
        self._checkers: Dict[str, Callable] = {}

    def register_checker(self, name: str, checker: Callable) -> None:
        """
        헬스체크 함수 등록

        Args:
            name: 서비스 이름
            checker: 비동기 헬스체크 함수 (ServiceHealth 반환)
        """
        self._checkers[name] = checker

    async def check_all(self, session: Optional[AsyncSession] = None) -> SystemHealth:
        """
        모든 서비스 헬스체크 수행

        Args:
            session: 데이터베이스 세션 (可选)

        Returns:
            SystemHealth: 전체 시스템 헬스 정보
        """
        services: Dict[str, ServiceHealth] = {}

        # 기본 체커 실행
        basic_checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            "api_gateway": self._check_api_gateway,
        }

        # 기본 체커 실행
        for name, checker in basic_checks.items():
            try:
                if name == "database" and session:
                    health = await checker(session)
                else:
                    health = await checker()
                services[name] = health
            except Exception as e:
                services[name] = ServiceHealth(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(e)}",
                )

        # 등록된 커스텀 체커 실행
        for name, checker in self._checkers.items():
            if name not in services:
                try:
                    health = await checker()
                    services[name] = health
                except Exception as e:
                    services[name] = ServiceHealth(
                        name=name,
                        status=HealthStatus.UNKNOWN,
                        message=f"Health check failed: {str(e)}",
                    )

        # 전체 상태 판정
        overall_status = self._determine_overall_status(services)

        # 가동 시간 계산
        uptime = time.time() - self.start_time

        return SystemHealth(
            status=overall_status,
            services=services,
            uptime_seconds=uptime,
        )

    async def check_service(self, name: str) -> ServiceHealth:
        """
        단일 서비스 헬스체크

        Args:
            name: 서비스 이름

        Returns:
            ServiceHealth: 서비스 헬스 정보
        """
        # 기본 체커
        basic_checkers = {
            "database": lambda: self._check_database(None),
            "redis": self._check_redis,
            "api_gateway": self._check_api_gateway,
        }

        if name in basic_checkers:
            try:
                return await basic_checkers[name]()
            except Exception as e:
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(e)}",
                )

        # 등록된 커스텀 체커
        if name in self._checkers:
            try:
                return await self._checkers[name]()
            except Exception as e:
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(e)}",
                )

        return ServiceHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            message="Service not found",
        )

    def _determine_overall_status(self, services: Dict[str, ServiceHealth]) -> HealthStatus:
        """
        전체 상태 판정

        규칙:
        - 모든 서비스가 healthy: healthy
        - 핵심 서비스(database, redis) 하나라도 down: unhealthy
        - 일부 서비스 degraded: degraded
        - 그 외: unhealthy
        """
        if not services:
            return HealthStatus.UNKNOWN

        # 상태별 카운트
        healthy_count = sum(1 for s in services.values() if s.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for s in services.values() if s.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for s in services.values() if s.status == HealthStatus.UNHEALTHY)

        total_count = len(services)

        # 핵심 서비스 체크
        core_services = ["database", "redis", "api_gateway"]
        for core in core_services:
            if core in services and services[core].status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY

        # 전체 판정
        if healthy_count == total_count:
            return HealthStatus.HEALTHY
        elif unhealthy_count == 0 and degraded_count > 0:
            return HealthStatus.DEGRADED
        elif unhealthy_count > total_count / 2:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED

    async def _check_database(self, session: Optional[AsyncSession]) -> ServiceHealth:
        """데이터베이스 헬스체크"""
        start_time = time.time()

        try:
            if session is None:
                # 동기 세션 생성 시도
                from src.database.session import get_sync_session
                with get_sync_session() as sync_session:
                    result = sync_session.execute(text("SELECT 1"))
                    result.fetchone()
            else:
                # 비동기 세션 사용
                await session.execute(text("SELECT 1"))

            response_time = (time.time() - start_time) * 1000

            # 응답 시간에 따른 상태
            if response_time > 1000:  # 1초 이상
                status = HealthStatus.DEGRADED
                message = f"Slow response: {response_time:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "OK"

            return ServiceHealth(
                name="database",
                status=status,
                response_time_ms=round(response_time, 2),
                message=message,
            )

        except Exception as e:
            return ServiceHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)}",
            )

    async def _check_redis(self) -> ServiceHealth:
        """Redis 헬스체크"""
        start_time = time.time()

        try:
            import os
            from redis import asyncio as aioredis

            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
            client = await aioredis.from_url(redis_url)

            try:
                await client.ping()
                response_time = (time.time() - start_time) * 1000

                # 메모리 사용량 확인
                info = await client.info("memory")
                used_memory = info.get("used_memory", 0)
                used_memory_human = info.get("used_memory_human", "unknown")

                # 응답 시간에 따른 상태
                if response_time > 500:  # 500ms 이상
                    status = HealthStatus.DEGRADED
                    message = f"Slow response: {response_time:.2f}ms"
                else:
                    status = HealthStatus.HEALTHY
                    message = "OK"

                return ServiceHealth(
                    name="redis",
                    status=status,
                    response_time_ms=round(response_time, 2),
                    message=message,
                    details={
                        "used_memory": used_memory,
                        "used_memory_human": used_memory_human,
                    },
                )

            finally:
                await client.close()

        except Exception as e:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)}",
            )

    async def _check_api_gateway(self) -> ServiceHealth:
        """API Gateway 자체 헬스체크"""
        start_time = time.time()

        try:
            # 기본 검사: 메모리, CPU 등
            import psutil
            process = psutil.Process()

            # 메모리 사용량
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # 응답 시간
            response_time = (time.time() - start_time) * 1000

            # 상태 판정
            if memory_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = "OK"

            return ServiceHealth(
                name="api_gateway",
                status=status,
                response_time_ms=round(response_time, 2),
                message=message,
                details={
                    "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "memory_percent": round(memory_percent, 2),
                    "cpu_percent": process.cpu_percent(),
                },
            )

        except ImportError:
            # psutil 없이 기본 체크
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                name="api_gateway",
                status=HealthStatus.HEALTHY,
                response_time_ms=round(response_time, 2),
                message="OK",
            )
        except Exception as e:
            return ServiceHealth(
                name="api_gateway",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
            )

    async def _check_http_service(
        self,
        name: str,
        base_url: str,
        health_path: str = "/health",
    ) -> ServiceHealth:
        """
        HTTP 서비스 헬스체크

        Args:
            name: 서비스 이름
            base_url: 서비스 베이스 URL
            health_path: 헬스체크 경로
        """
        start_time = time.time()

        try:
            url = f"{base_url}{health_path}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # 응답 시간에 따른 상태
                if response_time > 2000:  # 2초 이상
                    status = HealthStatus.DEGRADED
                    message = f"Slow response: {response_time:.2f}ms"
                else:
                    status = HealthStatus.HEALTHY
                    message = "OK"

                return ServiceHealth(
                    name=name,
                    status=status,
                    response_time_ms=round(response_time, 2),
                    message=message,
                )
            else:
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"HTTP {response.status_code}",
                )

        except httpx.TimeoutException:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Request timeout",
            )
        except Exception as e:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)}",
            )

    async def check_vcp_scanner(self, url: str) -> ServiceHealth:
        """VCP Scanner 헬스체크"""
        return await self._check_http_service("vcp_scanner", url)

    async def check_signal_engine(self, url: str) -> ServiceHealth:
        """Signal Engine 헬스체크"""
        return await self._check_http_service("signal_engine", url)

    async def check_market_analyzer(self, url: str) -> ServiceHealth:
        """Market Analyzer 헬스체크"""
        return await self._check_http_service("market_analyzer", url)


# 전역 인스턴스
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> Optional[HealthChecker]:
    """전역 헬스체커 인스턴스 반환"""
    return _health_checker


def init_health_checker(start_time: float, timeout: float = 5.0) -> HealthChecker:
    """
    헬스체커 초기화

    Args:
        start_time: 애플리케이션 시작 시간
        timeout: 외부 서비스 체크 타임아웃

    Returns:
        HealthChecker: 헬스체커 인스턴스
    """
    global _health_checker
    _health_checker = HealthChecker(start_time, timeout)
    return _health_checker
