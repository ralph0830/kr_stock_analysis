"""
HTTP 서비스 Mock 서버

API Gateway, VCP Scanner, Signal Engine, Chatbot 등의
마이크로서비스 Health Check를 Mock 처리합니다.
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime
from unittest.mock import MagicMock


class MockServiceServer:
    """
    마이크로서비스 Mock 서버

    실제 서비스 실행 없이 Health Check 응답을 제공합니다.
    """

    def __init__(self):
        """Mock 서버 초기화"""
        self.services: Dict[str, Dict[str, Any]] = {}
        self._init_default_services()

    def _init_default_services(self):
        """기본 서비스 상태 초기화"""
        default_services = {
            "api_gateway": {
                "status": "healthy",
                "port": 5111,
                "dependencies": ["vcp_scanner", "signal_engine", "chatbot"]
            },
            "vcp_scanner": {
                "status": "healthy",
                "port": 5112,
                "dependencies": []
            },
            "signal_engine": {
                "status": "healthy",
                "port": 5113,
                "dependencies": []
            },
            "chatbot": {
                "status": "healthy",
                "port": 5114,
                "dependencies": []
            },
            "daytrading_scanner": {
                "status": "healthy",
                "port": 5115,
                "dependencies": []
            }
        }

        for name, config in default_services.items():
            self.services[name] = config

    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """
        서비스 Health Check 응답 반환

        Args:
            service_name: 서비스 이름 (예: api_gateway)

        Returns:
            Health Check 응답 딕셔너리
        """
        service = self.services.get(service_name)

        if not service:
            return {
                "status": "error",
                "message": f"Service {service_name} not found"
            }

        return {
            "status": service["status"],
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "port": service["port"],
            "dependencies": service.get("dependencies", [])
        }

    def set_service_status(self, service_name: str, status: str):
        """
        서비스 상태 변경

        Args:
            service_name: 서비스 이름
            status: 상태 (healthy, unhealthy, error)
        """
        if service_name in self.services:
            self.services[service_name]["status"] = status

    def set_service_unhealthy(self, service_name: str):
        """서비스를 unhealthy 상태로 설정"""
        self.set_service_status(service_name, "unhealthy")

    def set_service_healthy(self, service_name: str):
        """서비스를 healthy 상태로 설정"""
        self.set_service_status(service_name, "healthy")

    def get_all_services_status(self) -> Dict[str, Any]:
        """전체 서비스 상태 반환"""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: config["status"]
                for name, config in self.services.items()
            }
        }


def create_mock_response(
    status_code: int = 200,
    data: Optional[Dict[str, Any]] = None,
    message: str = "success"
) -> Dict[str, Any]:
    """
    Mock HTTP 응답 생성

    Args:
        status_code: HTTP 상태 코드
        data: 응답 데이터
        message: 응답 메시지

    Returns:
        Mock 응답 딕셔너리
    """
    response = {
        "status_code": status_code,
        "message": message
    }

    if data:
        response["data"] = data

    return response


# ============================================================================
# Pytest Fixtures
# ============================================================================

import pytest


@pytest.fixture
def mock_service_server():
    """
    Mock 서비스 서버 Fixture

    Example:
        def test_api_gateway_health(mock_service_server):
            response = mock_service_server.get_service_health("api_gateway")
            assert response["status"] == "healthy"
    """
    server = MockServiceServer()
    return server


@pytest.fixture
def mock_service_responses():
    """
    Mock 서비스 응답 Fixture

    다양한 API 응답을 Mock 처리합니다.

    Example:
        def test_with_mock_responses(mock_service_responses):
            health_response = mock_service_responses["health_check"]
            assert health_response["status"] == "healthy"
    """
    return {
        # Health Check 응답
        "health_check": {
            "status": "healthy",
            "timestamp": "2026-02-06T00:00:00Z",
            "services": {
                "vcp_scanner": "healthy",
                "signal_engine": "healthy",
                "chatbot": "healthy",
                "daytrading_scanner": "healthy"
            }
        },

        # VCP Scanner 응답
        "vcp_signals": {
            "signals": [],
            "total": 0,
            "timestamp": "2026-02-06T00:00:00Z"
        },

        # Signal Engine 응답
        "jongga_signals": {
            "signals": [],
            "total": 0,
            "timestamp": "2026-02-06T00:00:00Z"
        },

        # Daytrading Scanner 응답
        "daytrading_signals": {
            "signals": [],
            "total": 0,
            "timestamp": "2026-02-06T00:00:00Z"
        },

        # Market Gate 응답
        "market_status": {
            "status": "open",
            "market_time": "09:00:00",
            "next_close_time": "15:30:00"
        },

        # AI 분석 응답
        "ai_analysis": {
            "ticker": "005930",
            "sentiment_score": 0.75,
            "recommendation": "buy",
            "confidence": 0.85,
            "created_at": "2026-02-06T00:00:00Z"
        },

        # 백테스트 응답
        "backtest_result": {
            "config_name": "test_config",
            "total_trades": 100,
            "win_rate": 0.65,
            "total_return": 0.15,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.8
        },

        # 종목 정보 응답
        "stock_info": {
            "ticker": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "sector": "전자",
            "close_price": 80500,
            "change": 500,
            "change_rate": 0.62
        },

        # 차트 데이터 응답
        "chart_data": {
            "ticker": "005930",
            "data": [
                {
                    "date": "2026-02-06",
                    "open": 80000,
                    "high": 81000,
                    "low": 79500,
                    "close": 80500,
                    "volume": 1000000
                }
            ]
        }
    }


@pytest.fixture
def mock_requests(monkeypatch):
    """
    requests 라이브러리 Mock Fixture

    실제 HTTP 요청 없이 테스트합니다.

    Example:
        def test_with_mock_requests(mock_requests, mock_service_responses):
            mock_requests.get.return_value.json.return_value = mock_service_responses["health_check"]
            mock_requests.get.return_value.status_code = 200

            response = requests.get("http://localhost:5111/health")
            assert response.status_code == 200
    """
    from unittest.mock import MagicMock

    mock = MagicMock()

    # GET 요청 Mock
    mock.get = MagicMock()
    mock.get.return_value.status_code = 200
    mock.get.return_value.json.return_value = {"status": "healthy"}

    # POST 요청 Mock
    mock.post = MagicMock()
    mock.post.return_value.status_code = 200
    mock.post.return_value.json.return_value = {"result": "success"}

    # PUT 요청 Mock
    mock.put = MagicMock()
    mock.put.return_value.status_code = 200
    mock.put.return_value.json.return_value = {"result": "updated"}

    # DELETE 요청 Mock
    mock.delete = MagicMock()
    mock.delete.return_value.status_code = 200
    mock.delete.return_value.json.return_value = {"result": "deleted"}

    monkeypatch.setattr("requests.get", mock.get)
    monkeypatch.setattr("requests.post", mock.post)
    monkeypatch.setattr("requests.put", mock.put)
    monkeypatch.setattr("requests.delete", mock.delete)

    return mock
