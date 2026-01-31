"""
서비스 정의 파일 모듈화 검증 테스트

TDD RED Phase - docker/compose/services/*.yml 파일이 유효한지 검증
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, List

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SERVICES_DIR = PROJECT_ROOT / "docker" / "compose" / "services"

# 필수 서비스 파일 목록
REQUIRED_SERVICE_FILES = [
    "api-gateway.yml",
    "vcp-scanner.yml",
    "signal-engine.yml",
    "chatbot.yml",
    "frontend.yml",
    "celery.yml",
]

# 필수 인프라 파일
REQUIRED_INFRA_FILE = "infra.yml"

# 필수 키 목록 (서비스 정의마다 필요한 최소 키)
REQUIRED_SERVICE_KEYS = ["services"]
REQUIRED_KEYS_IN_SERVICE = ["image", "ports"]  # image 또는 build 필수


def test_service_files_exist():
    """서비스 파일 존재 테스트"""
    for filename in REQUIRED_SERVICE_FILES:
        file_path = SERVICES_DIR / filename
        assert file_path.exists(), f"Service file not found: {filename}"


def test_infra_file_exists():
    """인프라 파일 존재 테스트"""
    file_path = PROJECT_ROOT / "docker" / "compose" / REQUIRED_INFRA_FILE
    assert file_path.exists(), f"Infra file not found: {REQUIRED_INFRA_FILE}"


def test_service_files_valid_yaml():
    """서비스 파일 유효한 YAML 테스트"""
    for filename in REQUIRED_SERVICE_FILES:
        file_path = SERVICES_DIR / filename
        with open(file_path, "r", encoding="utf-8") as f:
            # YAML 파싱 시도
            try:
                content = yaml.safe_load(f)
                assert content is not None, f"{filename}: Empty YAML content"
            except yaml.YAMLError as e:
                assert False, f"{filename}: Invalid YAML - {e}"


def test_infra_file_valid_yaml():
    """인프라 파일 유효한 YAML 테스트"""
    file_path = PROJECT_ROOT / "docker" / "compose" / REQUIRED_INFRA_FILE
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            content = yaml.safe_load(f)
            assert content is not None, f"{REQUIRED_INFRA_FILE}: Empty YAML content"
        except yaml.YAMLError as e:
            assert False, f"{REQUIRED_INFRA_FILE}: Invalid YAML - {e}"


def test_service_files_have_required_keys():
    """서비스 파일 필수 키 존재 테스트"""
    for filename in REQUIRED_SERVICE_FILES:
        file_path = SERVICES_DIR / filename
        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # 최상위 'services' 키 확인
        assert "services" in content, f"{filename}: Missing 'services' key"

        # 각 서비스에 image 또는 build 키 확인
        services = content["services"]
        assert len(services) > 0, f"{filename}: No services defined"

        for service_name, service_config in services.items():
            has_image_or_build = (
                "image" in service_config or
                "build" in service_config or
                "extends" in service_config  # extends 사용 가능
            )
            assert has_image_or_build, f"{filename}:{service_name} - Missing 'image', 'build', or 'extends'"


def test_infra_file_has_required_services():
    """인프라 파일 필수 서비스 존재 테스트"""
    file_path = PROJECT_ROOT / "docker" / "compose" / REQUIRED_INFRA_FILE
    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    assert "services" in content, f"{REQUIRED_INFRA_FILE}: Missing 'services' key"

    services = content["services"]
    # postgres, redis 필수
    assert "postgres" in services or "postgresql" in services or "db" in services, \
        f"{REQUIRED_INFRA_FILE}: Missing PostgreSQL service"
    assert "redis" in services, f"{REQUIRED_INFRA_FILE}: Missing Redis service"


def test_service_ports_consistent():
    """서비스 포트 일관성 테스트"""
    expected_ports = {
        "api-gateway.yml": 5111,
        "vcp-scanner.yml": 5112,
        "signal-engine.yml": 5113,
        "chatbot.yml": 5114,
        "frontend.yml": 5110,
    }

    for filename, expected_port in expected_ports.items():
        file_path = SERVICES_DIR / filename
        if not file_path.exists():
            continue  # 파일이 없으면 건너뜀 (GREEN phase에서 생성)

        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        services = content["services"]
        # 첫 번째 서비스의 포트 확인
        for service_name, service_config in services.items():
            if "ports" in service_config:
                # 포트 문자열에서 숫자 추출 (예: "5111:5111" → 5111)
                ports = service_config["ports"]
                if isinstance(ports, list) and len(ports) > 0:
                    port_str = str(ports[0]).split(":")[0]
                    actual_port = int(port_str)
                    assert actual_port == expected_port, \
                        f"{filename}:{service_name} - Expected port {expected_port}, got {actual_port}"


def test_compose_config_valid():
    """docker compose config 유효성 테스트"""
    # 모든 서비스 파일과 인프라 파일을 합쳐서 config 검증
    compose_files = []

    # 인프라 파일
    infra_path = PROJECT_ROOT / "docker" / "compose" / REQUIRED_INFRA_FILE
    if infra_path.exists():
        compose_files.extend(["-f", str(infra_path)])

    # 서비스 파일들
    for filename in REQUIRED_SERVICE_FILES:
        file_path = SERVICES_DIR / filename
        if file_path.exists():
            compose_files.extend(["-f", str(file_path)])

    if not compose_files:
        return  # 파일이 없으면 테스트 패스 (GREEN phase에서 생성)

    # docker compose config 실행
    result = subprocess.run(
        ["docker", "compose"] + compose_files + ["config", "--no-interpolate"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # stdout이 비어있지 않으면 유효한 YAML
    assert result.stdout.strip() != "", f"docker compose config failed: {result.stderr}"

    # 유효한 YAML인지 확인
    try:
        yaml.safe_load(result.stdout)
    except yaml.YAMLError as e:
        assert False, f"docker compose config output is invalid YAML: {e}"


def test_service_healthchecks():
    """서비스 헬스체크 존재 테스트"""
    for filename in REQUIRED_SERVICE_FILES:
        file_path = SERVICES_DIR / filename
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        services = content["services"]
        for service_name, service_config in services.items():
            # web 서비스는 healthcheck 권장
            if service_name not in ["postgres", "redis", "flower"]:
                # healthcheck가 있으면 좋음 (required는 아님)
                if "healthcheck" in service_config:
                    assert "test" in service_config["healthcheck"], \
                        f"{filename}:{service_name} - healthcheck missing 'test'"


if __name__ == "__main__":
    import pytest

    # 테스트 실행
    sys.exit(pytest.main([__file__, "-v"]))
