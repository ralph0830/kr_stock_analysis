"""
실행 스크립트 및 문서화 검증 테스트

TDD RED Phase - Makefile과 문서가 올바른지 검증
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# 필수 파일
REQUIRED_FILES = [
    "Makefile",
    "docker/compose/README.md",
]

# 필수 Makefile 타겟
REQUIRED_MAKE_TARGETS = [
    "dev",
    "prod",
    "stop",
    "clean",
    "logs",
    "build",
]


def test_required_files_exist():
    """필수 파일 존재 테스트"""
    for filename in REQUIRED_FILES:
        file_path = PROJECT_ROOT / filename
        assert file_path.exists(), f"Required file not found: {filename}"


def test_makefile_has_required_targets():
    """Makefile 필수 타겟 존재 테스트"""
    makefile_path = PROJECT_ROOT / "Makefile"
    content = makefile_path.read_text()

    defined_targets = set()
    for line in content.splitlines():
        line = line.strip()
        # 타겟 정의: "target:" 형식
        if line.endswith(":") and not line.startswith("#") and not line.startswith("\t"):
            target = line[:-1].strip()
            # .PHONY나 변수 정의 제외
            if not target.startswith(".") and "=" not in target:
                defined_targets.add(target)

    for target in REQUIRED_MAKE_TARGETS:
        assert target in defined_targets, f"Makefile: Missing target '{target}'"


def test_makefile_dev_command():
    """Makefile dev 명령 테스트"""
    result = subprocess.run(
        ["make", "-n", "dev"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    # -n은 dry-run이므로 명령만 검증
    assert result.returncode == 0, f"make dev failed: {result.stderr}"
    assert "docker compose" in result.stdout or "docker-compose" in result.stdout, \
        "make dev: Should run docker compose command"
    assert "--profile dev" in result.stdout or "dev" in result.stdout, \
        "make dev: Should use dev profile"


def test_makefile_prod_command():
    """Makefile prod 명령 테스트"""
    result = subprocess.run(
        ["make", "-n", "prod"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"make prod failed: {result.stderr}"
    assert "docker compose" in result.stdout or "docker-compose" in result.stdout, \
        "make prod: Should run docker compose command"
    assert "--profile prod" in result.stdout or "prod" in result.stdout, \
        "make prod: Should use prod profile"


def test_makefile_stop_command():
    """Makefile stop 명령 테스트"""
    result = subprocess.run(
        ["make", "-n", "stop"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"make stop failed: {result.stderr}"
    assert "docker compose" in result.stdout or "docker-compose" in result.stdout, \
        "make stop: Should run docker compose command"
    assert "down" in result.stdout or "stop" in result.stdout, \
        "make stop: Should run docker compose down or stop"


def test_makefile_clean_command():
    """Makefile clean 명령 테스트"""
    result = subprocess.run(
        ["make", "-n", "clean"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"make clean failed: {result.stderr}"
    # clean은 volume 제거를 해야 함
    assert "docker" in result.stdout, "make clean: Should run docker command"


def test_makefile_logs_command():
    """Makefile logs 명령 테스트"""
    result = subprocess.run(
        ["make", "-n", "logs"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"make logs failed: {result.stderr}"
    assert "docker" in result.stdout, "make logs: Should run docker command"
    assert "logs" in result.stdout, "make logs: Should have logs subcommand"


def test_makefile_build_command():
    """Makefile build 명령 테스트"""
    result = subprocess.run(
        ["make", "-n", "build"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"make build failed: {result.stderr}"
    assert "docker" in result.stdout, "make build: Should run docker command"
    assert "build" in result.stdout, "make build: Should have build subcommand"


def test_readme_exists_and_valid():
    """README 존재 및 유효성 테스트"""
    readme_path = PROJECT_ROOT / "docker" / "compose" / "README.md"
    assert readme_path.exists(), "README.md not found in docker/compose/"

    content = readme_path.read_text()

    # 필수 섹션 확인
    required_sections = [
        "#",
        "빠른 시작",
        "개발 환경",
        "운영 환경",
    ]

    for section in required_sections:
        assert section in content, f"README.md: Missing section '{section}'"

    # 코드 블록이 있어야 함 (사용법 예시)
    assert "```" in content or "    " in content, \
        "README.md: Should have code examples with code blocks or indentation"


def test_readme_has_correct_commands():
    """README에 올바른 명령어 포함 테스트"""
    readme_path = PROJECT_ROOT / "docker" / "compose" / "README.md"
    content = readme_path.read_text()

    # README에 포함되어야 할 명령어 예시
    required_command_patterns = [
        "docker compose --profile dev",
        "docker compose --profile prod",
        "make dev",
        "make prod",
    ]

    for pattern in required_command_patterns:
        assert pattern in content, f"README.md: Missing command pattern '{pattern}'"


if __name__ == "__main__":
    import pytest

    # 테스트 실행
    sys.exit(pytest.main([__file__, "-v"]))
