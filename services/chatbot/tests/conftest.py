"""
Chatbot Test Configuration
테스트를 위한 공통 설정 및 fixture
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (services.chatbot import용)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 서비스 루트도 sys.path에 추가
service_root = Path(__file__).parent.parent
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))
