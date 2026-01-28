"""
Chatbot Retriever Unit Tests
RAG 기반 지식 검색 기능을 테스트합니다.
"""

from unittest.mock import Mock, patch


# ============================================================================
# Test Data
# ============================================================================

MOCK_STOCKS = [
    {"ticker": "005930", "name": "삼성전자", "market": "KOSPI", "sector": "반도체"},
    {"ticker": "000660", "name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
    {"ticker": "035420", "name": "NAVER", "market": "KOSPI", "sector": "IT"},
]

MOCK_SIGNALS = [
    {
        "ticker": "005930",
        "name": "삼성전자",
        "signal_type": "vcp",
        "score": 85.0,
        "grade": "A",
        "created_at": "2026-01-28",
    },
    {
        "ticker": "000660",
        "name": "SK하이닉스",
        "signal_type": "jongga_v2",
        "score": 10,
        "grade": "S",
        "created_at": "2026-01-28",
    },
]

MOCK_NEWS = [
    {
        "ticker": "005930",
        "title": "삼성전자, 신기술 개발 발표",
        "sentiment": "positive",
        "score": 0.8,
    },
    {
        "ticker": "035420",
        "title": "NAVER, AI 서비스 확대",
        "sentiment": "positive",
        "score": 0.6,
    },
]

MOCK_MARKET_STATUS = {
    "status": "YELLOW",
    "level": 50,
    "kospi_status": "소폭 상승",
    "kosdaq_status": "소폭 하락",
}


# ============================================================================
# KnowledgeRetriever Tests (RED Phase)
# ============================================================================

class TestKnowledgeRetriever:
    """KnowledgeRetriever 클래스 테스트"""

    def test_import_retriever(self):
        """KnowledgeRetriever import 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever
        assert KnowledgeRetriever is not None

    def test_init_retriever(self):
        """KnowledgeRetriever 초기화 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        assert retriever is not None

    def test_search_stocks_empty_query(self):
        """빈 쿼리 처리 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        results = retriever.search_stocks("")

        assert results == []

    def test_search_stocks_short_query(self):
        """짧은 쿼리 처리 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        results = retriever.search_stocks("삼")

        assert results == []

    @patch('services.chatbot.retriever.KnowledgeRetriever._get_stock_repo')
    def test_search_stocks_by_name(self, mock_get_repo):
        """종목명으로 검색 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        # Mock 설정
        mock_stock1 = Mock()
        mock_stock1.ticker = "005930"
        mock_stock1.name = "삼성전자"
        mock_stock1.market = "KOSPI"
        mock_stock1.sector = "반도체"

        mock_repo = Mock()
        mock_repo.search.return_value = [mock_stock1]
        mock_get_repo.return_value = mock_repo

        retriever = KnowledgeRetriever()
        results = retriever.search_stocks("삼성")

        assert len(results) >= 1
        assert results[0]["name"] == "삼성전자"

    @patch('services.chatbot.retriever.KnowledgeRetriever._get_stock_repo')
    def test_search_stocks_by_ticker(self, mock_get_repo):
        """티커로 검색 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        mock_stock = Mock()
        mock_stock.ticker = "005930"
        mock_stock.name = "삼성전자"
        mock_stock.market = "KOSPI"
        mock_stock.sector = "반도체"

        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = mock_stock
        mock_get_repo.return_value = mock_repo

        retriever = KnowledgeRetriever()
        results = retriever.search_stocks("005930")

        assert len(results) >= 1
        assert results[0]["ticker"] == "005930"

    @patch('services.chatbot.retriever.KnowledgeRetriever._get_signal_repo')
    def test_search_signals(self, mock_get_repo):
        """시그널 검색 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        # Mock Signal 객체
        mock_signal = Mock()
        mock_signal.ticker = "005930"
        mock_signal.name = None
        mock_signal.signal_type = "vcp"
        mock_signal.score = 85.0
        mock_signal.grade = "A"
        mock_signal.signal_date = Mock()
        mock_signal.signal_date.isoformat.return_value = "2026-01-28"

        mock_repo = Mock()
        mock_repo.get_active.return_value = [mock_signal]
        mock_get_repo.return_value = mock_repo

        retriever = KnowledgeRetriever()
        results = retriever.search_signals(limit=10)

        assert len(results) >= 1
        assert results[0]["ticker"] == "005930"

    @patch('services.chatbot.retriever.KnowledgeRetriever._get_stock_repo')
    @patch('services.chatbot.retriever.KnowledgeRetriever._get_signal_repo')
    def test_search_signals_by_ticker(self, mock_signal_get_repo, mock_stock_get_repo):
        """특정 종목 시그널 검색 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        mock_signal = Mock()
        mock_signal.ticker = "005930"
        mock_signal.name = "삼성전자"
        mock_signal.signal_type = "vcp"
        mock_signal.score = 85.0
        mock_signal.grade = "A"
        mock_signal.signal_date = Mock()
        mock_signal.signal_date.isoformat.return_value = "2026-01-28"

        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = [mock_signal]
        mock_signal_get_repo.return_value = mock_repo

        retriever = KnowledgeRetriever()
        results = retriever.search_signals(ticker="005930", limit=10)

        assert len(results) >= 1

    def test_get_market_status(self):
        """Market Gate 상태 조회 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        status = retriever.get_market_status()

        assert status is not None
        assert "status" in status

    @patch('services.chatbot.retriever.KnowledgeRetriever.search_news')
    @patch('services.chatbot.retriever.KnowledgeRetriever.get_market_status')
    @patch('services.chatbot.retriever.KnowledgeRetriever.search_signals')
    @patch('services.chatbot.retriever.KnowledgeRetriever.search_stocks')
    def test_retrieve_context_for_stock_query(
        self, mock_stocks, mock_signals, mock_market, mock_news
    ):
        """종목 관련 질문 컨텍스트 검색 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        mock_stocks.return_value = MOCK_STOCKS[:1]
        mock_signals.return_value = MOCK_SIGNALS[:1]
        mock_news.return_value = MOCK_NEWS[:1]
        mock_market.return_value = MOCK_MARKET_STATUS

        retriever = KnowledgeRetriever()
        context = retriever.retrieve_context("삼성전자 추천해줘")

        assert context is not None
        assert context["query_type"] == "recommendation"
        assert context["stocks"] == MOCK_STOCKS[:1]

    def test_classify_query(self):
        """질문 유형 분류 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()

        assert retriever._classify_query("시장 상황 어때?") == "market"
        assert retriever._classify_query("삼성전자 추천해줘") == "recommendation"
        assert retriever._classify_query("삼성전자 정보") == "stock"
        assert retriever._classify_query("안녕하세요") == "general"

    def test_is_market_query(self):
        """시장 관련 질문 확인 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()

        assert retriever._is_market_query("시장 상황 어때?") is True
        assert retriever._is_market_query("KOSPI 지수") is True
        assert retriever._is_market_query("삼성전자 추천") is False

    @patch('services.chatbot.retriever.KnowledgeRetriever._get_stock_repo')
    def test_search_stocks_exception_handling(self, mock_get_repo):
        """예외 처리 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        mock_repo = Mock()
        mock_repo.search.side_effect = Exception("DB error")
        mock_get_repo.return_value = mock_repo

        retriever = KnowledgeRetriever()
        results = retriever.search_stocks("삼성")

        # 예외 발생 시 빈 리스트 반환
        assert results == []

    @patch('services.chatbot.retriever.KnowledgeRetriever._get_signal_repo')
    def test_search_signals_exception_handling(self, mock_get_repo):
        """시그널 검색 예외 처리 테스트"""
        from services.chatbot.retriever import KnowledgeRetriever

        mock_repo = Mock()
        mock_repo.get_active.side_effect = Exception("DB error")
        mock_get_repo.return_value = mock_repo

        retriever = KnowledgeRetriever()
        results = retriever.search_signals()

        # 예외 발생 시 빈 리스트 반환
        assert results == []
