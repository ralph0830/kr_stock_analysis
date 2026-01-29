"""
Chatbot Recommendations Endpoint Tests (TDD: RED Phase)
GET /recommendations 엔드포인트 테스트
먼저 실패하는 테스트를 작성하고, 그 후에 구현합니다.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


# ============================================================================
# Test Data
# ============================================================================

MOCK_RECOMMENDATIONS = [
    {
        "ticker": "005930",
        "name": "삼성전자",
        "signal_type": "vcp",
        "grade": "A",
        "score": 85,
        "position_size": 12.0,
    },
    {
        "ticker": "000660",
        "name": "SK하이닉스",
        "signal_type": "jongga_v2",
        "grade": "S",
        "score": 10,
        "position_size": 15.0,
    },
]


# ============================================================================
# GET /recommendations Endpoint Tests (RED Phase)
# ============================================================================

class TestRecommendationsEndpoint:
    """GET /recommendations 엔드포인트 테스트"""

    def test_import_app(self):
        """FastAPI app import 테스트"""
        from services.chatbot.main import app
        assert app is not None

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_vcp_strategy(self, mock_get_recommender):
        """VCP 전략 추천 테스트"""
        from services.chatbot.main import app

        # Mock recommender - MagicMock 사용하여 순환 참조 방지
        mock_recommender = MagicMock()
        mock_recommender.get_top_picks.return_value = MOCK_RECOMMENDATIONS
        mock_recommender.get_position_size.return_value = 12.0
        mock_get_recommender.return_value = mock_recommender

        client = TestClient(app)
        response = client.get("/recommendations?strategy=vcp&limit=5")

        # 이 테스트는 현재 실패해야 합니다 (RED Phase)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        mock_recommender.get_top_picks.assert_called_once_with(strategy="vcp", limit=5)

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_both_strategy(self, mock_get_recommender):
        """both 전략 추천 테스트 (VCP + 종가베팅)"""
        from services.chatbot.main import app

        mock_recommender = MagicMock()
        mock_recommender.get_top_picks.return_value = MOCK_RECOMMENDATIONS
        mock_recommender.get_position_size.return_value = 12.0
        mock_get_recommender.return_value = mock_recommender

        client = TestClient(app)
        response = client.get("/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 기본값은 both
        mock_recommender.get_top_picks.assert_called_once_with(strategy="both", limit=5)

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_with_custom_limit(self, mock_get_recommender):
        """사용자 지정 limit 파라미터 테스트"""
        from services.chatbot.main import app

        mock_recommender = MagicMock()
        mock_recommender.get_top_picks.return_value = MOCK_RECOMMENDATIONS[:1]
        mock_recommender.get_position_size.return_value = 15.0
        mock_get_recommender.return_value = mock_recommender

        client = TestClient(app)
        response = client.get("/recommendations?limit=3")

        assert response.status_code == 200
        mock_recommender.get_top_picks.assert_called_once_with(strategy="both", limit=3)

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_empty_result(self, mock_get_recommender):
        """빈 추천 결과 테스트"""
        from services.chatbot.main import app

        mock_recommender = MagicMock()
        mock_recommender.get_top_picks.return_value = []
        mock_get_recommender.return_value = mock_recommender

        client = TestClient(app)
        response = client.get("/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_response_structure(self, mock_get_recommender):
        """응답 구조 검증 테스트"""
        from services.chatbot.main import app

        mock_recommender = MagicMock()
        mock_recommender.get_top_picks.return_value = MOCK_RECOMMENDATIONS
        mock_recommender.get_position_size.return_value = 12.0
        mock_get_recommender.return_value = mock_recommender

        client = TestClient(app)
        response = client.get("/recommendations")

        assert response.status_code == 200
        data = response.json()

        # 응답 구조 검증
        for item in data:
            assert "ticker" in item
            assert "name" in item
            assert "signal_type" in item
            assert "grade" in item
            assert "score" in item
            assert "position_size" in item

    @patch('services.chatbot.main.get_recommender')
    def test_get_recommendations_exception_handling(self, mock_get_recommender):
        """예외 처리 테스트"""
        from services.chatbot.main import app

        mock_recommender = MagicMock()
        mock_recommender.get_top_picks.side_effect = Exception("Service error")
        mock_get_recommender.return_value = mock_recommender

        client = TestClient(app)
        response = client.get("/recommendations")

        # 예외 발생 시 200 OK와 빈 리스트 반환 (서비스 중단 방지)
        assert response.status_code == 200
        assert response.json() == []
