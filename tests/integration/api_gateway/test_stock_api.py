"""
API Gateway 종목 관련 API 통합 테스트
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta

from services.api_gateway.main import app
from src.database.session import get_db_session
from src.database.models import Base, Stock, DailyPrice


# 테스트용 데이터베이스 설정
TEST_DATABASE_URL = "sqlite:///./test_stock.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db_session():
    """테스트용 DB 세션 오버라이드"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 의존성 주입 오버라이드
app.dependency_overrides[get_db_session] = override_get_db_session


@pytest.fixture(scope="function")
def test_db():
    """테스트용 데이터베이스 초기화"""
    # 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 테스트 데이터 생성
    db = TestingSessionLocal()

    # 테스트용 종목 데이터
    stock = Stock(
        ticker="005930",
        name="삼성전자",
        market="KOSPI",
        sector="전기전자"
    )
    db.add(stock)

    # 테스트용 가격 데이터 (최근 30일)
    base_date = datetime.now().date()
    for i in range(30):
        price = DailyPrice(
            ticker="005930",
            date=base_date - timedelta(days=i),
            open_price=80000 + i * 100,
            high_price=81000 + i * 100,
            low_price=79500 + i * 100,
            close_price=80500 + i * 100,
            volume=1000000 + i * 10000,
        )
        db.add(price)

    db.commit()
    db.close()

    yield db

    # 테스트 후 정리
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """테스트 클라이언트"""
    return TestClient(app)


class TestStockDetailAPI:
    """종목 상세 API 테스트"""

    def test_get_stock_detail_success(self, client):
        """종목 상세 조회 성공 테스트"""
        response = client.get("/api/kr/stocks/005930")

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "005930"
        assert data["name"] == "삼성전자"
        assert data["market"] == "KOSPI"
        assert data["sector"] == "전기전자"
        assert "current_price" in data
        assert data["current_price"] is not None

    def test_get_stock_detail_not_found(self, client):
        """존재하지 않는 종목 조회 테스트"""
        response = client.get("/api/kr/stocks/999999")

        assert response.status_code == 404
        assert "종목을 찾을 수 없습니다" in response.json()["detail"]


class TestStockChartAPI:
    """종목 차트 API 테스트"""

    def test_get_stock_chart_success(self, client):
        """종목 차트 데이터 조회 성공 테스트"""
        response = client.get("/api/kr/stocks/005930/chart?period=1mo")

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "005930"
        assert data["period"] == "1mo"
        assert "data" in data
        assert len(data["data"]) > 0
        assert "total_points" in data

        # 첫 번째 데이터 포인트 검증
        first_point = data["data"][0]
        assert "date" in first_point
        assert "open" in first_point
        assert "high" in first_point
        assert "low" in first_point
        assert "close" in first_point
        assert "volume" in first_point

    def test_get_stock_chart_different_periods(self, client):
        """다양한 기간 차트 데이터 조회 테스트"""
        periods = ["1mo", "3mo", "6mo", "1y"]

        for period in periods:
            response = client.get(f"/api/kr/stocks/005930/chart?period={period}")

            assert response.status_code == 200
            data = response.json()
            assert data["period"] == period

    def test_get_stock_chart_not_found(self, client):
        """존재하지 않는 종목 차트 조회 테스트"""
        response = client.get("/api/kr/stocks/999999/chart")

        assert response.status_code == 404
        assert "종목을 찾을 수 없습니다" in response.json()["detail"]

    def test_get_stock_chart_data_ordering(self, client):
        """차트 데이터 날짜순 정렬 테스트"""
        response = client.get("/api/kr/stocks/005930/chart?period=1mo")

        assert response.status_code == 200
        data = response.json()
        chart_data = data["data"]

        # 날짜순 정렬 확인
        dates = [point["date"] for point in chart_data]
        assert dates == sorted(dates)
