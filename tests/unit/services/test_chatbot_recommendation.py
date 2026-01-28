"""
Chatbot Recommender Unit Tests
종목 추천 기능을 테스트합니다.
"""

from unittest.mock import Mock, patch


# ============================================================================
# Test Data
# ============================================================================

MOCK_VCP_SIGNALS = [
    {"ticker": "005930", "signal_type": "vcp", "score": 85, "grade": "A"},
    {"ticker": "000660", "signal_type": "vcp", "score": 75, "grade": "B"},
    {"ticker": "035420", "signal_type": "vcp", "score": 65, "grade": "C"},
]

MOCK_JONGGA_SIGNALS = [
    {"ticker": "005930", "signal_type": "jongga_v2", "score": 10, "grade": "S"},
    {"ticker": "000660", "signal_type": "jongga_v2", "score": 8, "grade": "A"},
    {"ticker": "035420", "signal_type": "jongga_v2", "score": 5, "grade": "C"},
]


# ============================================================================
# StockRecommender Tests
# ============================================================================

class TestStockRecommender:
    """StockRecommender 클래스 테스트"""

    def test_import_recommender(self):
        """StockRecommender import 테스트"""
        from services.chatbot.recommender import StockRecommender
        assert StockRecommender is not None

    def test_init_recommender(self):
        """StockRecommender 초기화 테스트"""
        from services.chatbot.recommender import StockRecommender

        recommender = StockRecommender()
        assert recommender is not None
        assert recommender._retriever is not None

    @patch('services.chatbot.recommender.get_retriever')
    def test_recommend_by_vcp(self, mock_get_retriever):
        """VCP 기반 추천 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_retriever = Mock()
        mock_retriever.search_signals.return_value = MOCK_VCP_SIGNALS
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        results = recommender.recommend_by_vcp(min_score=70, min_grade="A", limit=10)

        # A등급 이상만 필터링
        assert len(results) == 1
        assert results[0]["ticker"] == "005930"

    @patch('services.chatbot.recommender.get_retriever')
    def test_recommend_by_vcp_all_grades(self, mock_get_retriever):
        """VCP 전체 등급 추천 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_retriever = Mock()
        mock_retriever.search_signals.return_value = MOCK_VCP_SIGNALS
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        results = recommender.recommend_by_vcp(min_score=60, min_grade="C", limit=10)

        assert len(results) == 3

    @patch('services.chatbot.recommender.get_retriever')
    def test_recommend_by_jongga(self, mock_get_retriever):
        """종가베팅 기반 추천 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_retriever = Mock()
        mock_retriever.search_signals.return_value = MOCK_JONGGA_SIGNALS
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        results = recommender.recommend_by_jongga(min_score=8, min_grade="A", limit=10)

        # A등급 이상만 필터링
        assert len(results) == 2
        assert results[0]["ticker"] == "005930"

    @patch('services.chatbot.recommender.get_retriever')
    def test_get_top_picks_both(self, mock_get_retriever):
        """종합 추천 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_retriever = Mock()
        # VCP와 종가베팅 다른 결과 반환
        mock_retriever.search_signals.side_effect = [
            MOCK_VCP_SIGNALS,  # vcp 호출
            MOCK_JONGGA_SIGNALS,  # jongga_v2 호출
        ]
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        results = recommender.get_top_picks(strategy="both", limit=10)

        # 중복 제거된 결과
        tickers = [r["ticker"] for r in results]
        assert len(tickers) == len(set(tickers))  # 중복 없음

    @patch('services.chatbot.recommender.get_retriever')
    def test_get_top_picks_vcp_only(self, mock_get_retriever):
        """VCP만 추천 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_retriever = Mock()
        mock_retriever.search_signals.return_value = MOCK_VCP_SIGNALS
        mock_retriever.search_stocks.return_value = []
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        results = recommender.get_top_picks(strategy="vcp", limit=5)

        assert len(results) <= 3  # VCP만

    @patch('services.chatbot.recommender.get_retriever')
    def test_get_position_size(self, mock_get_retriever):
        """포지션 사이즈 계산 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_get_retriever.return_value = Mock()

        recommender = StockRecommender()
        assert recommender.get_position_size("S") == 15.0
        assert recommender.get_position_size("A") == 12.0
        assert recommender.get_position_size("B") == 10.0
        assert recommender.get_position_size("C") == 5.0

    @patch('services.chatbot.recommender.get_retriever')
    def test_format_recommendation(self, mock_get_retriever):
        """추천 포맷팅 테스트"""
        from services.chatbot.recommender import StockRecommender

        # Mock Stock 객체 (dict로 반환)
        mock_stock_dict = {
            "ticker": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "sector": "반도체"
        }

        mock_retriever = Mock()
        mock_retriever.search_stocks.return_value = [mock_stock_dict]
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        formatted = recommender.format_recommendation({
            "ticker": "005930",
            "signal_type": "vcp",
            "grade": "A",
            "score": 85
        })

        assert "삼성전자(005930)" in formatted
        assert "VCP" in formatted
        assert "A등급" in formatted
        assert "85점" in formatted
        assert "12.0%" in formatted  # A등급 포지션

    @patch('services.chatbot.recommender.get_retriever')
    def test_exception_handling(self, mock_get_retriever):
        """예외 처리 테스트"""
        from services.chatbot.recommender import StockRecommender

        mock_retriever = Mock()
        mock_retriever.search_signals.side_effect = Exception("DB error")
        mock_get_retriever.return_value = mock_retriever

        recommender = StockRecommender()
        results = recommender.recommend_by_vcp()

        # 예외 발생 시 빈 리스트 반환
        assert results == []
