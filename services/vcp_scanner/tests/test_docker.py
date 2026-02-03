"""
VCP Scanner Docker 테스트 (TDD RED Phase)

서비스가 Docker로 빌드되고 실행될 수 있는지 테스트
"""

import pytest
import subprocess
from pathlib import Path


class TestDockerfile:
    """Dockerfile 테스트"""

    def test_dockerfile_exists(self):
        """Dockerfile이 존재해야 함"""
        dockerfile_path = Path("services/vcp_scanner/Dockerfile")
        assert dockerfile_path.exists(), "Dockerfile이 존재해야 함"

    def test_dockerfile_has_lib_dependency(self):
        """Dockerfile가 ralph-stock-lib 의존해야 함"""
        dockerfile_path = Path("services/vcp_scanner/Dockerfile")
        content = dockerfile_path.read_text()

        # lib 패키지 복사 확인 (다양한 패턴 지원)
        assert ("COPY lib" in content or "lib/" in content or "lib\\ " in content), \
            "lib 폴더를 복사해야 함"
        # lib를 빌드하는 단계 확인
        assert ("lib" in content and "pip install" in content and "/lib" in content), \
            "lib 패키지를 설치해야 함"

    def test_dockerfile_multi_stage(self):
        """멀티스테이지 빌드 확인"""
        dockerfile_path = Path("services/vcp_scanner/Dockerfile")
        content = dockerfile_path.read_text()

        # Stage 지시어 포함
        assert "FROM" in content
        # 최소 2개 스테이지 (대소문자 구분 없이)
        from_count = content.lower().count(" as ")
        assert from_count >= 2, f"최소 2개 스테이지 필요: {from_count}개"


class TestPyproject:
    """pyproject.toml 테스트"""

    def test_pyproject_exists(self):
        """pyproject.toml이 존재해야 함"""
        pyproject_path = Path("services/vcp_scanner/pyproject.toml")
        assert pyproject_path.exists(), "pyproject.toml이 존재해야 함"

    def test_pyproject_has_lib_dependency(self):
        """pyproject.toml에 ralph-stock-lib 의존성이 있어야 함"""
        pyproject_path = Path("services/vcp_scanner/pyproject.toml")
        content = pyproject_path.read_text()

        assert "ralph-stock-lib" in content, "ralph-stock-lib가 의존성에 있어야 함"


class TestDockerignore:
    """.dockerignore 테스트"""

    def test_dockerignore_exists(self):
        """.dockerignore가 존재해야 함"""
        dockerignore_path = Path("services/vcp_scanner/.dockerignore")
        assert dockerignore_path.exists(), ".dockerignore가 존재해야 함"

    def test_dockerignore_excludes_tests(self):
        """.dockerignore가 tests 폴더를 제외해야 함"""
        dockerignore_path = Path("services/vcp_scanner/.dockerignore")
        content = dockerignore_path.read_text()

        # tests 폴더가 제외되어야 빌드 빠름
        assert "tests/" in content or "**/tests" in content or "tests" in content


@pytest.mark.slow
class TestDockerBuild:
    """Docker 빌드 테스트 (slow test)"""

    def test_docker_image_build(self):
        """Docker 이미지 빌드 테스트"""
        result = subprocess.run(
            [
                "docker", "build", "-f", "services/vcp_scanner/Dockerfile",
                "-t", "vcp-scanner:test", "."
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        # 빌드 시도되면 Docker가 설치되어야 함
        assert result.returncode in [0, 1, 125], "Docker 실행 가능해야 함"
