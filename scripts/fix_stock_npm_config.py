#!/usr/bin/env python3
"""
stock.ralphpark.com NPM 설정 수정 스크립트

문제: forward_host가 'frontend' (Docker 내부 이름)로 설정되어 있어
     NPM이 ralph-network에 연결되지 않으면 접속 불가

해결: forward_host를 112.219.120.75 (서버 IP)로 변경
"""

import os
import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('.env.npm')

npm_url = os.getenv('NPM_URL')
npm_email = os.getenv('NPM_EMAIL')
npm_password = os.getenv('NPM_PASSWORD')

# 설정
STOCK_HOST_ID = 35  # stock.ralphpark.com의 NPM 호스트 ID
NEW_FORWARD_HOST = "112.219.120.75"  # 서버 IP
FRONTEND_PORT = 5110
API_PORT = 5111

def main():
    print("🔧 stock.ralphpark.com NPM 설정 수정")
    print("=" * 50)

    # 1. 로그인
    print("1. NPM에 로그인...")
    session = requests.Session()
    response = session.post(
        f'{npm_url}/api/tokens',
        json={'identity': npm_email, 'secret': npm_password},
        timeout=10
    )
    response.raise_for_status()
    token = response.json()['token']
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    print("   ✅ 로그인 성공")

    # 2. 현재 설정 조회
    print("\n2. 현재 설정 조회...")
    response = session.get(
        f'{npm_url}/api/nginx/proxy-hosts/{STOCK_HOST_ID}',
        timeout=10
    )
    response.raise_for_status()
    current = response.json()

    print(f"   도메인: {', '.join(current.get('domain_names', []))}")
    print(f"   forward_host: {current.get('forward_host')}")
    print(f"   forward_port: {current.get('forward_port')}")

    # locations 확인
    locations = current.get('locations', [])
    print(f"   locations ({len(locations)}개):")
    for loc in locations:
        print(f"     - {loc.get('path')} → {loc.get('forward_host')}:{loc.get('forward_port')}")

    # 3. 설정 변경
    if current.get('forward_host') == NEW_FORWARD_HOST:
        print(f"\n   ⚠️  이미 forward_host가 {NEW_FORWARD_HOST}로 설정되어 있습니다.")
        print("   변경할 사항이 없습니다.")
        return

    print(f"\n3. 설정 변경...")
    print(f"   forward_host: {current.get('forward_host')} → {NEW_FORWARD_HOST}")

    # 허용된 필드만 사용
    allowed_fields = {
        "domain_names", "forward_host", "forward_port", "forward_scheme",
        "enabled", "advanced_config", "locations", "meta",
        "certificate_id", "ssl_forced", "http2_support", "hsts_enabled",
        "hsts_subdomains", "block_exploits", "caching_enabled",
        "allow_websocket_upgrade", "access_list_id", "ssl_forced_https"
    }

    # 메인 forward_host 변경
    payload = {k: v for k, v in current.items() if k in allowed_fields and v is not None}
    payload['forward_host'] = NEW_FORWARD_HOST

    # locations의 forward_host도 변경
    locations = current.get('locations', [])[:]
    for loc in locations:
        if loc.get('forward_host') == 'frontend':
            loc['forward_host'] = NEW_FORWARD_HOST
    payload['locations'] = locations

    # 4. 업데이트 요청
    print("\n4. NPM에 업데이트 요청...")
    response = session.put(
        f'{npm_url}/api/nginx/proxy-hosts/{STOCK_HOST_ID}',
        json=payload,
        timeout=10
    )

    if response.status_code == 200:
        result = response.json()
        print("   ✅ 업데이트 성공!")
        print(f"\n   새 설정:")
        print(f"     forward_host: {result.get('forward_host')}")
        print(f"     forward_port: {result.get('forward_port')}")
        print(f"\n   locations:")
        for loc in result.get('locations', []):
            print(f"     - {loc.get('path')} → {loc.get('forward_host')}:{loc.get('forward_port')}")
    else:
        print(f"   ❌ 업데이트 실패: {response.status_code}")
        print(f"   응답: {response.text}")

if __name__ == "__main__":
    main()
