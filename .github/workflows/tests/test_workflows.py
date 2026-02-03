"""
GitHub Actions 워크플로우 유효성 검증 테스트

TDD RED Phase - 워크플로우 구성 검증
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List


class WorkflowValidator:
    """GitHub Actions 워크플로우 검증기"""

    def __init__(self, workflows_dir: Path):
        """
        검증기 초기화

        Args:
            workflows_dir: .github/workflows 디렉토리 경로
        """
        self.workflows_dir = workflows_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """
        모든 워크플로우 검증

        Returns:
            True if all valid
        """
        required_workflows = [
            "ci.yml",
            "cd-staging.yml",
            "cd-production.yml",
            "test-docker-builds.yml",
            "release.yml",
        ]

        all_valid = True
        for workflow_name in required_workflows:
            filepath = self.workflows_dir / workflow_name
            if not filepath.exists():
                self.errors.append(f"Workflow not found: {workflow_name}")
                all_valid = False
                continue

            print(f"🔍 Validating {workflow_name}...")
            if not self._validate_workflow(filepath):
                all_valid = False

        return all_valid

    def _validate_workflow(self, filepath: Path) -> bool:
        """
        단일 워크플로우 검증

        Args:
            filepath: 워크플로우 파일 경로

        Returns:
            True if valid
        """
        try:
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f)

            # 기본 구조 확인
            if 'name' not in config:
                self.errors.append(f"{filepath.name}: Missing 'name'")
                return False

            if 'on' not in config and 'trigger' not in config:
                self.warnings.append(f"{filepath.name}: No triggers defined")

            # jobs 섹션 확인
            if 'jobs' not in config:
                self.errors.append(f"{filepath.name}: No 'jobs' section")
                return False

            jobs = config['jobs']

            # 각 job 검증
            for job_name, job_config in jobs.items():
                self._validate_job(job_name, job_config, filepath.name)

            return len(self.errors) == 0

        except yaml.YAMLError as e:
            self.errors.append(f"{filepath.name}: YAML parsing error - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{filepath.name}: Validation error - {e}")
            return False

    def _validate_job(self, name: str, config: Dict[str, Any], filename: str):
        """
        Job 설정 검증

        Args:
            name: Job 이름
            config: Job 설정
            filename: 워크플로우 파일명
        """
        # runs-on 확인
        if 'runs-on' not in config:
            self.warnings.append(f"{filename}: Job '{name}' missing 'runs-on'")

        # steps 확인
        if 'steps' not in config and 'uses' not in config:
            self.warnings.append(f"{filename}: Job '{name}' has no steps")


def test_workflow_files_exist():
    """필수 워크플로우 파일 존재 테스트"""
    workflows_dir = Path(__file__).parent.parent

    required_files = [
        "ci.yml",
        "cd-staging.yml",
        "cd-production.yml",
        "test-docker-builds.yml",
        "release.yml",
    ]

    for filename in required_files:
        filepath = workflows_dir / filename
        assert filepath.exists(), f"Required workflow not found: {filename}"


def test_ci_workflow_structure():
    """CI 워크플로우 구조 테스트"""
    workflows_dir = Path(__file__).parent.parent
    filepath = workflows_dir / "ci.yml"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    # 필수 jobs 확인
    jobs = config.get('jobs', {})
    required_jobs = ['lint', 'test-unit', 'test-services', 'build-and-push']

    for job in required_jobs:
        assert job in jobs, f"CI workflow missing job: {job}"


def test_cd_staging_workflow_structure():
    """CD Staging 워크플로우 구조 테스트"""
    workflows_dir = Path(__file__).parent.parent
    filepath = workflows_dir / "cd-staging.yml"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    # YAML의 'on' 키는 Python True로 변환됨
    # 직접 파일 내용으로 확인
    content = filepath.read_text()
    assert 'branches: [main]' in content or "branches:\n      - main" in content, "Staging CD should trigger on main branch"

    # 필수 jobs 확인
    jobs = config.get('jobs', {})
    required_jobs = ['deploy-staging', 'post-deploy-check']

    for job in required_jobs:
        assert job in jobs, f"Staging CD workflow missing job: {job}"


def test_cd_production_workflow_structure():
    """CD Production 워크플로우 구조 테스트"""
    workflows_dir = Path(__file__).parent.parent
    filepath = workflows_dir / "cd-production.yml"

    # 파일 내용으로 수동 트리거 확인
    content = filepath.read_text()
    assert 'workflow_dispatch' in content, "Production CD should require manual trigger"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    # 승인 입력 확인
    assert 'confirm:' in content or 'confirm' in content, "Production CD should require confirmation"

    # 필수 jobs 확인
    jobs = config.get('jobs', {})
    required_jobs = ['confirm-deployment', 'pre-deploy-check', 'build-production', 'deploy-production']

    for job in required_jobs:
        assert job in jobs, f"Production CD workflow missing job: {job}"


def test_workflow_registry_consistency():
    """워크플로우 레지스트리 설정 일관성 테스트"""
    workflows_dir = Path(__file__).parent.parent

    expected_registry = "ghcr.io"
    expected_prefix = "ralph-stock"

    for workflow_file in workflows_dir.glob("*.yml"):
        with open(workflow_file) as f:
            content = f.read()

        # 레지스트리 확인
        if 'REGISTRY:' in content:
            assert expected_registry in content, f"{workflow_file.name}: Registry mismatch"

        # 이미지 프리픽스 확인
        if 'IMAGE_PREFIX:' in content:
            assert expected_prefix in content, f"{workflow_file.name}: Image prefix mismatch"


def test_docker_build_workflow():
    """Docker 빌드 워크플로우 테스트"""
    workflows_dir = Path(__file__).parent.parent
    filepath = workflows_dir / "test-docker-builds.yml"

    # 파일 내용으로 PR 트리거 확인
    content = filepath.read_text()
    assert 'pull_request:' in content, "Docker build test should run on PR"

    with open(filepath) as f:
        config = yaml.safe_load(f)

    # 필수 jobs 확인
    jobs = config.get('jobs', {})
    required_jobs = ['build-services', 'validate-compose', 'test-compose-structure']

    for job in required_jobs:
        assert job in jobs, f"Docker build workflow missing job: {job}"


if __name__ == "__main__":
    workflows_dir = Path(__file__).parent.parent
    validator = WorkflowValidator(workflows_dir)

    print("🔍 Validating GitHub Actions workflows...")
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
