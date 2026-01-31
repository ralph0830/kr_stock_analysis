"""
Profiles 기반 Compose 파일 검증 테스트

TDD RED Phase - docker-compose.yml의 dev/prod profile이 올바른지 검증
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, List

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# 필수 파일
REQUIRED_COMPOSE_FILES = [
    "docker-compose.yml",
    "docker-compose.dev.yml",
    "docker-compose.prod.yml",
]

# 필수 profiles
REQUIRED_PROFILES = ["dev", "prod"]

# dev profile에서 실행되어야 할 서비스
DEV_REQUIRED_SERVICES = [
    "postgres",
    "redis",
    "api-gateway",
    "vcp-scanner",
    "signal-engine",
    "chatbot",
    "frontend",
    "celery-worker",
    "celery-beat",
    "flower",
]

# prod profile에서 실행되어야 할 서비스
PROD_REQUIRED_SERVICES = [
    "postgres",
    "redis",
    "api-gateway",
    "vcp-scanner",
    "signal-engine",
    "chatbot",
    "frontend",
    "celery-worker",
    "celery-beat",
    "flower",
]


def test_compose_files_exist():
    """통합 compose 파일 존재 테스트"""
    for filename in REQUIRED_COMPOSE_FILES:
        file_path = PROJECT_ROOT / filename
        assert file_path.exists(), f"Compose file not found: {filename}"


def test_main_compose_valid_yaml():
    """메인 compose 파일 유효한 YAML 테스트"""
    file_path = PROJECT_ROOT / "docker-compose.yml"
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            content = yaml.safe_load(f)
            assert content is not None, "docker-compose.yml: Empty YAML content"
        except yaml.YAMLError as e:
            assert False, f"docker-compose.yml: Invalid YAML - {e}"


def test_dev_compose_valid_yaml():
    """dev compose 파일 유효한 YAML 테스트"""
    file_path = PROJECT_ROOT / "docker-compose.dev.yml"
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            content = yaml.safe_load(f)
            assert content is not None, "docker-compose.dev.yml: Empty YAML content"
        except yaml.YAMLError as e:
            assert False, f"docker-compose.dev.yml: Invalid YAML - {e}"


def test_prod_compose_valid_yaml():
    """prod compose 파일 유효한 YAML 테스트"""
    file_path = PROJECT_ROOT / "docker-compose.prod.yml"
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            content = yaml.safe_load(f)
            assert content is not None, "docker-compose.prod.yml: Empty YAML content"
        except yaml.YAMLError as e:
            assert False, f"docker-compose.prod.yml: Invalid YAML - {e}"


def test_main_compose_has_profiles():
    """메인 compose 파일에 profiles 설정 존재 테스트"""
    file_path = PROJECT_ROOT / "docker-compose.yml"
    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    # services 키 확인
    assert "services" in content, "docker-compose.yml: Missing 'services' key"

    # 모든 서비스에 profiles 또는 profiles가 없으면 항상 실행되는 인프라
    services = content.get("services", {})

    # 인프라 서비스(postgres, redis)는 profiles가 없어도 됨
    infra_services = {"postgres", "redis"}

    for service_name, service_config in services.items():
        if service_name not in infra_services:
            # 앱 서비스는 profiles를 가져야 함
            profiles = service_config.get("profiles", [])
            assert len(profiles) > 0, f"{service_name}: Missing 'profiles'"


def test_dev_profile_services():
    """dev profile 서비스 구성 테스트"""
    # docker compose --profile dev config 실행
    result = subprocess.run(
        ["docker", "compose", "--profile", "dev", "config", "--no-interpolate"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, f"docker compose --profile dev config failed: {result.stderr}"

    # 출력 파싱
    config = yaml.safe_load(result.stdout)
    services = config.get("services", {})

    # dev 필수 서비스 확인
    for required_service in DEV_REQUIRED_SERVICES:
        assert required_service in services, f"dev profile: Missing service '{required_service}'"


def test_prod_profile_services():
    """prod profile 서비스 구성 테스트"""
    # docker compose --profile prod config 실행
    result = subprocess.run(
        ["docker", "compose", "--profile", "prod", "config", "--no-interpolate"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, f"docker compose --profile prod config failed: {result.stderr}"

    # 출력 파싱
    config = yaml.safe_load(result.stdout)
    services = config.get("services", {})

    # prod 필수 서비스 확인
    for required_service in PROD_REQUIRED_SERVICES:
        assert required_service in services, f"prod profile: Missing service '{required_service}'"


def test_dev_has_hot_reload():
    """dev profile에 핫 리로드 설정 확인"""
    result = subprocess.run(
        ["docker", "compose", "--profile", "dev", "config", "--no-interpolate"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    config = yaml.safe_load(result.stdout)
    services = config.get("services", {})

    # Python 서비스에 volumes 마운트 확인 (핫 리로드용)
    for service_name in ["api-gateway", "vcp-scanner", "signal-engine", "chatbot"]:
        if service_name in services:
            service = services[service_name]
            volumes = service.get("volumes", [])
            # 소스 코드 볼륨 마운트 확인
            has_source_mount = any("/app/" in str(v) for v in volumes)
            assert has_source_mount, f"dev profile: {service_name} missing source volume mount"


def test_prod_no_hot_reload():
    """prod profile에 핫 리로드 설정 없음 확인"""
    result = subprocess.run(
        ["docker", "compose", "--profile", "prod", "config", "--no-interpolate"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    config = yaml.safe_load(result.stdout)
    services = config.get("services", {})

    # Python 서비스에 readonly 볼륨 마운트 또는 볼륨 없음 확인
    for service_name in ["api-gateway", "vcp-scanner", "signal-engine", "chatbot"]:
        if service_name in services:
            service = services[service_name]
            # command에 --reload가 없어야 함
            command = service.get("command", [])
            cmd_str = " ".join(str(c) for c in command) if isinstance(command, list) else str(command)
            assert "--reload" not in cmd_str, f"prod profile: {service_name} should not have --reload"


def test_compose_include_infra():
    """메인 compose 파일이 infra를 포함하는지 확인"""
    file_path = PROJECT_ROOT / "docker-compose.yml"
    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    # include 또는 직접 정의로 infra 서비스가 있어야 함
    services = content.get("services", {})
    assert "postgres" in services or "redis" in services or "include" in content, \
        "docker-compose.yml: Should include infra services (postgres, redis)"


if __name__ == "__main__":
    import pytest

    # 테스트 실행
    sys.exit(pytest.main([__file__, "-v"]))
