"""
Dockerfile 경로 일관성 검증 테스트

TDD RED Phase - Dockerfile이 프로젝트 루트 기준으로 빌드되는지 검증
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 프로젝트 루트 (이 파일의 위치에서 계산)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class DockerfileValidator:
    """Dockerfile 경로 검증기"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """모든 Dockerfile 검증"""
        services = [
            ("api_gateway", "services/api_gateway/Dockerfile"),
            ("vcp_scanner", "services/vcp_scanner/Dockerfile"),
            ("signal_engine", "services/signal_engine/Dockerfile"),
            ("chatbot", "services/chatbot/Dockerfile"),
        ]

        all_valid = True
        for service_name, dockerfile_path in services:
            print(f"🔍 Validating {service_name}...")
            if not self._validate_dockerfile(service_name, dockerfile_path):
                all_valid = False

        return all_valid

    def _validate_dockerfile(self, service_name: str, dockerfile_path: str) -> bool:
        """
        단일 Dockerfile 검증

        Args:
            service_name: 서비스 이름
            dockerfile_path: Dockerfile 경로 (프로젝트 루트 기준)

        Returns:
            True if valid
        """
        full_path = self.project_root / dockerfile_path
        if not full_path.exists():
            self.errors.append(f"{service_name}: Dockerfile not found at {dockerfile_path}")
            return False

        # Dockerfile 내용 읽기
        content = full_path.read_text()

        # COPY 경로 검증
        copy_lines = self._extract_copy_commands(content)
        for cmd, src, dest in copy_lines:
            if not self._validate_copy_path(service_name, cmd, src):
                self.errors.append(f"{service_name}: Invalid COPY {src}")

        # 필수 파일 존재 확인
        required_files = self._get_required_files(service_name)
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                self.errors.append(f"{service_name}: Required file not found: {file_path}")

        return len(self.errors) == 0

    def _extract_copy_commands(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Dockerfile에서 COPY 명령 추출

        Returns:
            [(command, source, destination), ...]
        """
        import re

        copy_pattern = re.compile(r'^COPY\s+(?:--\S+\s+)*(\S+)\s+(\S+)', re.MULTILINE)
        return [("COPY", src, dest) for src, dest in copy_pattern.findall(content)]

    def _validate_copy_path(self, service_name: str, cmd: str, src: str) -> bool:
        """
        COPY 경로가 유효한지 검증

        Args:
            service_name: 서비스 이름
            cmd: COPY 명령
            src: 소스 경로

        Returns:
            True if valid
        """
        # lib/ 경로는 항상 유효해야 함
        if src.startswith("lib/") or src == "lib":
            if not (self.project_root / src).exists():
                self.errors.append(f"lib/ directory not found")
                return False

        # services/{service_name}/ 경로는 유효해야 함
        if src.startswith(f"services/{service_name}/"):
            if not (self.project_root / src).exists():
                self.errors.append(f"Service directory not found: {src}")
                return False

        # src/ 경로는 유효해야 함
        if src.startswith("src/") or src == "src":
            if not (self.project_root / src).exists():
                self.errors.append(f"src/ directory not found")
                return False

        # signal_engine 특수 케이스
        if service_name == "signal_engine":
            # pyproject.toml은 services/signal_engine/에 있어야 함
            if src == "pyproject.toml":
                if not (self.project_root / "services/signal_engine/pyproject.toml").exists():
                    self.errors.append(f"signal_engine: pyproject.toml should be at services/signal_engine/")
                    return False
            # scorer.py, main.py는 services/signal_engine/에 있어야 함
            if src in ["scorer.py", "main.py"]:
                if not (self.project_root / f"services/signal_engine/{src}").exists():
                    self.errors.append(f"signal_engine: {src} should be at services/signal_engine/")
                    return False

        return True

    def _get_required_files(self, service_name: str) -> List[str]:
        """
        서비스별 필수 파일 목록

        Args:
            service_name: 서비스 이름

        Returns:
            필수 파일 경로 리스트
        """
        common_files = ["lib/", "src/"]
        service_files = [
            f"services/{service_name}/Dockerfile",
            f"services/{service_name}/pyproject.toml",
            f"services/{service_name}/main.py",
        ]
        return common_files + service_files


def test_dockerfiles_exist():
    """Dockerfile 존재 테스트"""
    services = [
        "api_gateway",
        "vcp_scanner",
        "signal_engine",
        "chatbot",
    ]

    for service in services:
        dockerfile_path = PROJECT_ROOT / f"services/{service}/Dockerfile"
        assert dockerfile_path.exists(), f"Dockerfile not found for {service}"


def test_dockerfile_copy_paths():
    """Dockerfile COPY 경로 유효성 테스트"""
    validator = DockerfileValidator(PROJECT_ROOT)

    # 모든 COPY 경로가 존재하는지 확인
    services = [
        ("api_gateway", "services/api_gateway/Dockerfile"),
        ("vcp_scanner", "services/vcp_scanner/Dockerfile"),
        ("signal_engine", "services/signal_engine/Dockerfile"),
        ("chatbot", "services/chatbot/Dockerfile"),
    ]

    for service_name, dockerfile_path in services:
        full_path = PROJECT_ROOT / dockerfile_path
        content = full_path.read_text()

        # COPY 명령 추출 (정규식 수정 - 비캡처리 그룹 사용)
        import re
        # COPY 명령에서 소스/대상 경로만 추출 (--from 옵션은 무시)
        copy_pattern = re.compile(r'^COPY\s+(?:--\S+\s+)*(\S+)\s+(\S+)', re.MULTILINE)
        matches = copy_pattern.findall(content)

        for src, dest in matches:
            # lib/와 src/는 모든 서비스에서 필요
            if src in ["lib/", "lib", "src/", "src"]:
                assert (PROJECT_ROOT / src).exists(), f"{service_name}: {src} not found"

            # services/{service}/ 경로 확인
            if src.startswith(f"services/{service_name}/"):
                assert (PROJECT_ROOT / src).exists(), f"{service_name}: {src} not found"


def test_dockerfile_build_targets():
    """Dockerfile 빌드 타겟 존재 테스트"""
    required_targets = ["builder", "development", "production"]

    for service in ["api_gateway", "vcp_scanner", "signal_engine", "chatbot"]:
        dockerfile_path = PROJECT_ROOT / f"services/{service}/Dockerfile"
        content = dockerfile_path.read_text()

        for target in required_targets:
            # 대소문자 구분 없이 검사 (AS builder 또는 as builder)
            assert f"AS {target}" in content or f"as {target}" in content, \
                f"{service}: Missing target '{target}'"


def test_dockerfile_consistency():
    """Dockerfile 구조 일관성 테스트"""
    services = [
        ("api_gateway", "services/api_gateway/Dockerfile"),
        ("vcp_scanner", "services/vcp_scanner/Dockerfile"),
        ("signal_engine", "services/signal_engine/Dockerfile"),
        ("chatbot", "services/chatbot/Dockerfile"),
    ]

    for service_name, dockerfile_path in services:
        full_path = PROJECT_ROOT / dockerfile_path
        content = full_path.read_text()

        # Python 버전 일관성
        assert "python:3.11" in content or "python:3.12" in content, \
            f"{service_name}: Python version not specified"

        # EXPOSE 포트 확인
        port = {
            "api_gateway": "5111",
            "vcp_scanner": "5112",
            "signal_engine": "5113",
            "chatbot": "5114",
        }[service_name]

        assert f"EXPOSE {port}" in content, f"{service_name}: Port {port} not exposed"

        # HEALTHCHECK 존재
        assert "HEALTHCHECK" in content, f"{service_name}: Missing HEALTHCHECK"


def test_signal_engine_dockerfile_paths():
    """signal_engine Dockerfile 경로 특수 테스트"""
    dockerfile_path = PROJECT_ROOT / "services/signal_engine/Dockerfile"
    content = dockerfile_path.read_text()

    # pyproject.toml은 프로젝트 루트가 아닌 services/signal_engine/에 있어야 함
    # 현재 Dockerfile의 `COPY pyproject.toml ./`는 잘못됨
    assert "COPY services/signal_engine/pyproject.toml" in content or \
           "COPY pyproject.toml" not in content, \
           "signal_engine: pyproject.toml COPY path is incorrect"

    # scorer.py, main.py도 services/signal_engine/에서 복사해야 함
    assert "COPY services/signal_engine/main.py" in content or \
           "COPY main.py" not in content, \
           "signal_engine: main.py COPY path is incorrect"

    assert "COPY services/signal_engine/scorer.py" in content or \
           "COPY scorer.py" not in content, \
           "signal_engine: scorer.py COPY path is incorrect"


if __name__ == "__main__":
    validator = DockerfileValidator(PROJECT_ROOT)

    print("🔍 Validating Dockerfiles...")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")

    if validator.validate_all():
        print("✅ All validations passed!")
        sys.exit(0)
    else:
        print("❌ Validation failed!")
        print("\nErrors:")
        for error in validator.errors:
            print(f"  ❌ {error}")
        if validator.warnings:
            print("\nWarnings:")
            for warning in validator.warnings:
                print(f"  ⚠️  {warning}")
        sys.exit(1)
