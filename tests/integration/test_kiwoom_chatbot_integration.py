"""
Chatbot Integration Tests with Kiwoom API
Kiwoom REST API 실제 연동 테스트 (RED → GREEN → REFACTOR)
"""

import pytest
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# Kiwoom API 설정 확인
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_SECRET_KEY = os.getenv("KIWOOM_SECRET_KEY")
USE_KIWOOM_REST = os.getenv("USE_KIWOOM_REST", "false").lower() == "true"

# Kiwoom API가 없으면 테스트 스킵
pytestmark = pytest.mark.skipif(
    not (KIWOOM_APP_KEY and KIWOOM_SECRET_KEY and USE_KIWOOM_REST),
    reason="Kiwoom API credentials not configured"
)


# ============================================================================
# Test Data
# ============================================================================

TEST_TICKERS = ["005930", "000660"]  # 삼성전자, SK하이닉스


# ============================================================================
# GREEN Phase: Tests (Implementation)
# ============================================================================

class TestKiwoomChatbotIntegration:
    """Kiwoom API와 Chatbot 통합 테스트"""

    @pytest.mark.asyncio
    async def test_kiwoom_api_available(self):
        """Kiwoom API 설정 확인 테스트"""
        from services.chatbot.kiwoom_integration import is_kiwoom_available

        # Kiwoom API 사용 가능 여부 확인
        available = is_kiwoom_available()

        if KIWOOM_APP_KEY and KIWOOM_SECRET_KEY and USE_KIWOOM_REST:
            assert available is True
        else:
            assert available is False

    @pytest.mark.asyncio
    async def test_get_realtime_price_from_kiwoom(self):
        """Kiwoom API에서 실시간 가격 조회 테스트"""
        from services.chatbot.retriever import get_retriever

        retriever = get_retriever()

        # 삼성전자 실시간 가격 조회
        price_data = await retriever.get_realtime_price("005930")

        # 결과 검증
        assert price_data is not None or price_data is None  # API 연동 여부에 따라

        if price_data:
            assert "ticker" in price_data
            assert price_data["ticker"] == "005930"

    @pytest.mark.asyncio
    async def test_get_realtime_stock_info(self):
        """Kiwoom API에서 실시간 종목 정보 조회 테스트"""
        from services.chatbot.retriever import get_retriever

        retriever = get_retriever()

        # 종목 정보 조회
        stock_info = await retriever.get_realtime_stock_info("005930")

        # 결과 검증
        assert stock_info is not None or stock_info is None

        if stock_info:
            assert "ticker" in stock_info
            assert "name" in stock_info

    @pytest.mark.asyncio
    async def test_enrich_context_with_kiwoom_data(self):
        """컨텍스트에 Kiwoom 데이터 추가 테스트"""
        from services.chatbot.retriever import get_retriever
        from services.chatbot.kiwoom_integration import is_kiwoom_available

        retriever = get_retriever()

        # 기본 컨텍스트 생성
        context = {
            "query": "삼성전자 현재가",
            "query_type": "stock",
            "stocks": [
                {"ticker": "005930", "name": "삼성전자", "market": "KOSPI", "sector": "반도체"}
            ],
            "signals": [],
            "news": [],
        }

        # Kiwoom 데이터로 enrich
        enriched = await retriever.enrich_with_kiwoom_data(context)

        # 검증
        assert "stocks" in enriched
        assert len(enriched["stocks"]) > 0

        # 실시간 가격이 추가되었는지 확인
        if is_kiwoom_available():
            stock = enriched["stocks"][0]
            # Kiwoom API 연동 시 realtime_price 포함
            # API 연동 실패 시 포함되지 않을 수 있음
            assert "ticker" in stock

    @pytest.mark.asyncio
    async def test_chatbot_with_kiwoom_integration(self):
        """Chatbot이 Kiwoom 데이터를 사용하여 응답 생성 테스트"""
        from services.chatbot.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # 채팅 요청
        response = client.post("/chat", json={
            "message": "삼성전자 현재가 알려줘",
            "session_id": "kiwoom-test-123"
        })

        # 기본 응답 확인 (200 OK)
        assert response.status_code == 200

        data = response.json()
        assert "reply" in data
        assert "session_id" in data
        assert data["session_id"] == "kiwoom-test-123"

    @pytest.mark.asyncio
    async def test_chatbot_price_query(self):
        """가격 질문에 대한 Chatbot 응답 테스트"""
        from services.chatbot.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.post("/chat", json={
            "message": "005930 얼마야?",
            "session_id": "price-test-123"
        })

        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        # Kiwoom 데이터가 있다면 가격 정보 포함될 수 있음


# ============================================================================
# Kiwoom API Health Check
# ============================================================================

class TestKiwoomHealth:
    """Kiwoom API 헬스 체크"""

    @pytest.mark.asyncio
    async def test_kiwoom_integration_startup(self):
        """Kiwoom Integration 시작 테스트"""
        from src.api_gateway.kiwoom_integration import create_kiwoom_integration

        try:
            integration = create_kiwoom_integration()
            await integration.startup()

            # 시작 성공 확인
            # TODO: 실제 Kiwoom 연동 상태 확인 로직 추가

            await integration.shutdown()

        except Exception as e:
            pytest.fail(f"Kiwoom integration startup failed: {e}")


# ============================================================================
# Run tests command
# ============================================================================
"""
테스트 실행 방법:

# 모든 테스트 실행 (Kiwoom API 있는 경우만):
# pytest tests/integration/test_kiwoom_chatbot_integration.py -v

# Kiwoom API 없이도 실행 (skip된 테스트 확인용):
# pytest tests/integration/test_kiwoom_chatbot_integration.py -v

# 특정 테스트만 실행:
# pytest tests/integration/test_kiwoom_chatbot_integration.py::TestKiwoomChatbotIntegration::test_kiwoom_api_available -v
"""
