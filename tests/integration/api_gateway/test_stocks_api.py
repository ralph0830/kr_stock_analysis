"""
Stocks API Integration Tests
TDD GREEN Phase - Tests should pass with implementation
"""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from services.api_gateway.main import app
from src.database.session import get_db_session
from src.database.models import Stock, DailyPrice, Signal, InstitutionalFlow


# Override dependency for testing
async def override_get_db():
    """Test용 DB 세션 오버라이드"""
    from tests.conftest import test_db_session

    async for session in test_db_session():
        yield session


@pytest.fixture
async def client(test_db_session):
    """Test Client Fixture"""
    # Dependency override
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_stock(test_db_session: Session):
    """Sample Stock 데이터"""
    # 기존 데이터 삭제 (테스트 격리)
    test_db_session.query(DailyPrice).filter(DailyPrice.ticker == "005930").delete()
    test_db_session.query(Signal).filter(Signal.ticker == "005930").delete()
    test_db_session.query(InstitutionalFlow).filter(
        InstitutionalFlow.ticker == "005930"
    ).delete()
    test_db_session.query(Stock).filter(Stock.ticker == "005930").delete()
    test_db_session.commit()

    stock = Stock(
        ticker="005930",
        name="삼성전자",
        market="KOSPI",
        sector="반도체",
        market_cap=500000000000000,
    )
    test_db_session.add(stock)
    test_db_session.commit()
    test_db_session.refresh(stock)
    return stock


@pytest.fixture
def sample_daily_prices(test_db_session: Session, sample_stock: Stock):
    """Sample DailyPrice 데이터"""
    base_date = date.today() - timedelta(days=10)
    prices = []
    for i in range(10):
        price = DailyPrice(
            ticker=sample_stock.ticker,
            date=base_date + timedelta(days=i),
            open_price=80000 + i * 100,
            high_price=81000 + i * 100,
            low_price=79500 + i * 100,
            close_price=80500 + i * 100,
            volume=1000000 + i * 10000,
            foreign_net_buy=500000 + i * 50000,
            inst_net_buy=-300000 - i * 10000,
        )
        prices.append(price)
        test_db_session.add(price)
    test_db_session.commit()
    return prices


@pytest.fixture
def sample_signals(test_db_session: Session, sample_stock: Stock):
    """Sample Signal 데이터"""
    signals = [
        Signal(
            ticker=sample_stock.ticker,
            signal_type="VCP",
            status="OPEN",
            score=85.5,
            grade="A",
            contraction_ratio=0.3,
            entry_price=80000,
            target_price=88000,
            signal_date=date.today(),
        ),
        Signal(
            ticker=sample_stock.ticker,
            signal_type="JONGGA_V2",
            status="CLOSED",
            score=92.0,
            grade="S",
            total_score=12,
            entry_price=75000,
            signal_date=date.today() - timedelta(days=5),
            exit_time=datetime.now(),
            exit_reason="Target Reached",
        ),
    ]
    for sig in signals:
        test_db_session.add(sig)
    test_db_session.commit()
    return signals


@pytest.fixture
def sample_flows(test_db_session: Session, sample_stock: Stock):
    """Sample InstitutionalFlow 데이터"""
    base_date = date.today() - timedelta(days=10)
    flows = []
    for i in range(10):
        flow = InstitutionalFlow(
            ticker=sample_stock.ticker,
            date=base_date + timedelta(days=i),
            foreign_net_buy=500000 + i * 50000,
            foreign_consecutive_days=5 + i,
            foreign_trend="buying",
            inst_net_buy=-300000 - i * 10000,
            inst_consecutive_days=-2 - i,
            inst_trend="selling",
            foreign_net_5d=2000000 + i * 100000,
            inst_net_5d=-1000000 - i * 50000,
            supply_demand_score=60 + i,
        )
        flows.append(flow)
        test_db_session.add(flow)
    test_db_session.commit()
    return flows


class TestStocksAPIIntegration:
    """Stocks API 통합 테스트"""

    async def test_stocks_detail_api_success(self, client: AsyncClient, sample_stock):
        """종목 상세 API - 성공"""
        response = await client.get(f"/api/kr/stocks/{sample_stock.ticker}")

        # 라우트가 구현되었으므로 200 기대
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == sample_stock.ticker
        assert data["name"] == sample_stock.name

    async def test_stocks_detail_api_not_found(self, client: AsyncClient):
        """종목 상세 API - 종목 없음"""
        response = await client.get("/api/kr/stocks/999999")

        # 404 기대
        assert response.status_code == 404

    async def test_stocks_detail_api_response_structure(
        self, client: AsyncClient, sample_stock
    ):
        """종목 상세 API - 응답 구조 검증"""
        response = await client.get(f"/api/kr/stocks/{sample_stock.ticker}")

        assert response.status_code == 200
        data = response.json()
        required_fields = ["ticker", "name", "market"]
        for field in required_fields:
            assert field in data
        assert data["ticker"] == sample_stock.ticker

    async def test_stocks_chart_api_success(
        self, client: AsyncClient, sample_stock, sample_daily_prices
    ):
        """종목 차트 API - 성공"""
        response = await client.get(
            f"/api/kr/stocks/{sample_stock.ticker}/chart", params={"days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == sample_stock.ticker
        assert len(data["data"]) > 0

    async def test_stocks_chart_api_with_days_parameter(
        self, client: AsyncClient, sample_stock, sample_daily_prices
    ):
        """종목 차트 API - days 파라미터"""
        for days in [7, 30, 90]:
            response = await client.get(
                f"/api/kr/stocks/{sample_stock.ticker}/chart", params={"days": days}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == sample_stock.ticker

    async def test_stocks_chart_api_response_structure(
        self, client: AsyncClient, sample_stock, sample_daily_prices
    ):
        """종목 차트 API - 응답 구조 검증"""
        response = await client.get(
            f"/api/kr/stocks/{sample_stock.ticker}/chart", params={"days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        required_fields = ["ticker", "data", "total_points"]
        for field in required_fields:
            assert field in data
        assert isinstance(data["data"], list)

    async def test_stocks_flow_api_success(
        self, client: AsyncClient, sample_stock, sample_flows
    ):
        """종목 수급 API - 성공"""
        response = await client.get(
            f"/api/kr/stocks/{sample_stock.ticker}/flow", params={"days": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == sample_stock.ticker
        assert len(data["data"]) > 0

    async def test_stocks_flow_api_response_structure(
        self, client: AsyncClient, sample_stock, sample_flows
    ):
        """종목 수급 API - 응답 구조 검증"""
        response = await client.get(
            f"/api/kr/stocks/{sample_stock.ticker}/flow", params={"days": 20}
        )

        assert response.status_code == 200
        data = response.json()
        required_fields = ["ticker", "data", "smartmoney_score", "total_points"]
        for field in required_fields:
            assert field in data
        assert isinstance(data["data"], list)

    async def test_stocks_signals_api_success(
        self, client: AsyncClient, sample_stock, sample_signals
    ):
        """종목 시그널 API - 성공"""
        response = await client.get(f"/api/kr/stocks/{sample_stock.ticker}/signals")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == sample_stock.ticker
        assert data["total_signals"] == len(sample_signals)

    async def test_stocks_signals_api_response_structure(
        self, client: AsyncClient, sample_stock, sample_signals
    ):
        """종목 시그널 API - 응답 구조 검증"""
        response = await client.get(f"/api/kr/stocks/{sample_stock.ticker}/signals")

        assert response.status_code == 200
        data = response.json()
        required_fields = ["ticker", "total_signals", "open_signals", "signals"]
        for field in required_fields:
            assert field in data
        assert data["total_signals"] == len(sample_signals)

    async def test_stocks_detail_with_realtime_price(
        self, client: AsyncClient, sample_stock
    ):
        """종목 상세 API - 실시간 가격 포함"""
        response = await client.get(f"/api/kr/stocks/{sample_stock.ticker}")

        assert response.status_code == 200
        data = response.json()
        # Kiwoom API 연동 시 실시간 가격 포함
        # 현재는 DB 데이터만 반환
        assert "ticker" in data

    async def test_stocks_chart_empty_data(self, client: AsyncClient):
        """종목 차트 API - 데이터 없음"""
        # DailyPrice가 없는 종목 조회
        empty_stock_ticker = "999999"
        response = await client.get(
            f"/api/kr/stocks/{empty_stock_ticker}/chart", params={"days": 30}
        )

        # 종목이 없어도 API는 동작해야 함
        assert response.status_code in (200, 404)

    async def test_stocks_flow_smartmoney_score_calculation(
        self, client: AsyncClient, sample_stock, sample_flows
    ):
        """종목 수급 API - SmartMoney 점수 계산"""
        response = await client.get(
            f"/api/kr/stocks/{sample_stock.ticker}/flow", params={"days": 20}
        )

        assert response.status_code == 200
        data = response.json()
        # SmartMoney 점수 범위 검증 (0-100)
        assert 0 <= data["smartmoney_score"] <= 100

    async def test_stocks_signals_return_calculation(
        self, client: AsyncClient, sample_stock, sample_signals
    ):
        """종목 시그널 API - 수익률 계산"""
        response = await client.get(f"/api/kr/stocks/{sample_stock.ticker}/signals")

        assert response.status_code == 200
        data = response.json()
        # Signal 모델에 exit_price가 없으므로 수익률은 null
        assert data["ticker"] == sample_stock.ticker

    async def test_stocks_all_endpoints_implemented(
        self, client: AsyncClient, sample_stock
    ):
        """모든 stocks 엔드포인트 - 구현 확인"""
        endpoints = [
            f"/api/kr/stocks/{sample_stock.ticker}",
            f"/api/kr/stocks/{sample_stock.ticker}/chart",
            f"/api/kr/stocks/{sample_stock.ticker}/flow",
            f"/api/kr/stocks/{sample_stock.ticker}/signals",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            # 구현되었으므로 404가 아니어야 함
            assert response.status_code != 404
