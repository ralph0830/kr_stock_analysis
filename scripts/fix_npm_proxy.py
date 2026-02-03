#!/usr/bin/env python3
"""Nginx Proxy Manager forward_host 수정 스크립트"""
import os
import requests
from dotenv import load_dotenv

load_dotenv('.env.npm')

npm_url = os.getenv('NPM_URL')
npm_email = os.getenv('NPM_EMAIL')
npm_password = os.getenv('NPM_PASSWORD')

# 로그인
session = requests.Session()
response = session.post(f'{npm_url}/api/tokens', json={'identity': npm_email, 'secret': npm_password}, timeout=10)
token = response.json()['token']
session.headers.update({'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})

# 현재 설정 조회
host_id = 33  # stock.ralphpark.com
response = session.get(f'{npm_url}/api/nginx/proxy-hosts/{host_id}', timeout=10)
current = response.json()

print(f"Current forward_host: {current.get('forward_host')}")
print(f"Current forward_port: {current.get('forward_port')}")

# 업데이트 - 허용된 필드만 사용
allowed_fields = {
    "domain_names", "forward_host", "forward_port", "forward_scheme",
    "enabled", "advanced_config", "locations", "meta",
    "certificate_id", "ssl_forced", "http2_support", "hsts_enabled",
    "hsts_subdomains", "block_exploits", "caching_enabled",
    "allow_websocket_upgrade", "access_list_id", "ssl_forced_https"
}

# locations의 forward_host도 변경
locations = current.get('locations', [])[:]
for loc in locations:
    loc['forward_host'] = '112.219.120.75'

payload = {k: v for k, v in current.items() if k in allowed_fields}
payload['forward_host'] = '112.219.120.75'
payload['locations'] = locations

# None 값 제거
payload = {k: v for k, v in payload.items() if v is not None}

response = session.put(f'{npm_url}/api/nginx/proxy-hosts/{host_id}', json=payload, timeout=10)
print(f"\nUpdate status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✅ Updated forward_host to: {result.get('forward_host')}")
else:
    print(f"❌ Error: {response.text}")
