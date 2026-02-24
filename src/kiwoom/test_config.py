"""
키움 API 테스트용 설정

테스트 환경에서 타임아웃을 최적화하여 테스트 속도 개선
"""

from dataclasses import dataclass
from typing import Optional
from src.kiwoom.base import KiwoomConfig


@dataclass
class KiwoomTestConfig:
    """
    테스트용 키움 API 설정

    테스트 환경에서 타임아웃을 최적화하여 빠른 테스트 실행을 지원합니다.
    """
    # 기본 설정
    app_key: str = "test_app_key"
    secret_key: str = "test_secret"
    base_url: str = "https://mockapi.kiwoom.com"
    ws_url: str = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"

    # 모드 설정
    use_mock: bool = True
    debug_mode: bool = False

    # 테스트 최적화 타임아웃 설정
    # - 연결 타임아웃: 3초 (기본 5초)
    # - 수신 타임아웃: 10초 (기본 60초)
    # - 핑 타임아웃: 5초 (기본 10초)
    ws_connect_timeout: int = 3
    ws_recv_timeout: int = 10
    ws_ping_timeout: int = 5
    ws_ping_interval: Optional[int] = None

    # 재연결 설정
    max_reconnect_attempts: int = 2  # 테스트에서는 2회로 제한
    reconnect_delay: float = 0.5  # 테스트에서는 빠른 재시도

    def to_kiwoom_config(self) -> KiwoomConfig:
        """KiwoomConfig 객체로 변환"""
        return KiwoomConfig(
            app_key=self.app_key,
            secret_key=self.secret_key,
            base_url=self.base_url,
            ws_url=self.ws_url,
            use_mock=self.use_mock,
            debug_mode=self.debug_mode,
            ws_ping_interval=self.ws_ping_interval,
            ws_ping_timeout=self.ws_ping_timeout,
            ws_recv_timeout=self.ws_recv_timeout,
        )

    @classmethod
    def fast(cls) -> 'KiwoomTestConfig':
        """
        초고속 테스트용 설정 (CI/CD 환경 권장)

        - 수신 타임아웃: 5초
        - 연결 타임아웃: 2초
        """
        return cls(
            ws_connect_timeout=2,
            ws_recv_timeout=5,
            ws_ping_timeout=3,
            reconnect_delay=0.3,
        )

    @classmethod
    def standard(cls) -> 'KiwoomTestConfig':
        """표준 테스트용 설정"""
        return cls()

    @classmethod
    def integration(cls) -> 'KiwoomTestConfig':
        """
        통합 테스트용 설정 (느린 외부 API 고려)

        - 수신 타임아웃: 30초
        - 연결 타임아웃: 10초
        """
        return cls(
            ws_connect_timeout=10,
            ws_recv_timeout=30,
            ws_ping_timeout=10,
            max_reconnect_attempts=5,
        )
