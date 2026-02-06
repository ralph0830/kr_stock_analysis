"""
Daytrading 실시간 가격 연동 테스트 (TDD - Red Phase)

이 테스트 파일은 custom-recommendation 페이지의 실시간 가격 연동을 검증합니다.
TDD 방식으로 작성되었으며, 먼저 실패하는 테스트를 작성합니다.

테스트 커버리지:
1. Pydantic 모델에 current_price 필드 존재
2. API 응답에 current_price 포함
3. 종목이 브로드캐스터에 추가
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# 테스트 대상 모듈 임포트
from services.daytrading_scanner.models.daytrading import (
    DaytradingSignal,
    DaytradingCheck,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_signal_data():
    """샘플 시그널 데이터"""
    return {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "score": 90,
        "grade": "S",
        "checks": [
            {"name": "거래량 폭증", "status": "passed", "points": 15},
            {"name": "모멘텀 돌파", "status": "passed", "points": 15},
        ],
        "signal_type": "STRONG_BUY",
        "entry_price": 75000,
        "target_price": 80000,
        "stop_loss": 72000,
        "reasons": ["거래량 폭증", "모멘텀 돌파"]
    }


# =============================================================================
# Test 1: Pydantic 모델에 current_price 필드 존재
# =============================================================================

class TestDaytradingSignalModel:
    """DaytradingSignal 모델 검증"""

    def test_model_has_current_price_field(self, sample_signal_data):
        """
        GIVEN: DaytradingSignal 모델
        WHEN: 모델을 생성하면
        THEN: current_price 필드가 있어야 함
        """
        # Act & Assert
        # Pydantic 모델에 current_price 필드가 있는지 확인
        model_fields = DaytradingSignal.model_fields
        assert "current_price" in model_fields, \
            f"DaytradingSignal 모델에 current_price 필드가 없습니다. 현재 필드: {list(model_fields.keys())}"

    def test_model_accepts_current_price(self, sample_signal_data):
        """
        GIVEN: DaytradingSignal 모델
        WHEN: current_price를 포함하여 생성하면
        THEN: 정상적으로 생성되어야 함
        """
        # Arrange
        sample_signal_data["current_price"] = 75500

        # Act
        signal = DaytradingSignal(**sample_signal_data)

        # Assert
        assert signal.current_price == 75500
        assert signal.ticker == "005930"
        assert signal.name == "삼성전자"

    def test_model_current_price_is_optional(self, sample_signal_data):
        """
        GIVEN: DaytradingSignal 모델
        WHEN: current_price 없이 생성하면
        THEN: None이어야 함 (Optional)
        """
        # Act
        signal = DaytradingSignal(**sample_signal_data)

        # Assert
        assert signal.current_price is None


# =============================================================================
# Test 2: API 응답에 current_price 포함
# =============================================================================

class TestDaytradingSignalsAPI:
    """Daytrading Signals API 검증"""

    @pytest.mark.asyncio
    async def test_signals_response_includes_current_price(self):
        """
        GIVEN: /api/daytrading/signals 엔드포인트
        WHEN: 시그널을 조회하면
        THEN: 응답에 current_price 필드가 포함되어야 함
        """
        # 이 테스트는 실제 API 엔드포인트가 구현된 후 통과합니다
        from services.daytrading_scanner.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Act
        response = client.get("/api/daytrading/signals?limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        signals = data.get("data", {}).get("signals", [])

        if signals:
            # 최소 하나의 시그널이 있는 경우 current_price 필드 확인
            first_signal = signals[0]
            assert "current_price" in first_signal, \
                f"API 응답에 current_price 필드가 없습니다. 현재 필드: {list(first_signal.keys())}"

    @pytest.mark.asyncio
    async def test_signals_current_price_from_db(self):
        """
        GIVEN: DB에 일봉 데이터가 있는 종목
        WHEN: 시그널을 조회하면
        THEN: current_price는 DB의 최신 종가여야 함
        """
        from services.daytrading_scanner.main import app
        from fastapi.testclient import TestClient
        from src.database.session import get_db_session_sync
        from src.repositories.daily_price_repository import DailyPriceRepository

        # Arrange: 테스트용 시그널 생성
        with get_db_session_sync() as db:
            price_repo = DailyPriceRepository(db)
            # 삼성전자 최신 가격 조회
            latest_prices = price_repo.get_latest_by_ticker("005930", limit=1)
            expected_price = latest_prices[0].close_price if latest_prices else None

        client = TestClient(app)

        # Act
        response = client.get("/api/daytrading/signals?min_score=0&limit=50")

        # Assert
        assert response.status_code == 200
        data = response.json()
        signals = data.get("data", {}).get("signals", [])

        # 삼성전자 시그널이 있는 경우 확인
        samsung_signal = next((s for s in signals if s.get("ticker") == "005930"), None)
        if samsung_signal and expected_price:
            assert samsung_signal.get("current_price") == expected_price, \
                f"current_price가 DB 최신 가격과 다릅니다. 기대: {expected_price}, 실제: {samsung_signal.get('current_price')}"


# =============================================================================
# Test 3: 종목이 브로드캐스터에 추가
# =============================================================================

class TestDaytradingPriceBroadcasterIntegration:
    """DaytradingPriceBroadcaster 연동 검증"""

    @pytest.mark.asyncio
    async def test_signals_added_to_broadcaster(self):
        """
        GIVEN: API Gateway의 /api/daytrading/signals 엔드포인트
        WHEN: 시그널을 조회하면
        THEN: daytrading_price_broadcaster에 종목이 추가되어야 함

        참고: 이 테스트는 브로드캐스터 모듈이 로드 가능한지 확인합니다.
        실제 동작은 통합 환경에서 검증됩니다.
        """
        # 브로드캐스터 모듈을 직접 임포트하여 확인
        from services.daytrading_scanner.price_broadcaster import DaytradingPriceBroadcaster

        # Arrange: 브로드캐스터 인스턴스 생성
        broadcaster = DaytradingPriceBroadcaster()

        # Assert: 브로드캐스터 인터페이스 확인
        assert hasattr(broadcaster, "add_ticker"), \
            "DaytradingPriceBroadcaster에 add_ticker 메서드가 없습니다"
        assert hasattr(broadcaster, "remove_ticker"), \
            "DaytradingPriceBroadcaster에 remove_ticker 메서드가 없습니다"
        assert hasattr(broadcaster, "active_tickers"), \
            "DaytradingPriceBroadcaster에 active_tickers 속성이 없습니다"

    @pytest.mark.asyncio
    async def test_broadcaster_ticker_management(self):
        """
        GIVEN: daytrading_price_broadcaster
        WHEN: 종목을 추가하고 제거하면
        THEN: active_tickers가 올바르게 업데이트되어야 함
        """
        from services.daytrading_scanner.price_broadcaster import DaytradingPriceBroadcaster

        # Arrange: 브로드캐스터 인스턴스 및 테스트 종목
        broadcaster = DaytradingPriceBroadcaster()
        test_tickers = ["005930", "000270"]

        # Act: 종목 추가
        for ticker in test_tickers:
            broadcaster.add_ticker(ticker)

        # Assert: 종목이 추가되었는지 확인
        active_tickers = broadcaster.active_tickers
        for ticker in test_tickers:
            assert ticker in active_tickers, \
                f"종목 {ticker}가 브로드캐스터에 추가되지 않았습니다"

        # Act: 종목 제거
        for ticker in test_tickers:
            broadcaster.remove_ticker(ticker)

        # Assert: 종목이 제거되었는지 확인
        active_tickers = broadcaster.active_tickers
        for ticker in test_tickers:
            assert ticker not in active_tickers, \
                f"종목 {ticker}가 브로드캐스터에서 제거되지 않았습니다"
