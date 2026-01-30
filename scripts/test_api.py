#!/usr/bin/env python3
"""
API 테스트 스크립트
모든 API 엔드포인트를 테스트하고 결과를 출력합니다.
"""

import requests
from datetime import datetime

# API Gateway URL
API_BASE_URL = "http://localhost:5111"

# 색상 출력
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"
    BOLD = "\033[1m"

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def test_health_check():
    """헬스 체크 API 테스트"""
    print_header("1. 헬스 체크 (Health Check)")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /health")
            print(f"   Status: {data.get('status')}")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print_error(f"GET /health - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"GET /health - Error: {e}")
        return False

def test_get_signals():
    """VCP 시그널 목록 API 테스트"""
    print_header("2. VCP 시그널 목록 (Get Signals)")

    try:
        response = requests.get(f"{API_BASE_URL}/api/kr/signals?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /api/kr/signals")

            if isinstance(data, list) and len(data) > 0:
                print(f"   총 {len(data)}개 시그널 수신")
                print("\n   상위 3개 시그널:")
                for i, signal in enumerate(data[:3], 1):
                    print(f"   {i}. {signal.get('ticker')} - {signal.get('name')}")
                    print(f"      등급: {signal.get('grade')}, 점수: {signal.get('score')}")
            else:
                print_info("시그널 데이터 없음")
            return True
        else:
            print_error(f"GET /api/kr/signals - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"GET /api/kr/signals - Error: {e}")
        return False

def test_market_gate():
    """Market Gate 상태 API 테스트"""
    print_header("3. Market Gate 상태")

    try:
        response = requests.get(f"{API_BASE_URL}/api/kr/market-gate", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /api/kr/market-gate")
            print(f"   상태: {data.get('status')}")
            print(f"   레벨: {data.get('level')}")
            print(f"   KOSPI: {data.get('kospi_status')}")
            print(f"   KOSDAQ: {data.get('kosdaq_status')}")
            print(f"   업데이트: {data.get('updated_at')}")
            return True
        else:
            print_error(f"GET /api/kr/market-gate - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"GET /api/kr/market-gate - Error: {e}")
        return False

def test_jongga_v2():
    """종가베팅 V2 시그널 API 테스트"""
    print_header("4. 종가베팅 V2 시그널")

    try:
        response = requests.get(f"{API_BASE_URL}/api/kr/jongga-v2/latest?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /api/kr/jongga-v2/latest")

            if isinstance(data, list) and len(data) > 0:
                print(f"   총 {len(data)}개 시그널 수신")
                print("\n   상위 3개 시그널:")
                for i, signal in enumerate(data[:3], 1):
                    print(f"   {i}. {signal.get('ticker')} - {signal.get('name')}")
                    print(f"      등급: {signal.get('grade')}, 점수: {signal.get('score')}")
            else:
                print_info("시그널 데이터 없음")
            return True
        else:
            print_error(f"GET /api/kr/jongga-v2/latest - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"GET /api/kr/jongga-v2/latest - Error: {e}")
        return False

def test_realtime_prices():
    """실시간 가격 조회 API 테스트"""
    print_header("5. 실시간 가격 조회")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/kr/realtime-prices",
            json={"tickers": ["005930", "000660"]},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success("POST /api/kr/realtime-prices")

            if "prices" in data:
                prices = data["prices"]
                print(f"   총 {len(prices)}개 종목 가격 수신")
                for ticker, price_info in prices.items():
                    print(f"   {ticker}: {price_info.get('price')}원 ({price_info.get('change_rate')}%)")
            return True
        else:
            print_error(f"POST /api/kr/realtime-prices - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"POST /api/kr/realtime-prices - Error: {e}")
        return False

def test_websocket_stats():
    """WebSocket 통계 API 테스트"""
    print_header("6. WebSocket 통계")

    try:
        response = requests.get(f"{API_BASE_URL}/ws/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /ws/stats")
            print(f"   활성 연결: {data.get('active_connections')}")
            print(f"   브로드캐스터 실행: {data.get('broadcaster_running')}")
            print(f"   구독자 수: {data.get('subscriptions')}")
            return True
        else:
            print_error(f"GET /ws/stats - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"GET /ws/stats - Error: {e}")
        return False

def test_metrics():
    """메트릭 API 테스트"""
    print_header("7. 시스템 메트릭")

    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("GET /metrics")
            print(f"   요청 수: {data.get('requests', {}).get('total', 'N/A')}")
            print(f"   응답 시간: {data.get('response_time_ms', 'N/A')}")
            return True
        else:
            print_error(f"GET /metrics - Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"GET /metrics - Error: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print(f"\n{Colors.BOLD}🧪 Ralph Stock API 테스트{Colors.END}")
    print(f"📅 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 API Gateway: {API_BASE_URL}")

    # 테스트 실행
    tests = [
        test_health_check,
        test_get_signals,
        test_market_gate,
        test_jongga_v2,
        test_realtime_prices,
        test_websocket_stats,
        test_metrics,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_error(f"테스트 실패: {e}")
            results.append(False)

    # 요약
    print_header("테스트 결과 요약")

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"총 테스트: {total}")
    print_success(f"통과: {passed}")
    if failed > 0:
        print_error(f"실패: {failed}")

    print()
    if passed == total:
        print_success("모든 테스트 통과! ✨")
    else:
        print_error(f"{failed}개 테스트 실패")

    print()

if __name__ == "__main__":
    main()
