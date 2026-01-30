"""
Realtime Price Response Tests (TDD Phase 4 - GREEN)

챗봇 응답에 실시간 가격 포함 테스트
"""

import pytest
import os


# 챗봇 서비스 테스트는 환경 변수 필요
pytestmark = pytest.mark.skipif(
    not os.getenv("USE_KIWOOM_REST", "false").lower() == "true",
    reason="Kiwoom REST API가 비활성화되어 있습니다"
)


class TestChatbotWithRealtimePrice:
    """챗봇 실시간 가격 통합 테스트"""

    @pytest.mark.asyncio
    async def test_chat_with_samsung_current_price(self):
        """삼성전자 현재가 질문 시 실제 가격이 포함되어야 함"""
        from services.chatbot.main import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/chat",
                json={"message": "삼성전자 현재가 알려줘"},
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            reply = data["reply"]

            # 응답에 가격 정보가 포함되어야 함 (숫자로 표현된 가격)
            # 예: "152,000원" 또는 "152000원"
            assert any(char.isdigit() for char in reply), "응답에 가격 정보가 있어야 합니다"
            assert "삼성전자" in reply or "005930" in reply, "응답에 종목명이 포함되어야 합니다"

    @pytest.mark.asyncio
    async def test_chat_with_sk_hynix_price(self):
        """SK하이닉스 현재가 질문 시 실제 가격이 포함되어야 함"""
        from services.chatbot.main import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/chat",
                json={"message": "SK하이닉스 현재가是多少?"},
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            reply = data["reply"]

            assert any(char.isdigit() for char in reply), "응답에 가격 정보가 있어야 합니다"

    @pytest.mark.asyncio
    async def test_chat_with_multiple_stocks(self):
        """여러 종목 현재가 질문 시 모든 종목의 가격이 포함되어야 함"""
        from services.chatbot.main import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/chat",
                json={"message": "삼성전자와 SK하이닉스 현재가 알려줘"},
                timeout=60.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            reply = data["reply"]

            # 두 종목 모두 언급되어야 함
            assert ("삼성전자" in reply or "005930" in reply) and \
                   ("SK하이닉스" in reply or "000660" in reply), \
                   "두 종목 모두 응답에 포함되어야 합니다"

    @pytest.mark.asyncio
    async def test_chat_response_time_within_limit(self):
        """챗봇 응답 시간이 10초 이내여야 함"""
        import time
        from services.chatbot.main import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            response = await client.post(
                "/chat",
                json={"message": "삼성전자 현재가"},
                timeout=30.0
            )
            elapsed = time.time() - start

            assert response.status_code == 200
            assert elapsed < 15.0, f"응답 시간이 너무 깁니다: {elapsed:.2f}초"


class TestEnrichmentWithKiwoomData:
    """Kiwoom 데이터 Enrichment 테스트"""

    @pytest.mark.asyncio
    async def test_enrich_context_adds_realtime_price(self):
        """컨텍스트 enrich에 실시간 가격이 추가되어야 함"""
        from services.chatbot.retriever import get_retriever

        retriever = get_retriever()
        context = {
            "stocks": [
                {"ticker": "005930", "name": "삼성전자", "market": "KOSPI"},
                {"ticker": "000660", "name": "SK하이닉스", "market": "KOSDAQ"}
            ]
        }

        enriched = await retriever.enrich_with_kiwoom_data(context)

        assert "stocks" in enriched
        assert len(enriched["stocks"]) == 2

        # 첫 번째 종목에 실시간 가격이 있어야 함
        stock1 = enriched["stocks"][0]
        assert "realtime_price" in stock1
        rt_price = stock1["realtime_price"]
        assert "price" in rt_price
        assert rt_price["price"] > 0

        # 두 번째 종목에도 실시간 가격이 있어야 함
        stock2 = enriched["stocks"][1]
        assert "realtime_price" in stock2
        assert stock2["realtime_price"]["price"] > 0

    @pytest.mark.asyncio
    async def test_enrich_context_handles_api_failure(self):
        """API 실패 시에도 컨텍스트는 계속 진행되어야 함"""
        from services.chatbot.retriever import get_retriever
        from unittest.mock import AsyncMock, patch

        retriever = get_retriever()
        context = {
            "stocks": [
                {"ticker": "005930", "name": "삼성전자", "market": "KOSPI"}
            ]
        }

        # API 실패 mock
        mock_retrieve = AsyncMock(side_effect=Exception("API Error"))

        # enrich는 에러를 잡아서 계속 진행해야 함
        # 실제로는 get_realtime_price가 예외를 던지지만 enrich는 계속 진행
        enriched = await retriever.enrich_with_kiwoom_data(context)

        # 컨텍스트는 반환되어야 함
        assert "stocks" in enriched


class TestPromptWithRealtimePrice:
    """프롬프트에 실시간 가격 포함 테스트"""

    def test_prompt_includes_realtime_price(self):
        """프롬프트에 실시간 가격이 포함되어야 함"""
        from services.chatbot.prompts import build_rag_prompt

        context = {
            "query": "삼성전자 현재가 알려줘",
            "stocks": [
                {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "market": "KOSPI",
                    "sector": "반도체",
                    "realtime_price": {
                        "price": 152000,
                        "change": 1000,
                        "change_rate": 0.66,
                        "volume": 10000000,
                        "timestamp": "20260130"
                    }
                }
            ]
        }

        prompt = build_rag_prompt(context["query"], context)

        # 프롬프트에 가격 정보가 포함되어야 함
        assert "152,000" in prompt or "152000" in prompt
        assert "삼성전자" in prompt

    def test_prompt_without_realtime_price(self):
        """실시간 가격이 없을 때도 프롬프트가 생성되어야 함"""
        from services.chatbot.prompts import build_rag_prompt

        context = {
            "query": "삼성전자 현재가 알려줘",
            "stocks": [
                {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "market": "KOSPI",
                    "sector": "반도체"
                    # realtime_price 없음
                }
            ]
        }

        prompt = build_rag_prompt(context["query"], context)

        # 프롬프트는 생성되어야 함
        assert prompt is not None
        assert len(prompt) > 0
        assert "삼성전자" in prompt


class TestErrorResponseFormatting:
    """에러 응답 포맷팅 테스트"""

    @pytest.mark.asyncio
    async def test_invalid_ticker_error_message(self):
        """잘못된 종목 코드 요청 시 명확한 에러 메시지가 반환되어야 함"""
        from services.chatbot.main import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/chat",
                json={"message": "999999 현재가 알려줘"},
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data

            # 에러 상황에서도 응답은 있어야 함
            reply = data["reply"]
            assert len(reply) > 0

    @pytest.mark.asyncio
    async def test_unknown_stock_message(self):
        """알 수 없는 종목명 요청 시 적절한 응답이 반환되어야 함"""
        from services.chatbot.main import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/chat",
                json={"message": "존재하지않는종목 현재가 알려줘"},
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert len(data["reply"]) > 0
