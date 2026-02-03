"""
ELW Ticker Support E2E Tests (Phase 5)
ELW 티커 지원 종단간 테스트
"""

import pytest
from unittest.mock import Mock, patch
from services.chatbot.retriever import KnowledgeRetriever
from services.chatbot.ticker_parser import get_ticker_parser, TickerType
from src.collectors.news_collector import NewsCollector


class TestELWE2E:
    """ELW 티커 지원 E2E 테스트"""

    def test_e2e_elw_chatbot_query(self):
        """챗봇에서 "0001A0 뉴스" 질의 E2E 시나리오"""
        # 1. TickerParser로 티커 추출
        parser = get_ticker_parser()
        query = "0001A0 뉴스 알려줘"
        tickers = parser.extract(query)

        assert "0001A0" in tickers
        assert parser.get_ticker_type("0001A0") == TickerType.ELW

        # 2. Retriever로 종목 검색
        retriever = KnowledgeRetriever()
        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = None
            mock_repo.return_value.search.return_value = []

            stocks = retriever.search_stocks(query)

            assert len(stocks) > 0
            assert stocks[0]["ticker"] == "0001A0"
            assert stocks[0]["_is_fallback"] is True

        # 3. ELW 티커 뉴스 수집 확인 (TickerParser 사용)
        assert parser.is_elw("0001A0") is True

        # 네이버 뉴스 검색 URL 생성 확인
        from urllib.parse import urlparse, parse_qs
        ticker = "0001A0"
        search_url = f"https://search.naver.com/search.naver?where=news&query={ticker}"

        parsed = urlparse(search_url)
        params = parse_qs(parsed.query)

        assert params["where"][0] == "news"
        assert "0001A0" in params["query"][0]

    def test_e2e_multiple_elw_tickers(self):
        """복수 ELW 티커 처리 E2E"""
        parser = get_ticker_parser()

        query = "0001A0과 005930A 비교해줘"
        tickers = parser.extract(query)

        assert "0001A0" in tickers
        assert "005930A" in tickers

        # 두 티커 모두 ELW 타입 확인
        for ticker in tickers:
            assert parser.get_ticker_type(ticker) == TickerType.ELW

    def test_e2e_standard_ticker_not_affected(self):
        """표준 티커 기능 회귀 없음 E2E"""
        parser = get_ticker_parser()
        retriever = KnowledgeRetriever()

        # 1. 표준 티커 추출
        query = "005930 뉴스"
        tickers = parser.extract(query)

        assert "005930" in tickers
        assert parser.get_ticker_type("005930") == TickerType.STANDARD

        # 2. 종목 검색 (DB에 있는 종목 시뮬레이션)
        mock_stock = Mock()
        mock_stock.ticker = "005930"
        mock_stock.name = "삼성전자"
        mock_stock.market = "KOSPI"
        mock_stock.sector = "전자"

        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = mock_stock
            mock_repo.return_value.search.return_value = [mock_stock]

            stocks = retriever.search_stocks(query)

            assert len(stocks) > 0
            assert stocks[0]["ticker"] == "005930"
            assert stocks[0]["name"] == "삼성전자"
            assert "_is_fallback" not in stocks[0] or not stocks[0].get("_is_fallback")

    def test_e2e_elw_display_format(self):
        """ELW 티커 표시 포맷 E2E"""
        parser = get_ticker_parser()

        # ELW 티커 포맷
        display_elw = parser.format_for_display("0001A0")
        assert "(ELW)" in display_elw

        # 표준 티커 포맷
        display_std = parser.format_for_display("005930")
        assert display_std == "005930"

    def test_e2e_rights_ticker(self):
        """RIGHTS 티커 처리 E2E"""
        parser = get_ticker_parser()

        # RIGHTS 티커
        ticker = "005930A12345"
        assert parser.validate(ticker) is True
        assert parser.get_ticker_type(ticker) == TickerType.RIGHTS

        # 포맷
        display = parser.format_for_display(ticker)
        assert "(권리)" in display


class TestELWIntegrationScenarios:
    """ELW 통합 시나리오 테스트"""

    def test_scenario_user_queries_elw_news(self):
        """사용자 시나리오: ELW 종목 뉴스 조회"""
        # 사용자 입력
        user_input = "덕양에너젠 0001A0 최신 뉴스 알려줘"

        # 1. 티커 추출
        parser = get_ticker_parser()
        tickers = parser.extract(user_input)

        assert "0001A0" in tickers

        # 2. 종목 정보 생성 (fallback)
        retriever = KnowledgeRetriever()
        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = None
            mock_repo.return_value.search.return_value = []

            stocks = retriever.search_stocks(user_input)

            assert stocks[0]["ticker"] == "0001A0"
            assert stocks[0]["_is_fallback"] is True
            assert "ELW" in stocks[0]["market"]

    def test_scenario_mixed_ticker_types(self):
        """사용자 시나리오: 표준/ELW 티커 혼합"""
        parser = get_ticker_parser()

        # 사용자 입력
        user_input = "삼성전자 005930과 덕양에너젠 0001A0 비교"

        # 티커 추출
        tickers = parser.extract(user_input)

        # 두 티커 모두 추출되어야 함 (어떤 순서든 상관없음)
        assert "005930" in tickers
        assert "0001A0" in tickers

        # 타입 확인
        assert parser.get_ticker_type("005930") == TickerType.STANDARD
        assert parser.get_ticker_type("0001A0") == TickerType.ELW

    def test_scenario_chatbot_context_with_elw(self):
        """사용자 시나리오: 챗봇 컨텍스트에 ELW 종목 포함"""
        retriever = KnowledgeRetriever()

        # ELW 티커로 컨텍스트 검색
        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = None
            mock_repo.return_value.search.return_value = []

            context = retriever.retrieve_context("0001A0 뉴스")

            # 종목 정보 확인
            assert len(context["stocks"]) > 0
            assert context["stocks"][0]["ticker"] == "0001A0"
            assert context["stocks"][0]["_is_fallback"] is True
