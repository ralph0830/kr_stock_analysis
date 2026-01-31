"""
Docker Compose 설정 유효성 검증 테스트

TDD RED Phase - Compose 파일 구성 검증
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, List


class ComposeConfigValidator:
    """Docker Compose 설정 검증기"""

    def __init__(self, compose_dir: Path):
        """
        검증기 초기화

        Args:
            compose_dir: docker/compose 디렉토리 경로
        """
        self.compose_dir = compose_dir
        self.project_root = compose_dir.parent.parent
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """
        모든 compose 파일 검증

        Returns:
            True if all valid
        """
        files_to_check = [
            "docker-compose.base.yml",
            "docker-compose.dev.yml",
            "docker-compose.prod.yml",
            "docker-compose.test.yml",
        ]

        all_valid = True
        for filename in files_to_check:
            filepath = self.compose_dir / filename
            if not filepath.exists():
                self.errors.append(f"File not found: {filename}")
                all_valid = False
                continue

            print(f"🔍 Validating {filename}...")
            if not self._validate_file(filepath):
                all_valid = False

        # .env.example 확인
        env_example = self.compose_dir / ".env.example"
        if not env_example.exists():
            self.errors.append(".env.example not found")
            all_valid = False

        return all_valid

    def _validate_file(self, filepath: Path) -> bool:
        """
        단일 compose 파일 검증

        Args:
            filepath: compose 파일 경로

        Returns:
            True if valid
        """
        try:
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f)

            if not config or 'services' not in config:
                self.errors.append(f"{filepath.name}: No 'services' section found")
                return False

            services = config['services']
            required_keys = ['networks']

            for key in required_keys:
                if key not in config:
                    self.errors.append(f"{filepath.name}: Missing '{key}' section")
                    return False

            # 서비스별 검증
            for service_name, service_config in services.items():
                self._validate_service(service_name, service_config, filepath.name)

            # 구문 검증 (docker-compose config)
            self._validate_syntax(filepath)

            return len(self.errors) == 0

        except yaml.YAMLError as e:
            self.errors.append(f"{filepath.name}: YAML parsing error - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{filepath.name}: Validation error - {e}")
            return False

    def _validate_service(self, name: str, config: Dict[str, Any], filename: str):
        """
        서비스 설정 검증

        Args:
            name: 서비스 이름
            config: 서비스 설정
            filename: compose 파일명
        """
        # 필수 키 확인
        if 'image' not in config and 'build' not in config:
            self.errors.append(f"{filename}: Service '{name}' must have 'image' or 'build'")

        # build context 확인
        if 'build' in config:
            build_config = config['build']
            if 'context' in build_config:
                context = build_config['context']
                # 상대 경로인지 확인
                if context.startswith('../..'):
                    full_path = (self.compose_dir / context).resolve()
                    if not full_path.exists():
                        self.errors.append(
                            f"{filename}: Service '{name}' build context does not exist: {context}"
                        )

        # healthcheck 확인 (production)
        if 'prod' in filename:
            if name not in ['postgres', 'redis']:  # 인프라는 제외
                if 'healthcheck' not in config:
                    self.warnings.append(f"{filename}: Service '{name}' missing healthcheck")

        # resource limits 확인 (production)
        if 'prod' in filename:
            if 'deploy' not in config:
                self.warnings.append(f"{filename}: Service '{name}' missing resource limits")
            elif 'resources' not in config.get('deploy', {}):
                self.warnings.append(f"{filename}: Service '{name}' missing resource constraints")

    def _validate_syntax(self, filepath: Path):
        """
        Docker Compose 구문 검증

        Args:
            filepath: compose 파일 경로
        """
        try:
            result = subprocess.run(
                ['docker', 'compose', '-f', str(filepath), 'config'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.compose_dir)
            )

            if result.returncode != 0:
                self.errors.append(
                    f"{filepath.name}: docker-compose config failed - {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            self.errors.append(f"{filepath.name}: docker-compose config timeout")
        except FileNotFoundError:
            self.warnings.append(f"{filepath.name}: docker command not found, skipping syntax validation")


def test_compose_files_exist():
    """compose 파일 존재 테스트"""
    compose_dir = Path(__file__).parent

    required_files = [
        "docker-compose.base.yml",
        "docker-compose.dev.yml",
        "docker-compose.prod.yml",
        "docker-compose.test.yml",
        ".env.example",
    ]

    for filename in required_files:
        filepath = compose_dir / filename
        assert filepath.exists(), f"Required file not found: {filename}"


def test_base_compose_structure():
    """base compose 구조 테스트"""
    compose_dir = Path(__file__).parent
    filepath = compose_dir / "docker-compose.base.yml"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    # base compose는 인프라 서비스만 포함 (postgres, redis, flower)
    infra_services = ['postgres', 'redis', 'flower']

    services = config.get('services', {})
    for service in infra_services:
        assert service in services, f"Missing infrastructure service in base compose: {service}"

    # 애플리케이션 서비스는 base에 없어야 함
    app_services = ['api-gateway', 'vcp-scanner', 'signal-engine', 'chatbot', 'frontend']
    for service in app_services:
        assert service not in services, f"Application service should not be in base compose: {service}"

    # volumes, networks 확인
    assert 'volumes' in config
    assert 'networks' in config


def test_dev_compose_overrides():
    """dev compose override 설정 테스트"""
    compose_dir = Path(__file__).parent
    filepath = compose_dir / "docker-compose.dev.yml"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    # dev용 빌륨 마운트 확인
    services = config.get('services', {})
    for service_name, service_config in services.items():
        if service_name in ['api-gateway', 'vcp-scanner', 'signal-engine', 'chatbot']:
            assert 'volumes' in service_config, f"{service_name} should have volumes for hot reload"
            # 개발용 command 확인
            assert 'command' in service_config, f"{service_name} should have command with --reload"


def test_prod_compose_hardening():
    """prod compose 하드닝 테스트"""
    compose_dir = Path(__file__).parent
    filepath = compose_dir / "docker-compose.prod.yml"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    services = config.get('services', {})

    # 애�리케이션 서비스는 healthcheck 있어야 함
    app_services = ['api-gateway', 'vcp-scanner', 'signal-engine', 'chatbot']
    for service_name in app_services:
        if service_name in services:
            service_config = services[service_name]
            assert 'healthcheck' in service_config, f"{service_name} must have healthcheck"
            # resource limits 확인
            assert 'deploy' in service_config, f"{service_name} must have deploy configuration"
            assert 'resources' in service_config['deploy'], f"{service_name} must have resource limits"


def test_env_example_complete():
    """.env.example 필수 변수 확인"""
    compose_dir = Path(__file__).parent
    env_file = compose_dir / ".env.example"

    content = env_file.read_text()

    required_vars = [
        'DATABASE_URL',
        'REDIS_URL',
        'GEMINI_API_KEY',
        'KIWOOM_APP_KEY',
    ]

    for var in required_vars:
        assert var in content, f"Missing variable in .env.example: {var}"


if __name__ == "__main__":
    compose_dir = Path(__file__).parent
    validator = ComposeConfigValidator(compose_dir)

    print("🔍 Validating Docker Compose files...")
    print("=" * 60)

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
