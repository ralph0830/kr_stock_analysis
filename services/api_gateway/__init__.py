"""
API Gateway Package
Service Discovery 및 Routing 기능 제공
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (필요시)
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 유연한 import (지연 로딩)
def _get_service_registry():
    """ServiceRegistry 모듈 반환 (지연 로딩)"""
    try:
        from api_gateway.service_registry import ServiceRegistry, get_registry
        return ServiceRegistry, get_registry
    except ImportError:
        from services.api_gateway.service_registry import ServiceRegistry, get_registry
        return ServiceRegistry, get_registry


# 지연 import 지원
ServiceRegistry = None
get_registry = None

def __getattr__(name: str):
    """지연 import 지원"""
    if name in ("ServiceRegistry", "get_registry"):
        global ServiceRegistry, get_registry
        ServiceRegistry, get_registry = _get_service_registry()
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ServiceRegistry", "get_registry"]
