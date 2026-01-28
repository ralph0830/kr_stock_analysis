#!/usr/bin/env python
"""
OpenAPI 스펙 생성 스크립트

API Gateway의 OpenAPI 스펙을 JSON/YAML로 export합니다.
사용법:
    python scripts/generate_openapi_spec.py               # JSON 출력
    python scripts/generate_openapi_spec.py --yaml        # YAML 출력
    python scripts/generate_openapi_spec.py --output openapi.json
"""

import json
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 경로를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_openapi_json() -> dict:
    """OpenAPI JSON 스펙 생성"""
    from services.api_gateway.main import app
    return app.openapi()


def save_json(spec: dict, output_path: str) -> None:
    """OpenAPI 스펙을 JSON 파일로 저장"""
    output_file = Path(output_path)

    # 디렉토리가 없으면 생성
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    print(f"✅ OpenAPI JSON 스펙이 저장되었습니다: {output_file}")
    print(f"   - Endpoints: {len(spec.get('paths', {}))}")
    print(f"   - Components: {len(spec.get('components', {}).get('schemas', {}))}")


def save_yaml(spec: dict, output_path: str) -> None:
    """OpenAPI 스펙을 YAML 파일로 저장"""
    try:
        import yaml
    except ImportError:
        print("❌ PyYAML이 설치되지 않았습니다.")
        print("   설치: uv add pyyaml")
        sys.exit(1)

    output_file = Path(output_path)

    # 디렉토리가 없으면 생성
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✅ OpenAPI YAML 스펙이 저장되었습니다: {output_file}")
    print(f"   - Endpoints: {len(spec.get('paths', {}))}")
    print(f"   - Components: {len(spec.get('components', {}).get('schemas', {}))}")


def print_summary(spec: dict) -> None:
    """OpenAPI 스펙 요약 출력"""
    info = spec.get("info", {})
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})

    print("\n" + "=" * 60)
    print("📋 API Gateway OpenAPI 스펙 요약")
    print("=" * 60)
    print(f"Title:   {info.get('title', 'N/A')}")
    print(f"Version: {info.get('version', 'N/A')}")
    print(f"Endpoints: {len(paths)}")
    print(f"Schemas: {len(schemas)}")
    print("\n📡 Endpoints by Tag:")

    # 태그별 엔드포인트 그룹화
    tags = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict):
                for tag in details.get("tags", ["untagged"]):
                    if tag not in tags:
                        tags[tag] = []
                    tags[tag].append(f"{method.upper()} {path}")

    for tag, endpoints in sorted(tags.items()):
        print(f"  [{tag}] {len(endpoints)}개")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="OpenAPI 스펙 생성")
    parser.add_argument(
        "--yaml", "-y",
        action="store_true",
        help="YAML 형식으로 출력"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="출력 파일 경로 (기본값: stdout 또는 --openapi.json/--openapi.yaml)"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="스펙 요약만 출력"
    )

    args = parser.parse_args()

    # OpenAPI 스펙 생성
    spec = generate_openapi_json()

    # 요약 출력
    if args.summary or not args.yaml and not args.output:
        print_summary(spec)

    # JSON 출력
    if not args.yaml:
        if args.output:
            output_path = args.output
        else:
            output_path = project_root / "openapi.json"

        save_json(spec, output_path)

        # 파일 내용 미리보기
        if not args.output:
            print("\n📄 OpenAPI JSON 미리보기:")
            print("-" * 60)
            print(json.dumps(spec, ensure_ascii=False, indent=2)[:500] + "...")
            print("-" * 60)

    # YAML 출력
    if args.yaml:
        if args.output:
            output_path = args.output
        else:
            output_path = project_root / "openapi.yaml"

        save_yaml(spec, output_path)


if __name__ == "__main__":
    main()
