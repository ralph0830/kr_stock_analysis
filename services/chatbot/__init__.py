"""
Chatbot Service
RAG 기반 주식 분석 AI 챗봇 서비스
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
        from chatbot.main import app
        return app
    except ImportError:
        from services.chatbot.main import app
        return app

__version__ = "1.0.0"
__all__ = ["app"]
