"""
Chatbot Retriever ELW Tests (TDD: RED Phase)
ELW 티커 지원을 위한 Retriever 연동 테스트

Phase 2: RED - 실패하는 테스트 먼저 작성
"""

import pytest
from unittest.mock import Mock, patch
from services.chatbot.retriever import KnowledgeRetriever


class TestRetrieverELWTicker:
    """ELW 티커 지원 테스트"""

    @pytest.fixture
    def retriever(self):
        """KnowledgeRetriever 인스턴스"""
        # 기존 싱글톰 초기화 방지를 위해 새 인스턴스 생성
        return KnowledgeRetriever()

    def test_search_stocks_elw_ticker_type1(self, retriever):
        """ELW 티커 Type 1 (0001A0)로 종목 검색"""
        # ELW 티커는 DB에 없으므로 fallback 종목 생성
        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = None
            mock_repo.return_value.search.return_value = []

            result = retriever.search_stocks("0001A0 뉴스 알려줘")

            assert len(result) > 0
            assert result[0]["ticker"] == "0001A0"
            assert result[0]["_is_fallback"] is True
            # ELW 티커는 market 필드에 KOSDAQ-ELW 표시
            assert "ELW" in result[0]["market"] or result[0]["market"] == "KOSDAQ/KOSDAQ"

    def test_search_stocks_elw_ticker_type2(self, retriever):
        """ELW 티커 Type 2 (005930A)로 종목 검색"""
        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = None
            mock_repo.return_value.search.return_value = []

            result = retriever.search_stocks("005930A 뉴스")

            assert len(result) > 0
            assert result[0]["ticker"] == "005930A"
            assert result[0]["_is_fallback"] is True

    def test_search_stocks_with_elw_in_query(self, retriever):
        """쿼리에서 ELW 티커 추출"""
        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = None
            mock_repo.return_value.search.return_value = []

            result = retriever.search_stocks("0001A0과 005930A 비교해줘")

            # 첫 번째 ELW 티커가 추출되어야 함
            assert len(result) > 0
            assert result[0]["ticker"] in ["0001A0", "005930A"]
            assert result[0]["_is_fallback"] is True

    def test_standard_ticker_still_works(self, retriever):
        """기존 6자리 표준 티커 기능 회귀 없음"""
        # DB에 있는 종목 시뮬레이션
        mock_stock = Mock()
        mock_stock.ticker = "005930"
        mock_stock.name = "삼성전자"
        mock_stock.market = "KOSPI"
        mock_stock.sector = "전자"

        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            mock_repo.return_value.get_by_ticker.return_value = mock_stock
            mock_repo.return_value.search.return_value = [mock_stock]

            result = retriever.search_stocks("005930")

            assert len(result) > 0
            assert result[0]["ticker"] == "005930"
            assert result[0]["name"] == "삼성전자"
            assert result[0]["market"] == "KOSPI"
            assert "_is_fallback" not in result[0] or not result[0].get("_is_fallback")

    def test_mixed_ticker_types(self, retriever):
        """표준 티커와 ELW 티커가 섞인 쿼리 처리"""
        mock_stock = Mock()
        mock_stock.ticker = "005930"
        mock_stock.name = "삼성전자"
        mock_stock.market = "KOSPI"
        mock_stock.sector = "전자"

        with patch.object(retriever, '_get_stock_repo') as mock_repo:
            # 삼성전자는 DB에 있음
            def get_by_ticker_side_effect(ticker):
                if ticker == "005930":
                    return mock_stock
                return None

            mock_repo.return_value.get_by_ticker.side_effect = get_by_ticker_side_effect
            mock_repo.return_value.search.return_value = [mock_stock]

            result = retriever.search_stocks("삼성전자 005930과 0001A0 비교")

            # 최소한 삼성전자는 반환되어야 함
            assert len(result) > 0
            tickers = [r["ticker"] for r in result]
            assert "005930" in tickers


class TestRetrieverTickerExtraction:
    """티커 추출 로직 테스트"""

    def test_extract_elw_from_query(self):
        """TickerParser 사용하여 쿼리에서 ELW 티커 추출"""
        from services.chatbot.ticker_parser import get_ticker_parser

        parser = get_ticker_parser()

        # Type 1 ELW (0001A0)
        result = parser.extract("0001A0 뉴스 알려줘")
        assert "0001A0" in result

        # Type 2 ELW (005930A)
        result = parser.extract("005930A 뉴스")
        assert "005930A" in result

        # 복수 ELW 티커
        result = parser.extract("0001A0과 005930A 비교")
        assert "0001A0" in result
        assert "005930A" in result

    def test_validate_elw_tickers(self):
        """ELW 티커 유효성 검증"""
        from services.chatbot.ticker_parser import get_ticker_parser, TickerType

        parser = get_ticker_parser()

        # Type 1 ELW
        assert parser.validate("0001A0") is True
        assert parser.get_ticker_type("0001A0") == TickerType.ELW

        # Type 2 ELW
        assert parser.validate("005930A") is True
        assert parser.get_ticker_type("005930A") == TickerType.ELW

        # 표준 티커
        assert parser.validate("005930") is True
        assert parser.get_ticker_type("005930") == TickerType.STANDARD


class TestRetrieverNewsWithELW:
    """ELW 티커 뉴스 검색 테스트"""

    def test_search_news_with_elw_ticker(self):
        """ELW 티커로 뉴스 검색"""
        retriever = KnowledgeRetriever()

        with patch.object(retriever, '_get_stock_repo'):
            # DB에 뉴스가 없는 경우 실시간 수집 시도
            with patch.object(retriever, '_fetch_realtime_news') as mock_fetch:
                mock_fetch.return_value = [
                    {
                        "ticker": "0001A0",
                        "summary": "테스트 뉴스",
                        "news_urls": [{"title": "테스트", "url": "https://test.com"}],
                        "_is_realtime": True,
                    }
                ]

                result = retriever.search_news(ticker="0001A0", limit=5)

                # 실시간 뉴스가 반환되어야 함
                assert len(result) > 0
                assert result[0]["ticker"] == "0001A0"
                assert "_is_realtime" in result[0]
