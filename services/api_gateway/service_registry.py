"""
Service Registry - Service Discovery 구현
서비스 등록, 조회, 헬스 체크 기능 제공
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import httpx
from datetime import datetime, timedelta


@dataclass
class ServiceInfo:
    """서비스 정보 데이터 클래스"""
    name: str
    url: str
    health_check_url: Optional[str] = None
    health_check_interval: int = 30  # seconds
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    timeout: float = 5.0
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        """health_check_url이 없으면 url 기본값 사용"""
        if self.health_check_url is None:
            self.health_check_url = f"{self.url}/health"


class ServiceRegistry:
    """
    Service Registry 구현

    - 서비스 등록/조회
    - 헬스 체크
    - 비정상 서비스 제거
    - 환경 변수 기반 설정
    """

    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._load_from_env()

    def _load_from_env(self):
        """환경 변수에서 서비스 설정 로드"""
        # VCP Scanner
        vcp_url = os.getenv("VCP_SCANNER_URL", "http://localhost:8001")
        self.register(ServiceInfo(
            name="vcp-scanner",
            url=vcp_url,
            health_check_url=f"{vcp_url}/health"
        ))

        # Market Analyzer
        market_url = os.getenv("MARKET_ANALYZER_URL", "http://localhost:8002")
        self.register(ServiceInfo(
            name="market-analyzer",
            url=market_url,
            health_check_url=f"{market_url}/health"
        ))

        # Signal Engine
        signal_url = os.getenv("SIGNAL_ENGINE_URL", "http://localhost:8003")
        self.register(ServiceInfo(
            name="signal-engine",
            url=signal_url,
            health_check_url=f"{signal_url}/health",
            timeout=15.0  # AI 분석 포함하여 시간 더 소요
        ))

        # AI Analyzer
        ai_url = os.getenv("AI_ANALYZER_URL", "http://localhost:8004")
        self.register(ServiceInfo(
            name="ai-analyzer",
            url=ai_url,
            health_check_url=f"{ai_url}/health"
        ))

    def register(self, service_info: ServiceInfo) -> None:
        """
        서비스 등록

        Args:
            service_info: 등록할 서비스 정보
        """
        self._services[service_info.name] = service_info

    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        """
        서비스 조회

        Args:
            name: 서비스 이름

        Returns:
            서비스 정보 dict 또는 None (없는 경우)
        """
        service = self._services.get(name)
        if service is None:
            return None

        # 비정상 서비스는 반환하지 않음
        if not service.is_healthy:
            return None

        return {
            "name": service.name,
            "url": service.url,
            "health_check_url": service.health_check_url,
            "timeout": service.timeout,
        }

    def list_services(self) -> List[Dict[str, Any]]:
        """
        전체 서비스 목록 조회

        Returns:
            서비스 정보 dict 리스트
        """
        return [
            {
                "name": s.name,
                "url": s.url,
                "health_check_url": s.health_check_url,
                "is_healthy": s.is_healthy,
                "last_health_check": s.last_health_check.isoformat() if s.last_health_check else None,
            }
            for s in self._services.values()
        ]

    async def check_health(self, name: str) -> bool:
        """
        단일 서비스 헬스 체크

        Args:
            name: 서비스 이름

        Returns:
            True (정상), False (비정상)
        """
        service = self._services.get(name)
        if service is None:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    service.health_check_url,
                    timeout=service.timeout
                )
                response.raise_for_status()

                service.is_healthy = True
                service.last_health_check = datetime.now()
                service.retry_count = 0
                return True

        except (httpx.HTTPError, httpx.RequestError) as e:
            service.is_healthy = False
            service.last_health_check = datetime.now()
            service.retry_count += 1

            # 최대 재시도 횟수 초과 시 서비스 제거
            if service.retry_count >= service.max_retries:
                print(f"⚠️ Service {name} unhealthy after {service.retry_count} retries")

            return False

    async def check_all_health(self) -> Dict[str, bool]:
        """
        전체 서비스 헬스 체크

        Returns:
            {서비스 이름: 정상 여부} dict
        """
        results = {}
        tasks = []

        for name in self._services.keys():
            tasks.append(self.check_health(name))

        health_statuses = await asyncio.gather(*tasks, return_exceptions=True)

        for name, status in zip(self._services.keys(), health_statuses):
            if isinstance(status, Exception):
                results[name] = False
            else:
                results[name] = status

        return results

    def cleanup_unhealthy(self) -> List[str]:
        """
        비정상 서비스 제거

        Returns:
            제거된 서비스 이름 리스트
        """
        removed = []
        for name, service in list(self._services.items()):
            if not service.is_healthy or service.retry_count >= service.max_retries:
                del self._services[name]
                removed.append(name)
                print(f"🗑️ Removed unhealthy service: {name}")

        return removed

    def get_unhealthy_services(self) -> List[str]:
        """
        비정상 서비스 목록 조회

        Returns:
            비정상 서비스 이름 리스트
        """
        return [
            name for name, service in self._services.items()
            if not service.is_healthy
        ]


# 전역 인스턴스 (싱글톤)
_registry: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    """
    Service Registry 싱글톤 반환

    Returns:
        ServiceRegistry 인스턴스
    """
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


async def health_check_loop(interval: int = 30):
    """
    주기적 헬스 체크 루프

    Args:
        interval: 헬스 체크 간격 (초)
    """
    registry = get_registry()

    while True:
        try:
            results = await registry.check_all_health()

            unhealthy = [name for name, healthy in results.items() if not healthy]
            if unhealthy:
                print(f"⚠️ Unhealthy services: {unhealthy}")

            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            print("🛑 Health check loop stopped")
            break
        except Exception as e:
            print(f"❌ Health check error: {e}")
            await asyncio.sleep(interval)
