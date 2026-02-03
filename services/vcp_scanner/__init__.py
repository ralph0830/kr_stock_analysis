"""
VCP Scanner Service
VCP (Volatility Contraction Pattern) 스캐닝 및 시그널 생성
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (필요시)
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# app import (지연 로딩으로 변경)
def _get_app():
    """app 인스턴스 반환 (지연 로딩)"""
    try:
        # 서비스 독립 실행 시
        from vcp_scanner.main import app
        return app
    except ImportError:
        # 프로젝트 루트 실행 시
        from services.vcp_scanner.main import app
        return app

__all__ = ["app"]

# 모듈 레벨에서는 import 하지 않음 (순환 참조 방지)
# app = _get_app()  # 필요시에만 호출
