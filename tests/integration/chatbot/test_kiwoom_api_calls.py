"""
Kiwoom API Integration Tests (TDD Phase 1 - RED)

실제 API 호출 테스트: Kiwoom REST API를 통한 데이터 조회
"""

import pytest
import os
from datetime import datetime


class TestKiwoomDailyPricesAPI:
    """Kiwoom 일별 가격 API 통합 테스트"""

    @pytest.mark.asyncio
    async def test_get_daily_prices_samsung(self):
        """삼성전자(005930) 일별 가격 조회가 성공해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        # Kiwoom API가 사용 가능하지 않으면 스킵
        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            result = await get_kiwoom_current_price("005930")

            # 결과 검증
            assert result is not None, "삼성전자 가격 데이터가 있어야 합니다"
            assert "ticker" in result, "ticker 필드가 필요합니다"
            assert "price" in result, "price 필드가 필요합니다"
            assert "change" in result, "change 필드가 필요합니다"
            assert "change_rate" in result, "change_rate 필드가 필요합니다"
            assert "volume" in result, "volume 필드가 필요합니다"
            assert "timestamp" in result, "timestamp 필드가 필요합니다"

            # 데이터 유효성 검증
            assert result["ticker"] == "005930", "티커가 일치해야 합니다"
            assert result["price"] > 0, "가격은 0보다 커야 합니다"
            assert isinstance(result["change"], (int, float)), "등락폭은 숫자여야 합니다"
            assert isinstance(result["change_rate"], (int, float)), "등락률은 숫자여야 합니다"
            assert result["volume"] >= 0, "거래량은 0 이상이어야 합니다"

            # 타임스탬프 검증
            assert len(result["timestamp"]) == 8, "타임스탬프는 YYYYMMDD 형식이어야 합니다"

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")

    @pytest.mark.asyncio
    async def test_get_daily_prices_sk_hynix(self):
        """SK하이닉스(000660) 일별 가격 조회가 성공해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            result = await get_kiwoom_current_price("000660")

            assert result is not None, "SK하이닉스 가격 데이터가 있어야 합니다"
            assert result["ticker"] == "000660"
            assert result["price"] > 0

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")

    @pytest.mark.asyncio
    async def test_get_daily_prices_kakao(self):
        """카카오(035720) 일별 가격 조회가 성공해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            result = await get_kiwoom_current_price("035720")

            assert result is not None, "카카오 가격 데이터가 있어야 합니다"
            assert result["ticker"] == "035720"
            assert result["price"] > 0

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")


class TestKiwoomAPIErrorHandling:
    """Kiwoom API 에러 핸들링 테스트"""

    @pytest.mark.asyncio
    async def test_get_daily_prices_invalid_ticker(self):
        """존재하지 않는 종목 코드로 조회 시 에러가 발생해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            # 존재하지 않는 종목 코드
            with pytest.raises(KiwoomAPIError):
                await get_kiwoom_current_price("999999")
        except KiwoomAPIError:
            # Kiwoom API 자체가 에러를 반환하는 경우
            pytest.skip("Kiwoom API 연결 실패")

    @pytest.mark.asyncio
    async def test_get_daily_prices_empty_ticker(self):
        """빈 종목 코드로 조회 시 에러가 발생해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        with pytest.raises((KiwoomAPIError, ValueError, Exception)):
            await get_kiwoom_current_price("")

    @pytest.mark.asyncio
    async def test_get_daily_prices_malformed_ticker(self):
        """형식이 잘못된 종목 코드로 조회 시 에러가 발생해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        # 6자리가 아닌 티커
        with pytest.raises((KiwoomAPIError, Exception)):
            await get_kiwoom_current_price("00593")  # 5자리


class TestKiwoomAPIResponseAccuracy:
    """Kiwoom API 응답 정확성 테스트"""

    @pytest.mark.asyncio
    async def test_price_calculation_accuracy(self):
        """가격 계산이 정확해야 함 (등락률 계산 검증)"""
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            result = await get_kiwoom_current_price("005930")

            # 등락률 계산 검증: change_rate = (change / (price - change)) * 100
            price = result["price"]
            change = result["change"]
            change_rate = result["change_rate"]

            if price - change > 0:  # 전일가가 0보다 커야 계산 가능
                expected_rate = (change / (price - change)) * 100
                # ±0.1% 오차 허용
                assert abs(change_rate - expected_rate) < 0.1, \
                    f"등락률 계산이 부정확합니다: expected={expected_rate:.2f}, actual={change_rate:.2f}"

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")

    @pytest.mark.asyncio
    async def test_response_time_within_limit(self):
        """API 응답 시간이 2초 이내여야 함"""
        import time
        from services.chatbot.kiwoom_integration import get_kiwoom_current_price, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            start_time = time.time()
            result = await get_kiwoom_current_price("005930")
            elapsed = time.time() - start_time

            assert result is not None, "응답이 있어야 합니다"
            assert elapsed < 2.0, f"API 응답 시간이 너무 깁니다: {elapsed:.2f}초"

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")


class TestKiwoomChartDataAPI:
    """Kiwoom 차트 데이터 API 통합 테스트"""

    @pytest.mark.asyncio
    async def test_get_chart_data_samsung(self):
        """삼성전자 차트 데이터 조회가 성공해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_chart_data, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            result = await get_kiwoom_chart_data("005930", period="D", count=10)

            assert result is not None, "차트 데이터가 있어야 합니다"
            assert isinstance(result, list), "차트 데이터는 리스트여야 합니다"
            assert len(result) > 0, "차트 데이터가 최소 1개 이상이어야 합니다"

            # 첫 번째 데이터 구조 검증
            first_data = result[0]
            assert "date" in first_data
            assert "open" in first_data
            assert "high" in first_data
            assert "low" in first_data
            assert "close" in first_data
            assert "volume" in first_data

            # OHLC 관계 검증: High >= Close, Open >= Low
            assert first_data["high"] >= first_data["close"] >= 0
            assert first_data["high"] >= first_data["open"] >= 0
            assert first_data["low"] <= first_data["open"]

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")


class TestKiwoomStockInfoAPI:
    """Kiwoom 종목 정보 API 통합 테스트"""

    @pytest.mark.asyncio
    async def test_get_stock_info_samsung(self):
        """삼성전자 종목 정보 조회가 성공해야 함"""
        from services.chatbot.kiwoom_integration import get_kiwoom_stock_info, KiwoomAPIError

        if not os.getenv("USE_KIWOOM_REST", "false").lower() == "true":
            pytest.skip("Kiwoom REST API가 비활성화되어 있습니다")

        try:
            result = await get_kiwoom_stock_info("005930")

            assert result is not None, "종목 정보가 있어야 합니다"
            assert "ticker" in result
            assert "market" in result

            # DB에서 종목명을 가져올 수 있으면 확인
            if result.get("name"):
                assert result["name"] == "삼성전자", "종목명이 일치해야 합니다"

        except KiwoomAPIError as e:
            pytest.skip(f"Kiwoom API error: {e}")
