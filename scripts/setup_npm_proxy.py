#!/usr/bin/env python3
"""
Nginx Proxy Manager Proxy Host 설정 스크립트

stock.ralphpark.com 도메인을 추가하고 WebSocket 설정을 구성합니다.

사용법:
    python scripts/setup_npm_proxy.py

환경 변수 (.env.npm):
    NPM_URL: NPM 관리 URL (예: http://112.219.120.75:81)
    NPM_EMAIL: NPM 관리자 이메일
    NPM_PASSWORD: NPM 관리자 비밀번호
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class NginxProxyManager:
    """Nginx Proxy Manager API 클라이언트"""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token = None
        self.session = requests.Session()

    def login(self) -> bool:
        """NPM에 로그인하여 토큰 발급"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/tokens",
                json={"identity": self.email, "secret": self.password},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.token = data.get("token")
            if self.token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                })
                print(f"✅ NPM 로그인 성공: {self.base_url}")
                return True
            return False
        except requests.RequestException as e:
            print(f"❌ NPM 로그인 실패: {e}")
            return False

    def get_proxy_hosts(self) -> list:
        """모든 프록시 호스트 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/nginx/proxy-hosts",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ 프록시 호스트 조회 실패: {e}")
            return []

    def find_proxy_host(self, domain: str) -> dict | None:
        """도메인으로 프록시 호스트 찾기"""
        hosts = self.get_proxy_hosts()
        for host in hosts:
            if domain in host.get("domain_names", []):
                return host
        return None

    def check_websocket_config(self, host: dict) -> dict:
        """
        WebSocket 설정 상태 확인

        Returns:
            {
                'enabled': bool,           # allow_websocket_upgrade
                'ws_location': bool,       # /ws 경로 존재 여부
                'ws_port': int|None,       # /ws가 포워드하는 포트
                'api_port': int|None,      # /api가 포워드하는 포트
                'main_port': int           # 메인 포워드 포트
            }
        """
        result = {
            'enabled': host.get('allow_websocket_upgrade', False),
            'ws_location': False,
            'ws_port': None,
            'api_port': None,
            'main_port': host.get('forward_port')
        }

        # locations 필드 확인 (NPM은 locations를 사용)
        for location in host.get('locations', []):
            if location.get('path') == '/ws':
                result['ws_location'] = True
                result['ws_port'] = location.get('forward_port')
            elif location.get('path') == '/api':
                result['api_port'] = location.get('forward_port')

        return result

    def create_proxy_host(
        self,
        domain: str,
        forward_host: str,
        forward_port: int,
        forward_scheme: str = "http",
        enabled: bool = True,
        websocket_support: bool = True,
        api_backend_port: int = 5111
    ) -> dict | None:
        """
        프록시 호스트 생성

        Args:
            domain: 프록시 도메인 (예: stock.ralphpark.com)
            forward_host: 포워딩할 호스트 (예: 112.219.120.75 또는 172.17.0.1)
            forward_port: 메인 포워딩 포트 (프론트엔드용, 예: 5110)
            forward_scheme: 포워딩 스킴 (http/https)
            enabled: 활성화 여부
            websocket_support: WebSocket 지원 여부
            api_backend_port: API/WebSocket 백엔드 포트 (예: 5111)
        """
        # NPM API에서는 locations를 사용
        locations = []
        if websocket_support:
            # /api 경로를 API Gateway로
            locations.append({
                "path": "/api",
                "forward_scheme": forward_scheme,
                "forward_host": forward_host,
                "forward_port": api_backend_port
            })
            # /ws 경로를 API Gateway WebSocket으로
            locations.append({
                "path": "/ws",
                "forward_scheme": forward_scheme,
                "forward_host": forward_host,
                "forward_port": api_backend_port
            })

        # Advanced config for WebSocket headers
        advanced_config = """proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
add_header Cache-Control "no-store, no-cache, must-revalidate";
add_header Pragma "no-cache";""" if websocket_support else ""

        payload = {
            "domain_names": [domain],
            "forward_host": forward_host,
            "forward_port": forward_port,
            "forward_scheme": forward_scheme,
            "enabled": enabled,
            "advanced_config": advanced_config,
            "locations": locations,
            "meta": {
                "letsencrypt_agree": False,
                "dns_challenge": False
            },
            "certificate_id": None,
            "ssl_forced": False,
            "http2_support": False,
            "hsts_enabled": False,
            "hsts_subdomains": False,
            "block_exploits": False,
            "caching_enabled": False,
            "allow_websocket_upgrade": websocket_support
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/nginx/proxy-hosts",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            print(f"✅ 프록시 호스트 생성 성공: {domain}")
            print(f"   메인: {forward_host}:{forward_port}")
            if websocket_support:
                print(f"   /api, /ws → {forward_host}:{api_backend_port}")
            return result
        except requests.RequestException as e:
            print(f"❌ 프록시 호스트 생성 실패 ({domain}): {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"   응답: {e.response.text}")
            return None

    def update_proxy_host(
        self,
        host_id: int,
        domain: str,
        forward_host: str,
        forward_port: int,
        websocket_support: bool = True,
        api_backend_port: int = 5111
    ) -> dict | None:
        """프록시 호스트 업데이트"""
        # 먼저 현재 설정 조회
        try:
            response = self.session.get(
                f"{self.base_url}/api/nginx/proxy-hosts/{host_id}",
                timeout=10
            )
            response.raise_for_status()
            current_config = response.json()
        except requests.RequestException as e:
            print(f"❌ 현재 설정 조회 실패: {e}")
            return None

        # NPM API가 허용하는 필드만 유지 (실제 API 응답 기반)
        allowed_fields = {
            "domain_names", "forward_host", "forward_port", "forward_scheme",
            "enabled", "advanced_config", "locations", "meta",
            "certificate_id", "ssl_forced", "http2_support", "hsts_enabled",
            "hsts_subdomains", "block_exploits", "caching_enabled",
            "allow_websocket_upgrade", "access_list_id"
        }

        # locations 확인 및 업데이트
        locations = current_config.get("locations", [])[:]
        has_api_location = any(loc.get("path") == "/api" for loc in locations)
        has_ws_location = any(loc.get("path") == "/ws" for loc in locations)

        if websocket_support:
            # /api 위치가 없으면 추가
            if not has_api_location:
                locations.append({
                    "path": "/api",
                    "forward_scheme": current_config.get("forward_scheme", "http"),
                    "forward_host": current_config.get("forward_host", forward_host),
                    "forward_port": api_backend_port
                })
            else:
                # 기존 /api가 있으면 포트만 업데이트
                for loc in locations:
                    if loc.get("path") == "/api":
                        loc["forward_port"] = api_backend_port

            # /ws 위치가 없으면 추가
            if not has_ws_location:
                locations.append({
                    "path": "/ws",
                    "forward_scheme": current_config.get("forward_scheme", "http"),
                    "forward_host": current_config.get("forward_host", forward_host),
                    "forward_port": api_backend_port
                })
            else:
                # 기존 /ws가 있으면 포트만 업데이트
                for loc in locations:
                    if loc.get("path") == "/ws":
                        loc["forward_port"] = api_backend_port

        # Advanced config에 WebSocket 헤더가 없으면 추가
        advanced_config = current_config.get("advanced_config", "") or ""
        if "Upgrade $http_upgrade" not in advanced_config and websocket_support:
            if advanced_config:
                advanced_config += "\n"
            advanced_config += """proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
add_header Cache-Control "no-store, no-cache, must-revalidate";
add_header Pragma "no-cache";"""

        # 필요한 필드만 포함하는 payload 생성
        payload = {
            "domain_names": current_config.get("domain_names", []),
            "forward_host": current_config.get("forward_host"),
            "forward_port": current_config.get("forward_port"),
            "forward_scheme": current_config.get("forward_scheme", "http"),
            "enabled": current_config.get("enabled", True),
            "advanced_config": advanced_config.strip(),
            "locations": locations,
            "meta": current_config.get("meta", {}),
            "certificate_id": current_config.get("certificate_id"),
            "ssl_forced": current_config.get("ssl_forced", False),
            "http2_support": current_config.get("http2_support", False),
            "hsts_enabled": current_config.get("hsts_enabled", False),
            "hsts_subdomains": current_config.get("hsts_subdomains", False),
            "block_exploits": current_config.get("block_exploits", False),
            "caching_enabled": current_config.get("caching_enabled", False),
            "allow_websocket_upgrade": websocket_support,
            "access_list_id": current_config.get("access_list_id", 0),
        }

        # None 값 필터링
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = self.session.put(
                f"{self.base_url}/api/nginx/proxy-hosts/{host_id}",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            print(f"✅ 프록시 호스트 업데이트 성공: {domain}")
            return result
        except requests.RequestException as e:
            print(f"❌ 프록시 호스트 업데이트 실패 ({domain}): {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"   응답: {e.response.text}")
            return None


def setup_stock_subdomain(npm: NginxProxyManager, forward_host: str, forward_port: int = 5111, api_backend_port: int = 5111):
    """
    stock.ralphpark.com 서브도메인 설정

    Nginx Proxy Manager에서 stock.ralphpark.com을 추가하고
    WebSocket 설정을 구성합니다.
    """
    domain = "stock.ralphpark.com"

    # 기존 호스트 확인
    existing = npm.find_proxy_host(domain)
    if existing:
        print(f"ℹ️  기존 프록시 호스트 발견: {domain} (ID: {existing.get('id')})")
        ws_config = npm.check_websocket_config(existing)

        print(f"   WebSocket 설정 상태:")
        print(f"     - allow_websocket_upgrade: {ws_config['enabled']}")
        print(f"     - /ws location: {ws_config['ws_location']} (포트: {ws_config['ws_port']})")
        print(f"     - /api location: 포트 {ws_config['api_port']}")
        print(f"     - 메인 포워드: {ws_config['main_port']}")

        # WebSocket 또는 /api location이 올바르게 설정되지 않았으면 업데이트
        if not ws_config['ws_location'] or ws_config['ws_port'] != api_backend_port or ws_config['api_port'] != api_backend_port:
            print("   → WebSocket/API 설정이 필요합니다. 업데이트합니다...")
            npm.update_proxy_host(
                existing["id"],
                domain,
                forward_host,
                forward_port,
                websocket_support=True,
                api_backend_port=api_backend_port
            )
        else:
            print(f"   ✅ 이미 WebSocket/API 설정이 올바르게 되어 있습니다.")
        return existing

    # 새 프록시 호스트 생성
    print(f"ℹ️  새 프록시 호스트 생성: {domain}")
    return npm.create_proxy_host(
        domain=domain,
        forward_host=forward_host,
        forward_port=forward_port,
        forward_scheme="http",
        enabled=True,
        websocket_support=True,
        api_backend_port=api_backend_port
    )


def verify_ralphpark_domain(npm: NginxProxyManager, domain: str = "ralphpark.com"):
    """
    ralphpark.com 도메인의 WebSocket 설정 확인
    """
    print(f"\nℹ️  {domain} 도메인 WebSocket 설정 확인...")

    # 기존 호스트 확인 (정확히 일치하지 않으면 포함 확인)
    hosts = npm.get_proxy_hosts()
    for host in hosts:
        domain_names = host.get("domain_names", [])
        if domain in domain_names or any(domain in d for d in domain_names):
            print(f"   발견: {', '.join(domain_names)} (ID: {host.get('id')})")

            # WebSocket 설정 확인
            ws_config = npm.check_websocket_config(host)

            if ws_config['enabled'] or ws_config['ws_location']:
                print(f"   ✅ WebSocket 설정 완료")
                print(f"      - allow_websocket_upgrade: {ws_config['enabled']}")
                print(f"      - /ws location: {ws_config['ws_location']} (포트: {ws_config['ws_port']})")
                print(f"      - /api location: 포트 {ws_config['api_port']}")
            else:
                print(f"   ⚠️  WebSocket 설정이 없습니다.")
                print(f"   → 설정이 필요합니다.")
            return host

    print(f"   ⚠️  {domain} 도메인을 찾을 수 없습니다.")
    return None


def main():
    """메인 함수"""
    # .env.npm 파일 로드
    env_file = project_root / ".env.npm"
    if not env_file.exists():
        print(f"❌ .env.npm 파일을 찾을 수 없습니다: {env_file}")
        print("   다음 내용으로 .env.npm 파일을 생성하세요:")
        print("   NPM_URL=http://your-npm-ip:81")
        print("   NPM_EMAIL=your-email@example.com")
        print("   NPM_PASSWORD=your-password")
        sys.exit(1)

    load_dotenv(env_file)

    npm_url = os.getenv("NPM_URL")
    npm_email = os.getenv("NPM_EMAIL")
    npm_password = os.getenv("NPM_PASSWORD")

    if not all([npm_url, npm_email, npm_password]):
        print("❌ .env.npm 파일에 필요한 환경 변수가 누락되었습니다.")
        print("   필요한 변수: NPM_URL, NPM_EMAIL, NPM_PASSWORD")
        sys.exit(1)

    # NPM 클라이언트 초기화
    npm = NginxProxyManager(npm_url, npm_email, npm_password)

    # 로그인
    if not npm.login():
        sys.exit(1)

    # 현재 프록시 호스트 목록 표시
    print("\n" + "=" * 50)
    print("현재 프록시 호스트 목록:")
    print("=" * 50)
    hosts = npm.get_proxy_hosts()
    if hosts:
        for host in hosts:
            domains = ", ".join(host.get("domain_names", []))
            forward = f"{host.get('forward_scheme', 'http')}://{host.get('forward_host')}:{host.get('forward_port')}"
            enabled = "✅" if host.get("enabled") else "❌"
            ws = "🔌" if host.get("allow_websocket_upgrade") else "❌"
            print(f"   {enabled} {ws} {domains} → {forward}")
    else:
        print("   (프록시 호스트 없음)")

    # ralphpark.com 도메인 확인
    print("\n" + "=" * 50)
    print("기존 도메인 확인:")
    print("=" * 50)
    verify_ralphpark_domain(npm, "ralphpark.com")

    # stock.ralphpark.com 설정
    print("\n" + "=" * 50)
    print("stock.ralphpark.com 서브도메인 설정:")
    print("=" * 50)

    # 포워딩할 호스트 결정 (Docker 네트워크 내부 IP 또는 호스트 IP)
    # Docker 네트워크에서 실행 중인 경우 host.docker.internal 사용 가능
    # 아니면 호스트의 실제 IP 사용
    forward_host = "172.17.0.1"  # Docker 기본 게이트웨이 (기존 설정과 동일)

    # stock.ralphpark.com의 포트 구성:
    # - 메인 포워드: 5110 (Frontend)
    # - /api, /ws: 5111 (API Gateway)
    frontend_port = 5110
    api_port = 5111

    print(f"\n설정값:")
    print(f"  도메인: stock.ralphpark.com")
    print(f"  포워드 호스트: {forward_host}")
    print(f"  메인 포워드 (Frontend): {frontend_port}")
    print(f"  /api, /ws (API Gateway): {api_port}")
    print(f"  WebSocket: 지원")

    result = setup_stock_subdomain(
        npm,
        forward_host=forward_host,
        forward_port=frontend_port,
        api_backend_port=api_port
    )

    if result:
        print("\n" + "=" * 50)
        print("✅ 설정 완료!")
        print("=" * 50)
        print("\n다음 URL에서 접속 가능:")
        print("  - Frontend: http://stock.ralphpark.com")
        print("  - API: http://stock.ralphpark.com/api")
        print("  - WebSocket: ws://stock.ralphpark.com/ws")
        print("\nDNS 설정이 되어 있어야 합니다.")
        print("  stock.ralphpark.com A 레코드 → 서버 IP")
    else:
        print("\n❌ 설정 실패")


if __name__ == "__main__":
    main()
