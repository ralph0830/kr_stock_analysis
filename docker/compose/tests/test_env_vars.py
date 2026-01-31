"""
환경 변수 관리 시스템 검증 테스트

TDD RED Phase - .env 파일과 필수 환경 변수가 올바른지 검증
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMPOSE_DIR = PROJECT_ROOT / "docker" / "compose"

# 필수 환경 변수
REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "VCP_SCANNER_URL",
    "SIGNAL_ENGINE_URL",
    "CHATBOT_SERVICE_URL",
]

# 선택적 환경 변수 (기본값 있음)
OPTIONAL_ENV_VARS = [
    "GEMINI_API_KEY",
    "KIWOOM_APP_KEY",
    "KIWOOM_SECRET_KEY",
    "LOG_LEVEL",
]

# 필수 파일
REQUIRED_ENV_FILES = [
    ".env.example",
    ".env.dev",
    ".env.prod.template",
]


def test_env_files_exist():
    """환경 변수 파일 존재 테스트"""
    for filename in REQUIRED_ENV_FILES:
        file_path = COMPOSE_DIR / filename
        assert file_path.exists(), f"Environment file not found: {filename}"


def test_env_example_has_all_required_vars():
    """.env.example에 필수 변수 포함 테스트"""
    env_example = COMPOSE_DIR / ".env.example"

    # 파일 읽기
    content = env_example.read_text()

    # 주석(#)으로 시작하지 않는 라인 추출
    defined_vars = set()
    for line in content.splitlines():
        line = line.strip()
        # 주석和无값 라인 무시
        if not line or line.startswith("#"):
            continue
        # VARIABLE= 또는 VARIABLE: 형식 추출
        if "=" in line:
            var_name = line.split("=")[0].strip()
            defined_vars.add(var_name)
        elif ":" in line and not line.startswith(" "):
            var_name = line.split(":")[0].strip()
            defined_vars.add(var_name)

    # 필수 변수 확인
    for var in REQUIRED_ENV_VARS:
        assert var in defined_vars, f".env.example: Missing required variable '{var}'"


def test_env_dev_is_valid():
    """.env.dev 유효성 테스트"""
    env_dev = COMPOSE_DIR / ".env.dev"
    content = env_dev.read_text()

    # 빈 파일이거나 주석만 있어도 됨 (템플릿)
    # 적어도 몇 개의 변수는 있어야 함
    defined_vars = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            var_name = line.split("=")[0].strip()
            defined_vars.add(var_name)

    # 최한 몇 개의 기본 변수는 있어야 함
    assert len(defined_vars) > 0, ".env.dev: Should have at least some variables defined"
    assert "DATABASE_URL" in defined_vars or "POSTGRES_DB" in defined_vars, \
        ".env.dev: Should have DATABASE_URL or POSTGRES_DB"


def test_env_prod_template_is_valid():
    """.env.prod.template 유효성 테스트"""
    env_prod = COMPOSE_DIR / ".env.prod.template"
    content = env_prod.read_text()

    # 운영용은 민감 정보가 placeholder로 있어야 함
    defined_vars = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            var_name = line.split("=")[0].strip()
            defined_vars.add(var_name)

    # 필수 변수 확인
    assert "DATABASE_URL" in defined_vars or "POSTGRES_PASSWORD" in defined_vars, \
        ".env.prod.template: Should have DATABASE_URL or POSTGRES_PASSWORD"


def test_env_files_no_secrets():
    """실제 비밀값이 없는지 확인 테스트"""
    # .env.example과 .env.prod.template에는 실제 비밀값이 없어야 함
    for filename in [".env.example", ".env.prod.template"]:
        file_path = COMPOSE_DIR / filename
        content = file_path.read_text()

        # 의심스러운 패턴 확인
        suspicious_patterns = [
            "password=123",  # 단순 비밀번호
            "password=password",  # 동일한 값
            "secret=sk-",  # 실제 API 키 패턴 (Gemini, OpenAI 등)
            "key=ya29",  # Google OAuth 키 패턴
            "BEGIN PRIVATE KEY",  # RSA 개인키
        ]

        for pattern in suspicious_patterns:
            # 대소문자 구분 없이 검사
            assert pattern.lower() not in content.lower(), \
                f"{filename}: Contains suspicious pattern '{pattern}' (should use placeholder)"


def test_env_vars_consistent():
    """환경 변수 파일 간 일관성 테스트"""
    # 모든 환경 변수 파일의 변수 목록 추출
    def extract_vars(file_path: Path) -> Set[str]:
        if not file_path.exists():
            return set()
        content = file_path.read_text()
        vars = set()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                var_name = line.split("=")[0].strip()
                vars.add(var_name)
        return vars

    # .env.example이 가장 완전해야 함
    example_vars = extract_vars(COMPOSE_DIR / ".env.example")
    dev_vars = extract_vars(COMPOSE_DIR / ".env.dev")
    prod_vars = extract_vars(COMPOSE_DIR / ".env.prod.template")

    # .env.example은 최소한 dev와 prod의 변수를 모두 포함해야 함
    # (일부 변수는 환경별로 다를 수 있으므로 loose check)
    assert len(example_vars) >= len(dev_vars) * 0.5 or len(example_vars) >= 10, \
        ".env.example: Should contain most variables from other env files"


def test_env_example_has_documentation():
    """.env.example에 문서/주석이 있는지 테스트"""
    env_example = COMPOSE_DIR / ".env.example"
    content = env_example.read_text()

    # 주석 라인이 있어야 함
    lines = content.splitlines()
    comment_lines = [l for l in lines if l.strip().startswith("#")]

    assert len(comment_lines) >= 3, \
        ".env.example: Should have at least 3 comment lines for documentation"


def test_port_consistency():
    """포트 설정 일관성 테스트"""
    # 모든 환경 파일에서 포트 변수 확인
    expected_ports = {
        "POSTGRES_PORT": "5433",
        "REDIS_PORT": "6380",
        "API_GATEWAY_PORT": "5111",
        "VCP_SCANNER_PORT": "5112",
        "SIGNAL_ENGINE_PORT": "5113",
        "CHATBOT_PORT": "5114",
        "FRONTEND_PORT": "5110",
        "FLOWER_PORT": "5555",
    }

    # .env.dev에서 기본 포트 확인
    env_dev = COMPOSE_DIR / ".env.dev"
    if env_dev.exists():
        content = env_dev.read_text()
        for port_var, expected_value in expected_ports.items():
            if f"{port_var}=" in content:
                # 값이 있다면 예상값과 일치해야 함
                for line in content.splitlines():
                    if line.strip().startswith(f"{port_var}="):
                        actual_value = line.split("=")[1].strip()
                        # 빈 값이 아니면 확인
                        if actual_value and actual_value != '"..."':
                            assert actual_value == expected_value or actual_value == f'"{expected_value}"', \
                                f".env.dev: {port_var} should be {expected_value}, got {actual_value}"


if __name__ == "__main__":
    import pytest

    # 테스트 실행
    sys.exit(pytest.main([__file__, "-v"]))
