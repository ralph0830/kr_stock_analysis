"""
Kiwoom REST API Mock

Kiwoom 증권사 REST API 호출을 Mock 처리합니다.
토큰 발급, 차트 조회, 실시간 데이터 등을 포함합니다.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock


class MockKiwoomRestAPI:
    """
    Mock Kiwoom REST API

    실제 Kiwoom API 호출 없이 테스트할 수 있습니다.
    """

    def __init__(self):
        """Kiwoom REST API Mock 초기화"""
        self.app_key = "test_app_key"
        self.secret_key = "test_secret_key"
        self.token = None
        self.token_expiry = None
        self.token_valid = True

        # Mock 데이터
        self.stock_prices: Dict[str, int] = {
            "005930": 80500,  # 삼성전자
            "000660": 125000,  # SK하이닉스
            "035420": 320000,  # NAVER
        }

        self.suspended_stocks: set = set()

        # 차트 데이터
        self.chart_data: Dict[str, List[Dict[str, Any]]] = {}

    async def issue_token(self) -> str:
        """
        토큰 발급

        Returns:
            발급된 토큰
        """
        if not self.token_valid:
            raise Exception("토큰 발급 실패: 인증 오류")

        self.token = "mock_token_" + datetime.now().strftime("%Y%m%d%H%M%S")
        self.token_expiry = datetime.now() + timedelta(hours=24)
        return self.token

    async def ensure_token_valid(self):
        """토큰 유효성 확인 및 갱신"""
        if not self.token or not self.token_expiry:
            await self.issue_token()
            return

        if datetime.now() >= self.token_expiry:
            await self.issue_token()

    async def get_stock_daily_chart(
        self,
        ticker: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        일봉 차트 조회

        Args:
            ticker: 종목 코드
            days: 조회 일수

        Returns:
            차트 데이터 리스트
        """
        await self.ensure_token_valid()

        # Mock 데이터 생성
        if ticker not in self.chart_data:
            self.chart_data[ticker] = self._generate_mock_chart_data(ticker, days)

        return self.chart_data[ticker][:days]

    def _generate_mock_chart_data(
        self,
        ticker: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """
        Mock 차트 데이터 생성

        Args:
            ticker: 종목 코드
            days: 일수

        Returns:
            차트 데이터
        """
        base_price = self.stock_prices.get(ticker, 50000)
        chart = []

        for i in range(days):
            current_date = date.today() - timedelta(days=i)
            date_str = current_date.strftime("%Y%m%d")

            # 랜덤 가격 변동 생성
            import random
            open_price = base_price + random.randint(-1000, 1000)
            high_price = open_price + random.randint(0, 500)
            low_price = open_price - random.randint(0, 500)
            close_price = open_price + random.randint(-300, 300)
            volume = random.randint(500000, 2000000)

            chart.append({
                "date": date_str,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })

        return chart

    async def get_realtime_price(self, ticker: str) -> Dict[str, Any]:
        """
        실시간 가격 조회

        Args:
            ticker: 종목 코드

        Returns:
            실시간 가격 정보
        """
        await self.ensure_token_valid()

        price = self.stock_prices.get(ticker, 0)

        return {
            "ticker": ticker,
            "price": price,
            "change": 0,
            "change_rate": 0.0,
            "volume": 1000000,
            "timestamp": datetime.now().isoformat()
        }

    async def get_daily_trade_detail(self, ticker: str, date: str) -> Dict[str, Any]:
        """
        일별 거래 상세 조회

        Args:
            ticker: 종목 코드
            date: 날짜 (YYYYMMDD)

        Returns:
            거래 상세 정보
        """
        await self.ensure_token_valid()

        return {
            "ticker": ticker,
            "date": date,
            "open": self.stock_prices.get(ticker, 0),
            "high": self.stock_prices.get(ticker, 0) + 500,
            "low": self.stock_prices.get(ticker, 0) - 500,
            "close": self.stock_prices.get(ticker, 0),
            "volume": 1000000,
            "trading_value": 80000000000
        }

    async def get_suspended_stocks(self) -> List[str]:
        """
        거래정지 종목 조회

        Returns:
            거래정지 종목 코드 리스트
        """
        await self.ensure_token_valid()
        return list(self.suspended_stocks)

    def add_suspended_stock(self, ticker: str):
        """
        거래정지 종목 추가 (테스트용)

        Args:
            ticker: 종목 코드
        """
        self.suspended_stocks.add(ticker)

    def remove_suspended_stock(self, ticker: str):
        """
        거래정지 종목 제거 (테스트용)

        Args:
            ticker: 종목 코드
        """
        self.suspended_stocks.discard(ticker)

    def set_stock_price(self, ticker: str, price: int):
        """
        종목 가격 설정 (테스트용)

        Args:
            ticker: 종목 코드
            price: 가격
        """
        self.stock_prices[ticker] = price

    def set_token_invalid(self):
        """토큰을 무효 상태로 설정 (테스트용)"""
        self.token_valid = False
        self.token = None
        self.token_expiry = None

    def set_token_valid(self):
        """토큰을 유효 상태로 설정 (테스트용)"""
        self.token_valid = True


# ============================================================================
# Pytest Fixtures
# ============================================================================

import pytest


@pytest.fixture
def mock_kiwoom_api():
    """
    Mock Kiwoom REST API Fixture

    Example:
        async def test_get_chart(mock_kiwoom_api):
            chart = await mock_kiwoom_api.get_stock_daily_chart("005930", 10)
            assert len(chart) == 10
            assert chart[0]["ticker"] == "005930"
    """
    api = MockKiwoomRestAPI()
    return api


@pytest.fixture
def mock_kiwoom_token():
    """
    Mock Kiwoom 토큰 Fixture

    Example:
        async def test_with_token(mock_kiwoom_token):
            assert mock_kiwoom_token.startswith("mock_token_")
    """
    api = MockKiwoomRestAPI()
    return api.issue_token()


@pytest.fixture
def mock_kiwoom_chart_data():
    """
    Mock 차트 데이터 Fixture

    Example:
        def test_chart_data(mock_kiwoom_chart_data):
            assert "005930" in mock_kiwoom_chart_data
            assert len(mock_kiwoom_chart_data["005930"]) > 0
    """
    api = MockKiwoomRestAPI()

    # 샘플 차트 데이터 생성
    chart_data = {
        "005930": [
            {
                "date": "20260206",
                "open": 80000,
                "high": 81000,
                "low": 79500,
                "close": 80500,
                "volume": 1000000
            },
            {
                "date": "20260205",
                "open": 79000,
                "high": 80500,
                "low": 78800,
                "close": 80000,
                "volume": 1200000
            },
            {
                "date": "20260204",
                "open": 78500,
                "high": 79800,
                "low": 78300,
                "close": 79200,
                "volume": 900000
            }
        ],
        "000660": [
            {
                "date": "20260206",
                "open": 124000,
                "high": 126000,
                "low": 123500,
                "close": 125000,
                "volume": 800000
            }
        ]
    }

    return chart_data


@pytest.fixture
def mock_kiwoom_realtime_prices():
    """
    Mock 실시간 가격 데이터 Fixture

    Example:
        def test_realtime_prices(mock_kiwoom_realtime_prices):
            assert mock_kiwoom_realtime_prices["005930"]["price"] == 80500
    """
    return {
        "005930": {
            "ticker": "005930",
            "price": 80500,
            "change": 500,
            "change_rate": 0.62,
            "volume": 1500000,
            "timestamp": "2026-02-06T09:30:00"
        },
        "000660": {
            "ticker": "000660",
            "price": 125000,
            "change": 1000,
            "change_rate": 0.81,
            "volume": 500000,
            "timestamp": "2026-02-06T09:30:00"
        },
        "035420": {
            "ticker": "035420",
            "price": 320000,
            "change": -2000,
            "change_rate": -0.62,
            "volume": 300000,
            "timestamp": "2026-02-06T09:30:00"
        }
    }


@pytest.fixture
def mock_kiwoom_suspended_stocks():
    """
    Mock 거래정지 종목 Fixture

    Example:
        def test_suspended_stocks(mock_kiwoom_suspended_stocks):
            assert "123456" in mock_kiwoom_suspended_stocks
    """
    return ["123456", "234567", "345678"]


@pytest.fixture
def mock_kiwoom_responses(monkeypatch):
    """
    Kiwoom API 응답 Mock Fixture

    실제 Kiwoom API 호출을 Mock으로 대체합니다.

    Example:
        def test_with_mock_kiwoom(mock_kiwoom_responses, mock_kiwoom_api):
            mock_kiwoom_responses.get_stock_daily_chart.return_value = await mock_kiwoom_api.get_stock_daily_chart("005930", 10)

            chart = await kiwoom_api.get_stock_daily_chart("005930", 10)
            assert len(chart) == 10
    """
    from unittest.mock import AsyncMock

    mock = MagicMock()
    mock.get_stock_daily_chart = AsyncMock()
    mock.get_realtime_price = AsyncMock()
    mock.get_daily_trade_detail = AsyncMock()
    mock.get_suspended_stocks = AsyncMock()
    mock.issue_token = AsyncMock()
    mock.ensure_token_valid = AsyncMock()

    # 기본 응답 설정
    mock.issue_token.return_value = "mock_token_20260206"
    mock.ensure_token_valid.return_value = None

    return mock
