#!/usr/bin/env python3
"""
테스트 실행 스크립트 (성능 최적화)

사용법:
    # 빠른 테스트 실행 (단위 테스트)
    python scripts/run_tests.py fast

    # 전체 테스트 실행
    python scripts/run_tests.py all

    # 통합 테스트 실행
    python scripts/run_tests.py integration

    # 병렬 실행 (4 workers)
    python scripts/run_tests.py parallel

    # 타임아웃 30초로 실행
    python scripts/run_tests.py all --timeout 30
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> int:
    """명령어 실행 및 결과 출력"""
    print(f"\n{'='*60}")
    print(f" {description}")
    print(f"{'='*60}")
    print(f"명령어: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ {description} 완료")
    else:
        print(f"\n❌ {description} 실패 (exit code: {result.returncode})")

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="테스트 실행 스크립트 (성능 최적화)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  %(prog)s fast                    빠른 테스트만 실행 (단위 테스트)
  %(prog)s all                     전체 테스트 실행
  %(prog)s integration             통합 테스트만 실행
  %(prog)s parallel                병렬 실행 (4 workers)
  %(prog)s unit --timeout 30       단위 테스트 (타임아웃 30초)
  %(prog)s all -v --durations 10   상세 출력 + 느린 테스트 10개 표시
        """
    )

    parser.add_argument(
        "mode",
        choices=["fast", "all", "unit", "integration", "slow", "parallel"],
        help="테스트 실행 모드"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 출력"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="타임아웃 설정 (초 단위, 기본값: pytest.ini 따름)"
    )

    parser.add_argument(
        "-n", "--workers",
        type=int,
        default=4,
        help="병렬 worker 수 (기본값: 4)"
    )

    parser.add_argument(
        "--durations",
        type=int,
        default=None,
        help="느린 테스트 N개 표시"
    )

    args = parser.parse_args()

    # 기본 명령어
    cmd = ["uv", "run", "pytest"]

    # 모드별 설정
    mode_descriptions = {
        "fast": "빠른 테스트 실행 (단위 테스트)",
        "all": "전체 테스트 실행",
        "unit": "단위 테스트 실행",
        "integration": "통합 테스트 실행",
        "slow": "느린 테스트 실행",
        "parallel": "병렬 실행",
    }

    # 마커 설정
    if args.mode == "fast":
        cmd.extend(["-m", "fast"])
    elif args.mode == "unit":
        cmd.extend(["-m", "unit"])
    elif args.mode == "integration":
        cmd.extend(["-m", "integration"])
    elif args.mode == "slow":
        cmd.extend(["-m", "slow"])
    elif args.mode == "parallel":
        cmd.extend(["-n", str(args.workers)])

    # 추가 옵션
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")  # 기본적으로 간소화된 출력

    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])

    if args.durations:
        cmd.extend(["--durations", str(args.durations)])

    # 테스트 경로 (기본: 전체)
    if args.mode != "parallel":
        cmd.append("tests")

    # 실행
    returncode = run_command(cmd, mode_descriptions[args.mode])

    # 요약 출력
    if args.durations and returncode == 0:
        print(f"\n{'='*60}")
        print(" 💡 팁: 더 많은 성능 정보를 보려면 --durations 20 사용")
        print(f"{'='*60}")

    sys.exit(returncode)


if __name__ == "__main__":
    main()
