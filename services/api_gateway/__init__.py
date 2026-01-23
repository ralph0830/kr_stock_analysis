"""
API Gateway Package
Service Discovery 및 Routing 기능 제공
"""

from services.api_gateway.service_registry import ServiceRegistry, get_registry

__all__ = ["ServiceRegistry", "get_registry"]
