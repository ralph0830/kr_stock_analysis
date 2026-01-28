"""
API Gateway 백테스트 API 통합 테스트 (RED Phase)
TDD 첫 번째 단계 - 모든 테스트는 실패해야 함
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime

from services.api_gateway.main import app
from src.database.session import get_db_session
from src.database.models import Base, BacktestResult


# 테스트용 데이터베이스 설정
TEST_DATABASE_URL = "sqlite:///./test_backtest.db"
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

    # 테스트용 백테스트 결과 데이터
    backtests = [
        BacktestResult(
            id=1,
            config_name="vcp_conservative",
            backtest_date=date(2024, 1, 15),
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            win_rate=65.0,
            total_return_pct=25.5,
            max_drawdown_pct=-8.2,
            sharpe_ratio=1.8,
            avg_return_per_trade=0.255,
            profit_factor=2.1,
            created_at=datetime(2024, 1, 15, 10, 0, 0),
        ),
        BacktestResult(
            id=2,
            config_name="vcp_aggressive",
            backtest_date=date(2024, 1, 15),
            total_trades=150,
            winning_trades=80,
            losing_trades=70,
            win_rate=53.33,
            total_return_pct=35.8,
            max_drawdown_pct=-15.5,
            sharpe_ratio=1.5,
            avg_return_per_trade=0.239,
            profit_factor=1.8,
            created_at=datetime(2024, 1, 15, 11, 0, 0),
        ),
        BacktestResult(
            id=3,
            config_name="vcp_conservative",
            backtest_date=date(2024, 1, 10),
            total_trades=90,
            winning_trades=60,
            losing_trades=30,
            win_rate=66.67,
            total_return_pct=22.0,
            max_drawdown_pct=-7.5,
            sharpe_ratio=1.9,
            avg_return_per_trade=0.244,
            profit_factor=2.3,
            created_at=datetime(2024, 1, 10, 9, 30, 0),
        ),
    ]

    for bt in backtests:
        db.add(bt)

    db.commit()
    db.close()

    yield db

    # 테스트 후 정리
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """테스트 클라이언트"""
    return TestClient(app)


class TestBacktestSummaryAPI:
    """백테스트 요약 API 테스트"""

    def test_get_backtest_summary_success(self, client):
        """요약 조회 성공"""
        response = client.get("/api/kr/backtest/summary")

        assert response.status_code == 200
        data = response.json()

        assert "total_backtests" in data
        assert "avg_return_pct" in data
        assert "avg_win_rate" in data
        assert "best_return_pct" in data
        assert "worst_return_pct" in data

        # 데이터 검증
        assert data["total_backtests"] >= 3

    def test_get_backtest_summary_empty_data(self, client, test_db):
        """빈 데이터시 처리"""
        # 모든 데이터 삭제
        test_db.query(BacktestResult).delete()
        test_db.commit()

        response = client.get("/api/kr/backtest/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["total_backtests"] == 0
        assert data["avg_return_pct"] == 0.0
        assert data["avg_win_rate"] == 0.0

    def test_get_backtest_summary_with_config_filter(self, client):
        """설정명 필터링"""
        response = client.get("/api/kr/backtest/summary?config_name=vcp_conservative")

        assert response.status_code == 200
        data = response.json()

        # vcp_conservative 설정만 필터링
        assert data["total_backtests"] == 2


class TestBacktestLatestAPI:
    """최신 백테스트 조회 API 테스트"""

    def test_get_latest_backtests_success(self, client):
        """최신 백테스트 조회 성공"""
        response = client.get("/api/kr/backtest/latest")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "total" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0

        # 첫 번째 결과 검증
        first_result = data["results"][0]
        assert "id" in first_result
        assert "config_name" in first_result
        assert "backtest_date" in first_result
        assert "total_return_pct" in first_result

    def test_get_latest_backtests_with_limit(self, client):
        """limit 파라미터 적용"""
        response = client.get("/api/kr/backtest/latest?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) <= 2

    def test_get_latest_backtests_with_config_filter(self, client):
        """설정명 필터링"""
        response = client.get("/api/kr/backtest/latest?config_name=vcp_conservative")

        assert response.status_code == 200
        data = response.json()

        # 모든 결과가 vcp_conservative 설정인지 확인
        for result in data["results"]:
            assert result["config_name"] == "vcp_conservative"


class TestBacktestHistoryAPI:
    """백테스트 히스토리 조회 API 테스트"""

    def test_get_backtest_history_success(self, client):
        """히스토리 조회 성공"""
        response = client.get("/api/kr/backtest/history")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "total" in data
        assert isinstance(data["results"], list)

    def test_get_backtest_history_with_date_range(self, client):
        """날짜 범위 필터링"""
        response = client.get(
            "/api/kr/backtest/history?start_date=2024-01-01&end_date=2024-01-12"
        )

        assert response.status_code == 200
        data = response.json()

        # 날짜 범위 내 결과만 반환
        for result in data["results"]:
            backtest_date = datetime.fromisoformat(result["backtest_date"]).date()
            assert date(2024, 1, 1) <= backtest_date <= date(2024, 1, 12)

    def test_get_backtest_history_with_limit(self, client):
        """limit 파라미터 적용"""
        response = client.get("/api/kr/backtest/history?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) <= 2

    def test_get_backtest_history_with_config_filter(self, client):
        """설정명 필터링"""
        response = client.get("/api/kr/backtest/history?config_name=vcp_aggressive")

        assert response.status_code == 200
        data = response.json()

        # 모든 결과가 vcp_aggressive 설정인지 확인
        for result in data["results"]:
            assert result["config_name"] == "vcp_aggressive"


class TestBacktestBestResultAPI:
    """최고 수익률 조회 API 테스트"""

    def test_get_best_result_success(self, client):
        """최고 수익률 조회 성공"""
        response = client.get("/api/kr/backtest/best")

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "config_name" in data
        assert "total_return_pct" in data

        # 최고 수익률 검증
        assert data["total_return_pct"] == 35.8  # vcp_aggressive

    def test_get_best_result_with_config_filter(self, client):
        """설정명 필터링"""
        response = client.get("/api/kr/backtest/best?config_name=vcp_conservative")

        assert response.status_code == 200
        data = response.json()

        # vcp_conservative 중 최고 수익률
        assert data["config_name"] == "vcp_conservative"
        assert data["total_return_pct"] == 25.5

    def test_get_best_result_empty_returns_404(self, client, test_db):
        """데이터 없을 때 404 반환"""
        # 모든 데이터 삭제
        test_db.query(BacktestResult).delete()
        test_db.commit()

        response = client.get("/api/kr/backtest/best")

        assert response.status_code == 404
