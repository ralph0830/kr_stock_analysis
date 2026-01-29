"""
System Routes 테스트
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from services.api_gateway.main import app
from src.database.models import DailyPrice, Signal


class TestDataStatusAPI:
    """Data Status API 테스트"""

    def test_data_status_returns_structure(self):
        """Data Status API가 기본 구조를 반환해야 함"""
        client = TestClient(app)
        response = client.get("/api/system/data-status")

        assert response.status_code == 200
        data = response.json()

        # 필수 필드 확인
        assert "total_stocks" in data
        assert "updated_stocks" in data
        assert "data_files" in data
        assert "details" in data
        assert isinstance(data["details"], list)

    def test_data_status_prices_field(self):
        """prices 데이터 상태를 올바르게 조회해야 함"""
        client = TestClient(app)
        response = client.get("/api/system/data-status")

        assert response.status_code == 200
        data = response.json()

        # prices 필드가 존재하고 에러 상태가 아니어야 함
        assert "prices" in data["data_files"]
        # 에러 메시지가 있으면 실패 (현재 "DailyPrice.id has no attribute 'id'" 에러)
        prices_detail = next((d for d in data["details"] if d["name"] == "prices"), None)
        if prices_detail:
            # 에러가 있어서는 안 됨
            assert prices_detail["status"] in ["OK", "NO_DATA"]
            assert "error_message" not in prices_detail or prices_detail.get("error_message") is None

    @patch("services.api_gateway.routes.system.get_db_session")
    def test_data_status_with_mock_data(self, mock_get_db_session):
        """Mock 데이터로 정상 응답을 확인"""
        # Mock session 설정
        mock_session = Mock()
        mock_get_db_session.return_value = mock_session

        # Mock StockRepository
        with patch("services.api_gateway.routes.system.StockRepository") as mock_repo_cls:
            mock_repo = Mock()
            mock_repo.count.return_value = 100
            mock_repo_cls.return_value = mock_repo

            # Mock SignalRepository
            with patch("services.api_gateway.routes.system.SignalRepository") as mock_signal_repo_cls:
                mock_signal_repo = Mock()
                mock_signal_repo.count.return_value = 50
                mock_signal_repo_cls.return_value = mock_signal_repo

                # Mock DailyPrice count (Composite primary key 사용)
                with patch("services.api_gateway.routes.system.func") as mock_func:
                    # DailyPrice는 복합 기본 키를 사용하므로 count(*)를 사용해야 함
                    mock_func.count.return_value.scalar.return_value = 1000
                    mock_func.max.return_value.scalar.return_value = "2026-01-29"

                    # Mock Signal count
                    with patch.object(mock_signal_repo, "count", return_value=50):
                        with patch("services.api_gateway.routes.system.select"):
                            client = TestClient(app)
                            response = client.get("/api/system/data-status")

                            assert response.status_code == 200
                            data = response.json()

                            # 데이터 확인
                            assert data["total_stocks"] == 100
                            # prices는 복합 기본 키이므로 별도 처리 필요
